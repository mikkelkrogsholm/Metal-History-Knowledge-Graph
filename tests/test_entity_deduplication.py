"""
Tests for entity deduplication functionality
"""

import pytest
from pipeline.extraction_pipeline import FuzzyMatcher, EntityDeduplicator, EntityCandidate

class TestEntityDeduplication:
    
    @pytest.fixture
    def deduplicator(self):
        """Create a deduplicator instance"""
        matcher = FuzzyMatcher(similarity_threshold=0.85)
        return EntityDeduplicator(matcher)
    
    def test_add_new_entity(self, deduplicator):
        """Test adding a new entity"""
        entity_data = {"name": "Black Sabbath", "formed_year": 1968}
        deduplicator.add_entity("bands", entity_data, "chunk_001")
        
        assert len(deduplicator.entity_groups["bands"]) == 1
        group = deduplicator.entity_groups["bands"][0]
        assert group.name == "Black Sabbath"
        assert "chunk_001" in group.source_chunks
    
    def test_merge_similar_entities(self, deduplicator):
        """Test merging similar entities"""
        # Add first entity
        deduplicator.add_entity("bands", {"name": "Black Sabbath", "formed_year": 1968}, "chunk_001")
        
        # Add similar entity with typo
        deduplicator.add_entity("bands", {"name": "Black Sabath", "origin_city": "Birmingham"}, "chunk_002")
        
        # Should have merged into one group
        assert len(deduplicator.entity_groups["bands"]) == 1
        group = deduplicator.entity_groups["bands"][0]
        
        # Check variations tracked
        assert "Black Sabbath" in group.variations
        assert "Black Sabath" in group.variations
        
        # Check data merged
        assert group.original_data["formed_year"] == 1968
        assert group.original_data["origin_city"] == "Birmingham"
        
        # Check sources tracked
        assert len(group.source_chunks) == 2
    
    def test_data_merging_lists(self, deduplicator):
        """Test merging list data"""
        # Add person with instruments
        deduplicator.add_entity("people", {
            "name": "Tony Iommi",
            "instruments": ["guitar"]
        }, "chunk_001")
        
        # Add same person with more instruments
        deduplicator.add_entity("people", {
            "name": "Tony Iomi",  # Typo
            "instruments": ["guitar", "keyboards"]
        }, "chunk_002")
        
        group = deduplicator.entity_groups["people"][0]
        assert set(group.original_data["instruments"]) == {"guitar", "keyboards"}
    
    def test_data_merging_descriptions(self, deduplicator):
        """Test merging descriptions"""
        # Add band with description
        deduplicator.add_entity("bands", {
            "name": "Iron Maiden",
            "description": "NWOBHM pioneers"
        }, "chunk_001")
        
        # Add same band with different description
        deduplicator.add_entity("bands", {
            "name": "Iron Maiden",
            "description": "Known for galloping basslines"
        }, "chunk_002")
        
        group = deduplicator.entity_groups["bands"][0]
        desc = group.original_data["description"]
        assert "NWOBHM pioneers" in desc
        assert "Known for galloping basslines" in desc
    
    def test_conflict_detection(self, deduplicator):
        """Test conflict detection for numeric values"""
        # Add album with release year
        deduplicator.add_entity("albums", {
            "title": "Paranoid",
            "artist": "Black Sabbath",
            "release_year": 1970
        }, "chunk_001")
        
        # Add same album with different year
        deduplicator.add_entity("albums", {
            "title": "Paranoid",
            "artist": "Black Sabbath",
            "release_year": 1971
        }, "chunk_002")
        
        group = deduplicator.entity_groups["albums"][0]
        assert group.original_data["release_year"] == 1970  # Keeps first value
        assert "_conflicts" in group.original_data
        assert group.original_data["_conflicts"]["release_year"] == [1970, 1971]
    
    def test_alternate_values(self, deduplicator):
        """Test alternate value storage for different strings"""
        # Add location with description
        deduplicator.add_entity("locations", {
            "city": "Birmingham",
            "scene_description": "Industrial city that birthed heavy metal"
        }, "chunk_001")
        
        # Add same location with very different description
        deduplicator.add_entity("locations", {
            "city": "Birmingham",
            "scene_description": "Home of Black Sabbath"
        }, "chunk_002")
        
        group = deduplicator.entity_groups["locations"][0]
        # Should have alternate values since descriptions are quite different
        if "_alternate_values" in group.original_data:
            assert "scene_description" in group.original_data["_alternate_values"]
    
    def test_no_merge_different_entities(self, deduplicator):
        """Test that different entities don't merge"""
        deduplicator.add_entity("bands", {"name": "Black Sabbath"}, "chunk_001")
        deduplicator.add_entity("bands", {"name": "Black Flag"}, "chunk_002")
        deduplicator.add_entity("bands", {"name": "Deep Purple"}, "chunk_003")
        
        # Should have 3 separate groups
        assert len(deduplicator.entity_groups["bands"]) == 3
    
    def test_entity_without_name(self, deduplicator):
        """Test handling entities without name field"""
        # Entity without name should be skipped
        deduplicator.add_entity("bands", {"formed_year": 1970}, "chunk_001")
        assert len(deduplicator.entity_groups["bands"]) == 0
        
        # Album uses 'title' instead of 'name'
        deduplicator.add_entity("albums", {"title": "Master of Reality"}, "chunk_001")
        assert len(deduplicator.entity_groups["albums"]) == 1
    
    def test_cross_entity_type_isolation(self, deduplicator):
        """Test that entities of different types don't merge"""
        # Add band named Paranoid
        deduplicator.add_entity("bands", {"name": "Paranoid"}, "chunk_001")
        
        # Add album named Paranoid
        deduplicator.add_entity("albums", {"title": "Paranoid"}, "chunk_002")
        
        # Should remain separate
        assert len(deduplicator.entity_groups["bands"]) == 1
        assert len(deduplicator.entity_groups["albums"]) == 1