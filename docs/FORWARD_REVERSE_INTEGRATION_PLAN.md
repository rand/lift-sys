# Forward-Reverse Mode Integration Plan

**Version**: 1.0
**Date**: October 13, 2025
**Status**: Planning
**Goal**: Create a cohesive human-agent-IR interaction loop that enables iterative refinement, verification, and evolution of software specifications and implementations.

---

## Executive Summary

This plan outlines how forward mode (natural language → IR → code) and reverse mode (code → IR) can work together as a unified system with the Intermediate Representation (IR) as the central artifact. The key insight is that **IR is not just an output—it's a living contract** that mediates between human intent, machine verification, and code implementation.

**Core Principles:**
1. **IR-Centric**: All operations (refinement, verification, generation, analysis) operate on IR
2. **Human-Agent Collaboration**: Humans provide intent and decisions; agents provide suggestions and automation
3. **Continuous Verification**: Every change to IR is verified before proceeding
4. **Bidirectional Flow**: Code ↔ IR ↔ Intent flows both directions
5. **Provenance Tracking**: Every IR change tracks its origin (human, agent, code, verification)

---

## Current State Analysis

### Forward Mode (Prompt → IR → Code)

**Strengths:**
- ✅ Session management system for iterative refinement
- ✅ Typed holes for ambiguity tracking
- ✅ AI-assisted resolution with suggestions
- ✅ SMT verification for logical consistency
- ✅ Multiple interfaces (Web UI, CLI, TUI, SDK)

**Gaps:**
- ⚠️ No code generation from finalized IR
- ⚠️ No feedback loop from generated code back to IR
- ⚠️ Limited support for evolving existing IRs
- ⚠️ No diff/merge support for IR changes

### Reverse Mode (Code → IR)

**Strengths:**
- ✅ Whole-project and single-file analysis
- ✅ Static analysis (AST, types, signatures)
- ✅ Security analysis (CodeQL)
- ✅ Dynamic analysis (Daikon invariants)
- ✅ Progress tracking and error handling

**Gaps:**
- ⚠️ Extracted IRs are read-only (no refinement workflow)
- ⚠️ No connection to forward mode sessions
- ⚠️ Limited support for comparing code vs IR
- ⚠️ No validation that code matches its extracted IR

### Integration Gaps

**Missing Workflows:**
1. Extract IR from code → Refine IR → Generate improved code
2. Write IR manually → Generate code → Verify code matches IR
3. Compare two IRs (original vs extracted from generated code)
4. Evolve existing IR based on new requirements
5. Merge IRs from multiple sources

---

## The Interaction Loop

### Central Concept: IR as Living Contract

```
                    ┌─────────────────┐
                    │   Human Intent  │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │   Natural       │
                    │   Language      │
                    └────────┬────────┘
                             │
                  ┌──────────▼──────────┐
                  │                     │
         ┌────────▼────────┐   ┌───────▼────────┐
         │  Forward Mode   │   │  Reverse Mode  │
         │  (Prompt → IR)  │   │  (Code → IR)   │
         └────────┬────────┘   └───────┬────────┘
                  │                    │
                  └──────────┬─────────┘
                             │
                    ┌────────▼────────┐
                    │                 │
                    │   IR (Central)  │
                    │                 │
                    │  • Typed holes  │
                    │  • Assertions   │
                    │  • Evidence     │
                    │  • Provenance   │
                    │                 │
                    └────────┬────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
     ┌────────▼────────┐ ┌──▼───┐ ┌───────▼────────┐
     │  Agent Assists  │ │ SMT  │ │  Human Review  │
     │  (Suggestions)  │ │Verify│ │  (Decisions)   │
     └────────┬────────┘ └──┬───┘ └───────┬────────┘
              │              │              │
              └──────────────┼──────────────┘
                             │
                    ┌────────▼────────┐
                    │  Refined IR     │
                    │  (No holes,     │
                    │   Verified)     │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │  Code Generator │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │  Generated Code │
                    └────────┬────────┘
                             │
                             │ (feedback loop)
                             │
                    ┌────────▼────────┐
                    │  Reverse Mode   │
                    │  Validation     │
                    │  (Code → IR')   │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │  IR vs IR'      │
                    │  Comparison     │
                    └─────────────────┘
```

---

## Key Workflows

### Workflow 1: Pure Forward Mode (Greenfield)

**Use Case**: Building new functionality from scratch

```
1. Human: "I need a function to validate email addresses"
   ↓
2. Agent: Generate initial IR with holes
   • hole_function_name
   • hole_parameter_type
   • hole_return_type
   ↓
3. Agent: Provide suggestions for each hole
   • function_name: ["validate_email", "check_email", "is_valid_email"]
   • parameter_type: ["str", "EmailAddress (custom type)"]
   • return_type: ["bool", "ValidationResult"]
   ↓
4. Human: Select or customize resolutions
   • function_name: "validate_email"
   • parameter_type: "str"
   • return_type: "ValidationResult"  (explains why: "Need details about failure")
   ↓
5. System: Update IR, verify with SMT
   ↓
6. Agent: Identify new holes from resolution
   • hole_ValidationResult_structure
   ↓
7. [Repeat steps 3-6 until no holes remain]
   ↓
8. System: IR is complete and verified
   ↓
9. Agent: Generate code from IR
   ↓
10. System: Run reverse mode on generated code → IR'
    ↓
11. System: Compare IR vs IR'
    • If match: ✓ Code faithfully implements IR
    • If diff: Show differences, let human decide
```

**Success Criteria:**
- ✅ All holes resolved
- ✅ SMT verification passes
- ✅ Generated code compiles/runs
- ✅ Reverse-extracted IR matches original IR (within tolerance)

### Workflow 2: Reverse-to-Forward (Legacy Modernization)

**Use Case**: Understanding and improving existing code

```
1. Human: "Analyze this legacy authentication module"
   ↓
2. System: Run reverse mode on auth.py
   ↓
3. Agent: Extract IR with evidence
   • Function signatures from AST
   • Security issues from CodeQL
   • Invariants from Daikon traces
   • Type constraints from usage
   ↓
4. System: Present extracted IR to human
   ↓
5. Human: Review IR, identify issues
   • "This function has SQL injection risk"
   • "Missing input validation on user_id"
   • "Error handling is incomplete"
   ↓
6. System: Convert extracted IR to session
   • Create new spec session from reverse IR
   • Mark issues as typed holes
   ↓
7. Human + Agent: Iteratively refine IR
   • Add security assertions
   • Specify input validation
   • Define error handling behavior
   ↓
8. System: Verify refined IR
   ↓
9. Agent: Generate improved code from refined IR
   ↓
10. Human: Review side-by-side diff
    • Original code vs generated code
    • Highlight security improvements
    • Show added validations
    ↓
11. Human: Accept or iterate further
```

**Success Criteria:**
- ✅ Security issues identified and resolved
- ✅ IR captures all implicit behavior
- ✅ Generated code improves on original
- ✅ All tests still pass

### Workflow 3: IR Evolution (Feature Enhancement)

**Use Case**: Extending existing functionality

```
1. System: Load existing IR (from previous session or reverse mode)
   ↓
2. Human: "I want to add rate limiting to this API endpoint"
   ↓
3. Agent: Analyze required changes to IR
   • New effect: "rate_limiter_check"
   • New assertion: "requests_per_minute < MAX_RATE"
   • New parameter: "rate_limit_key"
   ↓
4. System: Create typed holes for new elements
   • hole_rate_limit_algorithm: ["token_bucket", "sliding_window", "fixed_window"]
   • hole_rate_limit_storage: ["redis", "memcached", "in_memory"]
   ↓
5. Human + Agent: Resolve holes
   ↓
6. System: Verify evolved IR
   • Check that new constraints don't conflict with existing
   • Ensure backward compatibility (if required)
   ↓
7. Agent: Generate code diff
   • Show what changes in implementation
   ↓
8. Human: Review and accept
   ↓
9. System: Run tests against new implementation
```

**Success Criteria:**
- ✅ Original functionality preserved
- ✅ New feature correctly integrated
- ✅ No conflicts in IR constraints
- ✅ Tests pass (old + new)

### Workflow 4: Cross-File Refactoring

**Use Case**: Restructuring code while maintaining behavior

```
1. Human: "Split this 1000-line module into separate concerns"
   ↓
2. System: Run reverse mode → extract IR for each function
   ↓
3. Agent: Identify concerns and suggest groupings
   • Group A: Authentication functions
   • Group B: Database operations
   • Group C: API handlers
   ↓
4. Human: Approve or adjust groupings
   ↓
5. System: For each group, create refined IR
   • Define module-level contracts
   • Specify interfaces between modules
   ↓
6. Agent: Generate new file structure with implementations
   ↓
7. System: Verify all original IRs are preserved
   • No behavior loss
   • All assertions still hold
   ↓
8. Human: Review structure, run tests
```

**Success Criteria:**
- ✅ All original behavior preserved
- ✅ Better separation of concerns
- ✅ All tests pass without modification
- ✅ Reverse mode on new code yields same IRs

---

## Technical Implementation Plan

### Phase 1: Code Generation (4-6 weeks)

**Goal**: Close the loop by generating code from finalized IRs

#### 1.1: IR to Code Translator

**Components:**
- **PythonCodeGenerator**: Translate IR to Python AST
- **TypeResolver**: Map IR types to Python type hints
- **AssertionInjector**: Convert IR assertions to runtime checks or type guards
- **EffectHandler**: Generate code for side effects (API calls, DB, filesystem)

**Example:**
```python
class PythonCodeGenerator:
    def generate(self, ir: IntermediateRepresentation) -> str:
        """Generate Python code from IR."""
        # Generate function signature
        signature = self._generate_signature(ir.signature)

        # Generate docstring from intent
        docstring = self._generate_docstring(ir.intent)

        # Generate parameter validation from assertions
        validations = self._generate_validations(ir.assertions)

        # Generate effect handlers
        effects = self._generate_effects(ir.effects)

        # Generate implementation body
        body = self._generate_body(ir, effects)

        return self._assemble_function(signature, docstring, validations, body)
```

**API Endpoint:**
```python
@app.post("/api/sessions/{session_id}/generate")
async def generate_code(
    session_id: str,
    target_language: str = "python",
    user: AuthenticatedUser = Depends(require_authenticated_user)
) -> CodeGenerationResponse:
    """Generate code from finalized IR."""
    session = await get_session(session_id)

    if session.status != "finalized":
        raise HTTPException(400, "Session must be finalized")

    ir = session.current_draft.ir

    if target_language == "python":
        generator = PythonCodeGenerator()
        code = generator.generate(ir)
    else:
        raise HTTPException(400, f"Unsupported language: {target_language}")

    return CodeGenerationResponse(
        code=code,
        language=target_language,
        metadata={
            "source_session": session_id,
            "generated_at": datetime.now(UTC).isoformat(),
        }
    )
```

#### 1.2: Validation Loop

**Components:**
- **RoundTripValidator**: Generate code → extract IR → compare
- **IRDiffer**: Compare two IRs and report differences
- **FidelityScorer**: Measure how well code implements IR

**Example:**
```python
class RoundTripValidator:
    def validate(self, original_ir: IR, generated_code: str) -> ValidationResult:
        """Validate that generated code matches IR."""
        # Extract IR from generated code
        extracted_ir = self.reverse_mode.lift_code_string(generated_code)

        # Compare IRs
        diff = self.ir_differ.diff(original_ir, extracted_ir)

        # Calculate fidelity score
        score = self.fidelity_scorer.score(diff)

        return ValidationResult(
            matches=score > 0.95,
            score=score,
            differences=diff,
            extracted_ir=extracted_ir
        )
```

#### 1.3: Frontend Integration

**New Components:**
- **CodePreview**: Show generated code with syntax highlighting
- **IRDiffViewer**: Side-by-side comparison of original vs extracted IR
- **GenerationControls**: Options for code generation (language, style, etc.)

**Mockup:**
```
┌─────────────────────────────────────────────────────┐
│ Session: session-abc123                             │
│ Status: Finalized ✓                                 │
├─────────────────────────────────────────────────────┤
│                                                     │
│ [IR View] [Generated Code] [Validation]            │
│                                                     │
│ ┌─────────────────────────────────────────────┐   │
│ │ def validate_email(email: str) ->           │   │
│ │     ValidationResult:                       │   │
│ │     """Validate email address format."""    │   │
│ │                                              │   │
│ │     # Pre-condition checks                  │   │
│ │     if not email:                           │   │
│ │         return ValidationResult(            │   │
│ │             valid=False,                    │   │
│ │             error="Email cannot be empty"   │   │
│ │         )                                   │   │
│ │                                              │   │
│ │     # Email validation logic                │   │
│ │     ...                                     │   │
│ └─────────────────────────────────────────────┘   │
│                                                     │
│ [Copy Code] [Download] [Run Tests]                 │
│                                                     │
│ Validation: ✓ Generated code matches IR (98%)      │
│                                                     │
└─────────────────────────────────────────────────────┘
```

### Phase 2: Reverse → Forward Connection (3-4 weeks)

**Goal**: Allow reverse-extracted IRs to enter forward mode refinement

#### 2.1: Session Import

**API:**
```python
@app.post("/api/sessions/import-from-reverse")
async def import_reverse_ir(
    request: ReverseImportRequest,
    user: AuthenticatedUser = Depends(require_authenticated_user)
) -> PromptSession:
    """Create a spec session from reverse-extracted IR."""
    # Load reverse IR
    reverse_ir = await load_reverse_result(request.reverse_result_id)

    # Convert to session format
    session = await create_session_from_ir(
        ir=reverse_ir,
        source="reverse",
        metadata={
            "original_file": reverse_ir.metadata.source_path,
            "evidence": reverse_ir.metadata.evidence,
        }
    )

    # Identify areas for improvement as holes
    holes = await identify_improvement_areas(reverse_ir)
    session.ambiguities = [h.id for h in holes]

    return session
```

**Improvement Detection:**
```python
def identify_improvement_areas(ir: IR) -> List[TypedHole]:
    """Identify areas where IR could be improved."""
    holes = []

    # Check for security issues in evidence
    for evidence in ir.metadata.evidence:
        if evidence.analysis == "codeql" and evidence.severity == "high":
            holes.append(TypedHole(
                id=f"hole_security_{evidence.id}",
                description=f"Security issue: {evidence.message}",
                suggestions=get_security_fixes(evidence)
            ))

    # Check for missing assertions
    if len(ir.assertions) == 0:
        holes.append(TypedHole(
            id="hole_add_preconditions",
            description="No pre-conditions specified",
            suggestions=["Add input validation", "Add null checks"]
        ))

    # Check for incomplete error handling
    if not has_error_handling(ir):
        holes.append(TypedHole(
            id="hole_error_handling",
            description="Error handling not specified",
            suggestions=["Add try-catch", "Specify error return values"]
        ))

    return holes
```

#### 2.2: IR Comparison Tool

**Component:**
```python
class IRDiffer:
    def diff(self, ir1: IR, ir2: IR) -> IRDiff:
        """Compare two IRs and report differences."""
        return IRDiff(
            signature_diff=self._diff_signatures(ir1.signature, ir2.signature),
            intent_diff=self._diff_intents(ir1.intent, ir2.intent),
            assertion_diff=self._diff_assertions(ir1.assertions, ir2.assertions),
            effect_diff=self._diff_effects(ir1.effects, ir2.effects),
            metadata_diff=self._diff_metadata(ir1.metadata, ir2.metadata),
        )

    def _diff_signatures(self, sig1, sig2):
        """Compare function signatures."""
        diffs = []

        if sig1.name != sig2.name:
            diffs.append(("name", sig1.name, sig2.name))

        # Compare parameters
        params1 = {p.name: p for p in sig1.parameters}
        params2 = {p.name: p for p in sig2.parameters}

        # Added parameters
        for name in params2.keys() - params1.keys():
            diffs.append(("parameter_added", None, params2[name]))

        # Removed parameters
        for name in params1.keys() - params2.keys():
            diffs.append(("parameter_removed", params1[name], None))

        # Changed parameters
        for name in params1.keys() & params2.keys():
            if params1[name] != params2[name]:
                diffs.append(("parameter_changed", params1[name], params2[name]))

        return diffs
```

**Frontend Visualization:**
```
┌─────────────────────────────────────────────────────────────┐
│ IR Comparison: Original vs Generated                       │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│ Signature:                                                  │
│   Name: validate_email ✓ (matches)                         │
│   Parameters:                                               │
│     - email: str ✓ (matches)                               │
│   + allow_plus_addressing: bool (added in generated)       │
│   Returns: ValidationResult ✓ (matches)                    │
│                                                             │
│ Assertions:                                                 │
│   ✓ email is not None (both)                              │
│   ✓ len(email) > 0 (both)                                 │
│   + email matches regex pattern (added in generated)       │
│                                                             │
│ Effects:                                                    │
│   ~ DNS lookup (modified: now with timeout)                │
│                                                             │
│ Overall Match: 95%                                          │
│                                                             │
│ [Accept Changes] [Reject] [Refine Further]                 │
└─────────────────────────────────────────────────────────────┘
```

### Phase 3: IR Evolution & Versioning (2-3 weeks)

**Goal**: Support evolving IRs over time

#### 3.1: IR Version Control

**Schema Extension:**
```python
@dataclass
class IRVersion:
    """Version metadata for IR."""
    version: int
    parent_version: int | None
    created_at: str
    created_by: str  # user_id or "agent"
    change_summary: str
    diff_from_parent: IRDiff | None

@dataclass
class VersionedIR:
    """IR with version history."""
    current: IntermediateRepresentation
    versions: List[IRVersion]

    def get_version(self, version: int) -> IntermediateRepresentation:
        """Retrieve a specific version."""
        pass

    def diff_versions(self, v1: int, v2: int) -> IRDiff:
        """Compare two versions."""
        pass
```

#### 3.2: Merge Operations

**Support merging IRs from different sources:**
```python
class IRMerger:
    def merge(
        self,
        base: IR,
        branch1: IR,
        branch2: IR,
        strategy: MergeStrategy = "human_guided"
    ) -> MergeResult:
        """Three-way merge of IRs."""
        # Identify conflicts
        conflicts = self._find_conflicts(base, branch1, branch2)

        if not conflicts:
            # Auto-merge
            merged = self._auto_merge(base, branch1, branch2)
            return MergeResult(success=True, ir=merged, conflicts=[])

        # Human intervention needed
        return MergeResult(
            success=False,
            ir=None,
            conflicts=conflicts,
            resolution_options=self._get_resolution_options(conflicts)
        )
```

### Phase 4: Agent-Assisted Workflows (3-4 weeks)

**Goal**: Intelligent agent actions throughout the loop

#### 4.1: Proactive Suggestions

**Agent capabilities:**
- Suggest improvements to IR based on evidence
- Identify potential bugs or security issues
- Recommend refactorings
- Propose test cases

**Example:**
```python
class AgentAdvisor:
    def analyze_ir(self, ir: IR) -> List[Suggestion]:
        """Analyze IR and provide suggestions."""
        suggestions = []

        # Check for common anti-patterns
        if self._has_overly_broad_types(ir):
            suggestions.append(Suggestion(
                type="type_refinement",
                severity="medium",
                message="Consider using more specific types",
                examples=[
                    "Change 'data: Any' to 'data: Dict[str, int]'",
                    "Add type guards for Union types"
                ]
            ))

        # Check for missing documentation
        if not ir.intent.rationale:
            suggestions.append(Suggestion(
                type="documentation",
                severity="low",
                message="Add rationale explaining why this function exists"
            ))

        # Check for security concerns
        if self._has_user_input(ir) and not self._has_validation(ir):
            suggestions.append(Suggestion(
                type="security",
                severity="high",
                message="User input detected without validation",
                action="Add input validation assertions"
            ))

        return suggestions
```

#### 4.2: Automated Testing

**Generate tests from IR:**
```python
class TestGenerator:
    def generate_tests(self, ir: IR) -> List[TestCase]:
        """Generate test cases from IR assertions."""
        tests = []

        # Generate positive tests
        for example in self._extract_examples(ir.intent):
            tests.append(TestCase(
                name=f"test_{ir.signature.name}_example_{len(tests)}",
                input=example.input,
                expected_output=example.output,
                type="positive"
            ))

        # Generate negative tests from assertions
        for assertion in ir.assertions:
            if assertion.predicate.startswith("not "):
                tests.append(TestCase(
                    name=f"test_{ir.signature.name}_invalid_input",
                    input=self._violate_assertion(assertion),
                    expected_output="raises Exception",
                    type="negative"
                ))

        # Generate edge cases
        tests.extend(self._generate_edge_cases(ir))

        return tests
```

---

## User Experience Design

### UX Principle 1: IR is Always Visible

**Implementation:**
- Every view shows current IR state
- Changes to IR are immediately visible
- IR diff view available at all times

### UX Principle 2: Provenance is Clear

**Implementation:**
- Every IR element shows its source (human, agent, code, verification)
- Change history is accessible
- Confidence scores displayed for agent suggestions

### UX Principle 3: Non-Linear Workflow

**Implementation:**
- Users can jump between forward and reverse mode
- Multiple sessions can be active simultaneously
- Easy to compare and merge IRs

### Unified Navigation

```
┌─────────────────────────────────────────────────────────────┐
│ lift-sys                                     [@user] [⚙️]   │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│ Sidebar:                           Main Content:           │
│ ┌────────────────┐                ┌─────────────────────┐ │
│ │ 📝 Workbench   │                │                     │ │
│ │                │                │   [Current View]    │ │
│ │ 📁 Repository  │                │                     │ │
│ │                │                │                     │ │
│ │ 🔄 Sessions    │◄───────────────┤   IR at center     │ │
│ │  • Forward (3) │                │                     │ │
│ │  • Reverse (1) │                │                     │ │
│ │                │                └─────────────────────┘ │
│ │ 📊 Comparisons │                                         │
│ │                │                Context Panel:           │
│ │ 🧪 Generated   │                ┌─────────────────────┐ │
│ │    Code (2)    │                │ Related IRs:        │ │
│ │                │                │ • Original (rev)    │ │
│ │ ⚡ Quick       │                │ • Refined (fwd)     │ │
│ │    Actions:    │                │ • Generated Code    │ │
│ │  [New Session] │                │                     │ │
│ │  [Analyze Code]│                │ Agent Suggestions:  │ │
│ │  [Compare IRs] │                │ • Add validation    │ │
│ └────────────────┘                │ • Improve types     │ │
│                                    └─────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

---

## Testing Strategy

### Unit Tests

**Coverage:**
- Code generation for all IR constructs
- IR comparison and diffing
- Round-trip validation
- Merge operations
- Agent suggestion algorithms

### Integration Tests

**Scenarios:**
1. Forward mode: Prompt → IR → Code → Validation
2. Reverse mode: Code → IR → Session → Refinement
3. Evolution: Existing IR → Changes → New Code
4. Merge: Two IRs → Merged IR → Verification

### End-to-End Tests

**User Journeys:**
```python
def test_greenfield_development():
    """Test complete forward mode workflow."""
    # User creates session
    session = client.create_session(prompt="Email validator")
    assert session.ambiguities  # Has holes

    # User resolves holes with agent help
    assists = client.get_assists(session.session_id)
    for hole_id, assist in zip(session.ambiguities, assists.assists):
        client.resolve_hole(
            session.session_id,
            hole_id,
            assist.suggestions[0]  # Pick first suggestion
        )

    # User finalizes
    result = client.finalize_session(session.session_id)
    assert result.ir  # Complete IR

    # System generates code
    code = client.generate_code(session.session_id)
    assert code.language == "python"
    assert "def" in code.code

    # System validates round-trip
    validation = client.validate_code(session.session_id, code.code)
    assert validation.matches
    assert validation.score > 0.95

def test_legacy_modernization():
    """Test reverse → forward → generate workflow."""
    # System analyzes legacy code
    reverse_result = client.reverse_analyze(
        module="legacy_auth.py",
        queries=["security/default"]
    )
    assert reverse_result.irs

    # User imports into session
    session = client.import_reverse_ir(
        reverse_result_id=reverse_result.id,
        ir_index=0
    )
    assert session.ambiguities  # Improvement areas identified

    # User addresses security issues
    for hole in session.ambiguities:
        if "security" in hole:
            assists = client.get_assists(session.session_id)
            # Apply security fix
            client.resolve_hole(session.session_id, hole, assists[0].suggestions[0])

    # Generate improved code
    code = client.generate_code(session.session_id)

    # Verify improvements
    new_reverse = client.reverse_analyze_string(code.code)
    assert len(new_reverse.metadata.evidence) < len(reverse_result.irs[0].metadata.evidence)
```

---

## Success Metrics

### Quantitative Metrics

**Code Quality:**
- Round-trip validation score: Target > 95%
- SMT verification success rate: Target 100%
- Generated code passes tests: Target > 90%

**User Efficiency:**
- Time to finalize IR: Measure and track
- Number of iterations to convergence: Target < 10
- Agent suggestion acceptance rate: Target > 50%

**System Reliability:**
- Code generation success rate: Target > 95%
- Reverse mode extraction accuracy: Target > 90%
- IR merge conflict rate: Track and minimize

### Qualitative Metrics

**User Satisfaction:**
- Users understand IR at center of workflow
- Users trust agent suggestions
- Users feel in control of decisions

**Developer Experience:**
- Easy to switch between forward and reverse
- Clear feedback at every step
- Helpful error messages and guidance

---

## Implementation Timeline

### Milestone 1: Code Generation (Weeks 1-6)

**Deliverables:**
- Python code generator from IR
- Basic validation (syntax, types)
- Frontend code preview
- Round-trip validator

**Dependencies:**
- None (can start immediately)

### Milestone 2: Reverse Integration (Weeks 7-10)

**Deliverables:**
- Import reverse IR into session
- Improvement area detection
- IR comparison tool
- Side-by-side diff viewer

**Dependencies:**
- Milestone 1 (code generation)

### Milestone 3: IR Evolution (Weeks 11-13)

**Deliverables:**
- IR versioning system
- Merge operations
- Version history UI
- Conflict resolution UI

**Dependencies:**
- Milestone 2 (reverse integration)

### Milestone 4: Agent Enhancements (Weeks 14-17)

**Deliverables:**
- Proactive IR analysis
- Security/quality suggestions
- Test case generation
- Refactoring recommendations

**Dependencies:**
- Milestones 1-3

### Milestone 5: Polish & Optimization (Weeks 18-20)

**Deliverables:**
- Performance optimization
- UX refinements
- Comprehensive documentation
- Tutorial videos

**Dependencies:**
- All previous milestones

---

## Risk Mitigation

### Technical Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| Code generation quality insufficient | High | Start with simple cases, iterate. Use templates. Allow human editing. |
| Round-trip validation too strict | Medium | Define tolerance thresholds. Focus on semantic equivalence, not syntactic. |
| IR merge conflicts too common | Medium | Design IR schema to minimize conflicts. Provide good tooling for resolution. |
| Performance issues with large IRs | Low | Profile early. Optimize serialization. Use caching. |

### UX Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| Users confused by IR-centric workflow | High | Excellent onboarding. Hide complexity initially. Progressive disclosure. |
| Users don't trust generated code | High | Show validation results. Allow inspection. Make editing easy. |
| Workflow too complex | Medium | Provide templates/quick actions. Smart defaults. Guided wizards. |

---

## Next Steps

### Immediate Actions (This Week)

1. **Create Beads issues** for each milestone
2. **Prototype code generator** for simple IRs
3. **Design IR comparison algorithm**
4. **Sketch UI mockups** for integrated workflow

### Short Term (Next 2 Weeks)

1. Implement basic Python code generator
2. Build round-trip validator
3. Create frontend code preview component
4. Write integration tests for forward mode → code

### Medium Term (Next Month)

1. Complete Milestone 1 (Code Generation)
2. Begin Milestone 2 (Reverse Integration)
3. User testing with dogfooding team
4. Iterate based on feedback

---

## Appendix A: IR Schema Enhancements

To support these workflows, the IR schema needs these additions:

```python
@dataclass
class Provenance:
    """Track origin of IR elements."""
    source: Literal["human", "agent", "reverse", "verification", "merge"]
    confidence: float  # 0.0 to 1.0
    timestamp: str
    author: str | None
    evidence: List[Evidence]

@dataclass
class IntermediateRepresentation:
    """Enhanced IR with provenance and versioning."""
    # Existing fields
    intent: Intent
    signature: Signature
    effects: List[Effect]
    assertions: List[Assertion]
    metadata: Metadata

    # New fields for integration
    provenance: Provenance
    version: int
    parent_version: int | None
    related_irs: List[str]  # IDs of related IRs
    validation_results: List[ValidationResult]

    # Computed fields
    @property
    def is_complete(self) -> bool:
        """Check if IR has no holes."""
        return len(self.holes) == 0

    @property
    def holes(self) -> List[TypedHole]:
        """Extract all typed holes from IR."""
        # Scan all fields for holes
        pass
```

---

## Appendix B: Agent Capabilities Matrix

| Capability | Forward Mode | Reverse Mode | IR Evolution |
|-----------|--------------|--------------|--------------|
| **Suggest hole resolutions** | ✓ Primary | - | ✓ |
| **Identify improvement areas** | ✓ | ✓ Primary | ✓ |
| **Generate test cases** | ✓ | ✓ | ✓ |
| **Detect security issues** | - | ✓ Primary | ✓ |
| **Propose refactorings** | - | ✓ | ✓ Primary |
| **Explain IR elements** | ✓ | ✓ | ✓ |
| **Compare IRs** | - | ✓ | ✓ Primary |
| **Generate code** | ✓ Primary | - | ✓ |
| **Validate code** | ✓ | ✓ | ✓ |

---

**Document Version**: 1.0
**Status**: Ready for Review
**Next Review**: After prototype completion
