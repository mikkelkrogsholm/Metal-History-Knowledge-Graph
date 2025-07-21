"""
Confidence scoring for entity extraction
Assesses the quality and reliability of extracted entities
"""

import re
from typing import Any, Dict, List, Optional, Union
from datetime import datetime

class ConfidenceScorer:
    """Score extraction confidence based on various signals"""
    
    def __init__(self):
        # Pattern dictionaries for different confidence levels
        self.patterns = {
            'high_confidence': [
                # Date patterns
                r'formed in \d{4}',
                r'released in \d{4}',
                r'founded in \d{4}',
                r'born (?:on\s+)?(?:\w+\s+)?\d{1,2},?\s*\d{4}',
                r'died (?:on\s+)?(?:\w+\s+)?\d{1,2},?\s*\d{4}',
                
                # Definitive statements
                r'pioneered',
                r'invented',
                r'created',
                r'established',
                r'founded',
                r'recorded at',
                r'produced by',
                
                # Clear relationships
                r'member of',
                r'played (?:guitar|bass|drums|vocals) (?:for|in)',
                r'formed by',
                r'consists of',
                
                # Technical specifications
                r'\d+(?:-string|string)',
                r'\d+(?:\.\d+)?["\']\s*(?:gauge|scale)',
                r'\d+\s*(?:BPM|bpm)',
                r'\d+\s*(?:Hz|hz|kHz)',
            ],
            
            'medium_confidence': [
                # Less definitive language
                r'influenced by',
                r'similar to',
                r'emerged from',
                r'developed from',
                r'inspired by',
                r'associated with',
                r'known for',
                r'often',
                r'typically',
                r'generally',
                
                # Approximate dates
                r'early \d{4}s',
                r'mid-?\d{4}s',
                r'late \d{4}s',
                r'around \d{4}',
                r'circa \d{4}',
            ],
            
            'low_confidence': [
                # Uncertain language
                r'possibly',
                r'might have',
                r'some say',
                r'allegedly',
                r'reportedly',
                r'believed to',
                r'thought to',
                r'may have',
                r'perhaps',
                r'unclear',
                r'disputed',
                r'controversial',
            ]
        }
        
        # Entity completeness weights
        self.completeness_weights = {
            'Band': {
                'formed_year': 0.15,
                'origin_city': 0.10,
                'origin_country': 0.10,
                'description': 0.05
            },
            'Person': {
                'instruments': 0.15,
                'associated_bands': 0.15,
                'description': 0.05
            },
            'Album': {
                'artist': 0.10,
                'release_year': 0.15,
                'label': 0.05,
                'studio': 0.05
            },
            'Movement': {
                'start_year': 0.15,
                'geographic_center': 0.10,
                'key_bands': 0.15,
                'characteristics': 0.10
            },
            'Equipment': {
                'type': 0.10,
                'manufacturer': 0.10,
                'specifications': 0.15,
                'associated_bands': 0.10
            }
        }
        
        # Source reliability indicators
        self.source_indicators = {
            'high_reliability': [
                'according to',
                'documented in',
                'recorded in',
                'confirmed by',
                'verified',
                'official',
            ],
            'medium_reliability': [
                'stated',
                'claimed',
                'described as',
                'noted',
            ],
            'low_reliability': [
                'rumored',
                'gossip',
                'unconfirmed',
                'speculation',
            ]
        }
    
    def score_entity(self, entity: Any, context: str, entity_type: str) -> float:
        """
        Score an entity's extraction confidence
        
        Args:
            entity: The extracted entity object
            context: The text context where entity was found
            entity_type: Type of entity (Band, Person, etc.)
            
        Returns:
            Confidence score between 0.0 and 1.0
        """
        score = 0.5  # Start with neutral confidence
        
        # 1. Check context patterns
        pattern_score = self._score_context_patterns(context)
        score = 0.3 * score + 0.3 * pattern_score
        
        # 2. Check entity completeness
        completeness_score = self._score_completeness(entity, entity_type)
        score = 0.7 * score + 0.3 * completeness_score
        
        # 3. Check source reliability
        source_score = self._score_source_reliability(context)
        score = 0.8 * score + 0.2 * source_score
        
        # 4. Apply entity-specific adjustments
        score = self._apply_entity_specific_rules(entity, score, entity_type)
        
        # Ensure score is within bounds
        return max(0.0, min(1.0, score))
    
    def _score_context_patterns(self, context: str) -> float:
        """Score based on language patterns in context"""
        context_lower = context.lower()
        
        high_matches = sum(1 for pattern in self.patterns['high_confidence'] 
                          if re.search(pattern, context_lower))
        medium_matches = sum(1 for pattern in self.patterns['medium_confidence'] 
                            if re.search(pattern, context_lower))
        low_matches = sum(1 for pattern in self.patterns['low_confidence'] 
                         if re.search(pattern, context_lower))
        
        # Calculate weighted score
        if high_matches > 0:
            base_score = 0.8
        elif medium_matches > 0:
            base_score = 0.5
        else:
            base_score = 0.3
        
        # Penalize for uncertainty markers
        if low_matches > 0:
            base_score *= (1 - 0.1 * min(low_matches, 3))
        
        # Boost for multiple high confidence patterns
        if high_matches > 1:
            base_score = min(1.0, base_score + 0.1 * (high_matches - 1))
        
        return base_score
    
    def _score_completeness(self, entity: Any, entity_type: str) -> float:
        """Score based on how complete the entity information is"""
        if entity_type not in self.completeness_weights:
            return 0.5  # Default score for unknown types
        
        weights = self.completeness_weights[entity_type]
        total_weight = sum(weights.values())
        achieved_weight = 0.0
        
        # Base score for having required fields
        achieved_weight += 0.4  # Name/title is always required
        
        for field, weight in weights.items():
            if hasattr(entity, field):
                value = getattr(entity, field)
                if value is not None:
                    if isinstance(value, list) and len(value) > 0:
                        achieved_weight += weight
                    elif isinstance(value, str) and value.strip():
                        achieved_weight += weight
                    elif isinstance(value, (int, float)):
                        achieved_weight += weight
        
        return achieved_weight / (total_weight + 0.4)
    
    def _score_source_reliability(self, context: str) -> float:
        """Score based on source reliability indicators"""
        context_lower = context.lower()
        
        for indicator in self.source_indicators['high_reliability']:
            if indicator in context_lower:
                return 0.9
        
        for indicator in self.source_indicators['medium_reliability']:
            if indicator in context_lower:
                return 0.6
        
        for indicator in self.source_indicators['low_reliability']:
            if indicator in context_lower:
                return 0.3
        
        return 0.5  # Default neutral score
    
    def _apply_entity_specific_rules(self, entity: Any, score: float, entity_type: str) -> float:
        """Apply entity-specific scoring adjustments"""
        
        if entity_type == 'Band':
            # Boost score if formation year is reasonable
            if hasattr(entity, 'formed_year') and entity.formed_year:
                if 1960 <= entity.formed_year <= datetime.now().year:
                    score += 0.05
                else:
                    score -= 0.1  # Penalize unrealistic years
        
        elif entity_type == 'Album':
            # Check for complete album info
            if (hasattr(entity, 'artist') and entity.artist and
                hasattr(entity, 'release_year') and entity.release_year):
                score += 0.05
        
        elif entity_type == 'Equipment':
            # Boost for technical specifications
            if hasattr(entity, 'specifications') and entity.specifications:
                if re.search(r'\d+', entity.specifications):  # Has numeric specs
                    score += 0.1
        
        elif entity_type == 'Movement':
            # Check for multiple key bands
            if hasattr(entity, 'key_bands') and len(entity.key_bands) >= 3:
                score += 0.05
        
        elif entity_type == 'TechnicalDetail':
            # Boost for precise specifications
            if hasattr(entity, 'specification') and entity.specification:
                if re.search(r'\d+(?:\.\d+)?', entity.specification):
                    score += 0.1
        
        return score
    
    def score_extraction_batch(self, extraction_result: Dict[str, List[Any]], 
                             contexts: Dict[str, str]) -> Dict[str, List[float]]:
        """
        Score a batch of extracted entities
        
        Args:
            extraction_result: Dictionary of entity type to list of entities
            contexts: Dictionary mapping entity to its context
            
        Returns:
            Dictionary of entity type to list of confidence scores
        """
        scores = {}
        
        for entity_type, entities in extraction_result.items():
            entity_scores = []
            for entity in entities:
                # Get context for this entity
                entity_key = f"{entity_type}:{getattr(entity, 'name', getattr(entity, 'title', str(entity)))}"
                context = contexts.get(entity_key, "")
                
                # Calculate score
                score = self.score_entity(entity, context, entity_type)
                entity_scores.append(score)
            
            scores[entity_type] = entity_scores
        
        return scores
    
    def get_confidence_report(self, scores: Dict[str, List[float]]) -> Dict[str, Any]:
        """Generate a confidence report from scores"""
        report = {
            'overall_confidence': 0.0,
            'entity_type_confidence': {},
            'high_confidence_count': 0,
            'medium_confidence_count': 0,
            'low_confidence_count': 0,
            'total_entities': 0
        }
        
        all_scores = []
        
        for entity_type, type_scores in scores.items():
            if type_scores:
                avg_score = sum(type_scores) / len(type_scores)
                report['entity_type_confidence'][entity_type] = {
                    'average': avg_score,
                    'min': min(type_scores),
                    'max': max(type_scores),
                    'count': len(type_scores)
                }
                all_scores.extend(type_scores)
                
                # Count confidence levels
                for score in type_scores:
                    if score >= 0.7:
                        report['high_confidence_count'] += 1
                    elif score >= 0.4:
                        report['medium_confidence_count'] += 1
                    else:
                        report['low_confidence_count'] += 1
        
        report['total_entities'] = len(all_scores)
        if all_scores:
            report['overall_confidence'] = sum(all_scores) / len(all_scores)
        
        return report