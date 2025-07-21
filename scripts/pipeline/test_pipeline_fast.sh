#!/bin/bash
# Test pipeline with mock data to verify pipeline flow works

set -e  # Exit on error

echo "🧪 Testing pipeline flow with mock data..."

# Get project root directory
PROJECT_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"

# Activate virtual environment if not already active
if [ -z "$VIRTUAL_ENV" ]; then
    if [ -f "$PROJECT_ROOT/venv/bin/activate" ]; then
        source "$PROJECT_ROOT/venv/bin/activate"
    fi
fi

cd "$PROJECT_ROOT"

# Create mock extraction output
echo "Creating mock extraction data..."
mkdir -p batch_extraction_output

# Create mock entity files
cat > batch_extraction_output/chunk_test_001_entities.json << 'EOF'
{
  "bands": [
    {
      "name": "Black Sabbath",
      "formed_year": 1968,
      "origin_location": "Birmingham, UK",
      "genres": ["heavy metal", "doom metal"],
      "_metadata": {
        "source_file": "test.md",
        "chunk_id": "test_001"
      }
    }
  ],
  "people": [
    {
      "name": "Tony Iommi",
      "roles": ["guitarist"],
      "birth_year": 1948,
      "_metadata": {
        "source_file": "test.md",
        "chunk_id": "test_001"
      }
    }
  ],
  "albums": [
    {
      "title": "Paranoid",
      "band_name": "Black Sabbath",
      "release_year": 1970,
      "_metadata": {
        "source_file": "test.md",
        "chunk_id": "test_001"
      }
    }
  ],
  "songs": [],
  "subgenres": [
    {
      "name": "Heavy Metal",
      "originated_year": 1970,
      "characteristics": ["distorted guitars", "heavy riffs"],
      "_metadata": {
        "source_file": "test.md",
        "chunk_id": "test_001"
      }
    }
  ],
  "locations": [
    {
      "city": "Birmingham",
      "country": "UK",
      "significance": "Birthplace of heavy metal",
      "_metadata": {
        "source_file": "test.md",
        "chunk_id": "test_001"
      }
    }
  ],
  "events": [],
  "equipment": [],
  "studios": [],
  "labels": [],
  "relationships": []
}
EOF

cat > batch_extraction_output/chunk_test_002_entities.json << 'EOF'
{
  "bands": [
    {
      "name": "Black Sabbath",
      "formed_year": 1968,
      "origin_location": "Birmingham, England",
      "genres": ["heavy metal"],
      "_metadata": {
        "source_file": "test.md",
        "chunk_id": "test_002"
      }
    },
    {
      "name": "Iron Maiden",
      "formed_year": 1975,
      "origin_location": "London, UK",
      "_metadata": {
        "source_file": "test.md",
        "chunk_id": "test_002"
      }
    }
  ],
  "people": [
    {
      "name": "Ozzy Osbourne",
      "roles": ["vocalist"],
      "birth_year": 1948,
      "_metadata": {
        "source_file": "test.md",
        "chunk_id": "test_002"
      }
    }
  ],
  "albums": [],
  "songs": [],
  "subgenres": [],
  "locations": [],
  "events": [],
  "equipment": [],
  "studios": [],
  "labels": [],
  "relationships": []
}
EOF

echo "✅ Mock data created"

# Run deduplication
echo ""
echo "Step 3: Deduplicating entities..."
./scripts/pipeline/03_deduplicate_entities.sh

# Run validation
echo ""
echo "Step 4: Validating entities..."
./scripts/pipeline/04_validate_entities.sh

# Skip embedding generation for speed
echo ""
echo "Step 5: Skipping embeddings (using entities without embeddings)..."
cp deduplicated_entities.json entities_with_embeddings.json

# Load to database
echo ""
echo "Step 6: Loading to Kuzu..."
./scripts/pipeline/06_load_to_kuzu.sh entities_with_embeddings.json metal_history.db --no-verify

echo ""
echo "✅ Pipeline test complete!"