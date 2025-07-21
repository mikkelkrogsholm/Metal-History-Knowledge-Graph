"""
FastAPI application for Metal History Knowledge Graph
"""

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from contextlib import asynccontextmanager
import kuzu
from pathlib import Path
import sys
import uuid

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.append(str(PROJECT_ROOT))

from src.api.routers import bands, albums, search, graph, pages, web_bands, web_albums
from src.api.services.database import DatabaseService
from src.api.config import settings
from src.api import deps

# Configure templates
template_dir = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(template_dir))

# Enable auto-reload in development
if settings.ENVIRONMENT == "development":
    templates.env.auto_reload = True

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle"""
    # Startup
    deps.db_service = DatabaseService(settings.DATABASE_PATH)
    yield
    # Shutdown
    if deps.db_service:
        deps.db_service.close()

# Create FastAPI app
app = FastAPI(
    title="Metal History Knowledge Graph API",
    description="API for exploring metal music history through a knowledge graph",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory=str(Path(__file__).parent / "static")), name="static")

# Include API routers
app.include_router(bands.router, prefix="/api/v1/bands", tags=["bands"])
app.include_router(albums.router, prefix="/api/v1/albums", tags=["albums"])
app.include_router(search.router, prefix="/api/v1/search", tags=["search"])
app.include_router(graph.router, prefix="/api/v1/graph", tags=["graph"])

# Include page routers (no prefix for web pages)
app.include_router(pages.router, tags=["pages"])
app.include_router(web_bands.router, tags=["web"])
app.include_router(web_albums.router, tags=["web"])

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Root endpoint - render home page"""
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "title": "Metal History Knowledge Graph"}
    )

@app.get("/api")
async def api_root():
    """API root endpoint"""
    return {
        "message": "Welcome to Metal History Knowledge Graph API",
        "docs": "/docs",
        "redoc": "/redoc"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Test database connection
        if deps.db_service and deps.db_service.is_connected():
            return {"status": "healthy", "database": "connected"}
        else:
            raise HTTPException(status_code=503, detail="Database not connected")
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))

# Error handlers
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Handle HTTP exceptions with custom error pages"""
    if exc.status_code == 404:
        return templates.TemplateResponse(
            "errors/404.html",
            {"request": request},
            status_code=404
        )
    elif exc.status_code == 500:
        return templates.TemplateResponse(
            "errors/500.html",
            {
                "request": request,
                "detail": str(exc.detail) if settings.ENVIRONMENT == "development" else None,
                "request_id": str(uuid.uuid4())
            },
            status_code=500
        )
    # For other status codes, return JSON response
    return {"detail": exc.detail, "status_code": exc.status_code}

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors"""
    return templates.TemplateResponse(
        "errors/500.html",
        {
            "request": request,
            "detail": "Invalid request data" if settings.ENVIRONMENT != "development" else str(exc),
            "request_id": str(uuid.uuid4())
        },
        status_code=422
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle all other exceptions"""
    return templates.TemplateResponse(
        "errors/500.html",
        {
            "request": request,
            "detail": "An unexpected error occurred" if settings.ENVIRONMENT != "development" else str(exc),
            "request_id": str(uuid.uuid4())
        },
        status_code=500
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)