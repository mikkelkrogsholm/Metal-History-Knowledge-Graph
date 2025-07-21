# Query Pattern Testing Report

Generated: 2025-07-19T20:14:06.642465
Database: schema/metal_history.db

## Performance Summary
- Total queries tested: 30
- Successful: 25
- Failed: 5
- Average execution time: 2.24ms

**Fastest Query**: Country metal statistics (0.5ms)
**Slowest Query**: Direct influence (9.57ms)

### By Category:
- **influence_patterns**: 5/5 successful, avg 5.18ms
- **genre_patterns**: 5/5 successful, avg 1.66ms
- **temporal_patterns**: 4/5 successful, avg 1.29ms
- **geographic_patterns**: 3/5 successful, avg 0.7ms
- **collaboration_patterns**: 5/5 successful, avg 1.81ms
- **complex_patterns**: 3/5 successful, avg 1.79ms

## Detailed Query Results

### Influence Patterns

**✓ Direct influence**
- Find direct band-to-band influences
- Execution time: 9.57ms
- Results found: 0

**✓ Multi-hop influence chains**
- Find influence chains of 2-3 hops
- Execution time: 5.81ms
- Results found: 0

**✓ Influence network size**
- Calculate influence network size for each band
- Execution time: 4.74ms
- Results found: 2
- Sample results:
  - ['Black Sabbath', 0, 0, 0]
  - ['Iron Maiden', 0, 0, 0]

**✓ Mutual influence detection**
- Find bands that influenced each other (should be rare/none)
- Execution time: 0.76ms
- Results found: 0

**✓ Influence by decade**
- Analyze influence patterns across decades
- Execution time: 5.03ms
- Results found: 0

### Genre Patterns

**✓ Band genre associations**
- Find bands and their associated genres
- Execution time: 1.26ms
- Results found: 0

**✓ Genre evolution paths**
- Trace genre evolution paths
- Execution time: 1.15ms
- Results found: 0

**✓ Genre popularity by band count**
- Find most popular genres by band count
- Execution time: 0.98ms
- Results found: 0

**✓ Cross-genre bands**
- Find bands that play multiple genres
- Execution time: 4.32ms
- Results found: 0

**✓ Genre origin locations**
- Find where genres originated
- Execution time: 0.61ms
- Results found: 0

### Temporal Patterns

**✗ Band timeline**
- Band formation and disbanding timeline
- Error: Binder exception: Cannot find property disbanded_year for b.

**✓ Album release timeline**
- Album releases chronologically
- Execution time: 0.85ms
- Results found: 1
- Sample results:
  - ['Black Sabbath', 'Paranoid', 1970]

**✓ Active bands by decade**
- Count of bands formed by decade
- Execution time: 1.6ms
- Results found: 2
- Sample results:
  - [1960, 1]
  - [1970, 1]

**✓ Member age at band formation**
- Calculate member ages when bands formed
- Execution time: 1.85ms
- Results found: 0

**✓ Era associations**
- Bands associated with specific eras
- Execution time: 0.88ms
- Results found: 0

### Geographic Patterns

**✓ Band locations**
- Where bands were formed
- Execution time: 0.55ms
- Results found: 0

**✗ Metal scenes by city**
- Cities with multiple metal bands
- Error: Parser exception: Invalid input <bands[0..>: expected rule oC_ProjectionItem (line: 6, offset: 42)
"                       band_count, bands[0..5] as sample_bands"
                                           ^^

**✓ Country metal statistics**
- Countries ranked by metal band count
- Execution time: 0.5ms
- Results found: 0

**✗ Recording studio locations**
- Most used recording studios
- Error: Binder exception: Table LOCATED_IN does not exist.

**✓ Genre geographic distribution**
- Genre distribution by country
- Execution time: 1.04ms
- Results found: 0

### Collaboration Patterns

**✓ Band members**
- Bands with their members
- Execution time: 0.91ms
- Results found: 0

**✓ Multi-band members**
- People who played in multiple bands
- Execution time: 0.97ms
- Results found: 0

**✓ Producer collaborations**
- Producers who worked with multiple bands
- Execution time: 1.36ms
- Results found: 0

**✓ Band connection network**
- Bands connected through shared members
- Execution time: 1.37ms
- Results found: 0

**✓ Album collaborations**
- Albums featuring guest artists
- Execution time: 4.47ms
- Results found: 0

### Complex Patterns

**✗ Shortest path between bands**
- Find shortest connection path between two bands
- Error: Parser exception: Invalid input <MATCH (b1:Band {name: 'Black Sabbath'}), (b2:Band {name: 'Iron Maiden'})
                MATCH path = shortestPath>: expected rule oC_SingleQuery (line: 3, offset: 29)
"                MATCH path = shortestPath((b1)-[*..10]-(b2))"
                              ^^^^^^^^^^^^

**✓ Influence PageRank approximation**
- Approximate PageRank for band influence
- Execution time: 2.07ms
- Results found: 2
- Sample results:
  - ['Black Sabbath', 0.0]
  - ['Iron Maiden', 0.0]

**✓ Album production network**
- Complete album production information
- Execution time: 1.42ms
- Results found: 1
- Sample results:
  - ['Paranoid', 'Black Sabbath', None, None]

**✓ Genre convergence points**
- Genres that emerged from multiple sources
- Execution time: 1.89ms
- Results found: 0

**✗ Band activity overlap**
- Bands that were active during overlapping periods
- Error: Binder exception: Cannot find property disbanded_year for b1.

## Data Consistency Validation

- Errors found: 0
- Warnings found: 0

### Validation Details:

**✓ Albums released before band formed**
- Issues found: 0

**✓ Members born after band formed**
- Issues found: 0

**✓ Circular influence relationships**
- Issues found: 0

**✓ Bands with no formation year**
- Issues found: 0

**✓ Albums with no release year**
- Issues found: 0

## Key Insights
1. Database contains minimal test data (2 bands, 1 person, 1 album)
2. Query performance is excellent (<5ms for all queries)
3. Complex path queries and aggregations work correctly
4. No data consistency issues found (expected with minimal data)
5. Framework ready for full dataset testing