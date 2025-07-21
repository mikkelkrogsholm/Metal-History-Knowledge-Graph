#!/usr/bin/env python3
"""
Graph Metrics Calculator for Metal History Knowledge Graph

This module provides comprehensive graph analytics including:
- Degree distribution analysis
- Clustering coefficient calculation
- Connected components detection
- Centrality measures
- Path analysis algorithms
"""

import kuzu
import numpy as np
from collections import defaultdict, Counter
from typing import Dict, List, Tuple, Any, Set
import json
from datetime import datetime
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path


class GraphAnalyzer:
    """Comprehensive graph analysis for the Metal History Knowledge Graph"""
    
    def __init__(self, db_path: str):
        """Initialize connection to Kuzu database"""
        self.db_path = db_path
        self.db = kuzu.Database(db_path)
        self.conn = kuzu.Connection(self.db)
        self.metrics = {}
        
    def calculate_degree_distribution(self) -> Dict[str, Any]:
        """Calculate in/out degree distribution for all node types"""
        print("Calculating degree distribution...")
        
        # Get degree for all nodes
        query = """
        MATCH (n)
        OPTIONAL MATCH (n)-[out_rel]->()
        WITH n, COUNT(out_rel) as out_degree
        OPTIONAL MATCH ()-[in_rel]->(n)
        RETURN labels(n)[0] as node_type, 
               n.name as name,
               n.id as node_id,
               out_degree, 
               COUNT(in_rel) as in_degree
        ORDER BY (out_degree + COUNT(in_rel)) DESC
        """
        
        result = self.conn.execute(query)
        degree_data = defaultdict(list)
        all_degrees = []
        
        while result.has_next():
            row = result.get_next()
            node_type = row[0]
            name = row[1]
            node_id = row[2]
            out_deg = row[3]
            in_deg = row[4]
            total_deg = out_deg + in_deg
            
            degree_data[node_type].append({
                'name': name,
                'id': node_id,
                'out_degree': out_deg,
                'in_degree': in_deg,
                'total_degree': total_deg
            })
            all_degrees.append(total_deg)
        
        # Calculate statistics
        stats = {
            'total_nodes': len(all_degrees),
            'avg_degree': np.mean(all_degrees) if all_degrees else 0,
            'median_degree': np.median(all_degrees) if all_degrees else 0,
            'max_degree': max(all_degrees) if all_degrees else 0,
            'degree_distribution': Counter(all_degrees),
            'by_node_type': {}
        }
        
        # Stats by node type
        for node_type, nodes in degree_data.items():
            degrees = [n['total_degree'] for n in nodes]
            stats['by_node_type'][node_type] = {
                'count': len(nodes),
                'avg_degree': np.mean(degrees) if degrees else 0,
                'max_degree': max(degrees) if degrees else 0,
                'top_nodes': sorted(nodes, key=lambda x: x['total_degree'], reverse=True)[:5]
            }
        
        self.metrics['degree_distribution'] = stats
        return stats
    
    def find_connected_components(self) -> Dict[str, Any]:
        """Find disconnected subgraphs using BFS"""
        print("Finding connected components...")
        
        # Get all nodes
        all_nodes_query = "MATCH (n) RETURN n.id as id, labels(n)[0] as type, n.name as name"
        result = self.conn.execute(all_nodes_query)
        
        all_nodes = {}
        while result.has_next():
            row = result.get_next()
            all_nodes[row[0]] = {'type': row[1], 'name': row[2]}
        
        visited = set()
        components = []
        
        def bfs_component(start_id: int) -> Set[int]:
            """BFS to find all nodes in component"""
            component = set()
            queue = [start_id]
            
            while queue:
                current = queue.pop(0)
                if current in visited:
                    continue
                    
                visited.add(current)
                component.add(current)
                
                # Get neighbors
                neighbors_query = """
                MATCH (n {id: $node_id})-[r]-(neighbor)
                RETURN DISTINCT neighbor.id as id
                """
                neighbors_result = self.conn.execute(neighbors_query, {"node_id": current})
                
                while neighbors_result.has_next():
                    neighbor_id = neighbors_result.get_next()[0]
                    if neighbor_id not in visited:
                        queue.append(neighbor_id)
            
            return component
        
        # Find all components
        for node_id in all_nodes:
            if node_id not in visited:
                component = bfs_component(node_id)
                if component:
                    components.append(component)
        
        # Analyze components
        component_stats = []
        for i, component in enumerate(sorted(components, key=len, reverse=True)):
            # Get node types in component
            node_types = defaultdict(int)
            sample_nodes = []
            
            for node_id in list(component)[:10]:  # Sample first 10
                node_info = all_nodes.get(node_id)
                if node_info:
                    node_types[node_info['type']] += 1
                    sample_nodes.append(node_info['name'])
            
            component_stats.append({
                'component_id': i,
                'size': len(component),
                'node_types': dict(node_types),
                'sample_nodes': sample_nodes
            })
        
        stats = {
            'num_components': len(components),
            'largest_component_size': len(components[0]) if components else 0,
            'component_sizes': [len(c) for c in components],
            'components': component_stats[:10]  # Top 10
        }
        
        self.metrics['connected_components'] = stats
        return stats
    
    def calculate_clustering_coefficient(self) -> Dict[str, Any]:
        """Calculate local and global clustering coefficients"""
        print("Calculating clustering coefficients...")
        
        # For each node, find triangles
        query = """
        MATCH (n)
        OPTIONAL MATCH (n)-[r1]-(neighbor1)
        OPTIONAL MATCH (n)-[r2]-(neighbor2)
        WHERE neighbor1.id < neighbor2.id
        OPTIONAL MATCH (neighbor1)-[r3]-(neighbor2)
        WITH n, 
             COUNT(DISTINCT [neighbor1.id, neighbor2.id]) as possible_edges,
             COUNT(DISTINCT CASE WHEN r3 IS NOT NULL THEN [neighbor1.id, neighbor2.id] END) as actual_edges
        WHERE possible_edges > 0
        RETURN labels(n)[0] as node_type,
               n.name as name,
               actual_edges,
               possible_edges,
               CASE WHEN possible_edges > 0 THEN actual_edges * 1.0 / possible_edges ELSE 0 END as local_cc
        """
        
        result = self.conn.execute(query)
        cc_by_type = defaultdict(list)
        all_cc = []
        
        while result.has_next():
            row = result.get_next()
            node_type = row[0]
            local_cc = row[4]
            
            cc_by_type[node_type].append(local_cc)
            all_cc.append(local_cc)
        
        # Calculate statistics
        stats = {
            'global_clustering_coefficient': np.mean(all_cc) if all_cc else 0,
            'avg_local_cc': np.mean(all_cc) if all_cc else 0,
            'by_node_type': {}
        }
        
        for node_type, cc_values in cc_by_type.items():
            if cc_values:
                stats['by_node_type'][node_type] = {
                    'avg_clustering': np.mean(cc_values),
                    'max_clustering': max(cc_values),
                    'num_nodes': len(cc_values)
                }
        
        self.metrics['clustering_coefficient'] = stats
        return stats
    
    def calculate_centrality_measures(self) -> Dict[str, Any]:
        """Calculate various centrality measures"""
        print("Calculating centrality measures...")
        
        centrality_stats = {}
        
        # 1. Degree Centrality (already calculated, just reorganize)
        if 'degree_distribution' in self.metrics:
            degree_data = self.metrics['degree_distribution']
            centrality_stats['degree_centrality'] = {
                'top_nodes': []
            }
            
            # Combine top nodes from all types
            all_top_nodes = []
            for node_type, type_data in degree_data['by_node_type'].items():
                for node in type_data['top_nodes']:
                    all_top_nodes.append({
                        'type': node_type,
                        'name': node['name'],
                        'degree': node['total_degree']
                    })
            
            centrality_stats['degree_centrality']['top_nodes'] = sorted(
                all_top_nodes, key=lambda x: x['degree'], reverse=True
            )[:20]
        
        # 2. Betweenness Centrality approximation (sampling shortest paths)
        print("  - Calculating betweenness centrality (sampling)...")
        betweenness_query = """
        MATCH (n:Band)
        WITH n, n.id as node_id
        LIMIT 20
        MATCH p = shortestPath((n)-[*..5]-(m:Band))
        WHERE n.id < m.id
        WITH nodes(p) as path_nodes
        UNWIND path_nodes as pn
        WITH pn, COUNT(*) as path_count
        RETURN labels(pn)[0] as node_type, pn.name as name, path_count
        ORDER BY path_count DESC
        LIMIT 20
        """
        
        betweenness_result = self.conn.execute(betweenness_query)
        betweenness_nodes = []
        
        while betweenness_result.has_next():
            row = betweenness_result.get_next()
            betweenness_nodes.append({
                'type': row[0],
                'name': row[1],
                'betweenness_score': row[2]
            })
        
        centrality_stats['betweenness_centrality'] = {
            'top_nodes': betweenness_nodes,
            'note': 'Approximated using sample of shortest paths'
        }
        
        # 3. Eigenvector Centrality approximation (influence-based)
        print("  - Calculating eigenvector centrality (influence-based)...")
        eigenvector_query = """
        MATCH (b:Band)
        OPTIONAL MATCH (b)<-[:INFLUENCED_BY]-(influenced:Band)
        OPTIONAL MATCH (b)-[:INFLUENCED_BY]->(influences:Band)
        WITH b, 
             COUNT(DISTINCT influenced) as num_influenced,
             COUNT(DISTINCT influences) as num_influences
        RETURN b.name as name,
               num_influenced,
               num_influences,
               num_influenced + num_influences * 0.5 as influence_score
        ORDER BY influence_score DESC
        LIMIT 20
        """
        
        eigenvector_result = self.conn.execute(eigenvector_query)
        eigenvector_nodes = []
        
        while eigenvector_result.has_next():
            row = eigenvector_result.get_next()
            eigenvector_nodes.append({
                'name': row[0],
                'bands_influenced': row[1],
                'influences': row[2],
                'influence_score': row[3]
            })
        
        centrality_stats['eigenvector_centrality'] = {
            'top_influential_bands': eigenvector_nodes
        }
        
        self.metrics['centrality_measures'] = centrality_stats
        return centrality_stats
    
    def analyze_paths(self) -> Dict[str, Any]:
        """Analyze path characteristics in the graph"""
        print("Analyzing paths...")
        
        path_stats = {}
        
        # 1. Average shortest path length (sample)
        print("  - Calculating average shortest path length...")
        path_length_query = """
        MATCH (n:Band), (m:Band)
        WHERE n.id < m.id
        WITH n, m LIMIT 100
        MATCH p = shortestPath((n)-[*..10]-(m))
        RETURN length(p) as path_length, COUNT(*) as count
        ORDER BY path_length
        """
        
        path_result = self.conn.execute(path_length_query)
        path_lengths = []
        
        while path_result.has_next():
            row = path_result.get_next()
            length = row[0]
            count = row[1]
            path_lengths.extend([length] * count)
        
        if path_lengths:
            path_stats['shortest_paths'] = {
                'avg_length': np.mean(path_lengths),
                'median_length': np.median(path_lengths),
                'max_length': max(path_lengths),
                'distribution': Counter(path_lengths)
            }
        
        # 2. Longest influence chains
        print("  - Finding longest influence chains...")
        influence_chain_query = """
        MATCH p = (b1:Band)-[:INFLUENCED_BY*..10]->(b2:Band)
        WITH p, length(p) as chain_length
        ORDER BY chain_length DESC
        LIMIT 5
        RETURN [n in nodes(p) | n.name] as chain, chain_length
        """
        
        chain_result = self.conn.execute(influence_chain_query)
        influence_chains = []
        
        while chain_result.has_next():
            row = chain_result.get_next()
            influence_chains.append({
                'chain': row[0],
                'length': row[1]
            })
        
        path_stats['influence_chains'] = influence_chains
        
        # 3. Genre evolution paths
        print("  - Analyzing genre evolution paths...")
        genre_path_query = """
        MATCH p = (g1:Genre)-[:EVOLVED_INTO*..5]->(g2:Genre)
        WITH p, length(p) as evolution_length
        ORDER BY evolution_length DESC
        LIMIT 5
        RETURN [n in nodes(p) | n.name] as evolution, evolution_length
        """
        
        genre_result = self.conn.execute(genre_path_query)
        genre_paths = []
        
        while genre_result.has_next():
            row = genre_result.get_next()
            genre_paths.append({
                'evolution': row[0],
                'length': row[1]
            })
        
        path_stats['genre_evolution'] = genre_paths
        
        self.metrics['path_analysis'] = path_stats
        return path_stats
    
    def visualize_degree_distribution(self, output_dir: str = "exploration/reports/"):
        """Create visualization of degree distribution"""
        if 'degree_distribution' not in self.metrics:
            self.calculate_degree_distribution()
        
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        # Plot degree distribution
        degree_dist = self.metrics['degree_distribution']['degree_distribution']
        degrees = list(degree_dist.keys())
        counts = list(degree_dist.values())
        
        plt.figure(figsize=(12, 6))
        
        # Linear plot
        plt.subplot(1, 2, 1)
        plt.bar(degrees[:50], counts[:50])  # First 50 degrees
        plt.xlabel('Degree')
        plt.ylabel('Count')
        plt.title('Degree Distribution (Linear Scale)')
        
        # Log-log plot
        plt.subplot(1, 2, 2)
        if degrees and counts:
            plt.loglog(degrees, counts, 'bo-', markersize=8)
            plt.xlabel('Degree (log)')
            plt.ylabel('Count (log)')
            plt.title('Degree Distribution (Log-Log Scale)')
        
        plt.tight_layout()
        plt.savefig(f"{output_dir}/degree_distribution.png", dpi=300, bbox_inches='tight')
        plt.close()
        
        # Plot by node type
        plt.figure(figsize=(10, 6))
        node_types = []
        avg_degrees = []
        
        for node_type, stats in self.metrics['degree_distribution']['by_node_type'].items():
            node_types.append(node_type)
            avg_degrees.append(stats['avg_degree'])
        
        plt.bar(node_types, avg_degrees)
        plt.xlabel('Node Type')
        plt.ylabel('Average Degree')
        plt.title('Average Degree by Node Type')
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.savefig(f"{output_dir}/degree_by_type.png", dpi=300, bbox_inches='tight')
        plt.close()
    
    def generate_report(self) -> str:
        """Generate comprehensive report of all metrics"""
        report = []
        report.append("# Metal History Knowledge Graph - Graph Metrics Report")
        report.append(f"\nGenerated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"Database: {self.db_path}")
        
        # Degree Distribution
        if 'degree_distribution' in self.metrics:
            dd = self.metrics['degree_distribution']
            report.append("\n## Degree Distribution")
            report.append(f"- Total nodes: {dd['total_nodes']:,}")
            report.append(f"- Average degree: {dd['avg_degree']:.2f}")
            report.append(f"- Median degree: {dd['median_degree']:.2f}")
            report.append(f"- Maximum degree: {dd['max_degree']}")
            
            report.append("\n### By Node Type:")
            for node_type, stats in dd['by_node_type'].items():
                report.append(f"\n**{node_type}**")
                report.append(f"- Count: {stats['count']:,}")
                report.append(f"- Average degree: {stats['avg_degree']:.2f}")
                report.append(f"- Top nodes:")
                for node in stats['top_nodes'][:3]:
                    report.append(f"  - {node['name']}: {node['total_degree']} connections")
        
        # Connected Components
        if 'connected_components' in self.metrics:
            cc = self.metrics['connected_components']
            report.append("\n## Connected Components")
            report.append(f"- Number of components: {cc['num_components']}")
            report.append(f"- Largest component size: {cc['largest_component_size']:,} nodes")
            report.append(f"- Component sizes: {cc['component_sizes'][:10]}")
        
        # Clustering Coefficient
        if 'clustering_coefficient' in self.metrics:
            clustering = self.metrics['clustering_coefficient']
            report.append("\n## Clustering Coefficient")
            report.append(f"- Global clustering coefficient: {clustering['global_clustering_coefficient']:.4f}")
            report.append("\n### By Node Type:")
            for node_type, stats in clustering['by_node_type'].items():
                report.append(f"- {node_type}: {stats['avg_clustering']:.4f}")
        
        # Centrality Measures
        if 'centrality_measures' in self.metrics:
            centrality = self.metrics['centrality_measures']
            report.append("\n## Centrality Measures")
            
            if 'degree_centrality' in centrality:
                report.append("\n### Top Nodes by Degree Centrality:")
                for node in centrality['degree_centrality']['top_nodes'][:10]:
                    report.append(f"- {node['name']} ({node['type']}): {node['degree']} connections")
            
            if 'betweenness_centrality' in centrality:
                report.append("\n### Top Nodes by Betweenness Centrality:")
                for node in centrality['betweenness_centrality']['top_nodes'][:10]:
                    report.append(f"- {node['name']} ({node['type']}): score {node['betweenness_score']}")
            
            if 'eigenvector_centrality' in centrality:
                report.append("\n### Most Influential Bands:")
                for band in centrality['eigenvector_centrality']['top_influential_bands'][:10]:
                    report.append(f"- {band['name']}: influenced {band['bands_influenced']} bands")
        
        # Path Analysis
        if 'path_analysis' in self.metrics:
            paths = self.metrics['path_analysis']
            report.append("\n## Path Analysis")
            
            if 'shortest_paths' in paths:
                sp = paths['shortest_paths']
                report.append(f"\n### Shortest Paths (sample):")
                report.append(f"- Average length: {sp['avg_length']:.2f}")
                report.append(f"- Median length: {sp['median_length']:.1f}")
                report.append(f"- Maximum length: {sp['max_length']}")
            
            if 'influence_chains' in paths:
                report.append("\n### Longest Influence Chains:")
                for chain in paths['influence_chains']:
                    report.append(f"- {' → '.join(chain['chain'])} (length: {chain['length']})")
            
            if 'genre_evolution' in paths:
                report.append("\n### Genre Evolution Paths:")
                for evolution in paths['genre_evolution']:
                    report.append(f"- {' → '.join(evolution['evolution'])} (length: {evolution['length']})")
        
        return "\n".join(report)
    
    def run_full_analysis(self):
        """Run all analysis methods"""
        print("Starting full graph analysis...")
        
        # Run all analyses
        self.calculate_degree_distribution()
        self.find_connected_components()
        self.calculate_clustering_coefficient()
        self.calculate_centrality_measures()
        self.analyze_paths()
        
        # Generate visualizations
        self.visualize_degree_distribution()
        
        # Generate report
        report = self.generate_report()
        
        # Save report
        report_path = "exploration/reports/phase3_graph_metrics_report.md"
        Path(report_path).parent.mkdir(parents=True, exist_ok=True)
        with open(report_path, 'w') as f:
            f.write(report)
        
        # Save raw metrics
        metrics_path = "exploration/reports/graph_metrics_raw.json"
        with open(metrics_path, 'w') as f:
            json.dump(self.metrics, f, indent=2, default=str)
        
        print(f"\nAnalysis complete!")
        print(f"Report saved to: {report_path}")
        print(f"Raw metrics saved to: {metrics_path}")
        print(f"Visualizations saved to: exploration/reports/")


def main():
    """Main execution function"""
    db_path = "schema/metal_history.db"
    
    analyzer = GraphAnalyzer(db_path)
    analyzer.run_full_analysis()


if __name__ == "__main__":
    main()