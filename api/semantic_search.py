"""
Semantic search implementation for Metal History API
Uses embeddings for intelligent entity discovery
"""

import numpy as np
from typing import List, Dict, Any, Optional, Tuple
import json
import logging
import time
import ollama
from sklearn.metrics.pairwise import cosine_similarity
import os

logger = logging.getLogger(__name__)

class SemanticSearchEngine:
    """Handles semantic search using pre-computed embeddings"""
    
    def __init__(
        self,
        embeddings_path: str = "../entities_with_embeddings.json",
        model: str = "snowflake-arctic-embed2:latest",
        dimension: int = 1024
    ):
        self.embeddings_path = embeddings_path
        self.model = model
        self.dimension = dimension
        self.entities_data = None
        self.embeddings_matrix = None
        self.entity_index = {}
        self._load_embeddings()
        
    def _load_embeddings(self):
        """Load pre-computed embeddings from file"""
        try:
            with open(self.embeddings_path, 'r') as f:
                data = json.load(f)
                
            self.entities_data = data
            
            # Build embeddings matrix and index
            embeddings_list = []
            index = 0
            
            for entity_type in ['bands', 'albums', 'people', 'songs', 'geographic_locations', 'subgenres']:
                if entity_type in data:
                    for entity_id, entity_data in data[entity_type].items():
                        if 'embedding' in entity_data and entity_data['embedding']:
                            embeddings_list.append(entity_data['embedding'])
                            self.entity_index[index] = {
                                'type': entity_type,
                                'id': entity_id,
                                'data': entity_data
                            }
                            index += 1
                            
            # Convert to numpy array for efficient computation
            self.embeddings_matrix = np.array(embeddings_list)
            logger.info(f"Loaded {len(self.entity_index)} embeddings from {self.embeddings_path}")
            
        except Exception as e:
            logger.error(f"Failed to load embeddings: {e}")
            self.embeddings_matrix = np.array([])
            
    def _get_query_embedding(self, query: str) -> Optional[np.ndarray]:
        """Generate embedding for search query"""
        try:
            response = ollama.embed(
                model=self.model,
                input=query
            )
            
            if 'embedding' in response:
                return np.array(response['embedding'])
            else:
                logger.error("No embedding in Ollama response")
                return None
                
        except Exception as e:
            logger.error(f"Failed to generate query embedding: {e}")
            return None
            
    def search(
        self,
        query: str,
        entity_types: Optional[List[str]] = None,
        limit: int = 10,
        threshold: float = 0.5
    ) -> List[Dict[str, Any]]:
        """
        Perform semantic search across entities
        
        Args:
            query: Search query text
            entity_types: Filter by entity types (bands, albums, etc.)
            limit: Maximum number of results
            threshold: Minimum similarity threshold (0-1)
            
        Returns:
            List of matching entities with relevance scores
        """
        if self.embeddings_matrix.size == 0:
            logger.warning("No embeddings loaded, falling back to empty results")
            return []
            
        # Get query embedding
        start_time = time.time()
        query_embedding = self._get_query_embedding(query)
        
        if query_embedding is None:
            return []
            
        # Calculate similarities
        query_embedding = query_embedding.reshape(1, -1)
        similarities = cosine_similarity(query_embedding, self.embeddings_matrix)[0]
        
        # Get top matches
        top_indices = np.argsort(similarities)[::-1]
        
        results = []
        for idx in top_indices:
            similarity = similarities[idx]
            
            # Skip if below threshold
            if similarity < threshold:
                break
                
            entity_info = self.entity_index[idx]
            
            # Filter by entity type if specified
            if entity_types and entity_info['type'] not in entity_types:
                continue
                
            # Build result
            result = {
                'entity_type': entity_info['type'],
                'id': entity_info['id'],
                'relevance_score': float(similarity),
                'data': entity_info['data']
            }
            
            results.append(result)
            
            if len(results) >= limit:
                break
                
        search_time = (time.time() - start_time) * 1000
        logger.info(f"Semantic search completed in {search_time:.2f}ms, found {len(results)} results")
        
        return results
    
    def find_similar(
        self,
        entity_id: str,
        entity_type: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Find entities similar to a given entity"""
        # Find the entity's embedding
        entity_embedding = None
        entity_idx = None
        
        for idx, info in self.entity_index.items():
            if info['id'] == entity_id and info['type'] == entity_type:
                entity_embedding = self.embeddings_matrix[idx]
                entity_idx = idx
                break
                
        if entity_embedding is None:
            logger.warning(f"Entity {entity_type}:{entity_id} not found in embeddings")
            return []
            
        # Calculate similarities
        entity_embedding = entity_embedding.reshape(1, -1)
        similarities = cosine_similarity(entity_embedding, self.embeddings_matrix)[0]
        
        # Get top matches (excluding the entity itself)
        top_indices = np.argsort(similarities)[::-1]
        
        results = []
        for idx in top_indices:
            if idx == entity_idx:
                continue
                
            similarity = similarities[idx]
            entity_info = self.entity_index[idx]
            
            result = {
                'entity_type': entity_info['type'],
                'id': entity_info['id'],
                'relevance_score': float(similarity),
                'data': entity_info['data']
            }
            
            results.append(result)
            
            if len(results) >= limit:
                break
                
        return results
    
    def get_entity_clusters(
        self,
        entity_type: str,
        n_clusters: int = 10,
        method: str = "kmeans"
    ) -> Dict[int, List[str]]:
        """Group entities into semantic clusters"""
        from sklearn.cluster import KMeans, DBSCAN
        
        # Get embeddings for specific entity type
        type_embeddings = []
        type_indices = []
        
        for idx, info in self.entity_index.items():
            if info['type'] == entity_type:
                type_embeddings.append(self.embeddings_matrix[idx])
                type_indices.append(idx)
                
        if not type_embeddings:
            return {}
            
        type_embeddings = np.array(type_embeddings)
        
        # Perform clustering
        if method == "kmeans":
            clusterer = KMeans(n_clusters=n_clusters, random_state=42)
            labels = clusterer.fit_predict(type_embeddings)
        elif method == "dbscan":
            clusterer = DBSCAN(eps=0.3, min_samples=5)
            labels = clusterer.fit_predict(type_embeddings)
        else:
            raise ValueError(f"Unknown clustering method: {method}")
            
        # Group entities by cluster
        clusters = {}
        for i, label in enumerate(labels):
            if label not in clusters:
                clusters[label] = []
            clusters[label].append(self.entity_index[type_indices[i]]['id'])
            
        return clusters
    
    def explain_similarity(
        self,
        entity1_id: str,
        entity1_type: str,
        entity2_id: str,
        entity2_type: str
    ) -> Dict[str, Any]:
        """Explain why two entities are similar"""
        # Get embeddings
        emb1 = None
        emb2 = None
        data1 = None
        data2 = None
        
        for idx, info in self.entity_index.items():
            if info['id'] == entity1_id and info['type'] == entity1_type:
                emb1 = self.embeddings_matrix[idx]
                data1 = info['data']
            elif info['id'] == entity2_id and info['type'] == entity2_type:
                emb2 = self.embeddings_matrix[idx]
                data2 = info['data']
                
        if emb1 is None or emb2 is None:
            return {"error": "One or both entities not found"}
            
        # Calculate similarity
        similarity = cosine_similarity(
            emb1.reshape(1, -1),
            emb2.reshape(1, -1)
        )[0][0]
        
        # Find common attributes
        common_attributes = []
        
        # Check genres
        if 'genres' in data1 and 'genres' in data2:
            common_genres = set(data1['genres']) & set(data2['genres'])
            if common_genres:
                common_attributes.append(f"genres: {', '.join(common_genres)}")
                
        # Check locations
        if 'origin_location' in data1 and 'origin_location' in data2:
            if data1['origin_location'] == data2['origin_location']:
                common_attributes.append(f"location: {data1['origin_location']}")
                
        # Check time period
        if 'formed_year' in data1 and 'formed_year' in data2:
            year_diff = abs(data1.get('formed_year', 0) - data2.get('formed_year', 0))
            if year_diff <= 5:
                common_attributes.append(f"time period: {year_diff} years apart")
                
        return {
            'entity1': {'id': entity1_id, 'type': entity1_type, 'name': data1.get('name')},
            'entity2': {'id': entity2_id, 'type': entity2_type, 'name': data2.get('name')},
            'similarity_score': float(similarity),
            'common_attributes': common_attributes,
            'explanation': self._generate_explanation(similarity, common_attributes)
        }
    
    def _generate_explanation(self, similarity: float, common_attributes: List[str]) -> str:
        """Generate human-readable explanation of similarity"""
        if similarity > 0.9:
            level = "extremely similar"
        elif similarity > 0.7:
            level = "very similar"
        elif similarity > 0.5:
            level = "moderately similar"
        else:
            level = "somewhat similar"
            
        explanation = f"These entities are {level} (similarity: {similarity:.2%})."
        
        if common_attributes:
            explanation += f" They share: {', '.join(common_attributes)}."
        else:
            explanation += " The similarity is based on semantic relationships in their descriptions."
            
        return explanation


class HybridSearchEngine:
    """Combines semantic and keyword search for best results"""
    
    def __init__(self, semantic_engine: SemanticSearchEngine, db_connection):
        self.semantic = semantic_engine
        self.db = db_connection
        
    def search(
        self,
        query: str,
        entity_types: Optional[List[str]] = None,
        limit: int = 10,
        semantic_weight: float = 0.7
    ) -> List[Dict[str, Any]]:
        """
        Perform hybrid search combining semantic and keyword matching
        
        Args:
            query: Search query
            entity_types: Filter by entity types
            limit: Maximum results
            semantic_weight: Weight for semantic results (0-1)
            
        Returns:
            Combined and ranked results
        """
        # Get semantic results
        semantic_results = self.semantic.search(
            query, 
            entity_types=entity_types,
            limit=limit * 2  # Get more for merging
        )
        
        # Get keyword results
        keyword_results = self._keyword_search(
            query,
            entity_types=entity_types,
            limit=limit * 2
        )
        
        # Merge and rank results
        merged = self._merge_results(
            semantic_results,
            keyword_results,
            semantic_weight
        )
        
        return merged[:limit]
    
    def _keyword_search(
        self,
        query: str,
        entity_types: Optional[List[str]],
        limit: int
    ) -> List[Dict[str, Any]]:
        """Perform keyword-based search in database"""
        results = []
        pattern = f".*{query}.*"
        
        if not entity_types or "bands" in entity_types:
            band_query = """
            MATCH (b:Band)
            WHERE b.name =~ $pattern OR b.description =~ $pattern
            RETURN 'band' as type, b.id as id, b.name as name,
                   b.description as description
            LIMIT $limit
            """
            
            band_results = self.db.execute_query(
                band_query,
                {"pattern": pattern, "limit": limit}
            )
            
            while band_results.has_next():
                row = band_results.get_next()
                results.append({
                    'entity_type': row[0],
                    'id': row[1],
                    'relevance_score': 1.0,  # Keyword match score
                    'data': {
                        'name': row[2],
                        'description': row[3]
                    }
                })
                
        # Add similar queries for albums, people, etc.
        
        return results
    
    def _merge_results(
        self,
        semantic_results: List[Dict[str, Any]],
        keyword_results: List[Dict[str, Any]],
        semantic_weight: float
    ) -> List[Dict[str, Any]]:
        """Merge and rank results from both search methods"""
        # Create a map of results by entity ID
        result_map = {}
        
        # Add semantic results
        for result in semantic_results:
            key = f"{result['entity_type']}:{result['id']}"
            result_map[key] = {
                **result,
                'final_score': result['relevance_score'] * semantic_weight,
                'match_types': ['semantic']
            }
            
        # Add or update with keyword results
        keyword_weight = 1 - semantic_weight
        for result in keyword_results:
            key = f"{result['entity_type']}:{result['id']}"
            
            if key in result_map:
                # Entity found in both - boost score
                result_map[key]['final_score'] += result['relevance_score'] * keyword_weight
                result_map[key]['match_types'].append('keyword')
            else:
                # Only in keyword results
                result_map[key] = {
                    **result,
                    'final_score': result['relevance_score'] * keyword_weight,
                    'match_types': ['keyword']
                }
                
        # Sort by final score
        sorted_results = sorted(
            result_map.values(),
            key=lambda x: x['final_score'],
            reverse=True
        )
        
        return sorted_results