# Experiments

This directory contains proof-of-concept experiments and research validation code.

## PoC 1: xgrammar IR Generation

**Goal**: Validate that xgrammar can enforce lift-sys's IR JSON schema with 95%+ success rate and <2s latency.

**Status**: ✅ Baseline validated (100% schema compliance)

**Files**:
- `poc_xgrammar_ir.py` - Main PoC script

**Running**:
```bash
uv run python experiments/poc_xgrammar_ir.py
```

**Next Steps**:
1. Integrate xgrammar with Anthropic LLM for real prompt → IR generation
2. Test with actual semantic IR generation (not just templates)
3. Measure quality of generated IR (beyond schema validation)

## Future PoCs

- **PoC 2**: xgrammar + ChatLSP quality improvement (Week 5)
- **PoC 3**: Loom-inspired assertion extraction (Week 15)
