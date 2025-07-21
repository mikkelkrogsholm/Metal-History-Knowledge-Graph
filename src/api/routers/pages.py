"""
Page routes for server-rendered content
"""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path

# Configure templates
template_dir = Path(__file__).parent.parent / "templates"
templates = Jinja2Templates(directory=str(template_dir))

router = APIRouter()

@router.get("/about", response_class=HTMLResponse)
async def about_page(request: Request):
    """About page"""
    return templates.TemplateResponse(
        "pages/content.html",
        {
            "request": request,
            "page_title": "About Metal History Knowledge Graph",
            "subtitle": "Exploring the connections in metal music history",
            "breadcrumbs": [
                {"name": "Home", "url": "/"},
                {"name": "About", "url": "/about"}
            ],
            "content": """
                <h2>Our Mission</h2>
                <p>
                    The Metal History Knowledge Graph is dedicated to preserving and exploring 
                    the rich history of metal music through data visualization and analysis.
                </p>
                
                <h2>What We Offer</h2>
                <ul>
                    <li>Comprehensive database of metal bands and albums</li>
                    <li>Interactive graph visualization of musical connections</li>
                    <li>Search and discovery tools for metal enthusiasts</li>
                    <li>API access for developers and researchers</li>
                </ul>
                
                <h2>Data Sources</h2>
                <p>
                    Our knowledge graph is built from carefully curated historical documents 
                    about metal music, processed using advanced natural language processing 
                    techniques to extract entities and relationships.
                </p>
            """,
            "actions": [
                {"text": "Explore Bands", "url": "/bands", "primary": True},
                {"text": "View API Docs", "url": "/docs", "primary": False}
            ],
            "related_links": [
                {"text": "Browse all bands", "url": "/bands"},
                {"text": "Search the database", "url": "/search"},
                {"text": "API documentation", "url": "/docs"}
            ]
        }
    )

@router.get("/api", response_class=HTMLResponse)
async def api_info_page(request: Request):
    """API information page"""
    return templates.TemplateResponse(
        "pages/content.html",
        {
            "request": request,
            "page_title": "API Documentation",
            "subtitle": "Access the Metal History Knowledge Graph programmatically",
            "breadcrumbs": [
                {"name": "Home", "url": "/"},
                {"name": "API", "url": "/api"}
            ],
            "content": """
                <h2>RESTful API</h2>
                <p>
                    Our API provides programmatic access to the Metal History Knowledge Graph,
                    allowing developers to build applications and conduct research.
                </p>
                
                <h2>Available Endpoints</h2>
                <h3>Bands</h3>
                <ul>
                    <li><code>GET /api/v1/bands</code> - List all bands</li>
                    <li><code>GET /api/v1/bands/{band_id}</code> - Get band details</li>
                    <li><code>GET /api/v1/bands/{band_id}/albums</code> - Get band's albums</li>
                    <li><code>GET /api/v1/bands/{band_id}/members</code> - Get band members</li>
                </ul>
                
                <h3>Albums</h3>
                <ul>
                    <li><code>GET /api/v1/albums</code> - List all albums</li>
                    <li><code>GET /api/v1/albums/{album_id}</code> - Get album details</li>
                </ul>
                
                <h3>Search</h3>
                <ul>
                    <li><code>GET /api/v1/search?q={query}</code> - Search across all entities</li>
                </ul>
                
                <h3>Graph</h3>
                <ul>
                    <li><code>GET /api/v1/graph/connections/{entity_id}</code> - Get entity connections</li>
                    <li><code>GET /api/v1/graph/subgraph/{entity_id}</code> - Get entity subgraph</li>
                </ul>
                
                <h2>Authentication</h2>
                <p>
                    The API is currently open and does not require authentication.
                    Rate limiting may apply to prevent abuse.
                </p>
            """,
            "actions": [
                {"text": "View Interactive Docs", "url": "/docs", "primary": True},
                {"text": "View ReDoc", "url": "/redoc", "primary": False}
            ]
        }
    )