#!/usr/bin/env python3
"""
OPTIONAL: Automated embedding generation pipeline for all entities.
Uses snowflake-arctic-embed2 model to generate 1024-dimensional embeddings.
NOTE: This is optional - only needed if you want semantic search capabilities.
"""

import json
try:
    import ollama
except ImportError:
    print("Warning: Ollama not installed. Embeddings are optional.")
    print("If you need semantic search, install ollama and run: ollama pull snowflake-arctic-embed2:latest")
    ollama = None
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional
import argparse
import logging
from tqdm import tqdm
import time
import sys

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.append(str(PROJECT_ROOT))

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class EmbeddingGenerator:
    """Generates embeddings for entities using Ollama."""
    
    def __init__(self, model: str = "snowflake-arctic-embed2:latest"):
        self.model = model
        self.stats = {
            'total_entities': 0,
            'embeddings_generated': 0,
            'failed_embeddings': 0,
            'generation_time': 0
        }
        
        # Verify model is available
        self._verify_model()
    
    def _verify_model(self):
        """Verify embedding model is available."""
        try:
            response = ollama.list()
            # Extract model names from the response
            if hasattr(response, 'models'):
                model_names = [m.model for m in response.models]
            else:
                # Fallback for different response types
                model_names = []
            
            if not any(self.model in name for name in model_names):
                logger.error(f"Model {self.model} not found!")
                logger.info("Available models: " + ", ".join(model_names))
                raise ValueError(f"Model {self.model} not available")
            logger.info(f"✓ Model {self.model} is available")
        except Exception as e:
            logger.error(f"Error checking models: {e}")
            raise
    
    def generate_embeddings_for_file(self, entities_file: str, output_file: str):
        """Generate embeddings for all entities in a file."""
        logger.info(f"Loading entities from {entities_file}")
        
        with open(entities_file, 'r') as f:
            data = json.load(f)
        
        entities = data.get('entities', {})
        
        # Process each entity type
        for entity_type, entity_list in entities.items():
            logger.info(f"Processing {len(entity_list)} {entity_type}")
            
            for entity in tqdm(entity_list, desc=f"Generating embeddings for {entity_type}"):
                self.stats['total_entities'] += 1
                
                # Generate embedding text
                embedding_text = self._create_embedding_text(entity_type, entity)
                
                # Generate embedding
                embedding = self._generate_embedding(embedding_text)
                
                if embedding is not None:
                    entity['embedding'] = embedding
                    self.stats['embeddings_generated'] += 1
                else:
                    self.stats['failed_embeddings'] += 1
        
        # Save updated entities
        logger.info(f"Saving entities with embeddings to {output_file}")
        with open(output_file, 'w') as f:
            json.dump(data, f, indent=2)
        
        self._print_summary()
    
    def _create_embedding_text(self, entity_type: str, entity: Dict) -> str:
        """Create text representation for embedding generation."""
        text_parts = []
        
        if entity_type == 'bands':
            text_parts.append(f"Band: {entity['name']}")
            if entity.get('formed_year'):
                text_parts.append(f"Formed: {entity['formed_year']}")
            if entity.get('origin_location'):
                text_parts.append(f"Origin: {entity['origin_location']}")
            if entity.get('genres'):
                text_parts.append(f"Genres: {', '.join(entity['genres'])}")
            if entity.get('description'):
                text_parts.append(entity['description'])
        
        elif entity_type == 'people':
            text_parts.append(f"Person: {entity['name']}")
            if entity.get('roles'):
                text_parts.append(f"Roles: {', '.join(entity['roles'])}")
            if entity.get('birth_year'):
                text_parts.append(f"Born: {entity['birth_year']}")
            if entity.get('known_for'):
                text_parts.append(f"Known for: {entity['known_for']}")
        
        elif entity_type == 'albums':
            text_parts.append(f"Album: {entity['title']}")
            if entity.get('band_name'):
                text_parts.append(f"By: {entity['band_name']}")
            if entity.get('release_year'):
                text_parts.append(f"Released: {entity['release_year']}")
            if entity.get('genres'):
                text_parts.append(f"Genres: {', '.join(entity['genres'])}")
        
        elif entity_type == 'songs':
            text_parts.append(f"Song: {entity['title']}")
            if entity.get('album_title'):
                text_parts.append(f"Album: {entity['album_title']}")
            if entity.get('band_name'):
                text_parts.append(f"By: {entity['band_name']}")
        
        elif entity_type == 'subgenres':
            text_parts.append(f"Subgenre: {entity['name']}")
            if entity.get('originated_year'):
                text_parts.append(f"Originated: {entity['originated_year']}")
            if entity.get('characteristics'):
                text_parts.append(f"Characteristics: {', '.join(entity['characteristics'])}")
            if entity.get('description'):
                text_parts.append(entity['description'])
        
        elif entity_type == 'locations':
            text_parts.append(f"Location: {entity.get('city', '')} {entity.get('country', '')}".strip())
            if entity.get('significance'):
                text_parts.append(f"Significance: {entity['significance']}")
        
        else:
            # Generic handling for other entity types
            if entity.get('name'):
                text_parts.append(f"{entity_type.rstrip('s').title()}: {entity['name']}")
            elif entity.get('title'):
                text_parts.append(f"{entity_type.rstrip('s').title()}: {entity['title']}")
            
            # Add any description or additional context
            for key in ['description', 'significance', 'characteristics']:
                if entity.get(key):
                    text_parts.append(str(entity[key]))
        
        return " | ".join(text_parts)
    
    def _generate_embedding(self, text: str) -> Optional[List[float]]:
        """Generate embedding for text using Ollama."""
        try:
            start_time = time.time()
            response = ollama.embeddings(
                model=self.model,
                prompt=text
            )
            self.stats['generation_time'] += time.time() - start_time
            
            return response['embedding']
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            return None
    
    def batch_generate_embeddings(self, input_dir: str, output_dir: str):
        """Process multiple entity files in a directory."""
        input_path = Path(input_dir)
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)
        
        entity_files = list(input_path.glob("*_entities.json"))
        
        logger.info(f"Found {len(entity_files)} entity files to process")
        
        for entity_file in entity_files:
            output_file = output_path / f"{entity_file.stem}_with_embeddings.json"
            logger.info(f"Processing {entity_file.name}")
            
            try:
                self.generate_embeddings_for_file(str(entity_file), str(output_file))
            except Exception as e:
                logger.error(f"Failed to process {entity_file}: {e}")
    
    def _print_summary(self):
        """Print generation summary."""
        print("\n" + "="*60)
        print("EMBEDDING GENERATION SUMMARY")
        print("="*60)
        print(f"Total entities: {self.stats['total_entities']}")
        print(f"Embeddings generated: {self.stats['embeddings_generated']}")
        print(f"Failed: {self.stats['failed_embeddings']}")
        print(f"Success rate: {(self.stats['embeddings_generated'] / max(1, self.stats['total_entities']) * 100):.1f}%")
        print(f"Total time: {self.stats['generation_time']:.1f}s")
        print(f"Avg time per embedding: {self.stats['generation_time'] / max(1, self.stats['embeddings_generated']):.3f}s")
        print("="*60)

def verify_embeddings(entities_file: str):
    """Verify embeddings in an entities file."""
    with open(entities_file, 'r') as f:
        data = json.load(f)
    
    entities = data.get('entities', {})
    
    print("\nEmbedding Verification:")
    print("-" * 40)
    
    for entity_type, entity_list in entities.items():
        with_embeddings = sum(1 for e in entity_list if 'embedding' in e)
        print(f"{entity_type}: {with_embeddings}/{len(entity_list)} have embeddings")
        
        if with_embeddings > 0:
            # Check embedding dimensions
            sample_embedding = next(e['embedding'] for e in entity_list if 'embedding' in e)
            print(f"  Embedding dimensions: {len(sample_embedding)}")

def main():
    parser = argparse.ArgumentParser(description="Generate embeddings for entities")
    parser.add_argument('input', type=str,
                       help='Input entities file or directory')
    parser.add_argument('--output', type=str,
                       help='Output file or directory')
    parser.add_argument('--model', type=str, default='snowflake-arctic-embed2:latest',
                       help='Ollama embedding model to use')
    parser.add_argument('--batch', action='store_true',
                       help='Process directory of entity files')
    parser.add_argument('--verify', action='store_true',
                       help='Verify embeddings in file')
    
    args = parser.parse_args()
    
    if args.verify:
        verify_embeddings(args.input)
    elif args.batch:
        if not args.output:
            args.output = 'embeddings_output'
        generator = EmbeddingGenerator(model=args.model)
        generator.batch_generate_embeddings(args.input, args.output)
    else:
        if not args.output:
            args.output = args.input.replace('.json', '_with_embeddings.json')
        generator = EmbeddingGenerator(model=args.model)
        generator.generate_embeddings_for_file(args.input, args.output)

if __name__ == "__main__":
    main()