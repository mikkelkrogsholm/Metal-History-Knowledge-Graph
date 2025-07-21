# Phase 3: Graph Properties Testing Agent

## Agent Role
You are responsible for analyzing and testing the graph properties of the Metal History Knowledge Graph. Your mission is to understand the graph's structure, test complex queries, and validate relationships.

## Objectives
1. Calculate comprehensive graph metrics
2. Test and optimize graph traversal queries
3. Validate relationship consistency
4. Identify structural patterns and anomalies

## Tasks

### Task 1: Graph Analytics Tool
Create `scripts/analysis/graph_metrics.py` with:
- Degree distribution analysis
- Clustering coefficient calculation
- Connected components detection
- Centrality measures (betweenness, closeness, eigenvector)
- Path analysis algorithms

### Task 2: Query Pattern Testing
Implement and test common query patterns:
- Band influence networks
- Genre evolution trees
- Geographic scene clustering
- Temporal activity analysis
- Collaboration networks
- Multi-hop relationship queries

### Task 3: Relationship Validation
- Check temporal consistency
- Validate bidirectional relationships
- Find logical inconsistencies
- Identify missing critical edges
- Test referential integrity

## Working Directory
- Scripts: `scripts/analysis/`
- Scratchpad: `exploration/scratchpads/phase3_graph_properties.md`
- Reports: `exploration/reports/phase3_graph_properties_report.md`

## Tools & Resources
- Database: `schema/metal_history.db`
- Kuzu documentation: https://kuzudb.com/
- NetworkX for analysis (if needed)
- Visualization: pyvis, matplotlib

## Success Criteria
- [ ] Complete graph metrics calculated
- [ ] Query performance < 100ms for common patterns
- [ ] All relationship inconsistencies identified
- [ ] Visualization of graph structure
- [ ] Optimization recommendations provided

## Reporting Format
Provide a structured report including:
1. **Graph Metrics**
   - Statistical properties
   - Structural analysis
   - Visualization plots
2. **Query Performance**
   - Query patterns tested
   - Execution times
   - Optimization applied
3. **Validation Results**
   - Inconsistencies found
   - Data quality issues
   - Suggested fixes
4. **Insights**
   - Interesting patterns
   - Central nodes/entities
   - Community structure

## Example Code Snippets

### Graph Metrics Calculation
```python
import kuzu
import numpy as np
from collections import defaultdict

class GraphAnalyzer:
    def __init__(self, db_path):
        self.db = kuzu.Database(db_path)
        self.conn = kuzu.Connection(self.db)
    
    def calculate_degree_distribution(self):
        """Calculate in/out degree for all nodes"""
        query = """
        MATCH (n)
        OPTIONAL MATCH (n)-[r]->()
        WITH n, COUNT(r) as out_degree
        OPTIONAL MATCH ()-[r2]->(n)
        RETURN labels(n)[0] as type, 
               n.name as name, 
               out_degree, 
               COUNT(r2) as in_degree
        """
        result = self.conn.execute(query)
        return self.process_degree_results(result)
    
    def find_connected_components(self):
        """Find disconnected subgraphs"""
        # Implement using BFS/DFS
        pass
    
    def calculate_clustering_coefficient(self):
        """Measure how densely connected the graph is"""
        # For each node, calculate ratio of actual vs possible connections
        pass
```

### Query Pattern Implementation
```python
def find_influence_chains(conn, start_band: str, max_depth: int = 3):
    """Find influence paths from a band"""
    query = f"""
    MATCH path = (b1:Band {{name: $start_band}})-[:INFLUENCED_BY*1..{max_depth}]->(b2:Band)
    RETURN path, length(path) as depth
    ORDER BY depth
    """
    return conn.execute(query, {"start_band": start_band})

def analyze_genre_evolution(conn):
    """Trace genre evolution paths"""
    query = """
    MATCH (g1:Subgenre)-[:EVOLVED_INTO]->(g2:Subgenre)
    OPTIONAL MATCH (g1)<-[:PLAYS_GENRE]-(b1:Band)
    OPTIONAL MATCH (g2)<-[:PLAYS_GENRE]-(b2:Band)
    RETURN g1.name, g2.name, COUNT(DISTINCT b1) as bands_g1, COUNT(DISTINCT b2) as bands_g2
    """
    return conn.execute(query)

def find_geographic_clusters(conn):
    """Find geographic metal scenes"""
    query = """
    MATCH (b:Band)-[:FORMED_IN]->(l:GeographicLocation)
    WITH l, COLLECT(b) as bands
    WHERE SIZE(bands) > 2
    RETURN l.city, l.country, SIZE(bands) as band_count, bands
    ORDER BY band_count DESC
    """
    return conn.execute(query)
```

### Relationship Validation
```python
def validate_temporal_consistency(conn):
    """Check for temporal anomalies"""
    issues = []
    
    # Check if bands formed before members were born
    query = """
    MATCH (p:Person)-[:MEMBER_OF]->(b:Band)
    WHERE p.birth_year > b.formed_year
    RETURN p.name, p.birth_year, b.name, b.formed_year
    """
    result = conn.execute(query)
    
    # Check if albums released before band formed
    query2 = """
    MATCH (b:Band)-[:RELEASED]->(a:Album)
    WHERE a.release_year < b.formed_year
    RETURN b.name, b.formed_year, a.title, a.release_year
    """
    result2 = conn.execute(query2)
    
    return issues

def check_bidirectional_consistency(conn):
    """Verify bidirectional relationships are consistent"""
    # Example: If A influenced B, B should not influence A
    query = """
    MATCH (b1:Band)-[:INFLUENCED_BY]->(b2:Band)
    MATCH (b2)-[:INFLUENCED_BY]->(b1)
    RETURN b1.name, b2.name
    """
    return conn.execute(query)
```

### Visualization
```python
from pyvis.network import Network
import networkx as nx

def visualize_band_network(conn, center_band: str, depth: int = 2):
    """Create interactive visualization of band relationships"""
    net = Network(height="750px", width="100%", bgcolor="#222222", font_color="white")
    
    # Get relationships around center band
    query = f"""
    MATCH (b1:Band {{name: $center_band}})-[r*1..{depth}]-(b2:Band)
    RETURN DISTINCT b1, type(r), b2
    """
    
    result = conn.execute(query, {"center_band": center_band})
    
    # Build network
    for row in result:
        net.add_node(row[0].name, label=row[0].name)
        net.add_node(row[2].name, label=row[2].name)
        net.add_edge(row[0].name, row[2].name, title=row[1])
    
    return net
```

## Test Queries to Benchmark
1. Find all bands influenced by Black Sabbath (multi-hop)
2. Trace thrash metal evolution path
3. Find most influential bands (PageRank-style)
4. Geographic clustering of NWOBHM bands
5. Temporal analysis of genre popularity
6. Find shortest path between two bands
7. Identify genre-crossing bands
8. Find collaboration networks
9. Trace member movements between bands
10. Identify isolated subgraphs

## Timeline
- Day 1: Implement graph metrics calculations
- Day 2: Test query patterns and optimize
- Day 3: Validate relationships and visualize

Document all findings, especially interesting patterns and anomalies!