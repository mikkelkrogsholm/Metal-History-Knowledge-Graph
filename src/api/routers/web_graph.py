"""
Web routes for graph visualization (server-side rendered)
"""

from fastapi import APIRouter, Request, Query, Depends, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from typing import Optional, List, Dict, Any, Union
from pathlib import Path
import math
import json

from src.api.deps import get_db
from src.api.services.database import DatabaseService

# Configure templates
template_dir = Path(__file__).parent.parent / "templates"
templates = Jinja2Templates(directory=str(template_dir))

router = APIRouter()

def optional_int(value: Union[str, int, None]) -> Optional[int]:
    """Convert empty string to None for optional int parameters"""
    if value == "" or value is None:
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None

@router.get("/graph", response_class=HTMLResponse)
async def graph_view(
    request: Request,
    view: str = Query("influences", description="Graph view type"),
    genre: Optional[str] = Query(None, description="Filter by genre"),
    year_from: Optional[str] = Query(None, description="Filter by year from"),
    year_to: Optional[str] = Query(None, description="Filter by year to"),
    limit: int = Query(50, ge=10, le=200, description="Limit nodes"),
    db: DatabaseService = Depends(get_db)
):
    """Render graph visualization page"""
    
    # Convert year parameters
    year_from_int = optional_int(year_from)
    year_to_int = optional_int(year_to)
    
    # Get graph data based on view type
    if view == "influences":
        graph_data = await get_influence_graph(db, genre, year_from_int, year_to_int, limit)
    elif view == "collaborations":
        graph_data = await get_collaboration_graph(db, genre, year_from_int, year_to_int, limit)
    elif view == "timeline":
        graph_data = await get_timeline_graph(db, genre, year_from_int, year_to_int, limit)
    elif view == "geographic":
        graph_data = await get_geographic_graph(db, genre, year_from_int, year_to_int, limit)
    else:
        graph_data = await get_influence_graph(db, genre, year_from_int, year_to_int, limit)
    
    # Calculate layout for server-side rendering
    layout = calculate_force_layout(graph_data["nodes"], graph_data["edges"])
    
    # Prepare data for template
    return templates.TemplateResponse(
        "graph/index.html",
        {
            "request": request,
            "view": view,
            "genre": genre,
            "year_from": year_from_int,
            "year_to": year_to_int,
            "limit": limit,
            "nodes": layout["nodes"],
            "edges": layout["edges"],
            "stats": graph_data["stats"],
            "graph_json": json.dumps(layout),
            "available_views": [
                {"value": "influences", "label": "Band Influences"},
                {"value": "collaborations", "label": "Collaborations"},
                {"value": "timeline", "label": "Timeline"},
                {"value": "geographic", "label": "Geographic"}
            ]
        }
    )

@router.get("/graph/data", response_class=HTMLResponse)
async def graph_data_endpoint(
    request: Request,
    view: str = Query("influences"),
    genre: Optional[str] = Query(None),
    year_from: Optional[str] = Query(None),
    year_to: Optional[str] = Query(None),
    limit: int = Query(50, ge=10, le=200),
    db: DatabaseService = Depends(get_db)
):
    """Return graph data for HTMX updates"""
    
    # Convert year parameters
    year_from_int = optional_int(year_from)
    year_to_int = optional_int(year_to)
    
    # Get graph data
    if view == "influences":
        graph_data = await get_influence_graph(db, genre, year_from, year_to, limit)
    elif view == "collaborations":
        graph_data = await get_collaboration_graph(db, genre, year_from_int, year_to_int, limit)
    elif view == "timeline":
        graph_data = await get_timeline_graph(db, genre, year_from_int, year_to_int, limit)
    elif view == "geographic":
        graph_data = await get_geographic_graph(db, genre, year_from_int, year_to_int, limit)
    else:
        graph_data = await get_influence_graph(db, genre, year_from_int, year_to_int, limit)
    
    # Calculate layout
    layout = calculate_force_layout(graph_data["nodes"], graph_data["edges"])
    
    # Return partial template
    return templates.TemplateResponse(
        "graph/visualization.html",
        {
            "request": request,
            "nodes": layout["nodes"],
            "edges": layout["edges"],
            "stats": graph_data["stats"],
            "graph_json": json.dumps(layout)
        }
    )

async def get_influence_graph(
    db: DatabaseService,
    genre: Optional[str],
    year_from: Optional[int],
    year_to: Optional[int],
    limit: int
) -> Dict[str, Any]:
    """Get band influence network"""
    
    # Build filters
    where_clauses = []
    if year_from:
        where_clauses.append(f"b.formed_year >= {year_from}")
    if year_to:
        where_clauses.append(f"b.formed_year <= {year_to}")
    
    where_clause = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
    
    # Get bands with connections (contemporary, mentioned together)
    nodes_query = f"""
        MATCH (b:BAND)
        {where_clause}
        OPTIONAL MATCH (b)-[r:MENTIONED_WITH|CONTEMPORARY_OF]-(other:BAND)
        WITH b, count(DISTINCT other) as connections
        WHERE connections > 0
        RETURN b.id as id,
               b.name as name,
               b.formed_year as year,
               b.origin_country as country,
               connections
        ORDER BY connections DESC
        LIMIT {limit}
    """
    
    nodes_result = db.execute_query(nodes_query)
    nodes = []
    node_ids = set()
    
    for row in nodes_result:
        nodes.append({
            "id": str(row["id"]),
            "name": row["name"],
            "year": row["year"],
            "country": row["country"],
            "connections": row["connections"],
            "type": "band"
        })
        node_ids.add(row["id"])
    
    # Get edges between these nodes
    edges = []
    if node_ids:
        edges_query = """
            MATCH (b1:BAND)-[r:MENTIONED_WITH|CONTEMPORARY_OF]-(b2:BAND)
            WHERE b1.id IN $node_ids AND b2.id IN $node_ids
            AND b1.id < b2.id
            RETURN b1.id as source,
                   b2.id as target,
                   type(r) as type
        """
        
        edges_result = db.execute_query(edges_query, {"node_ids": list(node_ids)})
        
        for row in edges_result:
            edges.append({
                "source": str(row["source"]),
                "target": str(row["target"]),
                "type": row["type"]
            })
    
    return {
        "nodes": nodes,
        "edges": edges,
        "stats": {
            "node_count": len(nodes),
            "edge_count": len(edges),
            "density": len(edges) / (len(nodes) * (len(nodes) - 1)) if len(nodes) > 1 else 0
        }
    }

async def get_collaboration_graph(
    db: DatabaseService,
    genre: Optional[str],
    year_from: Optional[int],
    year_to: Optional[int],
    limit: int
) -> Dict[str, Any]:
    """Get collaboration network between bands and people"""
    
    # Get bands with most collaborations
    nodes_query = f"""
        MATCH (b:BAND)<-[:MEMBER_OF]-(p:PERSON)
        OPTIONAL MATCH (p)-[:MEMBER_OF]->(other:BAND)
        WHERE other.id <> b.id
        WITH b, count(DISTINCT p) as members, count(DISTINCT other) as collaborations
        WHERE collaborations > 0
        RETURN b.id as id,
               b.name as name,
               b.formed_year as year,
               members,
               collaborations
        ORDER BY collaborations DESC
        LIMIT {limit // 2}
    """
    
    nodes_result = db.execute_query(nodes_query)
    nodes = []
    band_ids = set()
    
    for row in nodes_result:
        nodes.append({
            "id": f"band_{row['id']}",
            "name": row["name"],
            "year": row["year"],
            "members": row["members"],
            "collaborations": row["collaborations"],
            "type": "band"
        })
        band_ids.add(row["id"])
    
    # Get people who connect these bands
    if band_ids:
        people_query = """
            MATCH (p:PERSON)-[:MEMBER_OF]->(b:BAND)
            WHERE b.id IN $band_ids
            WITH p, collect(DISTINCT b.id) as bands
            WHERE size(bands) > 1
            RETURN p.id as id,
                   p.name as name,
                   bands
            LIMIT $limit
        """
        
        people_result = db.execute_query(people_query, {"band_ids": list(band_ids), "limit": limit // 2})
        
        edges = []
        for row in people_result:
            person_id = f"person_{row['id']}"
            nodes.append({
                "id": person_id,
                "name": row["name"],
                "type": "person",
                "bands": len(row["bands"])
            })
            
            # Create edges from person to each band
            for band_id in row["bands"]:
                edges.append({
                    "source": person_id,
                    "target": f"band_{band_id}",
                    "type": "member_of"
                })
    
    return {
        "nodes": nodes,
        "edges": edges if 'edges' in locals() else [],
        "stats": {
            "node_count": len(nodes),
            "edge_count": len(edges) if 'edges' in locals() else 0,
            "band_count": len([n for n in nodes if n["type"] == "band"]),
            "person_count": len([n for n in nodes if n["type"] == "person"])
        }
    }

async def get_timeline_graph(
    db: DatabaseService,
    genre: Optional[str],
    year_from: Optional[int],
    year_to: Optional[int],
    limit: int
) -> Dict[str, Any]:
    """Get timeline-based graph of band formations and influences"""
    
    # Get bands ordered by formation year
    year_from = year_from or 1960
    year_to = year_to or 2024
    
    nodes_query = f"""
        MATCH (b:BAND)
        WHERE b.formed_year >= {year_from} AND b.formed_year <= {year_to}
        RETURN b.id as id,
               b.name as name,
               b.formed_year as year,
               b.origin_country as country
        ORDER BY b.formed_year
        LIMIT {limit}
    """
    
    nodes_result = db.execute_query(nodes_query)
    nodes = []
    node_ids = set()
    
    for i, row in enumerate(nodes_result):
        nodes.append({
            "id": str(row["id"]),
            "name": row["name"],
            "year": row["year"],
            "country": row["country"],
            "x": (row["year"] - year_from) / (year_to - year_from) * 800 + 100,  # Timeline position
            "y": 300 + (i % 10) * 40,  # Stagger vertically
            "type": "band"
        })
        node_ids.add(row["id"])
    
    # Get connections between these bands
    edges = []
    if node_ids:
        edges_query = """
            MATCH (b1:BAND)-[r:MENTIONED_WITH]-(b2:BAND)
            WHERE b1.id IN $node_ids AND b2.id IN $node_ids
            AND b1.formed_year < b2.formed_year
            RETURN b1.id as source,
                   b2.id as target,
                   'connection' as type
        """
        
        edges_result = db.execute_query(edges_query, {"node_ids": list(node_ids)})
        
        for row in edges_result:
            edges.append({
                "source": str(row["source"]),
                "target": str(row["target"]),
                "type": row.get("type", "connection")
            })
    
    return {
        "nodes": nodes,
        "edges": edges,
        "stats": {
            "node_count": len(nodes),
            "edge_count": len(edges),
            "year_range": f"{year_from}-{year_to}",
            "avg_influences": len(edges) / len(nodes) if nodes else 0
        }
    }

async def get_geographic_graph(
    db: DatabaseService,
    genre: Optional[str],
    year_from: Optional[int],
    year_to: Optional[int],
    limit: int
) -> Dict[str, Any]:
    """Get geographic distribution of bands"""
    
    # Get bands grouped by country
    country_query = """
        MATCH (b:BAND)
        WHERE b.origin_country IS NOT NULL
        WITH b.origin_country as country, collect(b) as bands
        RETURN country,
               size(bands) as band_count,
               bands[0..10] as sample_bands
        ORDER BY band_count DESC
        LIMIT 20
    """
    
    country_result = db.execute_query(country_query)
    nodes = []
    edges = []
    
    # Create country nodes
    for i, row in enumerate(country_result):
        country_id = f"country_{row['country'].replace(' ', '_')}"
        nodes.append({
            "id": country_id,
            "name": row["country"],
            "band_count": row["band_count"],
            "type": "country",
            "x": 500 + 300 * math.cos(2 * math.pi * i / len(country_result)),
            "y": 400 + 300 * math.sin(2 * math.pi * i / len(country_result))
        })
        
        # Add sample bands
        for j, band in enumerate(row["sample_bands"]):
            if j >= limit // len(country_result):
                break
                
            band_id = f"band_{band['id']}"
            nodes.append({
                "id": band_id,
                "name": band["name"],
                "year": band.get("formed_year"),
                "type": "band",
                "x": nodes[-1]["x"] + 50 * math.cos(2 * math.pi * j / len(row["sample_bands"])),
                "y": nodes[-1]["y"] + 50 * math.sin(2 * math.pi * j / len(row["sample_bands"]))
            })
            
            edges.append({
                "source": band_id,
                "target": country_id,
                "type": "from_country"
            })
    
    return {
        "nodes": nodes,
        "edges": edges,
        "stats": {
            "node_count": len(nodes),
            "edge_count": len(edges),
            "country_count": len([n for n in nodes if n["type"] == "country"]),
            "band_count": len([n for n in nodes if n["type"] == "band"])
        }
    }

def calculate_force_layout(nodes: List[Dict], edges: List[Dict]) -> Dict[str, Any]:
    """Calculate positions for nodes using a simple force-directed layout"""
    
    # If nodes already have positions (timeline/geographic), use them
    if nodes and "x" in nodes[0]:
        return {"nodes": nodes, "edges": edges}
    
    # Simple circular layout as starting point
    node_count = len(nodes)
    for i, node in enumerate(nodes):
        angle = 2 * math.pi * i / node_count
        radius = min(300, max(150, node_count * 5))
        node["x"] = 500 + radius * math.cos(angle)
        node["y"] = 400 + radius * math.sin(angle)
        node["radius"] = min(20, max(5, node.get("connections", 1) * 2))
    
    # Simple force simulation (just a few iterations for server-side)
    for _ in range(10):
        # Repulsion between nodes
        for i, node1 in enumerate(nodes):
            fx, fy = 0, 0
            for j, node2 in enumerate(nodes):
                if i != j:
                    dx = node1["x"] - node2["x"]
                    dy = node1["y"] - node2["y"]
                    dist = math.sqrt(dx*dx + dy*dy)
                    if dist > 0:
                        force = 50 / (dist * dist)
                        fx += dx / dist * force
                        fy += dy / dist * force
            
            node1["x"] += fx * 0.1
            node1["y"] += fy * 0.1
            
            # Keep within bounds
            node1["x"] = max(50, min(950, node1["x"]))
            node1["y"] = max(50, min(750, node1["y"]))
    
    return {"nodes": nodes, "edges": edges}