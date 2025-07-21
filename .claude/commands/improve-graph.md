# Analyze Graph Command

This command analyzes the Kuzu graph database structure and content looking for ways to improve it.

## Usage
```
/improve-graph [aspect]
```

## Description
Analyzes the Metal History graph database to understand structure, relationships, and data patterns.
The goal is to find out how we can improve on the graph.

## Aspects
- `schema` - Show node types and relationships
- `stats` - Display entity counts and statistics  
- `quality` - Check data quality and completeness
- `relationships` - Analyze relationship patterns
- `embeddings` - Verify embedding coverage

## Examples
```
/analyze-graph
/analyze-graph stats
/analyze-graph relationships
```

## Tasks
1. Connect to Kuzu database
2. Run analysis queries
3. Identify data gaps or issues
4. Suggest improvements