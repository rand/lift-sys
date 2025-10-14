# Core Loop Completion Plan

**Version**: 1.0
**Date**: October 13, 2025
**Status**: Active
**Goal**: Complete forward mode and reverse mode to enable the full bidirectional workflow

---

## Reality Check: Current Implementation State

### ❌ What's Stubbed/Incomplete

#### Forward Mode - Prompt → IR
**File**: `lift_sys/spec_sessions/translator.py`

**Status**: 95% stubbed
```python
def _translate_with_llm(self, prompt: str, context: IR | None) -> IR:
    # Line 96-97: Explicitly states "In a real implementation, this would call the synthesizer"
    # Falls back to regex-based heuristics
    return self._translate_rule_based(prompt, context)
```

**What works**: Basic regex pattern matching for extracting function names, parameters
**What doesn't work**: No LLM-based translation, no structured generation, no semantic understanding

---

#### Forward Mode - Constrained Generation
**File**: `lift_sys/forward_mode/controller_runtime.py`

**Status**: 100% stubbed
```python
def _provider_stream(self, payload: dict[str, object]) -> Iterator[str]:
    # Lines 165-172: Just splits intent string on whitespace
    intent = payload.get("prompt", {}).get("intent", "")
    for token in intent.split():
        yield token
```

**What works**: Hook system, telemetry, configuration
**What doesn't work**: No actual LLM calls, no constrained decoding, no grammar enforcement

---

#### Forward Mode - Code Generation
**File**: `lift_sys/codegen/generator.py`

**Status**: Generates non-functional stubs only
```python
# Line 349: Implementation is literally:
lines.append(f'{indent}raise NotImplementedError("TODO: Implement {ir.signature.name}")')
```

**What works**: Docstring generation, assertion injection (as comments), type hints
**What doesn't work**: No actual function bodies, code doesn't run

---

#### Reverse Mode - Static Analysis
**File**: `lift_sys/reverse_mode/analyzers.py`

**Status**: 100% stubbed
```python
class CodeQLAnalyzer:
    def run(self, repo_path: str, queries: Iterable[str]) -> list[Finding]:
        # Line 23: "Placeholder implementation that emulates CodeQL outputs."
        return [Finding(kind="codeql", message=f"Query {query} requires refinement", ...)]

class DaikonAnalyzer:
    def run(self, repo_path: str, entrypoint: str) -> list[Finding]:
        # Lines 39-46: Returns hardcoded "x > 0 inferred"
        return [Finding(kind="daikon", message="x > 0 inferred", ...)]
```

**What works**: Nothing - returns fake data
**What doesn't work**: No CodeQL integration, no Daikon integration, no real invariant extraction

---

#### Reverse Mode - Code → IR Extraction
**File**: `lift_sys/reverse_mode/lifter.py`

**Status**: Partially stubbed (50%)
```python
def lift(self, target_module: str) -> IntermediateRepresentation:
    # Lines 375-378: Hardcoded signature
    signature = SigClause(
        name=Path(target_module).stem,
        parameters=[Parameter(name="x", type_hint="int", description="example parameter")],
        returns="int",
    )
```

**What works**: File discovery, repository management, progress tracking, error handling
**What doesn't work**: No AST parsing, no type extraction, signatures are hardcoded

---

### ✅ What's Actually Implemented

1. **Infrastructure** (100% real)
   - OAuth system with GitHub
   - Multi-provider configuration (Anthropic, OpenAI, Gemini, vLLM)
   - Modal deployment
   - Repository management
   - WebSocket progress streaming

2. **IR Data Model** (100% real)
   - Complete IR schema with all clauses
   - Versioning system
   - Provenance tracking
   - Comparison and merge operations
   - Typed holes

3. **Session Management** (100% real)
   - Create/list/get/update/finalize sessions
   - Revision history
   - State persistence (in-memory)
   - Frontend integration

4. **UI Components** (100% real)
   - Web UI with React + shadcn/ui
   - Multiple views (Prompt Workbench, Repository, Planner, Configuration)
   - Version history visualization
   - IR diff viewer
   - Proactive analysis display

5. **Testing & Deployment** (100% real)
   - 100+ tests (unit, integration, E2E)
   - CI/CD with GitHub Actions
   - Start script for unified development
   - Comprehensive error handling

---

## Completion Plan

### Phase 1: Minimum Viable Forward Mode (2-3 weeks)

**Goal**: Enable prompt → IR → runnable code workflow

#### 1.1 Implement Real Prompt → IR Translation
**Priority**: P0
**Effort**: 1 week
**File**: `lift_sys/spec_sessions/translator.py`

**Tasks**:
- [ ] Integrate with Anthropic/OpenAI API for structured output
- [ ] Design prompt template for IR generation
- [ ] Implement JSON schema validation for generated IR
- [ ] Add retry logic for malformed outputs
- [ ] Test with 20+ example prompts

**Implementation approach**:
```python
def _translate_with_llm(self, prompt: str, context: IR | None) -> IR:
    # Use Anthropic Claude with JSON schema constraint
    system = "You are an expert at converting natural language to formal IR specifications."

    schema = {
        "type": "object",
        "properties": {
            "intent": {"type": "object", "properties": {...}},
            "signature": {"type": "object", "properties": {...}},
            "assertions": {"type": "array", "items": {...}},
            "effects": {"type": "array", "items": {...}}
        },
        "required": ["intent", "signature"]
    }

    response = await self.provider.generate_structured(
        system=system,
        user=f"Convert to IR:\n\n{prompt}",
        schema=schema,
        temperature=0.3
    )

    return self.parser.loads(response.content)
```

**Acceptance criteria**:
- Generates valid IR JSON from natural language 95%+ of the time
- Correctly identifies ambiguities and creates typed holes
- Handles edge cases (incomplete prompts, ambiguous requirements)

---

#### 1.2 Implement Real Code Generation
**Priority**: P0
**Effort**: 1 week
**File**: `lift_sys/codegen/generator.py`

**Tasks**:
- [ ] Implement function body generation using LLM
- [ ] Inject runtime assertion checks (not just comments)
- [ ] Generate test cases from IR assertions
- [ ] Add syntax validation and formatting
- [ ] Handle imports and dependencies

**Implementation approach**:
```python
def _generate_function_body(self, ir: IR) -> list[str]:
    # Build context from IR
    context = {
        "intent": ir.intent.summary,
        "signature": ir.signature.to_dict(),
        "preconditions": [a.predicate for a in ir.get_preconditions()],
        "postconditions": [a.predicate for a in ir.get_postconditions()],
    }

    # Use LLM to generate implementation
    prompt = f"""Generate Python function implementation:
Intent: {context['intent']}
Signature: {context['signature']}
Preconditions: {context['preconditions']}
Postconditions: {context['postconditions']}

Requirements:
1. Check all preconditions at start
2. Implement the core logic
3. Verify all postconditions before return
4. Raise descriptive errors on violations
"""

    code = await self.provider.generate_code(prompt, language="python")
    return self._validate_and_format(code)
```

**Acceptance criteria**:
- Generated code runs without syntax errors 100% of the time
- Runtime assertions actually execute and catch violations
- Code passes generated unit tests 80%+ of the time
- Handles common patterns (CRUD, validation, transformation)

---

#### 1.3 Connect Prompt → IR → Code Pipeline
**Priority**: P0
**Effort**: 3 days
**File**: `lift_sys/api/server.py`

**Tasks**:
- [ ] Add `/api/spec-sessions/{id}/generate-code` endpoint
- [ ] Stream generation progress to frontend
- [ ] Add code preview and download
- [ ] Integrate with session workflow
- [ ] Add validation step

**New endpoint**:
```python
@app.post("/api/spec-sessions/{session_id}/generate-code")
async def generate_code_from_session(
    session_id: str,
    request: GenerateCodeRequest,
    user: AuthenticatedUser = Depends(require_authenticated_user),
) -> GenerateCodeResponse:
    session = STATE.session_manager.get_session(session_id)
    if not session.current_draft or not session.current_draft.ir:
        raise HTTPException(400, "Session has no finalized IR")

    # Generate code from IR
    generator = PythonCodeGenerator()
    source_code = generator.generate(session.current_draft.ir, options=request)

    # Validate generated code
    validation_result = await validate_generated_code(source_code, session.current_draft.ir)

    return GenerateCodeResponse(
        session_id=session_id,
        source_code=source_code,
        language="python",
        validation=validation_result
    )
```

**Acceptance criteria**:
- End-to-end workflow: prompt → refined IR → generated code in <2 minutes
- User can download Python file that runs
- Clear error messages when generation fails

---

### Phase 2: Minimum Viable Reverse Mode (2-3 weeks)

**Goal**: Enable code → IR extraction workflow

#### 2.1 Implement AST-Based Signature Extraction
**Priority**: P0
**Effort**: 1 week
**File**: `lift_sys/reverse_mode/ast_analyzer.py` (new)

**Tasks**:
- [ ] Create AST analyzer for Python
- [ ] Extract function signatures (name, parameters, return types)
- [ ] Extract docstrings and convert to intent
- [ ] Detect imports and dependencies
- [ ] Handle classes, async functions, decorators

**Implementation**:
```python
import ast
from typing import List

class ASTSignatureExtractor:
    def extract_function_signatures(self, source_code: str) -> List[FunctionSignature]:
        tree = ast.parse(source_code)
        signatures = []

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                sig = self._extract_signature(node)
                signatures.append(sig)

        return signatures

    def _extract_signature(self, node: ast.FunctionDef) -> FunctionSignature:
        # Extract parameters with type hints
        params = []
        for arg in node.args.args:
            param = Parameter(
                name=arg.arg,
                type_hint=self._get_type_annotation(arg.annotation),
                description=self._extract_param_doc(node, arg.arg)
            )
            params.append(param)

        # Extract return type
        return_type = self._get_type_annotation(node.returns)

        # Extract docstring as intent
        docstring = ast.get_docstring(node)

        return FunctionSignature(
            name=node.name,
            parameters=params,
            returns=return_type,
            docstring=docstring
        )
```

**Acceptance criteria**:
- Correctly extracts signatures from 95%+ of valid Python functions
- Handles type hints (PEP 484, 585, 604)
- Preserves docstring information
- Handles edge cases (varargs, kwargs, defaults)

---

#### 2.2 Implement Basic Invariant Extraction
**Priority**: P0
**Effort**: 1 week
**File**: `lift_sys/reverse_mode/invariant_extractor.py` (new)

**Tasks**:
- [ ] Extract preconditions from assert statements
- [ ] Extract postconditions from docstrings/comments
- [ ] Infer simple invariants from code patterns
- [ ] Use LLM to suggest additional invariants
- [ ] Generate confidence scores

**Implementation**:
```python
class InvariantExtractor:
    def extract_from_source(self, source_code: str, function_name: str) -> List[AssertClause]:
        tree = ast.parse(source_code)
        function_node = self._find_function(tree, function_name)

        invariants = []

        # Extract explicit assertions
        for node in ast.walk(function_node):
            if isinstance(node, ast.Assert):
                predicate = ast.unparse(node.test)
                invariants.append(AssertClause(
                    predicate=predicate,
                    rationale="Extracted from assert statement"
                ))

        # Extract from docstring examples
        docstring = ast.get_docstring(function_node)
        if docstring:
            doc_invariants = self._parse_docstring_invariants(docstring)
            invariants.extend(doc_invariants)

        # Use LLM to infer additional invariants
        suggested = await self._llm_suggest_invariants(function_node, invariants)
        invariants.extend(suggested)

        return invariants

    async def _llm_suggest_invariants(self, node, existing) -> List[AssertClause]:
        source = ast.unparse(node)
        prompt = f"""Analyze this function and suggest invariants:

{source}

Existing invariants:
{[inv.predicate for inv in existing]}

Suggest additional preconditions and postconditions."""

        response = await self.provider.generate(prompt)
        return self._parse_llm_response(response)
```

**Acceptance criteria**:
- Extracts 100% of explicit assertions
- Infers reasonable invariants for common patterns (null checks, range validation)
- LLM suggestions are valid and useful 70%+ of the time

---

#### 2.3 Connect Code → IR Pipeline
**Priority**: P0
**Effort**: 3 days
**File**: `lift_sys/reverse_mode/lifter.py`

**Tasks**:
- [ ] Replace hardcoded signature with AST extraction
- [ ] Replace stubbed analyzers with real implementations
- [ ] Add error recovery for malformed code
- [ ] Generate comprehensive metadata
- [ ] Test on real codebases

**Updated lift() method**:
```python
def lift(self, target_module: str) -> IntermediateRepresentation:
    if not self.repo:
        raise RepositoryNotLoadedError()

    # Read source code
    repo_path = Path(self.repo.working_tree_dir)
    module_path = repo_path / target_module
    source_code = module_path.read_text()

    # Extract signatures using AST
    ast_analyzer = ASTSignatureExtractor()
    signatures = ast_analyzer.extract_function_signatures(source_code)

    if not signatures:
        raise AnalysisError(f"No functions found in {target_module}")

    # For now, lift the first function (TODO: multi-function support)
    main_sig = signatures[0]

    # Extract invariants
    invariant_extractor = InvariantExtractor(self.provider)
    assertions = invariant_extractor.extract_from_source(source_code, main_sig.name)

    # Build intent from docstring
    intent = IntentClause(
        summary=main_sig.docstring or f"Function {main_sig.name}",
        rationale="Extracted from source code"
    )

    # Build signature clause
    signature = SigClause(
        name=main_sig.name,
        parameters=main_sig.parameters,
        returns=main_sig.returns
    )

    # Detect improvement opportunities
    holes = self._detect_improvement_holes(source_code, main_sig, assertions)

    return IntermediateRepresentation(
        intent=intent,
        signature=signature,
        effects=self._extract_effects(source_code),
        assertions=assertions,
        metadata=Metadata(
            source_path=target_module,
            origin="reverse",
            language="python"
        ),
        holes=holes
    )
```

**Acceptance criteria**:
- Extracts real function signatures from Python files
- Generates IR that matches the actual code structure
- Identifies genuine improvement opportunities
- Handles files with multiple functions

---

### Phase 3: Close the Loop (1-2 weeks)

**Goal**: Enable extract → refine → regenerate workflow

#### 3.1 Implement Round-Trip Validation
**Priority**: P0
**Effort**: 1 week
**File**: `lift_sys/validation/round_trip.py` (new)

**Tasks**:
- [ ] Generate code from IR
- [ ] Extract IR from generated code
- [ ] Compare original IR vs extracted IR
- [ ] Report differences with severity levels
- [ ] Suggest fixes for mismatches

**Implementation**:
```python
class RoundTripValidator:
    async def validate(self, original_ir: IR) -> ValidationResult:
        # Step 1: Generate code from IR
        generator = PythonCodeGenerator()
        generated_code = generator.generate(original_ir)

        # Step 2: Extract IR from generated code
        lifter = SpecificationLifter(config)
        extracted_ir = lifter.lift_from_string(generated_code)

        # Step 3: Compare IRs
        comparer = IRComparer()
        comparison = comparer.compare(original_ir, extracted_ir)

        # Step 4: Analyze differences
        issues = []
        if comparison.signature_changes:
            issues.append(Issue(
                severity="high",
                category="signature_mismatch",
                message="Generated code signature doesn't match IR",
                details=comparison.signature_changes
            ))

        if comparison.missing_assertions:
            issues.append(Issue(
                severity="medium",
                category="missing_assertions",
                message=f"{len(comparison.missing_assertions)} assertions not enforced",
                details=comparison.missing_assertions
            ))

        return ValidationResult(
            is_valid=len([i for i in issues if i.severity == "high"]) == 0,
            issues=issues,
            confidence_score=self._calculate_confidence(comparison)
        )
```

**Acceptance criteria**:
- Detects signature mismatches 100% of the time
- Detects missing assertions 90%+ of the time
- Provides actionable feedback for fixing issues
- Validation completes in <10 seconds

---

#### 3.2 Implement Improvement Workflow
**Priority**: P1
**Effort**: 5 days
**File**: `lift_sys/api/server.py`

**Tasks**:
- [ ] Create `/api/spec-sessions/from-code` endpoint
- [ ] Auto-create session with reverse-extracted IR
- [ ] Pre-populate improvement suggestions
- [ ] Enable refinement workflow
- [ ] Add regenerate + validate flow

**New endpoint**:
```python
@app.post("/api/spec-sessions/from-code")
async def create_session_from_code(
    request: CreateFromCodeRequest,
    user: AuthenticatedUser = Depends(require_authenticated_user)
) -> SessionResponse:
    # Extract IR from code
    lifter = STATE.lifter
    ir = lifter.lift_from_string(request.source_code, request.language)

    # Run proactive analysis
    advisor = AgentAdvisor()
    analysis = advisor.analyze(ir)

    # Convert suggestions to typed holes
    holes = convert_suggestions_to_holes(analysis.suggestions)
    ir = inject_holes(ir, holes)

    # Create session
    session = STATE.session_manager.create_from_reverse_mode_enhanced(
        ir=ir,
        improvement_holes=holes,
        metadata={
            "original_code": request.source_code,
            "language": request.language,
            "analysis_report": analysis.to_dict()
        }
    )

    return SessionResponse.from_session(session)
```

**Acceptance criteria**:
- Upload code → see extracted IR with improvement suggestions in <30 seconds
- Refine IR through normal session workflow
- Regenerate code and compare to original
- Show side-by-side diff of improvements

---

### Phase 4: Production Readiness (Parallel, ongoing)

#### 4.1 Real CodeQL Integration
**Priority**: P1
**Effort**: 2 weeks
**File**: `lift_sys/reverse_mode/codeql_analyzer.py` (new)

**Tasks**:
- [ ] Install and configure CodeQL CLI
- [ ] Create database from repository
- [ ] Run security queries
- [ ] Parse SARIF output
- [ ] Map findings to IR assertions

#### 4.2 Real Daikon Integration
**Priority**: P2
**Effort**: 2 weeks
**File**: `lift_sys/reverse_mode/daikon_analyzer.py` (new)

**Tasks**:
- [ ] Install Daikon
- [ ] Instrument Python code
- [ ] Capture execution traces
- [ ] Run Daikon invariant detector
- [ ] Parse .inv files
- [ ] Filter spurious invariants

#### 4.3 Constrained Generation with Outlines
**Priority**: P1
**Effort**: 2 weeks
**File**: `lift_sys/forward_mode/constrained_generator.py` (new)

**Tasks**:
- [ ] Integrate Outlines library
- [ ] Define JSON schema for IR
- [ ] Configure vLLM backend
- [ ] Implement streaming with constraints
- [ ] Add grammar-based generation option

---

## Prioritized Implementation Sequence

### Week 1-2: Enable Basic Forward Mode
1. ✅ Day 1-3: Implement LLM-based prompt → IR translation
2. ✅ Day 4-7: Implement function body generation
3. ✅ Day 8-10: Connect pipeline and test end-to-end

**Deliverable**: User can input prompt, get refined IR, download working Python code

---

### Week 3-4: Enable Basic Reverse Mode
4. ✅ Day 11-14: Implement AST-based signature extraction
5. ✅ Day 15-18: Implement invariant extraction
6. ✅ Day 19-21: Connect pipeline and test on real code

**Deliverable**: User can upload Python file, get extracted IR with real signatures and assertions

---

### Week 5-6: Close the Loop
7. ✅ Day 22-25: Implement round-trip validation
8. ✅ Day 26-28: Build improvement workflow
9. ✅ Day 29-30: Integration testing and bug fixes

**Deliverable**: Complete extract → refine → regenerate workflow with validation

---

### Week 7-8: Advanced Analysis (Optional)
10. ⏳ Day 31-38: CodeQL integration
11. ⏳ Day 39-44: Daikon integration
12. ⏳ Day 45-52: Constrained generation with Outlines

**Deliverable**: Production-quality analysis with real security findings and enforced constraints

---

## Success Metrics

### Phase 1 (Forward Mode MVP)
- [ ] Prompt → IR translation succeeds 95%+ of the time
- [ ] Generated code runs without syntax errors 100%
- [ ] Generated code passes unit tests 80%+
- [ ] End-to-end latency <2 minutes

### Phase 2 (Reverse Mode MVP)
- [ ] Signature extraction accuracy 95%+
- [ ] Invariant extraction finds 100% of explicit assertions
- [ ] LLM-suggested invariants are useful 70%+
- [ ] Handles 90% of well-typed Python code

### Phase 3 (Core Loop Complete)
- [ ] Round-trip validation detects signature mismatches 100%
- [ ] Improvement suggestions are actionable 80%+
- [ ] Regenerated code quality >= original 90%
- [ ] User can complete full workflow in <10 minutes

---

## Risk Mitigation

| Risk | Impact | Mitigation |
|------|--------|------------|
| LLM generates invalid IR JSON | High | Schema validation, retry with corrections, fallback to rule-based |
| Generated code doesn't match IR | High | Round-trip validation, confidence scoring, human review step |
| AST parsing fails on complex code | Medium | Graceful degradation, fall back to partial extraction |
| Extraction too slow for large repos | Medium | Parallel processing, caching, incremental analysis |
| LLM costs too high | Medium | Cache results, use smaller models where possible, local fallback |

---

## Dependencies

### External Services
- Anthropic API (for structured IR generation)
- OpenAI API (fallback)
- GitHub API (for repository access)

### External Tools (optional, Phase 4)
- CodeQL CLI (static analysis)
- Daikon (dynamic invariant detection)
- Outlines (constrained generation)

### Internal Dependencies
- All Phase 1 tasks must complete before Phase 2
- Phase 3 requires both Phase 1 and Phase 2
- Phase 4 can run in parallel with other phases

---

## Open Questions

1. **Which LLM for code generation?**
   - Option A: Claude 3.5 Sonnet (best quality, most expensive)
   - Option B: GPT-4 Turbo (good quality, cheaper)
   - Option C: Local CodeLlama (free, lower quality)
   - **Recommendation**: Start with Claude, add GPT-4 as fallback

2. **How to handle multi-file projects in reverse mode?**
   - Option A: Analyze files independently, create separate IRs
   - Option B: Build project-level call graph, create unified IR
   - **Recommendation**: Start with Option A, add Option B in Phase 4

3. **What confidence threshold for LLM-suggested invariants?**
   - Too low: Spam users with false positives
   - Too high: Miss useful suggestions
   - **Recommendation**: Start at 70%, tune based on user feedback

4. **How to handle breaking changes from regeneration?**
   - Option A: Always require manual review
   - Option B: Auto-accept if validation passes
   - Option C: Show diff, let user choose
   - **Recommendation**: Option C

---

## Next Steps

1. **Review and validate this plan** with stakeholders
2. **Set up tracking** in Beads for all tasks
3. **Allocate resources** (who will work on what)
4. **Start Phase 1** (Forward Mode MVP)
5. **Weekly check-ins** to assess progress and adjust plan

---

## Related Documents

- [Master Plan](MASTER_PLAN.md) - Overall project strategy
- [Forward-Reverse Integration Plan](FORWARD_REVERSE_INTEGRATION_PLAN.md) - Original integration vision
- [Architecture: Prompt to IR](../design/ARCHITECTURE_PROMPT_TO_IR.md) - Original forward mode design
