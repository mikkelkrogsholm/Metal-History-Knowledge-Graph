"""
API Dependencies
"""

from src.api.services.database import DatabaseService

# Global database service instance
db_service: DatabaseService = None

def get_db() -> DatabaseService:
    """Get database service dependency"""
    if not db_service:
        from fastapi import HTTPException
        raise HTTPException(status_code=503, detail="Database service not available")
    return db_service