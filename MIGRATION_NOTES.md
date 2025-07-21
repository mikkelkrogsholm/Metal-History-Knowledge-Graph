# Repository Reorganization - Migration Notes

## Overview
The repository has been reorganized to improve maintainability, support the upcoming FastAPI web application, and follow Python best practices.

## Major Changes

### 1. Directory Structure
- **Before**: Mixed source code, data files, and outputs in root and various directories
- **After**: Clear separation with `src/`, `data/`, `scripts/`, `tests/`, `docs/`, `config/`, and `logs/`

### 2. Source Code Organization
All Python source code moved to `src/`:
- `extraction/*.py` → `src/extraction/`
- `pipeline/*.py` → `src/pipeline/`
- `schema/initialize_kuzu.py` → `src/schema/`
- `history/text_splitter.py` → `src/utils/`

### 3. Data File Consolidation
All data files moved to `data/`:
- Raw documents → `data/raw/`
- Chunks → `data/processed/chunks/`
- Extraction outputs → `data/processed/extracted/`
- Deduplicated entities → `data/processed/deduplicated/`
- Embeddings → `data/processed/embeddings/`
- Database → `data/database/metal_history.db` (single location)

### 4. Import Path Updates
All Python imports updated to use `src.` prefix:
```python
# Old
from extraction.extraction_schemas import ExtractionResult

# New
from src.extraction.extraction_schemas import ExtractionResult
```

### 5. Script Path Updates
All scripts updated to reference new paths:
- Database: `data/database/metal_history.db`
- Chunks: `data/processed/chunks/chunks_optimized.json`
- Outputs: `data/processed/extracted/`, etc.

### 6. FastAPI Application
New API structure created in `src/api/`:
- `main.py` - Application entry point
- `config.py` - Configuration settings
- `routers/` - API endpoints (bands, albums, search, graph)
- `models/` - Pydantic models
- `services/` - Business logic (database service)
- `middleware/` - CORS and other middleware

### 7. Documentation Updates
- `README.md` - Completely rewritten with new structure
- `CLAUDE.md` - Updated with new paths and workflows
- Old subdirectory docs moved to main `docs/` folder

### 8. Clean Up
- Removed empty directories
- Consolidated duplicate files
- Updated `.gitignore` for new structure
- Added `.gitkeep` files for important empty directories

## Migration Instructions

If you have local changes or data:

1. **Stash your changes**: `git stash`
2. **Pull the reorganization**: `git pull`
3. **Move your data files**:
   ```bash
   mv your_entities.json data/processed/extracted/
   mv your_database.db data/database/
   ```
4. **Update your scripts** to use new paths
5. **Test with small extraction** before full run

## Benefits

1. **Cleaner Structure**: Easy to navigate and understand
2. **Better Separation**: Code, data, and config clearly separated
3. **FastAPI Ready**: Proper structure for web development
4. **Easier Deployment**: Just deploy `src/` and `config/`
5. **Single Database**: No more confusion about which database to use
6. **Standard Python Layout**: Follows community best practices

## Quick Test

Run a quick test to ensure everything works:
```bash
source venv/bin/activate
./scripts/pipeline/run_full_pipeline.sh --test 2
```

This will process 2 chunks through the entire pipeline.