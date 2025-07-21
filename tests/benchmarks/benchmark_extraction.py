"""
Performance benchmarks for entity extraction operations
"""

import pytest
import time
import statistics
import psutil
import json
from pathlib import Path
import sys
from typing import Dict, List, Callable
import threading

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from extraction.enhanced_extraction import extract_entities_enhanced
from extraction.extraction_schemas import ExtractionResult
from history.text_splitter import TextSplitter


class PerformanceBenchmark:
    """Base class for performance benchmarking"""
    
    def __init__(self):
        self.results = []
        self.process = psutil.Process()
    
    def measure_operation(self, operation: Callable, *args, **kwargs) -> Dict:
        """Measure performance of a single operation"""
        # Memory before
        self.process.memory_info()  # Warm up
        mem_before = self.process.memory_info().rss / 1024 / 1024  # MB
        
        # CPU before
        cpu_before = self.process.cpu_percent(interval=0.1)
        
        # Time operation
        start_time = time.perf_counter()
        result = operation(*args, **kwargs)
        end_time = time.perf_counter()
        
        # Memory after
        mem_after = self.process.memory_info().rss / 1024 / 1024  # MB
        
        # CPU after
        cpu_after = self.process.cpu_percent(interval=0.1)
        
        return {
            "result": result,
            "latency_ms": (end_time - start_time) * 1000,
            "memory_delta_mb": mem_after - mem_before,
            "memory_peak_mb": mem_after,
            "cpu_usage_percent": (cpu_before + cpu_after) / 2
        }
    
    def benchmark_operation(self, operation: Callable, *args, 
                          iterations: int = 10, warmup: int = 2, **kwargs) -> Dict:
        """Benchmark an operation multiple times"""
        # Warmup runs
        for _ in range(warmup):
            operation(*args, **kwargs)
        
        # Actual benchmark runs
        measurements = []
        for i in range(iterations):
            measurement = self.measure_operation(operation, *args, **kwargs)
            measurements.append(measurement)
            
            # Small delay between iterations
            time.sleep(0.1)
        
        # Calculate statistics
        latencies = [m["latency_ms"] for m in measurements]
        memory_deltas = [m["memory_delta_mb"] for m in measurements]
        cpu_usages = [m["cpu_usage_percent"] for m in measurements]
        
        return {
            "operation": operation.__name__,
            "iterations": iterations,
            "latency": {
                "mean": statistics.mean(latencies),
                "median": statistics.median(latencies),
                "stdev": statistics.stdev(latencies) if len(latencies) > 1 else 0,
                "min": min(latencies),
                "max": max(latencies),
                "p95": statistics.quantiles(latencies, n=20)[18] if len(latencies) >= 20 else max(latencies),
                "p99": statistics.quantiles(latencies, n=100)[98] if len(latencies) >= 100 else max(latencies)
            },
            "memory": {
                "mean_delta": statistics.mean(memory_deltas),
                "max_delta": max(memory_deltas),
                "peak": max(m["memory_peak_mb"] for m in measurements)
            },
            "cpu": {
                "mean": statistics.mean(cpu_usages),
                "max": max(cpu_usages)
            }
        }


class TestExtractionPerformance:
    """Benchmark extraction performance"""
    
    @pytest.fixture
    def benchmark(self):
        return PerformanceBenchmark()
    
    @pytest.fixture
    def sample_texts(self):
        """Different sized text samples for benchmarking"""
        return {
            "small": "Black Sabbath formed in Birmingham in 1968.",
            "medium": """Black Sabbath formed in Birmingham, England in 1968. The band consisted of 
                        Tony Iommi on guitar, Geezer Butler on bass, Bill Ward on drums, and 
                        Ozzy Osbourne on vocals. They are widely considered the pioneers of heavy metal music.
                        Their self-titled debut album was released in 1970.""",
            "large": """Black Sabbath formed in Birmingham, England in 1968. The band consisted of 
                       Tony Iommi on guitar, Geezer Butler on bass, Bill Ward on drums, and 
                       Ozzy Osbourne on vocals. They are widely considered the pioneers of heavy metal music.
                       
                       Their self-titled debut album "Black Sabbath" was released on February 13, 1970, 
                       which many consider the first true heavy metal album. The album featured dark themes 
                       and heavy, distorted guitar riffs that would define the genre. Songs like "Black Sabbath," 
                       "The Wizard," and "N.I.B." showcased their revolutionary sound.
                       
                       The band's second album, "Paranoid," was released later in 1970 and included classics 
                       like "War Pigs," "Iron Man," and the title track "Paranoid." This album solidified their 
                       status as metal pioneers and influenced countless bands that followed.
                       
                       Throughout the 1970s, Black Sabbath continued to release influential albums including 
                       "Master of Reality" (1971), "Vol. 4" (1972), "Sabbath Bloody Sabbath" (1973), 
                       "Sabotage" (1975), and "Technical Ecstasy" (1976).""" * 3  # Triple for larger test
        }
    
    def test_extraction_latency_by_size(self, benchmark, sample_texts):
        """Test how extraction latency scales with text size"""
        results = {}
        
        for size, text in sample_texts.items():
            print(f"\nBenchmarking {size} text ({len(text)} chars)...")
            result = benchmark.benchmark_operation(
                extract_entities_enhanced,
                text,
                iterations=5 if size == "large" else 10
            )
            results[size] = result
            
            print(f"  Mean latency: {result['latency']['mean']:.1f}ms")
            print(f"  Memory delta: {result['memory']['mean_delta']:.1f}MB")
        
        # Verify scaling is reasonable
        small_latency = results["small"]["latency"]["mean"]
        large_latency = results["large"]["latency"]["mean"]
        
        # Large text should take longer but not exponentially
        scaling_factor = large_latency / small_latency
        assert scaling_factor < 20, f"Extraction scaling is too high: {scaling_factor:.1f}x"
        
        return results
    
    def test_extraction_memory_usage(self, benchmark):
        """Test memory usage during extraction"""
        # Create a large text that might stress memory
        large_text = """
        The history of heavy metal is filled with legendary bands and musicians.
        """ * 100  # Repeat to create larger text
        
        # Add many entity mentions
        bands = ["Black Sabbath", "Iron Maiden", "Metallica", "Megadeth", "Slayer"]
        people = ["Tony Iommi", "Steve Harris", "James Hetfield", "Dave Mustaine", "Kerry King"]
        
        for i in range(20):
            large_text += f"\n{bands[i % len(bands)]} released their album in {1970 + i}."
            large_text += f"\n{people[i % len(people)]} played guitar for the band."
        
        result = benchmark.benchmark_operation(
            extract_entities_enhanced,
            large_text,
            iterations=5
        )
        
        # Memory usage should be reasonable
        assert result["memory"]["peak"] < 500, \
            f"Peak memory usage too high: {result['memory']['peak']:.1f}MB"
        
        # Memory should be released after extraction
        assert result["memory"]["mean_delta"] < 50, \
            f"Memory leak detected: {result['memory']['mean_delta']:.1f}MB average increase"
    
    def test_extraction_consistency(self, benchmark, sample_texts):
        """Test that extraction performance is consistent"""
        text = sample_texts["medium"]
        
        result = benchmark.benchmark_operation(
            extract_entities_enhanced,
            text,
            iterations=20
        )
        
        # Check consistency (coefficient of variation)
        cv = result["latency"]["stdev"] / result["latency"]["mean"]
        assert cv < 0.3, f"Extraction latency too variable: CV={cv:.2f}"
        
        # P95 should not be too far from mean
        p95_ratio = result["latency"]["p95"] / result["latency"]["mean"]
        assert p95_ratio < 2.0, f"P95 latency too high compared to mean: {p95_ratio:.1f}x"
    
    def test_parallel_extraction_performance(self, benchmark):
        """Test performance with parallel extraction"""
        texts = [
            "Black Sabbath formed in 1968 in Birmingham.",
            "Iron Maiden formed in 1975 in London.",
            "Metallica formed in 1981 in Los Angeles.",
            "Megadeth formed in 1983 in Los Angeles."
        ]
        
        # Sequential extraction
        start = time.perf_counter()
        sequential_results = []
        for text in texts:
            result = extract_entities_enhanced(text)
            sequential_results.append(result)
        sequential_time = (time.perf_counter() - start) * 1000
        
        # Parallel extraction using threads
        start = time.perf_counter()
        parallel_results = []
        threads = []
        
        def extract_threaded(text, index):
            result = extract_entities_enhanced(text)
            parallel_results.insert(index, result)
        
        for i, text in enumerate(texts):
            thread = threading.Thread(target=extract_threaded, args=(text, i))
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        parallel_time = (time.perf_counter() - start) * 1000
        
        print(f"\nSequential time: {sequential_time:.1f}ms")
        print(f"Parallel time: {parallel_time:.1f}ms")
        print(f"Speedup: {sequential_time/parallel_time:.2f}x")
        
        # Parallel should be faster (but not necessarily 4x due to GIL)
        assert parallel_time < sequential_time, "Parallel extraction not faster"
    
    @pytest.mark.slow
    def test_extraction_stress_test(self, benchmark):
        """Stress test with many extractions"""
        text = "Metallica released Master of Puppets in 1986, their third studio album."
        
        # Run many extractions to test stability
        result = benchmark.benchmark_operation(
            extract_entities_enhanced,
            text,
            iterations=100,
            warmup=5
        )
        
        # System should remain stable
        assert result["latency"]["mean"] < 1000, "Mean latency too high under load"
        assert result["cpu"]["max"] < 95, "CPU usage too high"
        
        # Check for performance degradation
        latencies = []
        for i in range(100):
            start = time.perf_counter()
            extract_entities_enhanced(text)
            latencies.append((time.perf_counter() - start) * 1000)
        
        # Compare first 10 vs last 10 extractions
        first_10_mean = statistics.mean(latencies[:10])
        last_10_mean = statistics.mean(latencies[-10:])
        
        degradation = (last_10_mean - first_10_mean) / first_10_mean
        assert degradation < 0.2, f"Performance degraded by {degradation*100:.1f}% over time"
    
    def test_chunk_processing_performance(self, benchmark):
        """Test performance of processing multiple chunks"""
        # Create test chunks
        splitter = TextSplitter(chunk_size=1000, chunk_overlap=100)
        
        long_text = """
        The history of heavy metal spans over five decades, beginning in the late 1960s and early 1970s.
        """ * 50
        
        chunks = splitter.split_text(long_text, source_file="test.md")
        
        # Benchmark chunk processing
        def process_chunks(chunks_to_process):
            results = []
            for chunk in chunks_to_process:
                result = extract_entities_enhanced(chunk.text)
                results.append(result)
            return results
        
        result = benchmark.benchmark_operation(
            process_chunks,
            chunks[:10],  # Process first 10 chunks
            iterations=3
        )
        
        chunks_per_second = 10 / (result["latency"]["mean"] / 1000)
        print(f"\nChunk processing rate: {chunks_per_second:.2f} chunks/second")
        
        # Should process at least 1 chunk per second
        assert chunks_per_second > 1.0, "Chunk processing too slow"