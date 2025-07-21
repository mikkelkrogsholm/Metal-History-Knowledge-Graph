"""
GraphQL API for Metal History Knowledge Graph
Provides flexible querying capabilities for complex relationships
"""

from ariadne import QueryType, ObjectType, make_executable_schema, graphql_sync
from ariadne.asgi import GraphQL
from typing import Dict, List, Any, Optional
import json

# Import database connection from main API
from metal_graph_api import DatabaseConnection

# GraphQL schema definition
type_defs = """
type Query {
    # Band queries
    band(id: ID!): Band
    bands(limit: Int = 10, offset: Int = 0, genre: String): [Band!]!
    searchBands(query: String!, limit: Int = 10): [Band!]!
    
    # Album queries
    album(id: ID!): Album
    albums(limit: Int = 10, year: Int, bandId: ID): [Album!]!
    
    # Person queries
    person(id: ID!): Person
    people(limit: Int = 10, instrument: String): [Person!]!
    
    # Genre queries
    genre(name: String!): Genre
    genres: [Genre!]!
    genreEvolution(genreName: String!): GenreEvolution
    
    # Timeline queries
    timeline(startYear: Int!, endYear: Int!): [TimelineEvent!]!
    
    # Network queries
    influenceNetwork(bandId: ID!, depth: Int = 2): InfluenceNetwork
    collaborationNetwork(personId: ID!): CollaborationNetwork
    
    # Statistics
    statistics: DatabaseStats
}

type Band {
    id: ID!
    name: String!
    formedYear: Int
    originLocation: GeographicLocation
    description: String
    genres: [Genre!]!
    members(active: Boolean): [Person!]!
    formerMembers: [Person!]!
    albums: [Album!]!
    songs: [Song!]!
    influencedBy: [Band!]!
    influenced: [Band!]!
    similarBands(limit: Int = 5): [SimilarBand!]!
}

type Album {
    id: ID!
    title: String!
    releaseYear: Int
    band: Band!
    songs: [Song!]!
    genres: [Genre!]!
    personnel: [AlbumPersonnel!]!
}

type Song {
    id: ID!
    title: String!
    duration: Int
    album: Album
    band: Band
    writers: [Person!]!
}

type Person {
    id: ID!
    name: String!
    birthYear: Int
    deathYear: Int
    instruments: [Instrument!]!
    bands: [BandMembership!]!
    albumCredits: [Album!]!
    songCredits: [Song!]!
    collaborators: [Person!]!
}

type Genre {
    name: String!
    description: String
    parentGenre: Genre
    subgenres: [Genre!]!
    bands(limit: Int = 10): [Band!]!
    originYear: Int
    originLocation: GeographicLocation
}

type GeographicLocation {
    id: ID!
    name: String!
    city: String
    state: String
    country: String!
    bands: [Band!]!
    venues: [Venue!]!
}

type Instrument {
    name: String!
    category: String
    players(limit: Int = 10): [Person!]!
}

type BandMembership {
    band: Band!
    startYear: Int
    endYear: Int
    active: Boolean!
    instruments: [Instrument!]!
}

type AlbumPersonnel {
    person: Person!
    roles: [String!]!
}

type SimilarBand {
    band: Band!
    similarityScore: Float!
    commonGenres: [Genre!]!
    reason: String!
}

type TimelineEvent {
    year: Int!
    events: [Event!]!
}

type Event {
    type: String!
    description: String!
    entity: Entity
}

union Entity = Band | Album | Person

type InfluenceNetwork {
    centralBand: Band!
    influences: [InfluenceRelation!]!
    totalBands: Int!
    maxDepth: Int!
}

type InfluenceRelation {
    source: Band!
    target: Band!
    type: String!
    strength: Float
}

type CollaborationNetwork {
    centralPerson: Person!
    collaborations: [Collaboration!]!
    totalPeople: Int!
}

type Collaboration {
    person: Person!
    projects: [CollaborationProject!]!
    strength: Float!
}

type CollaborationProject {
    type: String!
    name: String!
    year: Int
}

type GenreEvolution {
    genre: Genre!
    timeline: [GenreTimelineEntry!]!
    influences: [Genre!]!
    descendants: [Genre!]!
}

type GenreTimelineEntry {
    year: Int!
    bands: [Band!]!
    albums: [Album!]!
    significance: String
}

type DatabaseStats {
    totalBands: Int!
    totalAlbums: Int!
    totalSongs: Int!
    totalPeople: Int!
    totalGenres: Int!
    bandsByDecade: [DecadeStats!]!
    mostConnectedBands: [Band!]!
}

type DecadeStats {
    decade: Int!
    bandCount: Int!
    albumCount: Int!
}
"""

# Create query type and resolvers
query = QueryType()

@query.field("band")
def resolve_band(_, info, id: str):
    """Resolve a single band by ID"""
    db = info.context["db"]
    
    query = """
    MATCH (b:Band {id: $id})
    OPTIONAL MATCH (b)-[:ORIGINATED_IN]->(loc:GeographicLocation)
    RETURN b.id as id, b.name as name, b.formed_year as formed_year,
           b.description as description, loc
    """
    
    result = db.execute_query(query, {"id": id})
    if not result.has_next():
        return None
        
    row = result.get_next()
    return {
        "id": row[0],
        "name": row[1],
        "formedYear": row[2],
        "description": row[3],
        "originLocation": row[4] if row[4] else None
    }

@query.field("bands")
def resolve_bands(_, info, limit: int = 10, offset: int = 0, genre: Optional[str] = None):
    """Resolve multiple bands with optional filtering"""
    db = info.context["db"]
    
    if genre:
        query = """
        MATCH (b:Band)-[:PLAYS_GENRE]->(g:Subgenre {name: $genre})
        RETURN b.id as id, b.name as name, b.formed_year as formed_year
        ORDER BY b.name
        SKIP $offset LIMIT $limit
        """
        params = {"genre": genre, "limit": limit, "offset": offset}
    else:
        query = """
        MATCH (b:Band)
        RETURN b.id as id, b.name as name, b.formed_year as formed_year
        ORDER BY b.name
        SKIP $offset LIMIT $limit
        """
        params = {"limit": limit, "offset": offset}
    
    result = db.execute_query(query, params)
    bands = []
    
    while result.has_next():
        row = result.get_next()
        bands.append({
            "id": row[0],
            "name": row[1],
            "formedYear": row[2]
        })
    
    return bands

@query.field("searchBands")
def resolve_search_bands(_, info, query: str, limit: int = 10):
    """Search bands by name"""
    db = info.context["db"]
    
    search_query = """
    MATCH (b:Band)
    WHERE b.name =~ $pattern
    RETURN b.id as id, b.name as name, b.formed_year as formed_year
    LIMIT $limit
    """
    
    pattern = f".*{query}.*"
    result = db.execute_query(search_query, {"pattern": pattern, "limit": limit})
    
    bands = []
    while result.has_next():
        row = result.get_next()
        bands.append({
            "id": row[0],
            "name": row[1],
            "formedYear": row[2]
        })
    
    return bands

@query.field("genres")
def resolve_genres(_, info):
    """Get all genres"""
    db = info.context["db"]
    
    query = """
    MATCH (g:Subgenre)
    OPTIONAL MATCH (g)<-[:PLAYS_GENRE]-(b:Band)
    WITH g, COUNT(DISTINCT b) as band_count
    ORDER BY g.name
    RETURN g.name as name, g.description as description, band_count
    """
    
    result = db.execute_query(query)
    genres = []
    
    while result.has_next():
        row = result.get_next()
        genres.append({
            "name": row[0],
            "description": row[1],
            "_bandCount": row[2]  # Store for later use
        })
    
    return genres

@query.field("influenceNetwork")
def resolve_influence_network(_, info, bandId: str, depth: int = 2):
    """Get influence network for a band"""
    db = info.context["db"]
    
    # Get central band
    band_query = "MATCH (b:Band {id: $id}) RETURN b"
    band_result = db.execute_query(band_query, {"id": bandId})
    
    if not band_result.has_next():
        return None
    
    central_band = band_result.get_next()[0]
    
    # Get influence relationships up to specified depth
    influence_query = f"""
    MATCH path = (b:Band {{id: $id}})-[:INFLUENCED_BY|INFLUENCED*1..{depth}]-(other:Band)
    WITH relationships(path) as rels, nodes(path) as bands
    UNWIND range(0, length(rels)-1) as idx
    WITH rels[idx] as rel, bands[idx] as source, bands[idx+1] as target
    RETURN DISTINCT 
        source.id as source_id, source.name as source_name,
        target.id as target_id, target.name as target_name,
        type(rel) as rel_type
    """
    
    result = db.execute_query(influence_query, {"id": bandId})
    influences = []
    all_bands = set()
    
    while result.has_next():
        row = result.get_next()
        influences.append({
            "source": {"id": row[0], "name": row[1]},
            "target": {"id": row[2], "name": row[3]},
            "type": row[4],
            "strength": 0.8  # Could calculate based on other factors
        })
        all_bands.add(row[0])
        all_bands.add(row[2])
    
    return {
        "centralBand": {"id": bandId, "name": central_band["name"]},
        "influences": influences,
        "totalBands": len(all_bands),
        "maxDepth": depth
    }

@query.field("statistics")
def resolve_statistics(_, info):
    """Get database statistics"""
    db = info.context["db"]
    
    stats_queries = {
        "totalBands": "MATCH (b:Band) RETURN COUNT(b)",
        "totalAlbums": "MATCH (a:Album) RETURN COUNT(a)",
        "totalSongs": "MATCH (s:Song) RETURN COUNT(s)",
        "totalPeople": "MATCH (p:Person) RETURN COUNT(p)",
        "totalGenres": "MATCH (g:Subgenre) RETURN COUNT(g)"
    }
    
    stats = {}
    for key, q in stats_queries.items():
        result = db.execute_query(q)
        if result.has_next():
            stats[key] = result.get_next()[0]
        else:
            stats[key] = 0
    
    # Get bands by decade
    decade_query = """
    MATCH (b:Band)
    WHERE b.formed_year IS NOT NULL
    WITH floor(b.formed_year / 10) * 10 as decade, COUNT(b) as band_count
    ORDER BY decade
    RETURN decade, band_count
    """
    
    decade_result = db.execute_query(decade_query)
    bands_by_decade = []
    
    while decade_result.has_next():
        row = decade_result.get_next()
        bands_by_decade.append({
            "decade": int(row[0]),
            "bandCount": row[1],
            "albumCount": 0  # Would need another query for this
        })
    
    stats["bandsByDecade"] = bands_by_decade
    stats["mostConnectedBands"] = []  # Would need complex query
    
    return stats

# Object type resolvers
band_type = ObjectType("Band")
album_type = ObjectType("Album")
person_type = ObjectType("Person")
genre_type = ObjectType("Genre")

@band_type.field("genres")
def resolve_band_genres(band, info):
    """Resolve genres for a band"""
    db = info.context["db"]
    
    query = """
    MATCH (b:Band {id: $id})-[:PLAYS_GENRE]->(g:Subgenre)
    RETURN g.name as name, g.description as description
    """
    
    result = db.execute_query(query, {"id": band["id"]})
    genres = []
    
    while result.has_next():
        row = result.get_next()
        genres.append({
            "name": row[0],
            "description": row[1]
        })
    
    return genres

@band_type.field("albums")
def resolve_band_albums(band, info):
    """Resolve albums for a band"""
    db = info.context["db"]
    
    query = """
    MATCH (b:Band {id: $id})-[:RELEASED]->(a:Album)
    RETURN a.id as id, a.title as title, a.release_year as release_year
    ORDER BY a.release_year
    """
    
    result = db.execute_query(query, {"id": band["id"]})
    albums = []
    
    while result.has_next():
        row = result.get_next()
        albums.append({
            "id": row[0],
            "title": row[1],
            "releaseYear": row[2]
        })
    
    return albums

@band_type.field("members")
def resolve_band_members(band, info, active: Optional[bool] = None):
    """Resolve members for a band"""
    db = info.context["db"]
    
    if active is None:
        query = """
        MATCH (p:Person)-[:MEMBER_OF]->(b:Band {id: $id})
        RETURN p.id as id, p.name as name
        """
    else:
        # Would need active status in relationship
        query = """
        MATCH (p:Person)-[r:MEMBER_OF]->(b:Band {id: $id})
        RETURN p.id as id, p.name as name
        """
    
    result = db.execute_query(query, {"id": band["id"]})
    members = []
    
    while result.has_next():
        row = result.get_next()
        members.append({
            "id": row[0],
            "name": row[1]
        })
    
    return members

@band_type.field("influencedBy")
def resolve_band_influenced_by(band, info):
    """Resolve bands that influenced this band"""
    db = info.context["db"]
    
    query = """
    MATCH (b:Band {id: $id})-[:INFLUENCED_BY]->(influenced:Band)
    RETURN influenced.id as id, influenced.name as name
    """
    
    result = db.execute_query(query, {"id": band["id"]})
    bands = []
    
    while result.has_next():
        row = result.get_next()
        bands.append({
            "id": row[0],
            "name": row[1]
        })
    
    return bands

@band_type.field("influenced")
def resolve_band_influenced(band, info):
    """Resolve bands influenced by this band"""
    db = info.context["db"]
    
    query = """
    MATCH (b:Band {id: $id})<-[:INFLUENCED_BY]-(influenced:Band)
    RETURN influenced.id as id, influenced.name as name
    """
    
    result = db.execute_query(query, {"id": band["id"]})
    bands = []
    
    while result.has_next():
        row = result.get_next()
        bands.append({
            "id": row[0],
            "name": row[1]
        })
    
    return bands

# Create executable schema
schema = make_executable_schema(
    type_defs,
    query,
    band_type,
    album_type,
    person_type,
    genre_type
)

# Create GraphQL app
def create_graphql_app(db_connection):
    """Create GraphQL ASGI app with database context"""
    return GraphQL(
        schema,
        debug=True,
        context_value={"db": db_connection}
    )