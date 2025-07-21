"""
Pytest configuration and shared fixtures
"""

import pytest
import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

@pytest.fixture
def sample_text_chunks():
    """Sample text chunks for testing"""
    return [
        {
            "id": "test_chunk_001",
            "text": "Black Sabbath formed in Birmingham in 1968. Tony Iommi played guitar.",
            "source_file": "test_doc.md",
            "chunk_index": 0
        },
        {
            "id": "test_chunk_002", 
            "text": "Black Sabath (typo) was formed in Birmingham, UK. Ozzy Osbourne was the vocalist.",
            "source_file": "test_doc.md",
            "chunk_index": 1
        },
        {
            "id": "test_chunk_003",
            "text": "Iron Maiden formed in 1975 in London. They were part of the NWOBHM movement.",
            "source_file": "test_doc.md",
            "chunk_index": 2
        }
    ]

@pytest.fixture
def sample_entities():
    """Sample extracted entities for testing"""
    return {
        "bands": [
            {"name": "Black Sabbath", "formed_year": 1968, "origin_city": "Birmingham"},
            {"name": "Iron Maiden", "formed_year": 1975, "origin_city": "London"}
        ],
        "people": [
            {"name": "Tony Iommi", "instruments": ["guitar"], "associated_bands": ["Black Sabbath"]},
            {"name": "Ozzy Osbourne", "instruments": ["vocals"], "associated_bands": ["Black Sabbath"]}
        ],
        "subgenres": [
            {"name": "NWOBHM", "era_start": 1979, "era_end": 1983, "key_characteristics": "Fast, melodic"}
        ]
    }

@pytest.fixture
def mock_ollama_response():
    """Mock response from Ollama"""
    return {
        "response": """{"bands": [{"name": "Black Sabbath", "formed_year": 1968}], "people": [], "albums": [], "songs": [], "subgenres": [], "locations": [], "events": [], "equipment": [], "studios": [], "labels": [], "relationships": []}"""
    }