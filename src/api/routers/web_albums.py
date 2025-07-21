"""
Web routes for albums (server-side rendered)
"""

from fastapi import APIRouter, Request, Query, Depends, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from typing import Optional
from pathlib import Path
import math

from src.api.deps import get_db
from src.api.services.database import DatabaseService

# Configure templates
template_dir = Path(__file__).parent.parent / "templates"
templates = Jinja2Templates(directory=str(template_dir))

router = APIRouter()

@router.get("/albums", response_class=HTMLResponse)
async def albums_list(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(24, ge=1, le=100),
    q: Optional[str] = Query(None, description="Search query"),
    sort: Optional[str] = Query("-release_date", description="Sort field"),
    year_from: Optional[int] = Query(None, description="Filter by year from"),
    year_to: Optional[int] = Query(None, description="Filter by year to"),
    db: DatabaseService = Depends(get_db)
):
    """Render albums list page"""
    # Build query
    where_clauses = []
    if q:
        where_clauses.append(f"a.title CONTAINS '{q}'")
    if year_from:
        where_clauses.append(f"a.release_year >= {year_from}")
    if year_to:
        where_clauses.append(f"a.release_year <= {year_to}")
    
    where_clause = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
    
    # Determine sort clause
    sort_mapping = {
        "name": "a.name ASC",
        "-name": "a.name DESC",
        "release_date": "a.release_date ASC",
        "-release_date": "a.release_date DESC"
    }
    order_clause = f"ORDER BY {sort_mapping.get(sort, 'a.release_date DESC')}"
    
    # Get total count
    count_query = f"""
        MATCH (a:ALBUM)
        {where_clause}
        RETURN count(a) as total
    """
    count_result = db.execute_query(count_query)
    total = count_result[0]["total"] if count_result else 0
    total_pages = math.ceil(total / page_size)
    
    # Ensure page is within bounds
    page = min(page, total_pages) if total_pages > 0 else 1
    
    # Get albums with pagination
    offset = (page - 1) * page_size
    query = f"""
        MATCH (a:ALBUM)
        {where_clause}
        OPTIONAL MATCH (b:BAND)-[:RELEASED]->(a)
        RETURN a.id as id, 
               a.title as name,
               a.release_date as release_date,
               a.release_year as release_year,
               a.label as label,
               b.id as band_id,
               b.name as band_name
        {order_clause}
        SKIP {offset} LIMIT {page_size}
    """
    
    results = db.execute_query(query)
    
    # Transform results
    albums = []
    for row in results:
        albums.append({
            "id": row["id"],
            "name": row["name"],
            "release_date": row["release_date"],
            "release_year": row["release_year"],
            "label": row["label"],
            "album_type": "Album",  # Not in schema
            "track_count": 0,  # Not in schema
            "band_id": row["band_id"],
            "band_name": row["band_name"]
        })
    
    return templates.TemplateResponse(
        "albums/list.html",
        {
            "request": request,
            "albums": albums,
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": total_pages,
            "search_query": q,
            "sort": sort,
            "year_from": year_from,
            "year_to": year_to
        }
    )

@router.get("/albums/{album_id}", response_class=HTMLResponse)
async def album_detail(
    request: Request,
    album_id: str,
    db: DatabaseService = Depends(get_db)
):
    """Render album detail page"""
    # Get album details
    album_query = """
        MATCH (a:ALBUM {id: $album_id})
        OPTIONAL MATCH (b:BAND)-[:RELEASED]->(a)
        RETURN a.id as id,
               a.title as name,
               a.release_date as release_date,
               a.release_year as release_year,
               a.label as label,
               b.id as band_id,
               b.name as band_name
    """
    
    album_result = db.execute_query(album_query, {"album_id": int(album_id)})
    if not album_result:
        raise HTTPException(status_code=404, detail="Album not found")
    
    result = album_result[0]
    album = {
        "id": result["id"],
        "name": result["name"],
        "release_date": result["release_date"],
        "release_year": result["release_year"],
        "label": result["label"],
        "album_type": "Album",  # Not in schema
        "catalog_number": None,  # Not in schema
        "format": None,  # Not in schema
        "duration": None,  # Not in schema
        "genres": []  # Not in schema
    }
    
    band = None
    if result["band_id"]:
        band = {
            "id": result["band_id"],
            "name": result["band_name"]
        }
    
    # Get tracks (if available)
    tracks_query = """
        MATCH (a:ALBUM {id: $album_id})-[:CONTAINS]->(t:TRACK)
        RETURN t.position as position,
               t.title as title,
               t.duration as duration,
               t.features as features
        ORDER BY t.position
    """
    
    tracks_result = db.execute_query(tracks_query, {"album_id": int(album_id)})
    tracks = list(tracks_result) if tracks_result else []
    
    # Get credits (if available)
    credits_query = """
        MATCH (a:ALBUM {id: $album_id})<-[r:WORKED_ON]-(p:PERSON)
        RETURN p.name as person,
               r.role as role
        ORDER BY p.name
    """
    
    credits_result = db.execute_query(credits_query, {"album_id": int(album_id)})
    credits = list(credits_result) if credits_result else []
    
    # Get related albums (same year, same band, or similar)
    related_query = """
        MATCH (a:ALBUM {id: $album_id})
        OPTIONAL MATCH (b:BAND)-[:RELEASED]->(a)
        WITH a, b
        MATCH (related:ALBUM)
        WHERE related.id <> $album_id
        AND (
            (b IS NOT NULL AND (b)-[:RELEASED]->(related))
            OR abs(related.release_year - a.release_year) <= 1
        )
        OPTIONAL MATCH (rb:BAND)-[:RELEASED]->(related)
        RETURN DISTINCT related.id as id,
               related.name as name,
               related.release_date as release_date,
               rb.name as band_name
        ORDER BY CASE 
            WHEN b IS NOT NULL AND (b)-[:RELEASED]->(related) THEN 0
            ELSE 1
        END, related.release_date DESC
        LIMIT 8
    """
    
    related_result = db.execute_query(related_query, {"album_id": int(album_id)})
    related_albums = list(related_result) if related_result else []
    
    # Calculate total duration if tracks available
    total_duration = None
    if tracks:
        # This would need proper duration parsing/calculation
        pass
    
    return templates.TemplateResponse(
        "albums/detail.html",
        {
            "request": request,
            "album": album,
            "band": band,
            "tracks": tracks,
            "credits": credits,
            "related_albums": related_albums,
            "total_duration": total_duration
        }
    )