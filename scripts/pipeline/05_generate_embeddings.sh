#!/bin/bash
# Generate embeddings for all entities

set -e  # Exit on error

echo "🧮 Generating embeddings for entities..."

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

# Check Ollama is running
if ! ollama list >/dev/null 2>&1; then
    echo "❌ Ollama is not running!"
    echo "Please start Ollama first"
    exit 1
fi

# Check embedding model is available
if ! ollama list | grep -q "snowflake-arctic-embed2"; then
    echo "⚠️  Model snowflake-arctic-embed2 not found!"
    echo "Pulling model (this may take a while)..."
    ollama pull snowflake-arctic-embed2:latest
fi

# Default parameters
ENTITIES_FILE=${1:-"data/processed/deduplicated/deduplicated_entities.json"}
OUTPUT_FILE=${2:-"data/processed/embeddings/entities_with_embeddings.json"}

echo "Parameters:"
echo "  Input file: $ENTITIES_FILE"
echo "  Output file: $OUTPUT_FILE"
echo ""

# Change to project root
cd "$(dirname "$0")/../.." || exit 1

# Check if entities file exists
if [ ! -f "$ENTITIES_FILE" ]; then
    echo "❌ Entities file not found: $ENTITIES_FILE"
    echo "Run ./03_deduplicate_entities.sh first"
    exit 1
fi

# Generate embeddings
python scripts/automation/generate_embeddings.py \
    "$ENTITIES_FILE" \
    --output "$OUTPUT_FILE"

# Verify embeddings
echo ""
echo "Verifying embeddings..."
python scripts/automation/generate_embeddings.py \
    "$OUTPUT_FILE" \
    --verify

echo ""
echo "✅ Embeddings generated!"
echo "Output file: $OUTPUT_FILE"
echo ""
echo "Next step: ./06_load_to_kuzu.sh"