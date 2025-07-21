// Enhanced Kuzu Database Schema for Metal History
// Additional entities and relationships identified from the document

// Additional Node Types

// Specific movements and waves
CREATE NODE TABLE Movement(
    id INT64,
    name STRING, // NWOBHM, Proto-metal, etc.
    start_year INT32,
    end_year INT32,
    description STRING,
    estimated_bands INT32, // e.g., "1000+ bands" for NWOBHM
    key_compilation STRING, // e.g., "Metal for Muthas"
    embedding DOUBLE[1024], // snowflake-arctic-embed2 dimensions
    PRIMARY KEY (id)
);

// Technical specifications
CREATE NODE TABLE TechnicalDetail(
    id INT64,
    type STRING, // guitar_strings, scale_length, pedal, etc.
    specification STRING, // ".009-.042", "29.4 inches", "Boss HM-2"
    context STRING,
    PRIMARY KEY (id)
);

// Online platforms and technology
CREATE NODE TABLE Platform(
    id INT64,
    name STRING, // MySpace, TikTok, Pro Tools, etc.
    type STRING, // social_media, recording_software, streaming
    active_period STRING,
    impact STRING,
    PRIMARY KEY (id)
);

// Specific equipment/gear
CREATE NODE TABLE Equipment(
    id INT64,
    name STRING, // Boss HM-2, 8-string guitar, etc.
    type STRING, // pedal, guitar, amp_simulator
    manufacturer STRING,
    specifications STRING,
    PRIMARY KEY (id)
);

// Academic/Research entities
CREATE NODE TABLE AcademicResource(
    id INT64,
    title STRING,
    author STRING,
    year INT32,
    type STRING, // book, journal, documentary, organization
    description STRING,
    PRIMARY KEY (id)
);

// Hashtags and viral phenomena
CREATE NODE TABLE ViralPhenomenon(
    id INT64,
    name STRING, // #Metaltok, specific viral songs
    platform STRING,
    view_count INT64,
    video_count INT32,
    year INT32,
    PRIMARY KEY (id)
);

// NFT/Web3 projects
CREATE NODE TABLE Web3Project(
    id INT64,
    name STRING,
    type STRING, // NFT band, virtual concert
    unique_items INT32,
    launch_year INT32,
    description STRING,
    PRIMARY KEY (id)
);

// Production techniques
CREATE NODE TABLE ProductionStyle(
    id INT64,
    name STRING, // "Florida death metal sound", "buzzsaw sound"
    producer STRING,
    studio STRING,
    key_techniques STRING,
    description STRING,
    PRIMARY KEY (id)
);

// Compilation albums
CREATE NODE TABLE Compilation(
    id INT64,
    title STRING,
    release_year INT32,
    significance STRING,
    PRIMARY KEY (id)
);

// Additional Relationship Types

// Movement relationships
CREATE REL TABLE PART_OF_MOVEMENT(FROM Band TO Movement);
CREATE REL TABLE MOVEMENT_IN_ERA(FROM Movement TO Era);
CREATE REL TABLE MOVEMENT_SPAWNED_GENRE(FROM Movement TO Subgenre);

// Technical relationships
CREATE REL TABLE USES_EQUIPMENT(FROM Band TO Equipment, notable_for STRING);
CREATE REL TABLE REQUIRES_TECHNICAL(FROM Subgenre TO TechnicalDetail);
CREATE REL TABLE INNOVATED_TECHNIQUE(FROM Person TO TechnicalDetail, year INT32);

// Platform relationships
CREATE REL TABLE PROMOTED_ON(FROM Band TO Platform, success_metric STRING);
CREATE REL TABLE ENABLED_BY(FROM Band TO Platform, year INT32);
CREATE REL TABLE WENT_VIRAL(FROM Song TO ViralPhenomenon);

// Production relationships
CREATE REL TABLE PRODUCED_WITH_STYLE(FROM Album TO ProductionStyle);
CREATE REL TABLE PIONEERED_PRODUCTION(FROM Person TO ProductionStyle);
CREATE REL TABLE STUDIO_KNOWN_FOR(FROM Studio TO ProductionStyle);

// Compilation relationships
CREATE REL TABLE FEATURED_ON_COMPILATION(FROM Band TO Compilation);
CREATE REL TABLE COMPILATION_REPRESENTS(FROM Compilation TO Movement);

// Academic relationships
CREATE REL TABLE STUDIED_IN(FROM Subgenre TO AcademicResource);
CREATE REL TABLE DOCUMENTED_BY(FROM Movement TO AcademicResource);

// Web3 relationships
CREATE REL TABLE LAUNCHED_WEB3(FROM Band TO Web3Project);

// Additional relationship properties for existing relationships

// Enhanced MEMBER_OF to include specific incidents
CREATE REL TABLE CONFLICT_WITH(FROM Person TO Person, 
    type STRING, // murder, dispute, etc.
    year INT32,
    outcome STRING
);

// Regional variations
CREATE REL TABLE REGIONAL_VARIANT(FROM Subgenre TO GeographicLocation,
    variant_name STRING, // "Bay Area thrash", "Teutonic thrash"
    characteristics STRING
);

// Industry milestones
CREATE REL TABLE ACHIEVED_MILESTONE(FROM Band TO CulturalEvent,
    type STRING, // first_to, breakthrough, etc.
    significance STRING
);

// Song-specific achievements
CREATE REL TABLE SONG_MILESTONE(FROM Song TO Platform,
    achievement STRING, // "300,000+ videos", "Billboard success"
    metric_value STRING,
    year INT32
);

// Producer relationships expanded
CREATE REL TABLE STANDARDIZED_SOUND(FROM Person TO Subgenre,
    studio STRING,
    years_active STRING
);

// Parent genre relationships
CREATE REL TABLE PARENT_GENRE(FROM Subgenre TO Subgenre,
    influence_percentage INT32 // rough estimate of influence
);

// Hybrid genre creation
CREATE REL TABLE FUSION_OF(FROM Subgenre TO Subgenre,
    fusion_name STRING,
    year_emerged INT32
);

// Marketing/promotional relationships
CREATE REL TABLE MARKETING_CAMPAIGN(FROM Band TO Band,
    campaign_name STRING, // "funeral for nu-metal"
    year INT32,
    impact STRING
);

// Venue/Shop relationships  
CREATE NODE TABLE Venue(
    id INT64,
    name STRING, // Helvete record shop
    type STRING, // record_shop, club, festival_ground
    location STRING,
    significance STRING,
    active_years STRING,
    PRIMARY KEY (id)
);

CREATE REL TABLE CENTERED_AROUND(FROM Movement TO Venue);
CREATE REL TABLE VENUE_HOSTED(FROM Venue TO Band);

// Index creation for performance
CREATE INDEX idx_band_name ON Band(name);
CREATE INDEX idx_album_title ON Album(title);
CREATE INDEX idx_person_name ON Person(name);
CREATE INDEX idx_subgenre_name ON Subgenre(name);
CREATE INDEX idx_location_city ON GeographicLocation(city);
CREATE INDEX idx_song_title ON Song(title);
CREATE INDEX idx_platform_name ON Platform(name);