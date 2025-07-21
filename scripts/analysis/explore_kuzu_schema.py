#!/usr/bin/env python3
"""
Explore Kuzu database schema to understand available tables and relationships
"""

import kuzu
from pathlib import Path

def explore_schema(db_path: str):
    """Explore the Kuzu database schema"""
    db = kuzu.Database(db_path)
    conn = kuzu.Connection(db)
    
    print("=== KUZU DATABASE SCHEMA EXPLORATION ===\n")
    
    # Try to get node tables
    try:
        # Check if we can use CALL
        result = conn.execute("CALL show_tables() RETURN *;")
        print("Available tables:")
        while result.has_next():
            print(f"  - {result.get_next()}")
    except Exception as e:
        print(f"show_tables() error: {e}")
    
    # Try alternative approaches
    print("\n=== Testing Individual Node Types ===")
    
    # Common node types to test
    node_types = [
        'Band', 'Person', 'Album', 'Song', 'Genre', 'Subgenre',
        'GeographicLocation', 'Festival', 'Venue', 'Label',
        'Award', 'Tour', 'HistoricalEvent'
    ]
    
    existing_types = []
    
    for node_type in node_types:
        try:
            query = f"MATCH (n:{node_type}) RETURN COUNT(n) as count LIMIT 1"
            result = conn.execute(query)
            if result.has_next():
                count = result.get_next()[0]
                print(f"{node_type}: {count} nodes")
                existing_types.append(node_type)
        except Exception as e:
            if "does not exist" not in str(e):
                print(f"{node_type}: Error - {e}")
    
    print(f"\nFound {len(existing_types)} node types")
    
    # Test relationship types
    print("\n=== Testing Relationship Types ===")
    
    # For each node type, try to find relationships
    for node_type in existing_types[:3]:  # Test first 3 to avoid too much output
        print(f"\nRelationships for {node_type}:")
        try:
            # Outgoing relationships
            query = f"""
            MATCH (n:{node_type})-[r]->(m)
            RETURN TYPE(r) as rel_type, COUNT(*) as count
            GROUP BY rel_type
            ORDER BY count DESC
            LIMIT 5
            """
            result = conn.execute(query)
            has_rels = False
            while result.has_next():
                row = result.get_next()
                print(f"  -> {row[0]}: {row[1]} relationships")
                has_rels = True
            
            if not has_rels:
                print("  No outgoing relationships found")
                
        except Exception as e:
            print(f"  Error querying relationships: {e}")
    
    # Try a simple query
    print("\n=== Testing Simple Queries ===")
    
    try:
        # Test Band query
        query = "MATCH (b:Band) RETURN b.name as name, b.formed_year as year ORDER BY year LIMIT 5"
        result = conn.execute(query)
        print("\nOldest bands:")
        while result.has_next():
            row = result.get_next()
            print(f"  - {row[0]} ({row[1]})")
    except Exception as e:
        print(f"Band query error: {e}")
    
    # Test path queries
    print("\n=== Testing Path Queries ===")
    
    try:
        query = """
        MATCH (b1:Band {name: 'Black Sabbath'})-[:INFLUENCED_BY*1..2]->(b2:Band)
        RETURN b2.name as influenced_band
        LIMIT 5
        """
        result = conn.execute(query)
        print("\nBands influenced by Black Sabbath (1-2 hops):")
        while result.has_next():
            print(f"  - {result.get_next()[0]}")
    except Exception as e:
        print(f"Path query error: {e}")
    
    conn.close()

if __name__ == "__main__":
    db_path = "schema/metal_history.db"
    explore_schema(db_path)