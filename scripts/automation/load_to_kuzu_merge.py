#!/usr/bin/env python3
"""
Load extracted and deduplicated entities into Kuzu graph database using MERGE.
Handles all entity types and relationships with progress tracking.
MERGE ensures no duplicates - updates existing records or creates new ones.
"""

import json
import kuzu
import argparse
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
from tqdm import tqdm
import sys

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.append(str(PROJECT_ROOT))

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('kuzu_loading.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class KuzuMergeLoader:
    """Loads entities and relationships into Kuzu database using MERGE."""
    
    def __init__(self, db_path: str = "metal_history.db"):
        self.db_path = Path(db_path)
        self.db = None
        self.conn = None
        self.stats = {
            'nodes_merged': {},
            'nodes_updated': {},
            'relationships_merged': {},
            'errors': [],
            'start_time': datetime.now()
        }
    
    def connect(self):
        """Connect to Kuzu database."""
        try:
            self.db = kuzu.Database(str(self.db_path))
            self.conn = kuzu.Connection(self.db)
            logger.info(f"Connected to Kuzu database: {self.db_path}")
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            raise
    
    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
        logger.info("Database connection closed")
    
    def _get_existing_id(self, entity_type: str, name: str) -> Optional[int]:
        """Get existing ID for an entity by name."""
        table_map = {
            'band': 'Band',
            'person': 'Person',
            'location': 'GeographicLocation',
            'subgenre': 'Subgenre',
            'album': 'Album',
            'song': 'Song',
            'venue': 'Venue',
            'event': 'Event',
            'movement': 'Movement'
        }
        
        table = table_map.get(entity_type)
        if not table:
            return None
        
        try:
            result = self.conn.execute(f"""
                MATCH (n:{table})
                WHERE n.name = $name
                RETURN n.id
            """, {'name': name})
            
            if result.has_next():
                return result.get_next()[0]
        except:
            pass
        
        return None
    
    def _get_next_id(self, entity_type: str) -> int:
        """Get next available ID for an entity type."""
        table_map = {
            'band': 'Band',
            'person': 'Person',
            'location': 'GeographicLocation',
            'subgenre': 'Subgenre',
            'album': 'Album',
            'song': 'Song',
            'venue': 'Venue',
            'event': 'Event',
            'movement': 'Movement'
        }
        
        table = table_map.get(entity_type)
        if not table:
            return 1
        
        try:
            result = self.conn.execute(f"""
                MATCH (n:{table})
                RETURN max(n.id) AS max_id
            """)
            
            if result.has_next():
                max_id = result.get_next()[0]
                return (max_id + 1) if max_id else 1
        except:
            return 1
        
        return 1
    
    def load_entities_from_file(self, entities_file: str, batch_size: int = 100):
        """Load all entities from a JSON file into Kuzu."""
        logger.info(f"Loading entities from {entities_file}")
        
        with open(entities_file, 'r') as f:
            data = json.load(f)
        
        entities = data.get('entities', {})
        
        # Connect to database
        self.connect()
        
        try:
            # Load nodes first
            self._merge_bands(entities.get('bands', []), batch_size)
            self._merge_people(entities.get('people', []), batch_size)
            self._merge_locations(entities.get('locations', []), batch_size)
            self._merge_subgenres(entities.get('subgenres', []), batch_size)
            self._merge_albums(entities.get('albums', []), batch_size)
            self._merge_songs(entities.get('songs', []), batch_size)
            self._merge_venues(entities.get('venues', []), batch_size)
            self._merge_events(entities.get('events', []), batch_size)
            self._merge_movements(entities.get('movements', []), batch_size)
            
            # Load relationships
            self._merge_relationships(entities)
            
            # Print summary
            self._print_summary()
            
        finally:
            self.close()
    
    def _merge_bands(self, bands: List[Dict], batch_size: int):
        """Merge band nodes."""
        logger.info(f"Merging {len(bands)} bands...")
        
        for band in tqdm(bands, desc="Merging bands"):
            try:
                # Parse location into city and country
                origin_location = band.get('origin_location', '')
                origin_city = ''
                origin_country = ''
                if origin_location:
                    parts = origin_location.split(',')
                    origin_city = parts[0].strip() if parts else ''
                    origin_country = parts[1].strip() if len(parts) > 1 else ''
                
                # Check if band exists
                existing_id = self._get_existing_id('band', band['name'])
                
                # Prepare parameters matching schema
                params = {
                    'name': band['name'],
                    'formed_year': band.get('formed_year'),
                    'origin_city': origin_city,
                    'origin_country': origin_country,
                    'status': 'active' if band.get('active', True) else 'disbanded',
                    'description': band.get('description', ''),
                    'embedding': band.get('embedding', [0.0] * 1024)
                }
                
                if existing_id:
                    # Update existing band
                    params['id'] = existing_id
                    self.conn.execute("""
                        MATCH (b:Band {id: $id})
                        SET b.formed_year = $formed_year,
                            b.origin_city = $origin_city,
                            b.origin_country = $origin_country,
                            b.status = $status,
                            b.description = $description,
                            b.embedding = $embedding
                    """, params)
                    self.stats['nodes_updated']['bands'] = self.stats['nodes_updated'].get('bands', 0) + 1
                else:
                    # Create new band
                    params['id'] = self._get_next_id('band')
                    self.conn.execute("""
                        CREATE (b:Band {
                            id: $id,
                            name: $name,
                            formed_year: $formed_year,
                            origin_city: $origin_city,
                            origin_country: $origin_country,
                            status: $status,
                            description: $description,
                            embedding: $embedding
                        })
                    """, params)
                    self.stats['nodes_merged']['bands'] = self.stats['nodes_merged'].get('bands', 0) + 1
                
            except Exception as e:
                logger.error(f"Error merging band {band.get('name', 'Unknown')}: {e}")
                self.stats['errors'].append({
                    'entity_type': 'band',
                    'entity': band.get('name'),
                    'error': str(e)
                })
    
    def _merge_people(self, people: List[Dict], batch_size: int):
        """Merge person nodes."""
        logger.info(f"Merging {len(people)} people...")
        
        for person in tqdm(people, desc="Merging people"):
            try:
                # Map roles to instruments if applicable
                roles = person.get('roles', [])
                instruments = []
                for role in roles:
                    if role in ['guitarist', 'bassist', 'drummer', 'vocalist', 'keyboardist']:
                        instruments.append(role.replace('ist', ''))
                
                # Check if person exists
                existing_id = self._get_existing_id('person', person['name'])
                
                params = {
                    'name': person['name'],
                    'birth_year': person.get('birth_year'),
                    'death_year': person.get('death_year'),
                    'nationality': person.get('nationality'),
                    'instruments': instruments,
                    'description': person.get('known_for', ''),
                    'embedding': person.get('embedding', [0.0] * 1024)
                }
                
                if existing_id:
                    # Update existing person
                    params['id'] = existing_id
                    self.conn.execute("""
                        MATCH (p:Person {id: $id})
                        SET p.birth_year = $birth_year,
                            p.death_year = $death_year,
                            p.nationality = $nationality,
                            p.instruments = $instruments,
                            p.description = $description,
                            p.embedding = $embedding
                    """, params)
                    self.stats['nodes_updated']['people'] = self.stats['nodes_updated'].get('people', 0) + 1
                else:
                    # Create new person
                    params['id'] = self._get_next_id('person')
                    self.conn.execute("""
                        CREATE (p:Person {
                            id: $id,
                            name: $name,
                            birth_year: $birth_year,
                            death_year: $death_year,
                            nationality: $nationality,
                            instruments: $instruments,
                            description: $description,
                            embedding: $embedding
                        })
                    """, params)
                    self.stats['nodes_merged']['people'] = self.stats['nodes_merged'].get('people', 0) + 1
                
            except Exception as e:
                logger.error(f"Error merging person {person.get('name', 'Unknown')}: {e}")
                self.stats['errors'].append({
                    'entity_type': 'person',
                    'entity': person.get('name'),
                    'error': str(e)
                })
    
    def _merge_albums(self, albums: List[Dict], batch_size: int):
        """Merge album nodes."""
        logger.info(f"Merging {len(albums)} albums...")
        
        for album in tqdm(albums, desc="Merging albums"):
            try:
                # Check if album exists
                existing_id = self._get_existing_id('album', album['title'])
                
                params = {
                    'title': album['title'],
                    'release_year': album.get('release_year'),
                    'release_date': album.get('release_date'),  # DATE type, can be null
                    'chart_position': album.get('chart_position'),
                    'label': album.get('label', ''),
                    'producer': album.get('producer', ''),
                    'studio': album.get('studio', ''),
                    'description': album.get('description', ''),
                    'embedding': album.get('embedding', [0.0] * 1024)
                }
                
                if existing_id:
                    # Update existing album
                    params['id'] = existing_id
                    self.conn.execute("""
                        MATCH (a:Album {id: $id})
                        SET a.release_year = $release_year,
                            a.release_date = $release_date,
                            a.chart_position = $chart_position,
                            a.label = $label,
                            a.producer = $producer,
                            a.studio = $studio,
                            a.description = $description,
                            a.embedding = $embedding
                    """, params)
                    self.stats['nodes_updated']['albums'] = self.stats['nodes_updated'].get('albums', 0) + 1
                else:
                    # Create new album
                    params['id'] = self._get_next_id('album')
                    self.conn.execute("""
                        CREATE (a:Album {
                            id: $id,
                            title: $title,
                            release_year: $release_year,
                            release_date: $release_date,
                            chart_position: $chart_position,
                            label: $label,
                            producer: $producer,
                            studio: $studio,
                            description: $description,
                            embedding: $embedding
                        })
                    """, params)
                    self.stats['nodes_merged']['albums'] = self.stats['nodes_merged'].get('albums', 0) + 1
                
            except Exception as e:
                logger.error(f"Error merging album {album.get('title', 'Unknown')}: {e}")
                self.stats['errors'].append({
                    'entity_type': 'album',
                    'entity': album.get('title'),
                    'error': str(e)
                })
    
    def _merge_locations(self, locations: List[Dict], batch_size: int):
        """Merge location nodes."""
        logger.info(f"Merging {len(locations)} locations...")
        
        for location in tqdm(locations, desc="Merging locations"):
            try:
                # Check if location exists
                existing_id = self._get_existing_id('location', location['name'])
                
                params = {
                    'city': location.get('city', location['name']),
                    'region': location.get('region', ''),
                    'country': location.get('country', ''),
                    'scene_description': location.get('scene_description', ''),
                    'cultural_context': location.get('cultural_context', ''),
                    'embedding': location.get('embedding', [0.0] * 1024)
                }
                params['name'] = params['city']  # Use city as name
                
                if existing_id:
                    params['id'] = existing_id
                    self.conn.execute("""
                        MATCH (l:GeographicLocation {id: $id})
                        SET l.region = $region,
                            l.country = $country,
                            l.scene_description = $scene_description,
                            l.cultural_context = $cultural_context,
                            l.embedding = $embedding
                    """, params)
                    self.stats['nodes_updated']['locations'] = self.stats['nodes_updated'].get('locations', 0) + 1
                else:
                    params['id'] = self._get_next_id('location')
                    self.conn.execute("""
                        CREATE (l:GeographicLocation {
                            id: $id,
                            name: $name,
                            city: $city,
                            region: $region,
                            country: $country,
                            scene_description: $scene_description,
                            cultural_context: $cultural_context,
                            embedding: $embedding
                        })
                    """, params)
                    self.stats['nodes_merged']['locations'] = self.stats['nodes_merged'].get('locations', 0) + 1
                
            except Exception as e:
                logger.error(f"Error merging location {location.get('name', 'Unknown')}: {e}")
                self.stats['errors'].append({
                    'entity_type': 'location',
                    'entity': location.get('name'),
                    'error': str(e)
                })
    
    def _merge_subgenres(self, subgenres: List[Dict], batch_size: int):
        """Merge subgenre nodes."""
        logger.info(f"Merging {len(subgenres)} subgenres...")
        
        for subgenre in tqdm(subgenres, desc="Merging subgenres"):
            try:
                # Check if subgenre exists
                existing_id = self._get_existing_id('subgenre', subgenre['name'])
                
                params = {
                    'name': subgenre['name'],
                    'era_start': subgenre.get('era_start'),
                    'era_end': subgenre.get('era_end'),
                    'bpm_min': subgenre.get('bpm_min'),
                    'bpm_max': subgenre.get('bpm_max'),
                    'guitar_tuning': subgenre.get('guitar_tuning', ''),
                    'vocal_style': subgenre.get('vocal_style', ''),
                    'key_characteristics': subgenre.get('key_characteristics', ''),
                    'parent_influences': subgenre.get('parent_influences', []),
                    'legacy_impact': subgenre.get('legacy_impact', ''),
                    'description': subgenre.get('description', ''),
                    'embedding': subgenre.get('embedding', [0.0] * 1024)
                }
                
                if existing_id:
                    params['id'] = existing_id
                    self.conn.execute("""
                        MATCH (s:Subgenre {id: $id})
                        SET s.era_start = $era_start,
                            s.era_end = $era_end,
                            s.bpm_min = $bpm_min,
                            s.bpm_max = $bpm_max,
                            s.guitar_tuning = $guitar_tuning,
                            s.vocal_style = $vocal_style,
                            s.key_characteristics = $key_characteristics,
                            s.parent_influences = $parent_influences,
                            s.legacy_impact = $legacy_impact,
                            s.description = $description,
                            s.embedding = $embedding
                    """, params)
                    self.stats['nodes_updated']['subgenres'] = self.stats['nodes_updated'].get('subgenres', 0) + 1
                else:
                    params['id'] = self._get_next_id('subgenre')
                    self.conn.execute("""
                        CREATE (s:Subgenre {
                            id: $id,
                            name: $name,
                            era_start: $era_start,
                            era_end: $era_end,
                            bpm_min: $bpm_min,
                            bpm_max: $bpm_max,
                            guitar_tuning: $guitar_tuning,
                            vocal_style: $vocal_style,
                            key_characteristics: $key_characteristics,
                            parent_influences: $parent_influences,
                            legacy_impact: $legacy_impact,
                            description: $description,
                            embedding: $embedding
                        })
                    """, params)
                    self.stats['nodes_merged']['subgenres'] = self.stats['nodes_merged'].get('subgenres', 0) + 1
                
            except Exception as e:
                logger.error(f"Error merging subgenre {subgenre.get('name', 'Unknown')}: {e}")
                self.stats['errors'].append({
                    'entity_type': 'subgenre',
                    'entity': subgenre.get('name'),
                    'error': str(e)
                })
    
    def _merge_songs(self, songs: List[Dict], batch_size: int):
        """Merge song nodes."""
        logger.info(f"Merging {len(songs)} songs...")
        
        for song in tqdm(songs, desc="Merging songs"):
            try:
                # Check if song exists
                existing_id = self._get_existing_id('song', song['title'])
                
                params = {
                    'title': song['title'],
                    'duration_seconds': song.get('duration_seconds'),
                    'bpm': song.get('bpm'),
                    'description': song.get('description', ''),
                    'embedding': song.get('embedding', [0.0] * 1024)
                }
                
                if existing_id:
                    params['id'] = existing_id
                    self.conn.execute("""
                        MATCH (s:Song {id: $id})
                        SET s.duration_seconds = $duration_seconds,
                            s.bpm = $bpm,
                            s.description = $description,
                            s.embedding = $embedding
                    """, params)
                    self.stats['nodes_updated']['songs'] = self.stats['nodes_updated'].get('songs', 0) + 1
                else:
                    params['id'] = self._get_next_id('song')
                    self.conn.execute("""
                        CREATE (s:Song {
                            id: $id,
                            title: $title,
                            duration_seconds: $duration_seconds,
                            bpm: $bpm,
                            description: $description,
                            embedding: $embedding
                        })
                    """, params)
                    self.stats['nodes_merged']['songs'] = self.stats['nodes_merged'].get('songs', 0) + 1
                
            except Exception as e:
                logger.error(f"Error merging song {song.get('title', 'Unknown')}: {e}")
                self.stats['errors'].append({
                    'entity_type': 'song',
                    'entity': song.get('title'),
                    'error': str(e)
                })
    
    def _merge_venues(self, venues: List[Dict], batch_size: int):
        """Merge venue nodes."""
        logger.info(f"Merging {len(venues)} venues...")
        
        for venue in tqdm(venues, desc="Merging venues"):
            try:
                # Check if venue exists
                existing_id = self._get_existing_id('venue', venue['name'])
                
                params = {
                    'name': venue['name'],
                    'city': venue.get('city', ''),
                    'country': venue.get('country', ''),
                    'capacity': venue.get('capacity'),
                    'opened_year': venue.get('opened_year'),
                    'closed_year': venue.get('closed_year'),
                    'description': venue.get('description', ''),
                    'embedding': venue.get('embedding', [0.0] * 1024)
                }
                
                if existing_id:
                    params['id'] = existing_id
                    self.conn.execute("""
                        MATCH (v:Venue {id: $id})
                        SET v.city = $city,
                            v.country = $country,
                            v.capacity = $capacity,
                            v.opened_year = $opened_year,
                            v.closed_year = $closed_year,
                            v.description = $description,
                            v.embedding = $embedding
                    """, params)
                    self.stats['nodes_updated']['venues'] = self.stats['nodes_updated'].get('venues', 0) + 1
                else:
                    params['id'] = self._get_next_id('venue')
                    self.conn.execute("""
                        CREATE (v:Venue {
                            id: $id,
                            name: $name,
                            city: $city,
                            country: $country,
                            capacity: $capacity,
                            opened_year: $opened_year,
                            closed_year: $closed_year,
                            description: $description,
                            embedding: $embedding
                        })
                    """, params)
                    self.stats['nodes_merged']['venues'] = self.stats['nodes_merged'].get('venues', 0) + 1
                
            except Exception as e:
                logger.error(f"Error merging venue {venue.get('name', 'Unknown')}: {e}")
                self.stats['errors'].append({
                    'entity_type': 'venue',
                    'entity': venue.get('name'),
                    'error': str(e)
                })
    
    def _merge_events(self, events: List[Dict], batch_size: int):
        """Merge event nodes."""
        logger.info(f"Merging {len(events)} events...")
        
        for event in tqdm(events, desc="Merging events"):
            try:
                # Check if event exists
                existing_id = self._get_existing_id('event', event['name'])
                
                params = {
                    'name': event['name'],
                    'year': event.get('year'),
                    'location': event.get('location', ''),
                    'event_type': event.get('event_type', ''),
                    'description': event.get('description', ''),
                    'impact': event.get('impact', ''),
                    'participants': event.get('participants', []),
                    'embedding': event.get('embedding', [0.0] * 1024)
                }
                
                if existing_id:
                    params['id'] = existing_id
                    self.conn.execute("""
                        MATCH (e:Event {id: $id})
                        SET e.year = $year,
                            e.location = $location,
                            e.event_type = $event_type,
                            e.description = $description,
                            e.impact = $impact,
                            e.participants = $participants,
                            e.embedding = $embedding
                    """, params)
                    self.stats['nodes_updated']['events'] = self.stats['nodes_updated'].get('events', 0) + 1
                else:
                    params['id'] = self._get_next_id('event')
                    self.conn.execute("""
                        CREATE (e:Event {
                            id: $id,
                            name: $name,
                            year: $year,
                            location: $location,
                            event_type: $event_type,
                            description: $description,
                            impact: $impact,
                            participants: $participants,
                            embedding: $embedding
                        })
                    """, params)
                    self.stats['nodes_merged']['events'] = self.stats['nodes_merged'].get('events', 0) + 1
                
            except Exception as e:
                logger.error(f"Error merging event {event.get('name', 'Unknown')}: {e}")
                self.stats['errors'].append({
                    'entity_type': 'event',
                    'entity': event.get('name'),
                    'error': str(e)
                })
    
    def _merge_movements(self, movements: List[Dict], batch_size: int):
        """Merge movement nodes."""
        logger.info(f"Merging {len(movements)} movements...")
        
        for movement in tqdm(movements, desc="Merging movements"):
            try:
                # Check if movement exists
                existing_id = self._get_existing_id('movement', movement['name'])
                
                params = {
                    'name': movement['name'],
                    'start_year': movement.get('start_year'),
                    'end_year': movement.get('end_year'),
                    'description': movement.get('description', ''),
                    'key_bands': movement.get('key_bands', []),
                    'key_locations': movement.get('key_locations', []),
                    'characteristics': movement.get('characteristics', []),
                    'embedding': movement.get('embedding', [0.0] * 1024)
                }
                
                if existing_id:
                    params['id'] = existing_id
                    self.conn.execute("""
                        MATCH (m:Movement {id: $id})
                        SET m.start_year = $start_year,
                            m.end_year = $end_year,
                            m.description = $description,
                            m.key_bands = $key_bands,
                            m.key_locations = $key_locations,
                            m.characteristics = $characteristics,
                            m.embedding = $embedding
                    """, params)
                    self.stats['nodes_updated']['movements'] = self.stats['nodes_updated'].get('movements', 0) + 1
                else:
                    params['id'] = self._get_next_id('movement')
                    self.conn.execute("""
                        CREATE (m:Movement {
                            id: $id,
                            name: $name,
                            start_year: $start_year,
                            end_year: $end_year,
                            description: $description,
                            key_bands: $key_bands,
                            key_locations: $key_locations,
                            characteristics: $characteristics,
                            embedding: $embedding
                        })
                    """, params)
                    self.stats['nodes_merged']['movements'] = self.stats['nodes_merged'].get('movements', 0) + 1
                
            except Exception as e:
                logger.error(f"Error merging movement {movement.get('name', 'Unknown')}: {e}")
                self.stats['errors'].append({
                    'entity_type': 'movement',
                    'entity': movement.get('name'),
                    'error': str(e)
                })
    
    def _merge_relationships(self, entities: Dict):
        """Merge relationships between entities."""
        logger.info("Merging relationships...")
        
        # Band -> Album relationships
        for album in entities.get('albums', []):
            if 'band_name' in album:
                try:
                    # Check if relationship exists
                    result = self.conn.execute("""
                        MATCH (b:Band)-[r:RELEASED]->(a:Album)
                        WHERE b.name = $band_name AND a.title = $album_title
                        RETURN count(r) as count
                    """, {
                        'band_name': album['band_name'],
                        'album_title': album['title']
                    })
                    
                    if result.has_next() and result.get_next()[0] == 0:
                        # Create relationship if it doesn't exist
                        self.conn.execute("""
                            MATCH (b:Band), (a:Album)
                            WHERE b.name = $band_name AND a.title = $album_title
                            CREATE (b)-[r:RELEASED]->(a)
                        """, {
                            'band_name': album['band_name'],
                            'album_title': album['title']
                        })
                        self.stats['relationships_merged']['band_album'] = \
                            self.stats['relationships_merged'].get('band_album', 0) + 1
                except Exception as e:
                    logger.debug(f"Could not create RELEASED relationship: {e}")
        
        # Band -> Location relationships
        for band in entities.get('bands', []):
            if 'origin_location' in band:
                location = band['origin_location'].split(',')[0].strip()
                try:
                    # Check if relationship exists
                    result = self.conn.execute("""
                        MATCH (b:Band)-[r:FORMED_IN]->(l:GeographicLocation)
                        WHERE b.name = $band_name AND l.city = $location
                        RETURN count(r) as count
                    """, {
                        'band_name': band['name'],
                        'location': location
                    })
                    
                    if result.has_next() and result.get_next()[0] == 0:
                        # Create relationship if it doesn't exist
                        self.conn.execute("""
                            MATCH (b:Band), (l:GeographicLocation)
                            WHERE b.name = $band_name AND l.city = $location
                            CREATE (b)-[r:FORMED_IN]->(l)
                        """, {
                            'band_name': band['name'],
                            'location': location
                        })
                        self.stats['relationships_merged']['band_location'] = \
                            self.stats['relationships_merged'].get('band_location', 0) + 1
                except Exception as e:
                    logger.debug(f"Could not create FORMED_IN relationship: {e}")
        
        # Band -> Subgenre relationships
        for band in entities.get('bands', []):
            for genre in band.get('genres', []):
                try:
                    # Check if relationship exists
                    result = self.conn.execute("""
                        MATCH (b:Band)-[r:PLAYS_GENRE]->(s:Subgenre)
                        WHERE b.name = $band_name AND s.name = $genre_name
                        RETURN count(r) as count
                    """, {
                        'band_name': band['name'],
                        'genre_name': genre
                    })
                    
                    if result.has_next() and result.get_next()[0] == 0:
                        # Create relationship if it doesn't exist
                        self.conn.execute("""
                            MATCH (b:Band), (s:Subgenre)
                            WHERE b.name = $band_name AND s.name = $genre_name
                            CREATE (b)-[r:PLAYS_GENRE]->(s)
                        """, {
                            'band_name': band['name'],
                            'genre_name': genre
                        })
                        self.stats['relationships_merged']['band_genre'] = \
                            self.stats['relationships_merged'].get('band_genre', 0) + 1
                except Exception as e:
                    logger.debug(f"Could not create PLAYS_GENRE relationship: {e}")
    
    def _print_summary(self):
        """Print loading summary."""
        duration = (datetime.now() - self.stats['start_time']).total_seconds()
        
        print("\n" + "="*50)
        print("KUZU MERGE LOADING SUMMARY")
        print("="*50)
        
        print("\nNodes Created:")
        for node_type, count in self.stats['nodes_merged'].items():
            print(f"  {node_type}: {count}")
        
        print("\nNodes Updated:")
        for node_type, count in self.stats['nodes_updated'].items():
            print(f"  {node_type}: {count}")
        
        print("\nRelationships Created:")
        for rel_type, count in self.stats['relationships_merged'].items():
            print(f"  {rel_type}: {count}")
        
        if self.stats['errors']:
            print(f"\nErrors: {len(self.stats['errors'])}")
            for error in self.stats['errors'][:5]:  # Show first 5 errors
                print(f"  - {error['entity_type']}: {error['entity']} - {error['error']}")
            if len(self.stats['errors']) > 5:
                print(f"  ... and {len(self.stats['errors']) - 5} more errors")
        
        print(f"\nTotal time: {duration:.2f} seconds")
        print("="*50)


def main():
    parser = argparse.ArgumentParser(description="Load entities into Kuzu database using MERGE")
    parser.add_argument('entities_file', type=str,
                       help='Path to deduplicated entities JSON file')
    parser.add_argument('--db-path', type=str, default='metal_history.db',
                       help='Path to Kuzu database')
    parser.add_argument('--batch-size', type=int, default=100,
                       help='Batch size for loading')
    parser.add_argument('--verify', action='store_true',
                       help='Verify loaded entities after loading')
    
    args = parser.parse_args()
    
    # Check if database exists
    db_path = Path(args.db_path)
    
    # If it's just a filename, check in schema directory too
    if not db_path.exists() and not db_path.is_absolute():
        schema_db_path = Path('schema') / db_path
        if schema_db_path.exists():
            db_path = schema_db_path
            logger.info(f"Found database at {db_path}")
    
    if not db_path.exists():
        logger.error(f"Database not found at {db_path}")
        logger.info("Run 'python schema/initialize_kuzu.py' to create database first")
        return 1
    
    # Check if entities file exists
    entities_path = Path(args.entities_file)
    if not entities_path.exists():
        logger.error(f"Entities file not found: {entities_path}")
        return 1
    
    # Load entities
    loader = KuzuMergeLoader(str(db_path))
    try:
        loader.load_entities_from_file(str(entities_path), args.batch_size)
        
        if args.verify:
            print("\nVerifying loaded data...")
            loader.connect()
            
            # Count nodes
            for table in ['Band', 'Person', 'Album', 'Song', 'Subgenre']:
                result = loader.conn.execute(f"MATCH (n:{table}) RETURN count(n)")
                if result.has_next():
                    count = result.get_next()[0]
                    print(f"{table}: {count} nodes")
            
            loader.close()
        
        return 0
        
    except Exception as e:
        logger.error(f"Loading failed: {e}")
        return 1


if __name__ == "__main__":
    exit(main())