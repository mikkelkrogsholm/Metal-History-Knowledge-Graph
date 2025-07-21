#!/usr/bin/env python3
"""
Graph Explorer - Analyze Metal History Knowledge Graph
Provides comprehensive statistics and analysis of the graph database.
"""

import kuzu
import json
import os
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Any, Tuple
import argparse
from datetime import datetime


class GraphExplorer:
    """Analyze and explore the Metal History Knowledge Graph"""
    
    def __init__(self, db_path: str):
        """Initialize with database path"""
        self.db_path = Path(db_path)
        if not self.db_path.exists():
            raise FileNotFoundError(f"Database not found: {db_path}")
        
        self.db = kuzu.Database(str(self.db_path))
        self.conn = kuzu.Connection(self.db)
        
    def get_node_statistics(self) -> Dict[str, int]:
        """Count all nodes by type"""
        stats = {}
        
        # Define all possible node types from both schemas
        node_types = [
            'Band', 'Person', 'Album', 'Song', 'Subgenre', 
            'GeographicLocation', 'Event', 'Movement',
            'Label', 'Tour', 'Venue', 'Collaboration',
            'Influence', 'Era', 'Instrument', 'Award'
        ]
        
        for node_type in node_types:
            try:
                result = self.conn.execute(f'MATCH (n:{node_type}) RETURN COUNT(n) as count')
                if result.has_next():
                    count = result.get_next()[0]
                    if count > 0:
                        stats[node_type] = count
            except Exception as e:
                # Node type might not exist in current schema
                continue
                
        return stats
    
    def get_relationship_statistics(self) -> Dict[str, int]:
        """Count all relationships by type"""
        stats = {}
        
        # Get all relationship types
        try:
            # First, get a sample of relationships to identify types
            result = self.conn.execute("""
                MATCH ()-[r]->()
                RETURN DISTINCT label(r) as rel_type, COUNT(*) as count
                ORDER BY count DESC
            """)
            
            while result.has_next():
                row = result.get_next()
                if len(row) >= 2:
                    stats[row[0]] = row[1]
        except Exception as e:
            print(f"Error getting relationship stats: {e}")
            
        return stats
    
    def get_graph_properties(self) -> Dict[str, Any]:
        """Calculate graph-level properties"""
        properties = {}
        
        try:
            # Total nodes
            result = self.conn.execute("MATCH (n) RETURN COUNT(n) as count")
            properties['total_nodes'] = result.get_next()[0] if result.has_next() else 0
            
            # Total relationships
            result = self.conn.execute("MATCH ()-[r]->() RETURN COUNT(r) as count")
            properties['total_relationships'] = result.get_next()[0] if result.has_next() else 0
            
            # Average degree (relationships per node)
            if properties['total_nodes'] > 0:
                properties['avg_degree'] = properties['total_relationships'] / properties['total_nodes']
            else:
                properties['avg_degree'] = 0
                
            # Graph density
            n = properties['total_nodes']
            if n > 1:
                max_possible_edges = n * (n - 1)  # For directed graph
                properties['density'] = properties['total_relationships'] / max_possible_edges
            else:
                properties['density'] = 0
                
        except Exception as e:
            print(f"Error calculating graph properties: {e}")
            
        return properties
    
    def find_orphaned_nodes(self) -> Dict[str, List[Dict]]:
        """Find nodes with no relationships"""
        orphans = defaultdict(list)
        
        node_types = ['Band', 'Person', 'Album', 'Song', 'Subgenre', 
                      'GeographicLocation', 'Event', 'Movement']
        
        for node_type in node_types:
            try:
                # Find nodes with no incoming or outgoing relationships
                query = f"""
                MATCH (n:{node_type})
                WHERE NOT EXISTS {{ MATCH (n)-[]-() }}
                RETURN n.name as name, n.id as id
                LIMIT 10
                """
                result = self.conn.execute(query)
                
                while result.has_next():
                    row = result.get_next()
                    orphans[node_type].append({
                        'name': row[0] if len(row) > 0 else 'Unknown',
                        'id': row[1] if len(row) > 1 else None
                    })
            except Exception as e:
                continue
                
        return dict(orphans)
    
    def find_disconnected_components(self) -> Dict[str, Any]:
        """Analyze graph connectivity"""
        connectivity = {}
        
        try:
            # Find bands that are not connected to any other bands
            result = self.conn.execute("""
                MATCH (b:Band)
                WHERE NOT EXISTS {
                    MATCH (b)-[:INFLUENCED|:TOURED_WITH|:SHARES_MEMBER]-(other:Band)
                    WHERE b.id <> other.id
                }
                RETURN COUNT(b) as isolated_bands
            """)
            if result.has_next():
                connectivity['isolated_bands'] = result.get_next()[0]
                
            # Find people not connected to any bands
            result = self.conn.execute("""
                MATCH (p:Person)
                WHERE NOT EXISTS {
                    MATCH (p)-[:MEMBER_OF|:FOUNDED]->(b:Band)
                }
                RETURN COUNT(p) as unaffiliated_people
            """)
            if result.has_next():
                connectivity['unaffiliated_people'] = result.get_next()[0]
                
        except Exception as e:
            print(f"Error analyzing connectivity: {e}")
            
        return connectivity
    
    def get_top_entities(self, limit: int = 10) -> Dict[str, List[Dict]]:
        """Get most connected entities"""
        top_entities = {}
        
        try:
            # Most connected bands
            result = self.conn.execute(f"""
                MATCH (b:Band)-[r]-()
                RETURN b.name as name, COUNT(r) as connections
                ORDER BY connections DESC
                LIMIT {limit}
            """)
            
            bands = []
            while result.has_next():
                row = result.get_next()
                bands.append({'name': row[0], 'connections': row[1]})
            top_entities['bands'] = bands
            
            # Most prolific people
            result = self.conn.execute(f"""
                MATCH (p:Person)-[r]-()
                RETURN p.name as name, COUNT(r) as connections
                ORDER BY connections DESC
                LIMIT {limit}
            """)
            
            people = []
            while result.has_next():
                row = result.get_next()
                people.append({'name': row[0], 'connections': row[1]})
            top_entities['people'] = people
            
        except Exception as e:
            print(f"Error getting top entities: {e}")
            
        return top_entities
    
    def analyze_schema_coverage(self) -> Dict[str, Any]:
        """Analyze which parts of the schema are being used"""
        coverage = {
            'used_node_types': [],
            'unused_node_types': [],
            'used_relationship_types': [],
            'potential_missing_relationships': []
        }
        
        # All possible node types from enhanced schema
        all_node_types = [
            'Band', 'Person', 'Album', 'Song', 'Subgenre', 
            'GeographicLocation', 'Event', 'Movement',
            'Label', 'Tour', 'Venue', 'Collaboration',
            'Influence', 'Era', 'Instrument', 'Award'
        ]
        
        # Check which exist
        node_stats = self.get_node_statistics()
        coverage['used_node_types'] = list(node_stats.keys())
        coverage['unused_node_types'] = [nt for nt in all_node_types if nt not in node_stats]
        
        # Check relationships
        rel_stats = self.get_relationship_statistics()
        coverage['used_relationship_types'] = list(rel_stats.keys())
        
        # Suggest missing relationships based on existing nodes
        if 'Band' in coverage['used_node_types'] and 'Album' in coverage['used_node_types']:
            if 'RELEASED' not in coverage['used_relationship_types']:
                coverage['potential_missing_relationships'].append('Band -[RELEASED]-> Album')
                
        if 'Person' in coverage['used_node_types'] and 'Band' in coverage['used_node_types']:
            if 'MEMBER_OF' not in coverage['used_relationship_types']:
                coverage['potential_missing_relationships'].append('Person -[MEMBER_OF]-> Band')
                
        return coverage
    
    def generate_report(self) -> str:
        """Generate comprehensive analysis report"""
        report = []
        report.append("# Metal History Knowledge Graph Analysis Report")
        report.append(f"\nGenerated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"Database: {self.db_path}")
        
        # Node Statistics
        report.append("\n## Node Statistics")
        node_stats = self.get_node_statistics()
        if node_stats:
            for node_type, count in sorted(node_stats.items(), key=lambda x: x[1], reverse=True):
                report.append(f"- {node_type}: {count:,}")
        else:
            report.append("- No nodes found in database")
            
        # Relationship Statistics
        report.append("\n## Relationship Statistics")
        rel_stats = self.get_relationship_statistics()
        if rel_stats:
            for rel_type, count in sorted(rel_stats.items(), key=lambda x: x[1], reverse=True):
                report.append(f"- {rel_type}: {count:,}")
        else:
            report.append("- No relationships found in database")
            
        # Graph Properties
        report.append("\n## Graph Properties")
        properties = self.get_graph_properties()
        report.append(f"- Total Nodes: {properties.get('total_nodes', 0):,}")
        report.append(f"- Total Relationships: {properties.get('total_relationships', 0):,}")
        report.append(f"- Average Degree: {properties.get('avg_degree', 0):.2f}")
        report.append(f"- Graph Density: {properties.get('density', 0):.6f}")
        
        # Connectivity Analysis
        report.append("\n## Connectivity Analysis")
        connectivity = self.find_disconnected_components()
        if connectivity:
            for key, value in connectivity.items():
                report.append(f"- {key.replace('_', ' ').title()}: {value}")
                
        # Orphaned Nodes
        report.append("\n## Orphaned Nodes (No Relationships)")
        orphans = self.find_orphaned_nodes()
        if orphans:
            for node_type, nodes in orphans.items():
                if nodes:
                    report.append(f"\n### {node_type} ({len(nodes)} found)")
                    for node in nodes[:5]:  # Show first 5
                        report.append(f"- {node['name']}")
                    if len(nodes) > 5:
                        report.append(f"- ... and {len(nodes) - 5} more")
                        
        # Top Entities
        report.append("\n## Most Connected Entities")
        top_entities = self.get_top_entities()
        
        if 'bands' in top_entities and top_entities['bands']:
            report.append("\n### Top Bands by Connections")
            for band in top_entities['bands']:
                report.append(f"- {band['name']}: {band['connections']} connections")
                
        if 'people' in top_entities and top_entities['people']:
            report.append("\n### Top People by Connections")
            for person in top_entities['people']:
                report.append(f"- {person['name']}: {person['connections']} connections")
                
        # Schema Coverage
        report.append("\n## Schema Coverage Analysis")
        coverage = self.analyze_schema_coverage()
        
        report.append(f"\n### Used Node Types ({len(coverage['used_node_types'])})")
        for nt in coverage['used_node_types']:
            report.append(f"- {nt}")
            
        report.append(f"\n### Unused Node Types ({len(coverage['unused_node_types'])})")
        for nt in coverage['unused_node_types']:
            report.append(f"- {nt}")
            
        if coverage['potential_missing_relationships']:
            report.append("\n### Potential Missing Relationships")
            for rel in coverage['potential_missing_relationships']:
                report.append(f"- {rel}")
                
        return '\n'.join(report)


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Analyze Metal History Knowledge Graph')
    parser.add_argument('--db-path', default='schema/metal_history.db',
                        help='Path to Kuzu database')
    parser.add_argument('--output', help='Output file for report (default: print to console)')
    parser.add_argument('--json', action='store_true',
                        help='Output raw statistics as JSON')
    
    args = parser.parse_args()
    
    try:
        explorer = GraphExplorer(args.db_path)
        
        if args.json:
            # Output raw statistics as JSON
            stats = {
                'nodes': explorer.get_node_statistics(),
                'relationships': explorer.get_relationship_statistics(),
                'properties': explorer.get_graph_properties(),
                'orphans': explorer.find_orphaned_nodes(),
                'connectivity': explorer.find_disconnected_components(),
                'top_entities': explorer.get_top_entities(),
                'schema_coverage': explorer.analyze_schema_coverage()
            }
            
            output = json.dumps(stats, indent=2)
        else:
            # Generate human-readable report
            output = explorer.generate_report()
            
        if args.output:
            with open(args.output, 'w') as f:
                f.write(output)
            print(f"Report saved to: {args.output}")
        else:
            print(output)
            
    except FileNotFoundError as e:
        print(f"Error: {e}")
        print("Please ensure the database exists. Run: cd schema && python initialize_kuzu.py")
        return 1
    except Exception as e:
        print(f"Error analyzing graph: {e}")
        return 1
    
    return 0


if __name__ == '__main__':
    exit(main())