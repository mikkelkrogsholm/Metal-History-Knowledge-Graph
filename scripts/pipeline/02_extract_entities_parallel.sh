#!/bin/bash
# Extract entities from chunks using parallel processing

set -e  # Exit on error

echo "🔍 Extracting entities from chunks (parallel mode)..."

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

# Default parameters
CHUNKS_FILE=${1:-"chunks_optimized.json"}
LIMIT=${2:-""}
WORKERS=${3:-"3"}
OUTPUT_DIR=${4:-"batch_extraction_output"}

echo "Parameters:"
echo "  Chunks file: $CHUNKS_FILE"
echo "  Limit: ${LIMIT:-all chunks}"
echo "  Parallel workers: $WORKERS"
echo "  Output directory: $OUTPUT_DIR"
echo ""

# Change to project root
cd "$PROJECT_ROOT" || exit 1

# Check if chunks file exists
if [ ! -f "$CHUNKS_FILE" ]; then
    echo "❌ Chunks file not found: $CHUNKS_FILE"
    echo "Run ./01_split_documents.sh first"
    exit 1
fi

# Create output directory
mkdir -p "$OUTPUT_DIR"

# Prepare limit argument
LIMIT_ARG=""
if [ ! -z "$LIMIT" ]; then
    LIMIT_ARG="--limit $LIMIT"
fi

# Run parallel extraction
echo "Starting parallel extraction..."
python extraction/parallel_extraction.py \
    --chunks "$CHUNKS_FILE" \
    --workers "$WORKERS" \
    --output "$OUTPUT_DIR/parallel_extracted.json" \
    $LIMIT_ARG

# Check if extraction succeeded
if [ -f "$OUTPUT_DIR/parallel_extracted.json" ]; then
    # Convert to format expected by deduplication
    echo ""
    echo "Converting to standard format..."
    python -c "
import json

# Load parallel extraction output
with open('$OUTPUT_DIR/parallel_extracted.json', 'r') as f:
    data = json.load(f)

# Create output in expected format
output = {
    'metadata': {
        'total_entities': sum(len(v) for v in data['entities'].values() if isinstance(v, list)),
        'chunks_processed': data['metadata']['total_chunks'],
        'extraction_time': data['metadata']['total_time'],
        'avg_time_per_chunk': data['metadata']['avg_time_per_chunk']
    },
    'entities': data['entities']
}

# Save in expected location
with open('extracted_entities.json', 'w') as f:
    json.dump(output, f, indent=2)

print(f\"\\n✅ Extraction complete!\")
print(f\"Total entities: {output['metadata']['total_entities']}\")
print(f\"Total time: {data['metadata']['total_time']:.2f}s\")
print(f\"Average per chunk: {data['metadata']['avg_time_per_chunk']:.2f}s\")
print(f\"\\nWith {data['metadata']['parallel_workers']} workers, that's ~{data['metadata']['avg_time_per_chunk'] / data['metadata']['parallel_workers']:.2f}s effective time per chunk!\")
"
    
    echo ""
    echo "✅ Entity extraction complete!"
    echo "Output saved to: extracted_entities.json"
    echo ""
    echo "Next step: ./03_deduplicate_entities.sh"
else
    echo "❌ Extraction failed - no output file created"
    exit 1
fi