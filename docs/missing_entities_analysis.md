# Analysis of Missing Entities from Metal History Document

## Entities now covered in enhanced schema:

### 1. **Movements** (e.g., NWOBHM, Proto-metal)
- Distinct from Subgenres, these are cultural/temporal movements
- Include estimated band counts and key compilations

### 2. **Technical Details**
- String gauges (.009-.042)
- Scale lengths (29.4")
- Specific pedals (Boss HM-2)
- Fanned frets

### 3. **Platforms**
- MySpace (2005-2010)
- TikTok and #Metaltok
- Recording software (Pro Tools, Superior Drummer)
- Streaming services

### 4. **Equipment**
- 8-string guitars
- Specific pedals and gear
- Amp simulators

### 5. **Venues/Shops**
- Helvete record shop (crucial for black metal)
- Specific clubs and festival grounds

### 6. **Production Styles**
- "Florida death metal sound"
- "Stockholm buzzsaw sound"
- Producer-specific techniques

### 7. **Academic Resources**
- Books (Weinstein, Walser)
- Journals (Metal Music Studies)
- Documentaries (Sam Dunn's works)
- Organizations (International Society for Metal Music Studies)

### 8. **Viral Phenomena**
- Specific viral tracks ("Mary On A Cross")
- View counts and metrics
- Platform-specific success

### 9. **Web3/NFT Projects**
- The Shredderz (6,666 NFTs)
- Virtual concerts

### 10. **Compilations**
- "Metal for Muthas" (NWOBHM)
- Other scene-defining compilations

## Enhanced Relationships:

### 1. **Regional Variants**
- Bay Area thrash vs East Coast thrash
- Stockholm death metal vs Gothenburg melodic death
- Teutonic thrash

### 2. **Conflicts/Incidents**
- Euronymous murder by Varg Vikernes
- Band breakups and disputes

### 3. **Marketing Campaigns**
- Killswitch Engage's "funeral for nu-metal"

### 4. **Specific Achievements**
- First bands to do X
- Billboard chart success
- Viral metrics

### 5. **Production Lineages**
- Scott Burns standardizing Florida death metal
- Ross Robinson's nu-metal production style

## Data Extraction Considerations:

### 1. **Temporal Precision**
- Exact dates where available (February 13, 1970)
- Year ranges for movements
- Active periods for venues/platforms

### 2. **Quantitative Data**
- BPM ranges from the comparative table
- View counts (1 billion hashtag views)
- Band counts (1,000+ NWOBHM bands)
- Chart positions

### 3. **Geographic Hierarchies**
- City → Region → Country
- Scene-specific locations (Tampa for death metal)

### 4. **Cross-References**
- Paragraph numbers for citations
- Context preservation for entity extraction

### 5. **Embedding Priorities**
- Full paragraphs for context
- Key characteristics and descriptions
- Cultural and technological context

## Query Examples for Enhanced Schema:

```cypher
// Find all bands that went viral on TikTok
MATCH (b:Band)-[:RELEASED]->(a:Album)-[:CONTAINS_TRACK]->(s:Song)-[:WENT_VIRAL]->(v:ViralPhenomenon)
WHERE v.platform = 'TikTok'
RETURN b.name, s.title, v.view_count

// Trace production style lineages
MATCH (p:Person)-[:PIONEERED_PRODUCTION]->(ps:ProductionStyle)
MATCH (a:Album)-[:PRODUCED_WITH_STYLE]->(ps)
RETURN p.name, ps.name, collect(a.title)

// Find regional metal variants
MATCH (g:GeographicLocation)<-[:REGIONAL_VARIANT]-(s:Subgenre)
RETURN g.city, s.name, s.variant_name

// Academic study connections
MATCH (s:Subgenre)-[:STUDIED_IN]->(ar:AcademicResource)
WHERE ar.type = 'book'
RETURN s.name, ar.title, ar.author
```