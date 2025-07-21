#!/usr/bin/env python3
"""
Database optimization script for Metal History Knowledge Graph
Creates indexes, analyzes query patterns, and optimizes performance
"""

import kuzu
import time
import json
import logging
from typing import Dict, List, Tuple
import argparse
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DatabaseOptimizer:
    """Handles database optimization tasks"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.db = kuzu.Database(db_path)
        self.conn = kuzu.Connection(self.db)
        
    def create_indexes(self) -> Dict[str, bool]:
        """Create optimized indexes for common query patterns"""
        indexes = [
            # Entity lookup indexes
            ("Band", "id", "CREATE INDEX idx_band_id ON Band(id)"),
            ("Band", "name", "CREATE INDEX idx_band_name ON Band(name)"),
            ("Band", "formed_year", "CREATE INDEX idx_band_year ON Band(formed_year)"),
            
            ("Album", "id", "CREATE INDEX idx_album_id ON Album(id)"),
            ("Album", "title", "CREATE INDEX idx_album_title ON Album(title)"),
            ("Album", "release_year", "CREATE INDEX idx_album_year ON Album(release_year)"),
            
            ("Person", "id", "CREATE INDEX idx_person_id ON Person(id)"),
            ("Person", "name", "CREATE INDEX idx_person_name ON Person(name)"),
            
            ("Subgenre", "name", "CREATE INDEX idx_genre_name ON Subgenre(name)"),
            
            ("GeographicLocation", "name", "CREATE INDEX idx_location_name ON GeographicLocation(name)"),
            ("GeographicLocation", "city", "CREATE INDEX idx_location_city ON GeographicLocation(city)"),
            ("GeographicLocation", "country", "CREATE INDEX idx_location_country ON GeographicLocation(country)"),
            
            # Composite indexes for common queries
            ("Band", "formed_year,name", "CREATE INDEX idx_band_year_name ON Band(formed_year, name)"),
            ("Album", "release_year,title", "CREATE INDEX idx_album_year_title ON Album(release_year, title)"),
        ]
        
        results = {}
        for entity, columns, query in indexes:
            try:
                start_time = time.time()
                self.conn.execute(query)
                duration = time.time() - start_time
                logger.info(f"Created index on {entity}.{columns} in {duration:.2f}s")
                results[f"{entity}.{columns}"] = True
            except Exception as e:
                if "already exists" in str(e):
                    logger.info(f"Index on {entity}.{columns} already exists")
                    results[f"{entity}.{columns}"] = True
                else:
                    logger.error(f"Failed to create index on {entity}.{columns}: {e}")
                    results[f"{entity}.{columns}"] = False
                    
        return results
    
    def analyze_query_performance(self) -> List[Dict]:
        """Profile common query patterns"""
        test_queries = [
            {
                "name": "Band lookup by ID",
                "query": "MATCH (b:Band {id: 'band_black_sabbath'}) RETURN b",
                "expected_time": 10
            },
            {
                "name": "Band search by name pattern",
                "query": "MATCH (b:Band) WHERE b.name =~ '.*metal.*' RETURN b LIMIT 10",
                "expected_time": 50
            },
            {
                "name": "Genre bands",
                "query": """
                    MATCH (b:Band)-[:PLAYS_GENRE]->(g:Subgenre {name: 'heavy metal'})
                    RETURN b LIMIT 20
                """,
                "expected_time": 30
            },
            {
                "name": "Influence network (depth 2)",
                "query": """
                    MATCH path = (b:Band {name: 'Black Sabbath'})-[:INFLUENCED_BY*1..2]-(other:Band)
                    RETURN path LIMIT 50
                """,
                "expected_time": 100
            },
            {
                "name": "Timeline query",
                "query": """
                    MATCH (b:Band)
                    WHERE b.formed_year >= 1980 AND b.formed_year <= 1990
                    RETURN b.formed_year, b.name
                    ORDER BY b.formed_year
                """,
                "expected_time": 50
            },
            {
                "name": "Album with band join",
                "query": """
                    MATCH (b:Band)-[:RELEASED]->(a:Album)
                    WHERE a.release_year = 1970
                    RETURN b.name, a.title
                """,
                "expected_time": 40
            },
            {
                "name": "Complex aggregation",
                "query": """
                    MATCH (b:Band)-[:ORIGINATED_IN]->(loc:GeographicLocation)
                    WITH loc.country as country, COUNT(b) as band_count
                    WHERE band_count > 5
                    RETURN country, band_count
                    ORDER BY band_count DESC
                """,
                "expected_time": 80
            },
            {
                "name": "Member instruments",
                "query": """
                    MATCH (p:Person)-[:PLAYS]->(i:Instrument)
                    WHERE i.name = 'guitar'
                    MATCH (p)-[:MEMBER_OF]->(b:Band)
                    RETURN p.name, COLLECT(DISTINCT b.name) as bands
                    LIMIT 20
                """,
                "expected_time": 60
            }
        ]
        
        results = []
        for test in test_queries:
            try:
                # Warm up
                self.conn.execute(test["query"])
                
                # Measure performance (average of 3 runs)
                times = []
                for _ in range(3):
                    start_time = time.time()
                    result = self.conn.execute(test["query"])
                    # Consume results
                    count = 0
                    while result.has_next():
                        result.get_next()
                        count += 1
                    duration = (time.time() - start_time) * 1000  # Convert to ms
                    times.append(duration)
                
                avg_time = sum(times) / len(times)
                min_time = min(times)
                max_time = max(times)
                
                performance = {
                    "query_name": test["name"],
                    "avg_time_ms": round(avg_time, 2),
                    "min_time_ms": round(min_time, 2),
                    "max_time_ms": round(max_time, 2),
                    "expected_time_ms": test["expected_time"],
                    "performance": "GOOD" if avg_time <= test["expected_time"] else "NEEDS_OPTIMIZATION",
                    "row_count": count
                }
                
                results.append(performance)
                
                if performance["performance"] == "GOOD":
                    logger.info(f"✓ {test['name']}: {avg_time:.2f}ms (expected <{test['expected_time']}ms)")
                else:
                    logger.warning(f"✗ {test['name']}: {avg_time:.2f}ms (expected <{test['expected_time']}ms)")
                    
            except Exception as e:
                logger.error(f"Failed to run query '{test['name']}': {e}")
                results.append({
                    "query_name": test["name"],
                    "error": str(e)
                })
                
        return results
    
    def get_database_statistics(self) -> Dict:
        """Gather database statistics"""
        stats = {}
        
        # Entity counts
        entity_queries = {
            "bands": "MATCH (b:Band) RETURN COUNT(b)",
            "albums": "MATCH (a:Album) RETURN COUNT(a)",
            "people": "MATCH (p:Person) RETURN COUNT(p)",
            "songs": "MATCH (s:Song) RETURN COUNT(s)",
            "genres": "MATCH (g:Subgenre) RETURN COUNT(g)",
            "locations": "MATCH (l:GeographicLocation) RETURN COUNT(l)",
            "instruments": "MATCH (i:Instrument) RETURN COUNT(i)"
        }
        
        for key, query in entity_queries.items():
            try:
                result = self.conn.execute(query)
                if result.has_next():
                    stats[key] = result.get_next()[0]
            except Exception as e:
                logger.error(f"Failed to get {key} count: {e}")
                stats[key] = 0
        
        # Relationship counts
        rel_queries = {
            "band_genres": "MATCH ()-[r:PLAYS_GENRE]->() RETURN COUNT(r)",
            "band_members": "MATCH ()-[r:MEMBER_OF]->() RETURN COUNT(r)",
            "album_releases": "MATCH ()-[r:RELEASED]->() RETURN COUNT(r)",
            "influences": "MATCH ()-[r:INFLUENCED_BY]->() RETURN COUNT(r)",
            "locations": "MATCH ()-[r:ORIGINATED_IN]->() RETURN COUNT(r)"
        }
        
        stats["relationships"] = {}
        for key, query in rel_queries.items():
            try:
                result = self.conn.execute(query)
                if result.has_next():
                    stats["relationships"][key] = result.get_next()[0]
            except Exception as e:
                logger.error(f"Failed to get {key} relationship count: {e}")
                stats["relationships"][key] = 0
        
        # Data quality metrics
        quality_queries = {
            "bands_with_year": "MATCH (b:Band) WHERE b.formed_year IS NOT NULL RETURN COUNT(b)",
            "bands_with_location": "MATCH (b:Band)-[:ORIGINATED_IN]->() RETURN COUNT(DISTINCT b)",
            "bands_with_genres": "MATCH (b:Band)-[:PLAYS_GENRE]->() RETURN COUNT(DISTINCT b)",
            "albums_with_year": "MATCH (a:Album) WHERE a.release_year IS NOT NULL RETURN COUNT(a)",
            "people_with_instruments": "MATCH (p:Person)-[:PLAYS]->() RETURN COUNT(DISTINCT p)"
        }
        
        stats["data_quality"] = {}
        for key, query in quality_queries.items():
            try:
                result = self.conn.execute(query)
                if result.has_next():
                    count = result.get_next()[0]
                    # Calculate percentage
                    if key.startswith("bands_"):
                        total = stats.get("bands", 1)
                    elif key.startswith("albums_"):
                        total = stats.get("albums", 1)
                    elif key.startswith("people_"):
                        total = stats.get("people", 1)
                    else:
                        total = 1
                    
                    percentage = (count / total * 100) if total > 0 else 0
                    stats["data_quality"][key] = {
                        "count": count,
                        "percentage": round(percentage, 2)
                    }
            except Exception as e:
                logger.error(f"Failed to get {key} quality metric: {e}")
        
        return stats
    
    def optimize_for_production(self) -> Dict:
        """Run all optimization tasks"""
        logger.info("Starting database optimization...")
        
        results = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "database_path": self.db_path
        }
        
        # Create indexes
        logger.info("Creating indexes...")
        results["indexes"] = self.create_indexes()
        
        # Get statistics
        logger.info("Gathering database statistics...")
        results["statistics"] = self.get_database_statistics()
        
        # Analyze query performance
        logger.info("Analyzing query performance...")
        results["query_performance"] = self.analyze_query_performance()
        
        # Calculate overall health score
        total_queries = len(results["query_performance"])
        good_queries = sum(1 for q in results["query_performance"] 
                          if q.get("performance") == "GOOD")
        
        results["health_score"] = {
            "score": round((good_queries / total_queries * 100) if total_queries > 0 else 0, 2),
            "total_queries": total_queries,
            "optimized_queries": good_queries,
            "needs_optimization": total_queries - good_queries
        }
        
        logger.info(f"Optimization complete. Health score: {results['health_score']['score']}%")
        
        return results


def main():
    parser = argparse.ArgumentParser(description="Optimize Metal History database for production")
    parser.add_argument("--db-path", default="../../schema/metal_history.db",
                       help="Path to the Kuzu database")
    parser.add_argument("--output", default="optimization_report.json",
                       help="Output file for optimization report")
    
    args = parser.parse_args()
    
    # Check if database exists
    db_path = Path(args.db_path)
    if not db_path.exists():
        logger.error(f"Database not found at {db_path}")
        return 1
    
    # Run optimization
    optimizer = DatabaseOptimizer(str(db_path))
    results = optimizer.optimize_for_production()
    
    # Save results
    output_path = Path(args.output)
    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2)
    
    logger.info(f"Optimization report saved to {output_path}")
    
    # Print summary
    print("\n" + "="*60)
    print("DATABASE OPTIMIZATION SUMMARY")
    print("="*60)
    print(f"Total entities: {sum(results['statistics'].get(k, 0) for k in ['bands', 'albums', 'people', 'songs'])}")
    print(f"Health score: {results['health_score']['score']}%")
    print(f"Optimized queries: {results['health_score']['optimized_queries']}/{results['health_score']['total_queries']}")
    
    if results['health_score']['needs_optimization'] > 0:
        print("\nQueries needing optimization:")
        for query in results['query_performance']:
            if query.get('performance') == 'NEEDS_OPTIMIZATION':
                print(f"  - {query['query_name']}: {query['avg_time_ms']}ms (target: {query['expected_time_ms']}ms)")
    
    return 0


if __name__ == "__main__":
    exit(main())