# Query Graph Command

This command helps write and execute Cypher queries against the Kuzu database.

## Usage
```
/query-graph [natural_language_query]
```

## Description
Translates natural language questions into Cypher queries and executes them against the Metal History graph.

## Examples
```
/query-graph Show me all albums by Black Sabbath
/query-graph Which bands formed in Birmingham?
/query-graph Find the evolution of doom metal
/query-graph List all venues in California
```

## Tasks
1. Parse natural language query
2. Generate appropriate Cypher query
3. Execute against Kuzu database
4. Format and display results
5. Suggest related queries or refinements

## Query Templates
- Band discography
- Genre evolution and relationships
- Geographic analysis
- Time-based queries (by decade/year)
- Influence networks