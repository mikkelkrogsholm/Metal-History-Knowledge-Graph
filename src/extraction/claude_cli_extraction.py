#!/usr/bin/env python3
"""
Entity extraction using Claude Code CLI instead of Ollama.
Much faster than using local models!
"""

import json
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional
import logging
from tqdm import tqdm

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.append(str(PROJECT_ROOT))

from src.extraction.extraction_schemas import ExtractionResult
# from src.extraction.prompts import create_extraction_prompt  # Not needed

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ClaudeCliExtractor:
    """Extract entities using Claude Code CLI."""
    
    def __init__(self):
        # Check if Claude CLI is available
        try:
            result = subprocess.run(['claude', '--help'], capture_output=True, text=True)
            if result.returncode != 0:
                raise RuntimeError("Claude CLI not found. Please install Claude Code.")
        except FileNotFoundError:
            raise RuntimeError("Claude CLI not found. Please install Claude Code.")
    
    def extract_from_text(self, text: str) -> ExtractionResult:
        """Extract entities from text using Claude CLI."""
        
        # Create the extraction prompt
        extraction_prompt = f"""
Extract ALL entities and relationships from the following text. Be very thorough and include:

1. BANDS: Extract band names, formation years, cities of origin, and descriptions
2. PEOPLE: Extract musician names, their instruments (guitar, bass, drums, vocals), and associated bands
3. ALBUMS: Extract album titles, artists, release years/dates, labels, and studios
4. SONGS: Extract song titles, artists, albums they appear on, and BPM if mentioned
5. SUBGENRES: Extract genre names, era ranges, BPM ranges, tunings, vocal styles, and characteristics
6. LOCATIONS: Extract cities, regions, countries, and descriptions of local scenes
7. EVENTS: Extract event names, dates, types (festival/controversy/movement), and descriptions
8. EQUIPMENT: Extract equipment names (pedals, guitars, amps), types, and specifications
9. STUDIOS: Extract studio names, locations, and what they're famous for
10. LABELS: Extract record label names and founding years
11. RELATIONSHIPS: Extract all relationships between entities (who played in which band, which album was released by which band, where bands formed, etc.)

For dates, use YYYY-MM-DD format when full date is known, otherwise just YYYY.
For missing information, use null rather than guessing.

Text to analyze:
{text}

Please respond with a valid JSON object matching this schema:
{json.dumps(ExtractionResult.model_json_schema(), indent=2)}

Extract thoroughly - don't miss any entities!

IMPORTANT: Return ONLY the JSON object. Do not include any explanatory text before or after the JSON.
"""
        
        try:
            # Use Claude CLI with piped input and JSON output
            result = subprocess.run(
                ['claude', '--output-format', 'json'],
                input=extraction_prompt,
                capture_output=True,
                text=True,
                check=True
            )
            
            # Parse the JSON response
            response_data = json.loads(result.stdout)
            
            # Debug logging
            logger.debug(f"Claude response type: {type(response_data)}")
            logger.debug(f"Claude response keys: {response_data.keys() if isinstance(response_data, dict) else 'Not a dict'}")
            
            # Extract the actual content from Claude's response
            if isinstance(response_data, dict) and 'result' in response_data:
                content = response_data['result']
                logger.debug(f"Raw result content (first 300 chars): {content[:300] if isinstance(content, str) else content}")
                # The content should be a string containing JSON
                if isinstance(content, str):
                    # Claude might wrap the JSON in markdown code blocks
                    content = content.strip()
                    
                    # Find JSON in the response (might have explanatory text before it)
                    json_start = content.find('```json')
                    if json_start == -1:
                        json_start = content.find('```')
                    if json_start == -1:
                        json_start = content.find('{')
                    
                    if json_start > 0:
                        content = content[json_start:]
                    
                    # Check for markdown code blocks with or without language specifier
                    if content.startswith('```json\n'):
                        content = content[8:]  # Remove ```json\n
                    elif content.startswith('```json'):
                        content = content[7:]  # Remove ```json
                    elif content.startswith('```\n'):
                        content = content[4:]  # Remove ```\n
                    elif content.startswith('```'):
                        content = content[3:]  # Remove ```
                        
                    if content.endswith('\n```'):
                        content = content[:-4]  # Remove \n```
                    elif content.endswith('```'):
                        content = content[:-3]  # Remove ```
                        
                    content = content.strip()
                    
                    logger.debug(f"Cleaned content (first 200 chars): {content[:200]}...")
                    extracted_data = json.loads(content)
                    return ExtractionResult.model_validate(extracted_data)
                else:
                    return ExtractionResult.model_validate(content)
            else:
                # Try to parse directly
                return ExtractionResult.model_validate(response_data)
                
        except subprocess.CalledProcessError as e:
            logger.error(f"Claude CLI error: {e.stderr}")
            return ExtractionResult()
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            if 'result' in locals():
                logger.error(f"Raw stdout: {result.stdout[:500]}...")
                logger.error(f"Raw stderr: {result.stderr}")
            return ExtractionResult()
        except Exception as e:
            logger.error(f"Extraction error: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            return ExtractionResult()
    
    def extract_from_chunks(self, chunks_file: str, output_dir: str = "claude_extraction_output", limit: Optional[int] = None):
        """Extract entities from all chunks in a file."""
        
        # Create output directory
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)
        
        # Load chunks
        with open(chunks_file, 'r') as f:
            chunks_data = json.load(f)
        
        # Get all chunks from documents
        all_chunks = []
        for doc_name in chunks_data['documents']:
            doc_chunks = chunks_data['documents'][doc_name]
            for i, chunk in enumerate(doc_chunks):
                all_chunks.append({
                    'id': f"{doc_name}_{i:04d}",
                    'text': chunk['text'],
                    'metadata': chunk.get('metadata', {})
                })
        
        # Limit if requested
        if limit:
            all_chunks = all_chunks[:limit]
        
        logger.info(f"Processing {len(all_chunks)} chunks using Claude CLI...")
        
        # Process each chunk
        for chunk in tqdm(all_chunks, desc="Extracting entities"):
            chunk_id = chunk['id']
            output_file = output_path / f"chunk_{chunk_id}_entities.json"
            
            # Skip if already processed
            if output_file.exists():
                logger.info(f"Skipping {chunk_id} - already processed")
                continue
            
            # Extract entities
            result = self.extract_from_text(chunk['text'])
            
            # Convert to dict and add metadata
            result_dict = result.model_dump()
            
            # Add metadata to each entity
            for entity_type, entities in result_dict.items():
                if isinstance(entities, list):
                    for entity in entities:
                        entity['_metadata'] = {
                            'source_file': chunk_id.split('_')[0],
                            'chunk_id': chunk_id
                        }
            
            # Save result
            with open(output_file, 'w') as f:
                json.dump(result_dict, f, indent=2)
            
            logger.info(f"Processed {chunk_id}: {sum(len(v) if isinstance(v, list) else 0 for v in result_dict.values())} entities")

def main():
    """Run extraction using Claude CLI."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Extract entities using Claude Code CLI")
    parser.add_argument('--chunks', type=str, default='data/processed/chunks/chunks_optimized.json',
                       help='Path to chunks JSON file')
    parser.add_argument('--output-dir', type=str, default='data/processed/extracted',
                       help='Output directory for extracted entities')
    parser.add_argument('--limit', type=int, help='Limit number of chunks to process')
    parser.add_argument('--test', action='store_true', help='Test with a single chunk')
    
    args = parser.parse_args()
    
    extractor = ClaudeCliExtractor()
    
    if args.test:
        # Test with sample text
        test_text = "Black Sabbath formed in Birmingham in 1968. Tony Iommi played guitar."
        result = extractor.extract_from_text(test_text)
        print("Test extraction result:")
        print(json.dumps(result.model_dump(), indent=2))
    else:
        # Extract from chunks
        extractor.extract_from_chunks(args.chunks, args.output_dir, args.limit)

if __name__ == "__main__":
    main()