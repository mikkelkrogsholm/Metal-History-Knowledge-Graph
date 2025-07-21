"""
Specialized extraction prompts for missing entity types in metal history
"""

# Equipment extraction prompt
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

Text to analyze:
{text}
"""

# Movement extraction prompt
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

Text to analyze:
{text}
"""

# Production style extraction prompt
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

Text to analyze:
{text}
"""

# Venue extraction prompt
VENUE_EXTRACTION_PROMPT = """
You are an expert at identifying important venues in metal history.

Extract ALL venues mentioned including:
1. RECORD SHOPS: Helvete, specialty metal shops
2. CLUBS: CBGB, L'Amour, specific metal venues
3. FESTIVAL GROUNDS: Wacken location, Download sites
4. STUDIOS: Recording studios that became scene centers
5. REHEARSAL SPACES: Important practice venues

For each venue:
- name: Full venue name
- type: Category (record_shop/club/festival_ground/studio/rehearsal_space)
- location: City and address if mentioned
- active_years: When it was operational
- significance: Why it's important to metal history
- associated_bands: Bands that played/recorded there
- associated_movements: Scenes centered around it
- notable_events: Important shows or incidents

Context clues:
- "played at"
- "recorded at"
- "centered around"
- "scene headquarters"
- "gathered at"
- Geographic references
- "landmark venue"

Text to analyze:
{text}
"""

# Platform extraction prompt
PLATFORM_EXTRACTION_PROMPT = """
You are an expert at identifying technology platforms and media in metal history.

Extract ALL platforms and technologies including:
1. SOCIAL MEDIA: MySpace, Facebook, TikTok, Instagram
2. STREAMING: Spotify, Apple Music, Bandcamp
3. RECORDING SOFTWARE: Pro Tools, Logic, Cubase
4. VIDEO PLATFORMS: YouTube, MTV, Headbangers Ball
5. DISTRIBUTION: File sharing, torrents, physical media
6. COMMUNICATION: Forums, IRC, Discord

For each platform:
- name: Platform name
- type: Category (social_media/streaming/recording/video/distribution/communication)
- active_period: When it was relevant to metal
- impact: How it changed metal culture/business
- key_artists: Artists who leveraged it successfully
- metrics: User numbers, view counts if mentioned
- innovations: New possibilities it enabled

Look for:
- "promoted on"
- "went viral on"
- "recorded with"
- "distributed through"
- Technology brand names
- Social media references
- Digital transformation mentions

Text to analyze:
{text}
"""

# Technical detail extraction prompt
TECHNICAL_DETAIL_EXTRACTION_PROMPT = """
You are an expert at identifying technical specifications in metal music.

Extract ALL technical details including:
1. GUITAR SPECS: String gauges (.009-.042), scale lengths, tunings
2. TEMPO/TIMING: BPM ranges, blast beat speeds, time signatures
3. FREQUENCY: Hz tunings (A=440Hz vs A=432Hz), sub-bass frequencies
4. RECORDING SPECS: Bit rates, sample rates, tape speeds
5. AMPLIFICATION: Wattage, impedance, gain settings

For each technical detail:
- type: Category of specification
- specification: Exact technical value
- context: What it applies to (genre, band, song)
- significance: Why this spec matters
- comparison: How it differs from standard

Look for:
- Numbers with units
- Technical measurements
- Specification listings
- Gear settings
- Recording parameters
- Tuning references

Text to analyze:
{text}
"""

# Academic resource extraction prompt
ACADEMIC_RESOURCE_EXTRACTION_PROMPT = """
You are an expert at identifying academic and research resources about metal.

Extract ALL academic resources including:
1. BOOKS: Academic texts, histories, analyses
2. JOURNALS: Music journals, metal studies publications
3. DOCUMENTARIES: Films about metal history/culture
4. ORGANIZATIONS: Metal studies groups, research centers
5. CONFERENCES: Academic metal conferences

For each resource:
- title: Full title
- author: Author(s) or creator(s)
- year: Publication/release year
- type: Category (book/journal/documentary/organization/conference)
- focus: Main topic or aspect covered
- publisher: Publishing entity if mentioned
- significance: Contribution to metal scholarship

Look for:
- "published"
- "documented in"
- "study of"
- "research"
- Author citations
- Book/film titles in quotes or italics
- Academic terminology

Text to analyze:
{text}
"""

# Compilation extraction prompt
COMPILATION_EXTRACTION_PROMPT = """
You are an expert at identifying compilation albums in metal history.

Extract ALL compilation albums including:
1. SCENE COMPILATIONS: Metal for Muthas, local scene samplers
2. LABEL SAMPLERS: Record label compilations
3. TRIBUTE ALBUMS: Band tribute compilations
4. GENRE COLLECTIONS: Best of death metal, etc.
5. HISTORICAL RETROSPECTIVES: Decade collections

For each compilation:
- title: Full compilation title
- release_year: When it was released
- label: Record label if mentioned
- featured_bands: List of bands included
- significance: Why it's historically important
- associated_movement: Scene or movement it represents
- compiler: Who curated it if mentioned

Look for:
- "compilation"
- "various artists"
- "sampler"
- "collection"
- "featuring"
- Multiple band listings
- Scene documentation references

Text to analyze:
{text}
"""

# Viral phenomenon extraction prompt
VIRAL_PHENOMENON_EXTRACTION_PROMPT = """
You are an expert at identifying viral and internet phenomena in metal.

Extract ALL viral phenomena including:
1. HASHTAGS: #Metaltok, genre-specific tags
2. VIRAL VIDEOS: Specific songs/performances that went viral
3. MEMES: Metal-related internet memes
4. CHALLENGES: TikTok challenges, social media trends
5. VIRAL MOMENTS: Specific incidents that spread online

For each phenomenon:
- name: Hashtag, video title, or description
- platform: Where it went viral
- year: When it happened
- metrics: View counts, share numbers if mentioned
- participating_artists: Bands/artists involved
- impact: Effect on metal culture or specific artists
- duration: How long it remained relevant

Look for:
- "#" hashtags
- "went viral"
- "millions of views"
- "TikTok trend"
- Social media platform mentions
- View/share counts
- "internet sensation"

Text to analyze:
{text}
"""

# Web3 project extraction prompt
WEB3_PROJECT_EXTRACTION_PROMPT = """
You are an expert at identifying Web3 and blockchain projects in metal.

Extract ALL Web3 projects including:
1. NFT COLLECTIONS: Band NFTs, artwork collections
2. VIRTUAL BANDS: AI or metaverse bands
3. BLOCKCHAIN ALBUMS: Releases on blockchain
4. CRYPTO TOKENS: Band-specific cryptocurrencies
5. METAVERSE VENUES: Virtual concert spaces

For each project:
- name: Project name
- type: Category (NFT/virtual_band/blockchain_album/token/metaverse)
- launch_year: When it launched
- band_or_creator: Who created it
- unique_items: Number of NFTs/tokens if mentioned
- platform: Blockchain or metaverse platform used
- innovation: What makes it notable

Look for:
- "NFT"
- "blockchain"
- "cryptocurrency"
- "metaverse"
- "virtual"
- "Web3"
- Digital collectible references

Text to analyze:
{text}
"""

# Combined prompt for full extraction
def create_combined_extraction_prompt(text: str) -> str:
    """Create a comprehensive prompt that extracts all entity types"""
    return f"""
You are an expert at extracting ALL types of entities from metal history texts.

Extract the following entity types from the text:

1. EQUIPMENT: Guitars, pedals, amps, recording gear (Boss HM-2, 8-string guitars, etc.)
2. MOVEMENTS: Musical movements and scenes (NWOBHM, Bay Area thrash, etc.)
3. PRODUCTION STYLES: Named sounds and production techniques (Swedish death metal sound, etc.)
4. VENUES: Clubs, record shops, studios (Helvete, CBGB, etc.)
5. PLATFORMS: Technology and media (MySpace, Pro Tools, TikTok, etc.)
6. TECHNICAL DETAILS: Specifications and measurements (string gauges, BPM, tunings)
7. ACADEMIC RESOURCES: Books, documentaries, research
8. COMPILATIONS: Important compilation albums
9. VIRAL PHENOMENA: Hashtags, viral videos, memes
10. WEB3 PROJECTS: NFTs, blockchain, metaverse projects

Also continue extracting standard entities:
- Bands, People, Albums, Songs, Subgenres, Locations, Events, Studios, Labels

Be extremely thorough and extract ALL entities with their full context and relationships.

Text to analyze:
{text}
"""