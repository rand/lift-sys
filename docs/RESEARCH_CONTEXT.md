# Technology Research Context for lift-sys

**Version**: 1.0
**Date**: October 13, 2025
**Purpose**: Establish foundation for evaluating 9 technologies against lift-sys's goals

---

## Part 1: lift-sys's Mission and Goals

### Core Mission
> "Democratize high-quality software creation by making formal verification and AI-assisted development accessible to both engineers and semi-technical contributors through bidirectional transformation between natural language, formal specifications (IR), and verified code."

### Key Value Propositions

1. **Accessibility**: Non-engineers can specify requirements; engineers maintain control
2. **Verification**: Every artifact (IR, code) is formally verified before use
3. **Bidirectionality**: Seamlessly move between code ↔ IR ↔ natural language
4. **Provenance**: Track every change's origin (human, agent, verification)
5. **Iterative Refinement**: Progressive disambiguation through typed holes

### Primary User Workflows

#### Workflow A: Forward Mode (Greenfield Development)
```
Natural Language Prompt
    ↓
Initial IR with Holes (ambiguities identified)
    ↓
Human + Agent Iterative Refinement
    ↓
Complete, Verified IR
    ↓
Generated, Tested Code
    ↓
Validation: Does code match IR? (round-trip)
```

#### Workflow B: Reverse Mode (Legacy Modernization)
```
Existing Codebase
    ↓
Static + Dynamic Analysis
    ↓
Extracted IR with Evidence
    ↓
Improvement Detection (security, quality, performance)
    ↓
Human + Agent Refinement
    ↓
Regenerated, Improved Code
    ↓
Validation: Behavior preserved, quality improved?
```

#### Workflow C: The Core Loop (Bidirectional)
```
Code → IR → Refine → Code → Validate → Iterate
```

### Success Metrics

**Technical:**
- Prompt → IR translation: **95% success rate**
- Code generation: **100% syntax valid**, **80% passes tests**
- Reverse extraction: **95% signature accuracy**
- Round-trip validation: **100% detects mismatches**

**User Experience:**
- Session completion rate: **>80%** (user reaches finalized IR)
- Time to working code: **<10 minutes** from prompt
- Agent suggestions accepted: **>60%**
- Verification finds real bugs: **>30% of projects**

**Business:**
- Reduce specification time: **>40%** vs. manual documentation
- Adoption in **>3 organizations** within 6 months
- User NPS score: **>40**

### Key Differentiators

1. **IR as Living Contract**: Not just intermediate format, but the source of truth
2. **Typed Holes**: Explicit ambiguity tracking with agent assists
3. **Provenance Tracking**: Full audit trail of every IR element's origin
4. **Bidirectional**: Unlike Copilot (code only) or Cursor (edit only)
5. **Verification-First**: SMT checking, not just syntax validation
6. **Multi-Language by Design**: Language-agnostic IR with extensible code generation and analysis

---

## Part 2: Current Architecture and Integration Points

### High-Level Architecture

```
┌─────────────────────────────────────────────┐
│           User Interfaces                   │
│  Web UI │ CLI │ TUI │ Python SDK           │
└─────────────────┬───────────────────────────┘
                  │ HTTP/WebSocket
┌─────────────────▼───────────────────────────┐
│         FastAPI Backend                     │
│  • Session Management                       │
│  • OAuth & Auth                             │
│  • Progress Streaming                       │
└──────┬────────┬──────────┬──────────────────┘
       │        │          │
   ┌───▼───┐ ┌─▼────┐ ┌───▼────┐
   │Forward│ │Reverse│ │Planner │
   │ Mode  │ │ Mode  │ │        │
   └───┬───┘ └──┬───┘ └───┬────┘
       │        │          │
       └────────┴──────────┘
                │
        ┌───────▼────────┐
        │   IR (Core)    │
        │  • Versioning  │
        │  • Provenance  │
        │  • Validation  │
        └────────────────┘
```

### Key Components and Status

#### ✅ Production-Ready (100% Implemented)
1. **IR Data Model**
   - Complete schema with all clauses
   - Versioning, provenance, comparison, merging
   - Typed holes for ambiguity tracking
   - JSON serialization

2. **Session Management**
   - Full lifecycle (create, refine, finalize)
   - Revision history
   - In-memory persistence
   - Multi-interface access

3. **Infrastructure**
   - OAuth with GitHub
   - Multi-provider config (Anthropic, OpenAI, Gemini, vLLM)
   - Modal deployment
   - Repository management
   - WebSocket progress streaming

4. **UI Components**
   - React + shadcn/ui
   - All views functional
   - Version history visualization
   - IR diff viewer
   - Proactive analysis display

5. **Testing & CI/CD**
   - 100+ tests
   - GitHub Actions
   - Error handling
   - Documentation

#### ❌ Stubbed/Non-Functional (Needs Implementation)

1. **Forward Mode: Prompt → IR**
   - **Current**: Regex pattern matching
   - **Status**: 95% stubbed
   - **Gap**: No LLM integration, no semantic understanding
   - **Integration Point**: `lift_sys/spec_sessions/translator.py`

2. **Forward Mode: Constrained Generation**
   - **Current**: Splits intent string on whitespace
   - **Status**: 100% stubbed
   - **Gap**: No actual LLM calls, no grammar enforcement
   - **Integration Point**: `lift_sys/forward_mode/controller_runtime.py`

3. **Forward Mode: Code Generation**
   - **Current**: Generates `raise NotImplementedError()`
   - **Status**: Stubs only
   - **Gap**: No function bodies, code doesn't run
   - **Integration Point**: `lift_sys/codegen/generator.py`

4. **Reverse Mode: Static Analysis**
   - **Current**: Returns hardcoded placeholder data
   - **Status**: 100% stubbed
   - **Gap**: No CodeQL, no Daikon, no real invariant extraction
   - **Integration Point**: `lift_sys/reverse_mode/analyzers.py`

5. **Reverse Mode: Code → IR Extraction**
   - **Current**: Hardcoded signatures, no AST parsing
   - **Status**: 50% stubbed
   - **Gap**: No type extraction, no semantic analysis
   - **Integration Point**: `lift_sys/reverse_mode/lifter.py`

### Technology Stack

**Backend:**
- Python 3.11+
- FastAPI
- Git (for repository management)
- Z3 (SMT solver, partially integrated)

**Frontend:**
- React + TypeScript
- Vite
- TanStack Query
- shadcn/ui components

**Deployment:**
- Modal (hybrid cloud)
- Docker (local development)

**LLM Providers (configured but not fully utilized):**
- Anthropic Claude
- OpenAI GPT-4
- Google Gemini
- vLLM (local)

**Target Languages (multi-language support required):**
- **Phase 1 (current)**: Python
- **Phase 2 (near-term)**: TypeScript/JavaScript
- **Phase 3 (medium-term)**: Rust, Go
- **Extensible**: Plugin architecture for adding new languages

---

## Part 3: Gap Analysis and Priority Ranking

### Critical Gaps (P0 - Must Fix)

#### Gap 1: No Real LLM-Based Prompt → IR Translation
**Current Problem**: Uses regex heuristics; fails on anything non-trivial
**Impact**: Forward mode doesn't work for real users
**Required Capability**:
- Generate valid IR JSON from natural language
- Identify ambiguities and create typed holes
- Handle complex, multi-clause specifications

**Ideal Solution**:
- Structured/constrained LLM generation
- JSON schema enforcement
- Streaming with validation
- Retry logic for malformed outputs

**Technology Candidates**:
- llguidance (JSON schema enforcement)
- AICI (Wasm controllers)
- xgrammar (grammar-guided generation)

---

#### Gap 2: No Real Code Generation
**Current Problem**: Generates non-functional stubs
**Impact**: Users can't get runnable code from IR
**Required Capability**:
- Generate function bodies that implement IR
- Inject runtime assertion checks
- Generate valid, formatted Python
- Pass tests with 80%+ success rate

**Ideal Solution**:
- LLM-based code generation
- Template-based fallback
- Verification that code matches IR
- Test generation from assertions

**Technology Candidates**:
- Loom (synthesis from specs)
- Calligrapher (contract-based generation)
- llguidance (constrained code generation)

---

#### Gap 3: No Real Static Analysis for Reverse Mode
**Current Problem**: Returns fake hardcoded data
**Impact**: Reverse mode is useless
**Required Capability**:
- Extract function signatures from Python code
- Infer types from usage
- Extract preconditions/postconditions
- Detect security vulnerabilities

**Ideal Solution**:
- AST-based signature extraction
- Flow-sensitive type inference
- Pattern-based invariant extraction
- Integration with real analysis tools

**Technology Candidates**:
- stack-graphs (name resolution, cross-file)
- nuanced-py (type inference)
- CodeQL (security analysis)
- Daikon (dynamic invariants)

---

### High-Impact Gaps (P1 - Should Fix)

#### Gap 4: No Round-Trip Validation
**Current Problem**: Can't verify generated code matches IR
**Impact**: No confidence in code generation quality
**Required Capability**:
- Generate code from IR
- Extract IR from generated code
- Compare original vs. extracted IR
- Report mismatches with severity

**Ideal Solution**:
- Automated validation pipeline
- Semantic equivalence checking
- Clear diff visualization
- Suggested fixes

**Technology Candidates**:
- Loom (verification via synthesis)
- Calligrapher (bidirectional translation)
- Custom diff engine

---

#### Gap 5: Slow Inference for Interactive Use
**Current Problem**: Multi-turn refinement sessions may be slow
**Impact**: Poor user experience, high costs
**Required Capability**:
- Reduce latency for prompt → IR translation
- Speed up code generation
- Enable real-time suggestions

**Ideal Solution**:
- Speculative decoding
- Caching and reuse
- Parallel processing
- Smaller draft models

**Technology Candidates**:
- ATLAS (adaptive speculative decoding)
- Parallel Speculative Decoding
- Model distillation

---

### Medium-Impact Gaps (P2 - Nice to Have)

#### Gap 6: Limited Formal Verification
**Current Problem**: SMT checking is basic
**Impact**: Can't prove complex properties
**Required Capability**:
- Prove postconditions from preconditions
- Detect contradictions
- Generate counterexamples

**Technology Candidates**:
- Loom (SMT-based verification)
- Z3 (expand usage)

#### Gap 7: No Cross-Language Support
**Current Problem**: Python only
**Impact**: Limited applicability
**Required Capability**:
- Support TypeScript, Rust, Go
- Language-agnostic IR
- Multi-language code generation

**Technology Candidates**:
- stack-graphs (language-agnostic)
- xgrammar (multi-language)

---

## Part 4: Specific Research Questions by Technology

### Constrained Generation (llguidance, AICI, xgrammar)

**Primary Questions:**
1. Can it enforce our IR JSON schema with 100% reliability?
2. What's the latency overhead for a typical IR generation?
3. Does it support streaming generation?
4. Can we use it with Anthropic/OpenAI APIs or only self-hosted?
5. How does it handle deeply nested structures?
6. What's the error recovery mechanism?

**Experiments to Run:**
- Generate IR from 20 test prompts, measure success rate
- Benchmark latency vs. unconstrained generation
- Test with malformed schemas
- Evaluate developer experience

**Success Criteria:**
- 95%+ valid IR generation
- <2x latency overhead
- Works with at least one major provider
- Clear error messages

---

### Program Synthesis (Loom, Calligrapher)

**Primary Questions:**
1. Can Loom generate runnable Python from our IR?
2. How does Calligrapher's IR compare to lift-sys's IR?
3. What verification techniques are reusable?
4. Can we extract synthesis algorithms without full integration?
5. What's the synthesis time for typical functions?
6. How complete does the IR need to be?

**Experiments to Run:**
- Convert lift-sys IR to Loom format
- Run synthesis on example specifications
- Measure synthesis time
- Evaluate code quality

**Success Criteria:**
- Generated code compiles 100%
- Code passes tests 80%+
- Synthesis completes in <30 seconds
- Integration is feasible

---

### Static Analysis (stack-graphs, nuanced-py)

**Primary Questions:**
1. How accurate is type inference on real Python code?
2. Can stack-graphs extract inter-procedural dependencies?
3. What's the indexing time for a 100-file repository?
4. Can we query for function contracts?
5. How well does it handle dynamic features (eval, metaclasses)?
6. What's the API for integration?

**Experiments to Run:**
- Index lift-sys codebase
- Query for function signatures
- Measure accuracy vs. ground truth
- Evaluate incremental updates

**Success Criteria:**
- 90%+ accuracy on typed code
- Indexing completes in <60 seconds
- API is Python-friendly
- Incremental updates work

---

### Inference Optimization (ATLAS, Parallel Speculative Decoding)

**Primary Questions:**
1. What's the speedup for our typical workload?
2. Is there quality degradation?
3. Can we self-host or is it service-only?
4. What's the cost-benefit tradeoff?
5. Does it work with our target models?
6. What hardware is required?

**Experiments to Run:**
- Benchmark latency on typical IR generation
- Measure quality degradation
- Calculate cost savings
- Test with different model sizes

**Success Criteria:**
- 2-3x speedup
- <5% quality degradation
- Positive ROI within 6 months
- Feasible deployment

---

## Part 5: Technology Evaluation Framework

### Scoring Rubric (1-5 scale)

#### Relevance to Goals
- **5**: Directly solves a critical gap
- **4**: Strongly addresses a priority need
- **3**: Moderately useful
- **2**: Minor utility
- **1**: Not applicable

#### Maturity
- **5**: Production-ready, widely used
- **4**: Stable, some production use
- **3**: Beta, active development
- **2**: Alpha, experimental
- **1**: Prototype, research only

#### Integration Effort
- **5**: Drop-in replacement, minimal changes
- **4**: Well-defined API, moderate work
- **3**: Significant refactoring required
- **2**: Major architectural changes
- **1**: Incompatible, would need full rewrite

#### Impact
- **5**: Transformative, enables core workflows
- **4**: Significant improvement to key metrics
- **3**: Noticeable enhancement
- **2**: Minor improvement
- **1**: Negligible impact

#### Dependencies
- **5**: No external dependencies
- **4**: Minimal, well-maintained dependencies
- **3**: Moderate dependency complexity
- **2**: Heavy dependencies, some unmaintained
- **1**: Critical dependency on unavailable/unstable components

### Decision Matrix

Technology will be prioritized based on:
```
Priority Score = (Relevance × 3) + (Impact × 2) + Maturity + Integration Effort + Dependencies
Max Score = 55 (all 5s)
```

**Thresholds:**
- **P0 (Must Have)**: Score ≥ 40, Relevance ≥ 4
- **P1 (Should Have)**: Score ≥ 30, Relevance ≥ 3
- **P2 (Nice to Have)**: Score ≥ 20
- **Reject**: Score < 20 or Relevance < 2

---

## Part 6: Integration Requirements

### For Any Technology to be Adopted:

**Technical Requirements:**
1. Must work with Python 3.11+
2. Must integrate with FastAPI backend
3. Must support Modal deployment OR run locally
4. Must not break existing functionality
5. Must have automated tests

**Operational Requirements:**
1. Must be maintainable by 1-2 engineers
2. Must have acceptable licensing (preferably Apache/MIT)
3. Must have reasonable resource requirements
4. Must not significantly increase operational costs
5. Must have acceptable latency for interactive use

**Documentation Requirements:**
1. Must have clear integration documentation
2. Must have examples we can adapt
3. Must have troubleshooting guide
4. Must have performance characteristics documented

---

## Part 7: Success Criteria for Research Phase

At the end of 2-3 weeks, we should have:

1. ✅ **Clear ranking** of all 9 technologies by priority score
2. ✅ **Detailed assessment** documents for each technology
3. ✅ **Integration plans** for top 3 candidates
4. ✅ **Proof-of-concept** results validating top choice
5. ✅ **Updated architecture** diagrams showing integration points
6. ✅ **Risk assessment** for each adoption path
7. ✅ **Resource estimates** (time, cost, people)
8. ✅ **Executive summary** for stakeholders

### Concrete Deliverables

**Documents:**
- `RESEARCH_CONTEXT.md` (this document)
- `CONSTRAINED_GENERATION_ASSESSMENT.md`
- `SYNTHESIS_VERIFICATION_ASSESSMENT.md`
- `STATIC_ANALYSIS_ASSESSMENT.md`
- `INFERENCE_OPTIMIZATION_ASSESSMENT.md`
- `INTEGRATION_ROADMAP.md`
- `RESEARCH_FINDINGS_EXECUTIVE_SUMMARY.md`

**Artifacts:**
- Technology comparison spreadsheet
- Proof-of-concept code (for top choice)
- Performance benchmark results
- Updated architecture diagrams
- Integration task breakdown in Beads

**Decisions:**
- Which constrained generation framework to adopt
- Whether to integrate Loom or build custom synthesis
- Which static analysis tools to use
- Whether to invest in inference optimization

---

## Next Steps

With this context established, we can now proceed to:

**Phase 2**: Research constrained generation technologies (llguidance, AICI, xgrammar)
- Deep dive into each technology
- Run experiments
- Compare approaches
- Make recommendation

**Goal**: By end of Phase 2, know which constrained generation framework (if any) to adopt for lift-sys.

---

## References

- [README.md](../README.md) - Project overview
- [MASTER_PLAN.md](MASTER_PLAN.md) - Strategic roadmap
- [CORE_LOOP_COMPLETION_PLAN.md](CORE_LOOP_COMPLETION_PLAN.md) - Implementation gaps
- [RESEARCH_PLAN.md](RESEARCH_PLAN.md) - Research methodology
