"""
Search endpoints
"""

from fastapi import APIRouter, HTTPException, Query, Depends
from typing import List, Optional
from src.api.models.entities import SearchResult
from src.api.services.database import DatabaseService
from src.api.main import db_service
import numpy as np

router = APIRouter()

def get_db() -> DatabaseService:
    """Get database service dependency"""
    if not db_service:
        raise HTTPException(status_code=503, detail="Database service not available")
    return db_service

@router.get("/", response_model=List[SearchResult])
async def search(
    q: str = Query(..., min_length=2, description="Search query"),
    types: Optional[List[str]] = Query(None, description="Entity types to search"),
    limit: int = Query(20, ge=1, le=100),
    db: DatabaseService = Depends(get_db)
):
    """Search across all entity types"""
    if not types:
        types = ["Band", "Person", "Album", "Song", "Subgenre"]
    
    results = []
    
    for entity_type in types:
        # Text search query
        if entity_type == "Band":
            query = """
                MATCH (b:Band)
                WHERE b.name CONTAINS $q OR b.description CONTAINS $q
                RETURN 'Band' as entity_type, b.id as id, b.name as name,
                       b.description as description
                LIMIT $limit
            """
        elif entity_type == "Album":
            query = """
                MATCH (a:Album)
                WHERE a.title CONTAINS $q OR a.description CONTAINS $q
                RETURN 'Album' as entity_type, a.id as id, a.title as name,
                       a.description as description
                LIMIT $limit
            """
        elif entity_type == "Person":
            query = """
                MATCH (p:Person)
                WHERE p.name CONTAINS $q
                RETURN 'Person' as entity_type, p.id as id, p.name as name,
                       '' as description
                LIMIT $limit
            """
        elif entity_type == "Song":
            query = """
                MATCH (s:Song)
                WHERE s.title CONTAINS $q
                RETURN 'Song' as entity_type, s.id as id, s.title as name,
                       '' as description
                LIMIT $limit
            """
        elif entity_type == "Subgenre":
            query = """
                MATCH (s:Subgenre)
                WHERE s.name CONTAINS $q OR s.key_characteristics CONTAINS $q
                RETURN 'Subgenre' as entity_type, s.id as id, s.name as name,
                       s.key_characteristics as description
                LIMIT $limit
            """
        else:
            continue
        
        entity_results = db.execute_query(query, {"q": q, "limit": limit})
        
        for r in entity_results:
            results.append(SearchResult(
                entity_type=r['entity_type'],
                id=r['id'],
                name=r['name'],
                metadata={"description": r.get('description', '')}
            ))
    
    # Sort by relevance (simple approach - exact matches first)
    results.sort(key=lambda x: (
        not x.name.lower().startswith(q.lower()),
        not q.lower() in x.name.lower(),
        x.name.lower()
    ))
    
    return results[:limit]

@router.post("/semantic")
async def semantic_search(
    query: str,
    entity_type: Optional[str] = None,
    limit: int = Query(10, ge=1, le=50),
    db: DatabaseService = Depends(get_db)
):
    """Semantic search using embeddings (requires embedding generation)"""
    # This would require:
    # 1. Generate embedding for query using same model (snowflake-arctic-embed2)
    # 2. Compare with stored embeddings using cosine similarity
    # 3. Return top results
    
    # For now, return not implemented
    raise HTTPException(
        status_code=501,
        detail="Semantic search not yet implemented. Use regular search endpoint."
    )