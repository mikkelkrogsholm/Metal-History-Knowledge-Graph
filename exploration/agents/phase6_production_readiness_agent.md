# Phase 6: Production Readiness Agent

## Agent Role
You are responsible for making the Metal History Knowledge Graph production-ready. Your mission is to build APIs, optimize performance, create documentation, and ensure the system is scalable and maintainable.

## Objectives
1. Develop robust API endpoints
2. Optimize system performance
3. Create comprehensive documentation
4. Ensure production stability

## Tasks

### Task 1: API Development
Create `api/metal_graph_api.py`:
- RESTful endpoints for all operations
- GraphQL interface for complex queries
- Authentication and rate limiting
- Caching strategy
- API versioning

### Task 2: Performance Optimization
Optimize all components:
- Database query optimization
- Index strategy implementation
- Caching layer design
- Batch processing improvements
- Resource usage optimization

### Task 3: Documentation Suite
Create complete documentation:
- API reference with examples
- Query cookbook
- Deployment guide
- Performance tuning guide
- Troubleshooting manual

## Working Directory
- Scripts: `api/`, `scripts/optimization/`
- Scratchpad: `exploration/scratchpads/phase6_production.md`
- Reports: `exploration/reports/phase6_production_report.md`
- Docs: `docs/api/`, `docs/deployment/`

## Tools & Resources
- FastAPI or Flask for API
- Redis for caching
- Prometheus for metrics
- Docker for deployment
- OpenAPI for documentation

## Success Criteria
- [ ] API response time < 100ms (p95)
- [ ] 99.9% uptime capability
- [ ] Complete API documentation
- [ ] Horizontal scalability proven
- [ ] Security hardened

## Reporting Format
Provide a structured report including:
1. **API Implementation**
   - Endpoints created
   - Performance metrics
   - Security measures
2. **Optimization Results**
   - Before/after benchmarks
   - Resource savings
   - Scalability tests
3. **Documentation**
   - Coverage assessment
   - User feedback
   - Examples provided
4. **Deployment**
   - Architecture diagram
   - Scaling strategy
   - Monitoring setup

## Example Code Snippets

### RESTful API Implementation
```python
# api/metal_graph_api.py
from fastapi import FastAPI, HTTPException, Query, Depends
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
import redis
import json
from datetime import datetime

app = FastAPI(
    title="Metal History Knowledge Graph API",
    version="1.0.0",
    description="Explore the complete history of heavy metal music"
)

# Redis cache
cache = redis.Redis(host='localhost', port=6379, decode_responses=True)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Models
from pydantic import BaseModel

class BandResponse(BaseModel):
    id: str
    name: str
    formed_year: Optional[int]
    origin_location: Optional[str]
    genres: List[str]
    description: Optional[str]
    albums_count: int
    members_count: int

class SearchRequest(BaseModel):
    query: str
    entity_types: List[str] = ["bands", "albums", "people"]
    limit: int = 10
    use_semantic: bool = True

# Endpoints
@app.get("/api/v1/bands/{band_id}", response_model=BandResponse)
async def get_band(band_id: str):
    """Get detailed information about a specific band"""
    # Check cache
    cache_key = f"band:{band_id}"
    cached = cache.get(cache_key)
    if cached:
        return json.loads(cached)
    
    # Query database
    query = """
    MATCH (b:Band {id: $band_id})
    OPTIONAL MATCH (b)-[:PLAYS_GENRE]->(g:Subgenre)
    OPTIONAL MATCH (b)-[:RELEASED]->(a:Album)
    OPTIONAL MATCH (p:Person)-[:MEMBER_OF]->(b)
    RETURN b, 
           COLLECT(DISTINCT g.name) as genres,
           COUNT(DISTINCT a) as albums_count,
           COUNT(DISTINCT p) as members_count
    """
    
    result = db_conn.execute(query, {"band_id": band_id})
    if not result.has_next():
        raise HTTPException(status_code=404, detail="Band not found")
    
    # Process and cache
    data = process_band_result(result)
    cache.setex(cache_key, 3600, json.dumps(data))
    
    return data

@app.post("/api/v1/search")
async def search_entities(request: SearchRequest):
    """Search for entities using semantic or keyword search"""
    if request.use_semantic:
        results = semantic_search(request.query, request.entity_types, request.limit)
    else:
        results = keyword_search(request.query, request.entity_types, request.limit)
    
    return {
        "query": request.query,
        "results": results,
        "total": len(results),
        "search_type": "semantic" if request.use_semantic else "keyword"
    }

@app.get("/api/v1/timeline/{start_year}/{end_year}")
async def get_timeline(start_year: int, end_year: int):
    """Get timeline of metal history events"""
    query = """
    MATCH (b:Band)
    WHERE b.formed_year >= $start AND b.formed_year <= $end
    RETURN b.formed_year as year, COLLECT(b.name) as bands
    ORDER BY year
    """
    
    results = db_conn.execute(query, {"start": start_year, "end": end_year})
    timeline = [{"year": r[0], "bands": r[1]} for r in results]
    
    return {"start": start_year, "end": end_year, "timeline": timeline}

# GraphQL endpoint
from ariadne import QueryType, make_executable_schema, graphql_sync
from ariadne.asgi import GraphQL

type_defs = """
type Query {
    band(id: ID!): Band
    searchBands(query: String!, limit: Int = 10): [Band!]!
    genreEvolution(genreName: String!): GenreTree
}

type Band {
    id: ID!
    name: String!
    formedYear: Int
    members: [Person!]!
    albums: [Album!]!
    genres: [Genre!]!
    influencedBy: [Band!]!
    influenced: [Band!]!
}
"""

query = QueryType()

@query.field("band")
def resolve_band(_, info, id):
    return get_band_by_id(id)

schema = make_executable_schema(type_defs, query)
app.mount("/graphql", GraphQL(schema, debug=True))
```

### Performance Optimization
```python
# scripts/optimization/query_optimizer.py
import time
from functools import lru_cache
import asyncio
from concurrent.futures import ThreadPoolExecutor

class QueryOptimizer:
    def __init__(self, db_conn):
        self.db_conn = db_conn
        self.query_cache = {}
        self.executor = ThreadPoolExecutor(max_workers=4)
    
    def optimize_query(self, query: str):
        """Analyze and optimize Cypher query"""
        # Add indexes hints
        if "MATCH" in query and "WHERE" in query:
            # Suggest index usage
            query = self.add_index_hints(query)
        
        # Limit initial node matches
        if "MATCH (n)" in query:
            query = query.replace("MATCH (n)", "MATCH (n) WHERE n.id IS NOT NULL")
        
        return query
    
    def add_index_hints(self, query: str):
        """Add index usage hints to query"""
        # Detect filterable properties
        import re
        where_pattern = r'WHERE\s+(\w+)\.(\w+)\s*='
        matches = re.findall(where_pattern, query)
        
        for alias, property in matches:
            # Check if index exists
            if self.has_index(alias, property):
                query = f"// INDEX: {alias}.{property}\n{query}"
        
        return query
    
    @lru_cache(maxsize=1000)
    def cached_query(self, query: str, params_hash: str):
        """Cache frequently used queries"""
        return self.db_conn.execute(query, self.params_cache[params_hash])
    
    async def parallel_queries(self, queries: List[tuple]):
        """Execute multiple queries in parallel"""
        loop = asyncio.get_event_loop()
        
        tasks = []
        for query, params in queries:
            task = loop.run_in_executor(
                self.executor,
                self.db_conn.execute,
                query,
                params
            )
            tasks.append(task)
        
        results = await asyncio.gather(*tasks)
        return results

# Database optimization
class DatabaseOptimizer:
    def __init__(self, db_path):
        self.db = kuzu.Database(db_path)
        self.conn = kuzu.Connection(self.db)
    
    def create_optimal_indexes(self):
        """Create indexes for common query patterns"""
        indexes = [
            "CREATE INDEX idx_band_name ON Band(name)",
            "CREATE INDEX idx_band_year ON Band(formed_year)",
            "CREATE INDEX idx_album_year ON Album(release_year)",
            "CREATE INDEX idx_person_name ON Person(name)",
            "CREATE INDEX idx_location_city ON GeographicLocation(city)",
            "CREATE INDEX idx_genre_name ON Subgenre(name)"
        ]
        
        for index in indexes:
            try:
                self.conn.execute(index)
                print(f"Created: {index}")
            except Exception as e:
                print(f"Index exists or error: {e}")
    
    def analyze_query_performance(self):
        """Profile common queries"""
        test_queries = [
            ("Band lookup", "MATCH (b:Band {name: 'Metallica'}) RETURN b"),
            ("Genre bands", "MATCH (b:Band)-[:PLAYS_GENRE]->(g:Subgenre {name: 'thrash metal'}) RETURN b"),
            ("Influence chain", "MATCH path = (b1:Band)-[:INFLUENCED_BY*1..3]->(b2:Band) RETURN path LIMIT 100"),
            ("Timeline", "MATCH (b:Band) WHERE b.formed_year >= 1980 AND b.formed_year <= 1990 RETURN b")
        ]
        
        results = []
        for name, query in test_queries:
            start = time.time()
            result = self.conn.execute(query)
            count = len(list(result))
            duration = (time.time() - start) * 1000
            
            results.append({
                'query': name,
                'duration_ms': duration,
                'row_count': count
            })
        
        return results
```

### Caching Strategy
```python
# api/caching.py
from functools import wraps
import hashlib
import pickle

class CacheManager:
    def __init__(self, redis_client, default_ttl=3600):
        self.redis = redis_client
        self.default_ttl = default_ttl
    
    def cache_key(self, prefix: str, *args, **kwargs):
        """Generate cache key from function arguments"""
        key_data = f"{prefix}:{str(args)}:{str(sorted(kwargs.items()))}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def cached(self, prefix: str, ttl: int = None):
        """Decorator for caching function results"""
        def decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                # Generate cache key
                key = self.cache_key(prefix, *args, **kwargs)
                
                # Check cache
                cached = self.redis.get(key)
                if cached:
                    return pickle.loads(cached.encode('latin1'))
                
                # Call function
                result = await func(*args, **kwargs)
                
                # Cache result
                ttl_seconds = ttl or self.default_ttl
                self.redis.setex(
                    key,
                    ttl_seconds,
                    pickle.dumps(result).decode('latin1')
                )
                
                return result
            return wrapper
        return decorator
    
    def invalidate_pattern(self, pattern: str):
        """Invalidate all keys matching pattern"""
        for key in self.redis.scan_iter(match=pattern):
            self.redis.delete(key)

# Usage
cache_manager = CacheManager(redis_client)

@cache_manager.cached("band_details", ttl=7200)
async def get_band_details(band_id: str):
    # Expensive database query
    return fetch_band_from_db(band_id)
```

### Production Deployment
```yaml
# docker-compose.yml
version: '3.8'

services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_PATH=/data/metal_history.db
      - REDIS_URL=redis://redis:6379
      - LOG_LEVEL=INFO
    volumes:
      - ./data:/data
    depends_on:
      - redis
      - prometheus
    deploy:
      replicas: 3
      restart_policy:
        condition: on-failure
        max_attempts: 3

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data
    ports:
      - "6379:6379"

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./certs:/etc/nginx/certs
    depends_on:
      - api

  prometheus:
    image: prom/prometheus
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    ports:
      - "9090:9090"

  grafana:
    image: grafana/grafana
    ports:
      - "3000:3000"
    volumes:
      - grafana_data:/var/lib/grafana
      - ./grafana/dashboards:/etc/grafana/provisioning/dashboards

volumes:
  redis_data:
  prometheus_data:
  grafana_data:
```

### API Documentation
```python
# docs/api_examples.py
"""
# Metal History API Examples

## Authentication
```bash
export API_KEY="your-api-key"
curl -H "Authorization: Bearer $API_KEY" https://api.metalhistory.com/v1/bands
```

## Search Examples

### Semantic Search
```python
import requests

response = requests.post('https://api.metalhistory.com/v1/search', json={
    'query': 'atmospheric black metal from norway',
    'entity_types': ['bands', 'albums'],
    'limit': 20,
    'use_semantic': True
})

results = response.json()
for result in results['results']:
    print(f"{result['name']} - {result['relevance_score']}")
```

### GraphQL Query
```graphql
query BandDetails($bandId: ID!) {
  band(id: $bandId) {
    name
    formedYear
    members {
      name
      instruments
      activeYears
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
  }
}
```

### Timeline Query
```bash
curl "https://api.metalhistory.com/v1/timeline/1980/1990" | jq
```

## Batch Operations

### Bulk Entity Creation
```python
entities = [
    {'type': 'band', 'name': 'Mayhem', 'formed_year': 1984},
    {'type': 'band', 'name': 'Burzum', 'formed_year': 1991}
]

response = requests.post(
    'https://api.metalhistory.com/v1/entities/bulk',
    json={'entities': entities},
    headers={'Authorization': f'Bearer {API_KEY}'}
)
```
"""
```

### Monitoring Setup
```python
# api/monitoring.py
from prometheus_client import Counter, Histogram, Gauge
import time

# Metrics
request_count = Counter('api_requests_total', 'Total API requests', ['method', 'endpoint'])
request_duration = Histogram('api_request_duration_seconds', 'Request duration', ['method', 'endpoint'])
active_connections = Gauge('api_active_connections', 'Active connections')
cache_hits = Counter('cache_hits_total', 'Cache hit count', ['cache_type'])
error_count = Counter('api_errors_total', 'Total errors', ['error_type'])

def track_request(func):
    """Decorator to track API metrics"""
    @wraps(func)
    async def wrapper(request, *args, **kwargs):
        endpoint = request.url.path
        method = request.method
        
        # Track active connections
        active_connections.inc()
        
        # Track request
        request_count.labels(method=method, endpoint=endpoint).inc()
        
        # Time request
        start = time.time()
        try:
            response = await func(request, *args, **kwargs)
            return response
        except Exception as e:
            error_count.labels(error_type=type(e).__name__).inc()
            raise
        finally:
            duration = time.time() - start
            request_duration.labels(method=method, endpoint=endpoint).observe(duration)
            active_connections.dec()
    
    return wrapper
```

## Production Checklist
- [ ] Load testing completed (target: 1000 RPS)
- [ ] Security audit passed
- [ ] SSL certificates configured
- [ ] Rate limiting implemented
- [ ] Backup strategy defined
- [ ] Monitoring dashboards created
- [ ] Alert rules configured
- [ ] Documentation complete
- [ ] CI/CD pipeline ready
- [ ] Rollback procedure tested

## Timeline
- Day 1: Build core API endpoints
- Day 2: Implement caching and optimization
- Day 3: Create deployment configuration
- Day 4: Documentation and testing
- Day 5: Load testing and final adjustments

Focus on reliability, performance, and developer experience!