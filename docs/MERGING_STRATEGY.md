# Entity Merging Strategy

The pipeline implements sophisticated merging to combine information from different text sources while preserving all valuable data.

## Merging Rules

### 1. **New Information Addition**
When an entity from a new chunk has information not present in the existing entity, it's added:
- Black Sabbath from chunk_001: `{name, formed_year}`
- Black Sabbath from chunk_002: adds `origin_city`
- Black Sabbath from chunk_003: adds `origin_country, description`
- **Result**: Complete entity with all fields

### 2. **List Merging**
Lists are combined with duplicates removed:
- Tony Iommi from chunk_001: `instruments: ["guitar"]`
- Tony Iommi from chunk_002: `instruments: ["guitar", "keyboards"]`
- **Result**: `instruments: ["guitar", "keyboards"]`

### 3. **Description Combination**
Multiple descriptions are concatenated:
- If different descriptions are found, they're combined
- Example: "Pioneer of heavy metal" + "Founded in Birmingham" → "Pioneer of heavy metal Founded in Birmingham"

### 4. **Conflict Detection**
When numeric values differ, conflicts are tracked:
- Paranoid album from chunk_001: `release_year: 1970`
- Paranoid album from chunk_005: `release_year: 1971`
- **Result**: Keeps 1970 but adds `_conflicts: {release_year: [1970, 1971]}`

### 5. **Alternate Values**
When string values differ significantly (< 90% similarity):
- Stored in `_alternate_values` field
- Preserves different spellings or descriptions

## Example: Complete Entity After Merging

```json
{
  "name": "Black Sabbath",
  "formed_year": 1968,
  "origin_city": "Birmingham",
  "origin_country": "UK",
  "description": "Pioneers of heavy metal",
  "_metadata": {
    "variations": ["Black Sabbath", "Black Sabath"],
    "source_chunks": ["chunk_001", "chunk_002", "chunk_003"]
  }
}
```

## Benefits

1. **No Information Loss**: All data from different sources is preserved
2. **Conflict Visibility**: Conflicting information is tracked, not silently overwritten
3. **Source Tracking**: Know which chunks contributed which information
4. **Name Variations**: All spellings/variations are preserved

## Handling Different Document Sources

When processing both `history_from_claude.md` and `history_from_chatgpt.md`:
- Same entities mentioned in both documents will be merged
- Different perspectives or details will be combined
- Conflicting facts will be flagged for review

This ensures the final knowledge graph contains the most complete information possible from all sources.