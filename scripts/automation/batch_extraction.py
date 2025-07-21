#!/usr/bin/env python3
"""
Batch extraction script with progress monitoring and error recovery.
Processes chunks in batches with checkpointing for resumability.
"""

import json
import time
import argparse
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import logging
from tqdm import tqdm

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.append(str(PROJECT_ROOT))

from extraction.enhanced_extraction import extract_entities_enhanced
from pipeline.extraction_pipeline import EntityDeduplicator

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('batch_extraction.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class BatchExtractor:
    """Handles batch extraction with progress tracking and checkpointing."""
    
    def __init__(self, checkpoint_file: str = "extraction_checkpoint.json"):
        self.checkpoint_file = Path(checkpoint_file)
        self.checkpoint_data = self._load_checkpoint()
        self.stats = {
            'total_chunks': 0,
            'processed_chunks': 0,
            'failed_chunks': 0,
            'extraction_time': 0,
            'entities_extracted': {}
        }
    
    def _load_checkpoint(self) -> Dict:
        """Load checkpoint data if exists."""
        if self.checkpoint_file.exists():
            with open(self.checkpoint_file, 'r') as f:
                return json.load(f)
        return {
            'processed_chunks': [],
            'failed_chunks': [],
            'last_update': None
        }
    
    def _save_checkpoint(self):
        """Save current progress to checkpoint file."""
        self.checkpoint_data['last_update'] = datetime.now().isoformat()
        with open(self.checkpoint_file, 'w') as f:
            json.dump(self.checkpoint_data, f, indent=2)
    
    def process_chunks(self, chunks_file: str, batch_size: int = 5, 
                      output_dir: str = "batch_extraction_output",
                      resume: bool = True, limit: Optional[int] = None):
        """Process chunks in batches with progress monitoring."""
        
        # Load chunks
        with open(chunks_file, 'r') as f:
            chunks_data = json.load(f)
        
        all_chunks = []
        for doc_name, doc_chunks in chunks_data['documents'].items():
            for chunk in doc_chunks:
                chunk['document'] = doc_name
                all_chunks.append(chunk)
        
        # Apply limit if specified
        total_available = len(all_chunks)
        if limit:
            all_chunks = all_chunks[:limit]
            logger.info(f"Limiting to {limit} chunks (from {total_available} total)")
        
        self.stats['total_chunks'] = len(all_chunks)
        
        # Filter out already processed chunks if resuming
        if resume:
            chunks_to_process = [
                c for c in all_chunks 
                if c['id'] not in self.checkpoint_data['processed_chunks']
            ]
            logger.info(f"Resuming: {len(all_chunks) - len(chunks_to_process)} chunks already processed")
        else:
            chunks_to_process = all_chunks
            self.checkpoint_data = {'processed_chunks': [], 'failed_chunks': []}
        
        # Create output directory
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)
        
        # Process in batches
        with tqdm(total=len(chunks_to_process), desc="Processing chunks") as pbar:
            for i in range(0, len(chunks_to_process), batch_size):
                batch = chunks_to_process[i:i+batch_size]
                batch_results = []
                
                for chunk in batch:
                    chunk_id = chunk['id']
                    
                    try:
                        # Extract entities
                        start_time = time.time()
                        result = extract_entities_enhanced(chunk['text'])
                        extraction_time = time.time() - start_time
                        
                        # Add metadata to result
                        result_dict = result.model_dump()
                        
                        # Add source metadata to each entity type
                        for entity_type in result_dict:
                            if isinstance(result_dict[entity_type], list):
                                for entity in result_dict[entity_type]:
                                    if '_metadata' not in entity:
                                        entity['_metadata'] = {}
                                    entity['_metadata']['source_file'] = chunk['document']
                                    entity['_metadata']['chunk_id'] = chunk_id
                        
                        # Save individual result
                        chunk_output_file = output_path / f"chunk_{chunk_id}_entities.json"
                        with open(chunk_output_file, 'w') as f:
                            json.dump(result_dict, f, indent=2)
                        
                        # Update stats
                        self.stats['extraction_time'] += extraction_time
                        self.stats['processed_chunks'] += 1
                        self._update_entity_stats(result)
                        
                        # Mark as processed
                        self.checkpoint_data['processed_chunks'].append(chunk_id)
                        
                        logger.info(f"✓ Chunk {chunk_id}: {extraction_time:.1f}s")
                        
                    except Exception as e:
                        logger.error(f"✗ Chunk {chunk_id} failed: {str(e)}")
                        self.checkpoint_data['failed_chunks'].append({
                            'chunk_id': chunk_id,
                            'error': str(e),
                            'timestamp': datetime.now().isoformat()
                        })
                        self.stats['failed_chunks'] += 1
                    
                    pbar.update(1)
                
                # Save checkpoint after each batch
                self._save_checkpoint()
                self._save_stats(output_path)
                
                # Rate limiting
                if i + batch_size < len(chunks_to_process):
                    time.sleep(2)  # Pause between batches
        
        self._print_summary()
    
    def _update_entity_stats(self, result):
        """Update entity extraction statistics."""
        for entity_type in ['bands', 'people', 'albums', 'songs', 'subgenres', 
                           'locations', 'venues', 'events', 'movements']:
            count = len(getattr(result, entity_type, []))
            if entity_type not in self.stats['entities_extracted']:
                self.stats['entities_extracted'][entity_type] = 0
            self.stats['entities_extracted'][entity_type] += count
    
    def _save_stats(self, output_path: Path):
        """Save extraction statistics."""
        stats_file = output_path / "extraction_stats.json"
        with open(stats_file, 'w') as f:
            json.dump(self.stats, f, indent=2)
    
    def _print_summary(self):
        """Print extraction summary."""
        print("\n" + "="*60)
        print("EXTRACTION SUMMARY")
        print("="*60)
        print(f"Total chunks: {self.stats['total_chunks']}")
        print(f"Processed: {self.stats['processed_chunks']}")
        print(f"Failed: {self.stats['failed_chunks']}")
        print(f"Success rate: {(self.stats['processed_chunks'] / self.stats['total_chunks'] * 100):.1f}%")
        print(f"Total time: {self.stats['extraction_time']:.1f}s")
        print(f"Avg time per chunk: {self.stats['extraction_time'] / max(1, self.stats['processed_chunks']):.1f}s")
        print("\nEntities extracted:")
        for entity_type, count in self.stats['entities_extracted'].items():
            print(f"  {entity_type}: {count}")
        print("="*60)
    
    def retry_failed(self):
        """Retry extraction for failed chunks."""
        if not self.checkpoint_data['failed_chunks']:
            print("No failed chunks to retry")
            return
        
        print(f"Retrying {len(self.checkpoint_data['failed_chunks'])} failed chunks...")
        # Implementation for retry logic

def main():
    parser = argparse.ArgumentParser(description="Batch entity extraction with progress monitoring")
    parser.add_argument('--chunks', type=str, default='chunks_optimized.json',
                       help='Path to chunks JSON file')
    parser.add_argument('--batch-size', type=int, default=5,
                       help='Number of chunks to process in each batch')
    parser.add_argument('--output-dir', type=str, default='batch_extraction_output',
                       help='Directory for extraction output')
    parser.add_argument('--limit', type=int, default=None,
                       help='Limit number of chunks to process')
    parser.add_argument('--no-resume', action='store_true',
                       help='Start fresh, ignore checkpoint')
    parser.add_argument('--retry-failed', action='store_true',
                       help='Retry failed chunks from checkpoint')
    
    args = parser.parse_args()
    
    # Check if virtual environment is activated
    if not os.environ.get('VIRTUAL_ENV'):
        print("⚠️  Warning: Virtual environment not activated!")
        print("   Run: source venv/bin/activate")
    
    extractor = BatchExtractor()
    
    if args.retry_failed:
        extractor.retry_failed()
    else:
        extractor.process_chunks(
            chunks_file=args.chunks,
            batch_size=args.batch_size,
            output_dir=args.output_dir,
            resume=not args.no_resume,
            limit=args.limit
        )

if __name__ == "__main__":
    main()