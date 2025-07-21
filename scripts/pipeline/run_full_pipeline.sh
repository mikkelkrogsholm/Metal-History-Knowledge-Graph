#!/bin/bash
# Run the complete Metal History extraction pipeline

set -e  # Exit on error

echo "🚀 Running Metal History Full Pipeline"
echo "======================================"
echo ""

# Get project root directory
PROJECT_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"

# Activate virtual environment if not already active
if [ -z "$VIRTUAL_ENV" ]; then
    if [ -f "$PROJECT_ROOT/venv/bin/activate" ]; then
        echo "Activating virtual environment..."
        source "$PROJECT_ROOT/venv/bin/activate"
    else
        echo "❌ Virtual environment not found at $PROJECT_ROOT/venv"
        echo "Please create it first: python -m venv venv"
        exit 1
    fi
fi

# Check Claude CLI is available
if ! command -v claude >/dev/null 2>&1; then
    echo "❌ Claude CLI not found!"
    echo "Please install Claude Code from https://claude.ai/code"
    exit 1
fi

# Parse command line arguments
TEST_MODE=false
SKIP_STEPS=""
CHUNK_LIMIT=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --test)
            TEST_MODE=true
            # Check if next argument is a number
            if [[ $# -gt 1 && "$2" =~ ^[0-9]+$ ]]; then
                CHUNK_LIMIT="$2"
                shift 2
            else
                CHUNK_LIMIT=${CHUNK_LIMIT:-5}  # Default to 5 if not set
                shift
            fi
            ;;
        --chunks)
            CHUNK_LIMIT="$2"
            shift 2
            ;;
        --skip)
            SKIP_STEPS="$2"
            shift 2
            ;;
        --help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --test [N]    Run in test mode (default: 5 chunks)"
            echo "  --chunks N    Process only N chunks (e.g., --chunks 10)"
            echo "  --skip STEPS  Skip steps (comma-separated: split,extract,dedupe,validate,embed,load)"
            echo "  --help        Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0 --test                    # Quick test with 5 chunks"
            echo "  $0 --test 10                 # Test with 10 chunks"
            echo "  $0 --chunks 20               # Process 20 chunks"
            echo "  $0 --chunks 10 --skip embed  # 10 chunks, skip embeddings"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Set default limit for test mode
LIMIT=${CHUNK_LIMIT:-5}

# Set script directory
SCRIPT_DIR="$(dirname "$0")"

# Function to check if step should be skipped
should_skip() {
    [[ ",$SKIP_STEPS," == *",$1,"* ]]
}

# Start timer
START_TIME=$(date +%s)

# Step 1: Split documents
if ! should_skip "split"; then
    echo "Step 1/6: Splitting documents..."
    echo "---------------------------------"
    "$SCRIPT_DIR/01_split_documents.sh"
    echo ""
else
    echo "Skipping document splitting..."
fi

# Step 2: Extract entities
if ! should_skip "extract"; then
    echo "Step 2/6: Extracting entities..."
    echo "---------------------------------"
    if [ -n "$CHUNK_LIMIT" ]; then
        echo "📊 Processing $CHUNK_LIMIT chunks"
        "$SCRIPT_DIR/02_extract_entities.sh" "$CHUNK_LIMIT"
    else
        echo "📊 Processing all chunks"
        "$SCRIPT_DIR/02_extract_entities.sh"
    fi
    echo ""
else
    echo "Skipping entity extraction..."
fi

# Step 3: Deduplicate entities
if ! should_skip "dedupe"; then
    echo "Step 3/6: Deduplicating entities..."
    echo "-----------------------------------"
    "$SCRIPT_DIR/03_deduplicate_entities.sh"
    echo ""
else
    echo "Skipping deduplication..."
fi

# Step 4: Validate entities
if ! should_skip "validate"; then
    echo "Step 4/6: Validating entities..."
    echo "--------------------------------"
    "$SCRIPT_DIR/04_validate_entities.sh"
    echo ""
else
    echo "Skipping validation..."
fi

# Step 5: Generate embeddings
if ! should_skip "embed"; then
    echo "Step 5/6: Generating embeddings..."
    echo "----------------------------------"
    "$SCRIPT_DIR/05_generate_embeddings.sh"
    echo ""
else
    echo "Skipping embedding generation..."
fi

# Step 6: Load to Kuzu
if ! should_skip "load"; then
    echo "Step 6/6: Loading to Kuzu database (MERGE mode)..."
    echo "------------------------------------"
    "$SCRIPT_DIR/06_load_to_kuzu_merge.sh"
    echo ""
else
    echo "Skipping database loading..."
fi

# Calculate elapsed time
END_TIME=$(date +%s)
ELAPSED=$((END_TIME - START_TIME))
MINUTES=$((ELAPSED / 60))
SECONDS=$((ELAPSED % 60))

# Print summary
echo "======================================"
echo "✅ Pipeline Complete!"
echo "======================================"
echo "Total time: ${MINUTES}m ${SECONDS}s"
echo ""
echo "Output files:"
echo "  - data/processed/chunks/chunks_optimized.json"
echo "  - data/processed/extracted/"
echo "  - data/processed/deduplicated/deduplicated_entities.json"
echo "  - data/processed/deduplicated/validation_report.json"
echo "  - data/processed/embeddings/entities_with_embeddings.json"
echo "  - data/database/metal_history.db"
echo ""
echo "Query the database with:"
echo "  python"
echo "  >>> import kuzu"
echo "  >>> db = kuzu.Database('data/database/metal_history.db')"
echo "  >>> conn = kuzu.Connection(db)"
echo "  >>> result = conn.execute('MATCH (b:Band) RETURN b.name LIMIT 10')"
echo "  >>> print(result.get_as_df())"