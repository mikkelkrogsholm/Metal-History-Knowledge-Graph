# Automation Scripts

This directory contains automation scripts and tools to streamline the Metal History project workflow.

## 🚀 Quick Start

```bash
# Make scripts executable
chmod +x automation/*.py
chmod +x setup_hooks.sh

# Setup git hooks (after git init)
./scripts/setup_hooks.sh
```

## 📁 Directory Structure

```
scripts/
├── automation/          # Main automation scripts
│   ├── batch_extraction.py      # Batch entity extraction with progress
│   ├── entity_validation.py     # Validate extracted entities
│   └── generate_embeddings.py   # Generate embeddings for entities
├── hooks/              # Git hooks
│   └── pre-commit      # Pre-commit validation
└── setup_hooks.sh      # Install git hooks
```

## 🔧 Automation Scripts

### Batch Entity Extraction

Extract entities from chunks with progress monitoring and error recovery:

```bash
# Test with 5 chunks
python scripts/automation/batch_extraction.py --limit 5

# Full extraction with custom batch size
python scripts/automation/batch_extraction.py --batch-size 10

# Resume interrupted extraction
python scripts/automation/batch_extraction.py --resume

# Start fresh (ignore checkpoint)
python scripts/automation/batch_extraction.py --no-resume
```

Features:
- Progress bar with time estimates
- Automatic checkpointing for resume capability
- Error recovery and retry mechanisms
- Detailed logging and statistics
- Rate limiting to avoid overwhelming the LLM

### Entity Validation

Validate extracted entities for quality and consistency:

```bash
# Validate deduplicated entities
python scripts/automation/entity_validation.py deduplicated_entities.json

# Validate with custom output
python scripts/automation/entity_validation.py extracted_entities.json --output my_report.json
```

Checks performed:
- Duplicate detection
- Data type validation
- Year format and range validation
- Required field validation
- Relationship consistency
- Quality score calculation (0-100)

### Embedding Generation

Generate embeddings for all entities using snowflake-arctic-embed2:

```bash
# Generate embeddings for single file
python scripts/automation/generate_embeddings.py deduplicated_entities.json

# Batch process directory
python scripts/automation/generate_embeddings.py batch_extraction_output/ --batch

# Verify embeddings
python scripts/automation/generate_embeddings.py entities_with_embeddings.json --verify

# Use different model
python scripts/automation/generate_embeddings.py entities.json --model nomic-embed-text
```

Features:
- Intelligent text representation for each entity type
- Progress tracking with time estimates
- Batch processing support
- Embedding verification
- Model flexibility

### Load to Kuzu Database

Load extracted entities and relationships into Kuzu graph database:

```bash
# Initialize database first (if not exists)
cd schema && python initialize_kuzu.py && cd ..

# Load deduplicated entities
python scripts/automation/load_to_kuzu.py deduplicated_entities.json

# Load with custom database path
python scripts/automation/load_to_kuzu.py entities.json --db-path /path/to/metal_history.db

# Load and verify data
python scripts/automation/load_to_kuzu.py deduplicated_entities.json --verify

# Custom batch size for large datasets
python scripts/automation/load_to_kuzu.py entities.json --batch-size 500
```

Features:
- Loads all entity types (bands, people, albums, etc.)
- Creates relationships between entities
- Progress tracking for each entity type
- Error handling and logging
- Data verification queries
- Batch processing for performance

## 🪝 Git Hooks

### Pre-commit Hook

Automatically runs before each commit:

1. **Fast tests** - Runs unit tests marked as "not slow"
2. **Syntax check** - Validates Python syntax
3. **Large file warning** - Alerts for files >10MB
4. **Sensitive data check** - Scans for API keys, passwords, etc.

To skip hooks temporarily:
```bash
git commit --no-verify -m "Emergency fix"
```

### Setup

```bash
# After initializing git repository
./scripts/setup_hooks.sh
```

## 📊 Complete Pipeline Workflow

1. **Initialize database**:
   ```bash
   cd schema && python initialize_kuzu.py && cd ..
   ```

2. **Process text chunks**:
   ```bash
   python scripts/automation/batch_extraction.py --limit 10
   ```

3. **Validate extraction results**:
   ```bash
   python scripts/automation/entity_validation.py batch_extraction_output/extraction_stats.json
   ```

4. **Fix any issues** (manual review based on validation report)

5. **Run deduplication pipeline**:
   ```bash
   cd pipeline && python extraction_pipeline.py && cd ..
   ```

6. **Generate embeddings**:
   ```bash
   python scripts/automation/generate_embeddings.py deduplicated_entities.json
   ```

7. **Load into Kuzu database**:
   ```bash
   python scripts/automation/load_to_kuzu.py entities_with_embeddings.json --verify
   ```

8. **Query the graph**:
   ```python
   import kuzu
   db = kuzu.Database("metal_history.db")
   conn = kuzu.Connection(db)
   
   # Find all Black Sabbath albums
   result = conn.execute("""
       MATCH (b:Band)-[:RELEASED]->(a:Album)
       WHERE b.name = 'Black Sabbath'
       RETURN a.title, a.release_year
       ORDER BY a.release_year
   """)
   ```

## ⚙️ Configuration

### Batch Extraction Settings
- Default batch size: 5 chunks
- Default output: `batch_extraction_output/`
- Checkpoint file: `extraction_checkpoint.json`
- Log file: `batch_extraction.log`

### Validation Thresholds
- Year range: 1960-2024 (warnings outside range)
- Quality score deductions:
  - Error: -5 points
  - Warning: -2 points

### Embedding Settings
- Default model: `snowflake-arctic-embed2:latest`
- Dimensions: 1024
- Format: List of floats

## 🐛 Troubleshooting

### "Virtual environment not activated"
```bash
source venv/bin/activate
```

### "Model not found" (embeddings)
```bash
ollama pull snowflake-arctic-embed2:latest
```

### "Tests failing in pre-commit"
```bash
# Run tests manually to see details
pytest -v

# Skip tests temporarily
git commit --no-verify
```

### "Out of memory during batch extraction"
- Reduce batch size: `--batch-size 3`
- Process specific documents only
- Increase system swap space

## 🔄 Continuous Improvement

To add new automation:

1. Create script in `automation/`
2. Follow existing patterns (argparse, logging, progress bars)
3. Add error handling and checkpointing
4. Document in this README
5. Create tests in `tests/`

## 📝 Notes

- All scripts use absolute imports (add project root to sys.path)
- Progress bars use `tqdm` for consistency
- Logging goes to both file and console
- JSON is the standard data format
- Scripts are designed to be idempotent and resumable