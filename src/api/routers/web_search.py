"""
Web routes for search functionality (server-side rendered)
"""

from fastapi import APIRouter, Request, Query, Depends, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from typing import Optional, List
from pathlib import Path
import math

from src.api.deps import get_db
from src.api.services.database import DatabaseService

# Configure templates
template_dir = Path(__file__).parent.parent / "templates"
templates = Jinja2Templates(directory=str(template_dir))

router = APIRouter()

@router.get("/search", response_class=HTMLResponse)
async def search_page(
    request: Request,
    q: Optional[str] = Query(None, description="Search query"),
    type: List[str] = Query(default=[], description="Entity types to search"),
    sort: str = Query("relevance", description="Sort order"),
    year_from: Optional[int] = Query(None, description="Filter by year from"),
    year_to: Optional[int] = Query(None, description="Filter by year to"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: DatabaseService = Depends(get_db)
):
    """Render search page with results"""
    results = []
    total = 0
    total_pages = 0
    
    if q:
        # Perform search
        search_results = await search_entities(
            db, q, type, sort, year_from, year_to, page, page_size
        )
        results = search_results["results"]
        total = search_results["total"]
        total_pages = search_results["total_pages"]
    
    return templates.TemplateResponse(
        "search/search.html",
        {
            "request": request,
            "query": q,
            "results": results,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
            "types": type,
            "sort": sort,
            "year_from": year_from,
            "year_to": year_to,
            "show_filters": bool(type or year_from or year_to or sort != "relevance"),
            "initial_results": bool(q)
        }
    )

@router.get("/search/results", response_class=HTMLResponse)
async def search_results(
    request: Request,
    q: Optional[str] = Query(None, description="Search query"),
    type: List[str] = Query(default=[], description="Entity types to search"),
    sort: str = Query("relevance", description="Sort order"),
    year_from: Optional[int] = Query(None, description="Filter by year from"),
    year_to: Optional[int] = Query(None, description="Filter by year to"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: DatabaseService = Depends(get_db)
):
    """Return search results partial for HTMX"""
    results = []
    total = 0
    total_pages = 0
    
    if q:
        search_results = await search_entities(
            db, q, type, sort, year_from, year_to, page, page_size
        )
        results = search_results["results"]
        total = search_results["total"]
        total_pages = search_results["total_pages"]
    
    return templates.TemplateResponse(
        "search/results.html",
        {
            "request": request,
            "query": q,
            "results": results,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages
        }
    )

@router.get("/search/suggestions", response_class=HTMLResponse)
async def search_suggestions(
    request: Request,
    q: str = Query(..., description="Search query"),
    limit: int = Query(8, ge=1, le=20),
    db: DatabaseService = Depends(get_db)
):
    """Return search suggestions for autocomplete"""
    if len(q) < 2:
        return HTMLResponse("")
    
    suggestions = await get_suggestions(db, q, limit)
    
    return templates.TemplateResponse(
        "search/suggestions.html",
        {
            "request": request,
            "suggestions": suggestions
        }
    )

async def search_entities(
    db: DatabaseService,
    query: str,
    types: List[str],
    sort: str,
    year_from: Optional[int],
    year_to: Optional[int],
    page: int,
    page_size: int
) -> dict:
    """Search across all entity types with filters"""
    # Default to all types if none specified
    if not types:
        types = ["band", "album", "person"]
    
    all_results = []
    
    # Search bands
    if "band" in types:
        band_where = [f"b.name CONTAINS '{query}'"]
        if year_from:
            band_where.append(f"b.formed_year >= {year_from}")
        if year_to:
            band_where.append(f"b.formed_year <= {year_to}")
        
        band_query = f"""
            MATCH (b:BAND)
            WHERE {' AND '.join(band_where)}
            OPTIONAL MATCH (b)-[:RELEASED]->(a:ALBUM)
            WITH b, count(a) as album_count
            RETURN b.id as id,
                   b.name as name,
                   b.origin_country as origin,
                   b.formed_year as formed_year,
                   b.status as status,
                   album_count,
                   'band' as type
        """
        
        band_results = db.execute_query(band_query)
        for row in band_results:
            all_results.append({
                "id": row["id"],
                "name": row["name"],
                "type": "band",
                "origin": row["origin"],
                "formed_year": row["formed_year"],
                "status": row["status"],
                "album_count": row["album_count"],
                "relevance_score": calculate_relevance(query, row["name"])
            })
    
    # Search albums
    if "album" in types:
        album_where = [f"a.title CONTAINS '{query}'"]
        if year_from:
            album_where.append(f"a.release_year >= {year_from}")
        if year_to:
            album_where.append(f"a.release_year <= {year_to}")
        
        album_query = f"""
            MATCH (a:ALBUM)
            WHERE {' AND '.join(album_where)}
            OPTIONAL MATCH (b:BAND)-[:RELEASED]->(a)
            RETURN a.id as id,
                   a.title as name,
                   a.release_date as release_date,
                   a.release_year as release_year,
                   a.label as label,
                   b.id as band_id,
                   b.name as band_name,
                   'album' as type
        """
        
        album_results = db.execute_query(album_query)
        for row in album_results:
            all_results.append({
                "id": row["id"],
                "name": row["name"],
                "type": "album",
                "release_date": row["release_date"],
                "release_year": row["release_year"],
                "label": row["label"],
                "band_id": row["band_id"],
                "band_name": row["band_name"],
                "relevance_score": calculate_relevance(query, row["name"])
            })
    
    # Search people
    if "person" in types:
        person_query = f"""
            MATCH (p:PERSON)
            WHERE p.name CONTAINS '{query}'
            OPTIONAL MATCH (p)-[:MEMBER_OF]->(b:BAND)
            WITH p, collect({{id: b.id, name: b.name}}) as bands
            RETURN p.id as id,
                   p.name as name,
                   bands,
                   'person' as type
        """
        
        person_results = db.execute_query(person_query)
        for row in person_results:
            all_results.append({
                "id": row["id"],
                "name": row["name"],
                "type": "person",
                "instruments": [],  # Not in schema
                "birth_date": None,  # Not in schema
                "bands": [b for b in row["bands"] if b["id"]],
                "relevance_score": calculate_relevance(query, row["name"])
            })
    
    # Sort results
    if sort == "relevance":
        all_results.sort(key=lambda x: x["relevance_score"], reverse=True)
    elif sort == "name":
        all_results.sort(key=lambda x: x["name"])
    elif sort == "-name":
        all_results.sort(key=lambda x: x["name"], reverse=True)
    elif sort == "year":
        all_results.sort(key=lambda x: x.get("formed_year") or x.get("release_year") or 0)
    elif sort == "-year":
        all_results.sort(key=lambda x: x.get("formed_year") or x.get("release_year") or 0, reverse=True)
    
    # Paginate
    total = len(all_results)
    total_pages = math.ceil(total / page_size) if total > 0 else 0
    start = (page - 1) * page_size
    end = start + page_size
    paginated_results = all_results[start:end]
    
    return {
        "results": paginated_results,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages
    }

async def get_suggestions(db: DatabaseService, query: str, limit: int) -> List[dict]:
    """Get quick suggestions for autocomplete"""
    suggestions = []
    
    # Get band suggestions
    band_query = f"""
        MATCH (b:BAND)
        WHERE b.name CONTAINS '{query}'
        RETURN b.id as id,
               b.name as name,
               b.origin_country as origin,
               'band' as type
        ORDER BY b.name
        LIMIT {limit // 3}
    """
    
    band_results = db.execute_query(band_query)
    for row in band_results:
        suggestions.append({
            "id": row["id"],
            "name": row["name"],
            "type": "band",
            "origin": row["origin"]
        })
    
    # Get album suggestions
    album_query = f"""
        MATCH (a:ALBUM)
        WHERE a.title CONTAINS '{query}'
        OPTIONAL MATCH (b:BAND)-[:RELEASED]->(a)
        RETURN a.id as id,
               a.title as name,
               b.name as band_name,
               'album' as type
        ORDER BY a.title
        LIMIT {limit // 3}
    """
    
    album_results = db.execute_query(album_query)
    for row in album_results:
        suggestions.append({
            "id": row["id"],
            "name": row["name"],
            "type": "album",
            "band_name": row["band_name"]
        })
    
    # Get person suggestions
    person_query = f"""
        MATCH (p:PERSON)
        WHERE p.name CONTAINS '{query}'
        RETURN p.id as id,
               p.name as name,
               'person' as type
        ORDER BY p.name
        LIMIT {limit // 3}
    """
    
    person_results = db.execute_query(person_query)
    for row in person_results:
        suggestions.append({
            "id": row["id"],
            "name": row["name"],
            "type": "person"
        })
    
    # Sort by relevance
    suggestions.sort(key=lambda x: calculate_relevance(query, x["name"]), reverse=True)
    
    return suggestions[:limit]

def calculate_relevance(query: str, text: str) -> float:
    """Calculate simple relevance score"""
    if not text:
        return 0.0
    
    query_lower = query.lower()
    text_lower = text.lower()
    
    # Exact match
    if query_lower == text_lower:
        return 1.0
    
    # Starts with query
    if text_lower.startswith(query_lower):
        return 0.8
    
    # Contains query
    if query_lower in text_lower:
        return 0.6
    
    # Word match
    query_words = set(query_lower.split())
    text_words = set(text_lower.split())
    if query_words.intersection(text_words):
        return 0.4
    
    return 0.2