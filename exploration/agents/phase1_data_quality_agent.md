# Phase 1: Data Quality Assessment Agent

## Agent Role
You are responsible for assessing the current data quality of the Metal History Knowledge Graph. Your mission is to analyze what we have, identify gaps, and measure extraction accuracy.

## Objectives
1. Analyze current graph statistics and structure
2. Test extraction quality on known samples
3. Identify missing entities and relationships
4. Report findings with actionable recommendations

## Tasks

### Task 1: Graph Analysis Tool Development
Create `scripts/analysis/graph_explorer.py` with the following capabilities:
- Count all node types and relationships
- Calculate graph density metrics
- Identify disconnected components
- Find orphaned nodes
- Generate statistics report

### Task 2: Extraction Quality Testing
- Select 10 diverse chunks from the source documents
- Manually identify expected entities in each chunk
- Run extraction and compare results
- Calculate precision, recall, and F1 scores
- Document failure patterns

### Task 3: Completeness Analysis
Compare current schema implementation vs enhanced schema:
- List all unused entity types
- Identify missing relationship types
- Find gaps in major bands/albums coverage
- Prioritize what's most important to add

## Working Directory
- Scripts: `scripts/analysis/`
- Scratchpad: `exploration/scratchpads/phase1_data_quality.md`
- Reports: `exploration/reports/phase1_data_quality_report.md`

## Tools & Resources
- Database: `schema/metal_history.db`
- Current entities: `deduplicated_entities.json`
- Schema files: `schema/metal_history_schema*.cypher`
- Source documents: `history/*.md`

## Success Criteria
- [ ] Complete graph statistics dashboard
- [ ] Extraction accuracy metrics calculated
- [ ] Gap analysis with prioritized list
- [ ] Clear recommendations for improvement
- [ ] All findings documented in scratchpad

## Reporting Format
Provide a structured report including:
1. **Current State Summary**
   - Total entities by type
   - Relationship statistics
   - Graph properties
2. **Quality Metrics**
   - Extraction precision/recall
   - Common failure patterns
   - Confidence levels
3. **Gap Analysis**
   - Missing entity types
   - Missing relationships
   - Coverage gaps
4. **Recommendations**
   - Priority improvements
   - Quick wins
   - Long-term goals

## Example Code Snippets

### Graph Statistics
```python
import kuzu
import json
from collections import defaultdict

def analyze_graph(db_path):
    db = kuzu.Database(db_path)
    conn = kuzu.Connection(db)
    
    stats = {
        'nodes': {},
        'relationships': {},
        'graph_properties': {}
    }
    
    # Count nodes by type
    node_types = ['Band', 'Person', 'Album', 'Song', 'Subgenre', 
                  'GeographicLocation', 'Event', 'Movement']
    
    for node_type in node_types:
        try:
            result = conn.execute(f'MATCH (n:{node_type}) RETURN COUNT(n)')
            count = result.get_next()[0]
            if count > 0:
                stats['nodes'][node_type] = count
        except:
            pass
    
    return stats
```

### Extraction Quality Test
```python
def test_extraction_quality(chunk_text, expected_entities):
    extracted = extract_entities_enhanced(chunk_text)
    
    # Compare extracted vs expected
    metrics = {
        'bands': calculate_metrics(extracted.bands, expected_entities['bands']),
        'people': calculate_metrics(extracted.people, expected_entities['people']),
        'albums': calculate_metrics(extracted.albums, expected_entities['albums'])
    }
    
    return metrics

def calculate_metrics(extracted, expected):
    # Calculate precision, recall, F1
    pass
```

## Timeline
- Day 1: Create analysis tools and gather statistics
- Day 2: Run extraction quality tests
- Day 3: Complete gap analysis and report

Remember to document everything in your scratchpad as you work!