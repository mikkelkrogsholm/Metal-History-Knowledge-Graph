"""
Enhanced Metal History Knowledge Graph API
Includes caching, semantic search, and performance optimizations
"""

from fastapi import FastAPI, HTTPException, Query, Depends, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime
import kuzu
import json
import time
import logging
import os
from functools import lru_cache

# Import our modules
from caching import CacheManager, CacheWarmer, CacheInvalidator
from semantic_search import SemanticSearchEngine, HybridSearchEngine
from metal_graph_api import (
    BandResponse, AlbumResponse, PersonResponse, 
    SearchRequest, SearchResult, TimelineEntry,
    DatabaseConnection
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Metal History Knowledge Graph API - Enhanced",
    version="2.0.0",
    description="Production-ready API with caching and semantic search"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration
DB_PATH = os.getenv("METAL_GRAPH_DB_PATH", "../schema/metal_history.db")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
EMBEDDINGS_PATH = os.getenv("EMBEDDINGS_PATH", "../entities_with_embeddings.json")

# Initialize components
db_conn = DatabaseConnection(DB_PATH)
cache_manager = CacheManager(redis_url=REDIS_URL)
semantic_engine = SemanticSearchEngine(embeddings_path=EMBEDDINGS_PATH)
hybrid_search = HybridSearchEngine(semantic_engine, db_conn)
cache_warmer = CacheWarmer(cache_manager, db_conn)
cache_invalidator = CacheInvalidator(cache_manager)

# Enhanced models
class SemanticSearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=500)
    entity_types: List[str] = ["bands", "albums", "people"]
    limit: int = Field(default=10, ge=1, le=100)
    use_hybrid: bool = True
    semantic_weight: float = Field(default=0.7, ge=0, le=1)

class SimilarityRequest(BaseModel):
    entity_id: str
    entity_type: str
    limit: int = Field(default=10, ge=1, le=50)

# Middleware for request timing
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = (time.time() - start_time) * 1000
    response.headers["X-Process-Time"] = f"{process_time:.2f}ms"
    
    # Log slow requests
    if process_time > 100:
        logger.warning(f"Slow request: {request.url.path} took {process_time:.2f}ms")
        
    return response

# Dependencies
def get_db():
    return db_conn

def get_cache():
    return cache_manager

# Enhanced endpoints

@app.on_event("startup")
async def startup_event():
    """Initialize connections and warm cache on startup"""
    db_conn.connect()
    logger.info("Database connected")
    
    # Warm cache with popular data
    try:
        await cache_warmer.warm_popular_bands(50)
        await cache_warmer.warm_static_data()
        logger.info("Cache warming completed")
    except Exception as e:
        logger.error(f"Cache warming failed: {e}")
    
    logger.info("API startup complete")

@app.get("/api/v2/bands/{band_id}", response_model=BandResponse)
@cache_manager.cached("band", ttl=7200)
async def get_band_cached(
    band_id: str,
    db: DatabaseConnection = Depends(get_db)
):
    """Get band details with caching"""
    query = """
    MATCH (b:Band {id: $band_id})
    OPTIONAL MATCH (b)-[:PLAYS_GENRE]->(g:Subgenre)
    OPTIONAL MATCH (b)-[:RELEASED]->(a:Album)
    OPTIONAL MATCH (p:Person)-[:MEMBER_OF]->(b)
    OPTIONAL MATCH (b)-[:ORIGINATED_IN]->(loc:GeographicLocation)
    RETURN b.id as id,
           b.name as name, 
           b.formed_year as formed_year,
           b.description as description,
           loc.name as origin_location,
           COLLECT(DISTINCT g.name) as genres,
           COUNT(DISTINCT a) as albums_count,
           COUNT(DISTINCT p) as members_count
    """
    
    result = db.execute_query(query, {"band_id": band_id})
    
    if not result.has_next():
        raise HTTPException(status_code=404, detail=f"Band with id '{band_id}' not found")
    
    row = result.get_next()
    return BandResponse(
        id=row[0],
        name=row[1],
        formed_year=row[2],
        description=row[3],
        origin_location=row[4],
        genres=row[5] if row[5] else [],
        albums_count=row[6],
        members_count=row[7]
    )

@app.post("/api/v2/search/semantic", response_model=List[SearchResult])
async def semantic_search(
    request: SemanticSearchRequest,
    cache: CacheManager = Depends(get_cache)
):
    """Perform semantic or hybrid search"""
    # Check cache
    cache_key = cache._make_key(
        "search",
        request.query,
        str(request.entity_types),
        request.limit,
        request.use_hybrid,
        request.semantic_weight
    )
    
    cached_result = cache.get(cache_key)
    if cached_result:
        return cached_result
    
    # Perform search
    if request.use_hybrid:
        results = hybrid_search.search(
            request.query,
            entity_types=request.entity_types,
            limit=request.limit,
            semantic_weight=request.semantic_weight
        )
    else:
        results = semantic_engine.search(
            request.query,
            entity_types=request.entity_types,
            limit=request.limit
        )
    
    # Convert to API response format
    api_results = []
    for result in results:
        api_results.append(SearchResult(
            entity_type=result['entity_type'],
            id=result['id'],
            name=result['data'].get('name', result['id']),
            relevance_score=result.get('final_score', result.get('relevance_score')),
            metadata=result['data']
        ))
    
    # Cache results
    cache.set(cache_key, api_results, ttl=3600)
    
    return api_results

@app.post("/api/v2/similar")
async def find_similar_entities(
    request: SimilarityRequest,
    cache: CacheManager = Depends(get_cache)
):
    """Find entities similar to a given entity"""
    # Check cache
    cache_key = cache._make_key(
        "similar",
        request.entity_id,
        request.entity_type,
        request.limit
    )
    
    cached_result = cache.get(cache_key)
    if cached_result:
        return cached_result
    
    # Find similar entities
    results = semantic_engine.find_similar(
        request.entity_id,
        request.entity_type,
        request.limit
    )
    
    # Format response
    response = {
        "source_entity": {
            "id": request.entity_id,
            "type": request.entity_type
        },
        "similar_entities": [
            {
                "entity_type": r['entity_type'],
                "id": r['id'],
                "name": r['data'].get('name', r['id']),
                "similarity_score": r['relevance_score'],
                "metadata": r['data']
            }
            for r in results
        ]
    }
    
    # Cache results
    cache.set(cache_key, response, ttl=7200)
    
    return response

@app.get("/api/v2/timeline/{start_year}/{end_year}")
@cache_manager.cached("timeline", ttl=3600)
async def get_timeline_cached(
    start_year: int = Query(..., ge=1960, le=2025),
    end_year: int = Query(..., ge=1960, le=2025),
    db: DatabaseConnection = Depends(get_db)
):
    """Get timeline with caching"""
    if start_year > end_year:
        raise HTTPException(status_code=400, detail="Start year must be before or equal to end year")
    
    # Use parallel queries for better performance
    band_query = """
    MATCH (b:Band)
    WHERE b.formed_year >= $start AND b.formed_year <= $end
    WITH b.formed_year as year, COLLECT({type: 'band_formed', name: b.name, id: b.id}) as events
    ORDER BY year
    RETURN year, events
    """
    
    album_query = """
    MATCH (a:Album)<-[:RELEASED]-(b:Band)
    WHERE a.release_year >= $start AND a.release_year <= $end
    WITH a.release_year as year, 
         COLLECT({
             type: 'album_released', 
             name: a.title, 
             id: a.id, 
             band: b.name,
             band_id: b.id
         }) as events
    ORDER BY year
    RETURN year, events
    """
    
    params = {"start": start_year, "end": end_year}
    
    # Execute both queries
    band_results = db.execute_query(band_query, params)
    album_results = db.execute_query(album_query, params)
    
    # Merge results
    timeline_dict = {}
    
    while band_results.has_next():
        year, events = band_results.get_next()
        if year not in timeline_dict:
            timeline_dict[year] = []
        timeline_dict[year].extend(events)
    
    while album_results.has_next():
        year, events = album_results.get_next()
        if year not in timeline_dict:
            timeline_dict[year] = []
        timeline_dict[year].extend(events)
    
    # Create sorted timeline
    timeline = [
        {
            "year": year,
            "events": sorted(events, key=lambda x: x['name']),
            "event_count": len(events)
        }
        for year, events in sorted(timeline_dict.items())
    ]
    
    return {
        "start_year": start_year,
        "end_year": end_year,
        "total_years": len(timeline),
        "total_events": sum(t["event_count"] for t in timeline),
        "timeline": timeline
    }

@app.get("/api/v2/stats/cache")
async def get_cache_stats(cache: CacheManager = Depends(get_cache)):
    """Get cache statistics"""
    return cache.get_stats()

@app.post("/api/v2/cache/invalidate/{entity_type}/{entity_id}")
async def invalidate_cache(
    entity_type: str,
    entity_id: str,
    cache: CacheManager = Depends(get_cache)
):
    """Invalidate cache for a specific entity"""
    if entity_type == "band":
        cache_invalidator.invalidate_band(entity_id)
    elif entity_type == "album":
        cache_invalidator.invalidate_album(entity_id)
    else:
        cache_invalidator.invalidate_search()
    
    return {"message": f"Cache invalidated for {entity_type}:{entity_id}"}

@app.get("/api/v2/genre-network")
@cache_manager.cached("genre_network", ttl=7200)
async def get_genre_network(db: DatabaseConnection = Depends(get_db)):
    """Get genre relationship network"""
    query = """
    MATCH (g1:Subgenre)<-[:PLAYS_GENRE]-(b:Band)-[:PLAYS_GENRE]->(g2:Subgenre)
    WHERE g1.name < g2.name
    WITH g1.name as genre1, g2.name as genre2, COUNT(DISTINCT b) as shared_bands
    WHERE shared_bands > 2
    ORDER BY shared_bands DESC
    LIMIT 100
    RETURN genre1, genre2, shared_bands
    """
    
    results = db.execute_query(query)
    
    edges = []
    nodes = set()
    
    while results.has_next():
        g1, g2, count = results.get_next()
        edges.append({
            "source": g1,
            "target": g2,
            "weight": count
        })
        nodes.add(g1)
        nodes.add(g2)
    
    return {
        "nodes": [{"id": n, "label": n} for n in sorted(nodes)],
        "edges": edges,
        "total_genres": len(nodes),
        "total_connections": len(edges)
    }

@app.get("/api/v2/recommendations/{band_id}")
async def get_recommendations(
    band_id: str,
    limit: int = Query(default=10, ge=1, le=50),
    db: DatabaseConnection = Depends(get_db),
    cache: CacheManager = Depends(get_cache)
):
    """Get band recommendations based on various factors"""
    # Try cache first
    cache_key = cache._make_key("recommendations", band_id, limit)
    cached = cache.get(cache_key)
    if cached:
        return cached
    
    # Get band info
    band_info = await get_band_cached(band_id, db)
    
    # Find similar bands using multiple strategies
    recommendations = []
    
    # 1. Semantic similarity
    semantic_similar = semantic_engine.find_similar(band_id, "bands", limit * 2)
    for band in semantic_similar[:limit//2]:
        recommendations.append({
            "band_id": band['id'],
            "band_name": band['data'].get('name'),
            "reason": "semantic_similarity",
            "score": band['relevance_score']
        })
    
    # 2. Genre-based recommendations
    if band_info.genres:
        genre_query = """
        MATCH (b:Band)-[:PLAYS_GENRE]->(g:Subgenre)<-[:PLAYS_GENRE]-(other:Band)
        WHERE b.id = $band_id AND other.id <> $band_id
        AND g.name IN $genres
        WITH other, COUNT(DISTINCT g) as shared_genres
        ORDER BY shared_genres DESC
        LIMIT $limit
        RETURN other.id, other.name, shared_genres
        """
        
        genre_results = db.execute_query(
            genre_query,
            {"band_id": band_id, "genres": band_info.genres, "limit": limit//2}
        )
        
        while genre_results.has_next():
            other_id, other_name, shared = genre_results.get_next()
            recommendations.append({
                "band_id": other_id,
                "band_name": other_name,
                "reason": "shared_genres",
                "score": shared / len(band_info.genres)
            })
    
    # 3. Influence-based recommendations
    influence_query = """
    MATCH (b:Band {id: $band_id})-[:INFLUENCED_BY|INFLUENCED*1..2]-(other:Band)
    WHERE other.id <> $band_id
    WITH DISTINCT other
    LIMIT $limit
    RETURN other.id, other.name
    """
    
    influence_results = db.execute_query(
        influence_query,
        {"band_id": band_id, "limit": limit//3}
    )
    
    while influence_results.has_next():
        other_id, other_name = influence_results.get_next()
        recommendations.append({
            "band_id": other_id,
            "band_name": other_name,
            "reason": "influence_network",
            "score": 0.7
        })
    
    # Deduplicate and sort by score
    seen = set()
    unique_recommendations = []
    for rec in sorted(recommendations, key=lambda x: x['score'], reverse=True):
        if rec['band_id'] not in seen:
            seen.add(rec['band_id'])
            unique_recommendations.append(rec)
            if len(unique_recommendations) >= limit:
                break
    
    result = {
        "source_band": {
            "id": band_id,
            "name": band_info.name
        },
        "recommendations": unique_recommendations,
        "total": len(unique_recommendations)
    }
    
    # Cache result
    cache.set(cache_key, result, ttl=3600)
    
    return result

# Health check with detailed status
@app.get("/health/detailed")
async def detailed_health_check(
    db: DatabaseConnection = Depends(get_db),
    cache: CacheManager = Depends(get_cache)
):
    """Detailed health check including all components"""
    health_status = {
        "timestamp": datetime.utcnow().isoformat(),
        "components": {}
    }
    
    # Check database
    try:
        result = db.execute_query("MATCH (n) RETURN COUNT(n) as count LIMIT 1")
        db_healthy = result.has_next()
        health_status["components"]["database"] = {
            "status": "healthy" if db_healthy else "unhealthy",
            "connection": "active" if db_healthy else "failed"
        }
    except Exception as e:
        health_status["components"]["database"] = {
            "status": "unhealthy",
            "error": str(e)
        }
    
    # Check cache
    cache_stats = cache.get_stats()
    health_status["components"]["cache"] = {
        "status": cache_stats.get("status", "unknown"),
        "stats": cache_stats
    }
    
    # Check semantic search
    try:
        if semantic_engine.embeddings_matrix.size > 0:
            health_status["components"]["semantic_search"] = {
                "status": "healthy",
                "embeddings_loaded": len(semantic_engine.entity_index)
            }
        else:
            health_status["components"]["semantic_search"] = {
                "status": "unhealthy",
                "error": "No embeddings loaded"
            }
    except Exception as e:
        health_status["components"]["semantic_search"] = {
            "status": "unhealthy",
            "error": str(e)
        }
    
    # Overall status
    all_healthy = all(
        comp.get("status") == "healthy" 
        for comp in health_status["components"].values()
    )
    
    health_status["status"] = "healthy" if all_healthy else "degraded"
    
    return health_status

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=8000,
        log_config={
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "default": {
                    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                },
            },
            "handlers": {
                "default": {
                    "formatter": "default",
                    "class": "logging.StreamHandler",
                    "stream": "ext://sys.stdout",
                },
            },
            "root": {
                "level": "INFO",
                "handlers": ["default"],
            },
        }
    )