#!/bin/bash
# Extract entities from chunks using adaptive parallel processing

set -e  # Exit on error

echo "🔍 Extracting entities with adaptive parallelism..."

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
CHUNKS_FILE=${1:-"history/chunks_optimized.json"}
LIMIT=${2:-""}
WORKERS=${3:-""}  # Empty means auto-detect
OUTPUT_DIR=${4:-"batch_extraction_output"}

# Change to project root
cd "$PROJECT_ROOT" || exit 1

# Profile system if requested
if [ "$1" == "--profile" ]; then
    echo "🖥️  System Profile:"
    python scripts/automation/system_profiler.py
    echo ""
    echo "To see recommended extraction settings:"
    echo "  python scripts/automation/system_profiler.py --json"
    exit 0
fi

# Check dependencies
if ! python -c "import psutil" 2>/dev/null; then
    echo "Installing psutil for resource monitoring..."
    pip install psutil
fi

echo "Parameters:"
echo "  Chunks file: $CHUNKS_FILE"
echo "  Limit: ${LIMIT:-all chunks}"
if [ -z "$WORKERS" ]; then
    echo "  Workers: Auto-detected based on system"
else
    echo "  Workers: $WORKERS (manual override)"
fi
echo "  Output directory: $OUTPUT_DIR"
echo ""

# Check if chunks file exists
if [ ! -f "$CHUNKS_FILE" ]; then
    echo "❌ Chunks file not found: $CHUNKS_FILE"
    echo "Run ./01_split_documents.sh first"
    exit 1
fi

# Create output directory
mkdir -p "$OUTPUT_DIR"

# Prepare arguments
LIMIT_ARG=""
if [ ! -z "$LIMIT" ]; then
    LIMIT_ARG="--limit $LIMIT"
fi

WORKERS_ARG=""
if [ ! -z "$WORKERS" ]; then
    WORKERS_ARG="--workers $WORKERS"
fi

# Show system profile
echo "Analyzing system capabilities..."
python extraction/adaptive_parallel_extraction.py --profile

# Run adaptive extraction
echo ""
echo "Starting adaptive extraction..."
python extraction/adaptive_parallel_extraction.py \
    --chunks "$CHUNKS_FILE" \
    --output "$OUTPUT_DIR/adaptive_extracted.json" \
    $LIMIT_ARG \
    $WORKERS_ARG

# Check if extraction succeeded
if [ -f "$OUTPUT_DIR/adaptive_extracted.json" ]; then
    # Convert to standard format
    echo ""
    echo "Converting to standard format..."
    python -c "
import json

# Load adaptive extraction output
with open('$OUTPUT_DIR/adaptive_extracted.json', 'r') as f:
    data = json.load(f)

# Create output in expected format
output = {
    'metadata': {
        'total_entities': sum(len(v) for v in data['entities'].values() if isinstance(v, list)),
        'chunks_processed': data['metadata']['total_chunks'],
        'extraction_time': data['metadata']['total_time'],
        'avg_time_per_chunk': data['metadata']['avg_time_per_chunk'],
        'system_tier': data['metadata']['system_tier'],
        'workers_used': data['metadata']['parallel_workers'],
        'resource_stats': data['metadata']['resource_stats']
    },
    'entities': data['entities']
}

# Save in expected location
with open('extracted_entities.json', 'w') as f:
    json.dump(output, f, indent=2)

print(f\"\\n✅ Extraction complete!\")
print(f\"System tier: {data['metadata']['system_tier'].upper()}\")
print(f\"Workers used: {data['metadata']['parallel_workers']}\")
print(f\"Total entities: {output['metadata']['total_entities']}\")
print(f\"Total time: {data['metadata']['total_time']:.2f}s\")
print(f\"Average per chunk: {data['metadata']['avg_time_per_chunk']:.2f}s\")

# Show resource usage
stats = data['metadata']['resource_stats']
print(f\"\\nResource usage:\")
print(f\"  Max CPU: {stats['max_cpu_percent']:.1f}%\")
print(f\"  Max Memory: {stats['max_memory_percent']:.1f}%\")
if stats['throttle_events'] > 0:
    print(f\"  ⚠️  Throttled {stats['throttle_events']} times\")
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