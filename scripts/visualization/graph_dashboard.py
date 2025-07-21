#!/usr/bin/env python3
"""
Interactive dashboard for exploring the Metal History Knowledge Graph
Uses Streamlit for the web interface and various visualization libraries
"""

import streamlit as st
import json
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from pathlib import Path
import sys
from datetime import datetime
import networkx as nx
from pyvis.network import Network
import tempfile
import os

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent.parent))

# Try to import kuzu
try:
    import kuzu
    KUZU_AVAILABLE = True
except ImportError:
    KUZU_AVAILABLE = False
    st.warning("Kuzu not available. Install with: pip install kuzu")

# Page configuration
st.set_page_config(
    page_title="Metal History Knowledge Graph Explorer",
    page_icon="🎸",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main {
        padding-top: 2rem;
    }
    .stTabs [data-baseweb="tab-list"] button [data-testid="stMarkdownContainer"] p {
        font-size: 1.2rem;
    }
</style>
""", unsafe_allow_html=True)

class MetalHistoryDashboard:
    """Main dashboard class"""
    
    def __init__(self):
        self.initialize_session_state()
        self.load_data()
    
    def initialize_session_state(self):
        """Initialize session state variables"""
        if 'data_loaded' not in st.session_state:
            st.session_state.data_loaded = False
        if 'selected_entity' not in st.session_state:
            st.session_state.selected_entity = None
        if 'view_depth' not in st.session_state:
            st.session_state.view_depth = 2
    
    def load_data(self):
        """Load data from JSON files or Kuzu database"""
        if st.session_state.data_loaded:
            return
        
        # Sidebar for data source selection
        st.sidebar.title("Data Source")
        data_source = st.sidebar.selectbox(
            "Select data source",
            ["JSON Files", "Kuzu Database"] if KUZU_AVAILABLE else ["JSON Files"]
        )
        
        if data_source == "JSON Files":
            json_file = st.sidebar.file_uploader(
                "Upload extracted entities JSON",
                type=['json']
            )
            
            if json_file:
                data = json.load(json_file)
                st.session_state.entities = data.get('entities', data)
                st.session_state.data_loaded = True
                st.sidebar.success("Data loaded successfully!")
        
        elif data_source == "Kuzu Database":
            db_path = st.sidebar.text_input(
                "Database path",
                value="../../schema/metal_history.db"
            )
            
            if st.sidebar.button("Connect to Database"):
                try:
                    self.connect_to_kuzu(db_path)
                    st.session_state.data_loaded = True
                    st.sidebar.success("Connected to database!")
                except Exception as e:
                    st.sidebar.error(f"Error connecting to database: {e}")
    
    def connect_to_kuzu(self, db_path: str):
        """Connect to Kuzu database and load data"""
        db = kuzu.Database(db_path)
        conn = kuzu.Connection(db)
        
        # Load entities from database
        # This is a simplified version - you'd need actual queries
        st.session_state.entities = {
            'bands': [],
            'people': [],
            'albums': [],
            'movements': [],
            'venues': []
        }
        
        # Example query (adjust based on actual schema)
        # result = conn.execute("MATCH (b:Band) RETURN b LIMIT 100")
        # while result.has_next():
        #     st.session_state.entities['bands'].append(result.get_next())
    
    def render_dashboard(self):
        """Main dashboard rendering"""
        st.title("🎸 Metal History Knowledge Graph Explorer")
        
        if not st.session_state.data_loaded:
            st.info("Please load data using the sidebar.")
            return
        
        # Create tabs for different views
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "📊 Overview", 
            "🕸️ Network Graph", 
            "📅 Timeline", 
            "🗺️ Geographic Map",
            "🔍 Entity Explorer"
        ])
        
        with tab1:
            self.render_overview()
        
        with tab2:
            self.render_network_graph()
        
        with tab3:
            self.render_timeline()
        
        with tab4:
            self.render_geographic_map()
        
        with tab5:
            self.render_entity_explorer()
    
    def render_overview(self):
        """Render overview statistics"""
        st.header("Knowledge Graph Overview")
        
        entities = st.session_state.entities
        
        # Entity counts
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Bands", len(entities.get('bands', [])))
        with col2:
            st.metric("People", len(entities.get('people', [])))
        with col3:
            st.metric("Albums", len(entities.get('albums', [])))
        with col4:
            st.metric("Venues", len(entities.get('venues', [])))
        
        # Additional metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Movements", len(entities.get('movements', [])))
        with col2:
            st.metric("Subgenres", len(entities.get('subgenres', [])))
        with col3:
            st.metric("Equipment", len(entities.get('equipment', [])))
        with col4:
            st.metric("Events", len(entities.get('events', [])))
        
        # Charts
        st.subheader("Entity Distribution")
        
        # Pie chart of entity types
        entity_counts = {
            k: len(v) for k, v in entities.items() 
            if isinstance(v, list) and len(v) > 0
        }
        
        if entity_counts:
            fig = px.pie(
                values=list(entity_counts.values()),
                names=list(entity_counts.keys()),
                title="Distribution of Entity Types"
            )
            st.plotly_chart(fig, use_container_width=True)
        
        # Bands by country
        if 'bands' in entities and entities['bands']:
            bands_df = pd.DataFrame(entities['bands'])
            if 'origin_country' in bands_df.columns:
                country_counts = bands_df['origin_country'].value_counts().head(10)
                
                fig = px.bar(
                    x=country_counts.values,
                    y=country_counts.index,
                    orientation='h',
                    title="Top 10 Countries by Number of Bands",
                    labels={'x': 'Number of Bands', 'y': 'Country'}
                )
                st.plotly_chart(fig, use_container_width=True)
    
    def render_network_graph(self):
        """Render interactive network graph"""
        st.header("Entity Relationship Network")
        
        # Controls
        col1, col2, col3 = st.columns(3)
        
        with col1:
            center_type = st.selectbox(
                "Center Entity Type",
                ["Band", "Person", "Movement", "Venue"]
            )
        
        entities = st.session_state.entities
        entity_map = {
            'Band': entities.get('bands', []),
            'Person': entities.get('people', []),
            'Movement': entities.get('movements', []),
            'Venue': entities.get('venues', [])
        }
        
        with col2:
            entity_list = entity_map.get(center_type, [])
            if entity_list:
                entity_names = [e.get('name', e.get('title', 'Unknown')) for e in entity_list]
                selected_entity = st.selectbox("Select Entity", entity_names)
            else:
                selected_entity = None
                st.warning(f"No {center_type} entities found")
        
        with col3:
            depth = st.slider("Relationship Depth", 1, 3, 2)
        
        if st.button("Generate Network") and selected_entity:
            self.create_network_visualization(center_type, selected_entity, depth)
    
    def create_network_visualization(self, entity_type: str, entity_name: str, depth: int):
        """Create network visualization using PyVis"""
        net = Network(height="600px", width="100%", bgcolor="#222222", font_color="white")
        
        # Add central node
        net.add_node(
            entity_name,
            label=entity_name,
            color="#ff0000",
            size=30,
            title=f"{entity_type}: {entity_name}"
        )
        
        # Add related entities (simplified - would need actual relationship data)
        entities = st.session_state.entities
        relationships = entities.get('relationships', [])
        
        # For demo purposes, add some sample relationships
        if entity_type == "Band" and 'people' in entities:
            # Find band members
            for person in entities['people'][:5]:  # Limit for demo
                if entity_name in person.get('associated_bands', []):
                    person_name = person.get('name', 'Unknown')
                    net.add_node(
                        person_name,
                        label=person_name,
                        color="#00ff00",
                        size=20,
                        title=f"Person: {person_name}"
                    )
                    net.add_edge(entity_name, person_name, title="MEMBER_OF")
        
        # Configure physics
        net.set_options("""
        var options = {
          "physics": {
            "enabled": true,
            "solver": "forceAtlas2Based"
          }
        }
        """)
        
        # Save and display
        with tempfile.NamedTemporaryFile(delete=False, suffix=".html") as tmp:
            net.save_graph(tmp.name)
            with open(tmp.name, 'r') as f:
                html = f.read()
            st.components.v1.html(html, height=600)
            os.unlink(tmp.name)
    
    def render_timeline(self):
        """Render timeline visualization"""
        st.header("Metal History Timeline")
        
        entities = st.session_state.entities
        
        # Timeline type selection
        timeline_type = st.selectbox(
            "Timeline View",
            ["Band Formations", "Album Releases", "Movements", "All Events"]
        )
        
        # Create timeline data
        timeline_data = []
        
        if timeline_type == "Band Formations" and 'bands' in entities:
            for band in entities['bands']:
                if band.get('formed_year'):
                    timeline_data.append({
                        'year': band['formed_year'],
                        'event': f"{band['name']} formed",
                        'type': 'Band Formation',
                        'details': band.get('description', '')
                    })
        
        elif timeline_type == "Album Releases" and 'albums' in entities:
            for album in entities['albums']:
                if album.get('release_year'):
                    timeline_data.append({
                        'year': album['release_year'],
                        'event': f"{album['title']} by {album.get('artist', 'Unknown')}",
                        'type': 'Album Release',
                        'details': album.get('description', '')
                    })
        
        elif timeline_type == "Movements" and 'movements' in entities:
            for movement in entities['movements']:
                if movement.get('start_year'):
                    timeline_data.append({
                        'year': movement['start_year'],
                        'event': f"{movement['name']} begins",
                        'type': 'Movement Start',
                        'details': movement.get('characteristics', '')
                    })
        
        if timeline_data:
            # Sort by year
            timeline_data.sort(key=lambda x: x['year'])
            
            # Create timeline chart
            df = pd.DataFrame(timeline_data)
            
            # Group by year for counts
            yearly_counts = df.groupby(['year', 'type']).size().reset_index(name='count')
            
            fig = px.line(
                yearly_counts,
                x='year',
                y='count',
                color='type',
                title=f"{timeline_type} Over Time",
                labels={'count': 'Number of Events', 'year': 'Year'}
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Show recent events
            st.subheader("Recent Events")
            recent = df.nlargest(10, 'year')
            st.dataframe(recent[['year', 'event', 'type']], use_container_width=True)
        else:
            st.info(f"No timeline data available for {timeline_type}")
    
    def render_geographic_map(self):
        """Render geographic visualization"""
        st.header("Geographic Distribution")
        
        entities = st.session_state.entities
        
        # Map type selection
        map_type = st.selectbox(
            "Map View",
            ["Band Origins", "Venues", "Movements"]
        )
        
        if map_type == "Band Origins" and 'bands' in entities:
            # Create country counts
            bands_df = pd.DataFrame(entities['bands'])
            if 'origin_country' in bands_df.columns:
                country_counts = bands_df['origin_country'].value_counts().reset_index()
                country_counts.columns = ['country', 'count']
                
                # Create choropleth map
                fig = px.choropleth(
                    country_counts,
                    locations='country',
                    locationmode='country names',
                    color='count',
                    title="Bands by Country of Origin",
                    color_continuous_scale="Reds",
                    labels={'count': 'Number of Bands'}
                )
                
                st.plotly_chart(fig, use_container_width=True)
                
                # Top countries table
                st.subheader("Top Countries")
                st.dataframe(
                    country_counts.head(10),
                    use_container_width=True
                )
        
        elif map_type == "Venues" and 'venues' in entities:
            st.info("Venue mapping requires geocoding of addresses")
            # Would need geocoding to show venues on map
        
        elif map_type == "Movements" and 'movements' in entities:
            st.info("Movement mapping shows geographic centers of movements")
            # Would need geographic data for movements
    
    def render_entity_explorer(self):
        """Render detailed entity explorer"""
        st.header("Entity Explorer")
        
        entities = st.session_state.entities
        
        # Entity type selection
        entity_type = st.selectbox(
            "Entity Type",
            [k for k, v in entities.items() if isinstance(v, list) and len(v) > 0]
        )
        
        if entity_type:
            entity_list = entities[entity_type]
            
            # Search/filter
            search_term = st.text_input("Search entities", "")
            
            if search_term:
                # Filter entities
                filtered = []
                for entity in entity_list:
                    # Search in various fields
                    searchable = str(entity).lower()
                    if search_term.lower() in searchable:
                        filtered.append(entity)
                entity_list = filtered
            
            # Display count
            st.write(f"Found {len(entity_list)} {entity_type}")
            
            # Pagination
            items_per_page = 20
            num_pages = (len(entity_list) - 1) // items_per_page + 1
            page = st.number_input("Page", min_value=1, max_value=num_pages, value=1)
            
            start_idx = (page - 1) * items_per_page
            end_idx = min(start_idx + items_per_page, len(entity_list))
            
            # Display entities
            for i in range(start_idx, end_idx):
                entity = entity_list[i]
                
                with st.expander(
                    f"{entity.get('name', entity.get('title', f'Entity {i}'))}"
                ):
                    # Display all fields
                    for key, value in entity.items():
                        if value and key not in ['embedding']:  # Skip embeddings
                            st.write(f"**{key}**: {value}")
                    
                    # Action buttons
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button(f"View Network", key=f"net_{entity_type}_{i}"):
                            st.session_state.selected_entity = entity
                            st.info("Switch to Network Graph tab to view")
                    
                    with col2:
                        if st.button(f"View Details", key=f"det_{entity_type}_{i}"):
                            st.json(entity)


def main():
    """Main entry point"""
    dashboard = MetalHistoryDashboard()
    dashboard.render_dashboard()


if __name__ == "__main__":
    main()