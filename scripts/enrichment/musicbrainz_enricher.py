#!/usr/bin/env python3
"""
MusicBrainz enrichment for metal history entities
Fetches discography and additional metadata from MusicBrainz
"""

import json
import time
import logging
from typing import Dict, List, Any, Optional
from pathlib import Path
import sys
from datetime import datetime

# Try to import musicbrainzngs, provide instructions if not available
try:
    import musicbrainzngs
except ImportError:
    print("musicbrainzngs not installed. Install with: pip install musicbrainzngs")
    sys.exit(1)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MusicBrainzEnricher:
    """Enrich entities with MusicBrainz data"""
    
    def __init__(self, app_name: str = "MetalHistoryKG", 
                 app_version: str = "1.0",
                 contact: str = "https://github.com/metal-history-kg"):
        """Initialize MusicBrainz client"""
        musicbrainzngs.set_useragent(app_name, app_version, contact)
        self.rate_limit_delay = 1.0  # MusicBrainz requires 1 request per second
        self.last_request_time = 0
        self.cache = {}
        
    def _rate_limit(self):
        """Enforce rate limiting between requests"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.rate_limit_delay:
            time.sleep(self.rate_limit_delay - time_since_last)
        self.last_request_time = time.time()
    
    def search_artist(self, artist_name: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Search for an artist in MusicBrainz
        
        Args:
            artist_name: Name of the artist/band
            limit: Maximum number of results
            
        Returns:
            List of matching artists with metadata
        """
        cache_key = f"artist_search:{artist_name}:{limit}"
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        self._rate_limit()
        
        try:
            result = musicbrainzngs.search_artists(
                artist=artist_name,
                limit=limit
            )
            
            artists = []
            for artist in result.get('artist-list', []):
                artist_data = {
                    'mbid': artist.get('id'),
                    'name': artist.get('name'),
                    'sort_name': artist.get('sort-name'),
                    'disambiguation': artist.get('disambiguation', ''),
                    'type': artist.get('type', ''),
                    'score': artist.get('ext:score', 0),
                    'country': artist.get('country', ''),
                    'area': artist.get('area', {}).get('name', '') if 'area' in artist else '',
                    'life_span': {
                        'begin': artist.get('life-span', {}).get('begin', ''),
                        'end': artist.get('life-span', {}).get('end', ''),
                        'ended': artist.get('life-span', {}).get('ended', False)
                    },
                    'tags': [tag.get('name') for tag in artist.get('tag-list', [])][:5]
                }
                artists.append(artist_data)
            
            self.cache[cache_key] = artists
            return artists
            
        except Exception as e:
            logger.error(f"Error searching for artist {artist_name}: {e}")
            return []
    
    def get_artist_details(self, mbid: str) -> Dict[str, Any]:
        """
        Get detailed information about an artist
        
        Args:
            mbid: MusicBrainz ID of the artist
            
        Returns:
            Detailed artist information
        """
        cache_key = f"artist_details:{mbid}"
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        self._rate_limit()
        
        try:
            result = musicbrainzngs.get_artist_by_id(
                mbid,
                includes=['aliases', 'tags', 'ratings', 'artist-rels', 'url-rels']
            )
            
            artist = result.get('artist', {})
            details = {
                'mbid': artist.get('id'),
                'name': artist.get('name'),
                'sort_name': artist.get('sort-name'),
                'disambiguation': artist.get('disambiguation', ''),
                'type': artist.get('type', ''),
                'country': artist.get('country', ''),
                'area': artist.get('area', {}).get('name', '') if 'area' in artist else '',
                'life_span': artist.get('life-span', {}),
                'aliases': [
                    {
                        'name': alias.get('name'),
                        'sort_name': alias.get('sort-name'),
                        'type': alias.get('type'),
                        'primary': alias.get('primary', False)
                    }
                    for alias in artist.get('alias-list', [])
                ],
                'tags': [
                    {
                        'name': tag.get('name'),
                        'count': tag.get('count', 0)
                    }
                    for tag in artist.get('tag-list', [])
                ],
                'rating': {
                    'value': artist.get('rating', {}).get('value'),
                    'votes': artist.get('rating', {}).get('votes-count', 0)
                },
                'external_urls': [
                    {
                        'type': url.get('type'),
                        'url': url.get('target')
                    }
                    for url in artist.get('url-relation-list', [])
                ]
            }
            
            # Extract member relationships
            members = []
            for rel in artist.get('artist-relation-list', []):
                if rel.get('type') == 'member of band':
                    member_info = {
                        'name': rel.get('artist', {}).get('name'),
                        'mbid': rel.get('artist', {}).get('id'),
                        'begin': rel.get('begin', ''),
                        'end': rel.get('end', ''),
                        'ended': rel.get('ended', False)
                    }
                    members.append(member_info)
            
            if members:
                details['members'] = members
            
            self.cache[cache_key] = details
            return details
            
        except Exception as e:
            logger.error(f"Error getting artist details for {mbid}: {e}")
            return {}
    
    def get_artist_releases(self, mbid: str, release_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get releases for an artist
        
        Args:
            mbid: MusicBrainz ID of the artist
            release_type: Filter by type (album, single, ep, etc.)
            
        Returns:
            List of releases
        """
        cache_key = f"artist_releases:{mbid}:{release_type}"
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        self._rate_limit()
        
        try:
            # Get release groups (albums, EPs, etc.)
            result = musicbrainzngs.browse_release_groups(
                artist=mbid,
                release_type=release_type.split('|') if release_type else None,
                limit=100
            )
            
            releases = []
            for rg in result.get('release-group-list', []):
                release_data = {
                    'mbid': rg.get('id'),
                    'title': rg.get('title'),
                    'type': rg.get('type', ''),
                    'primary_type': rg.get('primary-type', ''),
                    'secondary_types': rg.get('secondary-type-list', []),
                    'first_release_date': rg.get('first-release-date', ''),
                    'disambiguation': rg.get('disambiguation', '')
                }
                releases.append(release_data)
            
            # Sort by release date
            releases.sort(key=lambda x: x.get('first_release_date', ''))
            
            self.cache[cache_key] = releases
            return releases
            
        except Exception as e:
            logger.error(f"Error getting releases for artist {mbid}: {e}")
            return []
    
    def enrich_band(self, band_name: str, formed_year: Optional[int] = None,
                    origin_country: Optional[str] = None) -> Dict[str, Any]:
        """
        Enrich band data with MusicBrainz information
        
        Args:
            band_name: Name of the band
            formed_year: Year band was formed (helps disambiguation)
            origin_country: Country of origin (helps disambiguation)
            
        Returns:
            Dictionary with enriched data
        """
        enriched = {
            'musicbrainz_found': False,
            'enrichment_source': 'musicbrainz'
        }
        
        # Search for artist
        search_results = self.search_artist(band_name, limit=5)
        
        if not search_results:
            logger.debug(f"No MusicBrainz results for {band_name}")
            return enriched
        
        # Find best match
        best_match = None
        best_score = 0
        
        for artist in search_results:
            score = artist.get('score', 0)
            
            # Boost score for matching metadata
            if origin_country and artist.get('country') == origin_country:
                score += 10
            if formed_year and artist.get('life_span', {}).get('begin', '').startswith(str(formed_year)):
                score += 10
            
            # Check for metal-related tags
            metal_tags = ['metal', 'heavy metal', 'thrash', 'death metal', 'black metal', 
                         'doom metal', 'power metal', 'progressive metal']
            if any(tag in metal_tags for tag in artist.get('tags', [])):
                score += 20
            
            if score > best_score:
                best_score = score
                best_match = artist
        
        if not best_match:
            return enriched
        
        # Get detailed information
        details = self.get_artist_details(best_match['mbid'])
        
        if details:
            enriched['musicbrainz_found'] = True
            enriched['mbid'] = details['mbid']
            enriched['name'] = details['name']
            enriched['disambiguation'] = details.get('disambiguation', '')
            enriched['type'] = details.get('type', '')
            enriched['country'] = details.get('country', '')
            enriched['area'] = details.get('area', '')
            enriched['life_span'] = details.get('life_span', {})
            enriched['aliases'] = details.get('aliases', [])
            enriched['tags'] = details.get('tags', [])
            enriched['rating'] = details.get('rating', {})
            enriched['members'] = details.get('members', [])
            enriched['match_confidence'] = best_score / 100.0
            
            # Get discography summary
            albums = self.get_artist_releases(best_match['mbid'], 'album')
            eps = self.get_artist_releases(best_match['mbid'], 'ep')
            
            enriched['discography_summary'] = {
                'album_count': len(albums),
                'ep_count': len(eps),
                'first_release': albums[0]['first_release_date'] if albums else None,
                'latest_release': albums[-1]['first_release_date'] if albums else None,
                'albums': albums[:10],  # First 10 albums
                'eps': eps[:5]  # First 5 EPs
            }
            
            # Extract useful URLs
            useful_urls = {}
            for url in details.get('external_urls', []):
                url_type = url.get('type', '').lower()
                if url_type in ['official homepage', 'wikipedia', 'discogs', 'bandcamp', 
                               'spotify', 'youtube', 'soundcloud']:
                    useful_urls[url_type] = url.get('url')
            enriched['external_urls'] = useful_urls
            
            logger.info(f"Found MusicBrainz data for {band_name}: {details['name']}")
        
        return enriched
    
    def enrich_album(self, album_title: str, artist_name: Optional[str] = None,
                    release_year: Optional[int] = None) -> Dict[str, Any]:
        """
        Enrich album data with MusicBrainz information
        
        Args:
            album_title: Title of the album
            artist_name: Artist name
            release_year: Year of release
            
        Returns:
            Dictionary with enriched data
        """
        enriched = {
            'musicbrainz_found': False,
            'enrichment_source': 'musicbrainz'
        }
        
        self._rate_limit()
        
        try:
            # Search for release
            search_params = {'release': album_title}
            if artist_name:
                search_params['artist'] = artist_name
            if release_year:
                search_params['date'] = str(release_year)
            
            result = musicbrainzngs.search_releases(**search_params, limit=5)
            
            releases = result.get('release-list', [])
            if not releases:
                return enriched
            
            # Find best match
            best_match = releases[0]  # Simple: take highest scored result
            
            enriched['musicbrainz_found'] = True
            enriched['mbid'] = best_match.get('id')
            enriched['title'] = best_match.get('title')
            enriched['artist'] = best_match.get('artist-credit-phrase', '')
            enriched['date'] = best_match.get('date', '')
            enriched['country'] = best_match.get('country', '')
            enriched['status'] = best_match.get('status', '')
            enriched['label'] = best_match.get('label-info-list', [{}])[0].get('label', {}).get('name', '') if best_match.get('label-info-list') else ''
            enriched['barcode'] = best_match.get('barcode', '')
            enriched['track_count'] = best_match.get('medium-list', [{}])[0].get('track-count', 0) if best_match.get('medium-list') else 0
            
            logger.info(f"Found MusicBrainz data for album {album_title}")
            
        except Exception as e:
            logger.error(f"Error enriching album {album_title}: {e}")
        
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
                    band.get('formed_year'),
                    band.get('origin_country')
                )
                
                # Merge enrichment with original data
                enriched_band = {**band, 'musicbrainz_enrichment': enrichment}
                enriched_bands.append(enriched_band)
                
                if enrichment['musicbrainz_found']:
                    stats['enriched'] += 1
                else:
                    stats['failed'] += 1
            
            enriched_data['entities']['bands'] = enriched_bands
            stats['by_type']['bands'] = {
                'processed': len(entities['bands']),
                'enriched': sum(1 for b in enriched_bands if b['musicbrainz_enrichment']['musicbrainz_found'])
            }
        
        # Process albums
        if 'albums' in entities:
            enriched_albums = []
            for album in entities['albums']:
                stats['total_processed'] += 1
                enrichment = self.enrich_album(
                    album.get('title', ''),
                    album.get('artist'),
                    album.get('release_year')
                )
                
                enriched_album = {**album, 'musicbrainz_enrichment': enrichment}
                enriched_albums.append(enriched_album)
                
                if enrichment['musicbrainz_found']:
                    stats['enriched'] += 1
                else:
                    stats['failed'] += 1
            
            enriched_data['entities']['albums'] = enriched_albums
            stats['by_type']['albums'] = {
                'processed': len(entities['albums']),
                'enriched': sum(1 for a in enriched_albums if a['musicbrainz_enrichment']['musicbrainz_found'])
            }
        
        # Add metadata
        enriched_data['enrichment_metadata'] = {
            'source': 'musicbrainz',
            'timestamp': datetime.now().isoformat(),
            'statistics': stats
        }
        
        # Save enriched data
        with open(output_path, 'w') as f:
            json.dump(enriched_data, f, indent=2)
        
        logger.info(f"Enrichment complete. Stats: {stats}")
        logger.info(f"Saved enriched data to {output_path}")
        
        return stats


def main():
    """Test the MusicBrainz enricher"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Enrich metal entities with MusicBrainz data")
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
    enricher = MusicBrainzEnricher()
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