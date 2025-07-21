"""
Web routes for bands (server-side rendered)
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

@router.get("/bands", response_class=HTMLResponse)
async def bands_list(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(24, ge=1, le=100),
    q: Optional[str] = Query(None, description="Search query"),
    sort: Optional[str] = Query("name", description="Sort field"),
    db: DatabaseService = Depends(get_db)
):
    """Render bands list page"""
    # Build query
    where_clauses = []
    if q:
        where_clauses.append(f"b.name CONTAINS '{q}'")
    
    where_clause = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
    
    # Determine sort clause
    sort_mapping = {
        "name": "b.name ASC",
        "-name": "b.name DESC",
        "formed_year": "b.formed_year ASC",
        "-formed_year": "b.formed_year DESC"
    }
    order_clause = f"ORDER BY {sort_mapping.get(sort, 'b.name ASC')}"
    
    # Get total count
    count_query = f"""
        MATCH (b:BAND)
        {where_clause}
        RETURN count(b) as total
    """
    count_result = db.execute_query(count_query)
    total = count_result[0]["total"] if count_result else 0
    total_pages = math.ceil(total / page_size)
    
    # Ensure page is within bounds
    page = min(page, total_pages) if total_pages > 0 else 1
    
    # Get bands with pagination
    offset = (page - 1) * page_size
    query = f"""
        MATCH (b:BAND)
        {where_clause}
        OPTIONAL MATCH (b)-[:RELEASED]->(a:ALBUM)
        WITH b, count(a) as album_count
        RETURN b.id as id, 
               b.name as name,
               b.origin_country as origin,
               b.formed_year as formed_year,
               b.status as status,
               album_count
        {order_clause}
        SKIP {offset} LIMIT {page_size}
    """
    
    results = db.execute_query(query)
    
    # Transform results
    bands = []
    for row in results:
        bands.append({
            "id": row["id"],
            "name": row["name"],
            "origin": row["origin"],
            "formed_year": row["formed_year"],
            "status": row["status"],
            "active": row["status"] == "Active" if row["status"] else True,
            "genres": [],  # Not in schema
            "album_count": row["album_count"]
        })
    
    return templates.TemplateResponse(
        "bands/list.html",
        {
            "request": request,
            "bands": bands,
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": total_pages,
            "search_query": q,
            "sort": sort
        }
    )

@router.get("/bands/{band_id}", response_class=HTMLResponse)
async def band_detail(
    request: Request,
    band_id: str,
    db: DatabaseService = Depends(get_db)
):
    """Render band detail page"""
    # Get band details
    band_query = """
        MATCH (b:BAND {id: $band_id})
        RETURN b.id as id,
               b.name as name,
               b.origin_country as origin,
               b.formed_year as formed_year,
               b.status as status
    """
    
    band_result = db.execute_query(band_query, {"band_id": int(band_id)})
    if not band_result:
        raise HTTPException(status_code=404, detail="Band not found")
    
    band = band_result[0]
    
    # Get albums
    albums_query = """
        MATCH (b:BAND {id: $band_id})-[:RELEASED]->(a:ALBUM)
        RETURN a.id as id,
               a.name as name,
               a.release_date as release_date,
               a.label as label,
               a.album_type as album_type
        ORDER BY a.release_date DESC
    """
    
    albums_result = db.execute_query(albums_query, {"band_id": int(band_id)})
    albums = list(albums_result) if albums_result else []
    
    # Get members
    members_query = """
        MATCH (b:BAND {id: $band_id})<-[:MEMBER_OF]-(p:PERSON)
        RETURN DISTINCT p.id as id,
               p.name as name,
               p.instruments as instruments,
               p.birth_date as birth_date
        ORDER BY p.name
    """
    
    members_result = db.execute_query(members_query, {"band_id": int(band_id)})
    members = list(members_result) if members_result else []
    
    # Get related bands (bands with shared members)
    related_query = """
        MATCH (b:BAND {id: $band_id})<-[:MEMBER_OF]-(p:PERSON)-[:MEMBER_OF]->(other:BAND)
        WHERE other.id <> $band_id
        WITH other, count(p) as shared_members
        RETURN other.id as id,
               other.name as name,
               'Shared members' as relationship
        ORDER BY shared_members DESC
        LIMIT 10
    """
    
    related_result = db.execute_query(related_query, {"band_id": int(band_id)})
    related_bands = list(related_result) if related_result else []
    
    # Calculate stats
    album_count = len(albums)
    member_count = len(members)
    
    years_active = None
    if band["formed_year"]:
        if band["disbanded_year"]:
            years_active = band["disbanded_year"] - band["formed_year"]
        elif band["active"]:
            years_active = 2024 - band["formed_year"]
    
    return templates.TemplateResponse(
        "bands/detail.html",
        {
            "request": request,
            "band": band,
            "albums": albums,
            "members": members,
            "related_bands": related_bands,
            "album_count": album_count,
            "member_count": member_count,
            "years_active": years_active
        }
    )