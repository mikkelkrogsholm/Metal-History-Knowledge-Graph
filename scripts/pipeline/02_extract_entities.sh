#!/bin/bash
# Extract entities from chunks using Claude Code CLI

set -e  # Exit on error

echo "🔍 Extracting entities from chunks using Claude CLI..."
echo "🚀 This uses Claude's API for fast, high-quality extraction"

# Get project root directory
PROJECT_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"

# Check if claude CLI is available
if ! command -v claude &> /dev/null; then
    echo "❌ Claude Code CLI not found!"
    echo "Please install: https://claude.ai/code"
    exit 1
fi

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
LIMIT=${1:-""}
OUTPUT_DIR=${2:-"data/processed/extracted"}
CHUNKS_FILE=${3:-"data/processed/chunks/chunks_optimized.json"}

echo "Parameters:"
echo "  Chunks file: $CHUNKS_FILE"
echo "  Output directory: $OUTPUT_DIR"
if [ -n "$LIMIT" ]; then
    echo "  Limit: $LIMIT chunks"
else
    echo "  Limit: Process all chunks"
fi
echo ""

# Change to project root
cd "$(dirname "$0")/../.." || exit 1

# Run extraction using Claude CLI
if [ -n "$LIMIT" ]; then
    python src/extraction/claude_cli_extraction.py \
        --chunks "$CHUNKS_FILE" \
        --output-dir "$OUTPUT_DIR" \
        --limit "$LIMIT"
else
    python src/extraction/claude_cli_extraction.py \
        --chunks "$CHUNKS_FILE" \
        --output-dir "$OUTPUT_DIR"
fi

echo ""
echo "✅ Extraction complete!"
echo "Output directory: $OUTPUT_DIR/"
echo ""
echo "Next step: ./03_deduplicate_entities.sh"