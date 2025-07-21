# Metal History Knowledge Graph - Claude Code Instructions

This project extracts entities and relationships from metal history documents to build a knowledge graph. The codebase has been reorganized for better maintainability and to support a FastAPI web application.

## 🏗️ Project Structure

```
history_of_metal/
├── src/                # All source code
│   ├── extraction/    # Entity extraction modules
│   ├── pipeline/      # Processing pipeline
│   ├── schema/        # Database schemas
│   ├── api/          # FastAPI application
│   └── utils/        # Shared utilities
├── data/              # All data files
│   ├── raw/          # Original documents
│   ├── processed/    # Processing outputs
│   ├── database/     # Kuzu database
│   └── cache/        # API cache
├── scripts/           # Automation scripts
├── tests/            # Test suite
├── docs/             # Documentation
├── config/           # Configuration
└── logs/             # Log files
```

## 🚀 Quick Start

**IMPORTANT**: ALWAYS activate the virtual environment first:
```bash
source venv/bin/activate
```

## 📝 Common Commands

### Essential Operations
```bash
# Text Processing
python src/utils/text_splitter.py --chunk-size 3000    # Split documents

# Entity Extraction (using Claude CLI - fast!)
./scripts/pipeline/02_extract_entities.sh 5            # Test with 5 chunks
./scripts/pipeline/02_extract_entities.sh              # Process all chunks

# Database Operations
python src/schema/initialize_kuzu.py                   # Create database
python src/schema/initialize_kuzu.py --reset           # Reset database

# Run Complete Pipeline
./scripts/pipeline/run_full_pipeline.sh --test         # Test mode (5 chunks)
./scripts/pipeline/run_full_pipeline.sh                # Full extraction

# Start API Server
cd src/api && uvicorn main:app --reload               # Development mode
```

### 🔍 Testing & Quality
```bash
pytest tests/ -v                                        # Run all tests
pytest tests/test_fuzzy_matching.py -v                  # Specific test
pytest --cov=src --cov-report=html                     # Coverage report
python -m pylint src/                                   # Lint code
python -m mypy src/                                     # Type checking
```

### 🌐 API Endpoints
```bash
# After starting server with: cd src/api && uvicorn main:app --reload
curl http://localhost:8000/health                       # Health check
curl http://localhost:8000/api/v1/bands                # List bands
curl "http://localhost:8000/api/v1/search?q=sabbath"   # Search
```

## 🔧 Key File Locations

### Source Code
- `src/extraction/claude_cli_extraction.py` - Main extraction using Claude CLI
- `src/pipeline/extraction_pipeline.py` - Deduplication and processing
- `src/schema/initialize_kuzu.py` - Database initialization
- `src/api/main.py` - FastAPI application entry point
- `src/utils/text_splitter.py` - Document chunking

### Data Files
- `data/raw/` - Original history documents
- `data/processed/chunks/chunks_optimized.json` - Document chunks
- `data/processed/extracted/` - Raw extraction outputs
- `data/processed/deduplicated/deduplicated_entities.json` - Cleaned entities
- `data/processed/embeddings/entities_with_embeddings.json` - With vectors
- `data/database/metal_history.db` - Kuzu graph database

### Scripts
- `scripts/pipeline/run_full_pipeline.sh` - Complete pipeline
- `scripts/pipeline/01-06_*.sh` - Individual pipeline steps
- `scripts/automation/` - Python automation tools

## 🎯 Workflow Patterns

### 1. Making Changes to Extraction
1. Edit files in `src/extraction/`
2. Test with: `./scripts/pipeline/02_extract_entities.sh 1`
3. Verify output in `data/processed/extracted/`
4. Run full pipeline when satisfied

### 2. Adding API Endpoints
1. Create router in `src/api/routers/`
2. Add models in `src/api/models/`
3. Update `src/api/main.py` to include router
4. Test with: `cd src/api && uvicorn main:app --reload`

### 3. Database Schema Changes
1. Update `src/schema/metal_history_schema_enhanced.cypher`
2. Modify `src/schema/initialize_kuzu.py`
3. Recreate database: `python src/schema/initialize_kuzu.py --reset`
4. Reload data: `./scripts/pipeline/06_load_to_kuzu_merge.sh`

## 📊 Performance Characteristics

- **Extraction**: ~20-30 seconds per chunk (Claude CLI)
- **Full pipeline**: ~30 minutes for 62 chunks
- **Database size**: ~1.5MB for complete graph
- **API response**: <100ms for most queries

## 💡 Important Notes

### New Structure Benefits
- **Clean separation**: Code, data, and config are clearly separated
- **Single database**: Only one database location to manage
- **FastAPI ready**: Proper structure for web development
- **Easy deployment**: Just deploy `src/` and `config/`

### Path Updates
All scripts and code have been updated to use new paths:
- Database: `data/database/metal_history.db`
- Chunks: `data/processed/chunks/chunks_optimized.json`
- Outputs: `data/processed/extracted/`, etc.

### Import Changes
Python imports now use the `src.` prefix:
```python
from src.extraction.extraction_schemas import ExtractionResult
from src.pipeline.extraction_pipeline import EntityDeduplicator
```

## 🐛 Troubleshooting

### Import Errors
```bash
# Ensure virtual environment is active
which python  # Should show venv/bin/python

# Check PYTHONPATH includes project root
echo $PYTHONPATH
```

### Path Not Found
- All data files are now under `data/`
- All source code is under `src/`
- Update any hardcoded paths in your scripts

### API Issues
```bash
# Check if port 8000 is in use
lsof -i :8000

# Run with different port
uvicorn main:app --port 8001
```

## 🔄 Migration from Old Structure

If you have existing data:
1. Move `*.json` files to appropriate `data/processed/` subdirs
2. Move database from `schema/metal_history.db` to `data/database/`
3. Update any custom scripts to use new paths
4. Test with small extraction before full run

## 📋 Git Workflow

### After Reorganization
```bash
git add -A
git commit -m "refactor: reorganize project structure for better maintainability"
git push origin main
```

### For New Features
```bash
git checkout -b feature/your-feature
# Make changes
git add -A
git commit -m "feat: add your feature"
git push origin feature/your-feature
```

## 🚨 Do's and Don'ts

### ✅ DO
- Keep all data files under `data/`
- Put new source code under appropriate `src/` subdirectory
- Update documentation when adding features
- Run tests before committing
- Use relative imports within `src/`

### ❌ DON'T
- Put data files in source directories
- Create new top-level directories without discussion
- Hardcode absolute paths
- Mix configuration with code
- Ignore the virtual environment

## 🎉 Ready to Code!

The project is now well-organized and ready for development. The FastAPI structure is in place for building a web interface, and all scripts have been updated to use the new paths.