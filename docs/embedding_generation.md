# Embedding Generation with Snowflake Arctic Embed 2

## Overview

This project uses **Snowflake Arctic Embed 2** for generating embeddings from text. This model produces 1024-dimensional vectors and supports multilingual content, making it ideal for the diverse geographic and cultural contexts in metal history.

## Model Specifications

- **Model**: snowflake-arctic-embed2:latest
- **Embedding Dimensions**: 1024
- **Context Window**: 8,192 tokens
- **Languages**: 74 languages supported
- **License**: Apache 2.0

## Installation

First, ensure Ollama is installed and pull the model:

```bash
ollama pull snowflake-arctic-embed2:latest
```

## Usage Examples

### Python Integration

```python
import ollama
import numpy as np

def generate_embedding(text: str) -> np.ndarray:
    """Generate embedding for a single text"""
    response = ollama.embed(
        model='snowflake-arctic-embed2:latest',
        input=text
    )
    return np.array(response['embedding'])

def generate_embeddings_batch(texts: list[str]) -> np.ndarray:
    """Generate embeddings for multiple texts"""
    response = ollama.embed(
        model='snowflake-arctic-embed2:latest',
        input=texts
    )
    return np.array(response['embeddings'])

# Example usage
text = "Black Sabbath pioneered heavy metal in Birmingham with their doom-laden riffs"
embedding = generate_embedding(text)
print(f"Embedding shape: {embedding.shape}")  # (1024,)

# Batch processing
texts = [
    "NWOBHM transformed metal from underground curiosity to global phenomenon",
    "Norway's second wave of black metal created controversy and innovation"
]
embeddings = generate_embeddings_batch(texts)
print(f"Batch embeddings shape: {embeddings.shape}")  # (2, 1024)
```

### Embedding Storage in Kuzu

When inserting nodes with embeddings:

```python
import kuzu

conn = kuzu.Connection(db)

# Prepare embedding as a list of floats
embedding = generate_embedding("Band description text").tolist()

# Insert band with embedding
query = """
    CREATE (b:Band {
        id: $id,
        name: $name,
        description: $description,
        embedding: $embedding
    })
"""
conn.execute(query, {
    "id": 1,
    "name": "Black Sabbath",
    "description": "Pioneered heavy metal in Birmingham",
    "embedding": embedding
})
```

### Vector Similarity Search

```python
def find_similar_bands(query_text: str, top_k: int = 5):
    """Find bands with similar descriptions using cosine similarity"""
    query_embedding = generate_embedding(query_text)
    
    # Kuzu doesn't have built-in vector similarity yet,
    # so we'll retrieve all embeddings and compute in Python
    result = conn.execute("""
        MATCH (b:Band)
        RETURN b.id, b.name, b.embedding
    """)
    
    similarities = []
    for row in result:
        band_embedding = np.array(row['b.embedding'])
        # Cosine similarity
        similarity = np.dot(query_embedding, band_embedding) / (
            np.linalg.norm(query_embedding) * np.linalg.norm(band_embedding)
        )
        similarities.append((row['b.id'], row['b.name'], similarity))
    
    # Sort by similarity and return top k
    similarities.sort(key=lambda x: x[2], reverse=True)
    return similarities[:top_k]
```

## Optimization Strategies

### 1. Matryoshka Representation Learning (MRL)

Reduce embedding dimensions while maintaining quality:

```python
def truncate_embedding(embedding: np.ndarray, target_dim: int = 256) -> np.ndarray:
    """Truncate embedding to smaller dimension using MRL"""
    return embedding[:target_dim]

# Original 1024-dim embedding
full_embedding = generate_embedding(text)

# Truncated 256-dim embedding (4x smaller)
small_embedding = truncate_embedding(full_embedding, 256)
```

### 2. Batch Processing

Process multiple texts efficiently:

```python
def process_paragraphs(paragraphs: list[str], batch_size: int = 32):
    """Process paragraphs in batches for efficiency"""
    all_embeddings = []
    
    for i in range(0, len(paragraphs), batch_size):
        batch = paragraphs[i:i + batch_size]
        embeddings = generate_embeddings_batch(batch)
        all_embeddings.extend(embeddings)
    
    return np.array(all_embeddings)
```

### 3. Context Window Management

Handle long texts that exceed the 8K token limit:

```python
def chunk_text(text: str, max_tokens: int = 8000) -> list[str]:
    """Split text into chunks that fit within context window"""
    # Simple word-based chunking (use proper tokenizer in production)
    words = text.split()
    chunks = []
    current_chunk = []
    
    for word in words:
        current_chunk.append(word)
        # Rough estimate: 1 word ≈ 1.3 tokens
        if len(current_chunk) * 1.3 > max_tokens:
            chunks.append(' '.join(current_chunk[:-1]))
            current_chunk = [word]
    
    if current_chunk:
        chunks.append(' '.join(current_chunk))
    
    return chunks
```

## Integration with Entity Extraction

When extracting entities from the metal history document:

```python
async def extract_and_embed_entities(paragraph: str, paragraph_num: int):
    """Extract entities and generate embeddings in one pass"""
    
    # Extract entities using Ollama (separate LLM call)
    entities = await extract_entities_with_llm(paragraph)
    
    # Generate embedding for the full paragraph context
    paragraph_embedding = generate_embedding(paragraph)
    
    # Process each entity
    for entity in entities:
        # Create contextual description
        context = f"{entity['type']}: {entity['name']} - {entity['context']}"
        entity_embedding = generate_embedding(context)
        
        # Store in database
        store_entity_with_embedding(
            entity=entity,
            embedding=entity_embedding,
            paragraph_embedding=paragraph_embedding,
            paragraph_num=paragraph_num
        )
```

## Performance Considerations

1. **Model Loading**: The model loads once and stays in memory
2. **Latency**: ~10ms per query on modern hardware
3. **Throughput**: 100+ documents/second on GPU
4. **Memory Usage**: ~1.2GB for model weights

## Error Handling

```python
def safe_generate_embedding(text: str, max_retries: int = 3):
    """Generate embedding with retry logic"""
    for attempt in range(max_retries):
        try:
            return generate_embedding(text)
        except Exception as e:
            if attempt == max_retries - 1:
                print(f"Failed to generate embedding: {e}")
                # Return zero vector as fallback
                return np.zeros(1024)
            time.sleep(2 ** attempt)  # Exponential backoff
```

## Monitoring and Logging

```python
import logging
import time

logger = logging.getLogger(__name__)

def generate_embedding_with_metrics(text: str):
    """Generate embedding with performance metrics"""
    start_time = time.time()
    
    embedding = generate_embedding(text)
    
    duration = time.time() - start_time
    logger.info(f"Generated embedding in {duration:.3f}s for {len(text)} chars")
    
    return embedding
```