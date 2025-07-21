#!/usr/bin/env python3
"""
Vector Search Engine for Metal History Knowledge Graph

This module implements efficient vector similarity search using cosine similarity
on 1024-dimensional embeddings from snowflake-arctic-embed2 model.
"""

import json
import numpy as np
import time
from typing import List, Tuple, Dict, Any, Optional
from pathlib import Path
import ollama
from dataclasses import dataclass


@dataclass
class SearchResult:
    """Represents a single search result"""
    entity_id: str
    entity_type: str
    entity_data: Dict[str, Any]
    similarity_score: float
    rank: int


class VectorSearchEngine:
    """
    Efficient vector search implementation with cosine similarity.
    
    Features:
    - Fast in-memory search
    - Cosine similarity computation
    - K-nearest neighbors search
    - Similarity threshold filtering
    - Batch processing support
    """
    
    def __init__(self, 
                 embeddings_path: str = "entities_with_embeddings.json",
                 embedding_model: str = "snowflake-arctic-embed2:latest"):
        """
        Initialize the vector search engine.
        
        Args:
            embeddings_path: Path to JSON file containing entity embeddings
            embedding_model: Ollama model to use for query embeddings
        """
        self.embeddings_path = Path(embeddings_path)
        self.embedding_model = embedding_model
        
        # Storage for entities and their embeddings
        self.entities = {}  # entity_id -> (entity_type, entity_data)
        self.embeddings = None  # numpy array of embeddings
        self.entity_ids = []  # list of entity IDs in same order as embeddings
        
        # Load embeddings into memory
        self._load_embeddings()
        
    def _load_embeddings(self):
        """Load entity embeddings from JSON file into memory."""
        print(f"Loading embeddings from {self.embeddings_path}...")
        
        with open(self.embeddings_path, 'r') as f:
            data = json.load(f)
        
        # Collect all entities and embeddings
        embeddings_list = []
        
        for entity_type, entities in data['entities'].items():
            for entity in entities:
                # Create unique entity ID
                entity_id = f"{entity_type}:{entity.get('name', 'unknown')}"
                
                # Store entity data
                self.entities[entity_id] = (entity_type, entity)
                self.entity_ids.append(entity_id)
                
                # Extract embedding
                embedding = np.array(entity['embedding'], dtype=np.float32)
                embeddings_list.append(embedding)
        
        # Convert to numpy array for efficient computation
        self.embeddings = np.vstack(embeddings_list)
        
        # Normalize embeddings for cosine similarity
        self._normalize_embeddings()
        
        print(f"Loaded {len(self.entities)} entities with {self.embeddings.shape[1]}-dimensional embeddings")
        
    def _normalize_embeddings(self):
        """Normalize embeddings to unit length for efficient cosine similarity."""
        norms = np.linalg.norm(self.embeddings, axis=1, keepdims=True)
        # Avoid division by zero
        norms = np.where(norms == 0, 1, norms)
        self.embeddings = self.embeddings / norms
        
    def generate_embedding(self, text: str) -> np.ndarray:
        """
        Generate embedding for a text query using Ollama.
        
        Args:
            text: Query text to embed
            
        Returns:
            Normalized embedding vector
        """
        try:
            response = ollama.embed(
                model=self.embedding_model,
                input=text
            )
            embedding = np.array(response.embeddings[0], dtype=np.float32)
            
            # Normalize for cosine similarity
            norm = np.linalg.norm(embedding)
            if norm > 0:
                embedding = embedding / norm
                
            return embedding
            
        except Exception as e:
            print(f"Error generating embedding: {e}")
            raise
            
    def cosine_similarity(self, query_embedding: np.ndarray, 
                         target_embeddings: Optional[np.ndarray] = None) -> np.ndarray:
        """
        Compute cosine similarity between query and target embeddings.
        
        Since embeddings are normalized, this is just dot product.
        
        Args:
            query_embedding: Normalized query embedding
            target_embeddings: Target embeddings (uses all if None)
            
        Returns:
            Array of similarity scores
        """
        if target_embeddings is None:
            target_embeddings = self.embeddings
            
        # Simple dot product since embeddings are normalized
        similarities = np.dot(target_embeddings, query_embedding)
        
        return similarities
        
    def search(self, 
               query: str, 
               top_k: int = 10,
               threshold: float = 0.0,
               entity_types: Optional[List[str]] = None) -> List[SearchResult]:
        """
        Search for entities similar to the query.
        
        Args:
            query: Natural language search query
            top_k: Number of top results to return
            threshold: Minimum similarity threshold (0-1)
            entity_types: Filter by entity types (e.g., ['bands', 'albums'])
            
        Returns:
            List of SearchResult objects sorted by similarity
        """
        start_time = time.time()
        
        # Generate query embedding
        query_embedding = self.generate_embedding(query)
        
        # Compute similarities
        similarities = self.cosine_similarity(query_embedding)
        
        # Create results
        results = []
        for idx, (entity_id, similarity) in enumerate(zip(self.entity_ids, similarities)):
            if similarity < threshold:
                continue
                
            entity_type, entity_data = self.entities[entity_id]
            
            # Filter by entity type if specified
            if entity_types and entity_type not in entity_types:
                continue
                
            results.append(SearchResult(
                entity_id=entity_id,
                entity_type=entity_type,
                entity_data=entity_data,
                similarity_score=float(similarity),
                rank=0  # Will be set after sorting
            ))
        
        # Sort by similarity score
        results.sort(key=lambda x: x.similarity_score, reverse=True)
        
        # Set ranks and limit to top_k
        for i, result in enumerate(results[:top_k]):
            result.rank = i + 1
            
        search_time = (time.time() - start_time) * 1000  # ms
        print(f"Search completed in {search_time:.1f}ms")
        
        return results[:top_k]
        
    def batch_search(self, 
                     queries: List[str], 
                     top_k: int = 10,
                     threshold: float = 0.0) -> Dict[str, List[SearchResult]]:
        """
        Perform batch search for multiple queries.
        
        Args:
            queries: List of search queries
            top_k: Number of top results per query
            threshold: Minimum similarity threshold
            
        Returns:
            Dictionary mapping queries to their results
        """
        results = {}
        
        for query in queries:
            results[query] = self.search(query, top_k, threshold)
            
        return results
        
    def find_similar_entities(self, 
                            entity_id: str, 
                            top_k: int = 10,
                            exclude_self: bool = True) -> List[SearchResult]:
        """
        Find entities similar to a given entity.
        
        Args:
            entity_id: ID of the entity to find similar to
            top_k: Number of similar entities to return
            exclude_self: Whether to exclude the query entity from results
            
        Returns:
            List of similar entities
        """
        if entity_id not in self.entities:
            raise ValueError(f"Entity {entity_id} not found")
            
        # Get entity's embedding
        entity_idx = self.entity_ids.index(entity_id)
        entity_embedding = self.embeddings[entity_idx]
        
        # Compute similarities
        similarities = self.cosine_similarity(entity_embedding)
        
        # Create results
        results = []
        for idx, (other_id, similarity) in enumerate(zip(self.entity_ids, similarities)):
            if exclude_self and other_id == entity_id:
                continue
                
            entity_type, entity_data = self.entities[other_id]
            
            results.append(SearchResult(
                entity_id=other_id,
                entity_type=entity_type,
                entity_data=entity_data,
                similarity_score=float(similarity),
                rank=0
            ))
        
        # Sort and limit
        results.sort(key=lambda x: x.similarity_score, reverse=True)
        
        for i, result in enumerate(results[:top_k]):
            result.rank = i + 1
            
        return results[:top_k]
        
    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about the search index."""
        entity_type_counts = {}
        for entity_id, (entity_type, _) in self.entities.items():
            entity_type_counts[entity_type] = entity_type_counts.get(entity_type, 0) + 1
            
        return {
            'total_entities': len(self.entities),
            'embedding_dimensions': self.embeddings.shape[1],
            'entity_types': entity_type_counts,
            'memory_usage_mb': self.embeddings.nbytes / (1024 * 1024)
        }


def main():
    """Example usage and testing."""
    # Initialize search engine
    print("Initializing vector search engine...")
    search_engine = VectorSearchEngine()
    
    # Print statistics
    stats = search_engine.get_statistics()
    print(f"\nSearch Index Statistics:")
    print(f"- Total entities: {stats['total_entities']}")
    print(f"- Embedding dimensions: {stats['embedding_dimensions']}")
    print(f"- Entity types: {stats['entity_types']}")
    print(f"- Memory usage: {stats['memory_usage_mb']:.2f} MB")
    
    # Test queries
    test_queries = [
        "British heavy metal bands",
        "Bands similar to Black Sabbath",
        "Heavy metal pioneers",
        "Birmingham metal scene",
        "Dark atmospheric metal"
    ]
    
    print("\n" + "="*50)
    print("TESTING VECTOR SEARCH")
    print("="*50)
    
    for query in test_queries:
        print(f"\nQuery: '{query}'")
        print("-" * 40)
        
        results = search_engine.search(query, top_k=5, threshold=0.3)
        
        if not results:
            print("No results found")
            continue
            
        for result in results:
            name = result.entity_data.get('name', 'Unknown')
            print(f"{result.rank}. [{result.entity_type}] {name}")
            print(f"   Similarity: {result.similarity_score:.3f}")
            
            # Show additional details
            if result.entity_type == 'bands':
                year = result.entity_data.get('formed_year', 'Unknown')
                location = result.entity_data.get('origin_location', 'Unknown')
                print(f"   Formed: {year}, Origin: {location}")
            elif result.entity_type == 'albums':
                artist = result.entity_data.get('artist', 'Unknown')
                year = result.entity_data.get('release_year', 'Unknown')
                print(f"   Artist: {artist}, Released: {year}")
    
    # Test similar entity search
    print("\n" + "="*50)
    print("TESTING SIMILAR ENTITY SEARCH")
    print("="*50)
    
    # Find entities similar to Black Sabbath
    black_sabbath_id = "bands:Black Sabbath"
    if black_sabbath_id in search_engine.entities:
        print(f"\nFinding entities similar to Black Sabbath...")
        similar = search_engine.find_similar_entities(black_sabbath_id, top_k=5)
        
        for result in similar:
            name = result.entity_data.get('name', 'Unknown')
            print(f"{result.rank}. [{result.entity_type}] {name}")
            print(f"   Similarity: {result.similarity_score:.3f}")


if __name__ == "__main__":
    main()