# AICI Integration Plan: Future Semantic Constraints

**Status**: 📋 **FUTURE WORK** - Revisit when >95% accuracy needed
**Created**: October 16, 2025
**Priority**: Low (current 90% success is excellent)

---

## Background

**Current Situation**:
- **Phase 5a** achieves **90% success** using XGrammar (syntax) + Assertion Validation (semantics)
- Remaining 10% failures are semantic bugs (type checking edge cases)
- XGrammar enforces JSON structure but **cannot enforce semantic constraints**

**Why AICI Could Help**:
- **Stateful controllers** can track generation context
- **Token-by-token logic** can detect anti-patterns during generation
- **Dynamic masking** can prevent specific code patterns

**Trade-off**:
- **Benefit**: Could improve 90% → 95-98%
- **Cost**: Significant complexity + development time
- **Risk**: May introduce false positives

---

## When to Revisit AICI

### Triggers (ANY of these)

1. **Success Rate Drops** 📉
   - Phase 3/4 tests show <80% success
   - Production usage reveals systematic failures
   - New bug categories beyond type checking

2. **Semantic Bugs Become Systematic** 🐛
   - Same pattern fails repeatedly (like get_type_name)
   - Retries + feedback don't improve results
   - Pattern can be precisely defined (no ambiguity)

3. **Upstream Improvements Insufficient** ⚠️
   - Prompt engineering doesn't help (tried Option 3)
   - AST pre-validation doesn't catch bugs (tried Option 2)
   - Only real-time constraint can solve

4. **Production Requirements** 🏭
   - Customer demands >95% accuracy
   - Safety-critical applications require guarantees
   - Cost of manual fixes > cost of AICI development

### Do NOT Revisit If

- ✅ Current 90% success is acceptable
- ✅ Manual fixes are rare and fast
- ✅ Upstream improvements haven't been tried yet
- ✅ Development time > benefit gained

---

## AICI Capabilities Review

### What AICI Provides

**Real-time Token Control**:
```python
class Controller:
    def on_token(self, token_id: int, state: State) -> Mask:
        # Custom logic per token
        # Return: ALLOW_TOKEN or MASK_TOKEN
        pass
```

**Stateful Generation Tracking**:
- Maintain context across tokens
- Remember function names, return statements
- Track code patterns (e.g., seen `type(` recently)

**WebAssembly Flexibility**:
- Write controllers in Rust, Python, JavaScript
- Compile to WebAssembly
- Run on CPU (parallel with GPU inference)

**Performance**:
- Controllers run alongside generation
- Near-zero overhead for simple logic
- Scales with complexity of controller

### What AICI Cannot Do

**Ambiguity Resolution**:
- Can't distinguish `type()` used correctly vs incorrectly
- Context-sensitive logic requires perfect understanding

**Semantic Understanding**:
- Still operates on tokens, not meaning
- Can detect patterns but not intent

**Guarantee Correctness**:
- May have false positives (block valid code)
- May have false negatives (miss subtle bugs)

---

## Integration Approach

### Phase 1: Research & Prototyping (2-3 weeks)

**Objectives**:
1. Set up AICI development environment
2. Create proof-of-concept controller
3. Test on get_type_name bug
4. Measure impact and overhead

**Tasks**:
- [ ] Install AICI framework
- [ ] Study AICI documentation and examples
- [ ] Identify targetable patterns (type(), __name__, etc.)
- [ ] Implement simple controller (block type computation)
- [ ] Test on Phase 2 get_type_name
- [ ] Measure: Success rate improvement, latency overhead, false positives

**Success Criteria**:
- ✅ Controller blocks type(value).__name__ pattern
- ✅ get_type_name test passes
- ✅ No false positives on other tests
- ✅ Latency overhead <10%

### Phase 2: Production Controller (2-3 weeks)

**Objectives**:
1. Expand controller to handle multiple patterns
2. Integrate with lift-sys pipeline
3. Add configuration for pattern management
4. Implement fallback strategies

**Tasks**:
- [ ] Create pattern library (anti-patterns to block)
- [ ] Implement stateful tracking (function context)
- [ ] Add configuration file for patterns
- [ ] Integrate with Modal provider
- [ ] Add override mechanism (allow patterns when needed)
- [ ] Comprehensive testing on all phases

**Success Criteria**:
- ✅ Phase 2 success rate >95%
- ✅ Phase 3 success rate >85%
- ✅ Configurable pattern library
- ✅ No regressions on passing tests

### Phase 3: Monitoring & Refinement (Ongoing)

**Objectives**:
1. Monitor for false positives/negatives
2. Tune patterns based on real usage
3. Add new patterns as bugs discovered
4. Optimize performance

**Tasks**:
- [ ] Implement telemetry (pattern hits, blocks)
- [ ] Set up alerting for false positives
- [ ] Create feedback loop for pattern updates
- [ ] Regular performance profiling
- [ ] Document known limitations

**Success Criteria**:
- ✅ <5% false positive rate
- ✅ Pattern updates deployed within days
- ✅ Performance stable over time

---

## Implementation Details

### Controller Architecture

**File**: `lift_sys/constraints/aici_controller.py`

```python
class LiftSysSemanticController:
    """AICI controller for semantic code constraints."""

    def __init__(self, config: ControllerConfig):
        self.patterns = config.anti_patterns
        self.state = GenerationState()

    def on_token(self, token_id: int) -> Mask:
        """Called for each token generated."""
        token = self.decode_token(token_id)

        # Track state
        self.state.update(token)

        # Check anti-patterns
        for pattern in self.patterns:
            if pattern.matches(self.state.recent_tokens):
                if pattern.should_block(self.state.context):
                    return MASK_TOKEN

        return ALLOW_TOKEN

    def on_completion(self, text: str) -> bool:
        """Called when generation completes."""
        # Final validation
        return True
```

**Pattern Configuration**: `lift_sys/constraints/patterns.yaml`

```yaml
patterns:
  - name: type_computation
    description: Block dynamic type computation in type checkers
    tokens: ["type", "(", "value", ")"]
    context:
      function_purpose: type_checking
      return_type: string
    action: block

  - name: class_name_access
    description: Block __class__.__name__ pattern
    tokens: ["__class__", ".", "__name__"]
    context:
      function_purpose: type_checking
    action: block

  - name: str_type_conversion
    description: Block str(type(x)) pattern
    tokens: ["str", "(", "type", "("]
    action: block
```

### Integration with Modal Provider

**File**: `lift_sys/providers/modal_provider.py`

```python
class ModalProvider(BaseProvider):
    def __init__(self, endpoint_url: str, aici_enabled: bool = False):
        self.aici_enabled = aici_enabled
        if aici_enabled:
            self.controller = LiftSysSemanticController.load()

    async def generate_structured(self, prompt: str, schema: dict, **kwargs):
        if self.aici_enabled:
            # Use AICI-enabled endpoint
            kwargs['controller'] = self.controller.to_wasm()

        # Standard generation
        result = await self._client.post(...)
        return result
```

### Testing Strategy

**Unit Tests**: Test individual patterns
```python
def test_type_computation_blocked():
    controller = LiftSysSemanticController(patterns=["type_computation"])
    tokens = ["return", " ", "type", "(", "value", ")"]

    for token in tokens:
        if token in ["type", "("]:
            assert controller.on_token(token) == MASK_TOKEN
```

**Integration Tests**: Test on real code generation
```python
async def test_get_type_name_with_aici():
    provider = ModalProvider(aici_enabled=True)
    result = await generator.generate(ir=get_type_name_ir)

    # Should NOT contain type(value).__name__
    assert "type(value).__name__" not in result.source_code
    assert "return 'other'" in result.source_code
```

**Regression Tests**: Ensure no false positives
```python
async def test_valid_type_usage_allowed():
    """Test that valid type() usage is not blocked."""
    ir = create_ir("Function that checks if value is instance of a type")

    result = await generator.generate(ir)
    # Should be able to use isinstance(value, type)
    assert result.success
```

---

## Cost-Benefit Analysis

### Estimated Effort

| Phase | Duration | Lines of Code | Risk |
|-------|----------|---------------|------|
| Research & Prototyping | 2-3 weeks | 500 | Low |
| Production Controller | 2-3 weeks | 1500 | Medium |
| Monitoring & Refinement | Ongoing | 500/quarter | Low |
| **Total Initial** | **4-6 weeks** | **2000** | **Medium** |

### Expected Benefits

| Metric | Current | With AICI | Improvement |
|--------|---------|-----------|-------------|
| Phase 2 Success | 90% | 95-98% | +5-8% |
| Phase 3 Success | 80%? | 85-90% | +5-10% |
| get_type_name | ❌ | ✅ | Fixed |
| Manual Fixes | 1/10 | 1/20 | 50% reduction |

### Risks

**Technical Risks**:
- AICI framework immature (may have bugs)
- WebAssembly overhead unpredictable
- Pattern matching brittle (context-dependent)

**Development Risks**:
- Learning curve (3-5 days)
- Integration complexity (multiple touch points)
- Testing burden (many edge cases)

**Operational Risks**:
- False positives block valid code
- False negatives miss bugs
- Pattern library maintenance overhead

### Decision Criteria

**Go Ahead If**:
- Success rate <80% on Phase 3
- Manual fix rate >10%
- Customer demands >95% accuracy
- Other approaches tried and failed

**Don't Proceed If**:
- Current success rate acceptable
- Upstream improvements not tried
- Development time > manual fix time
- Team lacks WebAssembly expertise

---

## Alternatives (Try These First)

### Option 1: Upstream Prompt Engineering (Easiest)

**Effort**: 2-4 hours
**Impact**: 90% → 95% (estimated)
**Risk**: Low

**Approach**: Add few-shot examples to IR generation prompt
```
When generating type-checking functions:

CORRECT ✅:
def check_type(value):
    if isinstance(value, bool):  # Check bool BEFORE int!
        return 'other'
    if isinstance(value, int):
        return 'int'
    ...
    return 'other'  # Literal string, not type(value).__name__

INCORRECT ❌:
def check_type(value):
    if isinstance(value, int):
        return 'int'
    else:
        return type(value).__name__  # Don't compute types!
```

### Option 2: AST-Level Pre-Validation (Moderate)

**Effort**: 8-12 hours
**Impact**: 90% → 92-95% (estimated)
**Risk**: Low-Medium

**Approach**: Parse generated code, detect anti-patterns, retry before execution
```python
def check_for_type_computation(code: str) -> list[str]:
    tree = ast.parse(code)
    issues = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id == "type":
                issues.append("Found type(value) call - use literal strings instead")
    return issues
```

### Option 3: Accept 90% Success (Pragmatic)

**Effort**: 0 hours
**Impact**: Current performance maintained
**Risk**: None

**Rationale**:
- 90% is excellent for ML systems
- Manual fixes rare and fast
- Diminishing returns beyond 90%
- Focus effort on higher-value features

---

## Monitoring & Success Metrics

### Metrics to Track (If AICI Implemented)

**Performance**:
- Success rate per phase (target: >95%)
- Generation latency (target: <10% overhead)
- Token-level overhead (measure per-token time)

**Quality**:
- False positive rate (target: <5%)
- False negative rate (target: <5%)
- Pattern hit rate (how often patterns trigger)

**Operational**:
- Pattern update frequency
- Time to add new pattern (target: <1 day)
- Controller crash rate (target: <1%)

### Dashboard (If Implemented)

```
AICI Controller Dashboard
=========================

Success Rates (Last 7 Days):
  Phase 2: 96.2% (↑ 6.2%)
  Phase 3: 87.5% (↑ 7.5%)

Pattern Hits (Last 24 Hours):
  type_computation: 12 blocks, 0 false positives
  class_name_access: 5 blocks, 1 false positive
  str_type_conversion: 3 blocks, 0 false positives

Performance:
  Avg. Generation Time: 2.15s (↑ 0.05s)
  Controller Overhead: 2.3% (target: <10%)
```

---

## Conclusion

### Current Recommendation: ⏸️ **WAIT**

**Rationale**:
1. ✅ **90% success is excellent** - At high end of industry standards
2. ✅ **Upstream improvements untried** - Option 1 (prompt engineering) likely to help
3. ✅ **Significant effort required** - 4-6 weeks for AICI integration
4. ✅ **Diminishing returns** - Going from 90% → 95% costs 10x effort

### When to Revisit: If ANY of

1. Phase 3 shows <80% success
2. Upstream improvements fail (tried Options 1+2)
3. Customer demands >95% accuracy
4. Semantic bugs become systematic

### Next Steps (Before AICI)

1. ✅ **Accept 90% success** - Document known limitation
2. ✅ **Proceed to Phase 3** - Validate on harder tests
3. 🔄 **Try prompt engineering** (if needed) - Option 1, 2-4 hours
4. 🔄 **Try AST pre-validation** (if needed) - Option 2, 8-12 hours
5. 📋 **Revisit AICI** (if still needed) - This plan

---

**Plan Status**: 📋 Ready for future implementation
**Decision**: Wait for stronger signal before proceeding
**Review Date**: After Phase 3 completion

**This plan will be revisited when success rate drops below 80% or production requirements demand >95% accuracy.**
