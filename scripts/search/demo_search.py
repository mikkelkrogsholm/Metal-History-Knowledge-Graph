#!/usr/bin/env python3
"""
Demo script for vector search capabilities.

This script demonstrates various search features including:
- Basic similarity search
- Natural language queries
- Finding similar entities
- Performance characteristics
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from scripts.search.vector_search import VectorSearchEngine
from scripts.search.semantic_query import SemanticQueryEngine


def demo_basic_search():
    """Demonstrate basic vector search."""
    print("\n" + "="*60)
    print("BASIC VECTOR SEARCH DEMO")
    print("="*60)
    
    # Initialize search engine
    engine = VectorSearchEngine()
    
    # Example queries
    queries = [
        "British heavy metal bands",
        "Bands similar to Black Sabbath",
        "Heavy metal pioneers",
        "Birmingham metal scene"
    ]
    
    for query in queries:
        print(f"\nQuery: '{query}'")
        print("-" * 40)
        
        results = engine.search(query, top_k=3, threshold=0.3)
        
        for result in results:
            name = result.entity_data.get('name', 'Unknown')
            entity_type = result.entity_type.capitalize()
            score = result.similarity_score
            
            print(f"{result.rank}. [{entity_type}] {name} (Score: {score:.3f})")
            
            # Show additional details
            if result.entity_type == 'bands':
                year = result.entity_data.get('formed_year', 'Unknown')
                location = result.entity_data.get('origin_location', 'Unknown')
                print(f"   Founded: {year} in {location}")


def demo_semantic_search():
    """Demonstrate semantic query interface."""
    print("\n" + "="*60)
    print("SEMANTIC SEARCH DEMO")
    print("="*60)
    
    # Initialize engines
    vector_engine = VectorSearchEngine()
    semantic_engine = SemanticQueryEngine(vector_engine)
    
    # Natural language queries
    queries = [
        "Find bands similar to Black Sabbath",
        "Show me British metal bands from Birmingham",
        "Heavy metal guitarists"
    ]
    
    for query in queries:
        print(f"\nQuery: '{query}'")
        print("-" * 60)
        
        results = semantic_engine.query(query, top_k=3)
        formatted = semantic_engine.format_results(results)
        print(formatted)


def demo_similar_entities():
    """Demonstrate finding similar entities."""
    print("\n" + "="*60)
    print("SIMILAR ENTITIES DEMO")
    print("="*60)
    
    engine = VectorSearchEngine()
    
    # Find entities similar to Black Sabbath
    entity_id = "bands:Black Sabbath"
    
    print(f"\nFinding entities similar to: Black Sabbath")
    print("-" * 40)
    
    try:
        similar = engine.find_similar_entities(entity_id, top_k=5, exclude_self=True)
        
        for result in similar:
            name = result.entity_data.get('name', 'Unknown')
            entity_type = result.entity_type.capitalize()
            score = result.similarity_score
            
            print(f"{result.rank}. [{entity_type}] {name} (Score: {score:.3f})")
            
    except ValueError as e:
        print(f"Error: {e}")


def demo_performance():
    """Demonstrate search performance."""
    print("\n" + "="*60)
    print("PERFORMANCE CHARACTERISTICS")
    print("="*60)
    
    engine = VectorSearchEngine()
    stats = engine.get_statistics()
    
    print("\nIndex Statistics:")
    print(f"- Total entities: {stats['total_entities']}")
    print(f"- Embedding dimensions: {stats['embedding_dimensions']}")
    print(f"- Entity breakdown: {stats['entity_types']}")
    print(f"- Memory usage: {stats['memory_usage_mb']:.2f} MB")
    
    # Measure search times
    import time
    
    print("\nSearch Latency Test (10 queries):")
    test_query = "heavy metal bands"
    latencies = []
    
    for i in range(10):
        start = time.perf_counter()
        _ = engine.search(test_query, top_k=10)
        latency = (time.perf_counter() - start) * 1000
        latencies.append(latency)
    
    avg_latency = sum(latencies) / len(latencies)
    min_latency = min(latencies)
    max_latency = max(latencies)
    
    print(f"- Average: {avg_latency:.1f}ms")
    print(f"- Min: {min_latency:.1f}ms")
    print(f"- Max: {max_latency:.1f}ms")
    print(f"- Target: <100ms ✅" if avg_latency < 100 else "- Target: <100ms ❌")


def main():
    """Run all demos."""
    print("\n" + "#"*60)
    print("# METAL HISTORY VECTOR SEARCH DEMO")
    print("#"*60)
    
    # Run all demos
    demo_basic_search()
    demo_semantic_search()
    demo_similar_entities()
    demo_performance()
    
    print("\n" + "#"*60)
    print("# Demo complete!")
    print("#"*60)


if __name__ == "__main__":
    main()