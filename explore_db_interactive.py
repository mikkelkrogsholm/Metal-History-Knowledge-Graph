#!/usr/bin/env python3
"""Interactive database explorer for the Metal History Knowledge Graph"""

import kuzu
from pathlib import Path

def main():
    print("=== Metal History Database Explorer ===\n")
    
    # Connect to database
    db_path = 'data/database/metal_history.db'
    if not Path(db_path).exists():
        print(f"Database not found at {db_path}")
        return
    
    db = kuzu.Database(db_path)
    conn = kuzu.Connection(db)
    
    # Show available queries
    queries = {
        '1': ("List all bands", "MATCH (b:Band) RETURN b.name ORDER BY b.name"),
        '2': ("List all albums", "MATCH (a:Album) RETURN a.title, a.release_year ORDER BY a.release_year"),
        '3': ("List all subgenres", "MATCH (s:Subgenre) RETURN s.name, s.description ORDER BY s.name"),
        '4': ("Find bands by country", "MATCH (b:Band) WHERE b.origin_country <> '' RETURN b.name, b.origin_country ORDER BY b.origin_country"),
        '5': ("Albums by year", "MATCH (a:Album) WHERE a.release_year IS NOT NULL RETURN a.title, a.release_year ORDER BY a.release_year"),
        '6': ("All relationships for a band", None),  # Custom query
        '7': ("Search entities by name", None),  # Custom query
        '8': ("Custom Cypher query", None),  # User input
        '9': ("Export data to JSON", None),  # Export function
    }
    
    while True:
        print("\nAvailable queries:")
        for key, (desc, _) in queries.items():
            print(f"  {key}. {desc}")
        print("  0. Exit")
        
        choice = input("\nSelect option: ").strip()
        
        if choice == '0':
            break
        elif choice == '6':
            # All relationships for a band
            band_name = input("Enter band name: ").strip()
            query = f"""
            MATCH (b:Band {{name: '{band_name}'}})
            OPTIONAL MATCH (b)-[r]-(n)
            RETURN type(r) as relationship, labels(n)[0] as node_type, 
                   CASE 
                     WHEN labels(n)[0] = 'Album' THEN n.title
                     WHEN labels(n)[0] = 'Person' THEN n.name
                     WHEN labels(n)[0] = 'Band' THEN n.name
                     WHEN labels(n)[0] = 'Subgenre' THEN n.name
                     ELSE 'Unknown'
                   END as name
            """
            try:
                result = conn.execute(query)
                print(f"\nRelationships for {band_name}:")
                while result.has_next():
                    row = result.get_next()
                    if row[0]:  # If relationship exists
                        print(f"  {row[0]} -> {row[1]}: {row[2]}")
            except Exception as e:
                print(f"Error: {e}")
        
        elif choice == '7':
            # Search entities by name
            search_term = input("Enter search term: ").strip()
            queries_to_run = [
                ("Bands", f"MATCH (b:Band) WHERE b.name =~ '.*{search_term}.*' RETURN b.name, b.description"),
                ("Albums", f"MATCH (a:Album) WHERE a.title =~ '.*{search_term}.*' RETURN a.title, a.release_year"),
                ("People", f"MATCH (p:Person) WHERE p.name =~ '.*{search_term}.*' RETURN p.name, p.nationality"),
                ("Subgenres", f"MATCH (s:Subgenre) WHERE s.name =~ '.*{search_term}.*' RETURN s.name, s.description"),
            ]
            
            for entity_type, query in queries_to_run:
                try:
                    result = conn.execute(query)
                    matches = []
                    while result.has_next():
                        matches.append(result.get_next())
                    
                    if matches:
                        print(f"\n{entity_type}:")
                        for match in matches:
                            print(f"  - {match[0]}: {match[1] if len(match) > 1 else ''}")
                except Exception as e:
                    pass
        
        elif choice == '8':
            # Custom query
            print("\nEnter Cypher query (or 'help' for examples):")
            query = input().strip()
            
            if query.lower() == 'help':
                print("\nExample queries:")
                print("  MATCH (b:Band) RETURN b.name LIMIT 10")
                print("  MATCH (b:Band)-[:PLAYS_GENRE]->(g:Subgenre) RETURN b.name, g.name")
                print("  MATCH (a:Album) WHERE a.release_year > 1980 RETURN a.title, a.release_year")
                continue
            
            try:
                result = conn.execute(query)
                rows = []
                while result.has_next():
                    rows.append(result.get_next())
                
                if rows:
                    print(f"\nResults ({len(rows)} rows):")
                    for row in rows[:20]:  # Limit to 20 rows
                        print(f"  {row}")
                    if len(rows) > 20:
                        print(f"  ... and {len(rows) - 20} more rows")
                else:
                    print("No results found.")
            except Exception as e:
                print(f"Error: {e}")
        
        elif choice == '9':
            # Export data
            import json
            
            export_data = {
                'bands': [],
                'albums': [],
                'people': [],
                'subgenres': []
            }
            
            # Export bands
            result = conn.execute("MATCH (b:Band) RETURN b")
            while result.has_next():
                band = result.get_next()[0]
                export_data['bands'].append({
                    'name': band.get('name'),
                    'origin_city': band.get('origin_city'),
                    'origin_country': band.get('origin_country'),
                    'status': band.get('status'),
                    'description': band.get('description')
                })
            
            # Export albums
            result = conn.execute("MATCH (a:Album) RETURN a")
            while result.has_next():
                album = result.get_next()[0]
                export_data['albums'].append({
                    'title': album.get('title'),
                    'release_year': album.get('release_year'),
                    'label': album.get('label'),
                    'description': album.get('description')
                })
            
            filename = 'data/processed/database_export.json'
            with open(filename, 'w') as f:
                json.dump(export_data, f, indent=2)
            print(f"\nData exported to {filename}")
            print(f"  Bands: {len(export_data['bands'])}")
            print(f"  Albums: {len(export_data['albums'])}")
        
        elif choice in queries:
            desc, query = queries[choice]
            if query:
                try:
                    result = conn.execute(query)
                    print(f"\n{desc}:")
                    count = 0
                    while result.has_next():
                        row = result.get_next()
                        print(f"  {' | '.join(str(r) for r in row)}")
                        count += 1
                    print(f"\nTotal: {count} results")
                except Exception as e:
                    print(f"Error: {e}")

if __name__ == "__main__":
    main()