"""
Pydantic schemas for metal history entity extraction
"""

from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import date

# Entity Models
class Band(BaseModel):
    name: str = Field(description="The band name")
    formed_year: Optional[int] = Field(None, description="Year the band was formed")
    origin_city: Optional[str] = Field(None, description="City where the band originated")
    origin_country: Optional[str] = Field(None, description="Country where the band originated")
    description: str = Field(description="Brief description of the band from the text")

class Person(BaseModel):
    name: str = Field(description="The person's name")
    instruments: List[str] = Field(default_factory=list, description="List of instruments played")
    associated_bands: List[str] = Field(default_factory=list, description="Bands associated with this person")
    description: str = Field(description="Brief description of the person")

class Album(BaseModel):
    title: str = Field(description="Album title")
    artist: str = Field(description="Band or artist name")
    release_year: Optional[int] = Field(None, description="Year of release")
    release_date: Optional[str] = Field(None, description="Full release date if known (YYYY-MM-DD)")
    label: Optional[str] = Field(None, description="Record label")
    studio: Optional[str] = Field(None, description="Recording studio")
    description: str = Field(description="Brief description or significance")

class Song(BaseModel):
    title: str = Field(description="Song title")
    artist: str = Field(description="Band or artist name")
    album: Optional[str] = Field(None, description="Album the song appears on")
    bpm: Optional[int] = Field(None, description="Beats per minute if mentioned")

class Subgenre(BaseModel):
    name: str = Field(description="Subgenre name")
    era_start: Optional[int] = Field(None, description="Start year of the era")
    era_end: Optional[int] = Field(None, description="End year of the era")
    bpm_min: Optional[int] = Field(None, description="Minimum BPM range")
    bpm_max: Optional[int] = Field(None, description="Maximum BPM range")
    guitar_tuning: Optional[str] = Field(None, description="Common guitar tuning")
    vocal_style: Optional[str] = Field(None, description="Characteristic vocal style")
    key_characteristics: str = Field(description="Key musical characteristics")
    parent_influences: List[str] = Field(default_factory=list, description="Parent genres that influenced this subgenre")

class Location(BaseModel):
    city: Optional[str] = Field(None, description="City name")
    region: Optional[str] = Field(None, description="Region or state")
    country: str = Field(description="Country name")
    scene_description: str = Field(description="Description of the local scene")

class Event(BaseModel):
    name: str = Field(description="Event name or description")
    date: Optional[str] = Field(None, description="Date (YYYY-MM-DD or YYYY)")
    type: str = Field(description="Type of event: festival/controversy/movement/other")
    description: str = Field(description="Brief description of the event")

class Equipment(BaseModel):
    name: str = Field(description="Equipment name")
    type: str = Field(description="Type: guitar/pedal/amp/other")
    specifications: Optional[str] = Field(None, description="Technical specifications")

class Studio(BaseModel):
    name: str = Field(description="Studio name")
    location: Optional[str] = Field(None, description="Studio location")
    famous_for: str = Field(description="What the studio is known for")

class Label(BaseModel):
    name: str = Field(description="Record label name")
    founded_year: Optional[int] = Field(None, description="Year founded")

# Relationship Model
class Relationship(BaseModel):
    type: str = Field(description="Relationship type: MEMBER_OF/FORMED_IN/RELEASED/PLAYS_GENRE/etc")
    from_entity_type: str = Field(description="Type of source entity: band/person/album/etc")
    from_entity_name: str = Field(description="Name of source entity")
    to_entity_type: str = Field(description="Type of target entity: band/location/genre/etc")
    to_entity_name: str = Field(description="Name of target entity")
    year: Optional[int] = Field(None, description="Year if applicable")
    role: Optional[str] = Field(None, description="Role in relationship if applicable")
    context: str = Field(description="Brief context from the text")

# Main extraction result
class ExtractionResult(BaseModel):
    bands: List[Band] = Field(default_factory=list, description="Bands mentioned in the text")
    people: List[Person] = Field(default_factory=list, description="People mentioned in the text")
    albums: List[Album] = Field(default_factory=list, description="Albums mentioned in the text")
    songs: List[Song] = Field(default_factory=list, description="Songs mentioned in the text")
    subgenres: List[Subgenre] = Field(default_factory=list, description="Subgenres mentioned in the text")
    locations: List[Location] = Field(default_factory=list, description="Locations mentioned in the text")
    events: List[Event] = Field(default_factory=list, description="Events mentioned in the text")
    equipment: List[Equipment] = Field(default_factory=list, description="Equipment mentioned in the text")
    studios: List[Studio] = Field(default_factory=list, description="Studios mentioned in the text")
    labels: List[Label] = Field(default_factory=list, description="Record labels mentioned in the text")
    relationships: List[Relationship] = Field(default_factory=list, description="Relationships between entities")