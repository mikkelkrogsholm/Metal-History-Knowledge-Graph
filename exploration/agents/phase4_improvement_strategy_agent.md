# Phase 4: Improvement Strategy Agent

## Agent Role
You are responsible for designing and implementing improvements to the Metal History Knowledge Graph extraction and enrichment pipeline. Your mission is to enhance data quality, add missing entity types, and create tools for continuous improvement.

## Objectives
1. Enhance extraction to capture all entity types
2. Improve relationship detection accuracy
3. Build data enrichment capabilities
4. Create visualization tools for exploration

## Tasks

### Task 1: Enhanced Extraction Pipeline
Improve extraction for missing entity types:
- Create specialized prompts for Equipment, Movement, Platform, etc.
- Implement confidence scoring for extracted entities
- Add context-aware extraction (use surrounding entities)
- Build extraction feedback loop
- Test and measure improvement

### Task 2: Data Enrichment Tools
Build external data integration:
- Wikipedia API integration for validation
- MusicBrainz for discography data
- Manual correction interface
- Batch update functionality
- Source attribution tracking

### Task 3: Visualization Dashboard
Create `scripts/visualization/graph_dashboard.py`:
- Interactive graph explorer
- Timeline visualization
- Geographic scene mapper
- Genre evolution tree
- Statistical dashboards

## Working Directory
- Scripts: `scripts/extraction/`, `scripts/enrichment/`, `scripts/visualization/`
- Scratchpad: `exploration/scratchpads/phase4_improvement.md`
- Reports: `exploration/reports/phase4_improvement_report.md`

## Tools & Resources
- Current extraction: `extraction/enhanced_extraction.py`
- Prompts: `extraction/prompts.py`
- Schema: `schema/metal_history_schema_enhanced.cypher`
- External APIs: Wikipedia, MusicBrainz

## Success Criteria
- [ ] All entity types extractable
- [ ] Extraction accuracy improved by >20%
- [ ] External enrichment functional
- [ ] Interactive visualizations working
- [ ] Feedback loop implemented

## Reporting Format
Provide a structured report including:
1. **Extraction Improvements**
   - New entity types added
   - Accuracy improvements
   - Performance metrics
2. **Enrichment Results**
   - External data integrated
   - Validation statistics
   - Coverage improvements
3. **Visualization Tools**
   - Screenshots/demos
   - User guide
   - Use cases
4. **Future Roadmap**
   - Remaining gaps
   - Suggested features
   - Maintenance plan

## Example Code Snippets

### Enhanced Extraction Prompts
```python
# extraction/specialized_prompts.py

EQUIPMENT_EXTRACTION_PROMPT = """
Extract musical equipment and gear mentioned in this text about metal music.
Focus on:
- Guitar types (7-string, 8-string, baritone)
- Pedals and effects (Boss HM-2, etc.)
- Amplifiers and cabinets
- Recording equipment
- Special techniques requiring specific gear

Return as JSON with confidence scores:
{
  "equipment": [
    {
      "name": "Boss HM-2",
      "type": "distortion pedal",
      "manufacturer": "Boss",
      "associated_bands": ["Entombed", "Dismember"],
      "significance": "Swedish death metal chainsaw sound",
      "confidence": 0.95
    }
  ]
}
"""

MOVEMENT_EXTRACTION_PROMPT = """
Identify musical movements and scenes in this text.
Look for:
- Named movements (NWOBHM, Bay Area thrash)
- Geographic scenes
- Time periods
- Key bands and venues
- Cultural significance

Return detailed movement data with relationships.
"""
```

### Confidence Scoring
```python
class ConfidenceScorer:
    def __init__(self):
        self.patterns = {
            'high_confidence': [
                r'formed in \d{4}',
                r'released .* album',
                r'member of',
                r'pioneered'
            ],
            'medium_confidence': [
                r'influenced by',
                r'similar to',
                r'emerged from'
            ],
            'low_confidence': [
                r'possibly',
                r'might have',
                r'some say'
            ]
        }
    
    def score_extraction(self, entity, context):
        score = 0.5  # baseline
        
        # Check pattern matches
        for pattern in self.patterns['high_confidence']:
            if re.search(pattern, context, re.I):
                score += 0.1
        
        # Check entity completeness
        if hasattr(entity, 'formed_year') and entity.formed_year:
            score += 0.1
        
        return min(score, 1.0)
```

### External Data Integration
```python
import wikipediaapi
from musicbrainzngs import set_useragent, search_artists

class DataEnricher:
    def __init__(self):
        self.wiki = wikipediaapi.Wikipedia('MetalHistoryBot/1.0')
        set_useragent("MetalHistory", "1.0", "metal@history.com")
    
    def enrich_band(self, band_name):
        enriched_data = {}
        
        # Wikipedia data
        page = self.wiki.page(f"{band_name} (band)")
        if page.exists():
            enriched_data['wikipedia'] = {
                'summary': page.summary[:500],
                'url': page.fullurl,
                'categories': [cat for cat in page.categories]
            }
        
        # MusicBrainz data
        result = search_artists(artist=band_name, limit=1)
        if result['artist-list']:
            artist = result['artist-list'][0]
            enriched_data['musicbrainz'] = {
                'id': artist['id'],
                'disambiguation': artist.get('disambiguation', ''),
                'life_span': artist.get('life-span', {}),
                'area': artist.get('area', {}).get('name', '')
            }
        
        return enriched_data
```

### Interactive Visualization
```python
import streamlit as st
import plotly.graph_objects as go
from pyvis.network import Network

def create_dashboard():
    st.title("Metal History Knowledge Graph Explorer")
    
    # Sidebar controls
    view_type = st.sidebar.selectbox(
        "View Type",
        ["Graph Network", "Timeline", "Geographic Map", "Genre Tree"]
    )
    
    if view_type == "Graph Network":
        show_band_network()
    elif view_type == "Timeline":
        show_timeline()
    elif view_type == "Geographic Map":
        show_geographic_distribution()
    elif view_type == "Genre Tree":
        show_genre_evolution()

def show_band_network():
    # Interactive network visualization
    center_band = st.text_input("Center Band", "Black Sabbath")
    depth = st.slider("Relationship Depth", 1, 3, 2)
    
    net = Network(height="600px", width="100%")
    # Build network from graph data
    # ... network building code ...
    
    # Display
    net.save_graph("temp.html")
    with open("temp.html", "r") as f:
        html = f.read()
    st.components.v1.html(html, height=600)

def show_timeline():
    # Timeline visualization with Plotly
    fig = go.Figure()
    
    # Add band formation events
    bands_data = get_bands_by_year()
    fig.add_trace(go.Scatter(
        x=bands_data['years'],
        y=bands_data['counts'],
        mode='lines+markers',
        name='Bands Formed'
    ))
    
    st.plotly_chart(fig)
```

### Feedback Loop Implementation
```python
class ExtractionFeedback:
    def __init__(self):
        self.feedback_db = "feedback.json"
        self.load_feedback()
    
    def record_correction(self, original, corrected, context):
        """Record manual corrections for learning"""
        self.feedback.append({
            'timestamp': datetime.now().isoformat(),
            'original': original,
            'corrected': corrected,
            'context': context
        })
        self.save_feedback()
    
    def apply_learned_patterns(self, extraction_result):
        """Apply previously learned corrections"""
        for item in self.feedback:
            if similar_context(extraction_result.context, item['context']):
                extraction_result = apply_correction(extraction_result, item)
        return extraction_result
```

## Priority Improvements
1. **Equipment & Gear** - Critical for technical accuracy
2. **Movements & Scenes** - Essential for historical context
3. **Geographic Data** - Important for scene analysis
4. **Production Styles** - Valuable for sonic evolution
5. **Platform/Technology** - Modern relevance

## Timeline
- Day 1: Design enhanced extraction prompts
- Day 2: Implement enrichment tools
- Day 3: Build visualization dashboard
- Day 4: Test improvements and document

Focus on measurable improvements and document all design decisions!