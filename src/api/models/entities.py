"""
Pydantic models for API entities
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

class BandBase(BaseModel):
    """Base band model"""
    name: str
    formed_year: Optional[int] = None
    origin_city: Optional[str] = None
    origin_country: Optional[str] = None
    status: Optional[str] = None
    description: Optional[str] = None

class BandResponse(BandBase):
    """Band response model"""
    id: int
    
    class Config:
        from_attributes = True

class AlbumBase(BaseModel):
    """Base album model"""
    title: str
    release_year: Optional[int] = None
    release_date: Optional[str] = None
    label: Optional[str] = None
    studio: Optional[str] = None
    description: Optional[str] = None

class AlbumResponse(AlbumBase):
    """Album response model"""
    id: int
    band_name: Optional[str] = None
    
    class Config:
        from_attributes = True

class PersonBase(BaseModel):
    """Base person model"""
    name: str
    birth_date: Optional[str] = None
    birth_place: Optional[str] = None
    instruments: List[str] = Field(default_factory=list)

class PersonResponse(PersonBase):
    """Person response model"""
    id: int
    bands: List[str] = Field(default_factory=list)
    
    class Config:
        from_attributes = True

class SubgenreBase(BaseModel):
    """Base subgenre model"""
    name: str
    era_start: Optional[int] = None
    era_end: Optional[int] = None
    key_characteristics: Optional[str] = None

class SubgenreResponse(SubgenreBase):
    """Subgenre response model"""
    id: int
    parent_genres: List[str] = Field(default_factory=list)
    
    class Config:
        from_attributes = True

class SearchResult(BaseModel):
    """Search result model"""
    entity_type: str
    id: int
    name: str
    score: Optional[float] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

class GraphNode(BaseModel):
    """Graph node for visualization"""
    id: str
    label: str
    type: str
    properties: Dict[str, Any] = Field(default_factory=dict)

class GraphEdge(BaseModel):
    """Graph edge for visualization"""
    id: str
    source: str
    target: str
    type: str
    properties: Dict[str, Any] = Field(default_factory=dict)

class GraphResponse(BaseModel):
    """Graph query response"""
    nodes: List[GraphNode]
    edges: List[GraphEdge]
    
class PaginationParams(BaseModel):
    """Pagination parameters"""
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    
class PaginatedResponse(BaseModel):
    """Paginated response wrapper"""
    items: List[Any]
    total: int
    page: int
    page_size: int
    total_pages: int