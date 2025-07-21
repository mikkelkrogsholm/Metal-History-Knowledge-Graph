"""
Configuration settings for the API
"""

from pydantic_settings import BaseSettings
from typing import List
from pathlib import Path

class Settings(BaseSettings):
    """API configuration settings"""
    
    # Database
    DATABASE_PATH: str = "data/database/metal_history.db"
    
    # API
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Metal History Knowledge Graph"
    
    # CORS
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:8000",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:8000",
    ]
    
    # Cache
    CACHE_DIR: str = "data/cache"
    CACHE_TTL: int = 3600  # 1 hour
    
    # Search
    SEARCH_LIMIT: int = 100
    MIN_SIMILARITY_SCORE: float = 0.7
    
    # Pagination
    DEFAULT_PAGE_SIZE: int = 20
    MAX_PAGE_SIZE: int = 100
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()