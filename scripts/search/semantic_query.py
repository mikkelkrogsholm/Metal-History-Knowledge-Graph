#!/usr/bin/env python3
"""
Semantic Query Interface for Metal History Knowledge Graph

This module provides natural language query processing and hybrid search
combining vector similarity with graph properties.
"""

import json
import re
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import kuzu
from pathlib import Path

from vector_search import VectorSearchEngine, SearchResult


class QueryIntent(Enum):
    """Types of query intents"""
    FIND_SIMILAR = "find_similar"  # "bands similar to X"
    FIND_BY_ATTRIBUTE = "find_by_attribute"  # "bands from the 80s"
    FIND_BY_LOCATION = "find_by_location"  # "British metal bands"
    FIND_BY_GENRE = "find_by_genre"  # "thrash metal bands"
    FIND_INFLUENCE = "find_influence"  # "bands influenced by X"
    FIND_MEMBERS = "find_members"  # "guitarists in X"
    GENERAL_SEARCH = "general_search"  # Default


@dataclass
class EnhancedSearchResult:
    """Search result enhanced with graph context"""
    base_result: SearchResult
    graph_context: Dict[str, Any]
    explanation: str
    combined_score: float


class SemanticQueryEngine:
    """
    Natural language query interface combining vector search with graph queries.
    
    Features:
    - Intent detection from natural language
    - Hybrid search (vector + graph)
    - Result explanation generation
    - Context enrichment from graph
    """
    
    def __init__(self, 
                 vector_engine: VectorSearchEngine,
                 db_path: str = "schema/metal_history.db"):
        """
        Initialize semantic query engine.
        
        Args:
            vector_engine: Vector search engine instance
            db_path: Path to Kuzu database
        """
        self.vector_engine = vector_engine
        self.db_path = Path(db_path)
        
        # Initialize Kuzu connection if database exists
        self.db = None
        self.conn = None
        if self.db_path.exists():
            try:
                self.db = kuzu.Database(str(self.db_path))
                self.conn = kuzu.Connection(self.db)
                print(f"Connected to Kuzu database at {self.db_path}")
            except Exception as e:
                print(f"Warning: Could not connect to database: {e}")
                
        # Patterns for intent detection
        self.intent_patterns = {
            QueryIntent.FIND_SIMILAR: [
                r"similar to (.+)",
                r"like (.+)",
                r"bands like (.+)",
                r"sounds like (.+)"
            ],
            QueryIntent.FIND_BY_LOCATION: [
                r"(british|american|norwegian|swedish|german) .*(bands?|artists?)",
                r"bands? from (.+)",
                r"(.+) metal scene"
            ],
            QueryIntent.FIND_BY_ATTRIBUTE: [
                r"from the (\d{2,4}s?)",
                r"(\d{4}) albums?",
                r"formed in (\d{4})"
            ],
            QueryIntent.FIND_BY_GENRE: [
                r"(thrash|death|black|doom|power|heavy) metal",
                r"(.+) metal bands?"
            ],
            QueryIntent.FIND_INFLUENCE: [
                r"influenced by (.+)",
                r"bands? that influenced (.+)",
                r"pioneers? of (.+)"
            ],
            QueryIntent.FIND_MEMBERS: [
                r"(guitarist|drummer|bassist|vocalist)s? (?:in|of|from) (.+)",
                r"members? of (.+)"
            ]
        }
        
    def parse_intent(self, query: str) -> Tuple[QueryIntent, Optional[str]]:
        """
        Parse query to determine intent and extract key information.
        
        Args:
            query: Natural language query
            
        Returns:
            Tuple of (intent, extracted_info)
        """
        query_lower = query.lower()
        
        for intent, patterns in self.intent_patterns.items():
            for pattern in patterns:
                match = re.search(pattern, query_lower)
                if match:
                    # Extract the relevant part
                    extracted = match.group(1) if match.groups() else None
                    return intent, extracted
                    
        return QueryIntent.GENERAL_SEARCH, None
        
    def get_graph_context(self, entity_id: str, entity_type: str) -> Dict[str, Any]:
        """
        Retrieve additional context from the graph database.
        
        Args:
            entity_id: Entity identifier
            entity_type: Type of entity (bands, albums, etc.)
            
        Returns:
            Dictionary with graph context
        """
        context = {}
        
        if not self.conn:
            return context
            
        try:
            # Extract entity name from ID
            entity_name = entity_id.split(":", 1)[1]
            
            if entity_type == "bands":
                # Get band relationships
                # Members
                members_query = """
                MATCH (b:Band {name: $name})-[:HAS_MEMBER]->(p:Person)
                RETURN p.name as member, p.instruments as instruments
                """
                members_result = self.conn.execute(members_query, {"name": entity_name})
                context['members'] = [dict(row) for row in members_result]
                
                # Albums
                albums_query = """
                MATCH (b:Band {name: $name})-[:RELEASED]->(a:Album)
                RETURN a.title as album, a.release_year as year
                ORDER BY a.release_year
                """
                albums_result = self.conn.execute(albums_query, {"name": entity_name})
                context['albums'] = [dict(row) for row in albums_result]
                
                # Genres
                genres_query = """
                MATCH (b:Band {name: $name})-[:PLAYS_GENRE]->(g:Genre)
                RETURN g.name as genre
                """
                genres_result = self.conn.execute(genres_query, {"name": entity_name})
                context['genres'] = [row['genre'] for row in genres_result]
                
            elif entity_type == "people":
                # Get person's bands
                bands_query = """
                MATCH (p:Person {name: $name})<-[:HAS_MEMBER]-(b:Band)
                RETURN b.name as band
                """
                bands_result = self.conn.execute(bands_query, {"name": entity_name})
                context['bands'] = [row['band'] for row in bands_result]
                
            elif entity_type == "albums":
                # Get album's band
                band_query = """
                MATCH (a:Album {title: $name})<-[:RELEASED]-(b:Band)
                RETURN b.name as band
                """
                band_result = self.conn.execute(band_query, {"name": entity_name})
                for row in band_result:
                    context['band'] = row['band']
                    
        except Exception as e:
            print(f"Error getting graph context: {e}")
            
        return context
        
    def generate_explanation(self, 
                           result: SearchResult, 
                           query: str,
                           intent: QueryIntent,
                           context: Dict[str, Any]) -> str:
        """
        Generate human-readable explanation for why this result matches.
        
        Args:
            result: Search result
            query: Original query
            intent: Detected query intent
            context: Graph context
            
        Returns:
            Explanation string
        """
        explanations = []
        
        # Base similarity explanation
        if result.similarity_score > 0.8:
            explanations.append("Very high semantic similarity")
        elif result.similarity_score > 0.6:
            explanations.append("Strong semantic match")
        elif result.similarity_score > 0.4:
            explanations.append("Moderate semantic match")
        
        # Intent-specific explanations
        if intent == QueryIntent.FIND_SIMILAR:
            explanations.append("Similar musical style and characteristics")
            
        elif intent == QueryIntent.FIND_BY_LOCATION:
            origin = result.entity_data.get('origin_location', '')
            if origin:
                explanations.append(f"Origin: {origin}")
                
        elif intent == QueryIntent.FIND_BY_ATTRIBUTE:
            if result.entity_type == 'bands':
                year = result.entity_data.get('formed_year')
                if year:
                    explanations.append(f"Formed in {year}")
            elif result.entity_type == 'albums':
                year = result.entity_data.get('release_year')
                if year:
                    explanations.append(f"Released in {year}")
                    
        # Add context-based explanations
        if context.get('genres'):
            explanations.append(f"Genres: {', '.join(context['genres'][:3])}")
            
        if context.get('members'):
            member_count = len(context['members'])
            explanations.append(f"{member_count} known members")
            
        return " | ".join(explanations)
        
    def query(self, 
              natural_language_query: str,
              top_k: int = 10,
              min_score: float = 0.3,
              entity_types: Optional[List[str]] = None) -> List[EnhancedSearchResult]:
        """
        Process natural language query and return enhanced results.
        
        Args:
            natural_language_query: User's query in natural language
            top_k: Number of results to return
            min_score: Minimum similarity score
            entity_types: Filter by entity types
            
        Returns:
            List of enhanced search results
        """
        # Parse intent
        intent, extracted_info = self.parse_intent(natural_language_query)
        print(f"Detected intent: {intent.value}, extracted: {extracted_info}")
        
        # Perform vector search
        vector_results = self.vector_engine.search(
            natural_language_query, 
            top_k=top_k * 2,  # Get more for filtering
            threshold=min_score,
            entity_types=entity_types
        )
        
        # Enhance results with graph context
        enhanced_results = []
        
        for result in vector_results:
            # Get graph context
            context = self.get_graph_context(
                result.entity_id, 
                result.entity_type
            )
            
            # Generate explanation
            explanation = self.generate_explanation(
                result, 
                natural_language_query, 
                intent, 
                context
            )
            
            # Calculate combined score (could be weighted differently)
            combined_score = result.similarity_score
            
            # Boost score based on intent matching
            if intent == QueryIntent.FIND_BY_LOCATION and extracted_info:
                origin = result.entity_data.get('origin_location', '').lower()
                if extracted_info in origin:
                    combined_score *= 1.2
                    
            enhanced_results.append(EnhancedSearchResult(
                base_result=result,
                graph_context=context,
                explanation=explanation,
                combined_score=combined_score
            ))
        
        # Sort by combined score
        enhanced_results.sort(key=lambda x: x.combined_score, reverse=True)
        
        return enhanced_results[:top_k]
        
    def format_results(self, results: List[EnhancedSearchResult]) -> str:
        """
        Format search results for display.
        
        Args:
            results: List of enhanced search results
            
        Returns:
            Formatted string representation
        """
        if not results:
            return "No results found."
            
        output = []
        
        for i, result in enumerate(results, 1):
            base = result.base_result
            name = base.entity_data.get('name', 'Unknown')
            
            output.append(f"{i}. [{base.entity_type}] {name}")
            output.append(f"   Score: {result.combined_score:.3f}")
            output.append(f"   {result.explanation}")
            
            # Add key details based on type
            if base.entity_type == 'bands':
                year = base.entity_data.get('formed_year', 'Unknown')
                location = base.entity_data.get('origin_location', 'Unknown')
                output.append(f"   Founded: {year} in {location}")
                
                if result.graph_context.get('genres'):
                    genres = ", ".join(result.graph_context['genres'])
                    output.append(f"   Genres: {genres}")
                    
                if result.graph_context.get('albums'):
                    album_count = len(result.graph_context['albums'])
                    output.append(f"   Albums: {album_count} releases")
                    
            elif base.entity_type == 'albums':
                artist = base.entity_data.get('artist', 'Unknown')
                year = base.entity_data.get('release_year', 'Unknown')
                output.append(f"   By: {artist} ({year})")
                
            elif base.entity_type == 'people':
                instruments = base.entity_data.get('instruments', [])
                if instruments:
                    output.append(f"   Instruments: {', '.join(instruments)}")
                    
                if result.graph_context.get('bands'):
                    bands = ", ".join(result.graph_context['bands'])
                    output.append(f"   Bands: {bands}")
                    
            output.append("")  # Empty line between results
            
        return "\n".join(output)


def main():
    """Example usage and testing."""
    import sys
    
    # Change to project root
    project_root = Path(__file__).parent.parent.parent
    sys.path.insert(0, str(project_root))
    
    # Initialize engines
    print("Initializing semantic query engine...")
    vector_engine = VectorSearchEngine(
        embeddings_path=project_root / "entities_with_embeddings.json"
    )
    query_engine = SemanticQueryEngine(
        vector_engine,
        db_path=project_root / "schema" / "metal_history.db"
    )
    
    # Test queries demonstrating different intents
    test_queries = [
        "Bands similar to Black Sabbath",
        "British heavy metal bands",
        "Bands from the 80s",
        "Heavy metal pioneers",
        "Albums from 1970",
        "Guitarists in metal bands",
        "Doom metal bands",
        "Birmingham metal scene"
    ]
    
    print("\n" + "="*60)
    print("SEMANTIC QUERY TESTING")
    print("="*60)
    
    for query in test_queries:
        print(f"\nQuery: '{query}'")
        print("-" * 60)
        
        results = query_engine.query(query, top_k=5)
        formatted = query_engine.format_results(results)
        print(formatted)
        
        print("\n" + "="*60)
        
    # Interactive mode
    print("\nEntering interactive mode. Type 'quit' to exit.")
    
    while True:
        try:
            query = input("\nEnter query: ").strip()
            if query.lower() in ['quit', 'exit', 'q']:
                break
                
            if not query:
                continue
                
            print("\nSearching...")
            results = query_engine.query(query, top_k=10)
            formatted = query_engine.format_results(results)
            print(formatted)
            
        except KeyboardInterrupt:
            print("\nExiting...")
            break
        except Exception as e:
            print(f"Error: {e}")


if __name__ == "__main__":
    main()