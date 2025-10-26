# Release Notes

## Version 0.3.0 - ICS Phase 1 & Backend Integration (2025-10-26)

**Major Feature Release:** Integrated Context Studio (ICS) Phase 1 complete with real backend NLP integration.

### 🎯 Highlights

- **ICS Phase 1 MVP**: Complete interactive specification editor with 22/22 E2E tests passing
- **Real Backend NLP**: spaCy + HuggingFace BERT integration for semantic analysis
- **Constraint Propagation**: Phase 2.1 visualization of constraint propagation between typed holes
- **Backend Integration Tests**: Comprehensive E2E test suite verifying real NLP pipeline
- **Production-Ready UI**: shadcn/ui-based interface with accessibility and responsive design

### 📊 By the Numbers

- **22 E2E tests passing** (Phase 1)
- **16 backend integration E2E tests** (real NLP pipeline)
- **Real NER**: spaCy + HuggingFace for PERSON, ORG, GPE entity detection
- **90.11 KB gzipped** bundle for ICS view
- **211 lines** of constraint propagation visualization

### ✨ New Features

#### ICS Phase 1: Core Editor
- **SemanticEditor**: ProseMirror-based editor with real-time semantic analysis
- **Entity Highlighting**: Visual highlights for entities, modals, constraints, holes
- **Tooltips**: Confidence scores and metadata on hover
- **Autocomplete**: Context-aware suggestions for technical terms
- **Typed Holes**: Visual widgets for unresolved specifications
- **Multi-panel Layout**: File explorer, symbols panel, inspector, chat

#### Backend NLP Pipeline
- **spaCy Integration**: Fast, accurate entity recognition (en_core_web_sm)
- **HuggingFace NER**: Advanced entity detection (dslim/bert-large-NER)
- **Modal Operator Detection**: Necessity, certainty, possibility, prohibition
- **Constraint Detection**: Temporal and conditional constraint extraction
- **Relationship Extraction**: Dependency parsing for causal/temporal relationships

#### Phase 2.1: Constraint Propagation
- **ConstraintPropagationView**: Visual representation of constraint flow
- **Solution Space Narrowing**: Before/after metrics with reduction percentage
- **Propagation History**: Timeline of all constraint propagations
- **Inspector Integration**: Filtered events by selected hole

### 🔧 Technical Improvements

**Frontend**:
- TypeScript strict mode throughout
- Zustand state management with Immer
- ProseMirror decorations for semantic highlights
- Playwright E2E testing with authentication
- Real-time analysis with 500ms debounce

**Backend**:
- FastAPI endpoints (/ics/analyze, /ics/health)
- CORS configuration for Vite dev server
- Lazy model loading for fast startup
- Type-compatible constraint structure
- Graceful fallback to mock when backend unavailable

**Testing**:
- Comprehensive E2E coverage (38 total tests)
- Backend integration verification
- Real vs mock analysis testing
- Performance benchmarks (<5s analysis time)

### 📝 Documentation

- [ICS Phase 2 Implementation Plan](docs/ics/ICS_PHASE2_NEXT_PLAN.md)
- [ICS Interface Specification](docs/ics/ICS_INTERFACE_SPECIFICATION.md)
- [Planning Documents](docs/planning/)
- [Backend Integration Summary](/tmp/backend_integration_summary.txt)

### 🚀 What's Next

**Phase 2.2**: Solution Space Narrowing visualization
**Phase 2.3**: AI Chat Assistant with /refine and /analyze commands
**Phase 2.4**: Enhanced backend (relationships, effects, assertions)

---

## Version 0.2.0 - Iterative Prompt-to-IR Refinement (2025-10-11)

**Major Feature Release:** Complete session management system for iterative specification refinement across all interfaces.

### 🎯 Highlights

- **Iterative Refinement**: Start with natural language, resolve ambiguities step-by-step
- **AI-Assisted Resolution**: Get smart suggestions for every ambiguity
- **Multi-Interface Parity**: Same workflow in Web UI, CLI, TUI, and Python SDK
- **SMT Verification**: Automatic validation ensures logical consistency
- **Complete Documentation**: Comprehensive guides, API docs, examples, and FAQs

### 📊 By the Numbers

- **275 total tests** (218 backend + 26 frontend + 31 CLI/TUI)
- **4 interfaces** (Web, CLI, TUI, SDK)
- **7 CLI commands** for complete session lifecycle
- **600+ lines** of API documentation
- **5 documentation guides** (Workflows, Best Practices, FAQ, API, IR Design)

---

## ✨ New Features

### Session Management API

Complete REST API for managing iterative refinement sessions:

```bash
POST   /spec-sessions          # Create session from prompt or IR
GET    /spec-sessions          # List all sessions
GET    /spec-sessions/{id}     # Get session details
POST   /spec-sessions/{id}/holes/{hole_id}/resolve  # Resolve ambiguity
GET    /spec-sessions/{id}/assists     # Get AI suggestions
POST   /spec-sessions/{id}/finalize    # Finalize and export IR
DELETE /spec-sessions/{id}     # Delete session
```

**Authentication**: OAuth-based with demo user header support for development.

**Key capabilities:**
- Stateful refinement with revision tracking
- TypedHole identification and classification
- Real-time validation status updates
- SMT-backed constraint verification
- Metadata tagging for organization

### Web UI: Prompt Workbench

New interactive UI for prompt refinement:

**Location**: http://localhost:5173 → "Prompt Workbench"

**Features:**
- Split-pane interface (sessions list + IR preview)
- Real-time ambiguity display with colored badges
- Inline hole resolution with input fields
- AI assist integration with suggestion chips
- WebSocket streaming for progress updates
- Session list with filtering and selection
- Visual validation status indicators

**Workflow:**
1. Enter natural language prompt
2. System generates IR with typed holes
3. Review ambiguities and AI suggestions
4. Resolve holes one at a time
5. Watch IR evolve in real-time
6. Finalize when all ambiguities resolved

### Enhanced IR View

Upgraded IR viewer with dual-mode support:

**New capabilities:**
- Source toggle: Plan (reverse mode) vs Session (prompt)
- Session selector dropdown
- Inline hole resolution UI
- Keyboard shortcuts (Enter to resolve)
- Visual hole highlighting
- Badge counts per section

**Backward compatible** with existing plan-based workflow.

### CLI Commands

Complete command-line interface for session management:

```bash
uv run python -m lift_sys.cli session <command>
```

**Commands:**
- `create` - Create session from prompt or IR file
- `list` - List all sessions
- `get` - Get session details (with --show-ir flag)
- `resolve` - Resolve a typed hole
- `assists` - Get AI suggestions
- `finalize` - Finalize session and export IR
- `delete` - Delete session

**Features:**
- JSON output mode for automation (`--json`)
- Rich formatted output for humans
- Custom API URL support (`--api-url`)
- Resolution type specification (`--type`)
- Output file support (`--output`)

**Examples:**
```bash
# Create and finalize a session
uv run python -m lift_sys.cli session create \
  --prompt "A function that validates email" --json

uv run python -m lift_sys.cli session resolve \
  <session-id> hole_function_name "validate_email"

uv run python -m lift_sys.cli session finalize \
  <session-id> --output finalized_ir.json
```

### TUI Integration

Textual user interface with session management:

**New tab**: "Prompt Refinement"

**Features:**
- Prompt input field with Ctrl+Enter submit
- Sessions list with live updates
- Active session details pane
- Ambiguity display
- Ctrl+L to refresh sessions

**Note**: Hole resolution currently via CLI/API; TUI displays state.

### Python Client SDK

Complete SDK for programmatic access:

**Location**: `lift_sys/client/session_client.py` (652 lines)

**Features:**
- Sync and async methods
- Type-safe dataclasses
- Full CRUD operations
- Automatic serialization/deserialization
- Custom headers and timeout support

**Example:**
```python
from lift_sys.client import SessionClient

client = SessionClient("http://localhost:8000")

# Create session
session = client.create_session(
    prompt="A function that sorts lists",
    metadata={"project": "utils"}
)

# Get assists
assists = client.get_assists(session.session_id)

# Resolve holes
for assist in assists.assists:
    if assist.suggestions:
        session = client.resolve_hole(
            session_id=session.session_id,
            hole_id=assist.hole_id,
            resolution_text=assist.suggestions[0]
        )

# Finalize
if not session.ambiguities:
    result = client.finalize_session(session.session_id)
    print(result.ir)
```

**Async support:**
```python
# All methods have async equivalents
session = await client.acreate_session(prompt="...")
```

---

## 📚 Documentation

### New Documentation

1. **[Workflow Guides](docs/WORKFLOW_GUIDES.md)** (~1500 lines)
   - Step-by-step tutorials for all interfaces
   - Complete examples with expected output
   - Common patterns and troubleshooting
   - CI/CD integration examples

2. **[Best Practices](docs/BEST_PRACTICES.md)** (~600 lines)
   - Effective prompt writing
   - Hole resolution strategies
   - Session management patterns
   - Team workflows

3. **[FAQ](docs/FAQ.md)** (~600 lines)
   - 30+ common questions answered
   - Troubleshooting guide
   - Advanced usage patterns

4. **[API Documentation](docs/API_SESSION_MANAGEMENT.md)** (~600 lines)
   - Complete endpoint reference
   - Request/response examples
   - Authentication guide
   - WebSocket events

5. **[Working Example](examples/session_workflow.py)** (~180 lines)
   - Complete end-to-end workflow
   - Error handling
   - Pretty-printed output

### Updated Documentation

- **README.md**: Added Quick Start section with examples for all interfaces
- **development_records/DEVELOPMENT_PLAN.md**: Updated status (Phase 3 complete)

---

## 🧪 Testing

### New Tests

**CLI Tests** (15 tests):
- Session creation (prompt and IR file)
- Session listing and retrieval
- Hole resolution with different types
- Assist suggestions
- Session finalization and deletion
- Rich vs JSON output modes
- Custom API URLs
- Error handling

**TUI Tests** (16 tests):
- SessionState creation and mutation
- Session client initialization
- Method existence verification
- Async session operations
- Widget integration
- Error handling

**Test Coverage:**
- All 275 tests passing
- Unit, integration, and API coverage
- Mocked dependencies for fast execution

---

## 🔧 Technical Changes

### Dependencies Added

- `typer>=0.9.0` - CLI framework
- `rich>=13.7` - Rich terminal output (already present)

### API Changes

**New endpoints:**
- `POST /spec-sessions` - Create session
- `GET /spec-sessions` - List sessions
- `GET /spec-sessions/{id}` - Get session
- `POST /spec-sessions/{id}/holes/{hole_id}/resolve` - Resolve hole
- `GET /spec-sessions/{id}/assists` - Get assists
- `POST /spec-sessions/{id}/finalize` - Finalize session
- `DELETE /spec-sessions/{id}` - Delete session

**New models:**
- `PromptSession` - Session state and metadata
- `IRDraft` - Versioned IR with validation status
- `TypedHole` - Ambiguity representation
- `AssistSuggestion` - AI suggestions

### Backend Changes

**New modules:**
- `lift_sys/services/spec_sessions/` - Session management service
- `lift_sys/client/` - Python SDK package
- `lift_sys/cli/` - CLI commands package

**Updated modules:**
- `lift_sys/main.py` - TUI session integration
- `lift_sys/ir/models.py` - TypedHole serialization fixes
- `lift_sys/ir/parser.py` - Hole parsing improvements

### Frontend Changes

**New components:**
- `frontend/src/views/PromptWorkbenchView.tsx` - Main refinement UI
- `frontend/src/views/EnhancedIrView.tsx` - Dual-mode IR viewer
- `frontend/src/lib/sessionApi.ts` - API client
- `frontend/src/types/sessions.ts` - Type definitions

---

## 🚀 Migration Guide

### For Existing Users

**No breaking changes!** All existing functionality remains unchanged.

**New capabilities are additive:**
- Existing reverse/forward mode workflows unchanged
- Existing API endpoints unchanged
- Existing TUI and frontend work as before

**To start using session management:**

1. **Web UI**: Navigate to "Prompt Workbench" tab
2. **CLI**: Run `uv run python -m lift_sys.cli session --help`
3. **SDK**: Import from `lift_sys.client`

### Configuration

**OAuth setup** (unchanged):
```bash
export LIFT_SYS_ENABLE_DEMO_USER_HEADER=1  # Dev mode
# OR configure proper OAuth for production
```

**API server** (unchanged):
```bash
./start.sh  # Starts both backend and frontend
```

---

## 🔜 What's Next

### Planned for v0.3.0

- **Real-time collaboration**: Multiple users editing same session
- **Hole templates**: Reusable patterns for common ambiguities
- **Batch operations**: Resolve multiple holes at once
- **Session history**: Rollback to previous drafts
- **Import/export**: Session portability

### Roadmap

- **v0.4.0**: Advanced SMT features and custom solvers
- **v0.5.0**: Multi-language support beyond Python
- **v1.0.0**: Production-ready release with stability guarantees

---

## 🙏 Acknowledgments

This release represents a significant milestone in making high-quality software creation accessible while keeping engineers in control.

Special thanks to the community for feedback and testing during development.

---

## 📖 Learn More

- **Quick Start**: See [README.md](README.md)
- **Tutorials**: Read [WORKFLOW_GUIDES.md](docs/WORKFLOW_GUIDES.md)
- **Best Practices**: Check [BEST_PRACTICES.md](docs/BEST_PRACTICES.md)
- **FAQ**: Review [FAQ.md](docs/FAQ.md)
- **API Reference**: See [API_SESSION_MANAGEMENT.md](docs/API_SESSION_MANAGEMENT.md)

---

## 🐛 Known Issues

### Minor Issues

1. **TUI hole resolution**: Currently requires CLI/API; inline resolution coming in v0.3.0
2. **WebSocket reconnection**: Manual page refresh needed if connection drops
3. **Large IR display**: Performance degrades with >100 holes (optimization planned)

### Workarounds

See [FAQ.md](docs/FAQ.md) for detailed troubleshooting.

---

## 📝 Changelog

### Added
- Complete session management API with 7 endpoints
- Web UI Prompt Workbench for interactive refinement
- Enhanced IR View with dual-mode support
- CLI commands for full session lifecycle
- TUI Prompt Refinement tab
- Python SDK with sync/async support
- Comprehensive documentation (5 guides, 3000+ lines)
- 31 new tests (15 CLI + 16 TUI)
- Working example script

### Changed
- IR serialization improved (TypedHole to_dict)
- Hole parsing enhanced (single hole and list cases)
- Frontend App.tsx updated with new routes
- README.md expanded with Quick Start examples

### Fixed
- TypedHole serialization using explicit to_dict()
- Hole parsing edge cases in IR parser
- Client package exports (IRDraft, AssistSuggestion)

---

## 🔗 Links

- **Repository**: https://github.com/rand/lift-sys
- **Issues**: https://github.com/rand/lift-sys/issues
- **Discussions**: https://github.com/rand/lift-sys/discussions
- **Documentation**: See `docs/` directory

---

**Full Diff**: v0.1.0...v0.2.0
**Release Date**: October 11, 2025
**Contributors**: lift-sys team + community

---

For questions or issues, please [open a GitHub issue](https://github.com/rand/lift-sys/issues).
