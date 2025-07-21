#!/usr/bin/env python3
"""Interactive database explorer for the Metal History Knowledge Graph"""

import kuzu
import json
from pathlib import Path

class DatabaseExplorer:
    def __init__(self, db_path='data/database/metal_history.db'):
        self.db = kuzu.Database(db_path)
        self.conn = kuzu.Connection(self.db)
    
    def get_schema_info(self):
        """Get all tables and their schemas"""
        print("=== DATABASE SCHEMA ===\n")
        
        # Get all tables
        tables_result = self.conn.execute("CALL show_tables() RETURN *")
        tables = []
        while tables_result.has_next():
            table_info = tables_result.get_next()
            table_name = table_info[1]
            table_type = table_info[2]
            tables.append((table_name, table_type))
        
        # Separate nodes and relationships
        nodes = [t[0] for t in tables if t[1] == 'NODE']
        rels = [t[0] for t in tables if t[1] == 'REL']
        
        print(f"Node Tables ({len(nodes)}):")
        for node in sorted(nodes):
            print(f"  - {node}")
            # Get properties
            try:
                props_result = self.conn.execute(f"CALL table_info('{node}') RETURN *")
                props = []
                while props_result.has_next():
                    prop = props_result.get_next()
                    props.append(f"{prop[1]}:{prop[2]}")
                print(f"    Properties: {', '.join(props[:5])}{'...' if len(props) > 5 else ''}")
            except:
                pass
        
        print(f"\nRelationship Tables ({len(rels)}):")
        for rel in sorted(rels):
            print(f"  - {rel}")
    
    def get_counts(self):
        """Get counts for all entities"""
        print("\n=== ENTITY COUNTS ===\n")
        
        # Node counts
        for table in ['Band', 'Person', 'Album', 'Song', 'Subgenre', 'GeographicLocation', 
                      'Era', 'RecordLabel', 'Studio', 'CulturalEvent', 'MediaOutlet']:
            try:
                result = self.conn.execute(f"MATCH (n:{table}) RETURN count(n) as count")
                count = result.get_next()[0] if result.has_next() else 0
                if count > 0:
                    print(f"{table}: {count}")
            except:
                pass
    
    def sample_data(self, limit=3):
        """Show sample data from main entities"""
        print("\n=== SAMPLE DATA ===\n")
        
        # Sample bands
        print(f"Sample Bands (limit {limit}):")
        result = self.conn.execute(f"MATCH (b:Band) RETURN b.name, b.origin_city, b.origin_country, b.status LIMIT {limit}")
        while result.has_next():
            row = result.get_next()
            print(f"  - {row[0]} | From: {row[1] or 'Unknown'}, {row[2] or 'Unknown'} | Status: {row[3]}")
        
        # Sample albums
        print(f"\nSample Albums (limit {limit}):")
        result = self.conn.execute(f"MATCH (a:Album) RETURN a.title, a.release_year LIMIT {limit}")
        while result.has_next():
            row = result.get_next()
            print(f"  - {row[0]} ({row[1] or 'Unknown year'})")
        
        # Sample people
        print(f"\nSample People (limit {limit}):")
        result = self.conn.execute(f"MATCH (p:Person) RETURN p.name, p.instruments, p.nationality LIMIT {limit}")
        while result.has_next():
            row = result.get_next()
            instruments = row[1] if row[1] else ['Unknown']
            print(f"  - {row[0]} | Instruments: {', '.join(instruments)} | Nationality: {row[2] or 'Unknown'}")
    
    def explore_relationships(self):
        """Show relationship patterns"""
        print("\n=== RELATIONSHIP PATTERNS ===\n")
        
        # Common patterns
        patterns = [
            ("Band -> Album", "MATCH (b:Band)-[r:RELEASED]->(a:Album) RETURN b.name, a.title LIMIT 5"),
            ("Band -> Band (Influence)", "MATCH (b1:Band)-[r:INFLUENCED_BY]->(b2:Band) RETURN b1.name, b2.name LIMIT 5"),
            ("Band -> Genre", "MATCH (b:Band)-[r:PLAYS_GENRE]->(g:Subgenre) RETURN b.name, g.name LIMIT 5"),
            ("Person -> Band", "MATCH (p:Person)-[r:MEMBER_OF]->(b:Band) RETURN p.name, b.name LIMIT 5"),
            ("Album -> Studio", "MATCH (a:Album)-[r:RECORDED_AT]->(s:Studio) RETURN a.title, s.name LIMIT 5"),
        ]
        
        for pattern_name, query in patterns:
            print(f"{pattern_name}:")
            try:
                result = self.conn.execute(query)
                count = 0
                while result.has_next():
                    row = result.get_next()
                    print(f"  - {row[0]} → {row[1]}")
                    count += 1
                if count == 0:
                    print("  (No relationships found)")
            except Exception as e:
                print(f"  Error: {e}")
            print()
    
    def search_band(self, band_name):
        """Search for a specific band and its relationships"""
        print(f"\n=== SEARCHING FOR: {band_name} ===\n")
        
        # Find band
        result = self.conn.execute(
            "MATCH (b:Band) WHERE b.name =~ $name RETURN b",
            {"name": f".*{band_name}.*"}
        )
        
        bands = []
        while result.has_next():
            band = result.get_next()[0]
            bands.append(band)
            print(f"Found: {band['name']}")
            print(f"  Origin: {band.get('origin_city', 'Unknown')}, {band.get('origin_country', 'Unknown')}")
            print(f"  Status: {band.get('status', 'Unknown')}")
            print(f"  Description: {band.get('description', 'No description')[:100]}...")
        
        if not bands:
            print("No bands found matching that name.")
            return
        
        # Get relationships for first match
        band_name = bands[0]['name']
        print(f"\nRelationships for {band_name}:")
        
        # Albums
        result = self.conn.execute(
            "MATCH (b:Band {name: $name})-[:RELEASED]->(a:Album) RETURN a.title",
            {"name": band_name}
        )
        albums = []
        while result.has_next():
            albums.append(result.get_next()[0])
        if albums:
            print(f"  Albums: {', '.join(albums)}")
        
        # Influences
        result = self.conn.execute(
            "MATCH (b:Band {name: $name})-[:INFLUENCED_BY]->(b2:Band) RETURN b2.name",
            {"name": band_name}
        )
        influences = []
        while result.has_next():
            influences.append(result.get_next()[0])
        if influences:
            print(f"  Influenced by: {', '.join(influences)}")
    
    def custom_query(self, query):
        """Execute a custom Cypher query"""
        try:
            result = self.conn.execute(query)
            rows = []
            while result.has_next():
                rows.append(result.get_next())
            return rows
        except Exception as e:
            return f"Error: {e}"

def main():
    explorer = DatabaseExplorer()
    
    # Show schema
    explorer.get_schema_info()
    
    # Show counts
    explorer.get_counts()
    
    # Show sample data
    explorer.sample_data(limit=5)
    
    # Explore relationships
    explorer.explore_relationships()
    
    # Search for specific bands
    for band in ["Black Sabbath", "Iron Maiden", "Metallica"]:
        explorer.search_band(band)
    
    print("\n=== CUSTOM QUERIES ===")
    print("\nYou can now use explorer.custom_query() to run any Cypher query.")
    print("Example: explorer.custom_query('MATCH (b:Band) RETURN b.name LIMIT 10')")

if __name__ == "__main__":
    main()