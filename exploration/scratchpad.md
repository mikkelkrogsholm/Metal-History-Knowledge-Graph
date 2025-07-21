# Exploration Scratchpad

This document serves as a working notes file for the Metal History Knowledge Graph exploration. All findings, code snippets, observations, and ideas will be documented here as we progress through the exploration plan.

---

## Session Log

### Session 1: Initial Setup (Date: 2025-07-19)

#### Current State Summary
- **Database**: Contains 51 entities from 4 chunks
  - 9 bands (Black Sabbath, Iron Maiden, Saxon, etc.)
  - 30 people (band members)
  - 5 albums
  - 4 songs
  - 2 subgenres (glam metal, thrash metal)
  - 1 event (NWOBHM)
- **Embeddings**: 1024-dimensional vectors using snowflake-arctic-embed2
- **Extraction**: Very slow (~15-300s per chunk with magistral:24b)

#### Key Observations
1. **Performance Issue**: Entity extraction is extremely slow
   - Adaptive extractor seems to have a bug with chunk limits
   - Only processed 2-4 chunks despite requesting more
   - Need to investigate parallel processing optimization

2. **Missing Entity Types**: Enhanced schema defines many types not yet extracted:
   - Movement, Equipment, Platform, ProductionStyle
   - Venue, Web3Project, ViralPhenomenon
   - AcademicResource, TechnicalDetail, Compilation

3. **Vector Search**: Not yet implemented beyond embedding generation
   - Embeddings are stored but no search functionality exists
   - Need to build similarity search capabilities

---

## Code Snippets

### Quick Database Query
```python
import kuzu
db = kuzu.Database('schema/metal_history.db')
conn = kuzu.Connection(db)

# Count entities
for table in ['Band', 'Person', 'Album', 'Song', 'Subgenre']:
    result = conn.execute(f'MATCH (n:{table}) RETURN COUNT(n) as count')
    print(f'{table}: {result.get_next()[0]}')
```

### Sample Vector Search (to implement)
```python
def find_similar_bands(query_text: str, conn, top_k: int = 5):
    # Generate query embedding
    query_emb = generate_embedding(query_text)
    
    # Retrieve all band embeddings
    result = conn.execute("""
        MATCH (b:Band) 
        WHERE b.embedding IS NOT NULL
        RETURN b.id, b.name, b.embedding
    """)
    
    # Calculate similarities
    similarities = []
    for row in result:
        band_emb = np.array(row[2])
        sim = cosine_similarity(query_emb, band_emb)
        similarities.append((row[0], row[1], sim))
    
    # Return top k
    return sorted(similarities, key=lambda x: x[2], reverse=True)[:top_k]
```

---

## Ideas & TODOs

### Immediate Priorities
1. Fix extraction performance - investigate why it's so slow
2. Build basic vector search functionality
3. Create graph visualization tool
4. Test extraction on more diverse chunks

### Enhancement Ideas
- Add web scraping for missing band data
- Implement fuzzy search for band/album names
- Create timeline visualization of metal evolution
- Build recommendation system based on embeddings

### Questions to Investigate
- Why is extraction taking 5+ minutes per chunk?
- Can we use a faster model for initial extraction?
- How accurate is the current fuzzy matching threshold (0.85)?
- What's the optimal chunk size for extraction?

---

## Useful Commands

```bash
# Quick entity count
jq '.metadata.total_entities' deduplicated_entities.json

# Check extraction progress
ls -la batch_extraction_output/*.json | wc -l

# Test single extraction
cd extraction && python -c "from enhanced_extraction import extract_entities_enhanced; print(extract_entities_enhanced('Test text'))"

# Database stats
python -c "import kuzu; db = kuzu.Database('schema/metal_history.db'); conn = kuzu.Connection(db); print(conn.execute('CALL TABLE_INFO(\"Band\");').get_as_df())"
```

---

## Performance Metrics

### Current Baseline (to improve)
- Extraction: ~8-12s/chunk (sequential), 15-300s (observed)
- Embedding generation: ~100ms/text
- Database load: ~2-5 minutes
- Fuzzy matching: ~1-2 minutes for deduplication

### Target Performance
- Extraction: <5s/chunk
- Vector search: <100ms
- Graph queries: <50ms for common patterns

---

## Data Quality Notes

### Extraction Issues Observed
- Some band members incorrectly associated with wrong bands
- Missing formation years for many bands
- Duplicate detection needs improvement
- Geographic locations not standardized

### Schema Observations
- Good coverage of core entities
- Missing many relationship types from enhanced schema
- Need better temporal modeling
- Could benefit from genre hierarchy

---

## Next Steps
1. Start Phase 1.1: Create graph analysis tool
2. Document current graph statistics
3. Identify most critical missing data
4. Build proof-of-concept vector search

---

*This document will be continuously updated throughout the exploration process.*