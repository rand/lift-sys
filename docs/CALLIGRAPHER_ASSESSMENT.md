# Calligrapher Assessment for lift-sys Integration

**Date**: October 14, 2025
**Version**: 1.0 (Final)
**Status**: Assessment Complete - **DO NOT INTEGRATE**
**Repository**: https://github.com/rand/calligrapher

---

## Executive Summary

Calligrapher is an **excellent static analysis tool** for Python call graph extraction and code comprehension. However, it is **fundamentally incompatible** with lift-sys's specification-driven development goals.

**Key Finding**: Calligrapher analyzes **what code does syntactically** (AST → call graph), while lift-sys specifies **what code should do semantically** (intent → verified code). These are complementary tools, not overlapping capabilities.

**Recommendation**: **DO NOT INTEGRATE**. Proceed with Loom-inspired approach for lift-sys reverse mode.

**Functional Overlap**: ~15% (basic signature extraction only)

---

## Repository Overview

### Project Details

- **Primary Language**: Zig (98.4% of codebase)
- **Target Language**: Python static analysis (planned: Rust, JavaScript, TypeScript, Zig)
- **Version**: v0.1.0 (released October 13, 2025)
- **Maturity**: Early stage, work in progress
- **License**: MIT
- **Code Quality**: High (50+ tests, CI, memory audits)

### Repository Structure

```
calligrapher/
├── src/           # Core Zig implementation (20 modules)
│   ├── callgraph.zig
│   ├── parser.zig
│   ├── extractors.zig
│   ├── resolution.zig
│   ├── export.zig
│   └── query.zig
├── docs/          # Extensive documentation
├── examples/      # Python test projects
└── test/          # Comprehensive test suite
```

### Documentation Quality

**Excellent** - Includes:
- QUICKSTART.md
- API.md
- Performance documentation
- Testing strategy
- Detailed roadmap

---

## Current Capabilities

### What Calligrapher DOES

**Static Code Analysis:**
- ✅ Call graph extraction (functions, classes, methods)
- ✅ Symbol resolution and scoping
- ✅ Type annotation tracking
- ✅ Complexity analysis (cyclomatic complexity, control flow depth, nesting)
- ✅ Multi-file project analysis
- ✅ Dependency tracking
- ✅ Query operations (find callers/callees, symbol search, path finding)

**Export Formats:**
- JSON (structured data)
- DOT (GraphViz visualization)
- Mermaid (diagrams)

**Performance:**
- 100k LOC analyzed in <10 seconds (roadmap goal)
- Memory-efficient Zig implementation

### What Calligrapher DOES NOT DO

**Critical Gaps for lift-sys:**
- ❌ **Contract-based programming**: No contract specifications
- ❌ **Code generation**: Only analyzes code, doesn't generate it
- ❌ **Formal verification**: No SMT integration
- ❌ **Intent tracking**: No intent clauses or semantic specifications
- ❌ **Reverse mode (lift-sys sense)**: No extraction of high-level intent from code
- ❌ **Forward mode**: No contract → code generation
- ❌ **Typed holes**: No ambiguity tracking mechanism
- ❌ **Assertion extraction**: No preconditions/postconditions
- ❌ **Effect tracking**: No side effect specifications
- ❌ **Provenance**: No source/confidence tracking

**Search Confirmation:**
- No references to "contract" in codebase
- No references to "specification" (formal specs)
- No references to "generation" (code generation)

---

## IR/Data Model Analysis

### Calligrapher's Data Model

```zig
Symbol {
    name: string
    kind: SymbolKind (function, method, class)
    range: SourceRange
    metadata: CodeMetrics (complexity)
    scope_id: ?ScopeId
    parent_id: ?SymbolId
}

Node {
    parent_id: NodeId
    node_type: NodeType
    source_range: SourceRange
    symbol_id: ?SymbolId
}

Edge {
    from_node: NodeId
    to_node: NodeId
    edge_type: EdgeType (calls, inherits)
}
```

**What It Tracks:**
- ✅ Source code locations
- ✅ Symbol hierarchy
- ✅ Call relationships
- ✅ Complexity metrics
- ✅ Control flow (loops, conditionals, nesting)
- ✅ Argument context
- ✅ Recursion detection
- ✅ Data flow (variable reads/writes)

**What It DOES NOT Track:**
- ❌ Intent or purpose (natural language)
- ❌ Contracts or assertions
- ❌ Formal specifications
- ❌ Effect clauses
- ❌ Provenance
- ❌ Typed holes or ambiguities
- ❌ Verification evidence

---

## Comparison with lift-sys IR

### lift-sys IR Structure (Target)

```python
IntermediateRepresentation {
    intent: IntentClause           # What the code should do
    signature: SigClause           # Function interface
    effects: List[EffectClause]    # Side effects
    assertions: List[AssertClause] # Logical invariants
    metadata: Metadata             # Provenance, evidence
}

TypedHole {
    identifier: str
    type_hint: str
    description: str
    constraints: dict
    kind: HoleKind
}

Provenance {
    source: ProvenanceSource
    confidence: float
    timestamp: str
    author: str
    evidence_refs: list[str]
}
```

### Functional Overlap Analysis

| lift-sys Component | Calligrapher Equivalent | Overlap | Notes |
|-------------------|------------------------|---------|-------|
| **IntentClause** (summary, rationale) | ❌ None | **0%** | No semantic intent tracking |
| **SigClause** (name, params, returns) | ✅ Symbol (name, kind), partial params | **30%** | Basic signature only |
| **EffectClause** (side effects) | ⚠️ Partial (tracks calls, data flow) | **20%** | Syntactic only, no semantic effects |
| **AssertClause** (formal predicates) | ❌ None | **0%** | No contract extraction |
| **TypedHole** (ambiguity tracking) | ❌ None | **0%** | No ambiguity mechanism |
| **Provenance** (source, confidence) | ❌ None | **0%** | No provenance tracking |
| **Metadata** (evidence, tracing) | ⚠️ Partial (source location only) | **10%** | Location only, no evidence |

**Total Functional Overlap: ~15%**

**Verdict**: Calligrapher provides low-level syntactic structure, but lift-sys needs high-level semantic specifications. The gap is too large.

---

## Roadmap Analysis

### Current Priorities (M8 Production Hardening)

- API stabilization
- Performance optimization (100k LOC in <10 seconds)
- Multi-language support (5 languages by v1.0)
- LSP implementation
- IDE integrations
- CI/CD plugins

### Future Features (M9+)

- Symbolic execution
- Machine learning integration
- Interactive analysis tools
- Additional languages (Go, C/C++, Java)

### Notable Absence

- ❌ No mention of contract-based programming
- ❌ No mention of code generation
- ❌ No mention of formal verification
- ❌ No mention of intent extraction
- **Focus**: Analysis and visualization, NOT specification or synthesis

**Verdict**: Roadmap diverges from lift-sys needs. No convergence planned.

---

## Integration Assessment

### Potential Advantages (if integrated)

1. **High-Performance Parsing**: Zig-based implementation is extremely fast
2. **Call Graph Analysis**: Could enhance reverse mode with call relationships
3. **Multi-Language Support**: Eventually supports 5+ languages
4. **Mature Tooling**: Good error handling, memory safety, testing

### Critical Disadvantages

1. **Fundamental Purpose Mismatch**:
   - Calligrapher: Static analysis tool (AST → call graph)
   - lift-sys: Specification-driven development (intent → verified code)
   - **Verdict**: Solving different problems

2. **No Shared Abstractions**:
   - Calligrapher has no concept of intent, contracts, or typed holes
   - No formal verification or constraint tracking
   - No code generation capabilities
   - **Verdict**: Incompatible data models

3. **Language Barrier**:
   - Calligrapher: Zig (requires Zig toolchain, FFI overhead)
   - lift-sys: Python (clean integration with existing stack)
   - **Verdict**: Unnecessary complexity

4. **Architectural Mismatch**:
   - Calligrapher exports static snapshots (JSON/DOT/Mermaid)
   - lift-sys needs living IR with refinement, verification, evolution
   - **Verdict**: Different paradigms

5. **Reinvention Required**:
   - Would need to build contract extraction on top of call graphs
   - Would need to add intent inference
   - Would need to add assertion discovery
   - Would need to add provenance tracking
   - **Verdict**: Essentially rebuilding lift-sys reverse mode with Calligrapher as parsing layer

6. **Development Velocity Risk**:
   - Calligrapher is early stage (v0.1.0)
   - Roadmap focuses on analysis, not contracts
   - No indication of alignment with lift-sys goals
   - **Verdict**: Diverging trajectories

### Cost-Benefit Analysis

**Costs:**
- Zig toolchain dependency
- FFI complexity (Python ↔ Zig)
- Data transformation overhead (call graph → IR)
- API maintenance burden
- Architectural complexity

**Benefits:**
- Slightly faster parsing (negligible for lift-sys use case)
- Potential multi-language support (years away, lift-sys already planned)

**Verdict**: **Costs significantly outweigh benefits**

---

## Comparison with Alternatives

### Better Options for lift-sys Reverse Mode

1. **Python AST Module** (Built-in):
   - ✅ Zero dependencies
   - ✅ Perfect Python integration
   - ✅ Sufficient for signature extraction
   - ✅ Can extract docstrings for intent
   - **Verdict**: Simpler and sufficient

2. **ChatLSP + Language Servers** (Already adopted):
   - ✅ Provides signature and type extraction
   - ✅ Multi-language via LSP
   - ✅ Semantic information
   - **Verdict**: Better fit, already integrated

3. **Loom-Inspired Weakest Precondition** (Planned):
   - ✅ Extracts assertions and contracts
   - ✅ Formal verification approach
   - ✅ Language-agnostic algorithms
   - **Verdict**: Exactly what lift-sys needs

4. **Daikon** (Already integrated):
   - ✅ Runtime invariant detection
   - ✅ Assertion extraction from tests
   - **Verdict**: Already working, enhance existing

---

## Recommendation

### DO NOT INTEGRATE Calligrapher ❌

**Rationale:**

1. **Purpose Mismatch**:
   - Calligrapher is a **code comprehension tool** (understand what exists)
   - lift-sys is a **specification-driven development tool** (define what should exist)
   - These are complementary but not substitutable

2. **Minimal Functional Overlap (~15%)**:
   - Only basic signature extraction overlaps
   - All high-value lift-sys capabilities missing (intent, contracts, effects, provenance)

3. **Better Alternatives Available**:
   - Python AST: Better for parsing
   - ChatLSP: Better for types
   - Loom-inspired: Better for contracts
   - Daikon: Better for invariants

4. **Integration Overhead Too High**:
   - Zig FFI complexity
   - Data model transformation
   - Architectural mismatch
   - Maintenance burden

5. **Loom-Inspired Approach is Superior**:
   - Direct alignment with lift-sys goals
   - TypedHoles already implement ambiguity tracking
   - Python-native keeps stack simple
   - Leverages Python ecosystem (mypy, pyre)

### Proceed with Loom-Inspired Implementation ✅

**Timeline**: 6-10 weeks (as originally planned)
**Effort**: Less than integrating Calligrapher (4-6 weeks) + building missing features (8-12 weeks)
**Result**: Purpose-built reverse mode that exactly meets lift-sys needs

---

## Alternative: Keep Projects Complementary

### Recommended Relationship

**Calligrapher and lift-sys should remain separate projects:**

1. **Calligrapher's Niche**: Code comprehension, visualization, call graphs
2. **lift-sys's Niche**: Specification-driven development, verification, synthesis

3. **Potential Collaboration**:
   - Users run Calligrapher separately for code exploration
   - Export lift-sys IR to formats compatible with Calligrapher visualization
   - Cross-reference call graphs with specifications
   - But keep architecturally separate

4. **Example Use Case**:
   ```
   User workflow:
   1. Explore legacy codebase with Calligrapher (understand structure)
   2. Use lift-sys reverse mode to extract specifications
   3. Refine specifications in lift-sys
   4. Generate improved code with lift-sys
   5. Visualize new architecture with Calligrapher
   ```

---

## Specific Recommendations for lift-sys

### Enhance Reverse Mode Instead

**Focus Areas:**

1. **Leverage Python AST**:
   ```python
   import ast
   tree = ast.parse(source_code)
   # Extract intent from docstrings, function names
   # Extract signatures from function definitions
   # Extract effects from function calls, assignments
   ```

2. **Integrate ChatLSP** (already planned):
   - Signature and type extraction
   - Multi-language via LSP
   - Semantic context

3. **Implement Loom-Inspired Verification**:
   - Weakest precondition generation
   - Assertion extraction from code structure
   - SMT-based constraint checking

4. **Enhance Daikon Integration**:
   - Runtime invariant → AssertClause conversion
   - Test-based contract discovery

---

## Conclusion

**Calligrapher is an excellent tool, but for a different problem domain.** Integrating it would be like using a microscope (Calligrapher) when you need a design blueprint system (lift-sys).

**Key Insight**:
- Calligrapher analyzes **what code does syntactically**
- lift-sys specifies **what code should do semantically**

These are complementary perspectives, not overlapping capabilities.

**Final Verdict**: Proceed with Loom-inspired approach. It better aligns with lift-sys's specification-driven development vision, maintains architectural simplicity, and enables the human-AI collaborative refinement loop that is lift-sys's core innovation.

---

## Appendix: Search Results from Calligrapher Repository

**Key files examined**:
- README.md - Project overview and goals
- QUICKSTART.md - Usage examples
- API.md - Data structures and exports
- ROADMAP.md - Development priorities
- src/*.zig - Core implementation (20 modules)

**Key findings**:
- Zero references to "contract"
- Zero references to "specification" (formal sense)
- Zero references to "generation" (code synthesis)
- Focus entirely on analysis and comprehension

**Confirmation**: Calligrapher is NOT a contract-based programming tool. It's a static analysis and visualization tool.

---

**Assessment Complete**: October 14, 2025
**Assessor**: Claude (via lift-sys research agent)
**Status**: Unblocking Loom-inspired implementation
