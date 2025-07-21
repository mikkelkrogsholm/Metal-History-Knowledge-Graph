"""
Metal History Knowledge Graph API
Production-ready REST and GraphQL API for exploring metal music history
"""

from fastapi import FastAPI, HTTPException, Query, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime
import kuzu
import json
import time
import logging
from functools import lru_cache
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Metal History Knowledge Graph API",
    version="1.0.0",
    description="Explore the complete history of heavy metal music through a knowledge graph"
)

# CORS middleware for production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure with specific origins in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database configuration
DB_PATH = os.getenv("METAL_GRAPH_DB_PATH", "../schema/metal_history.db")

# Pydantic models for API responses
class BandResponse(BaseModel):
    id: str
    name: str
    formed_year: Optional[int] = None
    origin_location: Optional[str] = None
    genres: List[str] = []
    description: Optional[str] = None
    albums_count: int = 0
    members_count: int = 0
    
class AlbumResponse(BaseModel):
    id: str
    title: str
    release_year: Optional[int] = None
    band_name: Optional[str] = None
    songs: List[str] = []
    genres: List[str] = []

class PersonResponse(BaseModel):
    id: str
    name: str
    birth_year: Optional[int] = None
    bands: List[str] = []
    instruments: List[str] = []
    
class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=500)
    entity_types: List[str] = ["bands", "albums", "people"]
    limit: int = Field(default=10, ge=1, le=100)
    offset: int = Field(default=0, ge=0)

class SearchResult(BaseModel):
    entity_type: str
    id: str
    name: str
    relevance_score: Optional[float] = None
    metadata: Dict[str, Any] = {}

class TimelineEntry(BaseModel):
    year: int
    events: List[Dict[str, Any]]

# Database connection management
class DatabaseConnection:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.db = None
        self.conn = None
        
    def connect(self):
        """Establish database connection"""
        try:
            self.db = kuzu.Database(self.db_path)
            self.conn = kuzu.Connection(self.db)
            logger.info(f"Connected to database at {self.db_path}")
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            raise
            
    def disconnect(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
            logger.info("Database connection closed")
            
    def execute_query(self, query: str, params: dict = None):
        """Execute a Cypher query with optional parameters"""
        if not self.conn:
            self.connect()
            
        try:
            start_time = time.time()
            result = self.conn.execute(query, params or {})
            execution_time = (time.time() - start_time) * 1000
            
            # Log slow queries
            if execution_time > 100:
                logger.warning(f"Slow query ({execution_time:.2f}ms): {query[:100]}...")
                
            return result
        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            raise HTTPException(status_code=500, detail="Database query failed")

# Initialize database connection
db_conn = DatabaseConnection(DB_PATH)

# Dependency to get database connection
def get_db():
    return db_conn

# API Endpoints

@app.on_event("startup")
async def startup_event():
    """Initialize database connection on startup"""
    db_conn.connect()
    logger.info("API startup complete")

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up database connection on shutdown"""
    db_conn.disconnect()
    logger.info("API shutdown complete")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Test database connection
        result = db_conn.execute_query("MATCH (n) RETURN COUNT(n) as count LIMIT 1")
        db_healthy = result.has_next()
    except:
        db_healthy = False
        
    return {
        "status": "healthy" if db_healthy else "unhealthy",
        "timestamp": datetime.utcnow().isoformat(),
        "database": "connected" if db_healthy else "disconnected"
    }

@app.get("/api/v1/bands/{band_id}", response_model=BandResponse)
async def get_band(band_id: str, db: DatabaseConnection = Depends(get_db)):
    """Get detailed information about a specific band"""
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

@app.get("/api/v1/albums/{album_id}", response_model=AlbumResponse)
async def get_album(album_id: str, db: DatabaseConnection = Depends(get_db)):
    """Get detailed information about a specific album"""
    query = """
    MATCH (a:Album {id: $album_id})
    OPTIONAL MATCH (b:Band)-[:RELEASED]->(a)
    OPTIONAL MATCH (a)-[:CONTAINS]->(s:Song)
    OPTIONAL MATCH (a)-[:ALBUM_GENRE]->(g:Subgenre)
    RETURN a.id as id,
           a.title as title,
           a.release_year as release_year,
           b.name as band_name,
           COLLECT(DISTINCT s.title) as songs,
           COLLECT(DISTINCT g.name) as genres
    """
    
    result = db.execute_query(query, {"album_id": album_id})
    
    if not result.has_next():
        raise HTTPException(status_code=404, detail=f"Album with id '{album_id}' not found")
    
    row = result.get_next()
    return AlbumResponse(
        id=row[0],
        title=row[1],
        release_year=row[2],
        band_name=row[3],
        songs=row[4] if row[4] else [],
        genres=row[5] if row[5] else []
    )

@app.get("/api/v1/people/{person_id}", response_model=PersonResponse)
async def get_person(person_id: str, db: DatabaseConnection = Depends(get_db)):
    """Get detailed information about a specific person"""
    query = """
    MATCH (p:Person {id: $person_id})
    OPTIONAL MATCH (p)-[:MEMBER_OF]->(b:Band)
    OPTIONAL MATCH (p)-[:PLAYS]->(i:Instrument)
    RETURN p.id as id,
           p.name as name,
           p.birth_year as birth_year,
           COLLECT(DISTINCT b.name) as bands,
           COLLECT(DISTINCT i.name) as instruments
    """
    
    result = db.execute_query(query, {"person_id": person_id})
    
    if not result.has_next():
        raise HTTPException(status_code=404, detail=f"Person with id '{person_id}' not found")
    
    row = result.get_next()
    return PersonResponse(
        id=row[0],
        name=row[1],
        birth_year=row[2],
        bands=row[3] if row[3] else [],
        instruments=row[4] if row[4] else []
    )

@app.post("/api/v1/search", response_model=List[SearchResult])
async def search_entities(
    request: SearchRequest,
    db: DatabaseConnection = Depends(get_db)
):
    """Search for entities using keyword matching"""
    results = []
    
    # Build search query based on entity types
    if "bands" in request.entity_types:
        band_query = """
        MATCH (b:Band)
        WHERE b.name =~ $pattern
        RETURN 'band' as type, b.id as id, b.name as name, 
               b.formed_year as formed_year, b.description as description
        LIMIT $limit OFFSET $offset
        """
        
        pattern = f".*{request.query}.*"
        band_results = db.execute_query(
            band_query, 
            {"pattern": pattern, "limit": request.limit, "offset": request.offset}
        )
        
        while band_results.has_next():
            row = band_results.get_next()
            results.append(SearchResult(
                entity_type=row[0],
                id=row[1],
                name=row[2],
                metadata={
                    "formed_year": row[3],
                    "description": row[4][:200] if row[4] else None
                }
            ))
    
    if "albums" in request.entity_types:
        album_query = """
        MATCH (a:Album)
        WHERE a.title =~ $pattern
        OPTIONAL MATCH (b:Band)-[:RELEASED]->(a)
        RETURN 'album' as type, a.id as id, a.title as name,
               a.release_year as release_year, b.name as band_name
        LIMIT $limit OFFSET $offset
        """
        
        pattern = f".*{request.query}.*"
        album_results = db.execute_query(
            album_query,
            {"pattern": pattern, "limit": request.limit, "offset": request.offset}
        )
        
        while album_results.has_next():
            row = album_results.get_next()
            results.append(SearchResult(
                entity_type=row[0],
                id=row[1],
                name=row[2],
                metadata={
                    "release_year": row[3],
                    "band_name": row[4]
                }
            ))
    
    if "people" in request.entity_types:
        person_query = """
        MATCH (p:Person)
        WHERE p.name =~ $pattern
        RETURN 'person' as type, p.id as id, p.name as name
        LIMIT $limit OFFSET $offset
        """
        
        pattern = f".*{request.query}.*"
        person_results = db.execute_query(
            person_query,
            {"pattern": pattern, "limit": request.limit, "offset": request.offset}
        )
        
        while person_results.has_next():
            row = person_results.get_next()
            results.append(SearchResult(
                entity_type=row[0],
                id=row[1],
                name=row[2],
                metadata={}
            ))
    
    return results

@app.get("/api/v1/timeline/{start_year}/{end_year}", response_model=List[TimelineEntry])
async def get_timeline(
    start_year: int = Query(..., ge=1960, le=2025),
    end_year: int = Query(..., ge=1960, le=2025),
    db: DatabaseConnection = Depends(get_db)
):
    """Get timeline of metal history events between specified years"""
    if start_year > end_year:
        raise HTTPException(status_code=400, detail="Start year must be before or equal to end year")
    
    query = """
    MATCH (b:Band)
    WHERE b.formed_year >= $start AND b.formed_year <= $end
    WITH b.formed_year as year, COLLECT({type: 'band_formed', name: b.name, id: b.id}) as band_events
    ORDER BY year
    RETURN year, band_events
    """
    
    # Also get album releases
    album_query = """
    MATCH (a:Album)
    WHERE a.release_year >= $start AND a.release_year <= $end
    OPTIONAL MATCH (b:Band)-[:RELEASED]->(a)
    WITH a.release_year as year, 
         COLLECT({type: 'album_released', name: a.title, id: a.id, band: b.name}) as album_events
    ORDER BY year
    RETURN year, album_events
    """
    
    # Execute queries
    band_results = db.execute_query(query, {"start": start_year, "end": end_year})
    album_results = db.execute_query(album_query, {"start": start_year, "end": end_year})
    
    # Combine results by year
    timeline_dict = {}
    
    # Add band formations
    while band_results.has_next():
        row = band_results.get_next()
        year, events = row[0], row[1]
        if year not in timeline_dict:
            timeline_dict[year] = []
        timeline_dict[year].extend(events)
    
    # Add album releases
    while album_results.has_next():
        row = album_results.get_next()
        year, events = row[0], row[1]
        if year not in timeline_dict:
            timeline_dict[year] = []
        timeline_dict[year].extend(events)
    
    # Convert to sorted list
    timeline = [
        TimelineEntry(year=year, events=events)
        for year, events in sorted(timeline_dict.items())
    ]
    
    return timeline

@app.get("/api/v1/genres")
async def get_genres(db: DatabaseConnection = Depends(get_db)):
    """Get all genres and subgenres in the database"""
    query = """
    MATCH (g:Subgenre)
    OPTIONAL MATCH (g)<-[:PLAYS_GENRE]-(b:Band)
    WITH g.name as genre, COUNT(DISTINCT b) as band_count
    ORDER BY band_count DESC
    RETURN genre, band_count
    """
    
    result = db.execute_query(query)
    genres = []
    
    while result.has_next():
        row = result.get_next()
        genres.append({
            "name": row[0],
            "band_count": row[1]
        })
    
    return {"genres": genres, "total": len(genres)}

@app.get("/api/v1/influences/{band_id}")
async def get_band_influences(band_id: str, db: DatabaseConnection = Depends(get_db)):
    """Get influence network for a band"""
    # Check if band exists
    check_query = "MATCH (b:Band {id: $band_id}) RETURN b.name"
    check_result = db.execute_query(check_query, {"band_id": band_id})
    
    if not check_result.has_next():
        raise HTTPException(status_code=404, detail=f"Band with id '{band_id}' not found")
    
    band_name = check_result.get_next()[0]
    
    # Get influences
    influenced_by_query = """
    MATCH (b:Band {id: $band_id})-[:INFLUENCED_BY]->(influenced:Band)
    RETURN influenced.id as id, influenced.name as name, influenced.formed_year as formed_year
    """
    
    influenced_query = """
    MATCH (b:Band {id: $band_id})<-[:INFLUENCED_BY]-(influenced:Band)
    RETURN influenced.id as id, influenced.name as name, influenced.formed_year as formed_year
    """
    
    influenced_by_results = db.execute_query(influenced_by_query, {"band_id": band_id})
    influenced_results = db.execute_query(influenced_query, {"band_id": band_id})
    
    influenced_by = []
    while influenced_by_results.has_next():
        row = influenced_by_results.get_next()
        influenced_by.append({
            "id": row[0],
            "name": row[1],
            "formed_year": row[2]
        })
    
    influenced = []
    while influenced_results.has_next():
        row = influenced_results.get_next()
        influenced.append({
            "id": row[0],
            "name": row[1],
            "formed_year": row[2]
        })
    
    return {
        "band_id": band_id,
        "band_name": band_name,
        "influenced_by": influenced_by,
        "influenced": influenced,
        "total_connections": len(influenced_by) + len(influenced)
    }

@app.get("/api/v1/stats")
async def get_database_stats(db: DatabaseConnection = Depends(get_db)):
    """Get database statistics"""
    stats_queries = {
        "total_bands": "MATCH (b:Band) RETURN COUNT(b)",
        "total_albums": "MATCH (a:Album) RETURN COUNT(a)",
        "total_people": "MATCH (p:Person) RETURN COUNT(p)",
        "total_songs": "MATCH (s:Song) RETURN COUNT(s)",
        "total_genres": "MATCH (g:Subgenre) RETURN COUNT(g)",
        "total_locations": "MATCH (l:GeographicLocation) RETURN COUNT(l)",
        "total_relationships": "MATCH ()-[r]->() RETURN COUNT(r)"
    }
    
    stats = {}
    for key, query in stats_queries.items():
        result = db.execute_query(query)
        if result.has_next():
            stats[key] = result.get_next()[0]
        else:
            stats[key] = 0
    
    # Get some interesting aggregates
    decade_query = """
    MATCH (b:Band)
    WHERE b.formed_year IS NOT NULL
    WITH floor(b.formed_year / 10) * 10 as decade, COUNT(b) as count
    ORDER BY decade
    RETURN decade, count
    """
    
    decade_results = db.execute_query(decade_query)
    decades = []
    while decade_results.has_next():
        row = decade_results.get_next()
        decades.append({
            "decade": int(row[0]),
            "band_count": row[1]
        })
    
    stats["bands_by_decade"] = decades
    
    return stats

# Error handlers
@app.exception_handler(404)
async def not_found_handler(request, exc):
    return JSONResponse(
        status_code=404,
        content={"detail": str(exc.detail)}
    )

@app.exception_handler(500)
async def internal_error_handler(request, exc):
    logger.error(f"Internal server error: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)