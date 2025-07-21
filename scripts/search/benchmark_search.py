#!/usr/bin/env python3
"""
Performance Benchmarking for Vector Search

This module tests search performance and quality metrics.
"""

import time
import statistics
import json
import numpy as np
from typing import List, Dict, Any
from pathlib import Path
import matplotlib.pyplot as plt
import sys

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from vector_search import VectorSearchEngine
from semantic_query import SemanticQueryEngine


class SearchBenchmark:
    """Comprehensive benchmarking for vector search performance."""
    
    def __init__(self, vector_engine: VectorSearchEngine):
        """Initialize benchmark with search engine."""
        self.vector_engine = vector_engine
        self.results = {
            'latency': {},
            'quality': {},
            'memory': {}
        }
        
    def benchmark_latency(self, 
                         test_queries: List[str], 
                         iterations: int = 100) -> Dict[str, float]:
        """
        Measure search latency statistics.
        
        Args:
            test_queries: List of queries to test
            iterations: Number of iterations per query
            
        Returns:
            Latency statistics
        """
        print(f"\nBenchmarking latency with {iterations} iterations per query...")
        
        all_latencies = []
        query_latencies = {}
        
        # Warm up
        for _ in range(10):
            self.vector_engine.search("warm up query", top_k=10)
        
        for query in test_queries:
            query_times = []
            
            for _ in range(iterations):
                start = time.perf_counter()
                _ = self.vector_engine.search(query, top_k=10)
                latency = (time.perf_counter() - start) * 1000  # ms
                query_times.append(latency)
                all_latencies.append(latency)
            
            query_latencies[query] = {
                'mean': statistics.mean(query_times),
                'median': statistics.median(query_times),
                'std': statistics.stdev(query_times) if len(query_times) > 1 else 0,
                'min': min(query_times),
                'max': max(query_times)
            }
        
        # Overall statistics
        overall_stats = {
            'mean_latency_ms': statistics.mean(all_latencies),
            'median_latency_ms': statistics.median(all_latencies),
            'p50_ms': statistics.quantiles(all_latencies, n=100)[49],
            'p95_ms': statistics.quantiles(all_latencies, n=100)[94],
            'p99_ms': statistics.quantiles(all_latencies, n=100)[98],
            'min_latency_ms': min(all_latencies),
            'max_latency_ms': max(all_latencies),
            'queries_tested': len(test_queries),
            'total_searches': len(all_latencies)
        }
        
        self.results['latency'] = {
            'overall': overall_stats,
            'per_query': query_latencies
        }
        
        return overall_stats
    
    def benchmark_quality(self, 
                         relevance_queries: Dict[str, List[str]]) -> Dict[str, float]:
        """
        Measure search quality using known relevant results.
        
        Args:
            relevance_queries: Dict mapping queries to expected relevant entities
            
        Returns:
            Quality metrics
        """
        print("\nBenchmarking search quality...")
        
        precision_scores = []
        recall_scores = []
        mrr_scores = []  # Mean Reciprocal Rank
        
        for query, expected_entities in relevance_queries.items():
            results = self.vector_engine.search(query, top_k=10)
            
            # Extract entity names from results
            result_names = [
                r.entity_data.get('name', '') 
                for r in results
            ]
            
            # Calculate precision at K
            relevant_found = sum(1 for name in result_names if name in expected_entities)
            precision = relevant_found / len(results) if results else 0
            precision_scores.append(precision)
            
            # Calculate recall
            recall = relevant_found / len(expected_entities) if expected_entities else 0
            recall_scores.append(recall)
            
            # Calculate reciprocal rank
            for i, name in enumerate(result_names):
                if name in expected_entities:
                    mrr_scores.append(1.0 / (i + 1))
                    break
            else:
                mrr_scores.append(0.0)
        
        quality_metrics = {
            'mean_precision': statistics.mean(precision_scores),
            'mean_recall': statistics.mean(recall_scores),
            'mean_reciprocal_rank': statistics.mean(mrr_scores),
            'queries_evaluated': len(relevance_queries)
        }
        
        self.results['quality'] = quality_metrics
        return quality_metrics
    
    def benchmark_scalability(self, 
                            query: str = "heavy metal bands",
                            k_values: List[int] = [1, 5, 10, 20, 50, 100]) -> Dict[str, Any]:
        """
        Test how performance scales with different k values.
        
        Args:
            query: Test query to use
            k_values: Different k values to test
            
        Returns:
            Scalability metrics
        """
        print("\nBenchmarking scalability...")
        
        latencies = []
        
        for k in k_values:
            times = []
            
            for _ in range(50):
                start = time.perf_counter()
                _ = self.vector_engine.search(query, top_k=k)
                latency = (time.perf_counter() - start) * 1000
                times.append(latency)
            
            avg_latency = statistics.mean(times)
            latencies.append(avg_latency)
            print(f"k={k}: {avg_latency:.2f}ms")
        
        # Plot scalability
        self._plot_scalability(k_values, latencies)
        
        return {
            'k_values': k_values,
            'latencies_ms': latencies
        }
    
    def _plot_scalability(self, k_values: List[int], latencies: List[float]):
        """Create scalability plot."""
        plt.figure(figsize=(10, 6))
        plt.plot(k_values, latencies, 'b-o', linewidth=2, markersize=8)
        plt.xlabel('k (number of results)', fontsize=12)
        plt.ylabel('Latency (ms)', fontsize=12)
        plt.title('Search Latency vs Number of Results', fontsize=14)
        plt.grid(True, alpha=0.3)
        
        # Add 100ms target line
        plt.axhline(y=100, color='r', linestyle='--', label='100ms target')
        plt.legend()
        
        # Save plot
        plt.savefig('search_scalability.png', dpi=150, bbox_inches='tight')
        plt.close()
        print("Scalability plot saved to search_scalability.png")
    
    def generate_report(self) -> str:
        """Generate comprehensive benchmark report."""
        report = []
        report.append("# Vector Search Performance Benchmark Report")
        report.append("=" * 60)
        
        # Latency results
        if 'latency' in self.results and self.results['latency']:
            latency = self.results['latency']['overall']
            report.append("\n## Latency Performance")
            report.append(f"- Mean latency: {latency['mean_latency_ms']:.2f}ms")
            report.append(f"- Median latency: {latency['median_latency_ms']:.2f}ms")
            report.append(f"- P95 latency: {latency['p95_ms']:.2f}ms")
            report.append(f"- P99 latency: {latency['p99_ms']:.2f}ms")
            report.append(f"- Min/Max: {latency['min_latency_ms']:.2f}ms / {latency['max_latency_ms']:.2f}ms")
            
            # Check against 100ms target
            if latency['p95_ms'] < 100:
                report.append("\n✅ **Performance target met**: P95 < 100ms")
            else:
                report.append("\n❌ **Performance target not met**: P95 > 100ms")
        
        # Quality results
        if 'quality' in self.results and self.results['quality']:
            quality = self.results['quality']
            report.append("\n## Search Quality")
            report.append(f"- Mean precision: {quality['mean_precision']:.2%}")
            report.append(f"- Mean recall: {quality['mean_recall']:.2%}")
            report.append(f"- Mean reciprocal rank: {quality['mean_reciprocal_rank']:.3f}")
            
            # Check against 85% relevance target
            relevance_score = (quality['mean_precision'] + quality['mean_recall']) / 2
            if relevance_score > 0.85:
                report.append(f"\n✅ **Quality target met**: Relevance > 85% ({relevance_score:.2%})")
            else:
                report.append(f"\n❌ **Quality target not met**: Relevance < 85% ({relevance_score:.2%})")
        
        # Memory usage
        stats = self.vector_engine.get_statistics()
        report.append("\n## Memory Usage")
        report.append(f"- Total entities: {stats['total_entities']}")
        report.append(f"- Embedding dimensions: {stats['embedding_dimensions']}")
        report.append(f"- Memory usage: {stats['memory_usage_mb']:.2f} MB")
        
        return "\n".join(report)
    
    def save_results(self, filename: str = "benchmark_results.json"):
        """Save benchmark results to JSON file."""
        with open(filename, 'w') as f:
            json.dump(self.results, f, indent=2)
        print(f"Results saved to {filename}")


def main():
    """Run comprehensive benchmarks."""
    # Initialize search engine
    print("Initializing vector search engine...")
    vector_engine = VectorSearchEngine()
    
    # Initialize benchmark
    benchmark = SearchBenchmark(vector_engine)
    
    # Test queries for latency
    latency_queries = [
        "British heavy metal bands",
        "Bands similar to Black Sabbath",
        "Heavy metal pioneers",
        "Albums from the 70s",
        "Doom metal",
        "Birmingham metal scene",
        "Fast aggressive metal",
        "Technical metal guitarists",
        "Concept albums",
        "Metal evolution"
    ]
    
    # Relevance test queries (adjust based on actual data)
    relevance_queries = {
        "Bands similar to Black Sabbath": ["Black Sabbath", "Sabbath"],
        "Heavy metal pioneers": ["Black Sabbath"],
        "British metal bands": ["Black Sabbath"],
        "Albums from 1970": ["Paranoid"]
    }
    
    # Run benchmarks
    print("\n" + "="*60)
    print("RUNNING PERFORMANCE BENCHMARKS")
    print("="*60)
    
    # 1. Latency benchmark
    latency_stats = benchmark.benchmark_latency(latency_queries, iterations=100)
    
    # 2. Quality benchmark
    quality_stats = benchmark.benchmark_quality(relevance_queries)
    
    # 3. Scalability benchmark
    scalability_stats = benchmark.benchmark_scalability()
    
    # Generate and print report
    report = benchmark.generate_report()
    print("\n" + report)
    
    # Save results
    benchmark.save_results()
    
    # Save report to file
    with open("benchmark_report.md", 'w') as f:
        f.write(report)
    print("\nReport saved to benchmark_report.md")


if __name__ == "__main__":
    main()