#!/bin/bash
# Extract entities using Claude Code CLI - MUCH faster than Ollama!

set -e

echo "🚀 Entity Extraction with Claude Code CLI"
echo "========================================"
echo "This uses Claude's API instead of local Ollama - expect 5-10x speedup!"
echo

# Check if claude CLI is available
if ! command -v claude &> /dev/null; then
    echo "❌ Claude Code CLI not found!"
    echo "Please install: https://claude.ai/code"
    exit 1
fi

# Activate virtual environment
source venv/bin/activate

# Parameters
CHUNKS_FILE=${1:-"history/chunks_optimized.json"}
OUTPUT_DIR=${2:-"claude_extraction_output"}
LIMIT=${3:-""}

echo "Parameters:"
echo "  Chunks file: $CHUNKS_FILE"
echo "  Output directory: $OUTPUT_DIR"
echo "  Limit: ${LIMIT:-all chunks}"
echo

# Create output directory
mkdir -p "$OUTPUT_DIR"

# Run extraction
if [ -n "$LIMIT" ]; then
    python extraction/claude_cli_extraction.py \
        --chunks "$CHUNKS_FILE" \
        --output-dir "$OUTPUT_DIR" \
        --limit "$LIMIT"
else
    python extraction/claude_cli_extraction.py \
        --chunks "$CHUNKS_FILE" \
        --output-dir "$OUTPUT_DIR"
fi

echo
echo "✅ Extraction complete!"
echo "Output saved to: $OUTPUT_DIR"

# Count entities
echo
echo "Entity counts:"
python -c "
import json
import os
from pathlib import Path

output_dir = Path('$OUTPUT_DIR')
total_entities = {'bands': 0, 'people': 0, 'albums': 0, 'songs': 0}

for file in output_dir.glob('chunk_*_entities.json'):
    with open(file, 'r') as f:
        data = json.load(f)
        for entity_type in total_entities:
            if entity_type in data:
                total_entities[entity_type] += len(data[entity_type])

for entity_type, count in total_entities.items():
    print(f'  {entity_type}: {count}')
"