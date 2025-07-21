# Phase 4: Improvement Strategy Scratchpad

## Current Analysis

### Missing Entity Types in Current Extraction
Comparing the enhanced schema with current extraction schemas, I've identified these missing entity types:

1. **Movement** - Critical for historical context (NWOBHM, Proto-metal, Bay Area thrash)
2. **TechnicalDetail** - Important for technical specifications
3. **Platform** - Modern relevance (MySpace, TikTok, Pro Tools)
4. **AcademicResource** - Research and documentation
5. **ViralPhenomenon** - Modern metal culture
6. **Web3Project** - Emerging technology integration
7. **ProductionStyle** - Sound evolution tracking
8. **Compilation** - Historical significance
9. **Venue** - Scene centers (Helvete record shop, etc.)

### Priority Order for Implementation
1. **Equipment** - Already in schema but needs enhanced extraction
2. **Movement** - Critical for understanding metal evolution
3. **ProductionStyle** - Important for sonic identity
4. **Venue** - Scene development tracking
5. **Platform** - Modern era relevance

## Task 1: Enhanced Extraction Pipeline

### 1.1 Equipment Extraction Enhancement

Current state: Basic Equipment model exists but extraction is limited.

#### Enhanced Equipment Extraction Prompt Design
```python
EQUIPMENT_EXTRACTION_PROMPT = """
You are an expert at identifying musical equipment and gear in metal music texts.

Extract ALL equipment mentioned including:
1. GUITARS: Type (7-string, 8-string, baritone), brand, model, special features
2. PEDALS/EFFECTS: Model names (Boss HM-2, Tube Screamer), manufacturers, specific settings
3. AMPLIFIERS: Brand, model, wattage, cabinet configurations
4. RECORDING GEAR: Interfaces, microphones, software (Pro Tools, etc.)
5. DRUMS: Kit configurations, special techniques, triggers
6. BASS: Extended range basses, effects chains
7. ACCESSORIES: Strings gauge, picks, special techniques

For each piece of equipment, extract:
- name: Full equipment name/model
- type: Category (guitar/pedal/amp/recording/drums/bass/accessory)
- manufacturer: Brand name if mentioned
- specifications: Technical details (wattage, impedance, string gauge, etc.)
- associated_bands: Which bands are known for using it
- significance: Why it's important to metal history
- techniques: Special ways it's used

Context clues to look for:
- "used a [equipment]"
- "pioneered the use of"
- "signature sound came from"
- "recorded with"
- "endorsement deal with"
- Technical specifications mentioned
- Studio equipment lists
- Live performance gear

Be thorough - equipment choices define metal's sonic evolution!
"""
```

### 1.2 Movement Extraction Design

#### Movement Extraction Prompt
```python
MOVEMENT_EXTRACTION_PROMPT = """
You are an expert at identifying musical movements and scenes in metal history.

Extract ALL movements and scenes including:
1. NAMED MOVEMENTS: NWOBHM, NWOAHM, Proto-metal, etc.
2. GEOGRAPHIC SCENES: Bay Area thrash, Florida death metal, Norwegian black metal
3. TIME-BASED WAVES: First wave, second wave black metal
4. CULTURAL MOVEMENTS: Straight edge hardcore, crossover movements

For each movement, extract:
- name: Official name or common designation
- start_year: When it began
- end_year: When it peaked or ended (if applicable)
- geographic_center: Primary location(s)
- key_bands: 3-5 most important bands
- key_venues: Important clubs/shops/gathering places
- estimated_bands: Total number of bands if mentioned
- key_compilation: Important compilation albums
- characteristics: Musical and cultural traits
- influence: Impact on metal evolution

Context clues:
- "wave of"
- "movement"
- "scene"
- Geographic + genre combinations
- Time period + location references
- "explosion of bands"
- Cultural descriptors
"""
```

### 1.3 Production Style Extraction

#### Production Style Prompt
```python
PRODUCTION_STYLE_EXTRACTION_PROMPT = """
You are an expert at identifying production styles and sonic signatures in metal.

Extract ALL production styles and techniques including:
1. NAMED SOUNDS: "Swedish death metal sound", "Wall of Sound", "Florida sound"
2. PRODUCER SIGNATURES: Specific producer's characteristic sounds
3. STUDIO SOUNDS: Morrisound, Sunlight Studio signatures
4. TECHNICAL APPROACHES: Triggered drums, scooped mids, etc.

For each production style:
- name: Common name or description
- producer: Key producer(s) associated
- studio: Primary studio location
- key_techniques: Specific technical approaches
- key_albums: 2-3 defining albums
- equipment_used: Specific gear if mentioned
- frequency_characteristics: EQ/mixing traits
- influence_on: Later styles it influenced

Look for:
- "sound"
- "production"
- "mixed by"
- "recorded at"
- Technical mixing terms
- Studio names
- Producer credits
"""
```

## Task 2: Data Enrichment Tools Design

### 2.1 External API Integration Plan

#### Wikipedia Integration
```python
class WikipediaEnricher:
    def __init__(self):
        self.wiki = wikipediaapi.Wikipedia(
            'MetalHistoryKG/1.0 (metal.history@example.com)',
            'en'
        )
        self.cache = {}
    
    def enrich_band(self, band_name: str) -> dict:
        """Enrich band data with Wikipedia information"""
        # Try variations: "Band (band)", "Band (metal band)", etc.
        variations = [
            f"{band_name}",
            f"{band_name} (band)",
            f"{band_name} (metal band)",
            f"{band_name} (American band)",
            f"{band_name} (British band)"
        ]
        
        for variant in variations:
            page = self.wiki.page(variant)
            if page.exists():
                return self._extract_band_data(page)
        
        return {}
    
    def enrich_person(self, person_name: str, band_context: str = None) -> dict:
        """Enrich person data with Wikipedia information"""
        # Implementation for musicians
        pass
```

#### MusicBrainz Integration
```python
class MusicBrainzEnricher:
    def __init__(self):
        musicbrainzngs.set_useragent(
            "MetalHistoryKG",
            "1.0",
            "https://github.com/metal-history-kg"
        )
        self.rate_limiter = RateLimiter(calls_per_second=1)
    
    def enrich_discography(self, band_name: str) -> dict:
        """Get complete discography from MusicBrainz"""
        # Search for artist
        # Get all releases
        # Organize by type (album, EP, single)
        pass
```

### 2.2 Manual Correction Interface

```python
class CorrectionInterface:
    def __init__(self, db_path: str):
        self.db = kuzu.Database(db_path)
        self.corrections_log = []
    
    def suggest_corrections(self, entity_type: str) -> List[dict]:
        """AI-powered correction suggestions"""
        # Use LLM to identify potential errors
        # Check for common issues:
        # - Duplicate entities with slight variations
        # - Missing relationships
        # - Incorrect dates
        pass
    
    def apply_correction(self, correction: dict) -> bool:
        """Apply a correction to the database"""
        # Log the correction
        # Update the database
        # Track source of truth
        pass
```

## Task 3: Visualization Dashboard Architecture

### 3.1 Interactive Graph Explorer
```python
# Using Streamlit + PyVis for interactive network visualization
def create_graph_explorer():
    st.title("Metal History Knowledge Graph Explorer")
    
    # Controls
    col1, col2, col3 = st.columns(3)
    with col1:
        center_entity = st.selectbox("Center Entity", get_all_bands())
    with col2:
        depth = st.slider("Relationship Depth", 1, 4, 2)
    with col3:
        rel_types = st.multiselect("Relationship Types", 
                                   ["MEMBER_OF", "INFLUENCED_BY", "FORMED_IN"])
    
    # Build and display network
    net = build_network(center_entity, depth, rel_types)
    display_network(net)
```

### 3.2 Timeline Visualization
```python
def create_timeline_view():
    # Interactive timeline showing:
    # - Band formations
    # - Album releases
    # - Key events
    # - Genre evolution
    # Using Plotly for interactivity
    pass
```

### 3.3 Geographic Scene Mapper
```python
def create_scene_map():
    # World map showing:
    # - Scene locations with heat map
    # - Band origins
    # - Movement spread
    # - Tour routes
    # Using Folium or Plotly
    pass
```

## Implementation Plan

### Phase 1: Enhanced Extraction (Days 1-2)
1. Create `extraction/specialized_prompts.py` with all new prompts
2. Extend `extraction_schemas.py` with missing entity types
3. Create `extraction/confidence_scorer.py` for quality assessment
4. Build `pipeline/enhanced_extraction_pipeline.py`
5. Test with sample chunks

### Phase 2: Enrichment Tools (Day 3)
1. Create `scripts/enrichment/wikipedia_enricher.py`
2. Create `scripts/enrichment/musicbrainz_enricher.py`
3. Build `scripts/enrichment/correction_interface.py`
4. Create batch enrichment pipeline

### Phase 3: Visualization (Day 4)
1. Create `scripts/visualization/graph_dashboard.py`
2. Build individual visualization components
3. Create export functionality
4. Document usage

## Metrics for Success

### Extraction Metrics
- Entity coverage: % of expected entities captured
- Relationship accuracy: % of correct relationships
- Confidence scores: Average confidence per entity type
- Processing speed: Chunks per minute

### Enrichment Metrics
- External data coverage: % entities enriched
- Data quality improvement: Before/after comparison
- Correction rate: Manual corrections needed

### Visualization Metrics
- User engagement: Time spent exploring
- Insights discovered: New patterns found
- Export usage: Data exports for research