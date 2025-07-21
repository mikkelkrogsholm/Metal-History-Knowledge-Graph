#!/bin/bash
# Configure extraction environment based on system capabilities

set -e

echo "🔧 Configuring Metal History extraction environment..."
echo ""

# Get project root directory
PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

# Activate virtual environment
if [ -z "$VIRTUAL_ENV" ]; then
    if [ -f "$PROJECT_ROOT/venv/bin/activate" ]; then
        source "$PROJECT_ROOT/venv/bin/activate"
    fi
fi

# Run system profiler and capture output
PROFILE_OUTPUT=$(python "$PROJECT_ROOT/scripts/automation/system_profiler.py" --json)

# Extract key values using Python
python << EOF
import json
import os

profile = json.loads('''$PROFILE_OUTPUT''')

# Extract values
tier = profile['profile']['performance_tier']
cores = profile['profile']['cpu']['physical_cores']
memory_gb = profile['profile']['memory']['total_gb']
workers = profile['extraction_settings']['parallel_workers']

print(f"System detected:")
print(f"  Performance tier: {tier.upper()}")
print(f"  CPU cores: {cores}")
print(f"  Total memory: {memory_gb} GB")
print(f"  Recommended workers: {workers}")
print()

# Create .env file if it doesn't exist
env_file = os.path.join('$PROJECT_ROOT', '.env')
env_lines = []

if os.path.exists(env_file):
    with open(env_file, 'r') as f:
        env_lines = [line.strip() for line in f if not line.startswith('METAL_')]

# Add our settings
env_lines.extend([
    f"METAL_EXTRACTION_TIER={tier}",
    f"METAL_EXTRACTION_WORKERS={workers}",
    f"METAL_SYSTEM_CORES={cores}",
    f"METAL_SYSTEM_MEMORY_GB={int(memory_gb)}"
])

# Write back
with open(env_file, 'w') as f:
    f.write('\\n'.join(env_lines) + '\\n')

print(f"✅ Environment configured in .env file")
print()
print("You can override auto-detection by setting:")
print("  export METAL_EXTRACTION_PROFILE=medium  # Force medium profile")
print("  export METAL_EXTRACTION_WORKERS=4       # Force 4 workers")
EOF

# Show extraction command examples
echo ""
echo "📝 Example commands for your system:"
echo ""
echo "# Quick test (5 chunks):"
echo "./scripts/pipeline/02_extract_entities_adaptive.sh chunks_optimized.json 5"
echo ""
echo "# Full extraction with auto-scaling:"
echo "./scripts/pipeline/02_extract_entities_adaptive.sh"
echo ""
echo "# Manual override (e.g., for testing):"
echo "./scripts/pipeline/02_extract_entities_adaptive.sh chunks_optimized.json \"\" 2  # Use 2 workers"
echo ""
echo "# Profile system:"
echo "./scripts/pipeline/02_extract_entities_adaptive.sh --profile"