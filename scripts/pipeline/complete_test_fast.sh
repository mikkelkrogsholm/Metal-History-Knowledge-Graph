#!/bin/bash
# Complete fast test of pipeline with mock data

set -e  # Exit on error

echo "🧪 Complete fast pipeline test with mock data..."
echo ""

# Get project root directory
PROJECT_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"

# Activate virtual environment if not already active
if [ -z "$VIRTUAL_ENV" ]; then
    if [ -f "$PROJECT_ROOT/venv/bin/activate" ]; then
        source "$PROJECT_ROOT/venv/bin/activate"
    fi
fi

cd "$PROJECT_ROOT"

# Clean up previous runs
echo "Cleaning up previous runs..."
rm -rf batch_extraction_output/ *.json schema/metal_history.db metal_history.db

# Step 1: Create chunks file
echo "Step 1: Creating mock chunks file..."
cat > chunks_optimized.json << 'EOF'
{
  "metadata": {
    "chunk_size": 3000,
    "chunk_overlap": 300,
    "total_documents": 1,
    "total_chunks": 2
  },
  "documents": {
    "test.md": [
      {
        "id": "test_001",
        "source_file": "test.md",
        "chunk_index": 0,
        "text": "Black Sabbath formed in Birmingham in 1968. Tony Iommi played guitar.",
        "start_char": 0,
        "end_char": 70,
        "char_count": 70,
        "word_count": 11
      },
      {
        "id": "test_002",
        "source_file": "test.md",
        "chunk_index": 1,
        "text": "Iron Maiden formed in London in 1975. Black Sabbath released Paranoid in 1970.",
        "start_char": 70,
        "end_char": 150,
        "char_count": 80,
        "word_count": 13
      }
    ]
  }
}
EOF
echo "✅ Chunks file created"

# Step 2: Create mock extraction output
echo ""
echo "Step 2: Creating mock extraction output..."
mkdir -p batch_extraction_output

cat > batch_extraction_output/chunk_test_001_entities.json << 'EOF'
{
  "bands": [
    {
      "name": "Black Sabbath",
      "formed_year": 1968,
      "origin_location": "Birmingham, UK",
      "_metadata": {"source_file": "test.md", "chunk_id": "test_001"}
    }
  ],
  "people": [
    {
      "name": "Tony Iommi",
      "roles": ["guitarist"],
      "_metadata": {"source_file": "test.md", "chunk_id": "test_001"}
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

cat > batch_extraction_output/chunk_test_002_entities.json << 'EOF'
{
  "bands": [
    {
      "name": "Iron Maiden",
      "formed_year": 1975,
      "origin_location": "London, UK",
      "_metadata": {"source_file": "test.md", "chunk_id": "test_002"}
    },
    {
      "name": "Black Sabbath",
      "formed_year": 1968,
      "_metadata": {"source_file": "test.md", "chunk_id": "test_002"}
    }
  ],
  "people": [],
  "albums": [
    {
      "title": "Paranoid",
      "band_name": "Black Sabbath",
      "release_year": 1970,
      "_metadata": {"source_file": "test.md", "chunk_id": "test_002"}
    }
  ],
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

echo "✅ Mock extraction complete"

# Step 3: Deduplication
echo ""
echo "Step 3: Deduplicating entities..."
./scripts/pipeline/03_deduplicate_entities.sh

# Step 4: Validation
echo ""
echo "Step 4: Validating entities..."
./scripts/pipeline/04_validate_entities.sh

# Step 5: Skip embeddings
echo ""
echo "Step 5: Skipping embeddings (copying deduplicated)..."
cp deduplicated_entities.json entities_with_embeddings.json

# Step 6: Load to database
echo ""
echo "Step 6: Loading to Kuzu database..."
./scripts/pipeline/06_load_to_kuzu.sh

# Step 7: Query the database
echo ""
echo "Step 7: Querying database..."
python -c "
import kuzu
db = kuzu.Database('schema/metal_history.db')
conn = kuzu.Connection(db)

print('\\nBands in database:')
result = conn.execute('MATCH (b:Band) RETURN b.name, b.formed_year')
while result.has_next():
    row = result.get_next()
    print(f'  - {row[0]} ({row[1]})')

print('\\nPeople in database:')
result = conn.execute('MATCH (p:Person) RETURN p.name')
while result.has_next():
    row = result.get_next()
    print(f'  - {row[0]}')

print('\\nAlbums in database:')
result = conn.execute('MATCH (a:Album) RETURN a.title')
while result.has_next():
    row = result.get_next()
    print(f'  - {row[0]}')
"

echo ""
echo "🎉 Complete pipeline test successful!"