"""
Integration tests for the extraction pipeline
"""

import pytest
import json
import tempfile
import os
from unittest.mock import Mock, patch
from pipeline.extraction_pipeline import ExtractionPipeline
from extraction.extraction_schemas import ExtractionResult, Band, Person

class TestPipelineIntegration:
    
    @pytest.fixture
    def mock_chunks_file(self):
        """Create a temporary chunks file for testing"""
        chunks_data = {
            "metadata": {
                "chunk_size": 2000,
                "chunk_overlap": 200,
                "total_documents": 1,
                "total_chunks": 3
            },
            "documents": {
                "test_doc.md": [
                    {
                        "id": "test_001",
                        "text": "Black Sabbath formed in Birmingham in 1968.",
                        "chunk_index": 0,
                        "char_count": 43
                    },
                    {
                        "id": "test_002", 
                        "text": "Black Sabath (typo) pioneered heavy metal. Tony Iommi played guitar.",
                        "chunk_index": 1,
                        "char_count": 68
                    },
                    {
                        "id": "test_003",
                        "text": "Iron Maiden formed in 1975. Part of NWOBHM movement.",
                        "chunk_index": 2,
                        "char_count": 52
                    }
                ]
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(chunks_data, f)
            temp_path = f.name
        
        yield temp_path
        os.unlink(temp_path)
    
    @pytest.fixture
    def mock_extraction_result(self):
        """Mock extraction result"""
        return ExtractionResult(
            bands=[
                Band(name="Black Sabbath", formed_year=1968, origin_city="Birmingham", 
                     description="Pioneered heavy metal")
            ],
            people=[
                Person(name="Tony Iommi", instruments=["guitar"], 
                       description="Guitarist")
            ]
        )
    
    def test_load_chunks(self, mock_chunks_file):
        """Test loading chunks from file"""
        # Need to patch the path construction
        with patch.object(ExtractionPipeline, 'load_chunks') as mock_load:
            mock_load.return_value = {
                "metadata": {"total_chunks": 3},
                "documents": {"test.md": [{"id": "1", "text": "test"}]}
            }
            
            pipeline = ExtractionPipeline(chunks_file=mock_chunks_file)
            data = pipeline.load_chunks()
            
            assert "metadata" in data
            assert "documents" in data
    
    def test_relationship_hashing(self):
        """Test relationship deduplication via hashing"""
        pipeline = ExtractionPipeline()
        
        rel1 = {
            "type": "MEMBER_OF",
            "from_entity_type": "person",
            "from_entity_name": "Tony Iommi",
            "to_entity_type": "band", 
            "to_entity_name": "Black Sabbath"
        }
        
        rel2 = {
            "type": "MEMBER_OF",
            "from_entity_type": "person",
            "from_entity_name": "TONY IOMMI",  # Different case
            "to_entity_type": "band",
            "to_entity_name": "black sabbath"  # Different case
        }
        
        hash1 = pipeline._hash_relationship(rel1)
        hash2 = pipeline._hash_relationship(rel2)
        
        assert hash1 == hash2  # Should be same hash despite case differences
    
    def test_process_extraction_result(self):
        """Test processing extraction results"""
        pipeline = ExtractionPipeline()
        
        result = ExtractionResult(
            bands=[Band(name="Metallica", formed_year=1981, description="Thrash band")],
            people=[Person(name="James Hetfield", instruments=["vocals", "guitar"])],
            relationships=[{
                "type": "MEMBER_OF",
                "from_entity_type": "person",
                "from_entity_name": "James Hetfield",
                "to_entity_type": "band",
                "to_entity_name": "Metallica",
                "year": 1981,
                "role": "Vocalist/Guitarist",
                "context": "Founding member"
            }]
        )
        
        pipeline._process_extraction_result(result, "chunk_001")
        
        # Check entities were added
        assert len(pipeline.deduplicator.entity_groups["bands"]) == 1
        assert len(pipeline.deduplicator.entity_groups["people"]) == 1
        assert len(pipeline.relationship_hashes) == 1
    
    @patch('pipeline.extraction_pipeline.extract_entities_enhanced')
    def test_process_chunks_with_limit(self, mock_extract, mock_chunks_file):
        """Test processing chunks with limit"""
        # Mock the extraction function
        mock_extract.return_value = ExtractionResult()
        
        # Create pipeline with mocked chunks file
        pipeline = ExtractionPipeline(chunks_file=os.path.basename(mock_chunks_file))
        
        # Mock load_chunks to return test data
        with patch.object(pipeline, 'load_chunks') as mock_load:
            mock_load.return_value = {
                "documents": {
                    "test.md": [
                        {"id": f"chunk_{i}", "text": f"Test chunk {i}"}
                        for i in range(10)
                    ]
                }
            }
            
            # Process with limit
            results = pipeline.process_chunks(limit=3)
            
            # Should only process 3 chunks
            assert mock_extract.call_count == 3
    
    def test_get_deduplicated_results(self):
        """Test getting final deduplicated results"""
        pipeline = ExtractionPipeline()
        
        # Add some test data
        pipeline.deduplicator.add_entity("bands", 
            {"name": "Black Sabbath", "formed_year": 1968}, "chunk_001")
        pipeline.deduplicator.add_entity("bands",
            {"name": "Black Sabath", "origin_city": "Birmingham"}, "chunk_002")
        
        results = pipeline._get_deduplicated_results()
        
        assert "entities" in results
        assert "metadata" in results
        assert len(results["entities"]["bands"]) == 1  # Should be deduplicated
        
        band = results["entities"]["bands"][0]
        assert band["name"] == "Black Sabbath"
        assert band["formed_year"] == 1968
        assert band["origin_city"] == "Birmingham"
        assert "_metadata" in band
        assert len(band["_metadata"]["variations"]) == 2
        assert len(band["_metadata"]["source_chunks"]) == 2