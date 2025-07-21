"""
Tests for Pydantic extraction schemas
"""

import pytest
from datetime import date
from extraction.extraction_schemas import (
    Band, Person, Album, Song, Subgenre, Location, 
    Event, Equipment, Studio, Label, Relationship, ExtractionResult
)

class TestEntitySchemas:
    
    def test_band_schema(self):
        """Test Band schema validation"""
        band = Band(
            name="Black Sabbath",
            formed_year=1968,
            origin_city="Birmingham",
            origin_country="UK",
            description="Pioneers of heavy metal"
        )
        
        assert band.name == "Black Sabbath"
        assert band.formed_year == 1968
        
        # Test with minimal data
        minimal_band = Band(name="Metallica", description="Thrash metal band")
        assert minimal_band.formed_year is None
        assert minimal_band.origin_city is None
    
    def test_person_schema(self):
        """Test Person schema validation"""
        person = Person(
            name="Tony Iommi",
            instruments=["guitar", "keyboards"],
            associated_bands=["Black Sabbath", "Heaven & Hell"],
            description="Lost fingertips in factory accident"
        )
        
        assert len(person.instruments) == 2
        assert "Black Sabbath" in person.associated_bands
        
        # Test default empty lists
        minimal_person = Person(name="Ozzy", description="Singer")
        assert minimal_person.instruments == []
        assert minimal_person.associated_bands == []
    
    def test_album_schema(self):
        """Test Album schema validation"""
        album = Album(
            title="Paranoid",
            artist="Black Sabbath",
            release_year=1970,
            release_date="1970-09-18",
            label="Vertigo",
            studio="Regent Sound Studios",
            description="Classic album"
        )
        
        assert album.title == "Paranoid"
        assert album.release_year == 1970
        assert album.release_date == "1970-09-18"
    
    def test_subgenre_schema(self):
        """Test Subgenre schema validation"""
        subgenre = Subgenre(
            name="Thrash Metal",
            era_start=1983,
            era_end=1991,
            bpm_min=180,
            bpm_max=250,
            guitar_tuning="E standard",
            vocal_style="Aggressive shouts",
            key_characteristics="Fast palm-muted riffs",
            parent_influences=["NWOBHM", "Hardcore Punk"]
        )
        
        assert subgenre.bpm_min == 180
        assert len(subgenre.parent_influences) == 2
    
    def test_relationship_schema(self):
        """Test Relationship schema validation"""
        rel = Relationship(
            type="MEMBER_OF",
            from_entity_type="person",
            from_entity_name="Tony Iommi",
            to_entity_type="band",
            to_entity_name="Black Sabbath",
            year=1968,
            role="Guitarist",
            context="Founding member"
        )
        
        assert rel.type == "MEMBER_OF"
        assert rel.year == 1968
        assert rel.role == "Guitarist"
    
    def test_extraction_result_schema(self):
        """Test ExtractionResult container schema"""
        result = ExtractionResult(
            bands=[Band(name="Sabbath", description="Band")],
            people=[Person(name="Ozzy", description="Singer")],
            albums=[],
            songs=[],
            subgenres=[],
            locations=[],
            events=[],
            equipment=[],
            studios=[],
            labels=[],
            relationships=[]
        )
        
        assert len(result.bands) == 1
        assert len(result.people) == 1
        assert len(result.albums) == 0
        
        # Test JSON serialization
        json_data = result.model_dump()
        assert "bands" in json_data
        assert json_data["bands"][0]["name"] == "Sabbath"
    
    def test_location_schema(self):
        """Test Location schema validation"""
        location = Location(
            city="Birmingham",
            region="West Midlands",
            country="UK",
            scene_description="Birthplace of heavy metal"
        )
        
        assert location.city == "Birmingham"
        assert location.country == "UK"
        
        # Test with minimal data
        minimal = Location(country="Norway", scene_description="Black metal scene")
        assert minimal.city is None
        assert minimal.region is None
    
    def test_equipment_schema(self):
        """Test Equipment schema validation"""
        equipment = Equipment(
            name="Boss HM-2",
            type="pedal",
            specifications="Swedish death metal buzzsaw sound"
        )
        
        assert equipment.type == "pedal"
        assert "Swedish" in equipment.specifications
    
    def test_schema_json_compatibility(self):
        """Test that schemas work with Ollama's format parameter"""
        # Get JSON schema
        schema = ExtractionResult.model_json_schema()
        
        assert "properties" in schema
        assert "bands" in schema["properties"]
        assert "people" in schema["properties"]
        assert "relationships" in schema["properties"]
        
        # Check nested schema
        bands_schema = schema["properties"]["bands"]
        assert bands_schema["type"] == "array"