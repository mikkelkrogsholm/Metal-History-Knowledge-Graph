"""
Enhanced Pydantic schemas for metal history entity extraction
Includes all entity types from the enhanced Kuzu schema
"""

from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import date

# Original Entity Models
class Band(BaseModel):
    name: str = Field(description="The band name")
    formed_year: Optional[int] = Field(None, description="Year the band was formed")
    origin_city: Optional[str] = Field(None, description="City where the band originated")
    origin_country: Optional[str] = Field(None, description="Country where the band originated")
    description: str = Field(description="Brief description of the band from the text")
    confidence: Optional[float] = Field(None, description="Confidence score for this extraction", ge=0.0, le=1.0)

class Person(BaseModel):
    name: str = Field(description="The person's name")
    instruments: List[str] = Field(default_factory=list, description="List of instruments played")
    associated_bands: List[str] = Field(default_factory=list, description="Bands associated with this person")
    description: str = Field(description="Brief description of the person")
    confidence: Optional[float] = Field(None, description="Confidence score for this extraction", ge=0.0, le=1.0)

class Album(BaseModel):
    title: str = Field(description="Album title")
    artist: str = Field(description="Band or artist name")
    release_year: Optional[int] = Field(None, description="Year of release")
    release_date: Optional[str] = Field(None, description="Full release date if known (YYYY-MM-DD)")
    label: Optional[str] = Field(None, description="Record label")
    studio: Optional[str] = Field(None, description="Recording studio")
    description: str = Field(description="Brief description or significance")
    confidence: Optional[float] = Field(None, description="Confidence score for this extraction", ge=0.0, le=1.0)

class Song(BaseModel):
    title: str = Field(description="Song title")
    artist: str = Field(description="Band or artist name")
    album: Optional[str] = Field(None, description="Album the song appears on")
    bpm: Optional[int] = Field(None, description="Beats per minute if mentioned")
    confidence: Optional[float] = Field(None, description="Confidence score for this extraction", ge=0.0, le=1.0)

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
    confidence: Optional[float] = Field(None, description="Confidence score for this extraction", ge=0.0, le=1.0)

class Location(BaseModel):
    city: Optional[str] = Field(None, description="City name")
    region: Optional[str] = Field(None, description="Region or state")
    country: str = Field(description="Country name")
    scene_description: str = Field(description="Description of the local scene")
    confidence: Optional[float] = Field(None, description="Confidence score for this extraction", ge=0.0, le=1.0)

class Event(BaseModel):
    name: str = Field(description="Event name or description")
    date: Optional[str] = Field(None, description="Date (YYYY-MM-DD or YYYY)")
    type: str = Field(description="Type of event: festival/controversy/movement/other")
    description: str = Field(description="Brief description of the event")
    confidence: Optional[float] = Field(None, description="Confidence score for this extraction", ge=0.0, le=1.0)

class Studio(BaseModel):
    name: str = Field(description="Studio name")
    location: Optional[str] = Field(None, description="Studio location")
    famous_for: str = Field(description="What the studio is known for")
    confidence: Optional[float] = Field(None, description="Confidence score for this extraction", ge=0.0, le=1.0)

class Label(BaseModel):
    name: str = Field(description="Record label name")
    founded_year: Optional[int] = Field(None, description="Year founded")
    confidence: Optional[float] = Field(None, description="Confidence score for this extraction", ge=0.0, le=1.0)

# Enhanced Equipment Model
class Equipment(BaseModel):
    name: str = Field(description="Equipment name/model")
    type: str = Field(description="Type: guitar/pedal/amp/recording/drums/bass/accessory")
    manufacturer: Optional[str] = Field(None, description="Brand name")
    specifications: Optional[str] = Field(None, description="Technical specifications")
    associated_bands: List[str] = Field(default_factory=list, description="Bands known for using this equipment")
    significance: Optional[str] = Field(None, description="Why it's important to metal history")
    techniques: Optional[str] = Field(None, description="Special ways it's used")
    confidence: Optional[float] = Field(None, description="Confidence score for this extraction", ge=0.0, le=1.0)

# New Entity Models

class Movement(BaseModel):
    name: str = Field(description="Movement name (NWOBHM, Bay Area thrash, etc.)")
    start_year: Optional[int] = Field(None, description="When the movement began")
    end_year: Optional[int] = Field(None, description="When it peaked or ended")
    geographic_center: List[str] = Field(default_factory=list, description="Primary location(s)")
    key_bands: List[str] = Field(default_factory=list, description="3-5 most important bands")
    key_venues: List[str] = Field(default_factory=list, description="Important clubs/shops")
    estimated_bands: Optional[int] = Field(None, description="Total number of bands")
    key_compilation: Optional[str] = Field(None, description="Important compilation album")
    characteristics: str = Field(description="Musical and cultural traits")
    influence: Optional[str] = Field(None, description="Impact on metal evolution")
    confidence: Optional[float] = Field(None, description="Confidence score for this extraction", ge=0.0, le=1.0)

class TechnicalDetail(BaseModel):
    type: str = Field(description="Category: string_gauge/scale_length/tuning/tempo/frequency")
    specification: str = Field(description="Exact technical value")
    context: str = Field(description="What it applies to (genre, band, song)")
    significance: Optional[str] = Field(None, description="Why this spec matters")
    comparison: Optional[str] = Field(None, description="How it differs from standard")
    confidence: Optional[float] = Field(None, description="Confidence score for this extraction", ge=0.0, le=1.0)

class Platform(BaseModel):
    name: str = Field(description="Platform name")
    type: str = Field(description="Category: social_media/streaming/recording/video/distribution")
    active_period: Optional[str] = Field(None, description="When it was relevant to metal")
    impact: Optional[str] = Field(None, description="How it changed metal culture/business")
    key_artists: List[str] = Field(default_factory=list, description="Artists who leveraged it")
    metrics: Optional[str] = Field(None, description="User numbers, view counts")
    innovations: Optional[str] = Field(None, description="New possibilities it enabled")
    confidence: Optional[float] = Field(None, description="Confidence score for this extraction", ge=0.0, le=1.0)

class AcademicResource(BaseModel):
    title: str = Field(description="Full title")
    author: Optional[str] = Field(None, description="Author(s) or creator(s)")
    year: Optional[int] = Field(None, description="Publication/release year")
    type: str = Field(description="book/journal/documentary/organization/conference")
    focus: Optional[str] = Field(None, description="Main topic covered")
    publisher: Optional[str] = Field(None, description="Publishing entity")
    significance: Optional[str] = Field(None, description="Contribution to metal scholarship")
    confidence: Optional[float] = Field(None, description="Confidence score for this extraction", ge=0.0, le=1.0)

class ViralPhenomenon(BaseModel):
    name: str = Field(description="Hashtag, video title, or description")
    platform: str = Field(description="Where it went viral")
    year: Optional[int] = Field(None, description="When it happened")
    view_count: Optional[int] = Field(None, description="Total views if mentioned")
    video_count: Optional[int] = Field(None, description="Number of videos for hashtags")
    participating_artists: List[str] = Field(default_factory=list, description="Bands/artists involved")
    impact: Optional[str] = Field(None, description="Effect on metal culture")
    duration: Optional[str] = Field(None, description="How long it remained relevant")
    confidence: Optional[float] = Field(None, description="Confidence score for this extraction", ge=0.0, le=1.0)

class Web3Project(BaseModel):
    name: str = Field(description="Project name")
    type: str = Field(description="NFT/virtual_band/blockchain_album/token/metaverse")
    launch_year: Optional[int] = Field(None, description="When it launched")
    band_or_creator: Optional[str] = Field(None, description="Who created it")
    unique_items: Optional[int] = Field(None, description="Number of NFTs/tokens")
    platform: Optional[str] = Field(None, description="Blockchain or metaverse platform")
    innovation: Optional[str] = Field(None, description="What makes it notable")
    confidence: Optional[float] = Field(None, description="Confidence score for this extraction", ge=0.0, le=1.0)

class ProductionStyle(BaseModel):
    name: str = Field(description="Common name or description")
    producer: Optional[str] = Field(None, description="Key producer(s)")
    studio: Optional[str] = Field(None, description="Primary studio")
    key_techniques: List[str] = Field(default_factory=list, description="Technical approaches")
    key_albums: List[str] = Field(default_factory=list, description="2-3 defining albums")
    equipment_used: List[str] = Field(default_factory=list, description="Specific gear")
    frequency_characteristics: Optional[str] = Field(None, description="EQ/mixing traits")
    influence_on: List[str] = Field(default_factory=list, description="Later styles influenced")
    confidence: Optional[float] = Field(None, description="Confidence score for this extraction", ge=0.0, le=1.0)

class Compilation(BaseModel):
    title: str = Field(description="Compilation title")
    release_year: Optional[int] = Field(None, description="Release year")
    label: Optional[str] = Field(None, description="Record label")
    featured_bands: List[str] = Field(default_factory=list, description="Bands included")
    significance: str = Field(description="Historical importance")
    associated_movement: Optional[str] = Field(None, description="Scene/movement represented")
    compiler: Optional[str] = Field(None, description="Who curated it")
    confidence: Optional[float] = Field(None, description="Confidence score for this extraction", ge=0.0, le=1.0)

class Venue(BaseModel):
    name: str = Field(description="Venue name")
    type: str = Field(description="record_shop/club/festival_ground/studio/rehearsal_space")
    location: Optional[str] = Field(None, description="City and address")
    active_years: Optional[str] = Field(None, description="When operational")
    significance: str = Field(description="Importance to metal history")
    associated_bands: List[str] = Field(default_factory=list, description="Bands that played/recorded")
    associated_movements: List[str] = Field(default_factory=list, description="Scenes centered around it")
    notable_events: List[str] = Field(default_factory=list, description="Important shows/incidents")
    confidence: Optional[float] = Field(None, description="Confidence score for this extraction", ge=0.0, le=1.0)

# Enhanced Relationship Model
class Relationship(BaseModel):
    type: str = Field(description="Relationship type")
    from_entity_type: str = Field(description="Type of source entity")
    from_entity_name: str = Field(description="Name of source entity")
    to_entity_type: str = Field(description="Type of target entity")
    to_entity_name: str = Field(description="Name of target entity")
    year: Optional[int] = Field(None, description="Year if applicable")
    role: Optional[str] = Field(None, description="Role in relationship")
    context: str = Field(description="Brief context from the text")
    properties: Optional[dict] = Field(None, description="Additional relationship properties")
    confidence: Optional[float] = Field(None, description="Confidence score", ge=0.0, le=1.0)

# Enhanced extraction result with all entity types
class EnhancedExtractionResult(BaseModel):
    # Original entities
    bands: List[Band] = Field(default_factory=list)
    people: List[Person] = Field(default_factory=list)
    albums: List[Album] = Field(default_factory=list)
    songs: List[Song] = Field(default_factory=list)
    subgenres: List[Subgenre] = Field(default_factory=list)
    locations: List[Location] = Field(default_factory=list)
    events: List[Event] = Field(default_factory=list)
    studios: List[Studio] = Field(default_factory=list)
    labels: List[Label] = Field(default_factory=list)
    equipment: List[Equipment] = Field(default_factory=list)
    
    # New entities
    movements: List[Movement] = Field(default_factory=list)
    technical_details: List[TechnicalDetail] = Field(default_factory=list)
    platforms: List[Platform] = Field(default_factory=list)
    academic_resources: List[AcademicResource] = Field(default_factory=list)
    viral_phenomena: List[ViralPhenomenon] = Field(default_factory=list)
    web3_projects: List[Web3Project] = Field(default_factory=list)
    production_styles: List[ProductionStyle] = Field(default_factory=list)
    compilations: List[Compilation] = Field(default_factory=list)
    venues: List[Venue] = Field(default_factory=list)
    
    # Relationships
    relationships: List[Relationship] = Field(default_factory=list)
    
    # Metadata
    extraction_metadata: Optional[dict] = Field(None, description="Metadata about the extraction process")