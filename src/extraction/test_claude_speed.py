#!/usr/bin/env python3
"""
Test Claude CLI speed vs Ollama for entity extraction.
"""

import time
import json
import subprocess
import ollama
from pathlib import Path
import sys

# Add project root
sys.path.append(str(Path(__file__).parent.parent.parent))
from src.extraction.extraction_schemas import ExtractionResult

def test_claude_cli(text: str) -> tuple[float, int]:
    """Test Claude CLI extraction speed."""
    prompt = f"""Extract entities from this text. Return ONLY valid JSON matching this structure:
{{
  "bands": [{{"name": "...", "formed_year": null, "origin_city": null, "origin_country": null, "description": "..."}}],
  "people": [{{"name": "...", "instruments": [], "associated_bands": [], "description": "..."}}],
  "albums": [],
  "songs": [],
  "subgenres": [],
  "locations": [],
  "events": [],
  "equipment": [],
  "studios": [],
  "labels": [],
  "relationships": []
}}

Text: {text[:1000]}...  # Truncate for testing

Extract all bands, people, and their relationships."""

    start = time.time()
    try:
        # Use simpler command
        result = subprocess.run(
            ['claude', '-p', prompt],
            capture_output=True,
            text=True,
            timeout=30
        )
        duration = time.time() - start
        
        # Try to count entities
        entity_count = 0
        if result.returncode == 0:
            try:
                # Find JSON in output (Claude might add text around it)
                output = result.stdout
                start_idx = output.find('{')
                end_idx = output.rfind('}') + 1
                if start_idx >= 0 and end_idx > start_idx:
                    json_str = output[start_idx:end_idx]
                    data = json.loads(json_str)
                    for key, value in data.items():
                        if isinstance(value, list):
                            entity_count += len(value)
            except:
                pass
                
        return duration, entity_count
        
    except subprocess.TimeoutExpired:
        return 30.0, 0
    except Exception as e:
        print(f"Error: {e}")
        return 0.0, 0

def test_ollama(text: str) -> tuple[float, int]:
    """Test Ollama/Magistral extraction speed."""
    prompt = f"""Extract entities from this text and return JSON:
Text: {text[:1000]}...

Extract bands, people, albums."""
    
    start = time.time()
    try:
        response = ollama.chat(
            model='magistral:24b',
            messages=[{'role': 'user', 'content': prompt}],
            options={'temperature': 0.1}
        )
        duration = time.time() - start
        
        # Try to count entities mentioned
        content = response['message']['content'].lower()
        entity_count = content.count('band') + content.count('person') + content.count('album')
        
        return duration, entity_count
        
    except Exception as e:
        print(f"Ollama error: {e}")
        return 0.0, 0

def main():
    # Load a test chunk
    with open('history/chunks_optimized.json', 'r') as f:
        data = json.load(f)
    
    # Get first chunk text
    first_doc = list(data['documents'].keys())[0]
    chunks = []
    
    # Find actual chunks
    for doc_name, doc_data in data['documents'].items():
        if isinstance(doc_data, list):
            for i, chunk in enumerate(doc_data):
                if isinstance(chunk, dict) and 'text' in chunk:
                    chunks.append(chunk['text'])
                    if len(chunks) >= 3:
                        break
        if len(chunks) >= 3:
            break
    
    if not chunks:
        print("Could not find chunk text in the expected format")
        return
    
    test_text = chunks[0] if chunks else "Black Sabbath formed in 1968. Tony Iommi played guitar."
    
    print("PERFORMANCE COMPARISON")
    print("=" * 50)
    print(f"Test text length: {len(test_text)} characters")
    print()
    
    # Test Claude CLI
    print("Testing Claude CLI...")
    claude_time, claude_entities = test_claude_cli(test_text)
    print(f"  Time: {claude_time:.2f}s")
    print(f"  Entities found: {claude_entities}")
    print()
    
    # Test Ollama (optional - might be slow)
    print("Testing Ollama/Magistral (this may take a while)...")
    print("Skipping Ollama test - we know it's slow (130+ seconds per chunk)")
    # ollama_time, ollama_entities = test_ollama(test_text)
    # print(f"  Time: {ollama_time:.2f}s")
    # print(f"  Entities mentioned: ~{ollama_entities}")
    
    print()
    print("SUMMARY")
    print("=" * 50)
    print(f"Claude CLI: ~{claude_time:.1f}s per chunk")
    print(f"Ollama/Magistral: ~130s per chunk (from previous tests)")
    print(f"Speed improvement: ~{130/claude_time:.0f}x faster")
    print()
    print(f"Time to process 62 chunks:")
    print(f"  Claude CLI: ~{62 * claude_time / 60:.1f} minutes")
    print(f"  Ollama: ~{62 * 130 / 60:.1f} minutes")

if __name__ == "__main__":
    main()