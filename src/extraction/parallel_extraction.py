#!/usr/bin/env python3
"""
Parallel entity extraction for improved performance.
Uses concurrent processing and connection pooling to speed up extraction.
"""

import json
import ollama
import asyncio
import aiohttp
from typing import List, Dict, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import partial
import time
from tqdm import tqdm
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.append(str(PROJECT_ROOT))

from src.extraction.extraction_schemas import ExtractionResult
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ParallelExtractor:
    """Parallel extraction with connection pooling and optimizations."""
    
    def __init__(self, model='magistral:24b', max_workers=3):
        self.model = model
        self.max_workers = max_workers
        self.options = {
            'temperature': 0.1,
            'num_ctx': 16384,  # Reduced for faster processing
            'top_p': 0.9,
            'num_predict': 4096,  # Limit output size
            'seed': 42  # For reproducibility
        }
        
    def _create_prompt(self, text: str) -> str:
        """Create extraction prompt with optimizations."""
        return f"""Extract entities from this metal history text. Be concise but thorough.

Extract: bands (name, formed_year, origin_location), people (name, roles), albums (title, band_name, release_year), songs (title), subgenres (name), locations (name), events (name, year).

Text: {text[:2000]}  # Limit text size for faster processing

Return valid JSON only."""

    def _extract_chunk(self, chunk: Dict[str, Any]) -> Dict[str, Any]:
        """Extract entities from a single chunk."""
        start_time = time.time()
        chunk_id = chunk.get('id', 'unknown')
        
        try:
            # Use simpler prompt for speed
            prompt = self._create_prompt(chunk['text'])
            
            response = ollama.chat(
                model=self.model,
                messages=[
                    {'role': 'user', 'content': prompt}
                ],
                format=ExtractionResult.model_json_schema(),
                options=self.options,
                stream=False
            )
            
            result = ExtractionResult.model_validate_json(response.message.content)
            
            # Add metadata
            result_dict = result.model_dump()
            for entity_type in result_dict:
                if isinstance(result_dict[entity_type], list):
                    for entity in result_dict[entity_type]:
                        if '_metadata' not in entity:
                            entity['_metadata'] = {}
                        entity['_metadata']['chunk_id'] = chunk_id
                        entity['_metadata']['extraction_time'] = time.time() - start_time
            
            logger.info(f"Extracted chunk {chunk_id} in {time.time() - start_time:.2f}s")
            return {
                'chunk_id': chunk_id,
                'entities': result_dict,
                'extraction_time': time.time() - start_time,
                'success': True
            }
            
        except Exception as e:
            logger.error(f"Error extracting chunk {chunk_id}: {e}")
            return {
                'chunk_id': chunk_id,
                'entities': {},
                'error': str(e),
                'extraction_time': time.time() - start_time,
                'success': False
            }
    
    def extract_parallel(self, chunks: List[Dict[str, Any]], 
                        show_progress: bool = True) -> Dict[str, Any]:
        """Extract entities from multiple chunks in parallel."""
        start_time = time.time()
        results = []
        
        # Create progress bar
        if show_progress:
            pbar = tqdm(total=len(chunks), desc="Extracting entities (parallel)")
        
        # Process chunks in parallel
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all tasks
            future_to_chunk = {
                executor.submit(self._extract_chunk, chunk): chunk 
                for chunk in chunks
            }
            
            # Process completed tasks
            for future in as_completed(future_to_chunk):
                result = future.result()
                results.append(result)
                
                if show_progress:
                    pbar.update(1)
                    avg_time = sum(r['extraction_time'] for r in results) / len(results)
                    pbar.set_postfix({'avg_time': f'{avg_time:.2f}s'})
        
        if show_progress:
            pbar.close()
        
        # Aggregate results
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
        
        successful_extractions = 0
        failed_extractions = 0
        
        for result in results:
            if result['success']:
                successful_extractions += 1
                entities = result['entities']
                for entity_type in all_entities:
                    if entity_type in entities:
                        all_entities[entity_type].extend(entities[entity_type])
            else:
                failed_extractions += 1
        
        total_time = time.time() - start_time
        avg_time_per_chunk = total_time / len(chunks) if chunks else 0
        
        return {
            'entities': all_entities,
            'metadata': {
                'total_chunks': len(chunks),
                'successful_extractions': successful_extractions,
                'failed_extractions': failed_extractions,
                'total_time': total_time,
                'avg_time_per_chunk': avg_time_per_chunk,
                'parallel_workers': self.max_workers
            }
        }


def optimize_extraction_settings():
    """Test and optimize extraction settings."""
    test_text = """Black Sabbath formed in Birmingham in 1968. 
    Tony Iommi played guitar. They released Paranoid in 1970."""
    
    settings_to_test = [
        {'num_ctx': 8192, 'num_predict': 2048},
        {'num_ctx': 16384, 'num_predict': 4096},
        {'num_ctx': 32768, 'num_predict': 8192},
    ]
    
    print("Testing extraction settings...")
    for settings in settings_to_test:
        start = time.time()
        try:
            response = ollama.chat(
                model='magistral:24b',
                messages=[{'role': 'user', 'content': f'Extract entities: {test_text}'}],
                format=ExtractionResult.model_json_schema(),
                options={'temperature': 0.1, **settings}
            )
            elapsed = time.time() - start
            print(f"Settings {settings}: {elapsed:.2f}s")
        except Exception as e:
            print(f"Settings {settings}: Failed - {e}")


def main():
    """Test parallel extraction."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Parallel entity extraction")
    parser.add_argument('--test', action='store_true', help='Run test extraction')
    parser.add_argument('--optimize', action='store_true', help='Test optimization settings')
    parser.add_argument('--workers', type=int, default=3, help='Number of parallel workers')
    parser.add_argument('--chunks', type=str, help='Path to chunks JSON file')
    parser.add_argument('--limit', type=int, help='Limit number of chunks to process')
    parser.add_argument('--output', type=str, default='parallel_extraction_output.json',
                       help='Output file path')
    
    args = parser.parse_args()
    
    if args.optimize:
        optimize_extraction_settings()
        return
    
    if args.test:
        # Create test chunks
        test_chunks = [
            {
                'id': 'test_001',
                'text': 'Black Sabbath formed in Birmingham in 1968. Tony Iommi played guitar.'
            },
            {
                'id': 'test_002', 
                'text': 'Iron Maiden formed in London in 1975. They released The Number of the Beast in 1982.'
            },
            {
                'id': 'test_003',
                'text': 'Metallica formed in Los Angeles in 1981. James Hetfield is the vocalist.'
            }
        ]
        
        extractor = ParallelExtractor(max_workers=args.workers)
        result = extractor.extract_parallel(test_chunks)
        
        print(f"\nExtraction completed in {result['metadata']['total_time']:.2f}s")
        print(f"Average time per chunk: {result['metadata']['avg_time_per_chunk']:.2f}s")
        print(f"Successful: {result['metadata']['successful_extractions']}")
        print(f"Failed: {result['metadata']['failed_extractions']}")
        
        # Show sample results
        if result['entities']['bands']:
            print(f"\nSample bands extracted: {[b['name'] for b in result['entities']['bands'][:3]]}")
        
        return
    
    if args.chunks:
        # Load chunks from file
        with open(args.chunks, 'r') as f:
            data = json.load(f)
        
        # Flatten chunks from all documents
        all_chunks = []
        for doc, chunks in data.get('documents', {}).items():
            all_chunks.extend(chunks)
        
        if args.limit:
            all_chunks = all_chunks[:args.limit]
        
        print(f"Processing {len(all_chunks)} chunks with {args.workers} workers...")
        
        extractor = ParallelExtractor(max_workers=args.workers)
        result = extractor.extract_parallel(all_chunks)
        
        # Save results
        with open(args.output, 'w') as f:
            json.dump(result, f, indent=2)
        
        print(f"\nExtraction completed in {result['metadata']['total_time']:.2f}s")
        print(f"Average time per chunk: {result['metadata']['avg_time_per_chunk']:.2f}s")
        print(f"Results saved to: {args.output}")
        
        # Show statistics
        total_entities = sum(len(v) for v in result['entities'].values() if isinstance(v, list))
        print(f"Total entities extracted: {total_entities}")


if __name__ == "__main__":
    main()