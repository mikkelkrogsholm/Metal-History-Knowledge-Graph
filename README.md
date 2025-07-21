# Metal History Knowledge Graph Project

A comprehensive system for extracting and modeling the history of heavy metal music using Natural Language Processing, graph databases, and semantic search.

## Overview

This project processes metal history documents to:
1. Extract entities (bands, people, albums, genres, etc.) using Claude AI
2. Identify and model relationships between entities
3. Store data in a Kuzu graph database with vector embeddings
4. Provide a FastAPI web interface for exploration and search

## Project Structure

```
history_of_metal/
├── src/                       # All source code
│   ├── extraction/           # Entity extraction using Claude CLI
│   ├── pipeline/             # Processing pipeline modules
│   ├── schema/              # Database schema definitions
│   ├── api/                 # FastAPI web application
│   └── utils/               # Shared utilities
├── data/                     # All data files
│   ├── raw/                 # Original history documents
│   ├── processed/           # Extraction outputs
│   │   ├── chunks/         # Document chunks
│   │   ├── extracted/      # Raw extractions
│   │   ├── deduplicated/   # Cleaned entities
│   │   └── embeddings/     # Vector embeddings
│   ├── database/            # Kuzu graph database
│   └── cache/              # API cache
├── scripts/                  # Executable scripts
│   ├── pipeline/           # Pipeline automation
│   ├── automation/         # Python utilities
│   └── analysis/          # Analysis tools
├── tests/                   # Test suite
├── docs/                    # Documentation
├── config/                  # Configuration
└── logs/                    # Log files
```

## Setup

### 1. Create Virtual Environment
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Install Claude Code CLI
```bash
# Visit https://claude.ai/code for installation
# Login with: claude login
# Verify: claude --version
```

### 4. Configure Environment
```bash
./scripts/configure_environment.sh
```

## Quick Start

### Run Complete Pipeline
```bash
# Test mode (5 chunks)
./scripts/pipeline/run_full_pipeline.sh --test

# Full extraction (all chunks)
./scripts/pipeline/run_full_pipeline.sh
```

### Individual Steps

1. **Split Documents**
   ```bash
   ./scripts/pipeline/01_split_documents.sh
   ```

2. **Extract Entities** (using Claude CLI)
   ```bash
   ./scripts/pipeline/02_extract_entities.sh 10  # First 10 chunks
   ```

3. **Deduplicate Entities**
   ```bash
   ./scripts/pipeline/03_deduplicate_entities.sh
   ```

4. **Validate Quality**
   ```bash
   ./scripts/pipeline/04_validate_entities.sh
   ```

5. **Generate Embeddings**
   ```bash
   ./scripts/pipeline/05_generate_embeddings.sh
   ```

6. **Load to Database**
   ```bash
   ./scripts/pipeline/06_load_to_kuzu_merge.sh
   ```

## Web API

### Start the API Server
```bash
cd src/api
uvicorn main:app --reload
```

### API Endpoints
- `GET /` - API documentation
- `GET /health` - Health check
- `GET /api/v1/bands` - List bands
- `GET /api/v1/albums` - List albums
- `GET /api/v1/search?q=sabbath` - Search entities
- `GET /api/v1/graph/subgenre-evolution` - Genre evolution graph

### API Documentation
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Database Queries

### Using Python
```python
import kuzu
db = kuzu.Database('data/database/metal_history.db')
conn = kuzu.Connection(db)

# Find bands from Birmingham
result = conn.execute("""
    MATCH (b:Band)-[:FORMED_IN]->(l:GeographicLocation)
    WHERE l.city = 'Birmingham'
    RETURN b.name, b.formed_year
""")
print(result.get_as_df())
```

### Common Queries
```cypher
# Genre evolution
MATCH (g1:Subgenre)-[:EVOLVED_INTO]->(g2:Subgenre)
RETURN g1.name, g2.name

# Band members
MATCH (p:Person)-[:MEMBER_OF]->(b:Band)
WHERE b.name = 'Black Sabbath'
RETURN p.name, p.instruments

# Albums by year
MATCH (a:Album)
WHERE a.release_year = 1970
RETURN a.title, a.band_name
```

## Development

### Running Tests
```bash
pytest tests/ -v                    # All tests
pytest tests/test_extraction.py -v  # Specific test
pytest --cov=src --cov-report=html  # Coverage report
```

### Code Quality
```bash
# Linting
pylint src/

# Type checking
mypy src/

# Format code
black src/
```

### Adding New Features
1. Create feature branch: `git checkout -b feature/your-feature`
2. Make changes following project structure
3. Add tests for new functionality
4. Update documentation
5. Create pull request

## Performance

- **Extraction Speed**: ~20-30 seconds per chunk (Claude CLI)
- **Total Processing**: ~30 minutes for full corpus
- **Database Size**: ~1.5MB for complete graph
- **API Response**: <100ms for most queries

## Configuration

### Environment Variables
Create `.env` file:
```env
# API Configuration
DATABASE_PATH=data/database/metal_history.db
API_HOST=0.0.0.0
API_PORT=8000

# Claude CLI (if using API keys)
ANTHROPIC_API_KEY=your_key_here

# Cache Settings
CACHE_TTL=3600
```

### Extraction Profiles
See `config/extraction_profiles.json` for system-specific settings.

## Troubleshooting

### Common Issues

1. **Claude CLI not found**
   - Install from https://claude.ai/code
   - Run `claude login` to authenticate

2. **Import errors**
   - Ensure virtual environment is activated
   - Check Python path includes project root

3. **Database not found**
   - Run `python src/schema/initialize_kuzu.py`
   - Check path: `data/database/metal_history.db`

4. **Slow extraction**
   - Normal: ~20-30s per chunk
   - Use `--limit` flag for testing
   - Check Claude API quotas

## Contributing

1. Fork the repository
2. Create your feature branch
3. Follow code style guidelines
4. Add comprehensive tests
5. Update documentation
6. Submit pull request

## License

This project is licensed under the MIT License - see LICENSE file for details.

## Acknowledgments

- Claude AI for entity extraction
- Kuzu Database for graph storage
- FastAPI for web framework
- Snowflake Arctic Embed for embeddings