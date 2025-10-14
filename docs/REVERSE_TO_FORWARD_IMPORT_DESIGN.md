# Reverse-to-Forward Import Flow Design

**Issue**: lift-sys-30
**Version**: 1.0
**Date**: October 13, 2025
**Status**: Design Complete
**Goal**: Define how reverse-extracted IRs enter forward mode sessions with improvement detection and metadata preservation.

---

## Executive Summary

This document specifies the complete design for importing reverse-mode extracted IRs into forward-mode refinement sessions. The key innovation is **intelligent improvement area detection** that identifies opportunities for enhancement based on static analysis, security findings, and specification completeness.

**Key Features:**
1. ✅ Seamless session creation from reverse-extracted IRs
2. ✅ Automated improvement area detection with typed holes
3. ✅ Evidence-based metadata preservation
4. ✅ Security issue promotion to refinement opportunities
5. ✅ Completeness analysis for missing specifications

---

## Current Implementation Review

### Existing Components

#### 1. Session Model (`lift_sys/spec_sessions/models.py`)

The `PromptSession` model already supports reverse mode:

```python
@dataclass
class PromptSession:
    session_id: str
    created_at: str
    updated_at: str
    status: str  # "active" | "finalized" | "abandoned"

    revisions: list[PromptRevision]
    ir_drafts: list[IRDraft]
    current_draft: IRDraft | None
    pending_resolutions: list[HoleResolution]

    source: str = "prompt"  # "prompt" | "reverse_mode"
    metadata: dict[str, Any]
```

**Key insight**: The `source` field already distinguishes reverse-mode sessions from prompt-based ones.

#### 2. Session Manager (`lift_sys/spec_sessions/manager.py`)

The `SessionManager.create_from_reverse_mode()` method provides basic import:

```python
def create_from_reverse_mode(
    self,
    ir: IntermediateRepresentation,
    metadata: dict | None = None,
) -> PromptSession:
    # Detect ambiguities
    holes = self.translator._detect_ambiguities(ir, ir.intent.summary)
    ir = self.translator._inject_holes(ir, holes)

    # Create draft
    draft = IRDraft(
        version=1,
        ir=ir,
        validation_status="incomplete" if holes else "pending",
        ambiguities=[h.identifier for h in holes],
        metadata=metadata or {},
    )

    # Create and store session
    session = PromptSession.create_new(
        source="reverse_mode",
        initial_draft=draft,
        metadata=metadata,
    )
    self.store.create(session)

    return session
```

**Current Limitations:**
- ❌ Only detects basic ambiguities (missing types, vague intent)
- ❌ Doesn't analyze security findings from reverse mode evidence
- ❌ Doesn't identify improvement opportunities beyond missing information
- ❌ Limited metadata preservation from reverse mode analysis

#### 3. Reverse Mode Lifter (`lift_sys/reverse_mode/lifter.py`)

Extracts IRs with rich evidence:

```python
def lift(self, target_module: str) -> IntermediateRepresentation:
    # Run analyses
    codeql_findings = self.codeql.run(repo_path, queries)
    daikon_findings = self.daikon.run(repo_path, entrypoint)
    stack_findings = self.stack_graphs.run(target_module)

    # Bundle evidence
    evidence, evidence_lookup = self._bundle_evidence(
        codeql_findings, daikon_findings, stack_findings
    )

    # Build IR with metadata
    metadata = Metadata(
        source_path=target_module,
        origin="reverse",
        language="python",
        evidence=evidence,  # Rich analysis findings preserved here
    )

    return IntermediateRepresentation(
        intent=intent,
        signature=signature,
        effects=effects,
        assertions=assertions,
        metadata=metadata,
    )
```

**Key insight**: Reverse mode already produces evidence-rich IRs with security findings, invariants, and code structure analysis.

---

## Design: Improvement Area Detection

### Algorithm Overview

The improvement area detection algorithm analyzes a reverse-extracted IR to identify opportunities for refinement. It operates in five phases:

```
┌─────────────────────────────────────────────────────────┐
│                  Reverse-Extracted IR                   │
│                                                          │
│  • Intent from docstrings/comments                      │
│  • Signature from AST                                   │
│  • Assertions from Daikon invariants                    │
│  • Effects from stack graphs                            │
│  • Evidence from CodeQL/Daikon/Stack                    │
└──────────────────────┬──────────────────────────────────┘
                       │
        ┌──────────────▼──────────────┐
        │  Improvement Detection      │
        │                             │
        │  1. Security Analysis       │
        │  2. Completeness Analysis   │
        │  3. Specification Quality   │
        │  4. Error Handling          │
        │  5. Documentation           │
        └──────────────┬──────────────┘
                       │
        ┌──────────────▼──────────────┐
        │  Typed Holes Generation     │
        │                             │
        │  • High-priority fixes      │
        │  • Missing specifications   │
        │  • Enhancement opportunities│
        └──────────────┬──────────────┘
                       │
        ┌──────────────▼──────────────┐
        │  Forward-Mode Session       │
        │                             │
        │  Ready for refinement       │
        └─────────────────────────────┘
```

### Phase 1: Security Analysis

Promotes CodeQL security findings to refinement opportunities:

```python
def detect_security_improvements(ir: IntermediateRepresentation) -> list[TypedHole]:
    """Identify security issues that should be addressed."""
    holes = []

    # Extract CodeQL findings from evidence
    codeql_findings = [
        e for e in ir.metadata.evidence
        if e.get("analysis") == "codeql"
    ]

    # Categorize by severity
    critical = [f for f in codeql_findings if f.get("severity") == "critical"]
    high = [f for f in codeql_findings if f.get("severity") == "high"]
    medium = [f for f in codeql_findings if f.get("severity") == "medium"]

    # Critical issues: Require immediate attention
    for finding in critical:
        holes.append(TypedHole(
            identifier=f"security_critical_{finding['id']}",
            type_hint="SecurityFix",
            description=f"🔴 CRITICAL: {finding['message']}",
            kind=HoleKind.ASSERTION,
            constraints={
                "severity": "critical",
                "evidence_id": finding["id"],
                "location": finding.get("location"),
                "remediation": get_security_remediation(finding),
            },
        ))

    # High-severity issues: Add as assertions
    for finding in high:
        holes.append(TypedHole(
            identifier=f"security_high_{finding['id']}",
            type_hint="SecurityAssertion",
            description=f"🟠 HIGH: {finding['message']}",
            kind=HoleKind.ASSERTION,
            constraints={
                "severity": "high",
                "evidence_id": finding["id"],
                "suggested_assertion": generate_security_assertion(finding),
            },
        ))

    # Medium-severity: Optional improvements
    if medium:
        holes.append(TypedHole(
            identifier="security_medium_batch",
            type_hint="SecurityReview",
            description=f"🟡 {len(medium)} medium-severity security issues found",
            kind=HoleKind.INTENT,
            constraints={
                "severity": "medium",
                "findings": medium,
                "review_suggested": True,
            },
        ))

    return holes
```

**Security Remediation Examples:**

| CodeQL Finding | Suggested Remediation |
|----------------|----------------------|
| SQL Injection  | "Add parameterized queries or use ORM" |
| Path Traversal | "Validate and sanitize file paths against whitelist" |
| XSS Vulnerability | "Escape HTML output or use template engine" |
| Hardcoded Secret | "Move to environment variables or secret management" |

### Phase 2: Completeness Analysis

Identifies missing or incomplete specifications:

```python
def detect_completeness_issues(ir: IntermediateRepresentation) -> list[TypedHole]:
    """Identify missing or incomplete specifications."""
    holes = []

    # 1. Missing pre-conditions
    if len(ir.assertions) == 0:
        holes.append(TypedHole(
            identifier="add_preconditions",
            type_hint="AssertionList",
            description="No pre-conditions specified. Consider adding input validation.",
            kind=HoleKind.ASSERTION,
            constraints={
                "suggestions": [
                    "Validate input ranges (e.g., x > 0)",
                    "Check for null/None values",
                    "Verify data types match expectations",
                    "Ensure required fields are present",
                ],
            },
        ))

    # 2. Missing post-conditions
    has_postconditions = any(
        "return" in a.predicate.lower() or "result" in a.predicate.lower()
        for a in ir.assertions
    )
    if not has_postconditions and ir.signature.returns:
        holes.append(TypedHole(
            identifier="add_postconditions",
            type_hint="AssertionList",
            description="No post-conditions specified. What guarantees does the return value provide?",
            kind=HoleKind.ASSERTION,
            constraints={
                "suggestions": [
                    "Specify return value range or properties",
                    "Define success/failure conditions",
                    "Document invariants maintained",
                ],
            },
        ))

    # 3. Missing parameter types
    untyped_params = [
        p for p in ir.signature.parameters
        if not p.type_hint or p.type_hint == "Any" or p.type_hint == "unknown"
    ]
    for param in untyped_params:
        holes.append(TypedHole(
            identifier=f"type_{param.name}",
            type_hint="TypeAnnotation",
            description=f"Parameter '{param.name}' has no type annotation",
            kind=HoleKind.SIGNATURE,
            constraints={
                "parameter_name": param.name,
                "inferred_usages": infer_type_from_usage(param, ir),
            },
        ))

    # 4. Missing return type
    if not ir.signature.returns or ir.signature.returns == "unknown":
        holes.append(TypedHole(
            identifier="return_type",
            type_hint="TypeAnnotation",
            description="Return type not specified",
            kind=HoleKind.SIGNATURE,
            constraints={
                "inferred_from_code": infer_return_type(ir),
            },
        ))

    # 5. Vague intent
    if len(ir.intent.summary.split()) < 5:
        holes.append(TypedHole(
            identifier="clarify_intent",
            type_hint="IntentDescription",
            description="Intent description is too brief. Provide more detail.",
            kind=HoleKind.INTENT,
            constraints={
                "current_length": len(ir.intent.summary.split()),
                "suggestions": [
                    "What is the primary purpose?",
                    "What problem does this solve?",
                    "What are the key behaviors?",
                ],
            },
        ))

    # 6. Missing rationale
    if not ir.intent.rationale:
        holes.append(TypedHole(
            identifier="add_rationale",
            type_hint="IntentRationale",
            description="No rationale provided. Why does this function exist?",
            kind=HoleKind.INTENT,
            constraints={
                "suggestions": [
                    "Explain design decisions",
                    "Document why this approach was chosen",
                    "Note important constraints or trade-offs",
                ],
            },
        ))

    return holes
```

### Phase 3: Specification Quality

Analyzes Daikon invariants for quality issues:

```python
def detect_quality_issues(ir: IntermediateRepresentation) -> list[TypedHole]:
    """Identify specification quality issues."""
    holes = []

    # Extract Daikon findings
    daikon_findings = [
        e for e in ir.metadata.evidence
        if e.get("analysis") == "daikon"
    ]

    # 1. Weak invariants (always true)
    weak_invariants = [
        f for f in daikon_findings
        if "trivial" in f.get("metadata", {}).get("tags", [])
    ]
    if weak_invariants:
        holes.append(TypedHole(
            identifier="strengthen_invariants",
            type_hint="AssertionRefinement",
            description=f"Found {len(weak_invariants)} trivial invariants. Consider strengthening.",
            kind=HoleKind.ASSERTION,
            constraints={
                "weak_invariants": weak_invariants,
                "suggestions": [
                    "Add more specific range constraints",
                    "Define relationships between variables",
                    "Specify ordering or uniqueness properties",
                ],
            },
        ))

    # 2. Conflicting invariants
    conflicts = detect_invariant_conflicts(ir.assertions, daikon_findings)
    for conflict in conflicts:
        holes.append(TypedHole(
            identifier=f"resolve_conflict_{conflict['id']}",
            type_hint="AssertionConflict",
            description=f"Conflicting specifications: {conflict['description']}",
            kind=HoleKind.ASSERTION,
            constraints={
                "conflict_detail": conflict,
                "resolution_options": conflict["resolutions"],
            },
        ))

    # 3. Missing test coverage indicators
    if not has_test_evidence(ir):
        holes.append(TypedHole(
            identifier="add_test_evidence",
            type_hint="TestCoverage",
            description="No test coverage evidence found. Dynamic analysis limited.",
            kind=HoleKind.METADATA,
            constraints={
                "suggestions": [
                    "Add unit tests to enable Daikon analysis",
                    "Run dynamic invariant detection",
                    "Validate specifications against test cases",
                ],
            },
        ))

    return holes
```

### Phase 4: Error Handling Analysis

Detects missing error handling specifications:

```python
def detect_error_handling_gaps(ir: IntermediateRepresentation) -> list[TypedHole]:
    """Identify missing error handling specifications."""
    holes = []

    # 1. No exception specifications
    has_error_effects = any(
        "error" in e.description.lower() or "exception" in e.description.lower()
        for e in ir.effects
    )
    has_error_assertions = any(
        "error" in a.predicate.lower() or "exception" in a.predicate.lower()
        for a in ir.assertions
    )

    if not has_error_effects and not has_error_assertions:
        holes.append(TypedHole(
            identifier="specify_error_handling",
            type_hint="ErrorSpecification",
            description="Error handling not specified. What exceptions can be raised?",
            kind=HoleKind.EFFECT,
            constraints={
                "suggestions": [
                    "List possible exceptions",
                    "Specify error return values",
                    "Document error recovery behavior",
                    "Define failure modes",
                ],
            },
        ))

    # 2. Resource cleanup
    resource_effects = [
        e for e in ir.effects
        if any(kw in e.description.lower() for kw in ["open", "connect", "allocate", "acquire"])
    ]
    cleanup_effects = [
        e for e in ir.effects
        if any(kw in e.description.lower() for kw in ["close", "disconnect", "free", "release"])
    ]

    if resource_effects and not cleanup_effects:
        holes.append(TypedHole(
            identifier="specify_resource_cleanup",
            type_hint="ResourceManagement",
            description="Resources acquired but cleanup not specified",
            kind=HoleKind.EFFECT,
            constraints={
                "resources": [e.description for e in resource_effects],
                "suggestions": [
                    "Add cleanup/close effects",
                    "Specify resource lifetime",
                    "Document cleanup guarantees",
                ],
            },
        ))

    return holes
```

### Phase 5: Documentation Quality

Evaluates intent clarity and completeness:

```python
def detect_documentation_gaps(ir: IntermediateRepresentation) -> list[TypedHole]:
    """Identify documentation quality issues."""
    holes = []

    # 1. Missing parameter descriptions
    undocumented_params = [
        p for p in ir.signature.parameters
        if not p.description or len(p.description) < 10
    ]
    if undocumented_params:
        holes.append(TypedHole(
            identifier="document_parameters",
            type_hint="Documentation",
            description=f"{len(undocumented_params)} parameters lack detailed descriptions",
            kind=HoleKind.SIGNATURE,
            constraints={
                "parameters": [p.name for p in undocumented_params],
                "suggestions": [
                    "Explain parameter purpose and expected values",
                    "Document valid ranges or formats",
                    "Note relationships to other parameters",
                ],
            },
        ))

    # 2. Missing examples
    has_examples = any(
        "example" in ir.intent.summary.lower() or
        "e.g." in ir.intent.summary.lower() or
        "for instance" in ir.intent.summary.lower()
    )
    if not has_examples:
        holes.append(TypedHole(
            identifier="add_usage_examples",
            type_hint="Documentation",
            description="No usage examples provided",
            kind=HoleKind.INTENT,
            constraints={
                "suggestions": [
                    "Add typical usage example",
                    "Show edge case handling",
                    "Demonstrate with concrete values",
                ],
            },
        ))

    return holes
```

### Complete Algorithm Implementation

```python
class ImprovementDetector:
    """Detects improvement opportunities in reverse-extracted IRs."""

    def __init__(self):
        self.security_analyzer = SecurityAnalyzer()
        self.type_inferencer = TypeInferencer()
        self.invariant_analyzer = InvariantAnalyzer()

    def detect_improvements(
        self,
        ir: IntermediateRepresentation,
    ) -> list[TypedHole]:
        """
        Analyze IR and generate typed holes for improvement areas.

        Args:
            ir: Reverse-extracted intermediate representation

        Returns:
            List of typed holes prioritized by importance
        """
        all_holes = []

        # Phase 1: Security (highest priority)
        security_holes = self.detect_security_improvements(ir)
        all_holes.extend(security_holes)

        # Phase 2: Completeness (high priority)
        completeness_holes = self.detect_completeness_issues(ir)
        all_holes.extend(completeness_holes)

        # Phase 3: Error Handling (medium priority)
        error_holes = self.detect_error_handling_gaps(ir)
        all_holes.extend(error_holes)

        # Phase 4: Quality (medium priority)
        quality_holes = self.detect_quality_issues(ir)
        all_holes.extend(quality_holes)

        # Phase 5: Documentation (low priority)
        doc_holes = self.detect_documentation_gaps(ir)
        all_holes.extend(doc_holes)

        # Prioritize and deduplicate
        return self._prioritize_holes(all_holes)

    def _prioritize_holes(self, holes: list[TypedHole]) -> list[TypedHole]:
        """Sort holes by priority."""
        priority_order = {
            "security_critical": 0,
            "security_high": 1,
            "add_preconditions": 2,
            "add_postconditions": 3,
            "specify_error_handling": 4,
            "type_": 5,
            "security_medium": 6,
            "strengthen_invariants": 7,
            "clarify_intent": 8,
            "document_": 9,
        }

        def get_priority(hole: TypedHole) -> int:
            for prefix, priority in priority_order.items():
                if hole.identifier.startswith(prefix):
                    return priority
            return 100  # Low priority for unmatched

        return sorted(holes, key=get_priority)
```

---

## Design: Metadata Preservation

### Metadata Structure

Reverse mode produces rich metadata that must be preserved:

```python
@dataclass
class Metadata:
    source_path: str
    origin: str  # "reverse" | "prompt" | "hybrid"
    language: str
    evidence: list[dict[str, Any]]  # Analysis findings
```

### Evidence Format

```python
{
    "id": "codeql-42",
    "analysis": "codeql",  # "codeql" | "daikon" | "stack_graphs"
    "location": "file.py:123:45",
    "message": "Potential SQL injection vulnerability",
    "metadata": {
        "severity": "high",
        "cwe": "CWE-89",
        "remediation": "Use parameterized queries",
    },
}
```

### Preservation Strategy

When creating a forward-mode session from reverse IR:

1. **Preserve Evidence**: Keep all analysis findings in session metadata
2. **Link Holes to Evidence**: Each typed hole references its source evidence
3. **Track Provenance**: Record which analysis produced each IR component
4. **Enable Traceability**: User can view evidence that led to suggestions

```python
def create_session_with_preserved_metadata(
    ir: IntermediateRepresentation,
    improvement_holes: list[TypedHole],
) -> PromptSession:
    """Create session with full metadata preservation."""

    # Inject improvement holes into IR
    ir_with_holes = inject_typed_holes(ir, improvement_holes)

    # Create draft with provenance tracking
    draft = IRDraft(
        version=1,
        ir=ir_with_holes,
        validation_status="incomplete" if improvement_holes else "pending",
        ambiguities=[h.identifier for h in improvement_holes],
        metadata={
            "reverse_analysis": {
                "source_file": ir.metadata.source_path,
                "language": ir.metadata.language,
                "evidence_count": len(ir.metadata.evidence),
                "evidence_by_type": count_evidence_by_type(ir.metadata.evidence),
            },
            "improvement_detection": {
                "total_holes": len(improvement_holes),
                "security_issues": count_security_holes(improvement_holes),
                "completeness_issues": count_completeness_holes(improvement_holes),
            },
            "original_evidence": ir.metadata.evidence,  # Preserve all findings
        },
    )

    # Create session with preserved context
    session = PromptSession.create_new(
        source="reverse_mode",
        initial_draft=draft,
        metadata={
            "import_source": "reverse_mode",
            "original_file": ir.metadata.source_path,
            "import_timestamp": datetime.now(UTC).isoformat() + "Z",
        },
    )

    return session
```

---

## Complete Import Flow

### End-to-End Process

```
┌─────────────────────────────────────────────────────────┐
│  1. User: "Analyze this codebase in reverse mode"       │
└───────────────────────┬─────────────────────────────────┘
                        │
        ┌───────────────▼─────────────┐
        │  Reverse Mode Lifter        │
        │                             │
        │  • Run CodeQL               │
        │  • Run Daikon               │
        │  • Run Stack Graphs         │
        │  • Extract IR with evidence │
        └───────────────┬─────────────┘
                        │
                        │ IntermediateRepresentation
                        │ (with evidence)
                        │
┌───────────────────────▼─────────────────────────────────┐
│  2. User: "Import this IR for refinement"               │
└───────────────────────┬─────────────────────────────────┘
                        │
        ┌───────────────▼─────────────┐
        │  Improvement Detector        │
        │                             │
        │  • Security analysis        │
        │  • Completeness check       │
        │  • Error handling review    │
        │  • Quality assessment       │
        │  • Documentation evaluation │
        └───────────────┬─────────────┘
                        │
                        │ List[TypedHole]
                        │ (prioritized improvements)
                        │
        ┌───────────────▼─────────────┐
        │  Session Creator            │
        │                             │
        │  • Inject holes into IR     │
        │  • Preserve evidence        │
        │  • Create IRDraft           │
        │  • Initialize PromptSession │
        └───────────────┬─────────────┘
                        │
                        │ PromptSession
                        │ (ready for refinement)
                        │
┌───────────────────────▼─────────────────────────────────┐
│  3. User enters forward-mode refinement                 │
│                                                          │
│  • Review detected improvements                         │
│  • Accept/reject/modify suggestions                     │
│  • Fill typed holes with specifications                 │
│  • Verify with SMT solver                               │
│  • Generate improved code                               │
└──────────────────────────────────────────────────────────┘
```

### API Design

```python
# New endpoint for importing reverse IRs
@app.post("/api/sessions/import-from-reverse")
async def import_reverse_ir(
    ir: dict,  # Serialized IR from reverse mode
    detect_improvements: bool = True,
    user: AuthenticatedUser = Depends(require_authenticated_user),
) -> SessionResponse:
    """
    Import a reverse-extracted IR into a forward-mode session.

    Args:
        ir: Serialized IntermediateRepresentation from reverse mode
        detect_improvements: Whether to run improvement detection
        user: Authenticated user

    Returns:
        Session response with ambiguities (improvement areas)
    """
    # Deserialize IR
    reverse_ir = IntermediateRepresentation.from_dict(ir)

    # Detect improvement opportunities
    improvement_holes = []
    if detect_improvements:
        detector = ImprovementDetector()
        improvement_holes = detector.detect_improvements(reverse_ir)

    # Create session with preserved metadata
    session = STATE.session_manager.create_from_reverse_mode_enhanced(
        ir=reverse_ir,
        improvement_holes=improvement_holes,
        metadata={
            "user_id": user.id,
            "import_timestamp": datetime.now(UTC).isoformat() + "Z",
        },
    )

    # Return session info
    return SessionResponse(
        session_id=session.session_id,
        status=session.status,
        source=session.source,
        created_at=session.created_at,
        updated_at=session.updated_at,
        current_draft=session.current_draft.to_dict() if session.current_draft else None,
        ambiguities=session.get_unresolved_holes(),
        revision_count=len(session.revisions),
        metadata=session.metadata,
    )


# Enhanced session manager method
class SessionManager:
    def create_from_reverse_mode_enhanced(
        self,
        ir: IntermediateRepresentation,
        improvement_holes: list[TypedHole],
        metadata: dict | None = None,
    ) -> PromptSession:
        """
        Create session from reverse IR with improvement detection.

        Args:
            ir: Reverse-extracted IR
            improvement_holes: Detected improvement opportunities
            metadata: Additional metadata

        Returns:
            PromptSession ready for refinement
        """
        # Inject improvement holes into IR
        ir_with_holes = self._inject_improvement_holes(ir, improvement_holes)

        # Create draft with full provenance
        draft = IRDraft(
            version=1,
            ir=ir_with_holes,
            validation_status="incomplete" if improvement_holes else "pending",
            ambiguities=[h.identifier for h in improvement_holes],
            metadata={
                "reverse_analysis": {
                    "source_file": ir.metadata.source_path,
                    "language": ir.metadata.language,
                    "evidence_count": len(ir.metadata.evidence),
                },
                "improvements_detected": {
                    "total": len(improvement_holes),
                    "by_priority": self._count_by_priority(improvement_holes),
                },
                "original_evidence": ir.metadata.evidence,
            },
        )

        # Create session
        session = PromptSession.create_new(
            source="reverse_mode",
            initial_draft=draft,
            metadata=metadata or {},
        )

        # Store and load into planner
        self.store.create(session)
        self.planner.load_ir(draft.ir)
        self.planner.current_session = session

        return session

    def _inject_improvement_holes(
        self,
        ir: IntermediateRepresentation,
        holes: list[TypedHole],
    ) -> IntermediateRepresentation:
        """Inject typed holes into appropriate IR sections."""

        # Group holes by kind
        intent_holes = [h for h in holes if h.kind == HoleKind.INTENT]
        signature_holes = [h for h in holes if h.kind == HoleKind.SIGNATURE]
        assertion_holes = [h for h in holes if h.kind == HoleKind.ASSERTION]
        effect_holes = [h for h in holes if h.kind == HoleKind.EFFECT]

        # Inject into IR
        return IntermediateRepresentation(
            intent=IntentClause(
                summary=ir.intent.summary,
                rationale=ir.intent.rationale,
                holes=ir.intent.holes + intent_holes,
            ),
            signature=SigClause(
                name=ir.signature.name,
                parameters=ir.signature.parameters,
                returns=ir.signature.returns,
                holes=ir.signature.holes + signature_holes,
            ),
            effects=ir.effects,  # TODO: Support effect holes
            assertions=ir.assertions,  # TODO: Support assertion holes
            metadata=ir.metadata,
        )
```

---

## Usage Examples

### Example 1: Security-Focused Import

```python
# User uploads code with SQL injection vulnerability
code = """
def get_user(username):
    query = f"SELECT * FROM users WHERE username = '{username}'"
    return db.execute(query)
"""

# Reverse mode extracts IR
reverse_ir = lifter.lift(code)

# Evidence includes CodeQL finding:
# {
#   "id": "codeql-sql-injection-42",
#   "analysis": "codeql",
#   "severity": "critical",
#   "message": "SQL injection vulnerability",
#   "location": "get_user:2",
# }

# Import into forward mode
session = await import_reverse_ir(ir=reverse_ir.to_dict())

# Session now has typed hole:
# {
#   "identifier": "security_critical_codeql-sql-injection-42",
#   "description": "🔴 CRITICAL: SQL injection vulnerability",
#   "kind": "assertion",
#   "constraints": {
#     "remediation": "Use parameterized queries or ORM",
#     "suggested_assertion": "query must be parameterized",
#   }
# }

# User refines in forward mode:
# 1. Reviews security issue
# 2. Accepts remediation suggestion
# 3. Adds assertion: "username must be sanitized"
# 4. Generates improved code with parameterized queries
```

### Example 2: Completeness-Focused Import

```python
# User has function with no type hints
code = """
def calculate_discount(price, discount_rate):
    return price * (1 - discount_rate)
"""

# Reverse mode extracts basic IR
reverse_ir = lifter.lift(code)

# Import with improvement detection
session = await import_reverse_ir(ir=reverse_ir.to_dict())

# Session has completeness holes:
# [
#   {
#     "identifier": "type_price",
#     "description": "Parameter 'price' has no type annotation",
#     "inferred_usages": ["used in multiplication"],
#   },
#   {
#     "identifier": "type_discount_rate",
#     "description": "Parameter 'discount_rate' has no type annotation",
#     "inferred_usages": ["used in arithmetic"],
#   },
#   {
#     "identifier": "add_preconditions",
#     "description": "No pre-conditions specified",
#     "suggestions": ["Validate input ranges"],
#   },
# ]

# User refines:
# 1. Fills type holes: price: float, discount_rate: float
# 2. Adds preconditions: price > 0, 0 <= discount_rate <= 1
# 3. Generates improved code with full specification
```

---

## Implementation Checklist

### Core Components

- [ ] `ImprovementDetector` class with five-phase analysis
- [ ] `SecurityAnalyzer` for CodeQL finding promotion
- [ ] `TypeInferencer` for type hint suggestions
- [ ] `InvariantAnalyzer` for Daikon quality assessment
- [ ] Enhanced `SessionManager.create_from_reverse_mode_enhanced()`
- [ ] API endpoint `/api/sessions/import-from-reverse`

### Testing

- [ ] Unit tests for each detection phase
- [ ] Integration test: reverse → import → refine → generate
- [ ] Security issue promotion test
- [ ] Completeness detection test
- [ ] Metadata preservation test
- [ ] Evidence traceability test

### Documentation

- [x] This design document
- [ ] API documentation
- [ ] User guide: "Importing Reverse-Mode Results"
- [ ] Developer guide: "Adding Custom Improvement Detectors"

---

## Future Enhancements

### Phase 1 Extensions

1. **Machine Learning Suggestions**: Use ML to suggest improvements based on similar code patterns
2. **Project-Wide Analysis**: Detect improvements across multiple files
3. **Custom Detection Rules**: Allow users to define custom improvement patterns
4. **Confidence Scoring**: Rate each suggestion by confidence level
5. **Interactive Review**: UI for reviewing and accepting/rejecting improvements in bulk

### Phase 2: Diff-Based Import

After IR versioning (lift-sys-35):

1. Compare reverse-extracted IR with existing forward-mode IR
2. Identify specific changes (what was added/removed/modified)
3. Import only the differences as refinement suggestions
4. Enable "sync" workflow: code changes → IR updates → review → accept/reject

---

## Conclusion

This design provides a comprehensive approach to importing reverse-extracted IRs into forward-mode refinement sessions. The key innovations are:

1. **Intelligent Improvement Detection**: Automatically identifies opportunities based on security, completeness, and quality
2. **Evidence Preservation**: Maintains full traceability from analysis findings to suggestions
3. **Prioritized Workflow**: Guides users to address critical issues first
4. **Seamless Integration**: Works within existing session management framework

By implementing this design, we enable the critical "reverse → refine → forward" loop that allows users to improve existing code systematically.
