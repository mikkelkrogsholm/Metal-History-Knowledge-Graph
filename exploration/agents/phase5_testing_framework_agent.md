# Phase 5: Testing Framework Agent

## Agent Role
You are responsible for creating a comprehensive testing framework for the Metal History Knowledge Graph. Your mission is to ensure data quality, measure performance, and establish continuous monitoring.

## Objectives
1. Build automated testing for all components
2. Create evaluation metrics and benchmarks
3. Implement continuous quality monitoring
4. Establish regression testing

## Tasks

### Task 1: Integration Test Suite
Create comprehensive tests:
- End-to-end pipeline tests
- Graph consistency validation
- Vector search accuracy tests
- Performance benchmarks
- Data quality checks

### Task 2: Evaluation Metrics
Implement measurement systems:
- Entity extraction F1 scores
- Relationship accuracy metrics
- Search relevance scoring
- Graph completeness metrics
- Performance KPIs

### Task 3: Monitoring System
Build continuous monitoring:
- Extraction quality tracking
- Database growth monitoring
- Query pattern analysis
- Performance trend tracking
- Automated alerting

## Working Directory
- Scripts: `tests/integration/`, `scripts/monitoring/`
- Scratchpad: `exploration/scratchpads/phase5_testing.md`
- Reports: `exploration/reports/phase5_testing_report.md`

## Tools & Resources
- Testing: pytest, pytest-benchmark
- Monitoring: logging, metrics collection
- Visualization: grafana, matplotlib
- Current tests: `tests/`

## Success Criteria
- [ ] 90%+ test coverage
- [ ] Automated quality metrics
- [ ] Performance regression detection
- [ ] Continuous monitoring active
- [ ] Clear quality dashboards

## Reporting Format
Provide a structured report including:
1. **Test Coverage**
   - Components tested
   - Coverage percentages
   - Critical paths covered
2. **Quality Metrics**
   - Current baselines
   - Improvement trends
   - Problem areas
3. **Performance Benchmarks**
   - Operation timings
   - Resource usage
   - Scalability limits
4. **Monitoring Setup**
   - Metrics collected
   - Alert thresholds
   - Dashboard screenshots

## Example Code Snippets

### Integration Test Framework
```python
# tests/integration/test_pipeline.py
import pytest
from pathlib import Path
import json
import time

class TestFullPipeline:
    @pytest.fixture
    def sample_documents(self):
        return [
            "Black Sabbath formed in Birmingham in 1968, pioneering heavy metal.",
            "Iron Maiden emerged from London's East End in 1975 during NWOBHM."
        ]
    
    def test_end_to_end_extraction(self, sample_documents, tmp_path):
        """Test complete extraction pipeline"""
        # Step 1: Split documents
        chunks = split_documents(sample_documents, chunk_size=100)
        assert len(chunks) == 2
        
        # Step 2: Extract entities
        extracted = []
        for chunk in chunks:
            entities = extract_entities_enhanced(chunk)
            extracted.append(entities)
        
        # Step 3: Deduplicate
        deduped = deduplicate_entities(extracted)
        assert len(deduped['bands']) >= 2
        
        # Step 4: Generate embeddings
        with_embeddings = generate_embeddings(deduped)
        assert all('embedding' in band for band in with_embeddings['bands'])
        
        # Step 5: Load to database
        db_path = tmp_path / "test.db"
        load_to_kuzu(with_embeddings, db_path)
        
        # Verify
        conn = kuzu.Connection(kuzu.Database(str(db_path)))
        result = conn.execute("MATCH (b:Band) RETURN COUNT(b)")
        assert result.get_next()[0] >= 2

    @pytest.mark.benchmark
    def test_extraction_performance(self, benchmark, sample_documents):
        """Benchmark extraction speed"""
        result = benchmark(extract_entities_enhanced, sample_documents[0])
        assert result.bands  # Ensure valid result
```

### Quality Metrics Implementation
```python
# scripts/monitoring/quality_metrics.py
from sklearn.metrics import precision_recall_fscore_support
import numpy as np

class ExtractionQualityMetrics:
    def __init__(self):
        self.ground_truth = self.load_ground_truth()
    
    def evaluate_extraction(self, extracted_entities, ground_truth_entities):
        """Calculate precision, recall, F1 for extraction"""
        metrics = {}
        
        for entity_type in ['bands', 'people', 'albums']:
            extracted = set(e.name for e in extracted_entities.get(entity_type, []))
            expected = set(e['name'] for e in ground_truth_entities.get(entity_type, []))
            
            tp = len(extracted & expected)
            fp = len(extracted - expected)
            fn = len(expected - extracted)
            
            precision = tp / (tp + fp) if (tp + fp) > 0 else 0
            recall = tp / (tp + fn) if (tp + fn) > 0 else 0
            f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
            
            metrics[entity_type] = {
                'precision': precision,
                'recall': recall,
                'f1': f1,
                'support': len(expected)
            }
        
        return metrics

class SearchQualityMetrics:
    def __init__(self):
        self.relevance_judgments = self.load_relevance_data()
    
    def evaluate_search(self, query, results, k=10):
        """Calculate search quality metrics"""
        relevant = self.relevance_judgments.get(query, [])
        
        # Precision@K
        retrieved = [r['id'] for r in results[:k]]
        relevant_retrieved = len([r for r in retrieved if r in relevant])
        precision_at_k = relevant_retrieved / k
        
        # Mean Reciprocal Rank
        for i, result in enumerate(retrieved):
            if result in relevant:
                mrr = 1 / (i + 1)
                break
        else:
            mrr = 0
        
        # NDCG
        dcg = sum(1 / np.log2(i + 2) for i, r in enumerate(retrieved) if r in relevant)
        idcg = sum(1 / np.log2(i + 2) for i in range(min(len(relevant), k)))
        ndcg = dcg / idcg if idcg > 0 else 0
        
        return {
            'precision_at_k': precision_at_k,
            'mrr': mrr,
            'ndcg': ndcg
        }
```

### Performance Benchmarking
```python
# tests/benchmarks/benchmark_operations.py
import pytest
import time
import psutil
import statistics

class PerformanceBenchmark:
    def __init__(self):
        self.results = []
    
    def benchmark_operation(self, operation, *args, iterations=10):
        """Benchmark any operation"""
        latencies = []
        memory_usage = []
        
        for _ in range(iterations):
            # Memory before
            process = psutil.Process()
            mem_before = process.memory_info().rss / 1024 / 1024  # MB
            
            # Time operation
            start = time.perf_counter()
            result = operation(*args)
            latency = (time.perf_counter() - start) * 1000  # ms
            
            # Memory after
            mem_after = process.memory_info().rss / 1024 / 1024
            
            latencies.append(latency)
            memory_usage.append(mem_after - mem_before)
        
        return {
            'operation': operation.__name__,
            'latency': {
                'mean': statistics.mean(latencies),
                'median': statistics.median(latencies),
                'p95': statistics.quantiles(latencies, n=20)[18],
                'p99': statistics.quantiles(latencies, n=100)[98]
            },
            'memory': {
                'mean': statistics.mean(memory_usage),
                'max': max(memory_usage)
            }
        }

# Specific benchmarks
def benchmark_extraction():
    text = "Sample metal history text..." * 100
    benchmark = PerformanceBenchmark()
    return benchmark.benchmark_operation(extract_entities_enhanced, text)

def benchmark_vector_search():
    query = "British heavy metal bands"
    benchmark = PerformanceBenchmark()
    return benchmark.benchmark_operation(vector_search, query)

def benchmark_graph_query():
    query = "MATCH (b:Band)-[:INFLUENCED_BY*1..3]->(b2:Band) RETURN b, b2"
    benchmark = PerformanceBenchmark()
    return benchmark.benchmark_operation(execute_query, query)
```

### Continuous Monitoring
```python
# scripts/monitoring/continuous_monitor.py
import logging
import json
from datetime import datetime
import schedule

class QualityMonitor:
    def __init__(self, log_file="quality_metrics.log"):
        self.logger = self.setup_logger(log_file)
        self.metrics_history = []
    
    def monitor_extraction_quality(self):
        """Run periodic quality checks"""
        # Sample recent extractions
        recent_extractions = self.get_recent_extractions()
        
        # Evaluate quality
        metrics = ExtractionQualityMetrics()
        results = []
        
        for extraction in recent_extractions:
            quality = metrics.evaluate_extraction(
                extraction['extracted'],
                extraction['ground_truth']
            )
            results.append(quality)
        
        # Aggregate metrics
        avg_f1 = statistics.mean([r['bands']['f1'] for r in results])
        
        # Log and alert
        self.logger.info(f"Extraction Quality - Avg F1: {avg_f1:.3f}")
        
        if avg_f1 < 0.8:
            self.alert(f"Extraction quality degraded: F1={avg_f1:.3f}")
        
        return avg_f1
    
    def monitor_search_performance(self):
        """Monitor search latency and quality"""
        test_queries = [
            "heavy metal bands from UK",
            "thrash metal albums 1980s",
            "doom metal pioneers"
        ]
        
        latencies = []
        for query in test_queries:
            start = time.time()
            results = vector_search(query)
            latency = (time.time() - start) * 1000
            latencies.append(latency)
        
        avg_latency = statistics.mean(latencies)
        self.logger.info(f"Search Performance - Avg Latency: {avg_latency:.1f}ms")
        
        if avg_latency > 100:
            self.alert(f"Search latency high: {avg_latency:.1f}ms")
    
    def monitor_database_growth(self):
        """Track database size and entity counts"""
        conn = get_db_connection()
        
        stats = {}
        for entity_type in ['Band', 'Person', 'Album', 'Song']:
            count = conn.execute(f"MATCH (n:{entity_type}) RETURN COUNT(n)").get_next()[0]
            stats[entity_type] = count
        
        self.logger.info(f"Database Stats: {json.dumps(stats)}")
        self.metrics_history.append({
            'timestamp': datetime.now().isoformat(),
            'stats': stats
        })
        
        # Check growth rate
        if len(self.metrics_history) > 2:
            growth_rate = self.calculate_growth_rate()
            if growth_rate < 0.01:  # Less than 1% growth
                self.alert("Database growth stalled")

# Schedule monitoring
monitor = QualityMonitor()
schedule.every(1).hours.do(monitor.monitor_extraction_quality)
schedule.every(30).minutes.do(monitor.monitor_search_performance)
schedule.every(1).days.do(monitor.monitor_database_growth)
```

### Test Data Generation
```python
def generate_test_data():
    """Generate comprehensive test dataset"""
    test_data = {
        'extraction_tests': [
            {
                'input': "Metallica formed in Los Angeles in 1981 by James Hetfield and Lars Ulrich.",
                'expected': {
                    'bands': [{'name': 'Metallica', 'formed_year': 1981, 'location': 'Los Angeles'}],
                    'people': [
                        {'name': 'James Hetfield', 'roles': ['vocalist', 'guitarist']},
                        {'name': 'Lars Ulrich', 'roles': ['drummer']}
                    ]
                }
            }
        ],
        'search_tests': [
            {
                'query': 'thrash metal bands California',
                'relevant_ids': ['metallica', 'megadeth', 'exodus', 'testament']
            }
        ],
        'graph_tests': [
            {
                'query': 'genre evolution from heavy metal',
                'expected_paths': [
                    ['heavy metal', 'thrash metal'],
                    ['heavy metal', 'doom metal'],
                    ['heavy metal', 'power metal']
                ]
            }
        ]
    }
    
    return test_data
```

## Critical Tests to Implement
1. **Extraction accuracy** on known corpus
2. **Deduplication effectiveness**
3. **Vector search relevance**
4. **Graph query performance**
5. **Data consistency validation**
6. **API response times**
7. **Memory usage under load**
8. **Concurrent request handling**
9. **Error recovery mechanisms**
10. **Data update workflows**

## Timeline
- Day 1: Build integration test suite
- Day 2: Implement quality metrics
- Day 3: Set up continuous monitoring
- Day 4: Create dashboards and documentation

Focus on automated, repeatable tests that catch regressions early!