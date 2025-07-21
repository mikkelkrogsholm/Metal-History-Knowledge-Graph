#!/usr/bin/env python3
"""
Wikipedia enrichment for metal history entities
Fetches additional data from Wikipedia to validate and enrich entities
"""

import json
import time
import logging
from typing import Dict, List, Any, Optional
from pathlib import Path
import sys

# Try to import wikipedia-api, provide instructions if not available
try:
    import wikipediaapi
except ImportError:
    print("wikipedia-api not installed. Install with: pip install wikipedia-api")
    sys.exit(1)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class WikipediaEnricher:
    """Enrich entities with Wikipedia data"""
    
    def __init__(self, user_agent: str = "MetalHistoryKG/1.0 (metal.history@example.com)"):
        self.wiki = wikipediaapi.Wikipedia(user_agent, 'en')
        self.cache = {}
        self.rate_limit_delay = 0.5  # seconds between requests
        self.last_request_time = 0
        
    def _rate_limit(self):
        """Enforce rate limiting between requests"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.rate_limit_delay:
            time.sleep(self.rate_limit_delay - time_since_last)
        self.last_request_time = time.time()
    
    def _get_page(self, title: str) -> Optional[wikipediaapi.WikipediaPage]:
        """Get Wikipedia page with caching"""
        if title in self.cache:
            return self.cache[title]
        
        self._rate_limit()
        page = self.wiki.page(title)
        self.cache[title] = page
        return page
    
    def enrich_band(self, band_name: str, origin_country: Optional[str] = None) -> Dict[str, Any]:
        """
        Enrich band data with Wikipedia information
        
        Args:
            band_name: Name of the band
            origin_country: Country of origin (helps disambiguation)
            
        Returns:
            Dictionary with enriched data
        """
        enriched = {
            'wikipedia_found': False,
            'enrichment_source': 'wikipedia'
        }
        
        # Try different title variations
        variations = [
            band_name,
            f"{band_name} (band)",
            f"{band_name} (metal band)",
        ]
        
        # Add country-specific variations if provided
        if origin_country:
            country_demonyms = {
                'United States': 'American',
                'United Kingdom': 'British',
                'England': 'English',
                'Germany': 'German',
                'Sweden': 'Swedish',
                'Norway': 'Norwegian',
                'Finland': 'Finnish',
                'Brazil': 'Brazilian',
                'Canada': 'Canadian',
                'Japan': 'Japanese'
            }
            demonym = country_demonyms.get(origin_country, origin_country)
            variations.extend([
                f"{band_name} ({demonym} band)",
                f"{band_name} ({origin_country} band)"
            ])
        
        # Try each variation
        for variant in variations:
            page = self._get_page(variant)
            if page and page.exists():
                enriched['wikipedia_found'] = True
                enriched['wikipedia_title'] = page.title
                enriched['wikipedia_url'] = page.fullurl
                enriched['summary'] = page.summary[:500] if page.summary else None
                
                # Extract categories
                categories = [cat.replace('Category:', '') for cat in page.categories.keys()]
                enriched['categories'] = categories[:10]  # Limit to 10 categories
                
                # Check if it's actually a metal band
                metal_keywords = ['metal', 'rock', 'band', 'music']
                is_metal = any(keyword in cat.lower() for cat in categories for keyword in metal_keywords)
                enriched['confidence_is_metal'] = 1.0 if is_metal else 0.3
                
                # Extract additional info from text
                text_lower = page.text[:1000].lower() if page.text else ""
                
                # Try to find formation year
                import re
                year_patterns = [
                    r'formed in (\d{4})',
                    r'founded in (\d{4})',
                    r'established in (\d{4})',
                    r'(\d{4})[\s\-–—]+present',
                    r'(\d{4})[\s\-–—]+\d{4}'
                ]
                for pattern in year_patterns:
                    match = re.search(pattern, text_lower)
                    if match:
                        enriched['formation_year_wikipedia'] = int(match.group(1))
                        break
                
                # Extract links to related bands
                links = list(page.links.keys())[:20]  # First 20 links
                enriched['related_entities'] = [
                    link for link in links 
                    if any(word in link.lower() for word in ['band', 'album', 'metal', 'rock'])
                ][:10]
                
                logger.info(f"Found Wikipedia page for {band_name}: {page.title}")
                break
        
        if not enriched['wikipedia_found']:
            logger.debug(f"No Wikipedia page found for {band_name}")
        
        return enriched
    
    def enrich_person(self, person_name: str, band_context: Optional[str] = None) -> Dict[str, Any]:
        """
        Enrich person data with Wikipedia information
        
        Args:
            person_name: Name of the person
            band_context: Associated band name for disambiguation
            
        Returns:
            Dictionary with enriched data
        """
        enriched = {
            'wikipedia_found': False,
            'enrichment_source': 'wikipedia'
        }
        
        # Try variations
        variations = [person_name]
        if band_context:
            variations.extend([
                f"{person_name} ({band_context})",
                f"{person_name} (musician)"
            ])
        
        for variant in variations:
            page = self._get_page(variant)
            if page and page.exists():
                enriched['wikipedia_found'] = True
                enriched['wikipedia_title'] = page.title
                enriched['wikipedia_url'] = page.fullurl
                enriched['summary'] = page.summary[:500] if page.summary else None
                
                # Extract birth/death info
                text_lower = page.text[:1000].lower() if page.text else ""
                
                import re
                # Birth year
                birth_match = re.search(r'born[^0-9]*(\d{4})', text_lower)
                if birth_match:
                    enriched['birth_year'] = int(birth_match.group(1))
                
                # Death year
                death_match = re.search(r'died[^0-9]*(\d{4})', text_lower)
                if death_match:
                    enriched['death_year'] = int(death_match.group(1))
                
                # Categories
                categories = [cat.replace('Category:', '') for cat in page.categories.keys()]
                enriched['categories'] = categories[:10]
                
                # Check if musician
                musician_keywords = ['musician', 'guitarist', 'bassist', 'drummer', 'vocalist', 'singer']
                is_musician = any(keyword in cat.lower() for cat in categories for keyword in musician_keywords)
                enriched['confidence_is_musician'] = 1.0 if is_musician else 0.3
                
                logger.info(f"Found Wikipedia page for {person_name}: {page.title}")
                break
        
        return enriched
    
    def enrich_album(self, album_title: str, artist: Optional[str] = None) -> Dict[str, Any]:
        """
        Enrich album data with Wikipedia information
        
        Args:
            album_title: Title of the album
            artist: Artist name for disambiguation
            
        Returns:
            Dictionary with enriched data
        """
        enriched = {
            'wikipedia_found': False,
            'enrichment_source': 'wikipedia'
        }
        
        # Try variations
        variations = [album_title]
        if artist:
            variations.extend([
                f"{album_title} ({artist} album)",
                f"{album_title} (album)"
            ])
        
        for variant in variations:
            page = self._get_page(variant)
            if page and page.exists():
                enriched['wikipedia_found'] = True
                enriched['wikipedia_title'] = page.title
                enriched['wikipedia_url'] = page.fullurl
                enriched['summary'] = page.summary[:500] if page.summary else None
                
                # Extract release info
                text_lower = page.text[:1000].lower() if page.text else ""
                
                import re
                # Release date
                release_patterns = [
                    r'released[^0-9]*(\d{1,2})[^0-9]*(\w+)[^0-9]*(\d{4})',
                    r'released[^0-9]*(\d{4})'
                ]
                for pattern in release_patterns:
                    match = re.search(pattern, text_lower)
                    if match:
                        if len(match.groups()) == 3:
                            enriched['release_date_full'] = f"{match.group(1)} {match.group(2)} {match.group(3)}"
                        else:
                            enriched['release_year_wikipedia'] = int(match.group(1))
                        break
                
                # Categories
                categories = [cat.replace('Category:', '') for cat in page.categories.keys()]
                enriched['categories'] = categories[:10]
                
                # Track listing (if in a recognizable format)
                if 'track listing' in text_lower:
                    enriched['has_track_listing'] = True
                
                logger.info(f"Found Wikipedia page for {album_title}: {page.title}")
                break
        
        return enriched
    
    def enrich_batch(self, entities: Dict[str, List[Dict]], output_path: str) -> Dict[str, Any]:
        """
        Enrich a batch of entities
        
        Args:
            entities: Dictionary of entity type to list of entity dictionaries
            output_path: Path to save enriched data
            
        Returns:
            Enrichment statistics
        """
        stats = {
            'total_processed': 0,
            'enriched': 0,
            'failed': 0,
            'by_type': {}
        }
        
        enriched_data = {'entities': {}}
        
        # Process bands
        if 'bands' in entities:
            enriched_bands = []
            for band in entities['bands']:
                stats['total_processed'] += 1
                enrichment = self.enrich_band(
                    band.get('name', ''),
                    band.get('origin_country')
                )
                
                # Merge enrichment with original data
                enriched_band = {**band, 'wikipedia_enrichment': enrichment}
                enriched_bands.append(enriched_band)
                
                if enrichment['wikipedia_found']:
                    stats['enriched'] += 1
                else:
                    stats['failed'] += 1
            
            enriched_data['entities']['bands'] = enriched_bands
            stats['by_type']['bands'] = {
                'processed': len(entities['bands']),
                'enriched': sum(1 for b in enriched_bands if b['wikipedia_enrichment']['wikipedia_found'])
            }
        
        # Process people
        if 'people' in entities:
            enriched_people = []
            for person in entities['people']:
                stats['total_processed'] += 1
                
                # Use first associated band as context
                band_context = person.get('associated_bands', [None])[0]
                enrichment = self.enrich_person(
                    person.get('name', ''),
                    band_context
                )
                
                enriched_person = {**person, 'wikipedia_enrichment': enrichment}
                enriched_people.append(enriched_person)
                
                if enrichment['wikipedia_found']:
                    stats['enriched'] += 1
                else:
                    stats['failed'] += 1
            
            enriched_data['entities']['people'] = enriched_people
            stats['by_type']['people'] = {
                'processed': len(entities['people']),
                'enriched': sum(1 for p in enriched_people if p['wikipedia_enrichment']['wikipedia_found'])
            }
        
        # Process albums
        if 'albums' in entities:
            enriched_albums = []
            for album in entities['albums']:
                stats['total_processed'] += 1
                enrichment = self.enrich_album(
                    album.get('title', ''),
                    album.get('artist')
                )
                
                enriched_album = {**album, 'wikipedia_enrichment': enrichment}
                enriched_albums.append(enriched_album)
                
                if enrichment['wikipedia_found']:
                    stats['enriched'] += 1
                else:
                    stats['failed'] += 1
            
            enriched_data['entities']['albums'] = enriched_albums
            stats['by_type']['albums'] = {
                'processed': len(entities['albums']),
                'enriched': sum(1 for a in enriched_albums if a['wikipedia_enrichment']['wikipedia_found'])
            }
        
        # Add metadata
        enriched_data['enrichment_metadata'] = {
            'source': 'wikipedia',
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'statistics': stats
        }
        
        # Save enriched data
        with open(output_path, 'w') as f:
            json.dump(enriched_data, f, indent=2)
        
        logger.info(f"Enrichment complete. Stats: {stats}")
        logger.info(f"Saved enriched data to {output_path}")
        
        return stats


def main():
    """Test the Wikipedia enricher"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Enrich metal entities with Wikipedia data")
    parser.add_argument('--input', required=True, help='Input JSON file with entities')
    parser.add_argument('--output', required=True, help='Output path for enriched data')
    parser.add_argument('--limit', type=int, help='Limit number of entities to process')
    
    args = parser.parse_args()
    
    # Load entities
    with open(args.input, 'r') as f:
        data = json.load(f)
    
    entities = data.get('entities', data)
    
    # Apply limit if specified
    if args.limit:
        for entity_type in entities:
            entities[entity_type] = entities[entity_type][:args.limit]
    
    # Create enricher and process
    enricher = WikipediaEnricher()
    stats = enricher.enrich_batch(entities, args.output)
    
    # Print summary
    print(f"\nEnrichment Summary:")
    print(f"Total processed: {stats['total_processed']}")
    print(f"Successfully enriched: {stats['enriched']} ({stats['enriched']/stats['total_processed']*100:.1f}%)")
    print(f"Failed: {stats['failed']}")
    print("\nBy entity type:")
    for entity_type, type_stats in stats['by_type'].items():
        print(f"  {entity_type}: {type_stats['enriched']}/{type_stats['processed']} enriched")


if __name__ == "__main__":
    main()