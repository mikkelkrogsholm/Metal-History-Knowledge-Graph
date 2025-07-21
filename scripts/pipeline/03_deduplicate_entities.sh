#!/bin/bash
# Deduplicate extracted entities using fuzzy matching

set -e  # Exit on error

echo "🔄 Deduplicating extracted entities..."

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
INPUT_DIR=${1:-"data/processed/extracted"}
OUTPUT=${2:-"data/processed/deduplicated/deduplicated_entities.json"}

echo "Parameters:"
echo "  Input directory: $INPUT_DIR"
echo "  Output file: $OUTPUT"
echo ""

# Change to project root
cd "$(dirname "$0")/../.." || exit 1

# Check if extraction output exists
if [ ! -d "$INPUT_DIR" ]; then
    echo "❌ Input directory not found: $INPUT_DIR"
    echo "Run ./02_extract_entities.sh first"
    exit 1
fi

# Combine all chunk entities into single file with preprocessing
echo "Combining and preprocessing chunk entities..."
python -c "
import json
import os
from pathlib import Path
from collections import defaultdict

input_dir = Path('$INPUT_DIR')
all_entities = {
    'bands': [], 'people': [], 'albums': [], 'songs': [],
    'subgenres': [], 'locations': [], 'venues': [], 
    'events': [], 'movements': [], 'studios': [], 'labels': [],
    'equipment': [], 'relationships': []
}
metadata = {'chunks_processed': 0}

# Read all chunk entity files
for chunk_file in input_dir.glob('chunk_*_entities.json'):
    with open(chunk_file, 'r') as f:
        chunk_data = json.load(f)
        for entity_type, entities in chunk_data.items():
            if entity_type in all_entities:
                all_entities[entity_type].extend(entities)
        metadata['chunks_processed'] += 1

# Extract locations from bands if not many locations found
if len(all_entities['locations']) < 10:
    print('Extracting locations from band data...')
    location_map = {}
    
    for band in all_entities['bands']:
        origin_location = band.get('origin_location', '')
        if origin_location:
            parts = [p.strip() for p in origin_location.split(',')]
            
            if len(parts) >= 2:
                city = parts[0]
                country = parts[-1]
                region = parts[1] if len(parts) > 2 else None
                
                loc_key = f'{city}|{country}'
                if loc_key not in location_map:
                    location_map[loc_key] = {
                        'city': city,
                        'country': country,
                        'region': region,
                        'scene_description': f'Metal scene in {city}',
                        'cultural_context': f'Home to bands: {band["name"]}',
                        '_metadata': band.get('_metadata', {})
                    }
                else:
                    # Update context
                    context = location_map[loc_key]['cultural_context']
                    if band['name'] not in context:
                        location_map[loc_key]['cultural_context'] += f', {band["name"]}'
            elif len(parts) == 1 and parts[0]:
                # Just city or country
                loc_key = parts[0]
                if loc_key not in location_map:
                    location_map[loc_key] = {
                        'city': parts[0],
                        'country': '',
                        'scene_description': f'Metal scene in {parts[0]}',
                        'cultural_context': f'Home to bands: {band["name"]}',
                        '_metadata': band.get('_metadata', {})
                    }
    
    # Add extracted locations
    all_entities['locations'].extend(list(location_map.values()))
    print(f'Extracted {len(location_map)} locations from band data')

# Save combined file
with open('data/processed/extracted/combined_entities.json', 'w') as f:
    json.dump({
        'entities': all_entities,
        'metadata': metadata
    }, f, indent=2)

print(f\"Combined {metadata['chunks_processed']} chunk files\")
"

# Run deduplication with preprocessing
echo ""
echo "Running deduplication and preprocessing..."
python -c "
import json
import sys
from pathlib import Path
from collections import defaultdict
sys.path.append(str(Path('$PROJECT_ROOT')))
from src.pipeline.extraction_pipeline import EntityDeduplicator, FuzzyMatcher

# Load combined entities
with open('data/processed/extracted/combined_entities.json', 'r') as f:
    data = json.load(f)

# Initialize fuzzy matcher and deduplicator
fuzzy_matcher = FuzzyMatcher(similarity_threshold=0.85)
deduplicator = EntityDeduplicator(fuzzy_matcher)

# Process each entity type
for entity_type, entities in data['entities'].items():
    for entity in entities:
        chunk_id = entity.get('_metadata', {}).get('chunk_id', 'unknown')
        deduplicator.add_entity(entity_type, entity, chunk_id)

# Build results in same format as extraction pipeline
results = {
    'metadata': {
        'total_entities': 0,
        'chunks_processed': data['metadata']['chunks_processed']
    },
    'entities': defaultdict(list)
}

# Convert entity groups to final format with preprocessing
for entity_type, groups in deduplicator.entity_groups.items():
    entities = []
    for group in groups:
        entity_data = group.original_data.copy()
        entity_data['_metadata'] = {
            'variations': list(group.variations),
            'source_chunks': list(group.source_chunks)
        }
        
        # Preprocess based on entity type
        if entity_type == 'bands':
            # Parse origin_location
            origin_location = entity_data.get('origin_location', '')
            if origin_location:
                parts = [p.strip() for p in origin_location.split(',')]
                if len(parts) >= 2:
                    entity_data['origin_city'] = parts[0]
                    entity_data['origin_country'] = parts[-1]
                elif len(parts) == 1:
                    entity_data['origin_city'] = parts[0]
                    entity_data['origin_country'] = ''
        
        elif entity_type == 'people':
            # Map roles to instruments
            roles = entity_data.get('roles', [])
            instruments = entity_data.get('instruments', [])
            
            if roles and not instruments:
                role_map = {
                    'guitarist': 'guitar', 'bassist': 'bass', 
                    'drummer': 'drums', 'vocalist': 'vocals',
                    'singer': 'vocals', 'keyboardist': 'keyboards'
                }
                for role in roles:
                    mapped = role_map.get(role.lower(), role)
                    if mapped not in instruments:
                        instruments.append(mapped)
                entity_data['instruments'] = instruments
        
        elif entity_type == 'albums':
            # Store band/artist info for relationships
            band_name = entity_data.get('band_name') or entity_data.get('artist')
            if band_name:
                entity_data['_band_name'] = band_name
        
        elif entity_type == 'songs':
            # Store album/artist info for relationships
            entity_data['_album'] = entity_data.get('album') or entity_data.get('album_title')
            entity_data['_artist'] = entity_data.get('artist') or entity_data.get('band_name')
        
        elif entity_type == 'subgenres':
            # Map originated_year to era_start
            if not entity_data.get('era_start') and entity_data.get('originated_year'):
                entity_data['era_start'] = entity_data['originated_year']
            
            # Convert characteristics list to string
            chars = entity_data.get('characteristics', [])
            if isinstance(chars, list) and chars:
                entity_data['key_characteristics'] = ', '.join(chars)
        
        entities.append(entity_data)
    
    results['entities'][entity_type] = entities
    results['metadata']['total_entities'] += len(entities)

# Infer additional relationships
print('Inferring relationships...')
inferred_rels = []

# Person -> Band relationships
for person in results['entities'].get('people', []):
    for band_name in person.get('associated_bands', []):
        rel = {
            'type': 'MEMBER_OF',
            'from_entity_type': 'person',
            'from_entity_name': person['name'],
            'to_entity_type': 'band',
            'to_entity_name': band_name,
            'role': person['instruments'][0] if person.get('instruments') else 'member',
            'context': 'Inferred from associated_bands'
        }
        inferred_rels.append(rel)

# Band -> Album relationships
for album in results['entities'].get('albums', []):
    if album.get('_band_name'):
        rel = {
            'type': 'RELEASED',
            'from_entity_type': 'band',
            'from_entity_name': album['_band_name'],
            'to_entity_type': 'album',
            'to_entity_name': album['title'],
            'year': album.get('release_year'),
            'context': 'Inferred from album data'
        }
        inferred_rels.append(rel)

# Add inferred relationships
if 'relationships' not in results['entities']:
    results['entities']['relationships'] = []
results['entities']['relationships'].extend(inferred_rels)
print(f'Added {len(inferred_rels)} inferred relationships')

# Convert defaultdict to regular dict for JSON serialization
results['entities'] = dict(results['entities'])

# Save results
with open('$OUTPUT', 'w') as f:
    json.dump(results, f, indent=2)

print(f\"\\nDeduplication complete!\")
print(f\"Total unique entities: {results['metadata']['total_entities']}\")
"

cd ..

# Show results
echo ""
echo "✅ Deduplication complete!"
python -c "
import json
with open('$OUTPUT', 'r') as f:
    data = json.load(f)
    print(f\"Total unique entities: {data['metadata']['total_entities']}\")
    for entity_type, entities in data['entities'].items():
        if entities:
            print(f\"  {entity_type}: {len(entities)}\")
"

# Clean up temporary file
# Keep combined_entities.json for reference
# rm -f data/processed/extracted/combined_entities.json

echo ""
echo "Next step: ./04_validate_entities.sh"