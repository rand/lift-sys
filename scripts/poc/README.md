# POC Scripts

**Purpose**: Proof-of-Concept scripts for testing new technologies and approaches.

## Contents

### test_guidance_typescript_poc.py

**Status**: Ready for testing
**Purpose**: Phase 1 POC for llguidance/Guidance migration plan
**What it tests**:
- Guidance library integration with transformers models
- JSON Schema constrained generation using `gen()` function
- TypeScript code generation using our existing schemas
- Output validation and latency measurement

**Usage**:
```bash
# Run the POC
uv run python scripts/poc/test_guidance_typescript_poc.py

# Or make it executable and run directly
chmod +x scripts/poc/test_guidance_typescript_poc.py
./scripts/poc/test_guidance_typescript_poc.py
```

**Requirements**:
- Guidance library (already in dependencies)
- Transformers library: `uv add transformers torch`
- Small model for testing: microsoft/phi-2 (auto-downloaded)

**Expected outcome**:
- ✅ Model loads successfully
- ✅ Prompt generation works
- ✅ Schema-constrained generation completes
- ✅ Output validates against TypeScript schema
- ✅ Latency measurement provided

**Next steps after successful POC**:
1. Phase 2: Test with production-grade models
2. Compare latency vs XGrammar baseline
3. Benchmark quality metrics
4. Test complex TypeScript patterns
5. Integration into main codebase

## Adding New POCs

When adding new POC scripts:
1. Create script in this directory: `scripts/poc/your_poc_name.py`
2. Make it executable: `chmod +x scripts/poc/your_poc_name.py`
3. Include clear documentation in the script header
4. Update this README with script description
5. Follow the POC template structure (see test_guidance_typescript_poc.py)

## POC Template Structure

```python
#!/usr/bin/env python3
"""
POC: [Brief description]
Phase [N] of [initiative name]

Usage:
    uv run python scripts/poc/your_poc.py
"""

# 1. Imports
# 2. Helper functions
# 3. Main test function with clear sections
# 4. Validation and measurement
# 5. Success/failure reporting
# 6. Next steps documentation
```
