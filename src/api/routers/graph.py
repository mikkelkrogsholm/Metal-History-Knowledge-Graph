"""
Graph query endpoints
"""

from fastapi import APIRouter, HTTPException, Query, Depends
from typing import Optional
from src.api.models.entities import GraphResponse, GraphNode, GraphEdge
from src.api.services.database import DatabaseService
from src.api.main import db_service

router = APIRouter()

def get_db() -> DatabaseService:
    """Get database service dependency"""
    if not db_service:
        raise HTTPException(status_code=503, detail="Database service not available")
    return db_service

@router.get("/neighborhood/{entity_type}/{entity_id}", response_model=GraphResponse)
async def get_entity_neighborhood(
    entity_type: str,
    entity_id: int,
    depth: int = Query(1, ge=1, le=3, description="Traversal depth"),
    db: DatabaseService = Depends(get_db)
):
    """Get graph neighborhood around an entity"""
    # Get the center node
    center_query = f"""
        MATCH (n:{entity_type} {{id: $id}})
        RETURN n
    """
    
    center_results = db.execute_query(center_query, {"id": entity_id})
    if not center_results:
        raise HTTPException(status_code=404, detail=f"{entity_type} not found")
    
    # Get neighborhood based on depth
    neighbor_query = f"""
        MATCH path = (n:{entity_type} {{id: $id}})-[*1..{depth}]-(m)
        RETURN path
    """
    
    paths = db.execute_query(neighbor_query, {"id": entity_id})
    
    # Extract unique nodes and edges
    nodes = {}
    edges = {}
    
    # Add center node
    center = center_results[0]['n']
    center_id = f"{entity_type}_{entity_id}"
    nodes[center_id] = GraphNode(
        id=center_id,
        label=center.get('name', center.get('title', str(entity_id))),
        type=entity_type,
        properties=center
    )
    
    # Process paths (simplified - would need proper path parsing)
    # This is a placeholder implementation
    for i, path in enumerate(paths[:20]):  # Limit to prevent huge graphs
        # Add connected nodes and edges based on path structure
        # Real implementation would parse the path object properly
        pass
    
    return GraphResponse(
        nodes=list(nodes.values()),
        edges=list(edges.values())
    )

@router.get("/subgenre-evolution", response_model=GraphResponse)
async def get_subgenre_evolution(db: DatabaseService = Depends(get_db)):
    """Get subgenre evolution graph"""
    query = """
        MATCH (s1:Subgenre)-[e:EVOLVED_INTO]->(s2:Subgenre)
        RETURN s1, e, s2
    """
    
    results = db.execute_query(query)
    
    nodes = {}
    edges = []
    
    for r in results:
        # Add source node
        s1_id = f"Subgenre_{r['s1']['id']}"
        if s1_id not in nodes:
            nodes[s1_id] = GraphNode(
                id=s1_id,
                label=r['s1']['name'],
                type="Subgenre",
                properties=r['s1']
            )
        
        # Add target node
        s2_id = f"Subgenre_{r['s2']['id']}"
        if s2_id not in nodes:
            nodes[s2_id] = GraphNode(
                id=s2_id,
                label=r['s2']['name'],
                type="Subgenre",
                properties=r['s2']
            )
        
        # Add edge
        edges.append(GraphEdge(
            id=f"{s1_id}_evolves_{s2_id}",
            source=s1_id,
            target=s2_id,
            type="EVOLVED_INTO",
            properties=r.get('e', {})
        ))
    
    return GraphResponse(nodes=list(nodes.values()), edges=edges)

@router.get("/band-connections/{band_id}", response_model=GraphResponse)
async def get_band_connections(
    band_id: int,
    db: DatabaseService = Depends(get_db)
):
    """Get connections between bands through shared members"""
    query = """
        MATCH (b1:Band {id: $id})<-[:MEMBER_OF]-(p:Person)-[:MEMBER_OF]->(b2:Band)
        WHERE b1.id != b2.id
        RETURN DISTINCT b1, p, b2
    """
    
    results = db.execute_query(query, {"id": band_id})
    
    nodes = {}
    edges = []
    
    for r in results:
        # Add bands
        b1_id = f"Band_{r['b1']['id']}"
        if b1_id not in nodes:
            nodes[b1_id] = GraphNode(
                id=b1_id,
                label=r['b1']['name'],
                type="Band",
                properties=r['b1']
            )
        
        b2_id = f"Band_{r['b2']['id']}"
        if b2_id not in nodes:
            nodes[b2_id] = GraphNode(
                id=b2_id,
                label=r['b2']['name'],
                type="Band",
                properties=r['b2']
            )
        
        # Add person
        p_id = f"Person_{r['p']['id']}"
        if p_id not in nodes:
            nodes[p_id] = GraphNode(
                id=p_id,
                label=r['p']['name'],
                type="Person",
                properties=r['p']
            )
        
        # Add edges
        edges.append(GraphEdge(
            id=f"{p_id}_member_of_{b1_id}",
            source=p_id,
            target=b1_id,
            type="MEMBER_OF",
            properties={}
        ))
        
        edges.append(GraphEdge(
            id=f"{p_id}_member_of_{b2_id}",
            source=p_id,
            target=b2_id,
            type="MEMBER_OF",
            properties={}
        ))
    
    return GraphResponse(nodes=list(nodes.values()), edges=edges)