"""
FastAPI application for Metal History Knowledge Graph
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import kuzu
from pathlib import Path
import sys

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.append(str(PROJECT_ROOT))

from src.api.routers import bands, albums, search, graph
from src.api.services.database import DatabaseService
from src.api.config import settings

# Global database connection
db_service = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle"""
    global db_service
    # Startup
    db_service = DatabaseService(settings.DATABASE_PATH)
    yield
    # Shutdown
    if db_service:
        db_service.close()

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

# Include routers
app.include_router(bands.router, prefix="/api/v1/bands", tags=["bands"])
app.include_router(albums.router, prefix="/api/v1/albums", tags=["albums"])
app.include_router(search.router, prefix="/api/v1/search", tags=["search"])
app.include_router(graph.router, prefix="/api/v1/graph", tags=["graph"])

@app.get("/")
async def root():
    """Root endpoint"""
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
        if db_service and db_service.is_connected():
            return {"status": "healthy", "database": "connected"}
        else:
            raise HTTPException(status_code=503, detail="Database not connected")
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)