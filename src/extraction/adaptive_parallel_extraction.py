#!/usr/bin/env python3
"""
Adaptive parallel entity extraction that scales based on system resources.
Monitors resource usage and adjusts dynamically.
"""

import json
import ollama
import time
import psutil
import threading
from typing import List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from queue import Queue, PriorityQueue
import logging
from tqdm import tqdm
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.append(str(PROJECT_ROOT))

from src.extraction.extraction_schemas import ExtractionResult
from scripts.automation.system_profiler import SystemProfiler

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ResourceMonitor:
    """Monitor system resources during extraction."""
    
    def __init__(self, limits: Dict[str, Any]):
        self.limits = limits
        self.running = False
        self.throttle_event = threading.Event()
        self.throttle_event.set()  # Start unthrottled
        self.stats = {
            'max_cpu': 0,
            'max_memory': 0,
            'throttle_count': 0
        }
        
    def start(self):
        """Start monitoring in background thread."""
        self.running = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()
        
    def stop(self):
        """Stop monitoring."""
        self.running = False
        if hasattr(self, 'monitor_thread'):
            self.monitor_thread.join(timeout=1)
            
    def _monitor_loop(self):
        """Monitor resources and throttle if needed."""
        while self.running:
            cpu_percent = psutil.cpu_percent(interval=0.5)
            memory_percent = psutil.virtual_memory().percent
            
            # Update max stats
            self.stats['max_cpu'] = max(self.stats['max_cpu'], cpu_percent)
            self.stats['max_memory'] = max(self.stats['max_memory'], memory_percent)
            
            # Check if we need to throttle
            if (cpu_percent > self.limits['max_cpu_percent'] or 
                memory_percent > self.limits['max_memory_percent']):
                if self.throttle_event.is_set():
                    logger.warning(f"Throttling: CPU {cpu_percent}%, Memory {memory_percent}%")
                    self.stats['throttle_count'] += 1
                    self.throttle_event.clear()
            else:
                if not self.throttle_event.is_set():
                    logger.info("Resuming normal operation")
                    self.throttle_event.set()
                    
            time.sleep(1)
    
    def wait_if_throttled(self):
        """Wait if system is under high load."""
        self.throttle_event.wait()


class AdaptiveParallelExtractor:
    """Adaptive extraction that scales based on available resources."""
    
    def __init__(self, model='magistral:24b', profile: Optional[Dict] = None):
        self.model = model
        
        # Get system profile and settings
        if profile:
            self.settings = profile
            # Get resource limits from profiler if not in profile
            if 'resource_limits' not in profile:
                profiler = SystemProfiler()
                self.resource_limits = profiler.get_resource_limits()
            else:
                self.resource_limits = profile['resource_limits']
        else:
            profiler = SystemProfiler()
            self.settings = profiler.get_extraction_settings()
            self.resource_limits = profiler.get_resource_limits()
        
        # Extraction options optimized for the system
        self.options = {
            'temperature': 0.1,
            'num_ctx': self.settings['num_ctx'],
            'num_predict': self.settings['num_predict'],
            'num_thread': self.settings.get('num_threads', 2),
            'top_p': 0.9,
            'seed': 42
        }
        
        # Resource monitor
        self.monitor = ResourceMonitor(self.resource_limits)
        
        # Cache for prefetched chunks if enabled
        self.chunk_cache = Queue() if self.settings.get('prefetch_chunks') else None
        
        logger.info(f"Initialized adaptive extractor: {self.settings['parallel_workers']} workers, "
                   f"tier: {self.settings['system_profile']['tier']}")
    
    def _create_prompt(self, text: str) -> str:
        """Create extraction prompt optimized for speed."""
        # Truncate text based on context window
        max_chars = min(len(text), self.settings['num_ctx'] // 4)
        text = text[:max_chars]
        
        return f"""Extract entities from this metal history text. Be concise.

Extract: bands (name, formed_year, origin_location), people (name, roles), albums (title, band_name, release_year), songs (title), subgenres (name), locations (name), events (name, year).

Text: {text}

Return valid JSON only."""

    def _extract_chunk_with_monitoring(self, chunk: Dict[str, Any]) -> Dict[str, Any]:
        """Extract entities from a single chunk with resource monitoring."""
        # Wait if system is throttled
        self.monitor.wait_if_throttled()
        
        start_time = time.time()
        chunk_id = chunk.get('id', 'unknown')
        
        try:
            prompt = self._create_prompt(chunk['text'])
            
            response = ollama.chat(
                model=self.model,
                messages=[{'role': 'user', 'content': prompt}],
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
    
    def _prefetch_chunks(self, chunks: List[Dict[str, Any]]):
        """Prefetch chunks into memory if enabled."""
        if not self.chunk_cache:
            return
            
        logger.info("Prefetching chunks into memory...")
        for chunk in chunks:
            self.chunk_cache.put(chunk)
    
    def extract_adaptive(self, chunks: List[Dict[str, Any]], 
                        show_progress: bool = True,
                        priority_field: Optional[str] = None) -> Dict[str, Any]:
        """
        Extract entities with adaptive parallelism and resource management.
        
        Args:
            chunks: List of text chunks to process
            show_progress: Show progress bar
            priority_field: Field to use for prioritizing chunks (e.g., 'importance')
        """
        start_time = time.time()
        
        # Start resource monitoring
        self.monitor.start()
        
        # Prefetch if enabled
        if self.settings.get('prefetch_chunks'):
            self._prefetch_chunks(chunks)
        
        # Sort chunks by priority if specified
        if priority_field:
            chunks = sorted(chunks, key=lambda x: x.get(priority_field, 0), reverse=True)
        
        results = []
        
        # Create progress bar
        if show_progress:
            pbar = tqdm(total=len(chunks), 
                       desc=f"Extracting ({self.settings['parallel_workers']} workers)")
        
        # Process chunks in batches for better memory management
        batch_size = self.settings.get('batch_size', 5)
        
        for i in range(0, len(chunks), batch_size * self.settings['parallel_workers']):
            batch = chunks[i:i + batch_size * self.settings['parallel_workers']]
            
            with ThreadPoolExecutor(max_workers=self.settings['parallel_workers']) as executor:
                # Submit batch
                future_to_chunk = {
                    executor.submit(self._extract_chunk_with_monitoring, chunk): chunk 
                    for chunk in batch
                }
                
                # Process completed tasks
                for future in as_completed(future_to_chunk):
                    result = future.result()
                    results.append(result)
                    
                    if show_progress:
                        pbar.update(1)
                        # Update progress with stats
                        avg_time = sum(r['extraction_time'] for r in results) / len(results)
                        success_rate = sum(1 for r in results if r['success']) / len(results) * 100
                        pbar.set_postfix({
                            'avg_time': f'{avg_time:.2f}s',
                            'success': f'{success_rate:.0f}%',
                            'throttled': self.monitor.stats['throttle_count']
                        })
        
        if show_progress:
            pbar.close()
        
        # Stop monitoring
        self.monitor.stop()
        
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
                'parallel_workers': self.settings['parallel_workers'],
                'system_tier': self.settings['system_profile']['tier'],
                'resource_stats': {
                    'max_cpu_percent': self.monitor.stats['max_cpu'],
                    'max_memory_percent': self.monitor.stats['max_memory'],
                    'throttle_events': self.monitor.stats['throttle_count']
                }
            }
        }


def benchmark_settings():
    """Benchmark different settings to find optimal configuration."""
    test_chunks = [
        {'id': f'test_{i}', 'text': 'Black Sabbath formed in Birmingham in 1968.'}
        for i in range(5)
    ]
    
    profiler = SystemProfiler()
    settings = profiler.get_extraction_settings()
    
    print("\n🧪 Benchmarking extraction settings...")
    print(f"System tier: {settings['system_profile']['tier']}")
    print(f"Testing with {len(test_chunks)} chunks\n")
    
    # Test different worker counts
    worker_counts = [1, 2, settings['parallel_workers'], settings['parallel_workers'] + 1]
    
    for workers in worker_counts:
        if workers > settings['system_profile']['cores']:
            continue
            
        settings['parallel_workers'] = workers
        extractor = AdaptiveParallelExtractor(profile=settings)
        
        start = time.time()
        result = extractor.extract_adaptive(test_chunks, show_progress=False)
        elapsed = time.time() - start
        
        print(f"Workers: {workers} - Time: {elapsed:.2f}s "
              f"({elapsed/len(test_chunks):.2f}s per chunk) "
              f"Throttled: {result['metadata']['resource_stats']['throttle_events']}")


def main():
    """Test adaptive extraction."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Adaptive parallel entity extraction")
    parser.add_argument('--profile', action='store_true', help='Show system profile')
    parser.add_argument('--benchmark', action='store_true', help='Benchmark settings')
    parser.add_argument('--chunks', type=str, help='Path to chunks JSON file')
    parser.add_argument('--limit', type=int, help='Limit number of chunks')
    parser.add_argument('--output', type=str, default='adaptive_extraction_output.json')
    parser.add_argument('--workers', type=int, help='Override worker count')
    
    args = parser.parse_args()
    
    if args.profile:
        profiler = SystemProfiler()
        profiler.print_profile()
        settings = profiler.get_extraction_settings()
        print(f"\nRecommended workers: {settings['parallel_workers']}")
        return
    
    if args.benchmark:
        benchmark_settings()
        return
    
    # Run extraction
    profiler = SystemProfiler()
    settings = profiler.get_extraction_settings()
    
    if args.workers:
        settings['parallel_workers'] = args.workers
        print(f"Overriding workers to: {args.workers}")
    
    if args.chunks:
        # Load chunks
        with open(args.chunks, 'r') as f:
            data = json.load(f)
        
        all_chunks = []
        for doc, chunks in data.get('documents', {}).items():
            all_chunks.extend(chunks)
        
        if args.limit:
            all_chunks = all_chunks[:args.limit]
        
        print(f"\n🚀 Adaptive extraction on {settings['system_profile']['tier'].upper()} tier system")
        print(f"Processing {len(all_chunks)} chunks with {settings['parallel_workers']} workers")
        print(f"Context window: {settings['num_ctx']}, Cache: {settings.get('use_memory_cache', False)}")
        
        extractor = AdaptiveParallelExtractor()
        result = extractor.extract_adaptive(all_chunks)
        
        # Save results
        with open(args.output, 'w') as f:
            json.dump(result, f, indent=2)
        
        # Print summary
        meta = result['metadata']
        print(f"\n✅ Extraction complete!")
        print(f"Total time: {meta['total_time']:.2f}s")
        print(f"Average per chunk: {meta['avg_time_per_chunk']:.2f}s")
        print(f"Success rate: {meta['successful_extractions']}/{meta['total_chunks']}")
        print(f"Max CPU usage: {meta['resource_stats']['max_cpu_percent']:.1f}%")
        print(f"Max memory usage: {meta['resource_stats']['max_memory_percent']:.1f}%")
        if meta['resource_stats']['throttle_events'] > 0:
            print(f"⚠️  Throttled {meta['resource_stats']['throttle_events']} times due to high load")


if __name__ == "__main__":
    main()