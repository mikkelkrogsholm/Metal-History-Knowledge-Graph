#!/bin/bash
# Load entities into Kuzu database using MERGE (no duplicates)

set -e  # Exit on error

echo "🗄️  Loading entities into Kuzu database (MERGE mode)..."

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
ENTITIES_FILE=${1:-"entities_with_embeddings.json"}
DB_PATH=${2:-"metal_history.db"}
VERIFY=${3:-"--verify"}

echo "Parameters:"
echo "  Entities file: $ENTITIES_FILE"
echo "  Database path: $DB_PATH"
echo "  Verify: $VERIFY"
echo "  Mode: MERGE (updates existing, creates new)"
echo ""

# Change to project root
cd "$(dirname "$0")/../.." || exit 1

# Check if entities file exists
if [ ! -f "$ENTITIES_FILE" ]; then
    echo "❌ Entities file not found: $ENTITIES_FILE"
    echo "Run ./05_generate_embeddings.sh first"
    exit 1
fi

# Check if database exists, create if not
if [ ! -d "$DB_PATH" ]; then
    echo "Database not found. Creating new database..."
    cd schema || exit 1
    python initialize_kuzu.py
    cd ..
fi

# Load entities using MERGE
python scripts/automation/load_to_kuzu_merge.py \
    "$ENTITIES_FILE" \
    --db-path "$DB_PATH" \
    $VERIFY

echo ""
echo "✅ Database loading complete (MERGE mode)!"
echo ""
echo "You can now query the database:"
echo "  python -c \"import kuzu; db = kuzu.Database('$DB_PATH'); conn = kuzu.Connection(db); print(conn.execute('MATCH (b:Band) RETURN b.name LIMIT 5').get_as_df())\""
echo ""
echo "🎉 Pipeline complete!"