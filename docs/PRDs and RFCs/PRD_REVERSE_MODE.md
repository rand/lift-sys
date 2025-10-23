# Product Requirements Document: Reverse Mode (Code to Specification Recovery)

**Version**: 1.0
**Date**: 2025-10-21
**Status**: Active
**Owner**: Codelift Team

---

## Document Overview

**Purpose**: Define the complete product vision, requirements, and strategy for Reverse Mode - lift's capability for extracting formal specifications from existing codebases.

**Audience**: Product team, engineering team, executive leadership, investors

**Related Documents**:
- [PRD: lift (Main)](PRD_LIFT.md) - Overall product vision
- [RFC: lift Architecture](RFC_LIFT_ARCHITECTURE.md) - Technical architecture
- [IR Specification v0.9](../lift-sys/docs/IR_SPECIFICATION.md) - Semantic IR design
- [Semantic IR Roadmap](../lift-sys/SEMANTIC_IR_ROADMAP.md) - IR adoption plan
- [Integrated Strategy](../lift-sys/docs/planning/INTEGRATED_STRATEGY.md) - IR + DSPy integration

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Problem Statement](#2-problem-statement)
3. [User Personas & Use Cases](#3-user-personas--use-cases)
4. [Functional Requirements](#4-functional-requirements)
5. [Non-Functional Requirements](#5-non-functional-requirements)
6. [Success Metrics](#6-success-metrics)
7. [Technical Approach](#7-technical-approach)
8. [User Experience](#8-user-experience)
9. [Roadmap & Milestones](#9-roadmap--milestones)
10. [Risk Analysis & Mitigation](#10-risk-analysis--mitigation)

---

## 1. Executive Summary

### The Problem

**90% of software development is maintenance, not greenfield creation.** Yet most AI coding tools focus exclusively on generating new code. This leaves critical workflows unaddressed:

- Understanding legacy code with no documentation
- Safely refactoring systems no one fully understands
- Migrating monoliths to microservices without breaking behavior
- Onboarding engineers to complex codebases quickly
- Auditing code for security and compliance

**Current solutions are inadequate:**
- Manual code reading: Slow, error-prone, doesn't scale
- Documentation: Outdated, incomplete, or missing entirely
- Static analysis tools: Catch bugs but don't explain intent
- AI code assistants: Generate new code but can't explain existing code

### The Solution: Reverse Mode

**Reverse Mode extracts formal specifications from existing code**, enabling understanding, safe refactoring, and knowledge preservation.

**How it works:**
1. **Multi-File Analysis**: Analyze entire repositories (1000+ files, 100K+ LOC)
2. **Static Analysis**: Extract types, signatures, call graphs, dependencies
3. **Dynamic Analysis**: Capture execution traces, infer invariants
4. **Security Analysis**: Detect vulnerabilities with CodeQL integration
5. **AI-Assisted Intent Recovery**: Generate IntentSpec from code, docs, and patterns
6. **FuncSpec Generation**: Infer pre/post conditions and constraints
7. **Alignment Maps**: Show IntentSpec ↔ FuncSpec correspondence
8. **Safe Refactoring**: Enable verified transformations via IR

### Current Status (October 2025)

**Infrastructure**: ✅ **COMPLETE**
- Multi-file analysis (100+ files)
- AST extraction and dependency graphs
- CodeQL security integration
- Progress tracking and error handling
- File discovery with intelligent exclusions

**Awaiting Enhancement** (DSPy Phase 2, Months 7-9):
- AI-powered intent extraction
- Semantic understanding of code purpose
- Type inference improvements
- Entity resolution across files

### Value Proposition

**For Engineering Teams**:
- **50% reduction** in time to understand legacy code
- **Zero behavioral regressions** during refactoring
- **3 weeks → 3 days** onboarding time for new engineers
- **Full audit trail** for compliance

**For Technical Leaders**:
- Document tribal knowledge before engineers leave
- De-risk migrations and refactors
- Enable safe technical debt reduction
- Meet regulatory requirements for code understanding

**For AI Agents**:
- Programmatic API for autonomous analysis
- Verifiable specifications for safe automation
- Full provenance for auditing

### Competitive Positioning

| Feature | lift Reverse Mode | GitHub Copilot | Cursor | OpenAI Code Interpreter |
|---------|------------------|----------------|--------|------------------------|
| **Code → Spec** | ✅ Full IR | ❌ No | 🟡 Comments only | ❌ No |
| **Multi-File** | ✅ 1000+ files | ❌ Single file | 🟡 Limited | ❌ No |
| **Security Analysis** | ✅ CodeQL | ❌ No | ❌ No | ❌ No |
| **Dynamic Analysis** | ✅ Daikon | ❌ No | ❌ No | ❌ No |
| **Intent Recovery** | ✅ AI + heuristics | ❌ No | ❌ No | ❌ No |
| **Provenance** | ✅ Full trace | ❌ No | ❌ No | ❌ No |
| **Safe Refactoring** | ✅ IR transformations | ❌ No | ❌ No | ❌ No |

**No other tool combines static + dynamic + semantic analysis for specification extraction.**

---

## 2. Problem Statement

### The Legacy Code Crisis

**Reality**: Most engineering time is spent maintaining existing systems, not building new ones.

**Statistics**:
- 75% of developer time spent understanding existing code (Stack Overflow, 2024)
- Average enterprise has 10-20 year old systems with no documentation
- 60% of security vulnerabilities in legacy code (OWASP)
- $85 billion spent annually on failed software projects, mostly due to poor understanding (Standish Group)

### Specific Pain Points

#### Pain 1: Undocumented Legacy Systems

**Scenario**: A 5-year-old Python service with 10K lines of code. Original author left. No documentation. Team needs to add a feature.

**Current Approach**:
1. Read code manually for days/weeks
2. Make educated guesses about behavior
3. Add feature with fingers crossed
4. Deploy and hope nothing breaks

**Problems**:
- Slow: 1-2 weeks to understand before starting work
- Risky: 40% chance of introducing regressions
- Knowledge loss: Understanding exists only in one engineer's head
- Unsustainable: Repeats every time someone new touches the code

**lift Solution**:
1. Run reverse mode: 30 minutes for full analysis
2. Get formal specs: IntentSpec + FuncSpec for every function
3. Understand behavior: What it does, why, and what constraints matter
4. Add feature confidently with verified transformations
5. Deploy with zero regressions (IR-proven equivalence)

**Impact**: 1-2 weeks → 1-2 days

---

#### Pain 2: Unsafe Refactoring

**Scenario**: Monolith → microservices migration. Team needs to extract authentication service without breaking existing behavior.

**Current Approach**:
1. Manually trace auth code across files
2. Extract to new service
3. Write extensive tests hoping to cover all cases
4. Deploy and monitor for issues
5. Fix production bugs as they appear

**Problems**:
- Missed dependencies: 30% chance of breaking edge cases
- Test coverage gaps: Tests don't cover all behaviors
- Production incidents: Regressions found by users, not tests
- Rollback friction: Hard to revert partial migrations

**lift Solution**:
1. Reverse mode extracts auth specifications
2. Generate IntentSpec for each auth function
3. Generate FuncSpec with pre/post conditions
4. Use IR transformations to extract service
5. Solver verifies behavioral equivalence
6. Deploy with proof of correctness

**Impact**: 30% regression risk → 0% with verified transformations

---

#### Pain 3: Onboarding Friction

**Scenario**: New engineer joins team. Needs to understand 50K LOC codebase to be productive.

**Current Approach**:
1. Read README (if it exists and is current)
2. Ask teammates questions (interrupts their work)
3. Read code for weeks
4. Make small changes, hope they're right
5. Slowly build mental model over 2-3 months

**Problems**:
- Slow: 2-3 months to full productivity
- Distracting: Senior engineers spend time explaining instead of building
- Error-prone: New engineers make mistakes from incomplete understanding
- Inconsistent: Each engineer builds different mental model

**lift Solution**:
1. Reverse mode generates specs for entire codebase
2. New engineer reads IntentSpec for high-level understanding
3. Dives into FuncSpec for specific functions
4. Explores alignment maps to see how intent maps to implementation
5. Uses split-view to connect IR to actual code

**Impact**: 2-3 months → 3-4 weeks to productivity

---

#### Pain 4: Security Audits

**Scenario**: Fintech company needs to prove code meets regulatory requirements before deployment.

**Current Approach**:
1. Manual code review by security team
2. Run static analysis tools (many false positives)
3. Document findings in spreadsheet
4. Developers fix issues
5. Repeat until clean (weeks)

**Problems**:
- Slow: 2-4 weeks per audit
- Incomplete: Static analysis misses business logic vulnerabilities
- Undocumented: Hard to prove what code actually does
- Not repeatable: Each audit starts from scratch

**lift Solution**:
1. Reverse mode with CodeQL integration
2. Extracts specifications + security findings
3. Generates IntentSpec showing what code should do
4. Identifies drift: where implementation diverges from intent
5. Creates full provenance chain for audit trail
6. Exports compliance report with SBOM, SLSA attestations

**Impact**: 2-4 weeks → 3-5 days, with full audit documentation

---

### Market Opportunity

**Total Addressable Market**: All software teams with legacy code (i.e., almost everyone)

**Specific Segments**:
1. **Financial Services**: Regulatory compliance requires code understanding
2. **Healthcare**: HIPAA/FDA require traceability and documentation
3. **Enterprise SaaS**: Large codebases, high turnover, need knowledge preservation
4. **Consulting/Agencies**: Multiple client codebases, frequent onboarding
5. **Open Source**: Community contributions need understanding of existing code

**Market Size**: $30B+ spent annually on code understanding, documentation, and refactoring

---

## 3. User Personas & Use Cases

### Persona 1: Marcus - Senior Backend Engineer

**Demographics**:
- 38 years old, 12 years experience
- Tech lead for 5-person team at F500 company
- Maintains 3 legacy services (15K-50K LOC each)
- Team has 30% annual turnover

**Goals**:
- Understand legacy code quickly when bugs arise
- Refactor safely without introducing regressions
- Onboard new team members faster
- Document tribal knowledge before senior engineers leave

**Pain Points**:
- Spends 60% of time understanding existing code
- Each refactoring is risky (no one understands full system)
- New engineers take 3 months to be productive
- Lost knowledge when senior engineer left with no documentation

**Jobs-to-Be-Done**:

1. **"When** a production bug occurs in legacy code, **I want to** quickly understand what the code does and why, **so I can** fix it confidently without breaking other things"

2. **"When** refactoring for performance, **I want to** prove my changes preserve behavior, **so I can** deploy without fear of regressions"

3. **"When** onboarding a new engineer, **I want to** provide them formal specifications, **so they** understand the codebase in weeks instead of months"

4. **"When** a senior engineer leaves, **I want to** capture their knowledge as formal specs, **so we** don't lose understanding of critical systems"

**How lift Reverse Mode Helps**:
- **Multi-file analysis**: Understand entire services in 30 minutes
- **IntentSpec extraction**: See what code is supposed to do in plain language
- **FuncSpec generation**: Get formal contracts for every function
- **Safe refactoring**: IR transformations with verified equivalence
- **Knowledge preservation**: Specs persist even as engineers leave

**Success Metrics for Marcus**:
- Bug fix time reduced from 2 days → 4 hours
- Zero regressions during refactoring
- New engineer productivity time: 3 months → 3 weeks
- Documentation coverage: 20% → 90% of critical functions

---

### Persona 2: Jennifer - Engineering Manager / Architect

**Demographics**:
- 45 years old, 20 years experience
- Manages 40-person engineering org
- Responsible for legacy migration roadmap
- Reports to CTO, accountable for technical risk

**Goals**:
- De-risk technical debt reduction initiatives
- Enable safe monolith → microservices migration
- Meet compliance requirements for code documentation
- Reduce time spent on "archaeology" work

**Pain Points**:
- Can't quantify risk of refactoring projects
- No way to know if migrations preserve behavior
- Regulatory audits require code documentation we don't have
- Engineers spend 70% of time understanding vs. building

**Jobs-to-Be-Done**:

1. **"When** planning a migration project, **I want to** understand all dependencies and behaviors upfront, **so I can** estimate accurately and avoid surprises"

2. **"When** facing a regulatory audit, **I want to** provide formal specifications for all critical code, **so we** pass compliance without months of manual documentation"

3. **"When** evaluating technical debt, **I want to** measure understanding gap (what code does vs. what we know it does), **so I can** prioritize work effectively"

4. **"When** an engineer proposes a refactoring, **I want to** require proof of behavioral equivalence, **so I** approve confidently"

**How lift Reverse Mode Helps**:
- **Repository analysis**: Understand entire codebase in hours
- **Dependency graphs**: See all relationships and effects
- **Compliance reports**: Auto-generate documentation for audits
- **Drift detection**: Measure gap between intent and implementation
- **Provenance tracking**: Full audit trail for regulatory requirements

**Success Metrics for Jennifer**:
- Migration planning time: 4 weeks → 1 week
- Regulatory audits: 100% pass rate with auto-generated docs
- Refactoring regressions: 30% → 0%
- Engineering productivity: 30% building → 70% building

---

### Persona 3: Sarah - Product Manager (Technical Background)

**Demographics**:
- 32 years old, 5 years PM experience
- CS degree, wrote code early in career (now rusty)
- Works with 8 engineers on B2B SaaS product
- Responsible for feature delivery and roadmap

**Goals**:
- Understand how existing features work (to plan related features)
- Identify opportunities for refactoring during feature planning
- Communicate technical decisions to stakeholders
- Validate that implementations match requirements

**Pain Points**:
- Can't read code fast enough to understand features
- Unsure if implementations match original specs
- Hard to estimate new features without understanding existing code
- Can't explain technical debt to executives

**Jobs-to-Be-Done**:

1. **"When** planning a related feature, **I want to** understand how existing features work, **so I can** estimate effort and identify dependencies"

2. **"When** reviewing implementations, **I want to** verify code matches the original spec, **so I** know it does what was requested"

3. **"When** explaining technical debt to executives, **I want to** show the gap between intent and implementation, **so they** understand the need for refactoring"

**How lift Reverse Mode Helps**:
- **IntentSpec in plain language**: Understand code without reading it
- **Alignment maps**: See where implementation matches/diverges from intent
- **Split-view navigation**: Connect high-level intent to actual code
- **Drift reports**: Quantify technical debt for stakeholders

**Success Metrics for Sarah**:
- Feature planning time: 2 days → 4 hours
- Spec compliance verification: Manual → Automated
- Technical debt communication: Vague → Quantified
- Cross-functional alignment: 70% → 95%

---

### Persona 4: DevSecOps Team - Security & Compliance

**Profile**: Team responsible for security, compliance, and risk management

**Goals**:
- Identify security vulnerabilities before deployment
- Prove code meets regulatory requirements
- Maintain audit trails for compliance
- Automate security analysis in CI/CD

**Pain Points**:
- Manual security reviews don't scale
- Static analysis tools have high false positive rates
- Hard to prove what code actually does for auditors
- No systematic way to track security properties

**Jobs-to-Be-Done**:

1. **"When** deploying to production, **we want to** prove code meets security requirements, **so we** pass compliance without manual review"

2. **"When** auditors ask "what does this code do?", **we want to** provide formal specifications, **so we** answer with evidence, not guesses"

3. **"When** vulnerabilities are discovered, **we want to** understand all affected code paths, **so we** can fix completely, not partially"

**How lift Reverse Mode Helps**:
- **CodeQL integration**: Automated security vulnerability detection
- **Provenance chains**: Full audit trail for every specification
- **Safety manifests**: SBOM, SLSA attestations, OPA policies
- **Dependency graphs**: Understand blast radius of vulnerabilities

**Success Metrics**:
- Security audit time: 4 weeks → 1 week
- Vulnerability detection: 70% → 95% (automated)
- Compliance pass rate: 80% → 100%
- Audit documentation time: 40 hours → 2 hours (automated)

---

### Use Case Matrix

| Use Case | Primary Persona | Frequency | Business Impact |
|----------|----------------|-----------|-----------------|
| **Understand legacy code** | Marcus | Daily | High - Enables feature work |
| **Safe refactoring** | Marcus | Weekly | Critical - Prevents regressions |
| **Onboard new engineers** | Jennifer | Monthly | High - Reduces time to productivity |
| **Security audit** | DevSecOps | Quarterly | Critical - Required for compliance |
| **Migration planning** | Jennifer | Quarterly | High - De-risks major projects |
| **Spec verification** | Sarah | Weekly | Medium - Ensures quality |
| **Knowledge preservation** | Marcus | Continuous | High - Prevents knowledge loss |
| **Drift detection** | Jennifer | Monthly | Medium - Measures technical debt |

---

## 4. Functional Requirements

### FR2.1: Repository Loading & Discovery

**Description**: Load repositories from local filesystems, Git URLs, or archives, and discover all analyzable files.

**Requirements**:
- FR2.1.1: Support local filesystem paths
- FR2.1.2: Support Git repository URLs with branch/tag selection
- FR2.1.3: Support repository archives (.zip, .tar.gz)
- FR2.1.4: Auto-discover Python files (extensible to other languages)
- FR2.1.5: Intelligent exclusion of build artifacts, caches, dependencies
- FR2.1.6: Configurable custom exclusion patterns
- FR2.1.7: File size limits to prevent analysis of generated files
- FR2.1.8: Progress reporting during discovery

**Acceptance Criteria**:
- ✅ Can analyze repositories with 1000+ files
- ✅ Excludes common build directories (venv, node_modules, __pycache__)
- ✅ Reports discovery progress (N files found)
- ✅ Handles missing or inaccessible files gracefully

**Priority**: P0 (Core capability)

---

### FR2.2: Multi-File Analysis

**Description**: Analyze entire repositories in a single operation, with progress tracking and error handling.

**Requirements**:
- FR2.2.1: Analyze all discovered files in sequence
- FR2.2.2: Configurable file limit (e.g., first 100 files)
- FR2.2.3: Per-file timeout to prevent hangs
- FR2.2.4: Total analysis time limit
- FR2.2.5: Progress callbacks for UI integration
- FR2.2.6: Continue on errors (partial results)
- FR2.2.7: Detailed error reporting per file
- FR2.2.8: Summary statistics (success/failure counts, time elapsed)

**Acceptance Criteria**:
- ✅ Can analyze 100+ file repository in <10 minutes
- ✅ Progress updates every file (current/total)
- ✅ Returns partial results even if some files fail
- ✅ Clear error messages for failed files
- ✅ Respects time limits and file limits

**Priority**: P0 (Essential for real repos)

---

### FR2.3: AST Extraction & Signature Recovery

**Description**: Extract abstract syntax trees and recover function/class signatures with types.

**Requirements**:
- FR2.3.1: Parse Python AST for all files
- FR2.3.2: Extract function signatures (name, parameters, return type)
- FR2.3.3: Extract class definitions and methods
- FR2.3.4: Infer types from type hints when available
- FR2.3.5: Handle missing type hints gracefully (holes)
- FR2.3.6: Extract docstrings for intent hints
- FR2.3.7: Build call graphs (who calls what)
- FR2.3.8: Build import dependency graphs

**Acceptance Criteria**:
- ✅ 90%+ signature accuracy (correct name, params, types)
- ✅ Call graphs show all function calls
- ✅ Dependency graphs show all imports
- ✅ Handles type hints, PEP 484, typing module

**Priority**: P0 (Foundation)

---

### FR2.4: Static Analysis (CodeQL Integration)

**Description**: Integrate CodeQL for security vulnerability detection and code property analysis.

**Requirements**:
- FR2.4.1: Run CodeQL queries on repository
- FR2.4.2: Support standard query suites (security/default)
- FR2.4.3: Support custom query suites
- FR2.4.4: Extract findings with locations and severity
- FR2.4.5: Map findings to IR evidence
- FR2.4.6: Configurable enable/disable
- FR2.4.7: Handle CodeQL installation/availability

**Acceptance Criteria**:
- ✅ Detects common vulnerabilities (SQL injection, XSS, etc.)
- ✅ Findings include file, line number, severity
- ✅ Gracefully handles CodeQL not installed (skip analysis)
- ✅ Results integrated into IR metadata

**Priority**: P0 (Differentiator)

---

### FR2.5: Dynamic Analysis (Daikon Integration)

**Description**: Capture execution traces and infer runtime invariants using Daikon.

**Requirements**:
- FR2.5.1: Instrument code for trace collection
- FR2.5.2: Execute code with specified entrypoint
- FR2.5.3: Collect variable values at key program points
- FR2.5.4: Run Daikon to infer likely invariants
- FR2.5.5: Extract invariants as predicates
- FR2.5.6: Map invariants to IR assertions
- FR2.5.7: Configurable enable/disable
- FR2.5.8: Handle execution failures gracefully

**Acceptance Criteria**:
- ✅ Infers common invariants (x > 0, len(list) >= 0)
- ✅ Invariants become IR assertions
- ✅ Handles code that doesn't execute (skips)
- ✅ Configurable entrypoint function

**Priority**: P1 (Nice to have, not essential for MVP)

---

### FR2.6: IntentSpec Generation (AI-Assisted)

**Description**: Generate human-readable intent specifications from code, docstrings, and patterns.

**Requirements**:
- FR2.6.1: Extract intent from docstrings
- FR2.6.2: Infer intent from function/variable names
- FR2.6.3: Analyze code patterns (if checks, loops, etc.)
- FR2.6.4: Use AI to summarize "what this does" in plain language
- FR2.6.5: Extract roles (sender, recipient, system)
- FR2.6.6: Extract goals (transfer money, validate input)
- FR2.6.7: Extract constraints (amount > 0, user exists)
- FR2.6.8: Confidence scoring for intent atoms

**Acceptance Criteria**:
- ✅ 85%+ intent fidelity (human eval: "does this match what code does?")
- ✅ Intent in plain language, not jargon
- ✅ Confidence scores for each intent atom
- ✅ Handles code with no docstrings (infers from code)

**Priority**: P0 (Depends on DSPy Phase 2, Month 7-9)

**Status**: ⏳ Awaiting AI enhancement

---

### FR2.7: FuncSpec Generation (Constraint Inference)

**Description**: Infer formal specifications (pre/post conditions, invariants) from code structure.

**Requirements**:
- FR2.7.1: Extract preconditions from assertions and checks
- FR2.7.2: Infer postconditions from return statements
- FR2.7.3: Discover invariants from loops and conditionals
- FR2.7.4: Extract effects (DB writes, API calls, file I/O)
- FR2.7.5: Infer refinement types from checks (e.g., `if x >= 0` → `{x: int | x >= 0}`)
- FR2.7.6: Build resource usage predicates (memory, CPU, I/O)
- FR2.7.7: Extract error handling constraints
- FR2.7.8: Generate holes for unknown constraints

**Acceptance Criteria**:
- ✅ 70%+ constraint recall (what % of actual constraints discovered)
- ✅ 80%+ constraint precision (what % of discovered constraints are real)
- ✅ Pre/post conditions for 60%+ of functions
- ✅ Holes for ambiguous constraints

**Priority**: P0 (Core value)

---

### FR2.8: Alignment Map Creation

**Description**: Map IntentSpec atoms to FuncSpec predicates, showing correspondence and drift.

**Requirements**:
- FR2.8.1: Create IntentSpec ↔ FuncSpec correspondence
- FR2.8.2: Confidence scores for each mapping
- FR2.8.3: Detect unmapped intent atoms (missing implementation)
- FR2.8.4: Detect unmapped predicates (undocumented behavior)
- FR2.8.5: Drift detection (intent diverges from implementation)
- FR2.8.6: Visualization in UI
- FR2.8.7: Export alignment reports

**Acceptance Criteria**:
- ✅ 90%+ drift detection accuracy
- ✅ Alignment maps show clear correspondence
- ✅ Confidence scores help prioritize review
- ✅ Reports identify documentation gaps

**Priority**: P1 (Month 15-18)

**Status**: ⏳ Planned for IR 0.9 Phase 5

---

### FR2.9: Dependency Graph Construction

**Description**: Build comprehensive dependency graphs showing imports, calls, data flows.

**Requirements**:
- FR2.9.1: Import dependency graph (module-level)
- FR2.9.2: Call graph (function-level)
- FR2.9.3: Data flow graph (variable-level)
- FR2.9.4: Cross-file relationship tracking
- FR2.9.5: Circular dependency detection
- FR2.9.6: Unused code detection
- FR2.9.7: API surface extraction

**Acceptance Criteria**:
- ✅ Graphs cover 95%+ of relationships
- ✅ Circular dependencies flagged
- ✅ Unused code identified
- ✅ Exportable as GraphML or JSON

**Priority**: P1 (Enables advanced features)

---

### FR2.10: IR Export & Storage

**Description**: Export specifications in IR 0.9 format, store persistently.

**Requirements**:
- FR2.10.1: Export each file's IR as JSON
- FR2.10.2: Export entire repository as IR collection
- FR2.10.3: Store in Supabase for persistence
- FR2.10.4: Version control for IR changes
- FR2.10.5: Import IR for refinement
- FR2.10.6: Export to Spec-IR surface syntax (human-friendly)
- FR2.10.7: Include all evidence and provenance

**Acceptance Criteria**:
- ✅ IR validates against schema
- ✅ Round-trip: Code → IR → Storage → IR (no loss)
- ✅ Provenance chains intact
- ✅ Evidence preserved

**Priority**: P0 (Essential)

---

### FR2.11: Safe Refactoring via IR Transformations

**Description**: Enable verified refactoring through formal IR transformations.

**Requirements**:
- FR2.11.1: Extract function transformation
- FR2.11.2: Inline function transformation
- FR2.11.3: Rename transformation
- FR2.11.4: Type refinement transformation
- FR2.11.5: Solver verification of equivalence
- FR2.11.6: Before/after preview
- FR2.11.7: Rollback capability

**Acceptance Criteria**:
- ✅ Zero behavioral regressions (solver-verified)
- ✅ Transformations preserve semantics
- ✅ Preview shows exact changes
- ✅ Can undo any transformation

**Priority**: P1 (Future, depends on IR 0.9 evaluator)

**Status**: ⏳ Planned for Months 7-10 (Hole Closures phase)

---

### FR2.12: Multi-Language Support

**Description**: Extend reverse mode beyond Python to other languages.

**Requirements**:
- FR2.12.1: Python (complete)
- FR2.12.2: TypeScript/JavaScript
- FR2.12.3: Go
- FR2.12.4: Rust
- FR2.12.5: Java
- FR2.12.6: Language-agnostic IR
- FR2.12.7: Language-specific analyzer plugins

**Acceptance Criteria**:
- ✅ Same quality metrics across languages
- ✅ Unified IR format
- ✅ Language-specific idiom handling

**Priority**: P1 (Q1 2026)

**Status**: ⏳ Planned

---

### FR2.13: Progress Tracking & Real-Time Updates

**Description**: Provide real-time progress updates for long-running analyses.

**Requirements**:
- FR2.13.1: WebSocket progress events
- FR2.13.2: File-level progress (N/M files analyzed)
- FR2.13.3: Stage-level progress (discovery, analysis, inference)
- FR2.13.4: Time estimates (elapsed, remaining)
- FR2.13.5: Error reporting during analysis
- FR2.13.6: Cancellation support

**Acceptance Criteria**:
- ✅ Progress updates at least every 5 seconds
- ✅ Accurate time estimates (±20%)
- ✅ Can cancel long-running analysis
- ✅ Errors reported immediately

**Priority**: P0 (UX requirement)

---

### FR2.14: Search & Filtering

**Description**: Search and filter reverse mode results.

**Requirements**:
- FR2.14.1: Search by file path
- FR2.14.2: Search by function name
- FR2.14.3: Filter by language
- FR2.14.4: Filter by presence of security findings
- FR2.14.5: Filter by number of holes (incomplete specs)
- FR2.14.6: Sort by file path, function name, complexity

**Acceptance Criteria**:
- ✅ Search returns results in <1s for 1000+ files
- ✅ Filters combine (AND logic)
- ✅ Results update in real-time as filters change

**Priority**: P0 (Usability)

---

### FR2.15: Provenance & Audit Trail

**Description**: Track all decisions and sources in reverse mode analysis.

**Requirements**:
- FR2.15.1: Record which analyzer produced which finding
- FR2.15.2: Link IR elements to source code locations
- FR2.15.3: Track AI decisions (if AI-assisted intent extraction)
- FR2.15.4: Link intent atoms to evidence
- FR2.15.5: Export audit reports
- FR2.15.6: Provenance chains (where did each spec come from?)

**Acceptance Criteria**:
- ✅ Every IR element has provenance
- ✅ Can trace any spec back to source
- ✅ Audit reports meet compliance requirements

**Priority**: P0 (Compliance)

---

## 5. Non-Functional Requirements

### NFR2.1: Scale

**Requirement**: Handle large repositories efficiently.

**Targets**:
- 1000+ files per repository
- 100,000+ lines of code
- 10MB max file size (configurable)
- 100+ files analyzable in <10 minutes

**Rationale**: Real-world enterprise codebases are large

**Validation**: Benchmark against 10 open-source repos (varying sizes)

---

### NFR2.2: Accuracy (Intent Fidelity)

**Requirement**: Extracted intent must match actual code behavior.

**Target**: 85%+ intent fidelity

**Definition**: Human evaluators rate "does IntentSpec accurately describe what code does?" on 1-10 scale. Average ≥8.5.

**Measurement**:
1. Select 100 random functions from analyzed repos
2. Show evaluators: code + generated IntentSpec
3. Ask: "Does this intent match what code does?"
4. Calculate: (sum of ratings) / (number of evaluations)

**Rationale**: Intent must be trustworthy for users to rely on it

---

### NFR2.3: Accuracy (Signature Recovery)

**Requirement**: Extracted signatures must match actual function signatures.

**Target**: 90%+ signature accuracy

**Definition**: Correct function name, parameter names, parameter types, return type

**Measurement**: Automated comparison of extracted signature vs. actual signature

**Rationale**: Signatures are objective and machine-verifiable

---

### NFR2.4: Constraint Quality

**Requirement**: Inferred constraints must be real (precision) and complete (recall).

**Targets**:
- 70%+ constraint recall (what % of actual constraints discovered)
- 80%+ constraint precision (what % of discovered constraints are real)

**Definition**:
- Recall = (discovered real constraints) / (total real constraints)
- Precision = (discovered real constraints) / (total discovered constraints)

**Measurement**: Manual evaluation by engineers on sample functions

**Rationale**: Balance between finding constraints and avoiding false positives

---

### NFR2.5: Performance (Analysis Time)

**Requirement**: Analysis must complete in reasonable time.

**Targets**:
- Single file: <10 seconds
- 100-file repository: <10 minutes
- 1000-file repository: <60 minutes

**Rationale**: Users won't wait hours for analysis

**Optimization**: Parallel analysis, caching, incremental re-analysis

---

### NFR2.6: Performance (Latency)

**Requirement**: UI must stay responsive during analysis.

**Targets**:
- Progress updates: Every 5 seconds
- UI interactions: <100ms response time
- Search/filter: <1 second for 1000+ results

**Rationale**: Users need feedback to know analysis is progressing

---

### NFR2.7: Reliability (Partial Results)

**Requirement**: Analysis must return partial results even if some files fail.

**Target**: ≥80% files successfully analyzed in typical repos

**Behavior**:
- Continue on errors (don't stop entire analysis)
- Report which files failed and why
- Return results for successful files

**Rationale**: Real codebases have broken files; don't let one break analysis

---

### NFR2.8: Security

**Requirement**: Reverse mode must not expose sensitive data.

**Controls**:
- Code stays local (no upload to external services)
- Results stored with Row-Level Security (Supabase)
- Evidence sanitized (no hardcoded secrets exposed)
- Access control: Users can only see their analyses

**Rationale**: Enterprise customers have strict security requirements

---

### NFR2.9: Incremental Analysis

**Requirement**: Re-analyze only changed files.

**Behavior**:
- Detect which files changed since last analysis
- Re-analyze only those files
- Preserve previous results for unchanged files

**Target**: 10x speedup for incremental analysis vs. full analysis

**Priority**: P1 (Future optimization)

---

### NFR2.10: Resource Limits

**Requirement**: Protect against resource exhaustion.

**Controls**:
- Max file size: 10MB (configurable)
- Max files: 1000 (configurable)
- Per-file timeout: 30s (configurable)
- Total analysis timeout: 60min (configurable)

**Behavior**: Skip files exceeding limits, log warnings

**Rationale**: Prevent runaway analyses from consuming resources

---

## 6. Success Metrics

### Product Metrics

**Adoption**:
- 50% of active lift users use reverse mode monthly (by Month 18)
- 200+ repositories analyzed by Month 18
- 1000+ repositories analyzed by Month 24

**Engagement**:
- 20+ files analyzed per session (median)
- 60%+ of reverse mode sessions lead to code changes
- 40%+ of users use both forward and reverse mode

**Retention**:
- 70%+ of users who try reverse mode use it again within 30 days
- 80%+ of users who use reverse mode 3+ times continue using it

---

### Quality Metrics

**Intent Fidelity**:
- **Target**: 85%+ (human eval: "does intent match code?")
- **Measurement**: Quarterly user study, 100 random functions
- **Baseline**: N/A (new capability)

**Signature Accuracy**:
- **Target**: 90%+ (correct name, params, types)
- **Measurement**: Automated comparison vs. ground truth
- **Baseline**: N/A

**Constraint Quality**:
- **Recall Target**: 70%+ (% of real constraints found)
- **Precision Target**: 80%+ (% of found constraints are real)
- **Measurement**: Manual evaluation by engineers

**Security Finding Accuracy**:
- **Target**: 90%+ precision, 80%+ recall (vs. manual security review)
- **Measurement**: Compare to expert security audit

---

### Performance Metrics

**Analysis Speed**:
- **Single file**: <10s for 90% of files
- **100 files**: <10 minutes
- **1000 files**: <60 minutes

**Progress Responsiveness**:
- **Updates**: Every 5 seconds minimum
- **UI latency**: <100ms for interactions
- **Search latency**: <1s for 1000+ results

---

### User Satisfaction

**Net Promoter Score (NPS)**:
- **Target**: 40+ overall
- **Segment targets**:
  - Senior engineers: 45+
  - Engineering managers: 50+
  - Security teams: 45+

**Feature Satisfaction**:
- **Intent extraction**: 8/10+ on "helps me understand code"
- **Security analysis**: 9/10+ on "identifies real issues"
- **Safe refactoring**: 9/10+ on "gives me confidence"

**Time Savings**:
- **Code understanding**: 50% reduction vs. manual reading
- **Onboarding**: 50% reduction vs. asking teammates
- **Security audits**: 70% reduction vs. manual review

---

### Business Impact Metrics

**Time to Value**:
- 80%+ of users get value from first reverse mode session
- Median time to first insight: <5 minutes

**Developer Productivity**:
- 30% increase in feature velocity (self-reported)
- 50% reduction in "understanding time" (tracked)

**Quality Improvements**:
- 40% reduction in bugs introduced during refactoring
- 90% reduction in regressions (with IR transformations)

**Cost Savings**:
- $100K+ saved annually per team (onboarding + refactoring time)
- 80% reduction in security audit costs

---

## 7. Technical Approach

### Analysis Pipeline

```
┌─────────────────────────────────────────────────────────────┐
│                     REVERSE MODE PIPELINE                    │
└─────────────────────────────────────────────────────────────┘

1. DISCOVERY
   Repository → File Discovery → Python files (exclude build artifacts)
   ↓
2. STATIC ANALYSIS
   Files → AST Parser → Signatures, Types, Call Graphs
   Files → CodeQL → Security Findings, Vulnerabilities
   Files → Pattern Matcher → Code Patterns, Idioms
   ↓
3. DYNAMIC ANALYSIS (Optional)
   Files → Daikon → Execution Traces → Likely Invariants
   ↓
4. AI-ASSISTED INTENT EXTRACTION (Month 7-9)
   Code + Docstrings + Patterns → DSPy → IntentSpec
   ↓
5. FUNCSPEC GENERATION
   Assertions → Preconditions
   Returns → Postconditions
   Loops → Invariants
   I/O → Effects
   ↓
6. ALIGNMENT
   IntentSpec + FuncSpec → Alignment Map → Drift Detection
   ↓
7. IR ASSEMBLY
   All Analyses → Intermediate Representation (IR 0.9)
   ↓
8. STORAGE & EXPORT
   IR → Supabase (PostgreSQL) + JSON Export
```

---

### Static Analysis Stack

**AST Parsing**:
- Python: `ast` module (standard library)
- TypeScript: `@typescript-eslint/parser`
- Go: `go/ast` and `go/parser`
- Rust: `syn` crate
- Java: JavaParser

**Type Extraction**:
- Python: PEP 484 type hints, `typing` module
- TypeScript: TypeScript compiler API
- Go: `go/types` package
- Rust: `rustc` type inference
- Java: Reflection + JavaParser

**Call Graph Construction**:
- Python: `ast.NodeVisitor` for calls, imports
- Cross-language: Language Server Protocol (LSP) where available

**Security Analysis**:
- CodeQL (all languages)
- Language-specific linters (pylint, ESLint, clippy, etc.)

---

### Dynamic Analysis Stack

**Execution Tracing**:
- Python: `sys.settrace` + custom tracer
- Daikon integration for invariant discovery

**Invariant Discovery** (Daikon):
1. Instrument code to log variable values
2. Execute with test inputs
3. Run Daikon to infer likely invariants
4. Filter and rank invariants by confidence

**Limitations**:
- Requires executable code
- Quality depends on test coverage
- May miss edge cases not exercised

**Future**: Record & replay production traffic for better invariants

---

### AI-Assisted Intent Extraction (DSPy)

**Phase**: Months 7-9 (DSPy Migration Phase 2)

**Approach**:
```python
class ExtractIntentFromCode(dspy.Signature):
    """Extract human-readable intent from code."""

    code: str = dspy.InputField(desc="Source code")
    docstring: str = dspy.InputField(desc="Function docstring (may be empty)")
    call_graph: str = dspy.InputField(desc="Functions this code calls")

    intent_summary: str = dspy.OutputField(desc="What this code does (plain language)")
    roles: list[str] = dspy.OutputField(desc="Actors/entities involved")
    goals: list[str] = dspy.OutputField(desc="Objectives this code achieves")
    constraints: list[str] = dspy.OutputField(desc="Rules/requirements enforced")

class InferTypeFromUsage(dspy.Signature):
    """Infer type from how variable is used."""

    variable_name: str = dspy.InputField(...)
    usage_examples: list[str] = dspy.InputField(desc="How variable is used in code")

    inferred_type: str = dspy.OutputField(desc="Most likely type")
    confidence: float = dspy.OutputField(desc="Confidence 0-1")
```

**Training Data**:
- Curated repos with good documentation
- Functions with clear docstrings
- User corrections from interactive refinement
- Solver feedback (when inferred specs fail)

**Optimization**: MIPROv2, BootstrapFewShot

**Result**: High-quality intent extraction that improves over time

---

### Dependency Graph Construction

**Module-Level (Imports)**:
```python
# Extract imports from AST
import ast

class ImportVisitor(ast.NodeVisitor):
    def visit_Import(self, node):
        # Track: from X import Y
    def visit_ImportFrom(self, node):
        # Track: import X
```

**Function-Level (Calls)**:
```python
class CallVisitor(ast.NodeVisitor):
    def visit_Call(self, node):
        # Track: function_name(args)
```

**Data-Flow (Variables)**:
- Use reaching definitions analysis
- Track variable assignments and uses
- Identify def-use chains

**Output**: GraphML or JSON for visualization

---

### Alignment Map Creation

**Approach** (Month 15-18, IR 0.9 Phase 5):
1. Parse IntentSpec atoms (goals, constraints)
2. Parse FuncSpec predicates (requires, ensures)
3. Use AI to match atoms ↔ predicates
4. Assign confidence scores
5. Flag unmapped atoms (documentation gaps)
6. Flag unmapped predicates (undocumented behavior)

**Example**:
```
IntentSpec: "Transfer money from sender to recipient"
  ↕ (0.95 confidence)
FuncSpec: ensures sender.balance' = sender.balance - amount
          ensures recipient.balance' = recipient.balance + amount
```

**Drift Detection**:
- If confidence <0.6: Flag as potential drift
- If unmapped atoms/predicates: Flag as documentation gap

---

### Safe Refactoring via IR Transformations

**Phase**: Months 7-10 (Hole Closures)

**Example Transformation: Extract Function**

1. **User selects** code block to extract
2. **lift analyzes** dependencies (variables used, side effects)
3. **lift generates** new function signature
4. **SMT solver verifies** equivalence:
   ```
   forall inputs: old_code(inputs) == new_function(inputs)
   ```
5. **If verified**: Apply transformation
6. **If not**: Show counterexample, ask user to refine

**Transformations Planned**:
- Extract function
- Inline function
- Rename (with scope awareness)
- Type refinement (narrow types based on usage)
- Effect extraction (separate pure from impure)

**Result**: Zero behavioral regressions

---

### Multi-Language Support Strategy

**Tier 1** (Complete): Python
**Tier 2** (Q1 2026): TypeScript, Go
**Tier 3** (Q2 2026): Rust, Java

**Architecture**:
- Language-agnostic IR (same for all languages)
- Language-specific parsers (plugins)
- Shared analysis pipeline
- Language-specific idiom handling

**Challenges**:
- Type systems differ (Python vs. Rust)
- Effect systems differ (Go vs. Haskell)
- Idioms differ (Java beans vs. Rust traits)

**Solution**: IR 0.9 is flexible enough to represent all

---

## 8. User Experience

### Experience 1: Understand Legacy Service (Web UI)

**Scenario**: Marcus needs to fix a bug in a 5-year-old Python service.

**Step-by-Step**:

1. **Navigate to Repository View**
   - Open http://localhost:5173
   - Click "Repository" in sidebar

2. **Connect Repository**
   - Select local path: `/repos/legacy-service`
   - Or: Enter GitHub URL: `https://github.com/company/legacy-service`

3. **Choose Analysis Mode**
   - Click "Entire Project" (analyze all files)

4. **Start Analysis**
   - Click "Analyze"
   - See progress bar: "Analyzing src/api/auth.py (12/47)"
   - Wait ~3 minutes for 47 files

5. **View Results Overview**
   - See list of 47 analyzed files
   - Search: "auth" (filters to 8 files)
   - See summary: 8 files, 23 functions, 12 security findings

6. **Dive into Specific File**
   - Click "View Details" on `src/api/auth.py`
   - See IntentSpec: "Validates user authentication tokens using JWT"
   - See FuncSpec:
     ```
     requires: token is not None
     requires: token matches JWT format
     ensures: returns True if valid, False otherwise
     effects: Reads from Redis cache
     ```
   - See Security Findings: "Potential timing attack in token comparison"
   - See Evidence: CodeQL finding at line 45

7. **Understand the Bug**
   - Marcus reads intent: "Should validate JWT tokens"
   - Reads spec: "Must not be None, must match format"
   - Sees security finding: "Timing attack"
   - **Insight**: Bug is string comparison isn't constant-time

8. **Fix with Confidence**
   - Marcus fixes timing attack
   - Runs reverse mode again to verify
   - Sees security finding resolved

**Outcome**: Bug fixed in 30 minutes instead of 2 days of code reading

---

### Experience 2: Safe Refactoring (CLI + SDK)

**Scenario**: Marcus needs to extract authentication logic into a separate service.

**Step-by-Step**:

1. **Analyze Current Code**
   ```bash
   uv run python -m lift_sys.cli reverse \
     --repo /repos/monolith \
     --analyze-all \
     --output monolith-specs.json
   ```
   Result: Specs for entire monolith saved

2. **Filter to Auth Functions**
   ```python
   import json
   specs = json.load(open("monolith-specs.json"))
   auth_specs = [s for s in specs if "auth" in s["metadata"]["source_path"]]
   print(f"Found {len(auth_specs)} auth-related files")
   ```

3. **Review Dependencies**
   ```python
   # Check what auth code depends on
   for spec in auth_specs:
       print(f"File: {spec['metadata']['source_path']}")
       print(f"Effects: {spec['effects']}")
       # Shows: "Reads from users table", "Writes to sessions table"
   ```

4. **Plan Extraction** (Future: IR Transformations)
   - Identify database dependencies
   - Identify API dependencies
   - Plan service boundaries

5. **Generate New Service** (Forward Mode)
   - Use extracted specs as input to forward mode
   - Generate new microservice code
   - Verify matches original behavior

6. **Deploy with Confidence**
   - Tests pass (behavior preserved)
   - Specs match (verified)
   - Zero regressions

**Outcome**: Safe extraction instead of risky manual migration

---

### Experience 3: Security Audit (API)

**Scenario**: DevSecOps team needs monthly security audit.

**Step-by-Step**:

1. **Run Analysis via API**
   ```bash
   curl -X POST http://localhost:8000/api/reverse \
     -H "Content-Type: application/json" \
     -d '{
       "module": null,
       "analyze_all": true,
       "queries": ["security/default", "security/injection"]
     }' > security-audit.json
   ```

2. **Parse Results**
   ```python
   import json
   results = json.load(open("security-audit.json"))

   # Extract security findings
   findings = []
   for ir in results["irs"]:
       for evidence in ir["metadata"]["evidence"]:
           if evidence["analysis"] == "codeql":
               findings.append({
                   "file": ir["metadata"]["source_path"],
                   "line": evidence["location"],
                   "severity": evidence["metadata"].get("severity", "unknown"),
                   "message": evidence["message"]
               })

   print(f"Found {len(findings)} security issues")
   ```

3. **Generate Report**
   ```python
   # Group by severity
   critical = [f for f in findings if f["severity"] == "critical"]
   high = [f for f in findings if f["severity"] == "high"]

   print(f"Critical: {len(critical)}")
   print(f"High: {len(high)}")

   # Export as CSV for leadership
   import csv
   with open("security-report.csv", "w") as f:
       writer = csv.DictWriter(f, fieldnames=["file", "line", "severity", "message"])
       writer.writeheader()
       writer.writerows(findings)
   ```

4. **Track Fixes**
   - Run reverse mode weekly
   - Compare findings to previous week
   - Measure: findings decreasing over time

**Outcome**: Automated security audits instead of 2-4 weeks of manual review

---

### Experience 4: Onboarding New Engineer (Web UI)

**Scenario**: Sarah (new engineer) joins team, needs to understand codebase.

**Step-by-Step**:

1. **Access Pre-Analyzed Repo**
   - Team lead already ran reverse mode
   - Sarah opens lift web UI
   - Sees repository already analyzed

2. **High-Level Overview**
   - Sees 200 files analyzed
   - Searches for "user" → 35 files
   - Searches for "payment" → 12 files
   - Gets mental map of codebase structure

3. **Dive into Feature Area**
   - Sarah assigned to work on payments
   - Clicks "View Details" on `src/payments/processor.py`
   - Reads IntentSpec: "Processes payment transactions with Stripe"
   - Reads FuncSpec:
     ```
     requires: amount > 0
     requires: payment_method is valid
     ensures: transaction recorded in database
     ensures: receipt sent to user
     effects: API call to Stripe
     effects: Database write to transactions table
     effects: Email sent via SendGrid
     ```

4. **Understand Dependencies**
   - Sees call graph: `process_payment` calls `validate_card`, `create_charge`, `send_receipt`
   - Sees import graph: depends on `stripe`, `database`, `email_service`
   - Understands: "To work on payments, I need to understand these 3 modules"

5. **Ask Smart Questions**
   - Instead of: "How do payments work?" (vague, time-consuming)
   - Sarah asks: "I see we call Stripe synchronously. Have we considered async for better perf?"
   - (Specific, informed question because she read the specs)

**Outcome**: Productive in 2 weeks instead of 2 months

---

## 9. Roadmap & Milestones

### Current Status (October 2025)

**Infrastructure**: ✅ **COMPLETE**
- Multi-file analysis (100+ files)
- AST extraction and dependency graphs
- CodeQL security integration
- Progress tracking and error handling
- File discovery with intelligent exclusions

**What Works Today**:
```python
from lift_sys.reverse_mode.lifter import SpecificationLifter, LifterConfig

config = LifterConfig(
    codeql_queries=["security/default"],
    run_codeql=True,
    run_daikon=False,
    max_files=100
)

lifter = SpecificationLifter(config)
lifter.load_repository("/path/to/repo")

# Analyze entire repository
irs = lifter.lift_all()
print(f"Analyzed {len(irs)} files")
```

**What's Missing**:
- ❌ AI-powered intent extraction (DSPy Phase 2)
- ❌ Type inference improvements
- ❌ Entity resolution across files
- ❌ Alignment maps (IntentSpec ↔ FuncSpec)
- ❌ Safe refactoring via IR transformations
- ❌ Multi-language support (only Python)

---

### Q2 2025: IR 0.9 Foundation + DSPy Setup

**Milestone**: IR with types, refinements, solvers

**Deliverables**:
- IR 0.9 Phase 1: Core types & refinements (Months 1-3)
- IR 0.9 Phase 2: Solver integration (Months 4-6)
- DSPy setup and training data collection (Month 4)

**Reverse Mode Impact**:
- Enhanced IR format with refinement types
- Solver validation of extracted constraints
- Foundation for AI-assisted intent extraction

**Go/No-Go**: Month 6
- If IR stable and solvers working → Proceed
- If too complex or slow → Simplify before continuing

---

### Q3 2025: AI-Assisted Intent Extraction

**Milestone**: DSPy-powered intent and type inference

**Deliverables**:
- DSPy Migration Phase 2: Reverse mode (Months 7-9)
  - `ExtractIntentFromCode` signature
  - `InferTypeFromUsage` signature
  - `ClassifyIntent` signature
- Training on curated repos with good documentation
- A/B testing vs. rule-based baseline

**Functional Requirements Enabled**:
- ✅ FR2.6: IntentSpec Generation (AI-Assisted)
- ✅ FR2.7: Enhanced FuncSpec Generation

**Success Metrics**:
- Intent fidelity: 85%+ (vs. baseline 60%)
- Type inference accuracy: 90%+ (vs. baseline 70%)
- User preference: 80%+ prefer AI-assisted vs. heuristics

**Priority**: P0 (Key differentiator)

---

### Q4 2025: Interactive Refinement + Surface Syntax

**Milestone**: Hole closures, partial evaluation, Spec-IR

**Deliverables**:
- IR 0.9 Phase 3: Hole closures & partial evaluation (Months 7-10)
- IR 0.9 Phase 4: Surface syntax & parsing (Months 11-14)
- DSPy Phase 3: Hole suggestions (Months 10-12)

**Reverse Mode Impact**:
- Execute reverse-mode specs with holes (preview behavior)
- Human-friendly Spec-IR syntax for specs
- AI suggests missing constraints based on traces

**User Experience**:
- View extracted specs in Spec-IR (readable, not JSON)
- See holes for unknowns, get AI suggestions
- Refine interactively with partial evaluation

---

### Q1 2026: Alignment & Provenance

**Milestone**: IntentSpec ↔ FuncSpec alignment, full audit trails

**Deliverables**:
- IR 0.9 Phase 5: Alignment & provenance (Months 15-18)
- DSPy Phase 4: Entity resolution (Months 13-15)
- Intent ledger for tracking decisions

**Functional Requirements Enabled**:
- ✅ FR2.8: Alignment Map Creation
- ✅ FR2.15: Provenance & Audit Trail

**Reverse Mode Features**:
- Alignment maps show IntentSpec ↔ FuncSpec correspondence
- Drift detection identifies documentation gaps
- Full provenance: trace every spec to source
- Compliance reports auto-generated

**Success Metrics**:
- Drift detection: 90%+ accuracy
- Audit pass rate: 100%
- Time to generate compliance report: 40 hours → 2 hours

---

### Q2 2026: Multi-Language + Safe Refactoring

**Milestone**: TypeScript/Go support, verified transformations

**Deliverables**:
- Multi-language parsers (TypeScript, Go)
- Language-agnostic IR (unified format)
- Safe refactoring via IR transformations
- Continuous learning pipeline (DSPy Phase 5)

**Functional Requirements Enabled**:
- ✅ FR2.11: Safe Refactoring via IR Transformations
- ✅ FR2.12: Multi-Language Support (TypeScript, Go)

**Reverse Mode Features**:
- Analyze TypeScript/Go codebases
- Extract function transformation with solver verification
- Inline/rename with behavioral equivalence proofs
- Zero regressions guaranteed

**Success Metrics**:
- Multi-language quality: Same as Python (85%+ intent fidelity)
- Refactoring safety: 0 regressions with IR transformations
- User satisfaction: 9/10+ on "gives me confidence to refactor"

---

### Q3 2026: Production & Scale

**Milestone**: Beta launch, enterprise features

**Deliverables**:
- IR 0.9 Phase 6: Production readiness (Months 19-20)
- Safety manifests (SBOM, SLSA, OPA)
- Incremental analysis (only re-analyze changed files)
- Performance optimization (10x faster)

**Reverse Mode Features**:
- Incremental re-analysis (10x faster for unchanged code)
- Safety manifests for compliance
- OPA policy enforcement
- Telemetry integration

**Success Metrics**:
- Beta users: 200+
- Repositories analyzed: 1000+
- NPS: 40+
- Zero critical bugs

---

### Gantt Chart (Simplified)

```
Month   Q2 2025              Q3 2025              Q4 2025              Q1 2026       Q2 2026
──────────────────────────────────────────────────────────────────────────────────────────
1-3     IR Types ████████
4-6     IR Solvers ████████
7-9                         AI Intent ████████
10-12                                           Refinement ████████
13-15                                                               Alignment █████
16-18                                                                             ████
19-20                                                                                  ██

Reverse Mode Capabilities by Quarter:
Q2: ✅ Basic (static only)
Q3: ✅ AI-assisted intent
Q4: ✅ Interactive refinement
Q1: ✅ Alignment + provenance
Q2: ✅ Multi-language + refactoring
```

---

## 10. Risk Analysis & Mitigation

### Critical Risks

#### R1: AI Intent Quality Insufficient

**Risk**: AI-extracted intent doesn't match actual code behavior (intent fidelity <70%)

**Likelihood**: Medium
**Impact**: High (core value proposition)

**Mitigation**:
1. **Extensive training data**: Curate 1000+ high-quality examples
2. **Multiple optimizers**: Try Bootstrap, MIPRO, BayesOpt
3. **Human-in-the-loop**: Show intent, ask for corrections, retrain
4. **Confidence scoring**: Show low-confidence intent as holes
5. **Fallback**: Use rule-based heuristics if AI underperforms

**Go/No-Go**: Month 9 (after DSPy Phase 2)
- If intent fidelity <70%: Pause AI, use heuristics
- If 70-85%: Continue with caution, iterate
- If >85%: Full steam ahead

**Contingency**: Ship without AI-assisted intent, use simpler heuristics

---

#### R2: Analysis Too Slow for Large Repos

**Risk**: 1000-file repo takes >2 hours to analyze

**Likelihood**: Medium
**Impact**: High (usability)

**Mitigation**:
1. **Parallel analysis**: Analyze files concurrently
2. **Incremental analysis**: Only re-analyze changed files
3. **Caching**: Cache AST, type info, CodeQL results
4. **Sampling**: Analyze representative subset for quick overview
5. **Lazy analysis**: Analyze on-demand (only files user opens)

**Targets**:
- 100 files: <10 minutes
- 1000 files: <60 minutes

**Contingency**: Limit to 100-file repos in beta, optimize before GA

---

#### R3: Constraint Inference Low Quality

**Risk**: Inferred constraints are wrong (precision <60%) or incomplete (recall <50%)

**Likelihood**: Medium
**Impact**: Medium (specs less useful)

**Mitigation**:
1. **Conservative inference**: Only extract high-confidence constraints
2. **Holes for unknowns**: Mark uncertain constraints as holes
3. **Solver validation**: Use SMT to check constraint consistency
4. **User feedback**: Learn from corrections
5. **Static + dynamic**: Combine AST analysis with execution traces

**Targets**:
- Precision: 80%+ (avoid false positives)
- Recall: 70%+ (find most constraints)

**Contingency**: Focus on high-confidence constraints, leave rest as holes

---

#### R4: Multi-Language Support Too Hard

**Risk**: TypeScript/Go support takes 2x longer than planned

**Likelihood**: Medium
**Impact**: Medium (delays roadmap)

**Mitigation**:
1. **Language-agnostic IR**: Design IR to work for all languages
2. **Shared pipeline**: Reuse analysis logic across languages
3. **Incremental rollout**: Python first, then TypeScript, then Go
4. **Community plugins**: Open architecture for language plugins

**Contingency**: Delay multi-language to Q3 2026, focus on Python excellence

---

#### R5: CodeQL Integration Issues

**Risk**: CodeQL difficult to install/use, users can't run security analysis

**Likelihood**: Low (CodeQL is mature)
**Impact**: Medium (security is differentiator)

**Mitigation**:
1. **Optional feature**: Make CodeQL optional, not required
2. **Fallback analyzers**: Use language-specific linters if CodeQL unavailable
3. **Cloud option**: Offer hosted CodeQL for users who can't install
4. **Documentation**: Clear setup instructions + troubleshooting

**Contingency**: Ship without CodeQL, add later when ready

---

### Medium Risks

#### R6: User Adoption Low

**Risk**: Users try reverse mode once, don't see value, don't return

**Mitigation**:
- Excellent onboarding (guided tour)
- Clear value demonstration (before/after metrics)
- Templates for common use cases
- Success stories and case studies

**Measurement**: 30-day retention rate

---

#### R7: Incremental Analysis Complexity

**Risk**: Incremental analysis harder than expected, takes 6 months instead of 2

**Mitigation**:
- Ship without incremental analysis first
- Add as optimization later
- Users can re-analyze full repo (slower but works)

**Priority**: P1 (nice to have, not essential)

---

#### R8: Provenance Storage Bloat

**Risk**: Full provenance chains make database too large

**Mitigation**:
- Compression for evidence
- Retention policies (keep recent, archive old)
- Tiered storage (hot/cold)

**Contingency**: Reduce provenance detail if needed

---

## Conclusion

**Reverse Mode is lift's differentiating capability for legacy code understanding and safe refactoring.**

### What Makes It Unique

1. **Multi-File Analysis**: Whole repositories, not just single files
2. **Static + Dynamic + Semantic**: Comprehensive analysis stack
3. **AI-Assisted Intent**: Understands "why" not just "what"
4. **Formal Specifications**: Machine-verifiable contracts
5. **Safe Refactoring**: Verified transformations with zero regressions
6. **Full Provenance**: Audit trails for compliance

### Market Opportunity

- **90% of development is maintenance** → Reverse mode addresses the majority use case
- **No competitive alternative** → Only tool combining static, dynamic, and semantic analysis
- **Enterprise need** → Compliance requires code understanding and documentation

### Current Status

- ✅ Infrastructure complete (multi-file, AST, CodeQL, progress tracking)
- ⏳ Awaiting AI enhancement (DSPy Phase 2, Months 7-9)
- 🎯 Production-ready Q2 2026

### Success Criteria

- **Quality**: 85%+ intent fidelity, 90%+ signature accuracy
- **Performance**: 1000 files in <60 minutes
- **Adoption**: 50% of users use reverse mode monthly
- **Impact**: 50% reduction in code understanding time

### Next Steps

1. **Month 7-9**: DSPy Phase 2 (AI-assisted intent extraction)
2. **Month 10-14**: Interactive refinement + Spec-IR syntax
3. **Month 15-18**: Alignment + provenance tracking
4. **Month 19-20**: Production readiness + beta launch

**Reverse Mode transforms legacy code from a liability into a documented, verifiable asset.**

---

**Document Status**: Active
**Last Updated**: 2025-10-21
**Next Review**: Monthly or with major milestone changes
**Maintained By**: Product & Engineering Leadership
**Version History**: v1.0 (2025-10-21) - Initial comprehensive PRD
