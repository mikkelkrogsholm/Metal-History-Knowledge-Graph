# Adaptive Extraction System

The Metal History pipeline includes an adaptive extraction system that automatically scales based on your hardware capabilities. This ensures optimal performance whether you're running on a powerful Mac Studio or a modest laptop.

## How It Works

1. **System Profiling**: Automatically detects CPU cores, memory, and system type
2. **Performance Tiers**: Categorizes your system (Low/Medium/Medium-High/High)
3. **Dynamic Scaling**: Adjusts worker count, batch size, and memory usage
4. **Resource Monitoring**: Throttles extraction if system resources are constrained
5. **Apple Silicon Optimization**: Special optimizations for M-series Macs

## Performance Tiers

### High Tier (16+ cores, 32+ GB RAM)
- **Workers**: 8 parallel extractors
- **Batch Size**: 10 chunks per batch
- **Context Window**: 16384 tokens
- **Features**: Memory caching, chunk prefetching
- **Expected Speed**: ~3-4 seconds per chunk

### Medium-High Tier (8+ cores, 16+ GB RAM)
- **Workers**: 4 parallel extractors
- **Batch Size**: 5 chunks per batch
- **Context Window**: 16384 tokens
- **Features**: Memory caching, chunk prefetching
- **Expected Speed**: ~5-6 seconds per chunk

### Medium Tier (4+ cores, 8+ GB RAM)
- **Workers**: 3 parallel extractors
- **Batch Size**: 3 chunks per batch
- **Context Window**: 8192 tokens (optimized for speed)
- **Features**: Memory caching (if >4GB available)
- **Expected Speed**: ~8-10 seconds per chunk

### Low Tier (<4 cores, <8 GB RAM)
- **Workers**: 1 (sequential processing)
- **Batch Size**: 1 chunk at a time
- **Context Window**: 8192 tokens
- **Features**: Minimal memory usage
- **Expected Speed**: ~10-15 seconds per chunk

## Usage

### Automatic Configuration
```bash
# Configure environment based on your system
./scripts/configure_environment.sh

# Run extraction with auto-detected settings
./scripts/pipeline/02_extract_entities_adaptive.sh
```

### View System Profile
```bash
# Detailed system analysis
python scripts/automation/system_profiler.py

# Quick profile during extraction
./scripts/pipeline/02_extract_entities_adaptive.sh --profile
```

### Manual Override
```bash
# Force specific worker count
./scripts/pipeline/02_extract_entities_adaptive.sh chunks.json "" 4

# Force profile via environment
export METAL_EXTRACTION_PROFILE=medium
./scripts/pipeline/02_extract_entities_adaptive.sh

# Override workers only
export METAL_EXTRACTION_WORKERS=2
./scripts/pipeline/02_extract_entities_adaptive.sh
```

## Resource Management

### CPU Limits
- **High Tier**: Max 85% CPU usage
- **Medium Tiers**: Max 75-80% CPU usage
- **Low Tier**: Max 70% CPU usage

### Memory Limits
- **Per Worker**: 15% of total system memory
- **Total Usage**: Max 75% of system memory
- **Throttling**: Automatic when limits exceeded

### Monitoring
The system continuously monitors resource usage and will:
1. Throttle extraction if CPU > limit
2. Pause workers if memory > limit
3. Resume when resources available

## Performance Comparison

| System Type | Sequential | Fixed Parallel (3) | Adaptive |
|------------|------------|-------------------|----------|
| MacBook Pro M3 Max (16 cores) | ~12s/chunk | ~5s/chunk | ~3s/chunk |
| MacBook Air M2 (8 cores) | ~12s/chunk | ~6s/chunk | ~5s/chunk |
| Mac Mini Intel (4 cores) | ~15s/chunk | ~8s/chunk | ~8s/chunk |
| Low-end laptop (2 cores) | ~15s/chunk | Overloaded | ~12s/chunk |

## Troubleshooting

### System running slow during extraction
- Check resource monitor: `./scripts/pipeline/02_extract_entities_adaptive.sh --profile`
- Reduce workers: `export METAL_EXTRACTION_WORKERS=$(($(nproc) - 2))`
- Use lower profile: `export METAL_EXTRACTION_PROFILE=medium`

### Out of memory errors
- Force low memory mode: `export METAL_EXTRACTION_PROFILE=low`
- Reduce batch size in `config/extraction_profiles.json`
- Close other applications

### Extraction seems too conservative
- Your system may have more capability than detected
- Try: `export METAL_EXTRACTION_WORKERS=$(($(nproc) - 1))`
- Monitor with: `htop` or Activity Monitor

## Configuration Files

### `.env` (created by configure_environment.sh)
```bash
METAL_EXTRACTION_TIER=high
METAL_EXTRACTION_WORKERS=8
METAL_SYSTEM_CORES=16
METAL_SYSTEM_MEMORY_GB=128
```

### `config/extraction_profiles.json`
Contains detailed settings for each performance tier. Modify to customize behavior.

## Best Practices

1. **First Run**: Always run `./scripts/configure_environment.sh` on a new system
2. **Testing**: Start with small batches (5-10 chunks) to verify performance
3. **Production**: Let the system auto-scale unless you have specific requirements
4. **Monitoring**: Keep an eye on the throttle counter - occasional throttling is normal
5. **Apple Silicon**: Benefits from unified memory - can use more aggressive settings

## Advanced Tuning

For maximum performance on high-end systems:
```bash
# Use all cores except one
export METAL_EXTRACTION_WORKERS=$(($(sysctl -n hw.ncpu) - 1))

# Increase context window for better accuracy (slower)
python extraction/adaptive_parallel_extraction.py \
  --chunks chunks.json \
  --workers 10 \
  --context 32768
```

For battery-powered devices:
```bash
# Conservative settings to preserve battery
export METAL_EXTRACTION_PROFILE=low
export METAL_EXTRACTION_WORKERS=2
```

## Benchmarking

Run benchmarks to find optimal settings:
```bash
# Test different worker configurations
python extraction/adaptive_parallel_extraction.py --benchmark

# Full system benchmark
python scripts/automation/benchmark_extraction.py
```