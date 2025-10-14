# Static Analysis Technology Assessment (Phase 4)

**Version**: 1.0
**Date**: October 14, 2025
**Purpose**: Evaluate static analysis technologies for lift-sys reverse mode (Code → IR extraction)

---

## Executive Summary

This document assesses static analysis technologies for extracting IR information (types, signatures, assertions) from existing code for lift-sys's reverse mode:

1. **stack-graphs**: GitHub's language-agnostic name resolution (ARCHIVED - not actively maintained)
2. **Nuanced**: Python static analysis for AI coding tools (new, promising)
3. **Loom** (re-evaluated): Specification extraction from Lean 4 programs
4. **Existing Python tools**: pytype, mypy, jedi, pyright

**Key Finding**: lift-sys already has working reverse mode with AST parsing + dynamic analysis (Daikon). For incremental improvements:
- **Short-term**: Use Pyright/mypy for better type inference (already integrated via ChatLSP)
- **Medium-term**: Evaluate Nuanced for enriched call graphs
- **Long-term**: Consider Loom's approach for formal specification extraction (reference architecture)

**Recommendation**: Focus on **improving existing reverse mode** rather than major new integrations. ChatLSP (Phase 2) already provides LSP-based type information, which addresses the main gap.

---

## Technology 1: stack-graphs

**Repository**: https://github.com/github/stack-graphs (ARCHIVED)
**Category**: Language-Agnostic Name Resolution
**Status**: Archived by GitHub, no longer actively maintained

### Overview

Stack-graphs is GitHub's framework for precise code navigation using graph-based name resolution. It enables "jump to definition" and "find all references" across programming languages without requiring build system configuration.

**Key Innovation**: Uses incremental, file-by-file graph construction to scale to millions of repositories, with Tree-sitter integration for parsing.

### Core Capabilities

- **Cross-file name resolution**: Resolves references across file boundaries
- **Language-agnostic**: Declarative DSL for defining language-specific rules
- **Incremental**: File-level graph construction for scalability
- **Tree-sitter integration**: Leverages existing parsers

### Evaluation for lift-sys Reverse Mode

#### Relevance for Code → IR Extraction (Score: 3/5)

**Can it extract information needed for lift-sys IR?**
- **PARTIALLY**: Focuses on name resolution, not full IR extraction
- Can find function definitions and references
- Cannot extract preconditions/postconditions
- Cannot infer assertions or contracts

**What it provides**:
- ✅ Function signatures (name, parameters)
- ✅ Cross-file dependencies
- ⚠️  Limited type information
- ❌ No assertion extraction
- ❌ No invariant detection

**For lift-sys IR**:
- Can populate SigClause (name, parameters)
- Cannot populate AssertClause
- Cannot populate IntentClause
- **Verdict**: Useful but incomplete

#### Multi-Language Support (Score: 5/5)

- Language-agnostic design
- Works with Python, TypeScript, Rust, Go, Java, etc.
- Requires defining rules for each language
- **Excellent** for lift-sys's multi-language goals

#### Maturity (Score: 2/5)

- **ARCHIVED**: No longer maintained by GitHub
- Would need to fork and maintain
- Powers GitHub's code navigation (proven at scale)
- **Verdict**: Proven technology but abandoned

#### Integration Effort (Score: 2/5)

- Requires forking archived repository
- Need to define language rules for Python/TypeScript/Rust/Go
- Rust implementation (requires Rust expertise)
- Estimated effort: 6-8 weeks
- **Verdict**: Moderate-to-high effort for abandoned tech

### Recommendation

**DO NOT ADOPT stack-graphs** for lift-sys

**Reasons**:
1. ❌ Archived/abandoned by GitHub
2. ❌ Incomplete for IR extraction (no assertions)
3. ⚠️  Significant maintenance burden
4. ✅ **Alternative**: Language servers (Pyright, tsserver, rust-analyzer) provide similar capabilities with active maintenance

---

## Technology 2: Nuanced

**Repository**: https://github.com/nuanced-dev/nuanced
**Category**: Python Static Analysis for AI Coding Tools
**Status**: Active development (v0.1.9, new project)

### Overview

Nuanced generates enriched function call graphs of Python packages using static analysis, providing AI coding assistants with compiler-grade knowledge about code behavior.

**Key Innovation**: Combines call graph generation with symbol/type facts, dataflow, and control flow analysis specifically designed for AI tooling integration.

### Core Capabilities

- **Call graph generation**: Function-level call relationships
- **Symbol facts**: Variable definitions, usages, scopes
- **Type facts**: Inferred type information
- **Dataflow analysis**: Value flow through program
- **Control flow analysis**: Execution paths
- **MCP server integration**: Powers Cursor, Claude Code, Codex

### Evaluation for lift-sys Reverse Mode

#### Relevance for Code → IR Extraction (Score: 4/5)

**Can it extract information needed for lift-sys IR?**
- **YES, MOSTLY**: Provides rich static analysis
- Call graphs useful for understanding program flow
- Type facts can populate SigClause type hints
- Symbol facts can identify function signatures

**What it provides**:
- ✅ Function signatures with types
- ✅ Call graph relationships
- ✅ Dataflow information (useful for assertions)
- ⚠️  Control flow (useful for invariants)
- ❌ No explicit precondition/postcondition extraction

**For lift-sys IR**:
- Can populate **SigClause** (name, parameters, returns with types)
- Can help infer **IntentClause** (from call graph + dataflow)
- Cannot directly populate **AssertClause** (need dynamic analysis)
- **Verdict**: Very useful for reverse mode

#### Multi-Language Support (Score: 1/5)

- **Python only**: No support for TypeScript, Rust, Go
- Uses Python-specific analysis (jarviscg fork)
- **Incompatible** with lift-sys's multi-language goals
- **Major limitation**

#### Maturity (Score: 2/5)

- **Very new**: v0.1.9 (early stage)
- Active development
- Y Combinator backed (good support)
- Not production-tested at scale
- **Verdict**: Promising but immature

#### Integration Effort (Score: 4/5)

- **Easy**: Python library with CLI
- Clean API: `nuanced init`, `nuanced enrich`
- JSON output for programmatic access
- Good documentation (though docs site has 404s)
- Estimated effort: 2-3 weeks
- **Verdict**: Easy to integrate

### Recommendation

**CONSIDER Nuanced for Python-only reverse mode improvements**

**Use cases**:
- ✅ Enhanced Python type inference (beyond AST parsing)
- ✅ Call graph analysis for better IntentClause generation
- ✅ Dataflow analysis for assertion inference

**Limitations**:
- ❌ Python only (breaks multi-language requirement)
- ⚠️  Early stage (v0.1.9)
- ⚠️  No TypeScript/Rust/Go support

**Decision**:
- **Short-term**: Skip Nuanced (breaks multi-language)
- **Long-term**: Consider if Python-specific analysis becomes critical
- **Alternative**: Use Pyright via ChatLSP (already integrated, multi-language)

---

## Technology 3: Loom (Re-evaluated for Reverse Mode)

**Repository**: https://github.com/verse-lab/loom
**Category**: Specification Extraction from Code
**Status**: Research prototype (Lean 4)

### Re-evaluation for Reverse Mode

As the user insightfully noted, Loom may be more useful for **reverse mode (Code → IR)** than for synthesis.

### What Loom Provides for Reverse Mode

#### Specification Extraction

Loom analyzes imperative programs to extract:
- **Preconditions** (`requires` clauses) → AssertClause
- **Postconditions** (`ensures` clauses) → AssertClause
- **Loop invariants** (`invariant` annotations) → AssertClause
- **Function signatures** → SigClause

**This is exactly what lift-sys reverse mode needs!**

#### Weakest Precondition Generation

Loom automatically generates weakest preconditions:
- Given a postcondition, infer required precondition
- Useful for extracting missing assertions
- Can help populate AssertClause from code

#### Verification Conditions

Loom generates verification conditions:
- Logical formulas that must hold for correctness
- Can be used to extract assertions
- SMT solver (cvc5) checks these conditions

### Evaluation for lift-sys Reverse Mode

#### Relevance for Code → IR Extraction (Score: 4/5)

**Can it extract specifications from code?**
- **YES**: This is Loom's purpose!
- Extracts preconditions, postconditions, invariants
- Generates verification conditions
- **Perfect match** for populating AssertClause

**What it provides for lift-sys IR**:
- ✅✅ **AssertClause**: Preconditions, postconditions, invariants
- ✅ **SigClause**: Function signatures
- ✅ Formal specifications (can be converted to natural language for IntentClause)
- ⚠️  **Requires manual annotation** of code with `requires`/`ensures`

**Limitations**:
- Lean 4 code only (not Python/TypeScript/Rust/Go)
- Requires developers to annotate code with specifications
- Cannot extract specifications from unannotated code

**Score justification**: 4/5 because Loom excellently extracts specifications, but only from Lean 4 code with manual annotations.

#### Approach as Reference Architecture (Score: 5/5)

**Can Loom's approach inform lift-sys's reverse mode?**
- **YES, ABSOLUTELY**!
- Loom demonstrates **how** to extract specifications
- Techniques are language-agnostic (conceptually)
- Can be adapted to Python/TypeScript/Rust/Go

**Key insights from Loom**:
1. **Weakest precondition generation**: Given postcondition, infer precondition
2. **Verification condition extraction**: Extract logical formulas from code
3. **Monadic shallow embedding**: Model side effects systematically
4. **Automated proof search**: Use SMT solvers to discharge proof obligations

**For lift-sys**:
- Can implement similar weakest precondition algorithm for Python
- Can extract verification conditions from Python code
- Can use Z3 (instead of cvc5) for SMT checking
- **Verdict**: Excellent reference architecture

#### Multi-Language Support (Score: 1/5)

- **Lean 4 only**: No Python/TypeScript/Rust/Go support
- Techniques are language-agnostic, but implementation is not
- Would need to reimplement for each target language
- **Major limitation**

#### Integration Effort for Direct Use (Score: 1/5)

- **Not practical**: Would require rewriting lift-sys codebases in Lean 4
- Estimated effort: 6-12 months
- **Not recommended for direct integration**

#### Integration Effort as Reference (Score: 5/5)

- **Very practical**: Study Loom's algorithms, adapt to lift-sys
- Weakest precondition generation can be implemented in Python
- Verification condition extraction can be language-specific
- Estimated effort: 4-6 weeks to implement Loom-inspired algorithms
- **Recommended approach**

### Recommendation

**ADOPT Loom's approach (not Loom itself) for lift-sys reverse mode**

#### How to Use Loom:

1. **Study Loom's Algorithms**
   - Weakest precondition generation
   - Verification condition extraction
   - Monadic modeling of side effects

2. **Implement Loom-Inspired Algorithms for Python**
   ```python
   # Example: Weakest precondition for Python
   def weakest_precondition(stmt: ast.AST, postcondition: Assertion) -> Assertion:
       """Given statement and postcondition, compute required precondition"""
       if isinstance(stmt, ast.Assign):
           # Substitute assigned variable with RHS in postcondition
           return substitute(postcondition, stmt.target, stmt.value)
       elif isinstance(stmt, ast.If):
           # Branch analysis
           true_wp = weakest_precondition(stmt.body, postcondition)
           false_wp = weakest_precondition(stmt.orelse, postcondition)
           return (stmt.test and true_wp) or (not stmt.test and false_wp)
       # ... more cases
   ```

3. **Adapt to TypeScript, Rust, Go**
   - Same algorithms, different AST structures
   - Language-specific type systems
   - Estimated effort: 1-2 weeks per language

4. **Integrate with lift-sys Reverse Mode**
   - Enhance `lift_sys/reverse_mode/analyzers.py`
   - Add Loom-inspired specification extraction
   - Complement existing Daikon dynamic analysis

#### Benefits:

- ✅ **AssertClause extraction** from code structure
- ✅ **Formal specifications** with SMT verification
- ✅ **Multi-language** (adapt algorithms per language)
- ✅ **Complements dynamic analysis** (Daikon)

#### Effort:

- **Research Loom**: 1 week
- **Implement for Python**: 3-4 weeks
- **Extend to TypeScript/Rust/Go**: 1-2 weeks each
- **Total**: 6-10 weeks

**Priority**: P1 (Should integrate Loom-inspired algorithms after Phase 2 technologies)

---

## Technology 4: Calligrapher (User's Project) ✅ ASSESSED

**Repository**: https://github.com/rand/calligrapher (User's own project)
**Category**: Static Analysis and Call Graph Extraction
**Status**: **Assessment Complete - DO NOT INTEGRATE**

### Overview

Calligrapher is a **static analysis tool** for Python call graph extraction and code comprehension, written in Zig. Despite initial assumptions about contract-based programming, comprehensive analysis reveals it is **fundamentally incompatible** with lift-sys's specification-driven development goals.

**Actual Capabilities**:
- Static code analysis (AST → call graph)
- Complexity metrics and visualization
- Multi-file project analysis
- Export to JSON/DOT/Mermaid

**Does NOT Provide**:
- ❌ Contract-based specifications
- ❌ Code generation
- ❌ Formal verification
- ❌ Intent tracking
- ❌ Reverse mode (in lift-sys sense)
- ❌ Typed holes or ambiguity tracking

**Key Finding**: Calligrapher analyzes **what code does syntactically**, while lift-sys specifies **what code should do semantically**. These are complementary tools, not overlapping capabilities.

### Potential Relevance for Reverse Mode

#### Verification Condition Extraction

If Calligrapher can extract verification conditions from code, this could help populate:
- **AssertClause**: Extracted preconditions/postconditions
- **SigClause**: Type contracts → parameter/return types
- **IntentClause**: Contract descriptions → intent summaries

#### Round-Trip Translation

If Calligrapher can translate code ↔ contracts, this is essentially **reverse mode**:
- Code → Contract = Code → IR (specification)
- Contract → Code = IR → Code (synthesis)

**This is exactly what lift-sys needs!**

### Comparison with Loom Approach

| Aspect | Loom | Calligrapher | Verdict |
|--------|------|--------------|---------|
| Specification Extraction | Yes (Lean 4) | TBD (likely Python?) | Calligrapher may be more practical |
| Multi-Language | No (Lean 4 only) | TBD | Depends on implementation |
| Type System | Lean 4 types | TBD | Need to assess |
| SMT Integration | Yes (cvc5) | TBD (scored 4/5) | Both likely have SMT |
| Production Readiness | Research prototype | Early (2/5) | Both experimental |
| Integration Effort | High (6-12 months) | Moderate (4/5) | Calligrapher easier |
| User Familiarity | Learning required | **User's own code** | **Huge advantage** |

### Critical Advantage: User's Own Project

**Calligrapher has a unique advantage**: The user (Rand) created it!

This means:
- ✅ **Deep familiarity** with codebase and architecture
- ✅ **Control** over design and evolution
- ✅ **Merge possibility** - Can integrate Calligrapher into lift-sys
- ✅ **Reuse** - Existing algorithms and code
- ✅ **No licensing issues** - User owns both projects

### Assessment Pending

**To properly evaluate Calligrapher for static analysis/reverse mode, we need:**

1. **Review Current State**
   - What reverse mode capabilities does Calligrapher have?
   - Can it extract specifications from code?
   - What languages does it support?

2. **Compare IR Formats**
   - Calligrapher IR vs. lift-sys IR
   - Feature matrix: What does each have that the other lacks?
   - Can they be unified?

3. **Evaluate Verification Condition Extraction**
   - Does Calligrapher extract preconditions/postconditions?
   - How does it handle assertions?
   - Is the approach language-agnostic?

4. **Determine Integration Strategy**
   - **Option A**: Merge Calligrapher into lift-sys
     - Calligrapher becomes lift-sys's reverse mode engine
     - Unified IR format
     - Single codebase

   - **Option B**: Extract specific components
     - Take verification condition extraction algorithms
     - Reimplement in lift-sys
     - Keep projects separate

   - **Option C**: Keep separate with integration
     - Calligrapher as library/service
     - lift-sys calls Calligrapher APIs
     - Maintain independence

### Questions for User

Before completing this assessment, please provide:

1. **Repository Access**: Is https://github.com/rand/calligrapher publicly accessible for review?

2. **Reverse Mode Capabilities**: Does Calligrapher currently support code → contract extraction?
   - If YES: What languages? What can it extract?
   - If NO: Is it on the roadmap?

3. **IR Format Comparison**: How does Calligrapher's IR compare to lift-sys's?
   - IntentClause equivalent?
   - SigClause equivalent?
   - AssertClause equivalent?
   - TypedHole equivalent?

4. **Integration Intent**: What would you prefer?
   - Merge Calligrapher into lift-sys?
   - Extract specific features?
   - Keep separate?

5. **Production Readiness**: What parts of Calligrapher are production-ready?
   - Verification condition extraction?
   - Type inference?
   - Contract checking?

### Preliminary Scoring (Based on Research Plan)

From the research plan, Calligrapher scored **31/45 (68.9%)** for synthesis:
- IR Schema: 4/5
- Type Constraints: 5/5
- SMT Integration: 4/5
- Multi-Language: 3/5
- Integration Effort: 4/5

**For reverse mode (code understanding), estimated scoring:**
- **Relevance**: 4/5 (verification condition extraction is perfect fit)
- **Multi-Language**: 3/5 (depends on implementation)
- **Maturity**: 2/5 (early stage)
- **Integration Effort**: 5/5 (**user's own code = easiest integration**)
- **Impact**: 4-5/5 (could be transformative if capabilities match)

### Assessment Results ✅

**Comprehensive assessment completed** (see `CALLIGRAPHER_ASSESSMENT.md` for full details).

**Key Findings**:
1. **Functional Overlap**: Only ~15% (basic signature extraction)
2. **Purpose Mismatch**: Code comprehension vs. specification-driven development
3. **No Contract Capabilities**: No intent, assertions, effects, or provenance tracking
4. **Language Barrier**: Zig implementation requires FFI complexity
5. **Roadmap Divergence**: Focus on analysis/visualization, not contracts/synthesis

### Recommendation ✅

**DO NOT INTEGRATE Calligrapher into lift-sys** ❌

**Rationale**:
- Minimal functional overlap (~15%)
- Better alternatives available (Python AST, ChatLSP, Loom-inspired)
- Integration overhead too high (Zig FFI, data transformation)
- Purpose mismatch (analysis vs. specification)
- Would require rebuilding lift-sys reverse mode on top of Calligrapher

**Alternative**: Keep projects complementary
- Users can run Calligrapher separately for visualization
- lift-sys focuses on specification-driven development
- Cross-reference but maintain architectural separation

**Decision**: **PROCEED with Loom-inspired implementation** ✅

**Priority**: **P1 (Unblocked)** - Loom-inspired implementation can proceed as originally planned (6-10 weeks).

---

## Comparative Analysis

### Static Analysis Tools for Reverse Mode

| Technology | Signatures | Types | Assertions | Multi-Lang | Maturity | Integration | Recommendation |
|------------|------------|-------|------------|------------|----------|-------------|----------------|
| **ChatLSP (Phase 2)** | ✅✅ | ✅✅ | ⚠️  | ✅✅ | ⚠️  | ✅ | **ADOPTED** |
| **Pyright** (via ChatLSP) | ✅✅ | ✅✅ | ❌ | Python only | ✅✅ | ✅ | **ADOPTED** |
| **stack-graphs** | ✅ | ⚠️  | ❌ | ✅✅ | ❌ | ⚠️  | **REJECT** (archived) |
| **Nuanced** | ✅✅ | ✅ | ⚠️  | ❌ | ⚠️  | ✅ | **DEFER** (Python only) |
| **Loom (approach)** | ✅ | ✅ | ✅✅ | ⚠️  | ✅ | ⚠️  | **ADOPT APPROACH** ✅ |
| **Calligrapher** | ⚠️ (15%) | ⚠️ (15%) | ❌ (0%) | ⚠️  (Zig) | ⚠️  | ❌ | **REJECT** ❌ |
| **Daikon** (existing) | ❌ | ❌ | ✅✅ | ✅ | ✅✅ | ✅ | **KEEP** |

### Key Insights

1. **ChatLSP Already Solves Most Problems**
   - Phase 2's ChatLSP provides type and signature extraction via language servers
   - Works with Pyright (Python), tsserver (TypeScript), rust-analyzer (Rust), gopls (Go)
   - **No need for additional signature/type extraction tools**

2. **Assertion Extraction is the Gap**
   - Daikon provides dynamic invariants (existing, working)
   - Loom-inspired static analysis can add formal specifications
   - **Calligrapher may provide contract/assertion extraction** (needs assessment)
   - **Opportunity**: Combine static (Loom/Calligrapher) + dynamic (Daikon) for comprehensive assertions

3. **Multi-Language is Critical**
   - stack-graphs: ✅ Multi-language, ❌ Archived
   - Nuanced: ❌ Python only
   - Loom: ⚠️  Lean 4, but algorithms are language-agnostic
   - Calligrapher: ⚠️  TBD (needs assessment)
   - ChatLSP: ✅✅ Language-agnostic LSP
   - **Winner**: ChatLSP + language-specific algorithm implementations

4. **Calligrapher Assessment Complete** ✅
   - **User's own project** but fundamentally incompatible
   - Calligrapher is code analysis tool, not specification tool
   - Only ~15% functional overlap with lift-sys needs
   - **Decision: Do not integrate** - Proceed with Loom-inspired approach

---

## Recommended Architecture for Reverse Mode

### Current State (Partially Implemented)

```
Existing Codebase (Python/TypeScript/Rust/Go)
    ↓
[AST Parsing] Extract signatures (basic)
    ↓
[Daikon] Dynamic invariant detection (existing)
    ↓
Partial IR (SigClause + basic AssertClause)
```

### Enhanced with Phase 2 + Phase 4 Findings

```
Existing Codebase (Python/TypeScript/Rust/Go)
    ↓
[ChatLSP + Language Server] Extract signatures + types
    ↓ (Pyright/tsserver/rust-analyzer/gopls)
SigClause (name, parameters with types, returns with types)
    ↓
[Loom-Inspired Static Analysis] Extract specifications
    ↓ (weakest precondition, verification conditions)
Static AssertClauses (preconditions, postconditions)
    ↓
[Daikon] Dynamic invariant detection
    ↓ (runtime traces)
Dynamic AssertClauses (inferred invariants)
    ↓
[Merge Static + Dynamic] Combine specifications
    ↓
Complete IR (IntentClause + SigClause + AssertClause)
```

**Benefits**:
- ✅ **SigClause**: ChatLSP provides accurate types
- ✅ **AssertClause**: Loom (static) + Daikon (dynamic) = comprehensive
- ✅ **Multi-language**: ChatLSP + language-specific algorithms
- ✅ **Leverages Phase 2**: No redundant work

**Effort**:
- ChatLSP integration: 4-5 weeks (Phase 2, already planned)
- Loom-inspired algorithms: 6-10 weeks (Phase 4 addition)
- Total: 10-15 weeks

---

## Recommended Priorities

### P0: Essential (Already Decided in Phase 2)

1. **ChatLSP + Language Servers**: Signature and type extraction
   - Provides: SigClause population
   - Effort: 4-5 weeks
   - **Status**: Adopted in Phase 2

### P1: High Value (New from Phase 4)

2. **Loom-Inspired Specification Extraction** ✅ UNBLOCKED
   - Provides: Static AssertClause population
   - Effort: 6-10 weeks
   - **Status**: **Calligrapher assessment complete - PROCEED**
   - **Decision**: Build Loom-inspired algorithms (better fit than Calligrapher)

3. **Enhanced Daikon Integration**: Dynamic invariants
   - Provides: Dynamic AssertClause population
   - Effort: 2-3 weeks (improve existing integration)
   - **Status**: Already integrated, can proceed independently

### P2: Nice to Have

4. **Nuanced for Python**: Enhanced Python analysis
   - Provides: Call graphs, dataflow
   - Effort: 2-3 weeks
   - **Status**: Defer (Python-only limitation)

### P3: Not Recommended

5. **stack-graphs**: Cross-file name resolution
   - Provides: Dependencies, references
   - Effort: 6-8 weeks + maintenance
   - **Status**: Reject (archived, incomplete)

---

## Open Questions

**~~CRITICAL (Calligrapher)~~:** ✅ RESOLVED
1. ~~Calligrapher Capabilities~~ → **ANSWERED**: No contract extraction, code analysis only
2. ~~Calligrapher IR~~ → **ANSWERED**: Call graphs, not specifications (~15% overlap)
3. ~~Calligrapher Multi-Language~~ → **ANSWERED**: Zig-based, Python target (FFI complexity)
4. ~~Integration Strategy~~ → **ANSWERED**: Do not integrate, keep complementary

**Loom-Inspired (PROCEEDING):**
5. **Loom Algorithm Complexity**: How difficult to implement weakest precondition for Python/TypeScript?
6. **Multi-Language Algorithms**: Can same specification extraction work across all target languages?

**General:**
7. **Static vs Dynamic Balance**: What % of assertions can be extracted statically vs dynamically?
8. **Integration with Daikon**: How to merge static and dynamic assertions without conflicts?
9. **Production Readiness**: Are static assertion extraction algorithms production-ready or experimental?

---

## Next Steps

**~~IMMEDIATE (Week 0)~~:** ✅ COMPLETE
1. ~~Assess Calligrapher~~ ✅ **DONE** - See `CALLIGRAPHER_ASSESSMENT.md`
2. ~~Decide Integration Strategy~~ ✅ **DONE** - Do not integrate, proceed with Loom-inspired

**Phase A (Weeks 1-10): Forward Mode** ← CURRENT PRIORITY
3. **Complete Phase 2 Integration**: xgrammar + ChatLSP (10 weeks)
   - Week 1-2: xgrammar IR generation (IN PROGRESS: lift-sys-48)
   - Week 3-4: xgrammar code generation
   - Week 5-6: ChatLSP integration
   - Week 7-8: TypeScript support
   - Week 9-10: Production deployment

**Phase C (Weeks 15-24): Reverse Mode - Loom-Inspired Approach** ← UNBLOCKED
4. **Research Loom Algorithms**: Study weakest precondition generation (2 weeks)
5. **POC: Static Assertion Extraction**: Implement for Python (3 weeks)
6. **Multi-Language Extension**: Adapt to TypeScript, Rust, Go (1-2 weeks each)
7. **Enhance Daikon Integration**: Combine static + dynamic (2-3 weeks)
8. **Test on Real Codebases**: Validate reverse mode quality (2 weeks)

---

## Conclusion

**Phase 4 Key Findings**:

1. **ChatLSP (Phase 2) addresses most needs**: Signatures and type extraction via language servers ✅
2. **Assertion extraction is the remaining gap**: Need static specification extraction ✅
3. **Calligrapher assessed and rejected**: Only ~15% overlap, fundamentally different purpose ✅
4. **Loom provides reference architecture**: Weakest precondition generation approach ✅

**Final Recommendations**:

1. **~~IMMEDIATE~~**: ~~Assess Calligrapher~~ ✅ **COMPLETE**
   - Assessment: `CALLIGRAPHER_ASSESSMENT.md`
   - Decision: Do not integrate (minimal overlap, purpose mismatch)
   - Loom-inspired approach is superior for lift-sys needs

2. **Phase A (Weeks 1-10)**: Focus on forward mode (xgrammar + ChatLSP) ← **CURRENT**
   - Week 1-2: xgrammar IR generation (IN PROGRESS)
   - Week 3-10: Complete forward mode integration

3. **Phase C (Weeks 15-24)**: Reverse mode with Loom-inspired algorithms ✅ **UNBLOCKED**
   - Research Loom weakest precondition generation (2 weeks)
   - Implement for Python (3 weeks)
   - Extend to TypeScript, Rust, Go (4-6 weeks)
   - Integrate with Daikon for comprehensive assertions (2-3 weeks)

**Critical Path Updated**:
- ✅ Calligrapher assessment complete
- ✅ Decision made: Proceed with Loom-inspired implementation
- ✅ No blockers for reverse mode architecture
- Focus on Phase A (forward mode) first, then Phase C (reverse mode)

---

## References

- stack-graphs: https://github.com/github/stack-graphs (archived)
- Nuanced: https://github.com/nuanced-dev/nuanced
- Loom: https://github.com/verse-lab/loom
- Calligrapher: https://github.com/rand/calligrapher (assessed - do not integrate, see CALLIGRAPHER_ASSESSMENT.md)
- Daikon: http://plse.cs.washington.edu/daikon/
- ChatLSP Paper: https://arxiv.org/abs/2409.00921

## Related Documents

- **CALLIGRAPHER_ASSESSMENT.md**: Comprehensive assessment of Calligrapher for lift-sys integration (conclusion: do not integrate)
