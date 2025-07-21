#!/usr/bin/env python3
"""
Enhanced entity extraction with specialized prompts for all entity types
"""

import json
import ollama
from typing import List, Dict, Any, Optional, Tuple
from .extraction_schemas_enhanced import (
    EnhancedExtractionResult, Equipment, Movement, ProductionStyle,
    Venue, Platform, TechnicalDetail, AcademicResource, Compilation,
    ViralPhenomenon, Web3Project
)
from .specialized_prompts import (
    EQUIPMENT_EXTRACTION_PROMPT, MOVEMENT_EXTRACTION_PROMPT,
    PRODUCTION_STYLE_EXTRACTION_PROMPT, VENUE_EXTRACTION_PROMPT,
    PLATFORM_EXTRACTION_PROMPT, TECHNICAL_DETAIL_EXTRACTION_PROMPT,
    ACADEMIC_RESOURCE_EXTRACTION_PROMPT, COMPILATION_EXTRACTION_PROMPT,
    VIRAL_PHENOMENON_EXTRACTION_PROMPT, WEB3_PROJECT_EXTRACTION_PROMPT,
    create_combined_extraction_prompt
)
from .confidence_scorer import ConfidenceScorer
from .prompts import segment_by_sections
import asyncio
from tqdm import tqdm
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SpecializedExtractor:
    """Extract entities using specialized prompts for each type"""
    
    def __init__(self, model: str = 'magistral:24b'):
        self.model = model
        self.confidence_scorer = ConfidenceScorer()
        self.extraction_options = {
            'temperature': 0.1,
            'num_ctx': 32768,
            'top_p': 0.9,
        }
    
    def extract_equipment(self, text: str) -> Tuple[List[Equipment], Dict[str, float]]:
        """Extract equipment entities with confidence scores"""
        prompt = EQUIPMENT_EXTRACTION_PROMPT.format(text=text)
        
        try:
            response = ollama.chat(
                model=self.model,
                messages=[
                    {'role': 'system', 'content': 'You are an expert at extracting musical equipment from texts.'},
                    {'role': 'user', 'content': prompt}
                ],
                format={
                    "type": "object",
                    "properties": {
                        "equipment": {
                            "type": "array",
                            "items": Equipment.model_json_schema()
                        }
                    }
                },
                options=self.extraction_options
            )
            
            result = json.loads(response.message.content)
            equipment_list = [Equipment(**item) for item in result.get('equipment', [])]
            
            # Score each entity
            scores = {}
            for eq in equipment_list:
                score = self.confidence_scorer.score_entity(eq, text, 'Equipment')
                eq.confidence = score
                scores[eq.name] = score
            
            return equipment_list, scores
            
        except Exception as e:
            logger.error(f"Equipment extraction error: {e}")
            return [], {}
    
    def extract_movements(self, text: str) -> Tuple[List[Movement], Dict[str, float]]:
        """Extract movement entities with confidence scores"""
        prompt = MOVEMENT_EXTRACTION_PROMPT.format(text=text)
        
        try:
            response = ollama.chat(
                model=self.model,
                messages=[
                    {'role': 'system', 'content': 'You are an expert at identifying musical movements in metal history.'},
                    {'role': 'user', 'content': prompt}
                ],
                format={
                    "type": "object",
                    "properties": {
                        "movements": {
                            "type": "array",
                            "items": Movement.model_json_schema()
                        }
                    }
                },
                options=self.extraction_options
            )
            
            result = json.loads(response.message.content)
            movements_list = [Movement(**item) for item in result.get('movements', [])]
            
            # Score each entity
            scores = {}
            for mov in movements_list:
                score = self.confidence_scorer.score_entity(mov, text, 'Movement')
                mov.confidence = score
                scores[mov.name] = score
            
            return movements_list, scores
            
        except Exception as e:
            logger.error(f"Movement extraction error: {e}")
            return [], {}
    
    def extract_production_styles(self, text: str) -> Tuple[List[ProductionStyle], Dict[str, float]]:
        """Extract production style entities with confidence scores"""
        prompt = PRODUCTION_STYLE_EXTRACTION_PROMPT.format(text=text)
        
        try:
            response = ollama.chat(
                model=self.model,
                messages=[
                    {'role': 'system', 'content': 'You are an expert at identifying production styles in metal music.'},
                    {'role': 'user', 'content': prompt}
                ],
                format={
                    "type": "object",
                    "properties": {
                        "production_styles": {
                            "type": "array",
                            "items": ProductionStyle.model_json_schema()
                        }
                    }
                },
                options=self.extraction_options
            )
            
            result = json.loads(response.message.content)
            styles_list = [ProductionStyle(**item) for item in result.get('production_styles', [])]
            
            # Score each entity
            scores = {}
            for style in styles_list:
                score = self.confidence_scorer.score_entity(style, text, 'ProductionStyle')
                style.confidence = score
                scores[style.name] = score
            
            return styles_list, scores
            
        except Exception as e:
            logger.error(f"Production style extraction error: {e}")
            return [], {}
    
    def extract_venues(self, text: str) -> Tuple[List[Venue], Dict[str, float]]:
        """Extract venue entities with confidence scores"""
        prompt = VENUE_EXTRACTION_PROMPT.format(text=text)
        
        try:
            response = ollama.chat(
                model=self.model,
                messages=[
                    {'role': 'system', 'content': 'You are an expert at identifying important venues in metal history.'},
                    {'role': 'user', 'content': prompt}
                ],
                format={
                    "type": "object",
                    "properties": {
                        "venues": {
                            "type": "array",
                            "items": Venue.model_json_schema()
                        }
                    }
                },
                options=self.extraction_options
            )
            
            result = json.loads(response.message.content)
            venues_list = [Venue(**item) for item in result.get('venues', [])]
            
            # Score each entity
            scores = {}
            for venue in venues_list:
                score = self.confidence_scorer.score_entity(venue, text, 'Venue')
                venue.confidence = score
                scores[venue.name] = score
            
            return venues_list, scores
            
        except Exception as e:
            logger.error(f"Venue extraction error: {e}")
            return [], {}
    
    def extract_platforms(self, text: str) -> Tuple[List[Platform], Dict[str, float]]:
        """Extract platform entities with confidence scores"""
        prompt = PLATFORM_EXTRACTION_PROMPT.format(text=text)
        
        try:
            response = ollama.chat(
                model=self.model,
                messages=[
                    {'role': 'system', 'content': 'You are an expert at identifying technology platforms in metal history.'},
                    {'role': 'user', 'content': prompt}
                ],
                format={
                    "type": "object",
                    "properties": {
                        "platforms": {
                            "type": "array",
                            "items": Platform.model_json_schema()
                        }
                    }
                },
                options=self.extraction_options
            )
            
            result = json.loads(response.message.content)
            platforms_list = [Platform(**item) for item in result.get('platforms', [])]
            
            # Score each entity
            scores = {}
            for platform in platforms_list:
                score = self.confidence_scorer.score_entity(platform, text, 'Platform')
                platform.confidence = score
                scores[platform.name] = score
            
            return platforms_list, scores
            
        except Exception as e:
            logger.error(f"Platform extraction error: {e}")
            return [], {}
    
    def extract_all_specialized(self, text: str) -> EnhancedExtractionResult:
        """
        Extract all specialized entity types from text
        Uses the combined extraction approach for efficiency
        """
        prompt = create_combined_extraction_prompt(text)
        
        try:
            response = ollama.chat(
                model=self.model,
                messages=[
                    {'role': 'system', 'content': 'You are an expert at extracting ALL types of entities from metal history texts.'},
                    {'role': 'user', 'content': prompt}
                ],
                format=EnhancedExtractionResult.model_json_schema(),
                options=self.extraction_options
            )
            
            result = EnhancedExtractionResult.model_validate_json(response.message.content)
            
            # Score all entities
            self._score_all_entities(result, text)
            
            # Add extraction metadata
            result.extraction_metadata = {
                'model': self.model,
                'temperature': self.extraction_options['temperature'],
                'text_length': len(text),
                'extraction_method': 'combined_specialized'
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Combined extraction error: {e}")
            return EnhancedExtractionResult()
    
    def _score_all_entities(self, result: EnhancedExtractionResult, text: str):
        """Add confidence scores to all entities in the result"""
        # Score each entity type
        entity_mappings = [
            ('bands', 'Band'),
            ('people', 'Person'),
            ('albums', 'Album'),
            ('songs', 'Song'),
            ('subgenres', 'Subgenre'),
            ('locations', 'Location'),
            ('events', 'Event'),
            ('studios', 'Studio'),
            ('labels', 'Label'),
            ('equipment', 'Equipment'),
            ('movements', 'Movement'),
            ('technical_details', 'TechnicalDetail'),
            ('platforms', 'Platform'),
            ('academic_resources', 'AcademicResource'),
            ('viral_phenomena', 'ViralPhenomenon'),
            ('web3_projects', 'Web3Project'),
            ('production_styles', 'ProductionStyle'),
            ('compilations', 'Compilation'),
            ('venues', 'Venue')
        ]
        
        for attr_name, entity_type in entity_mappings:
            entities = getattr(result, attr_name, [])
            for entity in entities:
                score = self.confidence_scorer.score_entity(entity, text, entity_type)
                entity.confidence = score
    
    def extract_from_chunks(self, chunks: List[Dict[str, Any]], 
                          limit: Optional[int] = None,
                          use_specialized: bool = True) -> Dict[str, Any]:
        """
        Extract entities from multiple text chunks
        
        Args:
            chunks: List of text chunks with metadata
            limit: Maximum number of chunks to process
            use_specialized: Whether to use specialized extraction
            
        Returns:
            Dictionary with all extracted entities and metadata
        """
        if limit:
            chunks = chunks[:limit]
        
        logger.info(f"Processing {len(chunks)} chunks with specialized extraction...")
        
        all_results = {
            'bands': [],
            'people': [],
            'albums': [],
            'songs': [],
            'subgenres': [],
            'locations': [],
            'events': [],
            'studios': [],
            'labels': [],
            'equipment': [],
            'movements': [],
            'technical_details': [],
            'platforms': [],
            'academic_resources': [],
            'viral_phenomena': [],
            'web3_projects': [],
            'production_styles': [],
            'compilations': [],
            'venues': [],
            'relationships': []
        }
        
        confidence_scores = []
        extraction_metadata = []
        
        for chunk in tqdm(chunks, desc="Extracting entities"):
            try:
                if use_specialized:
                    result = self.extract_all_specialized(chunk['text'])
                else:
                    # Fall back to original extraction if needed
                    from .enhanced_extraction import extract_entities_enhanced
                    basic_result = extract_entities_enhanced(chunk['text'])
                    # Convert to enhanced result
                    result = self._convert_to_enhanced(basic_result)
                
                # Collect entities
                for entity_type in all_results.keys():
                    entities = getattr(result, entity_type, [])
                    all_results[entity_type].extend(entities)
                
                # Collect confidence scores
                chunk_scores = {}
                for entity_type in all_results.keys():
                    entities = getattr(result, entity_type, [])
                    if entities:
                        scores = [getattr(e, 'confidence', 0.5) for e in entities]
                        chunk_scores[entity_type] = sum(scores) / len(scores) if scores else 0.0
                
                confidence_scores.append({
                    'chunk_id': chunk.get('chunk_id', 0),
                    'scores': chunk_scores,
                    'overall': sum(chunk_scores.values()) / len(chunk_scores) if chunk_scores else 0.0
                })
                
                # Collect metadata
                if result.extraction_metadata:
                    extraction_metadata.append({
                        'chunk_id': chunk.get('chunk_id', 0),
                        **result.extraction_metadata
                    })
                
            except Exception as e:
                logger.error(f"Error processing chunk {chunk.get('chunk_id', 'unknown')}: {e}")
                continue
        
        # Generate confidence report
        all_entity_scores = {}
        for entity_type, entities in all_results.items():
            if entities:
                scores = [getattr(e, 'confidence', 0.5) for e in entities]
                all_entity_scores[entity_type] = scores
        
        confidence_report = self.confidence_scorer.get_confidence_report(all_entity_scores)
        
        return {
            'entities': all_results,
            'metadata': {
                'chunks_processed': len(chunks),
                'extraction_method': 'specialized' if use_specialized else 'basic',
                'confidence_report': confidence_report,
                'chunk_scores': confidence_scores,
                'extraction_metadata': extraction_metadata
            }
        }
    
    def _convert_to_enhanced(self, basic_result) -> EnhancedExtractionResult:
        """Convert basic extraction result to enhanced format"""
        enhanced = EnhancedExtractionResult()
        
        # Copy over existing entities
        for attr in ['bands', 'people', 'albums', 'songs', 'subgenres', 
                    'locations', 'events', 'studios', 'labels', 'equipment',
                    'relationships']:
            if hasattr(basic_result, attr):
                setattr(enhanced, attr, getattr(basic_result, attr))
        
        return enhanced


def main():
    """Test specialized extraction"""
    extractor = SpecializedExtractor()
    
    # Test text with various entity types
    test_text = """
    The New Wave of British Heavy Metal (NWOBHM) emerged in the late 1970s, 
    centered around venues like the Bandwagon Soundhouse in London. Bands like 
    Iron Maiden used Boss HM-2 pedals to create their signature sound, recording 
    at Battery Studios with producer Martin Birch. The movement spawned over 1000 
    bands and was documented in the compilation "Metal for Muthas" (1980).
    
    In the 2020s, metal went viral on TikTok with #Metaltok garnering over 300 
    million views. Bands experimented with NFT releases, with Avenged Sevenfold 
    launching the Deathbats Club NFT collection.
    """
    
    print("Testing specialized extraction...")
    result = extractor.extract_all_specialized(test_text)
    
    print(f"\nExtracted {len(result.movements)} movements:")
    for mov in result.movements:
        print(f"  - {mov.name} (confidence: {mov.confidence:.2f})")
    
    print(f"\nExtracted {len(result.equipment)} equipment items:")
    for eq in result.equipment:
        print(f"  - {eq.name} (confidence: {eq.confidence:.2f})")
    
    print(f"\nExtracted {len(result.venues)} venues:")
    for venue in result.venues:
        print(f"  - {venue.name} (confidence: {venue.confidence:.2f})")
    
    print(f"\nExtracted {len(result.platforms)} platforms:")
    for platform in result.platforms:
        print(f"  - {platform.name} (confidence: {platform.confidence:.2f})")


if __name__ == "__main__":
    main()