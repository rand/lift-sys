# lift-sys Master Plan

**Version**: 2.0
**Last Updated**: October 13, 2025
**Status**: Active Development

---

## Mission Statement

`lift-sys` democratizes high-quality software creation by making formal verification and AI-assisted development accessible to both engineers and semi-technical contributors. We achieve this through bidirectional transformation between natural language, formal specifications (IR), and verified code.

---

## Current State Summary

### ✅ Completed Capabilities

#### Forward Mode (Prompt → IR → Code)
- **Session Management**: Full lifecycle management for iterative IR refinement
- **Typed Holes**: Automatic ambiguity detection and tracking
- **AI-Assisted Resolution**: Context-aware suggestions for resolving ambiguities
- **SMT Verification**: Automatic logical consistency checking
- **Multiple Interfaces**: Web UI, CLI, TUI, Python SDK
- **Code Generation**: Python code generation from finalized IR with runtime assertions
  - **CRITICAL TECHNICAL REQUIREMENT**: IR → Code MUST use constrained generation
  - Uses CODE_GENERATION_SCHEMA with SGLang + XGrammar
  - Enables speculative parallel decoding for 3-10x faster inference
  - Guarantees schema-valid JSON output, eliminates parsing failures
  - Allows batched generation of multiple code variations in parallel
- **IR Versioning**: Full version history with rollback and comparison
- **Provenance Tracking**: Track origin of every IR element (human/agent/reverse/merge)
- **Proactive Analysis**: AgentAdvisor provides quality suggestions across 6 categories

#### Reverse Mode (Code → IR)
- **Whole-Project Analysis**: Analyze entire repositories (100+ files)
- **Single-File Mode**: Backward compatible targeted analysis
- **Static Analysis**: AST parsing, type extraction, signature recovery
- **Security Analysis**: CodeQL integration for vulnerability detection
- **Dynamic Analysis**: Daikon invariant extraction from traces
- **Progress Tracking**: Real-time WebSocket updates during analysis
- **Error Resilience**: Graceful handling of per-file failures

#### Infrastructure
- **OAuth System**: GitHub OAuth with encrypted token storage
- **Multi-Provider Support**: Anthropic, OpenAI, Google Gemini, SGLang (Modal)
- **Modal Deployment**: SGLang + XGrammar + Qwen3-Coder-30B-A3B-Instruct on GPU
  - Migrated from vLLM to SGLang for native Qwen3 MoE support
  - XGrammar backend for constrained generation (3-10x faster JSON decoding)
  - RadixAttention for efficient prefix caching
- **Repository Management**: GitHub integration with sync and branch support
- **Comprehensive Testing**: 100+ tests covering critical paths

### 🚧 In Progress

- **Forward-Reverse Integration**: Bridging the two modes for complete workflows
- **Improvement Detection**: Automated identification of refactoring opportunities
- **Test Generation**: Automatic test case generation from IR specifications

### 📋 Planned (Next 6 months)

1. **Complete Forward-Reverse Loop** (P0)
2. **Production Readiness** (P0)
3. **Advanced Analysis** (P1)
4. **Developer Experience** (P1)
5. **Enterprise Features** (P2)

---

## Strategic Priorities

### P0: Complete the Core Loop (Next 2-4 weeks)

**Goal**: Enable complete bidirectional workflows where users can extract, refine, and regenerate code.

#### Workflow 1: Extract → Refine → Regenerate
**User Story**: "I have legacy code. Extract its spec, refine it, generate improved code."

**Required Features:**
- [x] ~~Import reverse IR into forward sessions~~ (lift-sys-34) ✅
- [x] ~~IR comparison and diff visualization~~ (lift-sys-32, 33) ✅
- [x] ~~IR merge operations~~ (lift-sys-36) ✅
- [x] ~~Code generation API~~ (lift-sys-29) ✅
- [ ] Round-trip validation (generate → reverse → compare)
- [ ] Improvement suggestion workflow integration

**Open Issues:**
- lift-sys-40: Test case generator from IR
- lift-sys-41: Security suggestion engine
- lift-sys-42: Refactoring recommender

**Deliverable**: Demo video showing complete extract→refine→regenerate workflow

#### Workflow 2: Specify → Generate → Validate
**User Story**: "I write a natural language prompt, get code, verify it matches my intent."

**Status**: 90% complete

**Remaining Work:**
- [ ] Automatic validation that generated code satisfies IR assertions
- [ ] Better error messages when code generation fails
- [ ] Support for more target languages (currently Python only)

**Open Issues:**
- lift-sys-44: UX refinement based on user feedback

### P0: Production Readiness (Parallel, 2-3 weeks)

**Goal**: Make lift-sys reliable and performant enough for daily use.

#### Stability
- [ ] Error recovery in all critical paths
- [ ] Rate limiting and quota management
- [ ] Session persistence beyond in-memory storage
- [ ] Graceful degradation when external services fail

#### Performance
- [x] ~~Performance profiling for large repositories~~ (lift-sys-20) ✅
- [ ] Caching for reverse mode analysis
- [ ] Parallel analysis for multi-file mode
- [ ] Optimize IR comparison for large diffs

**Open Issues:**
- lift-sys-43: Performance profiling and optimization

#### Documentation
- [x] ~~API documentation for session management~~ ✅
- [x] ~~Workflow guides for common tasks~~ ✅
- [ ] Architecture documentation for contributors
- [ ] Deployment guide for self-hosting
- [ ] Troubleshooting guide

**Open Issues:**
- lift-sys-45: Comprehensive integration documentation
- lift-sys-46: Tutorial content and examples

### P1: Advanced Analysis (4-6 weeks)

**Goal**: Make the IR analysis more powerful and actionable.

#### Agent-Driven Improvement
- [x] ~~Proactive IR quality analysis~~ (lift-sys-39) ✅
- [ ] Security vulnerability detection with fix suggestions (lift-sys-41)
- [ ] Automated refactoring recommendations (lift-sys-42)
- [ ] Test coverage analysis and generation (lift-sys-40)

#### Verification Depth
- [ ] Symbolic execution for deeper invariant discovery
- [ ] Property-based testing from IR assertions
- [ ] Formal proof generation for critical properties
- [ ] Contract verification against test traces

#### Multi-Language Support
- [ ] TypeScript/JavaScript reverse mode
- [ ] Rust code generation from IR
- [ ] Cross-language IR (Python spec → TypeScript impl)

### P1: Developer Experience (4-6 weeks)

**Goal**: Make lift-sys delightful to use daily.

#### IDE Integration
- [ ] VS Code extension for inline IR refinement
- [ ] JetBrains plugin for IR inspection
- [ ] Language server protocol (LSP) support
- [ ] Inline suggestions and quick fixes

#### Collaboration Features
- [ ] Shared sessions for team IR refinement
- [ ] Comment threads on IR elements
- [ ] Review workflow for IR changes
- [ ] IR approval gates for CI/CD

#### Observability
- [ ] Analytics dashboard (usage, success rates, error patterns)
- [ ] IR evolution visualization over time
- [ ] Verification success metrics
- [ ] Performance monitoring and alerts

### P2: Enterprise Features (3-6 months)

**Goal**: Enable organizations to adopt lift-sys at scale.

#### Security & Compliance
- [ ] SSO integration (SAML, OIDC)
- [ ] Audit logging for all IR changes
- [ ] Role-based access control (RBAC)
- [ ] Data residency options
- [ ] SOC 2 compliance readiness

#### Scale
- [ ] Multi-tenant deployment architecture
- [ ] Organization-level settings and policies
- [ ] Bulk import/export for IR libraries
- [ ] Custom analysis rule definitions

#### Customization
- [ ] Pluggable verification backends
- [ ] Custom code generators
- [ ] Domain-specific IR templates
- [ ] Organization-specific best practices

---

## Success Metrics

### Phase 1 (Current - Next 6 weeks)
**Metric**: Can demonstrate complete bidirectional workflow in <5 minutes

**Targets:**
- Extract IR from 50+ file repository in <30s
- Refine IR through 5+ iterations in <2 minutes
- Generate code that passes round-trip validation >95% of time
- Zero critical bugs in production deployment
- Documentation covers 100% of core workflows

### Phase 2 (2-4 months)
**Metric**: 10+ active users using lift-sys weekly

**Targets:**
- Average session success rate >80% (finalized without giving up)
- <3 support questions per active user
- Agent suggestions accepted >60% of the time
- Verification finds real bugs in >30% of projects analyzed
- NPS score >40

### Phase 3 (4-6 months)
**Metric**: Positive ROI for professional developers

**Targets:**
- Reduce specification time by >40% vs manual documentation
- Catch >2 bugs per project through verification
- Code generation accuracy >85% (compiles + passes tests)
- Adoption in >3 organizations
- >50% of users recommend to colleagues

---

## Technical Architecture Roadmap

### Current Architecture

```
┌─────────────────────────────────────────────────────┐
│                    Frontend                         │
│  React + Vite + shadcn/ui + TanStack Query         │
│  • Prompt Workbench • Repository View              │
│  • IR Editor • Planner View • Config               │
└───────────────────┬─────────────────────────────────┘
                    │ HTTP/WebSocket
┌───────────────────▼─────────────────────────────────┐
│                  FastAPI Backend                     │
│  • Session Management • OAuth • Progress Streams    │
└───────┬──────────┬──────────┬──────────┬────────────┘
        │          │          │          │
   ┌────▼───┐ ┌───▼────┐ ┌───▼────┐ ┌──▼─────┐
   │Forward │ │Reverse │ │Planner │ │ Code   │
   │ Mode   │ │ Mode   │ │        │ │  Gen   │
   └────┬───┘ └───┬────┘ └───┬────┘ └──┬─────┘
        │         │          │         │
        └─────────┴──────────┴─────────┘
                    │
            ┌───────▼────────┐
            │   IR (Central) │
            │  • Versioning  │
            │  • Provenance  │
            │  • Validation  │
            └────────────────┘
```

### Target Architecture (6 months)

```
┌──────────────────────────────────────────────────────┐
│                IDE Extensions                        │
│  VS Code • JetBrains • LSP Server                   │
└───────────────────┬──────────────────────────────────┘
                    │
┌───────────────────▼──────────────────────────────────┐
│              Web Frontend + CLI                      │
└───────────────────┬──────────────────────────────────┘
                    │
┌───────────────────▼──────────────────────────────────┐
│               API Gateway                            │
│  • Auth • Rate Limiting • Routing • Metrics         │
└───────┬──────────────────────────────────────────────┘
        │
┌───────▼───────────────────────────────────────────┐
│          Core Services (Microservices)            │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐         │
│  │ Session  │ │ Analysis │ │ Code Gen │         │
│  │ Service  │ │ Service  │ │ Service  │         │
│  └──────────┘ └──────────┘ └──────────┘         │
└───────┬───────────────────────────────────────────┘
        │
┌───────▼───────────────────────────────────────────┐
│              Data Layer                           │
│  PostgreSQL • Redis • S3 • Event Stream          │
└────────────────────────────────────────────────────┘
```

### Key Architectural Changes

#### Short Term (1-2 months)
- [ ] Replace in-memory session storage with PostgreSQL
- [ ] Add Redis for caching reverse mode results
- [ ] Implement proper event sourcing for IR changes
- [ ] Add structured logging and tracing

#### Medium Term (3-4 months)
- [ ] Extract services into separate deployments
- [ ] Add API gateway with authentication and rate limiting
- [ ] Implement async job queue for long-running analysis
- [ ] Add horizontal scaling for analysis workers

#### Long Term (5-6 months)
- [ ] Multi-region deployment
- [ ] Event-driven architecture with message bus
- [ ] Pluggable verification backends
- [ ] GraphQL API alongside REST

---

## Risk Management

### Technical Risks

| Risk | Impact | Likelihood | Mitigation | Owner |
|------|--------|------------|------------|-------|
| Code generation quality insufficient for production use | High | Medium | Extensive testing, human review workflow, confidence scores | TBD |
| Verification false positives frustrate users | High | Medium | Tunable sensitivity, clear explanations, easy overrides | TBD |
| Performance degrades with large codebases | High | High | Caching, parallel processing, incremental analysis | TBD |
| LLM API costs become prohibitive | Medium | Medium | Local model fallback, caching, cost monitoring | TBD |
| Security vulnerabilities in OAuth or token storage | Critical | Low | Security audit, penetration testing, encrypted storage | TBD |

### Product Risks

| Risk | Impact | Likelihood | Mitigation | Owner |
|------|--------|------------|------------|-------|
| Users don't understand IR abstraction | High | High | Better onboarding, examples, visual explanations | TBD |
| Forward-reverse gap confuses mental model | Medium | Medium | Clear workflow guides, terminology consistency | TBD |
| Too many features, not enough focus | Medium | High | Ruthless prioritization, user feedback loops | TBD |
| Competition from GitHub Copilot, Cursor, etc. | High | Medium | Focus on verification and formal methods differentiation | TBD |

---

## Open Questions

### Technical
1. **Multi-language IR**: Should we have one IR format for all languages or language-specific IRs?
   - **Consideration**: Unified IR enables cross-language workflows but may lose language-specific nuances
   - **Timeline**: Decide by end of Q1 2026

2. **Verification backend**: SMT solver sufficient or need custom provers?
   - **Consideration**: Z3 works well for simple properties but may struggle with complex invariants
   - **Timeline**: Evaluate alternatives by Q2 2026

3. **Deployment model**: SaaS-only or also self-hosted?
   - **Consideration**: Self-hosted appeals to security-conscious enterprises but increases support burden
   - **Timeline**: Pilot self-hosted with 1-2 partners in Q2 2026

### Product
1. **Primary user persona**: Professional developers or semi-technical team members?
   - **Consideration**: Different personas need different UX and documentation
   - **Timeline**: User research in Q4 2025

2. **Pricing model**: Per-seat, usage-based, or freemium?
   - **Consideration**: Impacts go-to-market strategy and feature gating
   - **Timeline**: Decide before public beta (Q1 2026)

3. **Open source strategy**: Core open, premium closed? Fully open?
   - **Consideration**: Balance community growth with sustainability
   - **Timeline**: Finalize by Q1 2026

---

## Milestones

### Q4 2025 (Current Quarter)
- [x] **M1**: Whole-project reverse mode (COMPLETE)
- [x] **M2**: Code generation pipeline (COMPLETE)
- [x] **M3**: IR versioning and provenance (COMPLETE)
- [x] **M4**: Proactive IR analysis (COMPLETE)
- [ ] **M5**: Complete forward-reverse integration (IN PROGRESS)
- [ ] **M6**: Production deployment readiness

### Q1 2026
- [ ] **M7**: Private beta with 5-10 users
- [ ] **M8**: IDE extension (VS Code) MVP
- [ ] **M9**: Multi-language support (TypeScript)
- [ ] **M10**: Performance optimization for 1000+ file repos
- [ ] **M11**: Comprehensive documentation and tutorials

### Q2 2026
- [ ] **M12**: Public beta launch
- [ ] **M13**: Security audit and SOC 2 readiness
- [ ] **M14**: Enterprise features (SSO, RBAC, audit logs)
- [ ] **M15**: Collaboration features (shared sessions, comments)

### Q3 2026
- [ ] **M16**: General availability (GA) release
- [ ] **M17**: Marketplace for IR templates and generators
- [ ] **M18**: Advanced verification (symbolic execution)
- [ ] **M19**: Multi-region deployment

---

## How to Use This Plan

### For Contributors
1. Check **Open Issues** in each priority section
2. Run `bd ready` to see what's unblocked and ready to work on
3. Coordinate on high-priority items (P0) before starting P1/P2 work
4. Update this document when completing major milestones

### For Stakeholders
- **Weekly**: Check progress on current quarter milestones
- **Monthly**: Review success metrics and adjust priorities
- **Quarterly**: Assess strategic direction and validate assumptions

### For Users
- **Current**: Read [Workflow Guides](WORKFLOW_GUIDES.md) for how to use lift-sys today
- **Upcoming**: Check milestones to see when features you need will arrive
- **Feedback**: File issues or join discussions to influence roadmap

---

## Related Documents

- [Whole-Project Reverse Mode Plan](whole-project-reverse-mode-plan.md) - Detailed plan for reverse mode (COMPLETE)
- [Forward-Reverse Integration Plan](FORWARD_REVERSE_INTEGRATION_PLAN.md) - Bridging the two modes (IN PROGRESS)
- [Workflow Guides](WORKFLOW_GUIDES.md) - User-facing tutorials and examples
- [API Documentation](API_SESSION_MANAGEMENT.md) - Complete API reference
- [Architecture Decision Records](../design/adr/) - Key technical decisions

---

## Changelog

### v2.0 - October 13, 2025
- Marked whole-project reverse mode as COMPLETE
- Marked code generation pipeline as COMPLETE
- Marked IR versioning, provenance, and analysis as COMPLETE
- Updated priorities to focus on forward-reverse integration
- Added risk management section
- Added open questions for key decisions
- Updated milestones for Q4 2025 - Q3 2026

### v1.0 - Earlier 2025
- Initial plan focusing on reverse mode enhancement
- Session management system design
- Basic forward mode capabilities
