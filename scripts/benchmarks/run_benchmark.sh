#!/bin/bash
# Quick runner for performance benchmarks

set -e

echo "==================================="
echo "lift-sys Performance Benchmark"
echo "==================================="
echo ""

# Check if Modal endpoint is available
echo "Checking Modal endpoint..."
if curl -s --max-time 5 https://rand--generate.modal.run/health > /dev/null 2>&1; then
    echo "✓ Modal endpoint is responding"
else
    echo "✗ Warning: Modal endpoint may be down or slow to respond"
    echo "  Cold start may take ~3 minutes"
fi

echo ""
echo "Starting benchmark..."
echo ""

# Navigate to repo root and run the benchmark
cd "$(dirname "$0")/../.."
uv run python performance_benchmark.py

echo ""
echo "==================================="
echo "Benchmark complete!"
echo "==================================="
