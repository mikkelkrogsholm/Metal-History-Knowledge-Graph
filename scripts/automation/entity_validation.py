#!/usr/bin/env python3
"""
Entity validation and quality checks for extracted entities.
Validates data consistency, completeness, and quality.
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Tuple, Set
from datetime import datetime
import sys

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.append(str(PROJECT_ROOT))

from extraction.extraction_schemas import Band, Person, Album, Song, Subgenre

class EntityValidator:
    """Validates extracted entities for quality and consistency."""
    
    def __init__(self):
        self.validation_results = {
            'errors': [],
            'warnings': [],
            'stats': {},
            'quality_score': 0.0
        }
        
        # Known valid patterns
        self.year_pattern = re.compile(r'^\d{4}$')
        self.name_pattern = re.compile(r'^[A-Za-z0-9\s\-\'&.,!]+$')
        
        # Known subgenres for validation
        self.known_subgenres = {
            'heavy metal', 'thrash metal', 'death metal', 'black metal',
            'doom metal', 'power metal', 'progressive metal', 'folk metal',
            'symphonic metal', 'gothic metal', 'industrial metal',
            'groove metal', 'nu metal', 'metalcore', 'deathcore'
        }
    
    def validate_entities_file(self, entities_file: str) -> Dict:
        """Validate entities from a JSON file."""
        with open(entities_file, 'r') as f:
            data = json.load(f)
        
        entities = data.get('entities', {})
        
        # Validate each entity type
        self._validate_bands(entities.get('bands', []))
        self._validate_people(entities.get('people', []))
        self._validate_albums(entities.get('albums', []))
        self._validate_songs(entities.get('songs', []))
        self._validate_subgenres(entities.get('subgenres', []))
        self._validate_relationships(entities)
        
        # Calculate quality score
        self._calculate_quality_score()
        
        return self.validation_results
    
    def _validate_bands(self, bands: List[Dict]):
        """Validate band entities."""
        band_names = set()
        
        for band in bands:
            # Check for duplicates
            if band['name'] in band_names:
                self._add_error(f"Duplicate band: {band['name']}")
            band_names.add(band['name'])
            
            # Validate required fields
            if not band.get('name'):
                self._add_error(f"Band missing name: {band}")
            
            # Validate year
            if band.get('formed_year'):
                if not self._is_valid_year(band['formed_year']):
                    self._add_error(f"Invalid formed_year for {band['name']}: {band['formed_year']}")
                elif int(band['formed_year']) < 1960 or int(band['formed_year']) > 2024:
                    self._add_warning(f"Unusual formed_year for {band['name']}: {band['formed_year']}")
            
            # Check for conflicts
            if band.get('_conflicts'):
                self._add_warning(f"Band {band['name']} has unresolved conflicts")
        
        self.validation_results['stats']['total_bands'] = len(bands)
        self.validation_results['stats']['unique_bands'] = len(band_names)
    
    def _validate_people(self, people: List[Dict]):
        """Validate person entities."""
        person_names = set()
        
        for person in people:
            # Check for duplicates
            if person['name'] in person_names:
                self._add_warning(f"Potential duplicate person: {person['name']}")
            person_names.add(person['name'])
            
            # Validate name format
            if not person.get('name'):
                self._add_error(f"Person missing name: {person}")
            elif len(person['name']) < 2:
                self._add_error(f"Invalid person name: {person['name']}")
            
            # Validate birth/death years
            if person.get('birth_year'):
                if not self._is_valid_year(person['birth_year']):
                    self._add_error(f"Invalid birth_year for {person['name']}: {person['birth_year']}")
            
            if person.get('death_year'):
                if not self._is_valid_year(person['death_year']):
                    self._add_error(f"Invalid death_year for {person['name']}: {person['death_year']}")
                elif person.get('birth_year') and int(person['death_year']) < int(person['birth_year']):
                    self._add_error(f"Death before birth for {person['name']}")
        
        self.validation_results['stats']['total_people'] = len(people)
    
    def _validate_albums(self, albums: List[Dict]):
        """Validate album entities."""
        for album in albums:
            # Validate required fields
            if not album.get('title'):
                self._add_error(f"Album missing title: {album}")
            
            if not album.get('band_name'):
                self._add_error(f"Album '{album.get('title', 'Unknown')}' missing band_name")
            
            # Validate release year
            if album.get('release_year'):
                if not self._is_valid_year(album['release_year']):
                    self._add_error(f"Invalid release_year for {album['title']}: {album['release_year']}")
                elif int(album['release_year']) < 1968 or int(album['release_year']) > 2024:
                    self._add_warning(f"Unusual release_year for {album['title']}: {album['release_year']}")
        
        self.validation_results['stats']['total_albums'] = len(albums)
    
    def _validate_songs(self, songs: List[Dict]):
        """Validate song entities."""
        for song in songs:
            if not song.get('title'):
                self._add_error(f"Song missing title: {song}")
            
            if song.get('duration') and song['duration'] < 0:
                self._add_error(f"Invalid duration for song {song['title']}: {song['duration']}")
        
        self.validation_results['stats']['total_songs'] = len(songs)
    
    def _validate_subgenres(self, subgenres: List[Dict]):
        """Validate subgenre entities."""
        for subgenre in subgenres:
            if not subgenre.get('name'):
                self._add_error(f"Subgenre missing name: {subgenre}")
            elif subgenre['name'].lower() not in self.known_subgenres:
                self._add_warning(f"Unknown subgenre: {subgenre['name']}")
        
        self.validation_results['stats']['total_subgenres'] = len(subgenres)
    
    def _validate_relationships(self, entities: Dict):
        """Validate entity relationships and cross-references."""
        bands = {b['name']: b for b in entities.get('bands', [])}
        people = {p['name']: p for p in entities.get('people', [])}
        
        # Validate album-band relationships
        for album in entities.get('albums', []):
            if album.get('band_name') and album['band_name'] not in bands:
                self._add_warning(f"Album '{album['title']}' references unknown band: {album['band_name']}")
        
        # Validate song-album relationships
        for song in entities.get('songs', []):
            if song.get('album_title'):
                album_exists = any(a['title'] == song['album_title'] 
                                 for a in entities.get('albums', []))
                if not album_exists:
                    self._add_warning(f"Song '{song['title']}' references unknown album: {song['album_title']}")
    
    def _is_valid_year(self, year) -> bool:
        """Check if year is valid format."""
        if isinstance(year, int):
            year = str(year)
        return bool(self.year_pattern.match(str(year)))
    
    def _add_error(self, message: str):
        """Add validation error."""
        self.validation_results['errors'].append({
            'message': message,
            'severity': 'error',
            'timestamp': datetime.now().isoformat()
        })
    
    def _add_warning(self, message: str):
        """Add validation warning."""
        self.validation_results['warnings'].append({
            'message': message,
            'severity': 'warning',
            'timestamp': datetime.now().isoformat()
        })
    
    def _calculate_quality_score(self):
        """Calculate overall quality score (0-100)."""
        total_entities = sum(v for k, v in self.validation_results['stats'].items() 
                           if k.startswith('total_'))
        
        if total_entities == 0:
            self.validation_results['quality_score'] = 0
            return
        
        # Start with 100 and deduct for issues
        score = 100
        
        # Deduct for errors (5 points each)
        score -= len(self.validation_results['errors']) * 5
        
        # Deduct for warnings (2 points each)
        score -= len(self.validation_results['warnings']) * 2
        
        # Ensure score doesn't go below 0
        self.validation_results['quality_score'] = max(0, score)
    
    def generate_report(self, output_file: str = "validation_report.json"):
        """Generate validation report."""
        with open(output_file, 'w') as f:
            json.dump(self.validation_results, f, indent=2)
        
        # Print summary
        print("\n" + "="*60)
        print("ENTITY VALIDATION REPORT")
        print("="*60)
        print(f"Quality Score: {self.validation_results['quality_score']}/100")
        print(f"Errors: {len(self.validation_results['errors'])}")
        print(f"Warnings: {len(self.validation_results['warnings'])}")
        print("\nEntity Counts:")
        for stat, count in self.validation_results['stats'].items():
            print(f"  {stat}: {count}")
        
        if self.validation_results['errors']:
            print("\nTop Errors:")
            for error in self.validation_results['errors'][:5]:
                print(f"  ❌ {error['message']}")
        
        if self.validation_results['warnings']:
            print("\nTop Warnings:")
            for warning in self.validation_results['warnings'][:5]:
                print(f"  ⚠️  {warning['message']}")
        print("="*60)

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Validate extracted entities")
    parser.add_argument('entities_file', type=str,
                       help='Path to entities JSON file')
    parser.add_argument('--output', type=str, default='validation_report.json',
                       help='Output file for validation report')
    
    args = parser.parse_args()
    
    validator = EntityValidator()
    validator.validate_entities_file(args.entities_file)
    validator.generate_report(args.output)

if __name__ == "__main__":
    main()