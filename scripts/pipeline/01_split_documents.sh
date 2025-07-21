#!/bin/bash
# Split history documents into chunks for processing

set -e  # Exit on error

echo "📄 Splitting history documents into chunks..."

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
CHUNK_SIZE=${1:-3000}
OVERLAP=${2:-300}
OUTPUT=${3:-"chunks_optimized.json"}

echo "Parameters:"
echo "  Chunk size: $CHUNK_SIZE"
echo "  Overlap: $OVERLAP"
echo "  Output: $OUTPUT"
echo ""

# Change to history directory
cd "$(dirname "$0")/../../history" || exit 1

# Run text splitter
python text_splitter.py \
    --chunk-size "$CHUNK_SIZE" \
    --overlap "$OVERLAP" \
    --output "$OUTPUT"

# Show results
echo ""
echo "✅ Chunking complete!"
python -c "
import json
with open('$OUTPUT', 'r') as f:
    data = json.load(f)
    print(f\"Total chunks: {data['metadata']['total_chunks']}\")
    for doc, chunks in data['documents'].items():
        print(f\"  {doc}: {len(chunks)} chunks\")
"

echo ""
echo "Next step: ./02_extract_entities.sh"