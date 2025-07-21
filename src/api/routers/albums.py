"""
Album endpoints
"""

from fastapi import APIRouter, HTTPException, Query, Depends
from typing import List, Optional
from src.api.models.entities import AlbumResponse, PaginatedResponse
from src.api.services.database import DatabaseService
from src.api.main import db_service

router = APIRouter()

def get_db() -> DatabaseService:
    """Get database service dependency"""
    if not db_service:
        raise HTTPException(status_code=503, detail="Database service not available")
    return db_service

@router.get("/", response_model=PaginatedResponse)
async def get_albums(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    year: Optional[int] = None,
    label: Optional[str] = None,
    db: DatabaseService = Depends(get_db)
):
    """Get all albums with optional filtering"""
    # Build query
    where_clauses = []
    if year:
        where_clauses.append(f"a.release_year = {year}")
    if label:
        where_clauses.append(f"a.label = '{label}'")
    
    where_clause = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
    
    # Get total count
    count_query = f"MATCH (a:Album) {where_clause} RETURN COUNT(a) as count"
    count_result = db.execute_query(count_query)
    total = count_result[0]['count'] if count_result else 0
    
    # Get paginated results
    offset = (page - 1) * page_size
    query = f"""
        MATCH (a:Album) {where_clause}
        OPTIONAL MATCH (b:Band)-[:RELEASED]->(a)
        RETURN a.id as id, a.title as title, a.release_year as release_year,
               a.release_date as release_date, a.label as label,
               a.studio as studio, a.description as description,
               b.name as band_name
        ORDER BY a.release_year DESC, a.title
        LIMIT {page_size} OFFSET {offset}
    """
    
    results = db.execute_query(query)
    albums = [AlbumResponse(**r) for r in results]
    
    return PaginatedResponse(
        items=albums,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size
    )

@router.get("/{album_id}", response_model=AlbumResponse)
async def get_album(album_id: int, db: DatabaseService = Depends(get_db)):
    """Get album by ID"""
    query = """
        MATCH (a:Album {id: $id})
        OPTIONAL MATCH (b:Band)-[:RELEASED]->(a)
        RETURN a.id as id, a.title as title, a.release_year as release_year,
               a.release_date as release_date, a.label as label,
               a.studio as studio, a.description as description,
               b.name as band_name
    """
    
    results = db.execute_query(query, {"id": album_id})
    if not results:
        raise HTTPException(status_code=404, detail="Album not found")
    
    return AlbumResponse(**results[0])

@router.get("/{album_id}/songs")
async def get_album_songs(album_id: int, db: DatabaseService = Depends(get_db)):
    """Get songs from album"""
    query = """
        MATCH (a:Album {id: $id})-[:CONTAINS_TRACK]->(s:Song)
        RETURN s.id as id, s.title as title, s.track_number as track_number,
               s.duration as duration, s.lyrics_theme as lyrics_theme
        ORDER BY s.track_number
    """
    
    results = db.execute_query(query, {"id": album_id})
    return results