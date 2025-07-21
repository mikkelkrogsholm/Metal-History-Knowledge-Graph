// Kuzu Database Schema for Metal History
// Node Types Definition

// Core Music Entities
CREATE NODE TABLE Band(
    id INT64,
    name STRING,
    formed_year INT32,
    origin_city STRING,
    origin_country STRING,
    status STRING, // active, disbanded, hiatus
    description STRING,
    embedding DOUBLE[1024], // for vector search using snowflake-arctic-embed2
    PRIMARY KEY (id)
);

CREATE NODE TABLE Person(
    id INT64,
    name STRING,
    birth_year INT32,
    death_year INT32,
    nationality STRING,
    instruments STRING[], // guitar, vocals, bass, drums, etc.
    description STRING,
    embedding DOUBLE[1024],
    PRIMARY KEY (id)
);

CREATE NODE TABLE Album(
    id INT64,
    title STRING,
    release_year INT32,
    release_date DATE,
    label STRING,
    producer STRING,
    studio STRING,
    chart_position INT32,
    description STRING,
    embedding DOUBLE[1024],
    PRIMARY KEY (id)
);

CREATE NODE TABLE Song(
    id INT64,
    title STRING,
    duration_seconds INT32,
    bpm INT32,
    description STRING,
    embedding DOUBLE[1024],
    PRIMARY KEY (id)
);

// Genre and Style
CREATE NODE TABLE Subgenre(
    id INT64,
    name STRING,
    era_start INT32,
    era_end INT32,
    bpm_min INT32,
    bpm_max INT32,
    guitar_tuning STRING,
    vocal_style STRING,
    key_characteristics STRING,
    parent_influences STRING[],
    legacy_impact STRING,
    description STRING,
    embedding DOUBLE[1024],
    PRIMARY KEY (id)
);

CREATE NODE TABLE MusicalCharacteristic(
    id INT64,
    type STRING, // tempo, tuning, technique, production
    value STRING,
    description STRING,
    PRIMARY KEY (id)
);

// Geographic and Temporal
CREATE NODE TABLE GeographicLocation(
    id INT64,
    city STRING,
    region STRING,
    country STRING,
    scene_description STRING,
    cultural_context STRING,
    embedding DOUBLE[1024],
    PRIMARY KEY (id)
);

CREATE NODE TABLE Era(
    id INT64,
    name STRING,
    start_year INT32,
    end_year INT32,
    description STRING,
    cultural_context STRING,
    technological_context STRING,
    embedding DOUBLE[1024],
    PRIMARY KEY (id)
);

// Cultural and Industry
CREATE NODE TABLE RecordLabel(
    id INT64,
    name STRING,
    founded_year INT32,
    location STRING,
    description STRING,
    PRIMARY KEY (id)
);

CREATE NODE TABLE Studio(
    id INT64,
    name STRING,
    location STRING,
    famous_for STRING,
    description STRING,
    PRIMARY KEY (id)
);

CREATE NODE TABLE CulturalEvent(
    id INT64,
    name STRING,
    date DATE,
    type STRING, // festival, controversy, movement
    impact STRING,
    description STRING,
    embedding DOUBLE[1024],
    PRIMARY KEY (id)
);

CREATE NODE TABLE MediaOutlet(
    id INT64,
    name STRING,
    type STRING, // magazine, tv_show, website, documentary
    active_years STRING,
    description STRING,
    PRIMARY KEY (id)
);

// Relationship Types Definition

// Band Relationships
CREATE REL TABLE FORMED_IN(FROM Band TO GeographicLocation);
CREATE REL TABLE PLAYS_GENRE(FROM Band TO Subgenre, is_primary BOOLEAN DEFAULT false);
CREATE REL TABLE RELEASED(FROM Band TO Album, release_order INT32);
CREATE REL TABLE ACTIVE_DURING(FROM Band TO Era);

// Person Relationships
CREATE REL TABLE MEMBER_OF(FROM Person TO Band, 
    role STRING, 
    join_year INT32, 
    leave_year INT32,
    is_founding_member BOOLEAN DEFAULT false
);
CREATE REL TABLE PRODUCED(FROM Person TO Album);
CREATE REL TABLE PERFORMED_ON(FROM Person TO Album, instruments STRING[]);

// Album/Song Relationships
CREATE REL TABLE CONTAINS_TRACK(FROM Album TO Song, track_number INT32);
CREATE REL TABLE RECORDED_AT(FROM Album TO Studio);
CREATE REL TABLE RELEASED_BY(FROM Album TO RecordLabel);
CREATE REL TABLE REPRESENTS_GENRE(FROM Album TO Subgenre, is_seminal BOOLEAN DEFAULT false);

// Genre Evolution
CREATE REL TABLE INFLUENCED_BY(FROM Subgenre TO Subgenre, influence_type STRING);
CREATE REL TABLE EVOLVED_INTO(FROM Subgenre TO Subgenre);
CREATE REL TABLE ORIGINATED_IN(FROM Subgenre TO GeographicLocation);
CREATE REL TABLE EMERGED_DURING(FROM Subgenre TO Era);

// Geographic Scene Relationships
CREATE REL TABLE SCENE_SPAWNED(FROM GeographicLocation TO Band);
CREATE REL TABLE SCENE_DEVELOPED(FROM GeographicLocation TO Subgenre);

// Cultural Impact
CREATE REL TABLE DOCUMENTED_IN(FROM Band TO MediaOutlet);
CREATE REL TABLE FEATURED_IN(FROM Album TO MediaOutlet);
CREATE REL TABLE PARTICIPATED_IN(FROM Band TO CulturalEvent);
CREATE REL TABLE INFLUENCED_EVENT(FROM Band TO CulturalEvent);

// Musical Characteristics
CREATE REL TABLE HAS_CHARACTERISTIC(FROM Subgenre TO MusicalCharacteristic);
CREATE REL TABLE USES_TECHNIQUE(FROM Band TO MusicalCharacteristic);
CREATE REL TABLE ALBUM_FEATURES(FROM Album TO MusicalCharacteristic);

// Cross-references for text extraction
CREATE REL TABLE MENTIONED_WITH(FROM Band TO Band, context STRING, source_paragraph INT32);
CREATE REL TABLE CONTEMPORARY_OF(FROM Band TO Band);
CREATE REL TABLE CITATION(
    FROM Band TO Album,
    quote STRING,
    context STRING,
    source_paragraph INT32
);