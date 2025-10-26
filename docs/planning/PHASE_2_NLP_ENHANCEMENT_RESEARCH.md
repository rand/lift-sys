# NLP Enhancement Research (lift-sys-372)

**Date**: 2025-10-26
**Status**: Research Complete
**Related Issue**: lift-sys-372
**Estimated Effort**: 13-18 hours

---

## Current NLP Extraction

### Location

**Main extraction code:**
- `/Users/rand/src/lift-sys/lift_sys/forward_mode/xgrammar_translator.py` - Primary NLP→IR translation
- `/Users/rand/src/lift-sys/lift_sys/forward_mode/best_of_n_translator.py` - Best-of-N sampling wrapper
- `/Users/rand/src/lift-sys/lift_sys/ir/constraint_detector.py` - Automatic constraint detection from IR
- `/Users/rand/src/lift-sys/lift_sys/nlp/pipeline.py` - Semantic analysis pipeline (ICS Phase 1)

**Prompt engineering:**
- `/Users/rand/src/lift-sys/lift_sys/ir/schema.py` - `get_prompt_for_ir_generation()` function (lines 320-436)
- Contains extensive prompt engineering for effects, assertions, loop patterns, return constraints

**Post-processing:**
- `/Users/rand/src/lift-sys/lift_sys/ir/constraint_detector.py` - `detect_and_apply_constraints()` (lines 393-417)
- `/Users/rand/src/lift-sys/lift_sys/forward_mode/xgrammar_translator.py` - `_json_to_ir()` (lines 221-292)
- `/Users/rand/src/lift-sys/lift_sys/forward_mode/best_of_n_translator.py` - `_score_ir()` (lines 117-210)

### What We Extract Today

**Constraint types extracted:**
1. **Effects** (`EffectClause`) - Side effects and external interactions
2. **Assertions** (`AssertClause`) - Logical predicates (preconditions, postconditions, invariants)
3. **Return Constraints** (`ReturnConstraint`) - Ensures computed values are returned
4. **Loop Behavior Constraints** (`LoopBehaviorConstraint`) - FIRST_MATCH, LAST_MATCH, ALL_MATCHES patterns
5. **Position Constraints** (`PositionConstraint`) - Element positioning requirements (e.g., @ and . in emails)

**Extraction method:**
- **Primary**: LLM-based extraction via Modal.com (Qwen2.5-Coder-32B-Instruct + XGrammar)
- **Schema**: JSON schema with xgrammar constrained generation
- **Post-processing**: Automatic constraint detection via regex patterns and keyword matching
- **NLP Libraries**:
  - spaCy 3.7+ (installed, used in ICS pipeline for entities/dependencies)
  - NLTK 3.8+ (installed, used in paraphrase generation)
  - HuggingFace Transformers (installed, used for advanced NER)

**Accuracy:**
- Performance benchmarks show ~60% real success rate on forward mode
- Median latency: ~16s for full IR generation
- Quality scoring via Best-of-N improves selection (assertion count, effect detail, literal detection, etc.)

### Current Relationship/Effect/Assertion Extraction

**Effects (CURRENTLY IMPLEMENTED):**
- Extracted via LLM prompt engineering in `schema.py`
- Prompt includes extensive guidance on explicit returns, literal values, loop patterns, control flow
- Stored as `EffectClause` objects with `description` field
- Post-validation ensures effects are present
- **Gap**: Effects are free-text descriptions, not structured relationships

**Assertions (CURRENTLY IMPLEMENTED):**
- Extracted via LLM prompt engineering in `schema.py`
- Stored as `AssertClause` objects with `predicate` and `rationale` fields
- Constraint detector analyzes assertions to identify position constraints
- **Gap**: Assertions are logical predicates, not structured property constraints

**Relationships (NOT YET IMPLEMENTED):**
- `nlp/pipeline.py` has stub: `_extract_relationships()` returns `[]` (line 228-233)
- Comment: "TODO: Implement relationship extraction using spaCy dependencies"
- ICS Phase 2 plan calls for implementing this
- **Gap**: No structured entity-to-entity relationships extracted

---

## Extension Points for Phase 2

### Relationships

**Code locations to modify:**
1. `/Users/rand/src/lift-sys/lift_sys/nlp/pipeline.py:228-233` - Implement `_extract_relationships()`
2. `/Users/rand/src/lift-sys/lift_sys/ir/schema.py` - Add `relationships` field to IR JSON schema
3. `/Users/rand/src/lift-sys/lift_sys/ir/models.py` - Add `RelationshipClause` dataclass
4. `/Users/rand/src/lift-sys/lift_sys/causal/dataflow_extractor.py` - Already extracts dataflow relationships from AST (can be adapted)

**Detection patterns:**
- **Dependency**: "X depends on Y", "X requires Y", "X uses Y", "X needs Y"
- **Creation**: "X creates Y", "X generates Y", "X produces Y", "X initializes Y"
- **Modification**: "X modifies Y", "X updates Y", "X changes Y", "X transforms Y"
- **Temporal**: "X before Y", "X after Y", "X during Y", "X triggers Y"
- **Causal**: "X causes Y", "X results in Y", "X leads to Y", "if X then Y"
- **Composition**: "X contains Y", "X includes Y", "X is part of Y"

**Example extractions:**
1. "Process input and return result" →
   - Relationship 1: `{from: "process", to: "input", type: "USES"}`
   - Relationship 2: `{from: "process", to: "result", type: "PRODUCES"}`
2. "Validate email before saving to database" →
   - Relationship 1: `{from: "validate", to: "email", type: "OPERATES_ON"}`
   - Relationship 2: `{from: "save", to: "database", type: "WRITES_TO"}`
   - Relationship 3: `{from: "validate", to: "save", type: "PRECEDES"}`
3. "Count depends on list length" →
   - Relationship 1: `{from: "count", to: "list.length", type: "DEPENDS_ON"}`

### Effects

**Code locations to modify:**
1. `/Users/rand/src/lift-sys/lift_sys/nlp/pipeline.py:133-134` - Implement effect detection (currently returns `[]`)
2. `/Users/rand/src/lift-sys/lift_sys/ir/schema.py:349-425` - Enhance effect extraction prompts
3. `/Users/rand/src/lift-sys/lift_sys/ir/models.py:197-210` - Potentially add structured fields to `EffectClause`

**Detection patterns:**
- **State modification**: "X modifies Y", "X changes Y state", "X updates Y"
- **Side effects**: "X writes to Y", "X logs Y", "X prints Y", "X sends Y"
- **Resource effects**: "X opens Y", "X closes Y", "X allocates Y", "X frees Y"
- **Control flow effects**: "X raises Y", "X throws Y", "X terminates Y"

**Example extractions:**
1. "Process input and return result" →
   - Effect 1: `{action: "process", target: "input", type: "TRANSFORM"}`
   - Effect 2: `{action: "return", target: "result", type: "OUTPUT"}`
2. "Save user data to database" →
   - Effect 1: `{action: "save", target: "database", type: "WRITE", entity: "user_data"}`
3. "Print error message and exit" →
   - Effect 1: `{action: "print", target: "stdout", type: "IO", content: "error_message"}`
   - Effect 2: `{action: "exit", target: "program", type: "TERMINATE"}`

### Assertions

**Code locations to modify:**
1. `/Users/rand/src/lift-sys/lift_sys/nlp/pipeline.py:134-135` - Implement assertion detection (currently returns `[]`)
2. `/Users/rand/src/lift-sys/lift_sys/ir/constraint_detector.py` - Enhance pattern detection
3. `/Users/rand/src/lift-sys/lift_sys/ir/models.py:213-227` - Potentially add structured fields to `AssertClause`

**Detection patterns:**
- **Type assertions**: "X must be Y", "X is Y", "X should be Y type"
- **Range assertions**: "X > Y", "X < Y", "X between Y and Z", "X in range [Y, Z]"
- **State assertions**: "X must not be null", "X is valid", "X is initialized"
- **Relational assertions**: "X equals Y", "X matches Y", "X contains Y"
- **Logical assertions**: "if X then Y", "X implies Y", "X or Y", "X and Y"

**Example extractions:**
1. "Input must be positive integer" →
   - Assertion 1: `{property: "input.type", operator: "==", value: "int", confidence: 0.9}`
   - Assertion 2: `{property: "input", operator: ">", value: "0", confidence: 0.9}`
2. "Email must contain @ and ." →
   - Assertion 1: `{property: "email", operator: "contains", value: "@", confidence: 1.0}`
   - Assertion 2: `{property: "email", operator: "contains", value: ".", confidence: 1.0}`
3. "Result should not be None" →
   - Assertion 1: `{property: "result", operator: "!=", value: "None", confidence: 0.8}`

---

## Implementation Plan

### Files to modify

1. **`lift_sys/ir/models.py`** - Add new IR clause types
   - Add `RelationshipClause` dataclass with fields: `from_entity`, `to_entity`, `relationship_type`, `confidence`
   - Add structured fields to `EffectClause`: `action`, `target`, `effect_type`
   - Add structured fields to `AssertClause`: `property`, `operator`, `value`

2. **`lift_sys/ir/schema.py`** - Update JSON schema and prompts
   - Add `relationships` array to IR schema
   - Enhance effect extraction prompts with structured output examples
   - Enhance assertion extraction prompts with property/operator/value format

3. **`lift_sys/nlp/pipeline.py`** - Implement extraction methods
   - Implement `_extract_relationships()` using spaCy dependency parsing
   - Implement `_detect_effects()` using verb phrase detection
   - Implement `_detect_assertions()` using conditional/constraint patterns

4. **`lift_sys/nlp/relationship_extractor.py`** - NEW FILE
   - Create dedicated relationship extraction module
   - Use spaCy dependency trees to identify subject-verb-object patterns
   - Use DSPy signatures for complex relationship inference

5. **`lift_sys/dspy_signatures/semantic_extraction.py`** - Enhance DSPy signatures
   - Add `RelationshipExtractorSignature`
   - Add `EffectExtractorSignature`
   - Add `AssertionExtractorSignature`

6. **`lift_sys/forward_mode/xgrammar_translator.py`** - Update translation
   - Modify `_json_to_ir()` to handle new relationship fields
   - Add relationship validation

### New test cases

1. **Relationship extraction test**:
   ```python
   # Input: "Process input and return result"
   # Expected:
   relationships = [
       {"from": "process", "to": "input", "type": "USES", "confidence": 0.85},
       {"from": "process", "to": "result", "type": "PRODUCES", "confidence": 0.85}
   ]
   ```

2. **Effect extraction test**:
   ```python
   # Input: "Save user data to database and log the action"
   # Expected:
   effects = [
       {"action": "save", "target": "database", "type": "WRITE", "entity": "user_data"},
       {"action": "log", "target": "log_file", "type": "WRITE", "entity": "action"}
   ]
   ```

3. **Assertion extraction test**:
   ```python
   # Input: "Input must be a positive integer between 1 and 100"
   # Expected:
   assertions = [
       {"property": "input.type", "operator": "==", "value": "int"},
       {"property": "input", "operator": ">", "value": "0"},
       {"property": "input", "operator": "<=", "value": "100"}
   ]
   ```

4. **Complex relationship test**:
   ```python
   # Input: "Validate email before saving to database, then send confirmation"
   # Expected:
   relationships = [
       {"from": "validate", "to": "email", "type": "OPERATES_ON"},
       {"from": "validate", "to": "save", "type": "PRECEDES"},
       {"from": "save", "to": "database", "type": "WRITES_TO"},
       {"from": "save", "to": "send", "type": "PRECEDES"},
       {"from": "send", "to": "confirmation", "type": "PRODUCES"}
   ]
   ```

5. **Integrated extraction test**:
   ```python
   # Input: "Function counts words in text and returns the count"
   # Expected:
   {
       "relationships": [
           {"from": "count_words", "to": "text", "type": "USES"},
           {"from": "count_words", "to": "count", "type": "PRODUCES"}
       ],
       "effects": [
           {"action": "split", "target": "text", "type": "TRANSFORM"},
           {"action": "count", "target": "words", "type": "COMPUTE"},
           {"action": "return", "target": "count", "type": "OUTPUT"}
       ],
       "assertions": [
           {"property": "text", "operator": "is_type", "value": "str"},
           {"property": "count", "operator": ">=", "value": "0"}
       ]
   }
   ```

### Estimated complexity

**MEDIUM** - Total: 13-18 hours

**Breakdown:**
- Relationship extraction: **4-5 hours** (spaCy dependencies + DSPy)
- Effect detection: **3-4 hours** (verb phrase analysis)
- Assertion detection: **3-4 hours** (pattern matching + DSPy)
- Schema updates: **1-2 hours**
- Testing: **2-3 hours**

**Factors reducing complexity:**
- ✅ NLP infrastructure already in place (spaCy, HuggingFace, DSPy installed)
- ✅ IR schema and models are extensible (dataclasses)
- ✅ Constraint detection framework exists (can be adapted)
- ✅ Similar patterns already implemented (entity extraction, modal detection)
- ✅ Causal graph extractors provide dataflow relationship precedent

**Factors increasing complexity:**
- ⚠️ Relationship extraction requires sophisticated dependency parsing
- ⚠️ Effect detection needs verb phrase analysis and semantic role labeling
- ⚠️ Assertion extraction requires logical operator detection
- ⚠️ Need to maintain backward compatibility with existing IR structure
- ⚠️ Testing requires diverse natural language examples
- ⚠️ DSPy signatures need careful prompt engineering for quality

---

## Risks & Considerations

**Risk 1: Relationship extraction accuracy**
- **Issue**: Dependency parsing may miss implicit relationships
- **Mitigation**: Combine spaCy dependencies with DSPy-based semantic inference
- **Example**: "The system validates user input" - spaCy sees subject-verb-object, DSPy infers OPERATES_ON relationship

**Risk 2: Effect vs. Relationship disambiguation**
- **Issue**: "X modifies Y" could be both an effect and a relationship
- **Mitigation**: Effects describe what happens, relationships describe connections - extract both
- **Example**: "Update database" → Effect: {action: "update", target: "database"}, Relationship: {from: "function", to: "database", type: "MODIFIES"}

**Risk 3: Schema compatibility**
- **Issue**: Adding new fields may break existing IR consumers
- **Mitigation**: Make new fields optional, maintain backward compatibility
- **Strategy**: Use `field(default_factory=list)` for new relationship/effect/assertion lists

**Risk 4: Prompt engineering complexity**
- **Issue**: LLM may not consistently extract structured relationships
- **Mitigation**: Use xgrammar constrained generation with strict schema
- **Fallback**: Use spaCy/regex patterns if LLM extraction fails

**Risk 5: Performance degradation**
- **Issue**: Additional extraction steps may increase latency
- **Mitigation**: Run extractions in parallel, cache results, optimize prompts
- **Target**: Keep total latency under 5s (currently ~16s median)

**Risk 6: Test coverage**
- **Issue**: Need diverse natural language examples to validate extraction
- **Mitigation**: Use ICS Phase 1 mock patterns as test baseline, add edge cases
- **Strategy**: Create test suite with 20+ examples covering all relationship/effect/assertion types

**Risk 7: spaCy model limitations**
- **Issue**: `en_core_web_sm` may not capture complex dependencies
- **Mitigation**: Consider upgrading to `en_core_web_lg` or `en_core_web_trf` for better accuracy
- **Tradeoff**: Larger models increase latency (100ms → 500ms)

---

## Next Steps

1. **Review this research** with team/stakeholders
2. **Prioritize features**: Relationships vs Effects vs Assertions (can implement incrementally)
3. **Create lift-sys-372 sub-tasks** if needed (one per feature)
4. **Set up development branch**: `feature/phase-2-nlp-enhancement`
5. **Begin implementation**: Start with relationships (highest value)

---

**Summary**: This is a well-scoped enhancement with clear extension points. The existing infrastructure (spaCy, DSPy, constraint detection) provides a strong foundation. Main implementation work involves adding structured extraction for relationships/effects/assertions, updating IR schema, and comprehensive testing. Medium complexity, manageable within 13-18 hours of focused development.
