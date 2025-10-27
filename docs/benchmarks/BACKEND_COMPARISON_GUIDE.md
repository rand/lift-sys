# Backend Comparison Benchmark Guide

**Last Updated**: 2025-10-27
**Purpose**: Compare llguidance vs XGrammar performance
**Script**: `scripts/benchmarks/compare_backends.py`

---

## Overview

This benchmark compares the performance of llguidance and XGrammar backends for constrained JSON generation. It measures:

- **Success Rate**: Percentage of prompts that produce valid schema-compliant output
- **Latency**: End-to-end time from request to response
- **Token Throughput**: Tokens generated per second
- **Reliability**: Failure modes and error rates

## Prerequisites

### 1. llguidance Endpoint (Already Deployed)

Current llguidance endpoint:
```
https://rand--qwen-80b-generate.modal.run
```

This is the primary production endpoint running vLLM 0.11.0 with llguidance.

### 2. XGrammar Endpoint (Must Deploy Separately)

To run a comparison, you need to deploy an XGrammar endpoint. Two options:

#### Option A: Deploy Separate XGrammar App

Create `lift_sys/inference/modal_qwen_xgrammar.py` based on the llguidance version but with XGrammar backend:

```python
# In modal_qwen_vllm.py, change:
guided_decoding_backend="guidance"  # llguidance

# To:
guided_decoding_backend="xgrammar"  # XGrammar
```

Deploy:
```bash
modal deploy lift_sys/inference/modal_qwen_xgrammar.py --name qwen-xgrammar
```

This creates:
```
https://rand--xgrammar-generate.modal.run
```

#### Option B: Use Historical Data

If you have cached XGrammar responses from before the migration, you can analyze those for comparison without deploying a new endpoint.

## Running the Benchmark

### Basic Usage

```bash
# Compare llguidance (current) vs XGrammar (must deploy first)
python scripts/benchmarks/compare_backends.py \
    --llguidance https://rand--qwen-80b-generate.modal.run \
    --xgrammar https://rand--xgrammar-generate.modal.run
```

### Advanced Options

```bash
# Run more tests for statistical significance
python scripts/benchmarks/compare_backends.py \
    --num-tests 100 \
    --timeout 180 \
    --output validation/benchmark_results_$(date +%Y%m%d).json
```

### Parameters

- `--llguidance URL`: llguidance endpoint (default: current production)
- `--xgrammar URL`: XGrammar endpoint (must specify)
- `--num-tests N`: Number of test prompts (default: 50, max: 50)
- `--timeout SECS`: Timeout per request (default: 120s)
- `--output FILE`: Save detailed JSON results

## Test Prompts

The benchmark includes 50 carefully designed test prompts:

1. **Simple functions** (10): Basic operations (add, multiply, reverse)
2. **Medium complexity** (10): List operations, string processing, validation
3. **Complex algorithms** (10): Binary search, quicksort, graph algorithms
4. **Edge cases** (10): Error handling, optional parameters, type hints
5. **Real-world scenarios** (10): JSON parsing, password validation, URL sanitization

All prompts use a standardized function generation schema with required fields:
- `name` (string)
- `parameters` (array of objects)
- `returns` (string)
- `body` (string, function implementation)
- `description` (string, optional)

## Interpreting Results

### Success Rate

```
Success Rate:  llguidance: 85.0%  XGrammar: 4.8%
```

- **Target**: >50% (baseline)
- **Goal**: >80% (production-ready)
- **Baseline**: XGrammar was 4.8% in Phase 1 validation

### Latency Metrics

```
Latency (successful runs):
  Average:        llguidance: 16.2s  XGrammar: 85.3s
  Median:         llguidance: 14.8s  XGrammar: 82.1s
  P95:            llguidance: 28.5s  XGrammar: 124.7s
```

- **Average**: Mean latency for successful generations
- **Median**: Middle value (less affected by outliers)
- **P95**: 95th percentile (worst-case for 95% of requests)
- **P99**: 99th percentile (extreme cases)

### Improvement Calculation

```
Improvement (llguidance vs XGrammar):
  Success rate:   +80.2 percentage points
  Latency reduction: +81.0%
  Speedup:        5.3x faster
```

- **Success rate improvement**: Absolute percentage point difference
- **Latency reduction**: Percentage faster
- **Speedup**: Multiplicative factor (XGrammar time / llguidance time)

## Example Output

```
🔬 Starting benchmark comparison
   llguidance endpoint: https://rand--qwen-80b-generate.modal.run
   XGrammar endpoint: https://rand--xgrammar-generate.modal.run
   Number of tests: 50
   Timeout: 120s

Testing llguidance backend...
  [1/50] Testing: Write a Python function that adds two numbers...
    ✅ 2.34s
  [2/50] Testing: Write a Python function that checks if a number is even...
    ✅ 1.87s
  ...

Testing XGrammar backend...
  [1/50] Testing: Write a Python function that adds two numbers...
    ❌ 120.00s (Timeout)
  [2/50] Testing: Write a Python function that checks if a number is even...
    ✅ 78.23s
  ...

================================================================================
BENCHMARK COMPARISON: llguidance vs XGrammar
================================================================================

Metric                              llguidance             XGrammar
--------------------------------------------------------------------------------
Total Tests                                 50                   50
Successes                                   42                    3
Failures                                     8                   47
Success Rate                             84.0%                 6.0%

Latency (successful runs):
  Average                               14.2s                82.5s
  Median                                13.1s                79.3s
  Min                                    1.8s                65.2s
  Max                                   32.7s               103.8s
  P95                                   27.4s                98.1s
  P99                                   31.2s               102.4s

Token Usage (avg):
  Tokens per request                    127.3                134.7

Improvement (llguidance vs XGrammar):
  Success rate                   +78.0 percentage points
  Latency reduction                      +82.8%
  Speedup                                  5.8x

================================================================================

📊 Detailed results saved to: validation/benchmark_results_20251027.json
```

## Analyzing Detailed Results

The JSON output contains full details for every test:

```json
{
  "timestamp": "2025-10-27T15:30:00",
  "llguidance": {
    "stats": { /* aggregate statistics */ },
    "results": [
      {
        "backend": "llguidance",
        "prompt": "Write a Python function that adds two numbers",
        "success": true,
        "latency_seconds": 2.34,
        "tokens_used": 45,
        "generation_time_ms": 2123.5,
        "finish_reason": "stop",
        "output": { /* generated function */ }
      },
      // ... more results
    ]
  },
  "xgrammar": { /* same structure */ }
}
```

Use this data for:
- Identifying which prompt types succeed/fail
- Analyzing error patterns
- Comparing token usage
- Statistical significance testing

## When to Run Benchmarks

Run benchmarks when:

1. **After major changes**: New backend, model version, or vLLM update
2. **Before production**: Validate performance meets requirements
3. **Regular monitoring**: Monthly or quarterly to track regressions
4. **Comparing options**: Testing different backends or configurations

## Current Status (2025-10-27)

- ✅ **llguidance endpoint**: Deployed and validated
- ❌ **XGrammar endpoint**: Not currently deployed (old endpoint stopped)
- ⏳ **Benchmark ready**: Script complete, waiting for XGrammar deployment

**Next Steps**:
1. Decide if XGrammar comparison is needed
2. If yes, deploy XGrammar endpoint temporarily
3. Run benchmark with both endpoints
4. Document results for historical comparison

## Alternative: Historical Comparison

If you don't want to deploy XGrammar again, you can document the comparison using:

1. **Phase 1 validation data**: 4.8% success rate, ~85s latency (documented)
2. **Current llguidance data**: From recent test runs
3. **Estimated improvement**: Based on available metrics

This avoids the cost of deploying and running XGrammar for comparison.

---

## References

- **Benchmark Script**: `scripts/benchmarks/compare_backends.py`
- **Phase 1 XGrammar Results**: `validation/PHASE1_VALIDATION_ANALYSIS.md`
- **Phase 3 llguidance Results**: `validation/PHASE3_LLGUIDANCE_MIGRATION_RESULTS.md`
- **Infrastructure Status**: `validation/PHASE3_INFRASTRUCTURE_FIXES_STATUS.md`
