# Metal History Project Tests

This directory contains comprehensive tests for all components of the Metal History project.

## Test Structure

```
tests/
├── __init__.py              # Test package marker
├── conftest.py              # Shared fixtures and configuration
├── test_text_splitter.py    # Tests for text chunking functionality
├── test_fuzzy_matching.py   # Tests for fuzzy string matching
├── test_entity_deduplication.py  # Tests for entity deduplication
├── test_extraction_schemas.py    # Tests for Pydantic schemas
└── test_pipeline_integration.py  # Integration tests for the pipeline
```

## Running Tests

### Prerequisites
```bash
source venv/bin/activate
pip install pytest pytest-asyncio pytest-cov pytest-mock
```

### Run all tests:
```bash
pytest
```

### Run with coverage:
```bash
pytest --cov=. --cov-report=html
```

### Run specific test file:
```bash
pytest tests/test_fuzzy_matching.py
```

### Run specific test:
```bash
pytest tests/test_fuzzy_matching.py::TestFuzzyMatcher::test_typos
```

### Run tests by marker:
```bash
# Run only unit tests
pytest -m unit

# Skip slow tests
pytest -m "not slow"
```

### Run with verbose output:
```bash
pytest -v
```

## Test Coverage

The tests cover:

1. **Text Splitting** (`test_text_splitter.py`)
   - Chunk size limits
   - Section-based splitting
   - Paragraph chunking with overlap
   - Minimum chunk size enforcement

2. **Fuzzy Matching** (`test_fuzzy_matching.py`)
   - Exact and case-insensitive matching
   - Typo tolerance
   - Special character handling
   - Plural detection
   - Best match finding

3. **Entity Deduplication** (`test_entity_deduplication.py`)
   - Similar entity merging
   - Data combination from multiple sources
   - Conflict detection
   - List merging
   - Description concatenation

4. **Extraction Schemas** (`test_extraction_schemas.py`)
   - All Pydantic model validations
   - Required vs optional fields
   - JSON serialization
   - Schema generation for Ollama

5. **Pipeline Integration** (`test_pipeline_integration.py`)
   - Chunk loading
   - Entity processing
   - Relationship deduplication
   - Final result generation

## Writing New Tests

When adding new functionality, please:

1. Create appropriate test files following the naming convention
2. Use fixtures from `conftest.py` when possible
3. Add docstrings to test functions
4. Group related tests in classes
5. Use descriptive test names that explain what's being tested

Example test structure:
```python
class TestNewFeature:
    
    @pytest.fixture
    def setup_data(self):
        """Fixture for test data"""
        return {"test": "data"}
    
    def test_feature_behavior(self, setup_data):
        """Test that feature behaves correctly"""
        result = new_feature(setup_data)
        assert result == expected_value
```

## Mocking External Dependencies

For tests that would call Ollama or other external services, use mocks:

```python
from unittest.mock import patch

@patch('module.ollama.generate')
def test_with_mock_ollama(mock_generate):
    mock_generate.return_value = {"response": "mocked"}
    # Your test code
```

## Continuous Integration

Tests should pass before merging any changes. The test suite is designed to run quickly (< 30 seconds) by mocking external calls.