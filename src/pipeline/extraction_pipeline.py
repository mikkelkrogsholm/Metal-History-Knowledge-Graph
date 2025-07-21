#!/usr/bin/env python3
"""
Extraction pipeline that processes chunks and handles deduplication
"""

import sys
import os
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.append(str(PROJECT_ROOT))

import json
import ollama
from typing import List, Dict, Set, Tuple, Optional
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from tqdm import tqdm
import argparse
from collections import defaultdict
import hashlib

from src.extraction.extraction_schemas import ExtractionResult, Band, Album, Person
from src.extraction.enhanced_extraction import extract_entities_enhanced

@dataclass
class EntityCandidate:
    """Represents a potential entity match for deduplication"""
    entity_type: str
    name: str
    original_data: dict
    source_chunks: Set[str] = field(default_factory=set)
    variations: Set[str] = field(default_factory=set)
    
    def add_variation(self, name: str, chunk_id: str):
        self.variations.add(name)
        self.source_chunks.add(chunk_id)

class FuzzyMatcher:
    """Handle fuzzy matching of entity names"""
    
    def __init__(self, similarity_threshold: float = 0.85):
        self.similarity_threshold = similarity_threshold
    
    def calculate_similarity(self, s1: str, s2: str) -> float:
        """Calculate similarity between two strings"""
        # Normalize strings
        s1 = s1.lower().strip()
        s2 = s2.lower().strip()
        
        # Exact match
        if s1 == s2:
            return 1.0
        
        # Use SequenceMatcher for fuzzy matching
        return SequenceMatcher(None, s1, s2).ratio()
    
    def are_similar(self, s1: str, s2: str) -> bool:
        """Check if two strings are similar enough"""
        return self.calculate_similarity(s1, s2) >= self.similarity_threshold
    
    def find_best_match(self, name: str, candidates: List[str]) -> Optional[Tuple[str, float]]:
        """Find the best matching candidate for a name"""
        best_match = None
        best_score = 0.0
        
        for candidate in candidates:
            score = self.calculate_similarity(name, candidate)
            if score > best_score and score >= self.similarity_threshold:
                best_score = score
                best_match = candidate
        
        return (best_match, best_score) if best_match else None

class EntityDeduplicator:
    """Handle entity deduplication with LLM disambiguation"""
    
    def __init__(self, fuzzy_matcher: FuzzyMatcher):
        self.fuzzy_matcher = fuzzy_matcher
        self.entity_groups = defaultdict(list)  # type -> list of EntityCandidate
        self.canonical_names = {}  # normalized name -> canonical name
    
    def add_entity(self, entity_type: str, entity_data: dict, chunk_id: str):
        """Add an entity and check for duplicates"""
        name = entity_data.get('name', entity_data.get('title', ''))
        if not name:
            return
        
        # Check for existing similar entities
        existing_group = self._find_similar_group(entity_type, name)
        
        if existing_group:
            # Add to existing group
            existing_group.add_variation(name, chunk_id)
            # Merge data
            self._merge_entity_data(existing_group.original_data, entity_data)
        else:
            # Create new group
            candidate = EntityCandidate(
                entity_type=entity_type,
                name=name,
                original_data=entity_data.copy(),
                source_chunks={chunk_id},
                variations={name}
            )
            self.entity_groups[entity_type].append(candidate)
    
    def _find_similar_group(self, entity_type: str, name: str) -> Optional[EntityCandidate]:
        """Find an existing group that this entity belongs to"""
        for group in self.entity_groups[entity_type]:
            # Check against all variations in the group
            for variation in group.variations:
                if self.fuzzy_matcher.are_similar(name, variation):
                    return group
        return None
    
    def _merge_entity_data(self, existing: dict, new: dict):
        """Merge new entity data into existing - combining all information"""
        for key, value in new.items():
            if value is not None and key != '_metadata':
                if key not in existing or existing[key] is None:
                    # Add new information
                    existing[key] = value
                elif isinstance(value, list) and isinstance(existing[key], list):
                    # Merge lists (e.g., instruments, associated_bands)
                    # Keep all unique items
                    combined = existing[key] + value
                    # Preserve order but remove duplicates
                    seen = set()
                    unique_items = []
                    for item in combined:
                        if item not in seen:
                            seen.add(item)
                            unique_items.append(item)
                    existing[key] = unique_items
                elif key == 'description':
                    # Combine descriptions if they're different
                    if value != existing[key] and value not in existing[key]:
                        existing[key] = f"{existing[key]} {value}"
                elif isinstance(value, (int, float)):
                    # For numeric values, keep the non-None value
                    # If both exist and differ, keep the first one but log it
                    if existing[key] != value:
                        if '_conflicts' not in existing:
                            existing['_conflicts'] = {}
                        existing['_conflicts'][key] = [existing[key], value]
                elif isinstance(value, str):
                    # For strings, if they differ significantly, store both
                    if self.fuzzy_matcher.calculate_similarity(existing[key], value) < 0.9:
                        if '_alternate_values' not in existing:
                            existing['_alternate_values'] = {}
                        if key not in existing['_alternate_values']:
                            existing['_alternate_values'][key] = []
                        if value not in existing['_alternate_values'][key]:
                            existing['_alternate_values'][key].append(value)
    
    async def disambiguate_with_llm(self, candidates: List[EntityCandidate]) -> List[EntityCandidate]:
        """Use LLM to disambiguate similar entities"""
        if len(candidates) < 2:
            return candidates
        
        # Group highly similar entities for LLM review
        groups_to_check = []
        checked = set()
        
        for i, candidate1 in enumerate(candidates):
            if i in checked:
                continue
            
            similar_group = [candidate1]
            checked.add(i)
            
            for j, candidate2 in enumerate(candidates[i+1:], i+1):
                if j in checked:
                    continue
                
                # Check if any variations are similar
                for var1 in candidate1.variations:
                    for var2 in candidate2.variations:
                        if self.fuzzy_matcher.calculate_similarity(var1, var2) > 0.75:
                            similar_group.append(candidate2)
                            checked.add(j)
                            break
            
            if len(similar_group) > 1:
                groups_to_check.append(similar_group)
        
        # Ask LLM about each group
        for group in groups_to_check:
            if len(group) > 1:
                merged = await self._llm_merge_decision(group)
                if merged:
                    # Replace group with merged entity
                    for entity in group[1:]:
                        candidates.remove(entity)
                    group[0].original_data = merged
        
        return candidates
    
    async def _llm_merge_decision(self, similar_entities: List[EntityCandidate]) -> Optional[dict]:
        """Ask LLM if entities should be merged"""
        entity_info = []
        for entity in similar_entities:
            entity_info.append({
                'variations': list(entity.variations),
                'data': entity.original_data,
                'sources': list(entity.source_chunks)
            })
        
        prompt = f"""Are these the same {similar_entities[0].entity_type}? 
Analyze the variations and data to determine if they refer to the same entity.

Entities to compare:
{json.dumps(entity_info, indent=2)}

Respond with JSON:
{{
  "same_entity": true/false,
  "canonical_name": "the correct name if same",
  "merged_data": {{merged entity data}} or null
}}"""

        try:
            response = ollama.generate(
                model='magistral:24b',
                prompt=prompt,
                options={'temperature': 0.1}
            )
            
            result = json.loads(response['response'])
            if result.get('same_entity'):
                return result.get('merged_data')
        except:
            # If LLM fails, don't merge
            pass
        
        return None

class ExtractionPipeline:
    """Main pipeline for processing chunks and extracting entities"""
    
    def __init__(self, chunks_file: str = 'chunks_optimized.json'):
        self.chunks_file = chunks_file
        self.fuzzy_matcher = FuzzyMatcher(similarity_threshold=0.85)
        self.deduplicator = EntityDeduplicator(self.fuzzy_matcher)
        self.relationship_hashes = set()  # Track unique relationships
    
    def load_chunks(self) -> Dict:
        """Load chunks from JSON file"""
        chunks_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'history',
            self.chunks_file
        )
        
        with open(chunks_path, 'r') as f:
            return json.load(f)
    
    def process_chunks(self, limit: Optional[int] = None, 
                      documents: Optional[List[str]] = None) -> Dict:
        """
        Process chunks and extract entities
        
        Args:
            limit: Maximum number of chunks to process (for testing)
            documents: Specific documents to process (if None, process all)
        
        Returns:
            Dictionary with extracted and deduplicated entities
        """
        data = self.load_chunks()
        all_chunks = []
        
        # Collect chunks from specified documents
        for doc_name, chunks in data['documents'].items():
            if documents and doc_name not in documents:
                continue
            all_chunks.extend(chunks)
        
        # Apply limit if specified
        if limit:
            all_chunks = all_chunks[:limit]
        
        print(f"\nProcessing {len(all_chunks)} chunks...")
        
        # Process each chunk
        for chunk in tqdm(all_chunks, desc="Extracting entities"):
            try:
                # Extract entities from chunk
                result = extract_entities_enhanced(chunk['text'])
                
                # Add entities to deduplicator
                self._process_extraction_result(result, chunk['id'])
                
            except Exception as e:
                print(f"\nError processing chunk {chunk['id']}: {e}")
        
        # Get deduplicated results
        return self._get_deduplicated_results()
    
    def _process_extraction_result(self, result: ExtractionResult, chunk_id: str):
        """Process extraction result and add to deduplicator"""
        # Process each entity type
        for band in result.bands:
            self.deduplicator.add_entity('bands', band.model_dump(), chunk_id)
        
        for person in result.people:
            self.deduplicator.add_entity('people', person.model_dump(), chunk_id)
        
        for album in result.albums:
            self.deduplicator.add_entity('albums', album.model_dump(), chunk_id)
        
        for song in result.songs:
            self.deduplicator.add_entity('songs', song.model_dump(), chunk_id)
        
        for subgenre in result.subgenres:
            self.deduplicator.add_entity('subgenres', subgenre.model_dump(), chunk_id)
        
        for location in result.locations:
            self.deduplicator.add_entity('locations', location.model_dump(), chunk_id)
        
        for event in result.events:
            self.deduplicator.add_entity('events', event.model_dump(), chunk_id)
        
        for equipment in result.equipment:
            self.deduplicator.add_entity('equipment', equipment.model_dump(), chunk_id)
        
        for studio in result.studios:
            self.deduplicator.add_entity('studios', studio.model_dump(), chunk_id)
        
        for label in result.labels:
            self.deduplicator.add_entity('labels', label.model_dump(), chunk_id)
        
        # Process relationships (with deduplication)
        for rel in result.relationships:
            rel_hash = self._hash_relationship(rel.model_dump())
            if rel_hash not in self.relationship_hashes:
                self.relationship_hashes.add(rel_hash)
                self.deduplicator.add_entity('relationships', rel.model_dump(), chunk_id)
    
    def _hash_relationship(self, rel: dict) -> str:
        """Create a hash for relationship deduplication"""
        # Create a canonical representation
        key_parts = [
            rel.get('type', ''),
            rel.get('from_entity_type', ''),
            rel.get('from_entity_name', '').lower(),
            rel.get('to_entity_type', ''),
            rel.get('to_entity_name', '').lower()
        ]
        key = '|'.join(key_parts)
        return hashlib.md5(key.encode()).hexdigest()
    
    def _get_deduplicated_results(self) -> Dict:
        """Get final deduplicated results"""
        results = {
            'metadata': {
                'total_entities': 0,
                'chunks_processed': len(self.deduplicator.entity_groups)
            },
            'entities': {}
        }
        
        # Convert entity groups to final format
        for entity_type, groups in self.deduplicator.entity_groups.items():
            entities = []
            for group in groups:
                entity_data = group.original_data.copy()
                entity_data['_metadata'] = {
                    'variations': list(group.variations),
                    'source_chunks': list(group.source_chunks)
                }
                entities.append(entity_data)
            
            results['entities'][entity_type] = entities
            results['metadata']['total_entities'] += len(entities)
        
        return results

def main():
    parser = argparse.ArgumentParser(description='Extract entities from metal history chunks')
    parser.add_argument('--limit', type=int, help='Limit number of chunks to process')
    parser.add_argument('--documents', nargs='+', help='Specific documents to process')
    parser.add_argument('--output', default='extracted_entities.json', help='Output file')
    parser.add_argument('--chunks-file', default='chunks_optimized.json', help='Input chunks file')
    
    args = parser.parse_args()
    
    # Check virtual environment
    if 'venv' not in sys.prefix:
        print("WARNING: Virtual environment not activated!")
        print("Run: source venv/bin/activate")
        sys.exit(1)
    
    # Initialize pipeline
    pipeline = ExtractionPipeline(chunks_file=args.chunks_file)
    
    # Process chunks
    results = pipeline.process_chunks(
        limit=args.limit,
        documents=args.documents
    )
    
    # Save results
    output_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        args.output
    )
    
    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2)
    
    # Print summary
    print(f"\n{'='*60}")
    print("EXTRACTION COMPLETE")
    print(f"{'='*60}")
    print(f"Total entities extracted: {results['metadata']['total_entities']}")
    
    for entity_type, entities in results['entities'].items():
        print(f"\n{entity_type.upper()}: {len(entities)}")
        # Show first 3 examples
        for entity in entities[:3]:
            name = entity.get('name', entity.get('title', 'Unknown'))
            variations = entity.get('_metadata', {}).get('variations', [])
            print(f"  - {name}")
            if len(variations) > 1:
                print(f"    Variations: {', '.join(variations)}")
    
    print(f"\nResults saved to: {output_path}")

if __name__ == "__main__":
    main()