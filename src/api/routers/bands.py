"""
Band endpoints
"""

from fastapi import APIRouter, HTTPException, Query, Depends
from typing import List, Optional
from src.api.models.entities import BandResponse, AlbumResponse, PersonResponse, PaginatedResponse
from src.api.services.database import DatabaseService
from src.api.deps import get_db

router = APIRouter()

@router.get("/", response_model=PaginatedResponse)
async def get_bands(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    country: Optional[str] = None,
    year: Optional[int] = None,
    db: DatabaseService = Depends(get_db)
):
    """Get all bands with optional filtering"""
    # Build query
    where_clauses = []
    if country:
        where_clauses.append(f"b.origin_country = '{country}'")
    if year:
        where_clauses.append(f"b.formed_year = {year}")
    
    where_clause = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
    
    # Get total count
    count_query = f"MATCH (b:Band) {where_clause} RETURN COUNT(b) as count"
    count_result = db.execute_query(count_query)
    total = count_result[0]['count'] if count_result else 0
    
    # Get paginated results
    offset = (page - 1) * page_size
    query = f"""
        MATCH (b:Band) {where_clause}
        RETURN b.id as id, b.name as name, b.formed_year as formed_year,
               b.origin_city as origin_city, b.origin_country as origin_country,
               b.status as status, b.description as description
        ORDER BY b.name
        LIMIT {page_size} OFFSET {offset}
    """
    
    results = db.execute_query(query)
    bands = [BandResponse(**r) for r in results]
    
    return PaginatedResponse(
        items=bands,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size
    )

@router.get("/{band_id}", response_model=BandResponse)
async def get_band(band_id: int, db: DatabaseService = Depends(get_db)):
    """Get band by ID"""
    query = """
        MATCH (b:Band {id: $id})
        RETURN b.id as id, b.name as name, b.formed_year as formed_year,
               b.origin_city as origin_city, b.origin_country as origin_country,
               b.status as status, b.description as description
    """
    
    results = db.execute_query(query, {"id": band_id})
    if not results:
        raise HTTPException(status_code=404, detail="Band not found")
    
    return BandResponse(**results[0])

@router.get("/{band_id}/albums", response_model=List[AlbumResponse])
async def get_band_albums(band_id: int, db: DatabaseService = Depends(get_db)):
    """Get albums by band"""
    query = """
        MATCH (b:Band {id: $id})-[:RELEASED]->(a:Album)
        RETURN a.id as id, a.title as title, a.release_year as release_year,
               a.release_date as release_date, a.label as label,
               a.studio as studio, a.description as description,
               b.name as band_name
        ORDER BY a.release_year
    """
    
    results = db.execute_query(query, {"id": band_id})
    return [AlbumResponse(**r) for r in results]

@router.get("/{band_id}/members", response_model=List[PersonResponse])
async def get_band_members(band_id: int, db: DatabaseService = Depends(get_db)):
    """Get band members"""
    query = """
        MATCH (p:Person)-[:MEMBER_OF]->(b:Band {id: $id})
        RETURN p.id as id, p.name as name, p.birth_date as birth_date,
               p.birth_place as birth_place, p.instruments as instruments
    """
    
    results = db.execute_query(query, {"id": band_id})
    
    # Get all bands for each person
    people = []
    for r in results:
        person_bands_query = """
            MATCH (p:Person {id: $id})-[:MEMBER_OF]->(b:Band)
            RETURN b.name as band_name
        """
        bands_result = db.execute_query(person_bands_query, {"id": r['id']})
        r['bands'] = [b['band_name'] for b in bands_result]
        people.append(PersonResponse(**r))
    
    return people