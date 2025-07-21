# Metal History Knowledge Graph API Documentation

## Overview

The Metal History Knowledge Graph API provides comprehensive access to the interconnected history of heavy metal music. It combines traditional REST endpoints with GraphQL for flexible querying, semantic search capabilities, and high-performance caching.

## Base URL

```
https://api.metalhistory.com
```

## Authentication

Currently, the API is open access. API key authentication will be added in future versions.

## Rate Limiting

- General endpoints: 10 requests/second
- Search endpoints: 5 requests/second
- Burst allowance: 2x the base rate

## Response Format

All responses follow this structure:

```json
{
  "data": { ... },        // For successful responses
  "error": {              // For error responses
    "message": "...",
    "code": "...",
    "details": { ... }
  }
}
```

## Core Endpoints

### 1. Band Operations

#### Get Band Details
```http
GET /api/v1/bands/{band_id}
```

**Parameters:**
- `band_id` (path, required): Unique band identifier

**Response:**
```json
{
  "id": "band_black_sabbath",
  "name": "Black Sabbath",
  "formed_year": 1968,
  "origin_location": "Birmingham, England",
  "genres": ["heavy metal", "doom metal"],
  "description": "Pioneering heavy metal band...",
  "albums_count": 19,
  "members_count": 8
}
```

### 2. Search Operations

#### Keyword Search
```http
POST /api/v1/search
```

**Request Body:**
```json
{
  "query": "sabbath",
  "entity_types": ["bands", "albums", "people"],
  "limit": 10,
  "offset": 0
}
```

**Response:**
```json
[
  {
    "entity_type": "band",
    "id": "band_black_sabbath",
    "name": "Black Sabbath",
    "relevance_score": 1.0,
    "metadata": {
      "formed_year": 1968,
      "description": "..."
    }
  }
]
```

#### Semantic Search (AI-Powered)
```http
POST /api/v2/search/semantic
```

**Request Body:**
```json
{
  "query": "atmospheric doom metal from england",
  "entity_types": ["bands"],
  "limit": 10,
  "use_hybrid": true,
  "semantic_weight": 0.7
}
```

**Response:**
```json
[
  {
    "entity_type": "band",
    "id": "band_cathedral",
    "name": "Cathedral",
    "relevance_score": 0.89,
    "metadata": {
      "genres": ["doom metal"],
      "origin_location": "Coventry, England"
    }
  }
]
```

### 3. Timeline Queries

#### Get Historical Timeline
```http
GET /api/v1/timeline/{start_year}/{end_year}
```

**Parameters:**
- `start_year` (path, required): Start year (1960-2025)
- `end_year` (path, required): End year (1960-2025)

**Response:**
```json
{
  "start_year": 1968,
  "end_year": 1970,
  "total_years": 3,
  "total_events": 42,
  "timeline": [
    {
      "year": 1968,
      "events": [
        {
          "type": "band_formed",
          "name": "Black Sabbath",
          "id": "band_black_sabbath"
        }
      ],
      "event_count": 8
    }
  ]
}
```

### 4. Influence Network

#### Get Band Influences
```http
GET /api/v1/influences/{band_id}
```

**Response:**
```json
{
  "band_id": "band_metallica",
  "band_name": "Metallica",
  "influenced_by": [
    {
      "id": "band_black_sabbath",
      "name": "Black Sabbath",
      "formed_year": 1968
    }
  ],
  "influenced": [
    {
      "id": "band_trivium",
      "name": "Trivium",
      "formed_year": 1999
    }
  ],
  "total_connections": 15
}
```

### 5. Recommendations

#### Get Band Recommendations
```http
GET /api/v2/recommendations/{band_id}?limit=10
```

**Response:**
```json
{
  "source_band": {
    "id": "band_iron_maiden",
    "name": "Iron Maiden"
  },
  "recommendations": [
    {
      "band_id": "band_judas_priest",
      "band_name": "Judas Priest",
      "reason": "shared_genres",
      "score": 0.95
    },
    {
      "band_id": "band_saxon",
      "band_name": "Saxon",
      "reason": "semantic_similarity",
      "score": 0.87
    }
  ],
  "total": 10
}
```

## GraphQL API

The GraphQL endpoint provides more flexible querying capabilities:

```
POST /graphql
```

### Example Query

```graphql
query BandDetails($bandId: ID!) {
  band(id: $bandId) {
    name
    formedYear
    genres {
      name
      description
    }
    members(active: true) {
      name
      instruments {
        name
      }
    }
    albums {
      title
      releaseYear
      songs {
        title
        duration
      }
    }
    influencedBy {
      name
    }
    similarBands(limit: 5) {
      band {
        name
      }
      similarityScore
      commonGenres {
        name
      }
    }
  }
}
```

### Variables
```json
{
  "bandId": "band_iron_maiden"
}
```

## Advanced Features

### 1. Similar Entity Search

Find entities similar to a given entity using AI embeddings:

```http
POST /api/v2/similar
```

**Request:**
```json
{
  "entity_id": "band_black_sabbath",
  "entity_type": "bands",
  "limit": 10
}
```

### 2. Genre Network

Visualize genre relationships:

```http
GET /api/v2/genre-network
```

**Response:**
```json
{
  "nodes": [
    {"id": "heavy metal", "label": "Heavy Metal"},
    {"id": "thrash metal", "label": "Thrash Metal"}
  ],
  "edges": [
    {
      "source": "heavy metal",
      "target": "thrash metal",
      "weight": 45
    }
  ],
  "total_genres": 25,
  "total_connections": 120
}
```

### 3. Database Statistics

```http
GET /api/v1/stats
```

**Response:**
```json
{
  "total_bands": 5234,
  "total_albums": 12456,
  "total_people": 8901,
  "total_songs": 45678,
  "total_genres": 89,
  "total_locations": 234,
  "total_relationships": 98765,
  "bands_by_decade": [
    {
      "decade": 1970,
      "band_count": 234
    }
  ]
}
```

## Performance Tips

1. **Use Caching Headers**: Responses include cache headers. Respect them to reduce load.

2. **Batch Requests**: When possible, use GraphQL to fetch multiple related entities in one request.

3. **Pagination**: Always use pagination for list endpoints:
   ```
   ?limit=20&offset=40
   ```

4. **Field Selection**: In GraphQL, only request the fields you need.

5. **Semantic Search**: For natural language queries, use semantic search for better results.

## Error Codes

| Code | Description |
|------|-------------|
| 400 | Bad Request - Invalid parameters |
| 404 | Not Found - Entity doesn't exist |
| 429 | Too Many Requests - Rate limit exceeded |
| 500 | Internal Server Error |

## SDKs and Examples

### Python Example

```python
import requests

# Search for bands
response = requests.post(
    "https://api.metalhistory.com/api/v2/search/semantic",
    json={
        "query": "progressive metal from sweden",
        "entity_types": ["bands"],
        "limit": 5
    }
)

bands = response.json()
for band in bands:
    print(f"{band['name']} - Score: {band['relevance_score']}")
```

### JavaScript Example

```javascript
// Using fetch API
const searchBands = async (query) => {
  const response = await fetch('https://api.metalhistory.com/api/v1/search', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      query: query,
      entity_types: ['bands', 'albums'],
      limit: 10
    })
  });
  
  return response.json();
};

// GraphQL query
const graphqlQuery = `
  query GetBand($id: ID!) {
    band(id: $id) {
      name
      formedYear
      albums {
        title
        releaseYear
      }
    }
  }
`;

const getBandDetails = async (bandId) => {
  const response = await fetch('https://api.metalhistory.com/graphql', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      query: graphqlQuery,
      variables: { id: bandId }
    })
  });
  
  return response.json();
};
```

## Monitoring and Health

### Health Check
```http
GET /health
```

### Detailed Health Status
```http
GET /health/detailed
```

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-19T15:30:00Z",
  "components": {
    "database": {
      "status": "healthy",
      "connection": "active"
    },
    "cache": {
      "status": "connected",
      "stats": {
        "total_keys": 1234,
        "hit_rate": 87.5
      }
    },
    "semantic_search": {
      "status": "healthy",
      "embeddings_loaded": 50000
    }
  }
}
```

## Changelog

### v2.0.0 (Current)
- Added semantic search capabilities
- Implemented Redis caching
- Added GraphQL endpoint
- Performance optimizations
- Enhanced recommendation engine

### v1.0.0
- Initial release
- Basic CRUD operations
- Keyword search
- Timeline queries

## Support

For API support, feature requests, or bug reports:
- Email: api-support@metalhistory.com
- GitHub: https://github.com/metalhistory/api
- Documentation: https://docs.metalhistory.com