# Phase 2: Vector Search Implementation Agent

## Agent Role
You are responsible for implementing and testing vector search capabilities for the Metal History Knowledge Graph. Your mission is to build semantic search functionality that leverages the 1024-dimensional embeddings.

## Objectives
1. Implement efficient vector similarity search
2. Create intuitive search interfaces
3. Test search quality and performance
4. Enable semantic discovery of bands, albums, and genres

## Tasks

### Task 1: Vector Search Module
Create `scripts/search/vector_search.py` with:
- Cosine similarity search implementation
- K-nearest neighbors functionality
- Batch similarity computation
- Search result ranking
- Similarity threshold filtering

### Task 2: Semantic Query Interface
Create `scripts/search/semantic_query.py` with:
- Natural language query processing
- Query embedding generation
- Multi-entity search (bands, albums, songs)
- Hybrid search (vector + graph properties)
- Result explanation generation

### Task 3: Performance Optimization
- Implement embedding caching
- Test with various index structures
- Measure query latency
- Optimize for real-time search
- Profile memory usage

## Working Directory
- Scripts: `scripts/search/`
- Scratchpad: `exploration/scratchpads/phase2_vector_search.md`
- Reports: `exploration/reports/phase2_vector_search_report.md`

## Tools & Resources
- Embeddings: `entities_with_embeddings.json`
- Model: `snowflake-arctic-embed2:latest`
- Database: `schema/metal_history.db`
- Embedding docs: `docs/embedding_generation.md`

## Success Criteria
- [ ] Working vector search with <100ms latency
- [ ] Natural language query interface
- [ ] Search quality metrics >85% relevance
- [ ] Performance benchmarks documented
- [ ] Integration with graph queries

## Reporting Format
Provide a structured report including:
1. **Implementation Details**
   - Architecture overview
   - Algorithm choices
   - Optimization strategies
2. **Search Quality**
   - Test queries and results
   - Relevance metrics
   - Failure cases
3. **Performance Metrics**
   - Query latency distribution
   - Memory usage
   - Scalability analysis
4. **Usage Examples**
   - Sample queries
   - API documentation
   - Integration guide

## Example Code Snippets

### Vector Search Implementation
```python
import numpy as np
from typing import List, Tuple
import ollama

class VectorSearchEngine:
    def __init__(self, embedding_model='snowflake-arctic-embed2:latest'):
        self.model = embedding_model
        self.entity_embeddings = {}
        self.load_embeddings()
    
    def search(self, query: str, top_k: int = 10) -> List[Tuple[str, float]]:
        # Generate query embedding
        query_embedding = self.generate_embedding(query)
        
        # Calculate similarities
        similarities = []
        for entity_id, (entity_data, embedding) in self.entity_embeddings.items():
            similarity = self.cosine_similarity(query_embedding, embedding)
            similarities.append((entity_id, entity_data, similarity))
        
        # Sort and return top k
        similarities.sort(key=lambda x: x[2], reverse=True)
        return similarities[:top_k]
    
    def cosine_similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))
```

### Semantic Query Interface
```python
class SemanticQueryEngine:
    def __init__(self, vector_engine, graph_conn):
        self.vector_engine = vector_engine
        self.graph_conn = graph_conn
    
    def query(self, natural_language_query: str):
        # Parse query intent
        intent = self.parse_intent(natural_language_query)
        
        # Perform vector search
        vector_results = self.vector_engine.search(natural_language_query)
        
        # Enhance with graph data
        enhanced_results = []
        for entity_id, entity_data, score in vector_results:
            graph_data = self.get_graph_context(entity_id, intent)
            enhanced_results.append({
                'entity': entity_data,
                'score': score,
                'context': graph_data,
                'explanation': self.generate_explanation(entity_data, score)
            })
        
        return enhanced_results
```

### Performance Testing
```python
import time
import statistics

def benchmark_search(search_engine, test_queries, iterations=100):
    latencies = []
    
    for query in test_queries:
        for _ in range(iterations):
            start = time.time()
            results = search_engine.search(query)
            latency = (time.time() - start) * 1000  # ms
            latencies.append(latency)
    
    return {
        'mean_latency': statistics.mean(latencies),
        'p50': statistics.median(latencies),
        'p95': statistics.quantiles(latencies, n=20)[18],
        'p99': statistics.quantiles(latencies, n=100)[98]
    }
```

## Test Queries
Use these for quality testing:
1. "British heavy metal bands from the 80s"
2. "Bands similar to Black Sabbath"
3. "Albums with dark atmospheric sound"
4. "Guitarists who pioneered metal"
5. "Evolution of thrash metal"
6. "Bands that influenced doom metal"
7. "Fast aggressive metal from Norway"
8. "Concept albums about war"
9. "Female-fronted metal bands"
10. "Technical death metal pioneers"

## Timeline
- Day 1: Implement basic vector search
- Day 2: Build semantic query interface
- Day 3: Optimize performance and test

Document all findings and code iterations in your scratchpad!