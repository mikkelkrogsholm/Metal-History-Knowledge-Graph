# Pipeline Scripts

This directory contains shell scripts for running the complete Metal History extraction pipeline.

## 🚀 Quick Start

```bash
# Make scripts executable
chmod +x *.sh

# Run full pipeline (30+ minutes)
./run_full_pipeline.sh

# Run in test mode (5 chunks only)
./run_full_pipeline.sh --test

# Skip certain steps
./run_full_pipeline.sh --skip extract,embed
```

## 📜 Individual Scripts

Each script can be run independently:

### 1. Split Documents
```bash
./01_split_documents.sh [chunk_size] [overlap] [output_file]
# Example: ./01_split_documents.sh 3000 300 chunks.json
```
Splits markdown documents into processable chunks.

### 2. Extract Entities
```bash
./02_extract_entities.sh [limit] [batch_size] [chunks_file]
# Example: ./02_extract_entities.sh 10 5 chunks.json
```
Extracts entities using Mistral/Magistral LLM. **⚠️ SLOW: 30-60s per chunk**

### 3. Deduplicate Entities
```bash
./03_deduplicate_entities.sh [input_dir] [output_file]
# Example: ./03_deduplicate_entities.sh batch_extraction_output entities.json
```
Merges duplicate entities using fuzzy matching (85% similarity).

### 4. Validate Entities
```bash
./04_validate_entities.sh [entities_file] [report_file]
# Example: ./04_validate_entities.sh entities.json report.json
```
Validates data quality and generates quality score (0-100).

### 5. Generate Embeddings
```bash
./05_generate_embeddings.sh [entities_file] [output_file]
# Example: ./05_generate_embeddings.sh entities.json entities_embedded.json
```
Generates 1024-dimensional embeddings using snowflake-arctic-embed2.

### 6. Load to Kuzu
```bash
./06_load_to_kuzu.sh [entities_file] [db_path] [--verify|--no-verify]
# Example: ./06_load_to_kuzu.sh entities_embedded.json metal.db --verify
```
Loads all entities and relationships into Kuzu graph database.

## 🔄 Full Pipeline

The `run_full_pipeline.sh` script orchestrates all steps:

```bash
# Full run (processes all documents)
./run_full_pipeline.sh

# Test mode (processes 5 chunks only)
./run_full_pipeline.sh --test

# Skip steps (comma-separated)
./run_full_pipeline.sh --skip split,validate

# Available skip options:
# - split: Skip document splitting
# - extract: Skip entity extraction
# - dedupe: Skip deduplication
# - validate: Skip validation
# - embed: Skip embedding generation
# - load: Skip database loading
```

## ⏱️ Performance Expectations

- **Document splitting**: < 1 minute
- **Entity extraction**: 30-60 seconds per chunk
  - Test mode (5 chunks): ~5 minutes
  - Full run: 30+ minutes
- **Deduplication**: 1-2 minutes
- **Validation**: < 1 minute
- **Embedding generation**: 5-10 minutes
- **Database loading**: 2-5 minutes

**Total time**: 45-60 minutes for full pipeline

## 📊 Output Files

1. `chunks_optimized.json` - Document chunks
2. `batch_extraction_output/` - Raw extracted entities per chunk
3. `deduplicated_entities.json` - Merged unique entities
4. `validation_report.json` - Quality assessment
5. `entities_with_embeddings.json` - Entities with embeddings
6. `metal_history.db/` - Kuzu database directory

## 🔍 Verifying Results

```bash
# Check chunk count
jq '.metadata.total_chunks' chunks_optimized.json

# Check entity counts
jq '.metadata.total_entities' deduplicated_entities.json

# Check quality score
jq '.quality_score' validation_report.json

# Query database
python -c "
import kuzu
db = kuzu.Database('metal_history.db')
conn = kuzu.Connection(db)
result = conn.execute('MATCH (b:Band) RETURN COUNT(b) as count')
print(f'Total bands: {result.get_next()[0]}')
"
```

## ⚠️ Prerequisites

1. **Virtual environment activated**:
   ```bash
   source venv/bin/activate
   ```

2. **Ollama running** with models:
   ```bash
   ollama list
   # Should show:
   # - magistral:24b
   # - snowflake-arctic-embed2:latest
   ```

3. **Required Python packages**:
   ```bash
   pip install -r requirements.txt
   ```

## 🛠️ Troubleshooting

### "Virtual environment not activated"
```bash
source venv/bin/activate
```

### "Ollama is not running"
```bash
# Start Ollama
ollama serve
```

### "Model not found"
```bash
# Pull required models
ollama pull magistral:24b
ollama pull snowflake-arctic-embed2:latest
```

### "Out of memory"
- Reduce batch size in extraction script
- Process fewer chunks at once
- Increase system swap space

### "Database errors"
```bash
# Reset database
rm -rf metal_history.db
cd schema && python initialize_kuzu.py
```

## 🔄 Re-running Pipeline

To re-run after errors:

1. **Resume extraction** (uses checkpoint):
   ```bash
   cd ../..
   python scripts/automation/batch_extraction.py --resume
   ```

2. **Skip completed steps**:
   ```bash
   ./run_full_pipeline.sh --skip split,extract
   ```

3. **Start fresh**:
   ```bash
   rm -rf batch_extraction_output/ *.json metal_history.db
   ./run_full_pipeline.sh
   ```