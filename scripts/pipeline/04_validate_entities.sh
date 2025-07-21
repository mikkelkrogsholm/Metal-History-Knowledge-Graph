#!/bin/bash
# Validate extracted entities for quality and consistency

set -e  # Exit on error

echo "✅ Validating extracted entities..."

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
ENTITIES_FILE=${1:-"data/processed/deduplicated/deduplicated_entities.json"}
REPORT_FILE=${2:-"data/processed/deduplicated/validation_report.json"}

echo "Parameters:"
echo "  Entities file: $ENTITIES_FILE"
echo "  Report file: $REPORT_FILE"
echo ""

# Change to project root
cd "$(dirname "$0")/../.." || exit 1

# Check if entities file exists
if [ ! -f "$ENTITIES_FILE" ]; then
    echo "❌ Entities file not found: $ENTITIES_FILE"
    echo "Run ./03_deduplicate_entities.sh first"
    exit 1
fi

# Run validation
python scripts/automation/entity_validation.py \
    "$ENTITIES_FILE" \
    --output "$REPORT_FILE"

# Check quality score
echo ""
QUALITY_SCORE=$(python -c "
import json
with open('$REPORT_FILE', 'r') as f:
    report = json.load(f)
    print(report['quality_score'])
")

if python3 -c "import sys; sys.exit(0 if $QUALITY_SCORE >= 70 else 1)" 2>/dev/null; then
    echo "✅ Quality score: $QUALITY_SCORE/100"
else
    echo "⚠️  Warning: Quality score is low ($QUALITY_SCORE/100)"
    echo "Review validation report for issues: $REPORT_FILE"
fi

echo ""
echo "Next step: ./05_generate_embeddings.sh"