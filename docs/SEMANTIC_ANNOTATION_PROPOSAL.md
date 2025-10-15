# Semantic Annotation Implementation Proposal

**Date**: 2025-10-15
**Status**: Proposed (Awaiting Decision)
**Based On**: SEMANTIC_ANNOTATION_RESEARCH.md

---

## Executive Summary

After analyzing VS Code semantic highlighting, Ariadne diagnostics, and LSP protocol, I recommend **4 enhancements** for lift-sys. One is **high-value for Phase 4** (semantic highlighting), three are **optional UX polish**.

**Key Insight**: These enhancements improve **visual feedback and UX quality** but are not critical for MVP functionality.

**Recommended Action**: Adopt minimal set (Enhancement 2 only) in Phase 4, defer others based on user feedback.

---

## Proposed Enhancements

### Enhancement 1: Rich Diagnostic Formatting ⭐⭐⭐⭐
**Impact**: HIGH (UX) | **Effort**: 2-3 days | **Priority**: P1 | **Phase**: 4 or 6

#### What:
Adopt Ariadne-style diagnostic formatting for IR ambiguities and errors.

**Example Output**:
```
IR Ambiguity Detected: Missing parameter type
   ┌─ user_prompt:1:1
   │
 1 │ send message to user
   │      ^^^^^^^ What type is 'message'?
   │                  ^^^^ Which user? Need identifier type
   │
   = Suggestions:
     • message: str (text message)
     • message: dict (structured data)
```

**Benefits**:
- ✅ Clearer error communication
- ✅ Faster user comprehension
- ✅ Professional appearance
- ✅ Multi-span visual annotations

**Implementation**:
- Backend: `lift_sys/diagnostics/ariadne_formatter.py` (~200 lines)
- Frontend: React components for rendering formatted diagnostics
- API: `GET /api/ir/{ir_id}/diagnostics/formatted`

**New Bead**: lift-sys-171 (P1, defer to Phase 4 or 6)

---

### Enhancement 2: Semantic Highlighting in Code Preview ⭐⭐⭐⭐⭐
**Impact**: CRITICAL (for provenance) | **Effort**: 3-4 days | **Priority**: P1 | **Phase**: 4

#### What:
Add semantic highlighting to frontend code preview, distinguishing IR-derived vs. boilerplate code.

**Custom Token Types**:
- `ir_entity`: Code from IR entities (functions, classes)
- `ir_constraint`: Code implementing assertions/constraints
- `ir_inferred`: Inferred logic elements
- `ir_hole`: Unresolved typed holes
- `boilerplate`: Auto-generated scaffolding

**Visual Example**:
```python
def calculate_sum(numbers: list[int]) -> int:  # ← 'ir_entity' (blue)
    """Calculate sum of numbers."""              # ← 'boilerplate' (gray)
    assert len(numbers) > 0                      # ← 'ir_constraint' (orange)
    return sum(numbers)                          # ← 'ir_inferred' (green)
```

**Benefits**:
- ✅ **Core to Phase 4**: Provenance visualization requires showing what came from where
- ✅ Users see IR-to-code mapping visually
- ✅ Increases trust in generated code
- ✅ Supports hover tooltips with provenance links

**Implementation**:
```typescript
// Frontend: src/features/codegen/SemanticCodeViewer.tsx
interface SemanticToken {
  line: number;
  startChar: number;
  length: number;
  tokenType: 'ir_entity' | 'ir_constraint' | 'ir_inferred' | 'boilerplate';
  provenance?: string;  // Link to IR element ID
}
```

```python
# Backend: lift_sys/api/semantic_tokens.py
@router.get("/code/{code_id}/semantic-tokens")
async def get_semantic_tokens(code_id: str) -> SemanticTokensResponse:
    """Generate semantic tokens for generated code"""
    # Map GeneratedCode.metadata to semantic tokens
    code = await get_generated_code(code_id)
    return build_semantic_tokens(code)
```

**Integration with Existing Features**:
- Uses `GeneratedCode.metadata` (already exists)
- Integrates with Phase 4: lift-sys-121 (IR-to-Code Mapping)
- Enhances lift-sys-122 (Interactive Provenance Visualization)

**New Bead**: lift-sys-170 (P1, Phase 4 - **RECOMMENDED**)

---

### Enhancement 3: LSP-Style Code Actions for Suggestions ⭐⭐⭐
**Impact**: MEDIUM (UX) | **Effort**: 2 days | **Priority**: P2 | **Phase**: 6

#### What:
Structure refinement suggestions as LSP-style code actions with kinds and automated edits.

**Data Model**:
```python
@dataclass
class IRCodeAction:
    """LSP-inspired code action for IR refinement"""
    kind: CodeActionKind  # quickfix, refactor, clarify, resolve_hole
    title: str            # "Specify message as str type"
    diagnostic: Optional[Ambiguity]
    edit: IRDelta         # Automated change (from ACE Enhancement A)
    confidence: ConfidenceLevel  # From MuSLR Enhancement 1

class CodeActionKind(Enum):
    QUICKFIX = "quickfix"           # Fix specific ambiguity
    RESOLVE_HOLE = "resolve_hole"   # Fill typed hole
    CLARIFY = "clarify"             # Add missing constraint
    REFACTOR = "refactor"           # Restructure IR
```

**Benefits**:
- ✅ Structured suggestion metadata
- ✅ One-click automated fixes
- ✅ Better categorization
- ✅ **Synergy**: Uses ACE delta updates + MuSLR confidence

**New Bead**: lift-sys-173 (P2, defer to Phase 6)

---

### Enhancement 4: Diagnostic Severity Levels ⭐⭐
**Impact**: MEDIUM (UX) | **Effort**: 1 day | **Priority**: P2 | **Phase**: 3 or 6

#### What:
Adopt LSP's 4-level severity system for IR diagnostics.

**Severity Levels**:
```python
class DiagnosticSeverity(Enum):
    ERROR = 1    # Must resolve (missing required field)
    WARNING = 2  # Should resolve (ambiguous type)
    INFO = 3     # May resolve (optimization opportunity)
    HINT = 4     # Optional (style suggestion)
```

**Use Cases**:
- **ERROR**: Missing function name → blocks code generation
- **WARNING**: Ambiguous "user" reference → should clarify
- **INFO**: Could add validation constraint → nice-to-have
- **HINT**: Consider more descriptive name → style

**Benefits**:
- ✅ Prioritize critical issues
- ✅ Don't block on minor issues
- ✅ Color-coded UI by severity
- ✅ Better user guidance

**New Bead**: lift-sys-172 (P2, defer to Phase 6)

---

## Implementation Options

### Option A: Full Integration in Phase 4

**Adopt in Phase 4** (Weeks 25-32):
- Enhancement 1: Rich Diagnostic Formatting (2-3 days)
- Enhancement 2: Semantic Highlighting (3-4 days)
- Enhancement 4: Diagnostic Severity (1 day)

**Total Effort**: 6-8 days (1.2-1.6 weeks)

**Pros**:
- ✅ Comprehensive UX improvement
- ✅ All enhancements synergize with Phase 4 goals
- ✅ Professional, polished experience

**Cons**:
- ⚠️ Extends Phase 4 by +12.5-25%
- ⚠️ Phase 3 already extended by 2 weeks (ACE)
- ⚠️ May delay MVP

**Timeline Impact**:
- **Phase 4**: 8 weeks → 9-10 weeks
- **Overall**: 54 weeks → 55-56 weeks (+1.8-3.7%)

---

### Option B: Phase 3 + 4 Split

**Phase 3** (Weeks 17-26):
- Enhancement 4: Diagnostic Severity (1 day)

**Phase 4** (Weeks 27-34):
- Enhancement 1: Rich Diagnostic Formatting (2-3 days)
- Enhancement 2: Semantic Highlighting (3-4 days)

**Total Effort**: 6-8 days split across phases

**Pros**:
- ✅ More gradual integration
- ✅ Quick win (severity) in Phase 3

**Cons**:
- ⚠️ Fragments implementation
- ⚠️ Still extends both phases

**Timeline Impact**: Same as Option A (spread across 2 phases)

---

### Option C: Phase 6 Defer (Conservative)

**Defer all enhancements to Phase 6** (Weeks 47-52):
- Based on user feedback from beta testing

**Total Effort**: 0 days now, 6-8 days later

**Pros**:
- ✅ Focus on core functionality first
- ✅ User feedback guides UX investments
- ✅ No scope creep in Phases 3-4

**Cons**:
- ⚠️ Phase 4 provenance visualization without semantic highlighting
- ⚠️ May miss opportunity for better UX early

**Timeline Impact**: None (deferred)

---

### Option D: Minimal (Recommended)

**Adopt only Enhancement 2 in Phase 4**:
- Semantic Highlighting (3-4 days)

**Defer Enhancements 1, 3, 4 to Phase 6**:
- Based on user feedback

**Total Effort**: 3-4 days (0.6-0.8 weeks)

**Pros**:
- ✅ **Enhancement 2 is core to Phase 4** (provenance visualization)
- ✅ Minimal scope increase (+6-12% to Phase 4)
- ✅ High ROI (critical feature, reasonable effort)
- ✅ Other enhancements deferred based on user needs

**Cons**:
- ⚠️ No rich diagnostic formatting (Enhancement 1)
- ⚠️ No severity levels (Enhancement 4)

**Timeline Impact**:
- **Phase 4**: 8 weeks → 8.5-9 weeks
- **Overall**: 54 weeks → 54.5-55 weeks (+0.9-1.8%)

---

## Comparison Matrix

| Option | Effort Now | Phase 4 Impact | Overall Impact | UX Quality | Risk |
|--------|-----------|----------------|----------------|------------|------|
| **A: Full Integration** | 6-8 days | +1-2 weeks | +1.8-3.7% | Excellent | Medium |
| **B: Split** | 6-8 days | +0.5-1 week | +1.8-3.7% | Excellent | Medium |
| **C: Defer All** | 0 days | 0 weeks | 0% | Basic | Low |
| **D: Minimal** | 3-4 days | +0.5 week | +0.9-1.8% | Good | Low |

---

## Dependency Graph

### Option D (Minimal) - Recommended

```
Phase 4 Core:
lift-sys-119: Provenance Tracking Engine
lift-sys-120: Provenance Data Collection
lift-sys-121: IR-to-Code Mapping
  ↓
lift-sys-170: Semantic Highlighting ← NEW (Enhancement 2, 3-4 days)
  ↓
lift-sys-122: Interactive Provenance Visualization
lift-sys-123: Provenance Trail UI Component
```

### Option A (Full Integration)

```
Phase 4 Core:
lift-sys-121: IR-to-Code Mapping
  ↓
lift-sys-174: Semantic Highlighting ← NEW (Enhancement 2)
  ↓
lift-sys-122: Interactive Provenance Visualization

lift-sys-123: Provenance Trail UI Component
  ↓
lift-sys-171: Rich Diagnostic Formatting ← NEW (Enhancement 1)
  ↓
lift-sys-124: Provenance Explanation System

lift-sys-172: Diagnostic Severity Levels ← NEW (Enhancement 4)
  ↓
lift-sys-125: Filtering and Navigation
```

---

## Synergy with ACE/MuSLR

### Enhancement 2 + ACE Enhancement A

```
ACE A: Delta-Based IR Updates (lift-sys-167)
  ↓
Semantic Highlighting (lift-sys-174)
  (Show what changed visually after delta application)
```

### Enhancement 3 + ACE + MuSLR

```
ACE A: Delta Updates (lift-sys-167)
MuSLR 1: Confidence Levels (lift-sys-163)
  ↓
Enhancement 3: LSP-Style Code Actions (lift-sys-175)
  (Code actions = delta + confidence metadata)
```

### Enhancement 1 + Enhancement 4

```
Enhancement 4: Diagnostic Severity (lift-sys-176)
  ↓
Enhancement 1: Rich Diagnostic Formatting (lift-sys-173)
  (Severity determines color coding in formatted output)
```

---

## Technical Implementation Details

### Enhancement 2: Semantic Highlighting (Minimal Option)

**Backend Changes**:
```python
# File: lift_sys/api/semantic_tokens.py
from fastapi import APIRouter
from lift_sys.ir.models import IntermediateRepresentation
from lift_sys.codegen.generator import GeneratedCode

@dataclass
class SemanticToken:
    line: int
    start_char: int
    length: int
    token_type: str  # ir_entity, ir_constraint, ir_inferred, boilerplate
    provenance_id: Optional[str]  # Link to IR element

@router.get("/code/{code_id}/semantic-tokens")
async def get_semantic_tokens(code_id: str) -> List[SemanticToken]:
    """Generate semantic tokens for generated code"""
    code = await get_generated_code(code_id)

    # Extract metadata about provenance
    # GeneratedCode.metadata already has this info
    tokens = []

    # Map each line to its source in IR
    for line_num, line_metadata in code.metadata.get("line_provenance", {}).items():
        if line_metadata.get("source") == "ir_entity":
            tokens.append(SemanticToken(
                line=line_num,
                start_char=0,
                length=len(code.source_code.split("\n")[line_num]),
                token_type="ir_entity",
                provenance_id=line_metadata.get("ir_element_id")
            ))

    return tokens
```

**Frontend Changes**:
```typescript
// File: src/features/codegen/SemanticCodeViewer.tsx
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';

interface SemanticToken {
  line: number;
  startChar: number;
  length: number;
  tokenType: 'ir_entity' | 'ir_constraint' | 'ir_inferred' | 'boilerplate';
  provenanceId?: string;
}

export function SemanticCodeViewer({ codeId }: { codeId: string }) {
  const { data: tokens } = useQuery(['semantic-tokens', codeId],
    () => api.getSemanticTokens(codeId)
  );

  // Custom renderer with semantic token styling
  return (
    <SyntaxHighlighter
      language="python"
      customStyle={getTokenStyle}
      wrapLines
      lineProps={(lineNumber) => {
        const token = tokens?.find(t => t.line === lineNumber);
        return {
          style: { backgroundColor: getTokenBgColor(token?.tokenType) },
          'data-provenance-id': token?.provenanceId,
        };
      }}
    >
      {code}
    </SyntaxHighlighter>
  );
}
```

**Estimated Effort Breakdown**:
- Backend API endpoint: 0.5 day
- Frontend viewer component: 1 day
- Token generation logic: 1 day
- Testing + integration: 0.5-1 day
- **Total**: 3-4 days

---

### Enhancement 1: Rich Diagnostic Formatting (Full Option)

**Backend Implementation**:
```python
# File: lift_sys/diagnostics/ariadne_formatter.py
from dataclasses import dataclass
from typing import List, Tuple

@dataclass
class Span:
    start: int
    end: int
    message: str
    color: str  # red, blue, yellow

class DiagnosticFormatter:
    """Ariadne-inspired diagnostic formatter"""

    def format_ambiguity(
        self,
        ambiguity: Ambiguity,
        prompt: str
    ) -> str:
        """Generate rich formatted diagnostic"""
        lines = []

        # Header
        lines.append(f"IR Ambiguity Detected: {ambiguity.category}")
        lines.append(f"   ┌─ user_prompt:{ambiguity.location.line}:{ambiguity.location.col}")
        lines.append(f"   │")

        # Source line with annotations
        source_line = prompt.split("\n")[ambiguity.location.line - 1]
        lines.append(f" {ambiguity.location.line} │ {source_line}")

        # Span annotations
        for span in ambiguity.spans:
            underline = " " * span.start + "^" * (span.end - span.start)
            lines.append(f"   │ {underline} {span.message}")

        # Suggestions
        if ambiguity.suggestions:
            lines.append(f"   │")
            lines.append(f"   = Suggestions:")
            for sugg in ambiguity.suggestions:
                lines.append(f"     • {sugg}")

        return "\n".join(lines)
```

**Estimated Effort**: 2-3 days

---

## Risk Analysis

### Risk 1: Scope Creep in Phase 4
**Risk**: Phase 4 already ambitious, adding enhancements may cause delays
**Mitigation**:
- **Option D (Minimal)**: Only Enhancement 2 (+0.5 week)
- **Option C**: Defer all to Phase 6
- Enhancements are independent (can drop if needed)

### Risk 2: Semantic Token Performance
**Risk**: Generating tokens for large files may be slow
**Mitigation**:
- Cache tokens in `GeneratedCode.metadata`
- Generate incrementally on IR updates
- Expected size: ~1KB per 100 lines (negligible)

### Risk 3: Frontend Complexity
**Risk**: Custom semantic highlighting adds React complexity
**Mitigation**:
- Use `react-syntax-highlighter` (mature library)
- Or Monaco Editor (built-in semantic tokens)
- Fallback: Plain syntax highlighting

### Risk 4: Over-Engineering
**Risk**: Building LSP-style infrastructure we don't fully use
**Mitigation**:
- Start minimal (Enhancement 2 only)
- Enhancements 1, 3, 4 are optional
- Defer based on user feedback

---

## Success Metrics

### Enhancement 2: Semantic Highlighting (Minimal)

**Must Have**:
- ✅ Generated code has semantic tokens
- ✅ UI visually distinguishes IR-derived vs. boilerplate
- ✅ Hover tooltips show provenance links

**Nice to Have**:
- ✅ Users report better understanding (survey: "I understand where code came from")
- ✅ Increased trust in generated code
- ✅ Reduced "why did it generate this?" questions

**Measurement**:
- Track hover interactions (analytics)
- User survey: "How clear is the code provenance?" (1-10 scale)
- Target: 8+/10 satisfaction

---

## Final Recommendations

### Primary Recommendation: **Option D (Minimal)**

**Adopt**:
- ✅ **Enhancement 2: Semantic Highlighting** (3-4 days in Phase 4)

**Defer**:
- 🟡 Enhancement 1, 3, 4 to Phase 6 (based on user feedback)

**Rationale**:
1. **Enhancement 2 is core to Phase 4**: Provenance visualization requires showing IR-to-code mapping
2. **Minimal scope increase**: +0.5 week to Phase 4 (+6-12%)
3. **High ROI**: Critical feature, reasonable effort
4. **Phase 3 already extended**: ACE/MuSLR added 2 weeks
5. **User feedback first**: Polish UX based on what users actually need

**Timeline Impact**: 54 weeks → 54.5-55 weeks (+0.9-1.8%)

---

### Alternative Recommendation: **Option A (Full Integration)**

**If user prioritizes UX quality**:
- Adopt Enhancements 1, 2, 4 in Phase 4 (6-8 days)
- Defer Enhancement 3 to Phase 6

**Rationale**:
- Rich diagnostics significantly improve refinement experience
- Severity levels are quick win (1 day)
- All synergize with Phase 4 goals

**Timeline Impact**: 54 weeks → 55-56 weeks (+1.8-3.7%)

---

## Comparison: All Research

### Research Summary

| Research Topic | Critical Enhancements | Timeline Impact | Status |
|----------------|----------------------|-----------------|--------|
| **ACE + MuSLR** | 4 high-priority (7-10 days) | +2 weeks to Phase 3 | ✅ Approved |
| **Semantic Annotation (Minimal)** | 1 enhancement (3-4 days) | +0.5 week to Phase 4 | 🟡 Proposed |
| **Semantic Annotation (Full)** | 3 enhancements (6-8 days) | +1-2 weeks to Phase 4 | 🟡 Proposed |

### Combined Timeline Impact

**If Minimal Semantic Annotation Adopted** (Recommended):
- **Original Plan**: 52 weeks
- **With ACE/MuSLR**: 54 weeks (+3.8%)
- **With Semantic Annotation**: 54.5-55 weeks (+4.8-5.8%)
- **Total Increase**: 2.5-3 weeks (+4.8-5.8%)

**If Full Semantic Annotation Adopted**:
- **Total**: 55-56 weeks (+5.8-7.7%)
- **Total Increase**: 3-4 weeks

---

## Next Steps

### Immediate (No Action Required)

This research is **informational only** - no code changes in this pass.

### Decision Point: Before Phase 4 Starts (Week 25)

**Question**: Adopt semantic annotation enhancements in Phase 4?

**Options**:
- **A**: Full integration (Enhancements 1, 2, 4) - 6-8 days
- **B**: Phase 3 + 4 split - 6-8 days
- **C**: Defer all to Phase 6 - 0 days
- **D**: Minimal (Enhancement 2 only) - 3-4 days [**RECOMMENDED**]

### If Option D Adopted:

1. ✅ Created Bead item for Enhancement 2 (lift-sys-170) - **DONE**
2. Update Phase 4 task dependencies
3. Design semantic token schema
4. Extend `GeneratedCode.metadata` for provenance tracking
5. Implement during Phase 4 weeks 26-27

---

## Documentation Reference

**This Research**:
- `SEMANTIC_ANNOTATION_RESEARCH.md` (comprehensive analysis)
- `SEMANTIC_ANNOTATION_PROPOSAL.md` (this document)

**Previous Research**:
- `ACE_RESEARCH_ANALYSIS.md`
- `ACE_IMPLEMENTATION_PROPOSAL.md`
- `MUSLR_RESEARCH_ANALYSIS.md`
- `MUSLR_IMPLEMENTATION_PROPOSAL.md`
- `APPROVED_ENHANCEMENTS_SUMMARY.md`

---

## Conclusion

VS Code semantic highlighting, Ariadne diagnostics, and LSP protocol provide proven patterns for rich visual feedback.

**Key Insight**: Enhancement 2 (Semantic Highlighting) is **core to Phase 4 provenance visualization**, while others are valuable UX polish.

**Recommended Action**: **Option D (Minimal)** - Adopt Enhancement 2 only (3-4 days in Phase 4), defer others to Phase 6.

**Status**: Research complete, awaiting user decision before Phase 4.

---

**End of Proposal**
