#!/bin/bash
# Test pipeline with configurable number of chunks

set -e  # Exit on error

# Parameters
CHUNK_LIMIT=${1:-5}  # Default to 5 chunks if not specified
SKIP_STEPS=${2:-""}  # Optional: comma-separated list of steps to skip
USE_ADAPTIVE=${3:-true}  # Use adaptive extraction by default

echo "🧪 Testing Metal History Pipeline"
echo "=================================="
echo "Chunks to process: $CHUNK_LIMIT"
echo "Skip steps: ${SKIP_STEPS:-none}"
echo "Use adaptive extraction: $USE_ADAPTIVE"
echo ""

# Get project root directory
PROJECT_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"

# Activate virtual environment if not already active
if [ -z "$VIRTUAL_ENV" ]; then
    if [ -f "$PROJECT_ROOT/venv/bin/activate" ]; then
        source "$PROJECT_ROOT/venv/bin/activate"
    else
        echo "❌ Virtual environment not found at $PROJECT_ROOT/venv"
        echo "Please create it first: python -m venv venv"
        exit 1
    fi
fi

cd "$PROJECT_ROOT"

# Function to check if step should be skipped
should_skip() {
    if [ -z "$SKIP_STEPS" ]; then
        return 1
    fi
    [[ ",$SKIP_STEPS," == *",$1,"* ]]
}

# Start timer
START_TIME=$(date +%s)

# Step 1: Split documents (if not already done)
if ! should_skip "split"; then
    if [ ! -f "chunks_optimized.json" ]; then
        echo "Step 1: Splitting documents..."
        echo "---------------------------------"
        ./scripts/pipeline/01_split_documents.sh
        echo ""
    else
        echo "Step 1: Using existing chunks file"
        TOTAL_CHUNKS=$(python -c "import json; print(json.load(open('chunks_optimized.json'))['metadata']['total_chunks'])")
        echo "  Total chunks available: $TOTAL_CHUNKS"
        echo "  Will process: $CHUNK_LIMIT chunks"
        echo ""
    fi
else
    echo "Skipping document splitting..."
fi

# Step 2: Extract entities from limited chunks
if ! should_skip "extract"; then
    echo "Step 2: Extracting entities from $CHUNK_LIMIT chunks..."
    echo "---------------------------------"
    
    if [ "$USE_ADAPTIVE" = true ] && [ -f "./scripts/pipeline/02_extract_entities_adaptive.sh" ]; then
        echo "Using adaptive extraction..."
        ./scripts/pipeline/02_extract_entities_adaptive.sh chunks_optimized.json "$CHUNK_LIMIT"
    else
        echo "Using standard extraction..."
        ./scripts/pipeline/02_extract_entities.sh "$CHUNK_LIMIT"
    fi
    echo ""
else
    echo "Skipping entity extraction..."
fi

# Step 3: Deduplicate entities
if ! should_skip "dedupe"; then
    echo "Step 3: Deduplicating entities..."
    echo "---------------------------------"
    ./scripts/pipeline/03_deduplicate_entities.sh
    echo ""
else
    echo "Skipping deduplication..."
fi

# Step 4: Validate entities
if ! should_skip "validate"; then
    echo "Step 4: Validating entities..."
    echo "---------------------------------"
    ./scripts/pipeline/04_validate_entities.sh
    echo ""
else
    echo "Skipping validation..."
fi

# Step 5: Generate embeddings (optional for test)
if ! should_skip "embed"; then
    echo "Step 5: Generating embeddings..."
    echo "---------------------------------"
    if command -v ollama &> /dev/null && ollama list | grep -q "snowflake-arctic-embed2"; then
        ./scripts/pipeline/05_generate_embeddings.sh
    else
        echo "⚠️  Embedding model not available, copying deduplicated data..."
        cp deduplicated_entities.json entities_with_embeddings.json
    fi
    echo ""
else
    echo "Skipping embedding generation..."
    if [ ! -f "entities_with_embeddings.json" ] && [ -f "deduplicated_entities.json" ]; then
        cp deduplicated_entities.json entities_with_embeddings.json
    fi
fi

# Step 6: Load to Kuzu
if ! should_skip "load"; then
    echo "Step 6: Loading to Kuzu database (MERGE mode)..."
    echo "---------------------------------"
    ./scripts/pipeline/06_load_to_kuzu_merge.sh
    echo ""
else
    echo "Skipping database loading..."
fi

# Calculate elapsed time
END_TIME=$(date +%s)
ELAPSED=$((END_TIME - START_TIME))
MINUTES=$((ELAPSED / 60))
SECONDS=$((ELAPSED % 60))

# Summary
echo ""
echo "======================================"
echo "✅ Test Pipeline Complete!"
echo "======================================"
echo "Chunks processed: $CHUNK_LIMIT"
echo "Total time: ${MINUTES}m ${SECONDS}s"
echo ""

# Show statistics if extraction was done
if [ -f "extracted_entities.json" ] && ! should_skip "extract"; then
    python -c "
import json
with open('extracted_entities.json') as f:
    data = json.load(f)
    total = sum(len(v) for k, v in data['entities'].items() if isinstance(v, list))
    print(f'Entities extracted: {total}')
    for entity_type, entities in data['entities'].items():
        if isinstance(entities, list) and entities:
            print(f'  {entity_type}: {len(entities)}')
"
fi

# Show database stats if loaded
if [ -d "schema/metal_history.db" ] && ! should_skip "load"; then
    echo ""
    echo "Database contents:"
    python -c "
import kuzu
db = kuzu.Database('schema/metal_history.db')
conn = kuzu.Connection(db)
for table in ['Band', 'Person', 'Album', 'Song', 'Subgenre']:
    result = conn.execute(f'MATCH (n:{table}) RETURN count(n)')
    if result.has_next():
        count = result.get_next()[0]
        if count > 0:
            print(f'  {table}: {count}')
"
fi

echo ""
echo "Test files generated:"
[ -f "chunks_optimized.json" ] && echo "  ✓ chunks_optimized.json"
[ -f "extracted_entities.json" ] && echo "  ✓ extracted_entities.json"
[ -f "deduplicated_entities.json" ] && echo "  ✓ deduplicated_entities.json"
[ -f "validation_report.json" ] && echo "  ✓ validation_report.json"
[ -f "entities_with_embeddings.json" ] && echo "  ✓ entities_with_embeddings.json"
[ -d "schema/metal_history.db" ] && echo "  ✓ schema/metal_history.db/"

echo ""
echo "Usage examples:"
echo "  ./scripts/pipeline/test_pipeline.sh 10        # Process 10 chunks"
echo "  ./scripts/pipeline/test_pipeline.sh 20 embed  # Process 20 chunks, skip embeddings"
echo "  ./scripts/pipeline/test_pipeline.sh 5 \"\" false # 5 chunks, standard extraction"
echo ""