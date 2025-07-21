#!/usr/bin/env python3
"""
Load extracted and deduplicated entities into Kuzu graph database.
Handles all entity types and relationships with progress tracking.
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
        logging.FileHandler('logs/kuzu_loading.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class KuzuLoader:
    """Loads entities and relationships into Kuzu database."""
    
    def __init__(self, db_path: str = "data/database/metal_history.db"):
        self.db_path = Path(db_path)
        self.db = None
        self.conn = None
        self.stats = {
            'nodes_created': {},
            'relationships_created': {},
            'errors': [],
            'start_time': datetime.now()
        }
        self.id_counter = 1  # For generating numeric IDs
        self.name_to_id = {}  # Map names to numeric IDs
    
    def _extract_locations_from_bands(self, bands: List[Dict]) -> List[Dict]:
        """Extract GeographicLocation entities from band origin_location data."""
        locations = {}
        
        for band in bands:
            origin_location = band.get('origin_location', '')
            if origin_location:
                parts = [p.strip() for p in origin_location.split(',')]
                
                if len(parts) >= 2:
                    # "City, Country" or "City, State, Country" format
                    city = parts[0]
                    country = parts[-1]
                    region = parts[1] if len(parts) > 2 else None
                    
                    # Create unique key for location
                    loc_key = f"{city}|{country}"
                    
                    if loc_key not in locations:
                        locations[loc_key] = {
                            'city': city,
                            'country': country,
                            'region': region,
                            'significance': f"Origin location of {band['name']}",
                            '_metadata': band.get('_metadata', {})
                        }
                    else:
                        # Update significance to include multiple bands
                        current_sig = locations[loc_key]['significance']
                        if band['name'] not in current_sig:
                            locations[loc_key]['significance'] += f", {band['name']}"
                elif len(parts) == 1:
                    # Just city or country
                    loc_key = parts[0]
                    if loc_key not in locations:
                        locations[loc_key] = {
                            'city': parts[0],
                            'country': '',
                            'significance': f"Origin location of {band['name']}",
                            '_metadata': band.get('_metadata', {})
                        }
        
        return list(locations.values())
    
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
    
    def _get_numeric_id(self, entity_type: str, name: str) -> int:
        """Get or create a numeric ID for an entity."""
        key = f"{entity_type}:{name}"
        if key not in self.name_to_id:
            self.name_to_id[key] = self.id_counter
            self.id_counter += 1
        return self.name_to_id[key]
    
    def load_entities_from_file(self, entities_file: str, batch_size: int = 100):
        """Load all entities from a JSON file into Kuzu."""
        logger.info(f"Loading entities from {entities_file}")
        
        with open(entities_file, 'r') as f:
            data = json.load(f)
        
        # Handle both nested and flat structures
        if 'entities' in data:
            entities = data['entities']
        else:
            entities = data
        
        # Extract locations from band data if not present
        if not entities.get('locations'):
            entities['locations'] = self._extract_locations_from_bands(entities.get('bands', []))
        
        # Connect to database
        self.connect()
        
        try:
            # Load nodes first - order matters for relationships
            self._load_locations(entities.get('locations', []), batch_size)  # Load locations first
            self._load_bands(entities.get('bands', []), batch_size)
            self._load_people(entities.get('people', []), batch_size)
            self._load_subgenres(entities.get('subgenres', []), batch_size)
            self._load_albums(entities.get('albums', []), batch_size)
            self._load_songs(entities.get('songs', []), batch_size)
            # Note: Venue not in base schema, skip
            # self._load_venues(entities.get('venues', []), batch_size)
            self._load_events(entities.get('events', []), batch_size)
            # Note: Movement not in base schema, skip
            # self._load_movements(entities.get('movements', []), batch_size)
            
            # Load relationships
            self._load_relationships(entities)
            
            # Print summary
            self._print_summary()
            
        finally:
            self.close()
    
    def _load_bands(self, bands: List[Dict], batch_size: int):
        """Load band nodes."""
        logger.info(f"Loading {len(bands)} bands...")
        
        for band in tqdm(bands, desc="Loading bands"):
            try:
                # Parse location into city and country
                origin_location = band.get('origin_location', '')
                origin_city = ''
                origin_country = ''
                if origin_location:
                    parts = [p.strip() for p in origin_location.split(',')]
                    if len(parts) >= 2:
                        # Handle "City, Country" or "City, State, Country" formats
                        origin_city = parts[0]
                        origin_country = parts[-1]  # Last part is usually country
                    elif len(parts) == 1:
                        # Just country or city
                        origin_city = parts[0]
                
                # Prepare parameters matching schema
                params = {
                    'id': self._get_numeric_id('band', band['name']),
                    'name': band['name'],
                    'formed_year': band.get('formed_year'),
                    'origin_city': origin_city,
                    'origin_country': origin_country,
                    'status': band.get('status', 'active'),  # Use status if provided
                    'description': band.get('description', ''),
                    'embedding': band.get('embedding', [0.0] * 1024)  # Default embedding if missing
                }
                
                # Create node
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
                
                self.stats['nodes_created']['bands'] = self.stats['nodes_created'].get('bands', 0) + 1
                
            except Exception as e:
                logger.error(f"Error loading band {band.get('name', 'Unknown')}: {e}")
                self.stats['errors'].append({
                    'entity_type': 'band',
                    'entity': band.get('name'),
                    'error': str(e)
                })
    
    def _load_people(self, people: List[Dict], batch_size: int):
        """Load person nodes."""
        logger.info(f"Loading {len(people)} people...")
        
        for person in tqdm(people, desc="Loading people"):
            try:
                # Map roles to instruments if applicable
                roles = person.get('roles', [])
                instruments = person.get('instruments', [])  # Check if instruments already provided
                
                # If no instruments but we have roles, try to map them
                if not instruments and roles:
                    role_to_instrument = {
                        'guitarist': 'guitar',
                        'bassist': 'bass',
                        'drummer': 'drums',
                        'vocalist': 'vocals',
                        'keyboardist': 'keyboards',
                        'singer': 'vocals',
                        'guitar': 'guitar',
                        'bass': 'bass',
                        'drums': 'drums',
                        'vocals': 'vocals',
                        'keyboards': 'keyboards'
                    }
                    for role in roles:
                        role_lower = role.lower()
                        if role_lower in role_to_instrument:
                            instruments.append(role_to_instrument[role_lower])
                        else:
                            # Use the role as-is if not in mapping
                            instruments.append(role)
                
                # Ensure instruments is a list and remove duplicates
                instruments = list(set(instruments)) if instruments else []
                
                params = {
                    'id': self._get_numeric_id('person', person['name']),
                    'name': person['name'],
                    'birth_year': person.get('birth_year'),
                    'death_year': person.get('death_year'),
                    'nationality': person.get('nationality'),
                    'instruments': instruments,
                    'description': person.get('description', person.get('known_for', '')),
                    'embedding': person.get('embedding', [0.0] * 1024)
                }
                
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
                
                self.stats['nodes_created']['people'] = self.stats['nodes_created'].get('people', 0) + 1
                
            except Exception as e:
                logger.error(f"Error loading person {person.get('name', 'Unknown')}: {e}")
                self.stats['errors'].append({
                    'entity_type': 'person',
                    'entity': person.get('name'),
                    'error': str(e)
                })
    
    def _load_locations(self, locations: List[Dict], batch_size: int):
        """Load geographic location nodes."""
        logger.info(f"Loading {len(locations)} locations...")
        
        for location in tqdm(locations, desc="Loading locations"):
            try:
                params = {
                    'id': self._get_numeric_id('location', location.get('city', 'unknown')),
                    'city': location.get('city'),
                    'state_province': location.get('state_province'),
                    'country': location.get('country'),
                    'region': location.get('region', ''),
                    'significance': location.get('significance', location.get('scene_description', '')),
                    'source_chunks': location.get('_metadata', {}).get('source_chunks', [])
                }
                
                # Schema expects these exact properties
                self.conn.execute("""
                    CREATE (l:GeographicLocation {
                        id: $id,
                        city: $city,
                        region: $region,
                        country: $country,
                        scene_description: $significance,
                        cultural_context: $cultural_context,
                        embedding: $embedding
                    })
                """, {
                    'id': params['id'],
                    'city': params['city'] or '',
                    'region': params['region'] or params.get('state_province', ''),
                    'country': params['country'] or '',
                    'significance': params['significance'],
                    'cultural_context': location.get('cultural_context', ''),
                    'embedding': location.get('embedding', [0.0] * 1024)
                })
                
                self.stats['nodes_created']['locations'] = self.stats['nodes_created'].get('locations', 0) + 1
                
            except Exception as e:
                logger.error(f"Error loading location {location}: {e}")
                self.stats['errors'].append({
                    'entity_type': 'location',
                    'entity': str(location),
                    'error': str(e)
                })
    
    def _load_subgenres(self, subgenres: List[Dict], batch_size: int):
        """Load subgenre nodes."""
        logger.info(f"Loading {len(subgenres)} subgenres...")
        
        for subgenre in tqdm(subgenres, desc="Loading subgenres"):
            try:
                # Map era_start from various possible fields
                era_start = subgenre.get('era_start') or subgenre.get('originated_year') or subgenre.get('started_year')
                
                # Convert characteristics to string if it's a list
                characteristics = subgenre.get('characteristics') or subgenre.get('key_characteristics', [])
                if isinstance(characteristics, list):
                    key_characteristics = ', '.join(characteristics)
                else:
                    key_characteristics = str(characteristics)
                
                params = {
                    'id': self._get_numeric_id('subgenre', subgenre['name']),
                    'name': subgenre['name'],
                    'era_start': era_start,
                    'era_end': None,  # Not specified in our data
                    'bpm_min': subgenre.get('bpm_min'),
                    'bpm_max': subgenre.get('bpm_max'),
                    'guitar_tuning': subgenre.get('guitar_tuning'),
                    'vocal_style': subgenre.get('vocal_style'),
                    'key_characteristics': key_characteristics,
                    'parent_influences': subgenre.get('parent_influences', []),
                    'embedding': subgenre.get('embedding', [0.0] * 1024)
                }
                
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
                        embedding: $embedding
                    })
                """, params)
                
                self.stats['nodes_created']['subgenres'] = self.stats['nodes_created'].get('subgenres', 0) + 1
                
            except Exception as e:
                logger.error(f"Error loading subgenre {subgenre.get('name', 'Unknown')}: {e}")
                self.stats['errors'].append({
                    'entity_type': 'subgenre',
                    'entity': subgenre.get('name'),
                    'error': str(e)
                })
    
    def _load_albums(self, albums: List[Dict], batch_size: int):
        """Load album nodes."""
        logger.info(f"Loading {len(albums)} albums...")
        
        for album in tqdm(albums, desc="Loading albums"):
            try:
                # Handle release date - could be full date or just year
                release_date = album.get('release_date')
                release_year = album.get('release_year')
                
                if not release_date and release_year:
                    # Convert year to date format
                    release_date = f"{release_year}-01-01"
                elif release_date and len(release_date) == 4:  # Just a year
                    release_date = f"{release_date}-01-01"
                
                # Ensure we have release_year
                if not release_year and release_date:
                    try:
                        release_year = int(release_date[:4])
                    except:
                        release_year = None
                
                params = {
                    'id': self._get_numeric_id('album', album['title']),
                    'title': album['title'],
                    'release_year': release_year,  # Schema uses release_year not release_date
                    'release_date': release_date,
                    'label': album.get('label'),
                    'producer': album.get('producer'),
                    'studio': album.get('studio'),
                    'chart_position': album.get('chart_position'),
                    'description': album.get('description', ''),
                    'embedding': album.get('embedding', [0.0] * 1024)
                }
                
                # Store band info for relationship creation later
                if album.get('band_name') or album.get('artist'):
                    album['_band_name'] = album.get('band_name', album.get('artist'))
                
                self.conn.execute("""
                    CREATE (a:Album {
                        id: $id,
                        title: $title,
                        release_date: $release_date,
                        label: $label,
                        producer: $producer,
                        studio: $studio,
                        chart_position: $chart_position,
                        description: $description,
                        embedding: $embedding
                    })
                """, params)
                
                self.stats['nodes_created']['albums'] = self.stats['nodes_created'].get('albums', 0) + 1
                
            except Exception as e:
                logger.error(f"Error loading album {album.get('title', 'Unknown')}: {e}")
                self.stats['errors'].append({
                    'entity_type': 'album',
                    'entity': album.get('title'),
                    'error': str(e)
                })
    
    def _load_songs(self, songs: List[Dict], batch_size: int):
        """Load song nodes."""
        logger.info(f"Loading {len(songs)} songs...")
        
        for song in tqdm(songs, desc="Loading songs"):
            try:
                # Convert duration to seconds if needed
                duration_seconds = song.get('duration_seconds') or song.get('duration')
                
                params = {
                    'id': self._get_numeric_id('song', song['title']),
                    'title': song['title'],
                    'duration_seconds': duration_seconds,
                    'bpm': song.get('bpm'),
                    'description': song.get('description', ''),
                    'embedding': song.get('embedding', [0.0] * 1024)
                }
                
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
                
                self.stats['nodes_created']['songs'] = self.stats['nodes_created'].get('songs', 0) + 1
                
            except Exception as e:
                logger.error(f"Error loading song {song.get('title', 'Unknown')}: {e}")
                self.stats['errors'].append({
                    'entity_type': 'song',
                    'entity': song.get('title'),
                    'error': str(e)
                })
    
    def _load_venues(self, venues: List[Dict], batch_size: int):
        """Load venue nodes."""
        logger.info(f"Loading {len(venues)} venues...")
        
        for venue in tqdm(venues, desc="Loading venues"):
            try:
                params = {
                    'id': self._get_numeric_id('venue', venue['name']),
                    'name': venue['name'],
                    'location': venue.get('location'),
                    'capacity': venue.get('capacity'),
                    'opened_year': venue.get('opened_year'),
                    'closed_year': venue.get('closed_year'),
                    'significance': venue.get('significance', ''),
                    'source_chunks': venue.get('_metadata', {}).get('source_chunks', [])
                }
                
                self.conn.execute("""
                    CREATE (v:Venue {
                        id: $id,
                        name: $name,
                        location: $location,
                        capacity: $capacity,
                        opened_year: $opened_year,
                        closed_year: $closed_year,
                        significance: $significance,
                        source_chunks: $source_chunks
                    })
                """, params)
                
                self.stats['nodes_created']['venues'] = self.stats['nodes_created'].get('venues', 0) + 1
                
            except Exception as e:
                logger.error(f"Error loading venue {venue.get('name', 'Unknown')}: {e}")
                self.stats['errors'].append({
                    'entity_type': 'venue',
                    'entity': venue.get('name'),
                    'error': str(e)
                })
    
    def _load_events(self, events: List[Dict], batch_size: int):
        """Load event nodes."""
        logger.info(f"Loading {len(events)} events...")
        
        for event in tqdm(events, desc="Loading events"):
            try:
                # Map to CulturalEvent schema
                params = {
                    'id': self._get_numeric_id('event', event['name']),
                    'name': event['name'],
                    'type': event.get('type', 'movement'),  # Default to movement type
                    'date': event.get('date'),  # Must be proper DATE format or None
                    'impact': event.get('impact', event.get('significance', '')),
                    'description': event.get('description', ''),
                    'embedding': event.get('embedding', [0.0] * 1024)
                }
                
                self.conn.execute("""
                    CREATE (e:CulturalEvent {
                        id: $id,
                        name: $name,
                        type: $type,
                        date: $date,
                        impact: $impact,
                        description: $description,
                        embedding: $embedding
                    })
                """, params)
                
                self.stats['nodes_created']['events'] = self.stats['nodes_created'].get('events', 0) + 1
                
            except Exception as e:
                logger.error(f"Error loading event {event.get('name', 'Unknown')}: {e}")
                self.stats['errors'].append({
                    'entity_type': 'event',
                    'entity': event.get('name'),
                    'error': str(e)
                })
    
    def _load_movements(self, movements: List[Dict], batch_size: int):
        """Load movement nodes."""
        logger.info(f"Loading {len(movements)} movements...")
        
        for movement in tqdm(movements, desc="Loading movements"):
            try:
                params = {
                    'id': self._get_numeric_id('movement', movement['name']),
                    'name': movement['name'],
                    'started_year': movement.get('started_year'),
                    'ended_year': movement.get('ended_year'),
                    'origin_location': movement.get('origin_location'),
                    'key_bands': movement.get('key_bands', []),
                    'characteristics': movement.get('characteristics', []),
                    'description': movement.get('description', ''),
                    'source_chunks': movement.get('_metadata', {}).get('source_chunks', []),
                    'embedding': movement.get('embedding', [0.0] * 1024)
                }
                
                self.conn.execute("""
                    CREATE (m:Movement {
                        id: $id,
                        name: $name,
                        started_year: $started_year,
                        ended_year: $ended_year,
                        origin_location: $origin_location,
                        key_bands: $key_bands,
                        characteristics: $characteristics,
                        description: $description,
                        source_chunks: $source_chunks,
                        embedding: $embedding
                    })
                """, params)
                
                self.stats['nodes_created']['movements'] = self.stats['nodes_created'].get('movements', 0) + 1
                
            except Exception as e:
                logger.error(f"Error loading movement {movement.get('name', 'Unknown')}: {e}")
                self.stats['errors'].append({
                    'entity_type': 'movement',
                    'entity': movement.get('name'),
                    'error': str(e)
                })
    
    def _load_relationships(self, entities: Dict):
        """Load relationships between entities."""
        logger.info("Loading relationships...")
        
        # Band -> Album relationships
        self._create_released_relationships(entities)
        
        # Band -> Location relationships
        self._create_formed_in_relationships(entities)
        
        # Band -> Subgenre relationships
        self._create_plays_genre_relationships(entities)
        
        # Person -> Band relationships
        self._create_member_of_relationships(entities)
        
        # Album -> Song relationships
        self._create_contains_track_relationships(entities)
        
        # Other relationships from extraction data
        self._create_extracted_relationships(entities)
        
        logger.info("Relationships loading complete")
    
    def _create_released_relationships(self, entities: Dict):
        """Create RELEASED relationships between bands and albums."""
        albums = entities.get('albums', [])
        
        for album in tqdm(albums, desc="Creating RELEASED relationships"):
            # Check for band_name, artist, or _band_name (from loading)
            band_name = album.get('band_name') or album.get('artist') or album.get('_band_name')
            if band_name:
                try:
                    # Use numeric IDs for matching
                    band_id = self._get_numeric_id('band', band_name)
                    album_id = self._get_numeric_id('album', album['title'])
                    
                    self.conn.execute("""
                        MATCH (b:Band), (a:Album)
                        WHERE b.id = $band_id AND a.id = $album_id
                        CREATE (b)-[r:RELEASED {release_order: $release_order}]->(a)
                    """, {
                        'band_id': band_id,
                        'album_id': album_id,
                        'release_order': album.get('release_order', 1)
                    })
                    
                    rel_type = 'band_released_album'
                    self.stats['relationships_created'][rel_type] = \
                        self.stats['relationships_created'].get(rel_type, 0) + 1
                    
                except Exception as e:
                    logger.error(f"Error creating RELEASED relationship: {e}")
    
    def _create_formed_in_relationships(self, entities: Dict):
        """Create FORMED_IN relationships between bands and locations."""
        bands = entities.get('bands', [])
        locations = entities.get('locations', [])
        
        # First create a location lookup
        location_lookup = {}
        for loc in locations:
            if loc.get('city'):
                location_lookup[loc['city'].lower()] = loc
        
        for band in tqdm(bands, desc="Creating FORMED_IN relationships"):
            if band.get('origin_location') or (band.get('origin_city') and band.get('origin_country')):
                try:
                    # Extract city from origin_location or use origin_city
                    city_name = band.get('origin_city')
                    if not city_name and band.get('origin_location'):
                        parts = [p.strip() for p in band['origin_location'].split(',')]
                        city_name = parts[0] if parts else None
                    
                    if city_name and city_name.lower() in location_lookup:
                        # Match existing location
                        band_id = self._get_numeric_id('band', band['name'])
                        location_id = self._get_numeric_id('location', city_name)
                        
                        self.conn.execute("""
                            MATCH (b:Band), (l:GeographicLocation)
                            WHERE b.id = $band_id AND l.id = $location_id
                            CREATE (b)-[r:FORMED_IN]->(l)
                        """, {
                            'band_id': band_id,
                            'location_id': location_id
                        })
                    
                    rel_type = 'band_formed_in_location'
                    self.stats['relationships_created'][rel_type] = \
                        self.stats['relationships_created'].get(rel_type, 0) + 1
                    
                except Exception as e:
                    logger.error(f"Error creating FORMED_IN relationship: {e}")
    
    def _create_plays_genre_relationships(self, entities: Dict):
        """Create PLAYS_GENRE relationships between bands and subgenres."""
        bands = entities.get('bands', [])
        
        for band in tqdm(bands, desc="Creating PLAYS_GENRE relationships"):
            for genre in band.get('genres', []):
                try:
                    self.conn.execute("""
                        MATCH (b:Band), (s:Subgenre)
                        WHERE b.name = $band_name AND s.name = $genre_name
                        CREATE (b)-[r:PLAYS_GENRE]->(s)
                    """, {
                        'band_name': band['name'],
                        'genre_name': genre
                    })
                    
                    rel_type = 'band_plays_genre'
                    self.stats['relationships_created'][rel_type] = \
                        self.stats['relationships_created'].get(rel_type, 0) + 1
                    
                except Exception as e:
                    # Genre might not exist as entity
                    logger.debug(f"Could not create PLAYS_GENRE relationship: {e}")
    
    def _create_member_of_relationships(self, entities: Dict):
        """Create MEMBER_OF relationships between people and bands."""
        people = entities.get('people', [])
        
        for person in tqdm(people, desc="Creating MEMBER_OF relationships"):
            # Check for associated_bands field
            for band_name in person.get('associated_bands', []):
                try:
                    person_id = self._get_numeric_id('person', person['name'])
                    band_id = self._get_numeric_id('band', band_name)
                    
                    # Determine role from instruments
                    instruments = person.get('instruments', [])
                    role = instruments[0] if instruments else 'member'
                    
                    self.conn.execute("""
                        MATCH (p:Person), (b:Band)
                        WHERE p.id = $person_id AND b.id = $band_id
                        CREATE (p)-[r:MEMBER_OF {role: $role}]->(b)
                    """, {
                        'person_id': person_id,
                        'band_id': band_id,
                        'role': role
                    })
                    
                    rel_type = 'person_member_of_band'
                    self.stats['relationships_created'][rel_type] = \
                        self.stats['relationships_created'].get(rel_type, 0) + 1
                    
                except Exception as e:
                    logger.debug(f"Could not create MEMBER_OF relationship: {e}")
    
    def _create_contains_track_relationships(self, entities: Dict):
        """Create CONTAINS_TRACK relationships between albums and songs."""
        songs = entities.get('songs', [])
        
        for song in tqdm(songs, desc="Creating CONTAINS_TRACK relationships"):
            if song.get('album') or song.get('album_title'):
                try:
                    album_title = song.get('album') or song.get('album_title')
                    song_id = self._get_numeric_id('song', song['title'])
                    album_id = self._get_numeric_id('album', album_title)
                    
                    self.conn.execute("""
                        MATCH (a:Album), (s:Song)
                        WHERE a.id = $album_id AND s.id = $song_id
                        CREATE (a)-[r:CONTAINS_TRACK {track_number: $track_num}]->(s)
                    """, {
                        'album_id': album_id,
                        'song_id': song_id,
                        'track_num': song.get('track_number', 1)
                    })
                    
                    rel_type = 'album_contains_track'
                    self.stats['relationships_created'][rel_type] = \
                        self.stats['relationships_created'].get(rel_type, 0) + 1
                    
                except Exception as e:
                    logger.debug(f"Could not create CONTAINS_TRACK relationship: {e}")
    
    def _create_extracted_relationships(self, entities: Dict):
        """Create relationships from explicit relationship entities."""
        relationships = entities.get('relationships', [])
        
        for rel in tqdm(relationships, desc="Creating extracted relationships"):
            try:
                # Map relationship types to schema types
                rel_type_map = {
                    'member_of': 'MEMBER_OF',
                    'formed_in': 'FORMED_IN',
                    'released': 'RELEASED',
                    'plays_genre': 'PLAYS_GENRE',
                    'influenced_by': 'INFLUENCED_BY',
                    'produced': 'PRODUCED',
                    'recorded_at': 'RECORDED_AT'
                }
                
                rel_type = rel_type_map.get(rel['type'].lower(), rel['type'].upper())
                
                # Skip if relationship type is not in schema
                valid_rel_types = ['FORMED_IN', 'PLAYS_GENRE', 'RELEASED', 'ACTIVE_DURING',
                                  'MEMBER_OF', 'PRODUCED', 'PERFORMED_ON', 'CONTAINS_TRACK',
                                  'RECORDED_AT', 'RELEASED_BY', 'REPRESENTS_GENRE',
                                  'INFLUENCED_BY', 'EVOLVED_INTO', 'ORIGINATED_IN',
                                  'EMERGED_DURING', 'SCENE_SPAWNED', 'SCENE_DEVELOPED',
                                  'DOCUMENTED_IN', 'FEATURED_IN', 'PARTICIPATED_IN',
                                  'INFLUENCED_EVENT', 'HAS_CHARACTERISTIC', 
                                  'USES_TECHNIQUE', 'ALBUM_FEATURES', 'MENTIONED_WITH',
                                  'CONTEMPORARY_OF', 'CITATION']
                
                if rel_type not in valid_rel_types:
                    logger.debug(f"Skipping invalid relationship type: {rel_type}")
                    continue
                
                # Get numeric IDs for entities
                from_id = self._get_numeric_id(rel['from_entity_type'], rel['from_entity_name'])
                to_id = self._get_numeric_id(rel['to_entity_type'], rel['to_entity_name'])
                
                # Build dynamic query based on relationship type
                params = {
                    'from_id': from_id,
                    'to_id': to_id
                }
                
                # Add optional properties
                props = []
                if rel.get('year'):
                    props.append('year: $year')
                    params['year'] = rel['year']
                if rel.get('role'):
                    props.append('role: $role')
                    params['role'] = rel['role']
                
                props_str = f" {{{', '.join(props)}}}" if props else ""
                
                # Create relationship
                query = f"""
                    MATCH (a), (b)
                    WHERE a.id = $from_id AND b.id = $to_id
                    CREATE (a)-[r:{rel_type}{props_str}]->(b)
                """
                
                self.conn.execute(query, params)
                
                self.stats['relationships_created'][rel_type.lower()] = \
                    self.stats['relationships_created'].get(rel_type.lower(), 0) + 1
                    
            except Exception as e:
                logger.debug(f"Could not create extracted relationship: {e}")
    
    def verify_data(self):
        """Verify loaded data with sample queries."""
        logger.info("Verifying loaded data...")
        
        self.connect()
        
        try:
            # Count nodes
            node_counts = {}
            for node_type in ['Band', 'Person', 'Album', 'Song', 'Subgenre', 
                            'GeographicLocation', 'CulturalEvent', 'RecordLabel', 'Studio', 'Era']:
                try:
                    result = self.conn.execute(f"MATCH (n:{node_type}) RETURN COUNT(n) as count")
                    count = result.get_next()[0]
                    node_counts[node_type] = count
                    logger.info(f"{node_type} nodes: {count}")
                except Exception as e:
                    logger.warning(f"Could not count {node_type}: {e}")
            
            # Count relationships
            rel_counts = {}
            for rel_type in ['RELEASED', 'FORMED_IN', 'PLAYS_GENRE', 'MEMBER_OF']:
                result = self.conn.execute(f"MATCH ()-[r:{rel_type}]->() RETURN COUNT(r) as count")
                count = result.get_next()[0]
                rel_counts[rel_type] = count
                logger.info(f"{rel_type} relationships: {count}")
            
            # Sample queries
            logger.info("\nSample data:")
            
            # Top 5 bands
            result = self.conn.execute("""
                MATCH (b:Band)
                RETURN b.name, b.formed_year
                ORDER BY b.formed_year
                LIMIT 5
            """)
            logger.info("Earliest bands:")
            while result.has_next():
                row = result.get_next()
                logger.info(f"  - {row[0]} ({row[1]})")
            
        finally:
            self.close()
    
    def _print_summary(self):
        """Print loading summary."""
        elapsed = (datetime.now() - self.stats['start_time']).total_seconds()
        
        print("\n" + "="*60)
        print("KUZU LOADING SUMMARY")
        print("="*60)
        print(f"Loading time: {elapsed:.1f} seconds")
        
        print("\nNodes created:")
        total_nodes = 0
        for node_type, count in self.stats['nodes_created'].items():
            print(f"  {node_type}: {count}")
            total_nodes += count
        print(f"  TOTAL: {total_nodes}")
        
        print("\nRelationships created:")
        total_rels = 0
        for rel_type, count in self.stats['relationships_created'].items():
            print(f"  {rel_type}: {count}")
            total_rels += count
        print(f"  TOTAL: {total_rels}")
        
        if self.stats['errors']:
            print(f"\nErrors encountered: {len(self.stats['errors'])}")
            for i, error in enumerate(self.stats['errors'][:5]):
                print(f"  {i+1}. {error['entity_type']}: {error['entity']} - {error['error']}")
            if len(self.stats['errors']) > 5:
                print(f"  ... and {len(self.stats['errors']) - 5} more")
        
        print("="*60)

def main():
    parser = argparse.ArgumentParser(description="Load entities into Kuzu database")
    parser.add_argument('entities_file', type=str,
                       help='Path to deduplicated entities JSON file')
    parser.add_argument('--db-path', type=str, default='data/database/metal_history.db',
                       help='Path to Kuzu database')
    parser.add_argument('--batch-size', type=int, default=100,
                       help='Batch size for loading')
    parser.add_argument('--verify', action='store_true',
                       help='Verify data after loading')
    
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
        logger.info("Run 'python src/schema/initialize_kuzu.py' to create database first")
        sys.exit(1)
    
    loader = KuzuLoader(db_path=str(db_path))
    
    try:
        # Load entities
        loader.load_entities_from_file(args.entities_file, args.batch_size)
        
        # Verify if requested
        if args.verify:
            loader.verify_data()
            
    except Exception as e:
        logger.error(f"Loading failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()