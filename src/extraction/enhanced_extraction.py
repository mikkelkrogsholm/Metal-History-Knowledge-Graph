#!/usr/bin/env python3
"""
Enhanced entity extraction using Claude Code CLI
"""

import json
import subprocess
from typing import List
from .extraction_schemas import ExtractionResult
from .prompts import segment_by_sections
import asyncio
from tqdm import tqdm

def extract_entities_enhanced(text: str) -> ExtractionResult:
    """
    Enhanced extraction with more specific prompting
    """
    # Create a more detailed prompt
    enhanced_prompt = f"""You are an expert at extracting structured information from metal music history texts.

Extract ALL entities and relationships from the following text. Be very thorough and include:

1. BANDS: Extract band names, formation years, cities of origin, and descriptions
2. PEOPLE: Extract musician names, their instruments (guitar, bass, drums, vocals), and associated bands
3. ALBUMS: Extract album titles, artists, release years/dates, labels, and studios
4. SONGS: Extract song titles, artists, albums they appear on, and BPM if mentioned
5. SUBGENRES: Extract genre names, era ranges, BPM ranges, tunings, vocal styles, and characteristics
6. LOCATIONS: Extract cities, regions, countries, and descriptions of local scenes
7. EVENTS: Extract event names, dates, types (festival/controversy/movement), and descriptions
8. EQUIPMENT: Extract equipment names (pedals, guitars, amps), types, and specifications
9. STUDIOS: Extract studio names, locations, and what they're famous for
10. LABELS: Extract record label names and founding years
11. RELATIONSHIPS: Extract all relationships between entities (who played in which band, which album was released by which band, where bands formed, etc.)

For dates, use YYYY-MM-DD format when full date is known, otherwise just YYYY.
For missing information, use null rather than guessing.

Text to analyze:
{text}

Extract thoroughly - don't miss any entities!"""

    try:
        # Add JSON schema to prompt
        full_prompt = enhanced_prompt + f"\n\nRespond with ONLY a valid JSON object matching this schema:\n{json.dumps(ExtractionResult.model_json_schema(), indent=2)}"
        
        # Use Claude CLI for extraction
        result = subprocess.run(
            ['claude', '-p', full_prompt, '--output-format', 'json'],
            capture_output=True,
            text=True,
            check=True
        )
        
        # Parse the JSON response
        response_data = json.loads(result.stdout)
        
        if isinstance(response_data, dict) and 'result' in response_data:
            content = response_data['result']
            if isinstance(content, str):
                # Strip markdown code blocks if present
                content = content.strip()
                if content.startswith('```json'):
                    content = content[7:]
                if content.startswith('```'):
                    content = content[3:]
                if content.endswith('```'):
                    content = content[:-3]
                content = content.strip()
                
                extracted_data = json.loads(content)
                return ExtractionResult.model_validate(extracted_data)
        
        return ExtractionResult()
        
    except Exception as e:
        print(f"Error: {e}")
        return ExtractionResult()

def batch_extract_document(limit: int = None):
    """
    Extract entities from the entire document with progress tracking
    """
    # Read document
    with open('../history/history_from_claude.md', 'r') as f:
        full_text = f.read()
    
    # Segment document
    segments = segment_by_sections(full_text)
    
    # Filter substantial segments
    substantial_segments = [s for s in segments if s['char_count'] > 300]
    
    if limit:
        substantial_segments = substantial_segments[:limit]
    
    print(f"\nProcessing {len(substantial_segments)} segments...")
    
    all_entities = {
        'bands': [],
        'people': [],
        'albums': [],
        'songs': [],
        'subgenres': [],
        'locations': [],
        'events': [],
        'equipment': [],
        'studios': [],
        'labels': [],
        'relationships': []
    }
    
    # Process each segment with progress bar
    for seg in tqdm(substantial_segments, desc="Extracting entities"):
        try:
            result = extract_entities_enhanced(seg['text'])
            
            # Aggregate results
            result_dict = result.model_dump()
            for key in all_entities:
                all_entities[key].extend(result_dict.get(key, []))
            
            # Add segment tracking to relationships
            for rel in result_dict.get('relationships', []):
                rel['source_segment'] = seg['id']
                
        except Exception as e:
            print(f"\nError in segment {seg['id']}: {e}")
    
    # Summary statistics
    print("\n" + "="*60)
    print("EXTRACTION SUMMARY")
    print("="*60)
    for entity_type, entities in all_entities.items():
        if entities:
            print(f"{entity_type.upper()}: {len(entities)} extracted")
            # Show first 3 examples
            for entity in entities[:3]:
                if isinstance(entity, dict):
                    name = entity.get('name', entity.get('title', str(entity)))
                    print(f"  - {name}")
    
    # Save complete results
    output_file = 'complete_extraction_results.json'
    with open(output_file, 'w') as f:
        json.dump({
            'metadata': {
                'total_segments': len(substantial_segments),
                'extraction_model': 'magistral:24b',
                'schema_version': '1.0'
            },
            'entities': all_entities
        }, f, indent=2)
    
    print(f"\nComplete results saved to {output_file}")
    
    # Also save deduplicated entities
    deduplicated = deduplicate_entities(all_entities)
    with open('deduplicated_entities.json', 'w') as f:
        json.dump(deduplicated, f, indent=2)
    print(f"Deduplicated entities saved to deduplicated_entities.json")
    
    return all_entities

def deduplicate_entities(entities: dict) -> dict:
    """
    Remove duplicate entities based on name/title
    """
    deduplicated = {}
    
    for entity_type, entity_list in entities.items():
        if entity_type == 'relationships':
            # Don't deduplicate relationships
            deduplicated[entity_type] = entity_list
            continue
            
        seen = set()
        unique_entities = []
        
        for entity in entity_list:
            # Get identifier (name or title)
            identifier = entity.get('name', entity.get('title', ''))
            
            if identifier and identifier not in seen:
                seen.add(identifier)
                unique_entities.append(entity)
        
        deduplicated[entity_type] = unique_entities
    
    return deduplicated

def test_single_segment():
    """Test on a single rich segment"""
    
    test_text = """The New Wave of British Heavy Metal (1979-1983) transformed metal from underground curiosity to global phenomenon. Emerging from Britain's economic hardship, NWOBHM bands like Iron Maiden, Saxon, and Diamond Head accelerated tempos to 120-160 BPM while maintaining melody within heaviness. The movement's DIY ethos, exemplified by the "Metal for Muthas" compilation (1980), spawned an estimated 1,000+ bands. Iron Maiden's galloping rhythms, twin guitar harmonies, and theatrical stage shows on albums like The Number of the Beast (1982) became the genre's gold standard."""
    
    print("Testing enhanced extraction on single segment...")
    result = extract_entities_enhanced(test_text)
    
    print("\nExtraction Results:")
    result_dict = result.model_dump()
    
    for entity_type, entities in result_dict.items():
        if entities:
            print(f"\n{entity_type.upper()}: {len(entities)}")
            for entity in entities:
                if isinstance(entity, dict):
                    print(f"  {entity}")
    
    with open('enhanced_test_result.json', 'w') as f:
        json.dump(result_dict, f, indent=2)
    print("\nSaved to enhanced_test_result.json")

if __name__ == "__main__":
    import sys
    import argparse
    
    if 'venv' not in sys.prefix:
        print("WARNING: Virtual environment not activated!")
        print("Run: source venv/bin/activate")
        sys.exit(1)
    
    parser = argparse.ArgumentParser(description='Extract entities from metal history document')
    parser.add_argument('--test', action='store_true', help='Run test on single segment')
    parser.add_argument('--limit', type=int, help='Limit number of segments to process')
    parser.add_argument('--full', action='store_true', help='Process entire document')
    
    args = parser.parse_args()
    
    print("Enhanced Metal History Entity Extraction")
    print("="*60)
    
    if args.test:
        print("\nTesting single segment...")
        test_single_segment()
    elif args.full:
        print("\nProcessing full document...")
        batch_extract_document()
    else:
        limit = args.limit or 5
        print(f"\nProcessing first {limit} segments...")
        batch_extract_document(limit=limit)