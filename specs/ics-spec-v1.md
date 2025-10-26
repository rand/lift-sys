# ICS (Integrated Context Studio) - Refined Specification v1

**Version**: 1.0
**Date**: 2025-10-25
**Status**: Phase 1 Complete
**Source**: Based on `docs/ICS_INTERFACE_SPECIFICATION.md` (1,548 lines) with critical refinements

---

## Document Purpose

This specification refines the original ICS interface specification by:
1. **Adding explicit OODA loop mapping** (user requirement)
2. **Documenting comprehensive state handling** (empty, error, loading states)
3. **Clarifying MVP scope** vs future phases
4. **Planning backend completion** (4 TODOs)
5. **Planning frontend fixes** (decoration application, 10 failing tests)
6. **Defining integration validation** strategy

**Key Changes from Original**:
- ✨ NEW: OODA Loop Framework (Section 2)
- ✨ NEW: Component State Machines (Section 3)
- ✨ NEW: MVP Scope Definition (Section 4)
- ✨ NEW: Backend Test & TODO Plan (Section 5)
- ✨ NEW: Frontend Fix Plan (Section 6)
- ✨ NEW: Integration Validation (Section 7)

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [OODA Loop Framework](#2-ooda-loop-framework) ✨ NEW
3. [Component State Machines](#3-component-state-machines) ✨ NEW
4. [MVP Scope Definition](#4-mvp-scope-definition) ✨ NEW
5. [Backend Implementation Plan](#5-backend-implementation-plan) ✨ NEW
6. [Frontend Fix Plan](#6-frontend-fix-plan) ✨ NEW
7. [Integration Validation](#7-integration-validation) ✨ NEW
8. [Acceptance Criteria](#8-acceptance-criteria)
9. [Reference: Original Spec](#9-reference-original-spec)

---

## 1. Executive Summary

### What is ICS?

**Integrated Context Studio** is a semantic-aware specification editor that enables developers to write natural language requirements with:
- Real-time NLP analysis (entities, modals, constraints, holes, ambiguities)
- Typed hole tracking with dependency graphs
- Constraint propagation visualization
- AI-assisted refinement

### Core Value Proposition

**Problem**: Writing specifications is tedious, error-prone, and lacks real-time feedback.

**Solution**: ICS provides OODA-optimized feedback loops (< 2s) for:
- **Observe**: See semantic elements highlighted as you type
- **Orient**: Understand relationships, holes, constraints via inspector
- **Decide**: AI suggestions guide next steps
- **Act**: Edit, resolve holes, propagate constraints

### Technology Stack

**Frontend**:
- React 18 + TypeScript (strict mode)
- ProseMirror (rich text editing + decorations)
- Zustand (state management + persist)
- shadcn/ui (UI components)
- react-resizable-panels (layout)

**Backend** (optional, with graceful degradation):
- FastAPI (Python API)
- spaCy (NLP: tokenization, POS, NER, dependencies)
- HuggingFace Transformers (advanced NER: dslim/bert-large-NER)
- Pattern matching (modal operators, typed holes, ambiguities)

**Deployment**:
- Frontend: Vercel/Cloudflare
- Backend: Modal.com (serverless GPU for NLP models)

### Current Status

**Implemented** (Phase 1 & 2 per original spec):
- ✅ 10 React components (3,063 lines)
- ✅ Backend NLP pipeline (344 lines, functional)
- ✅ ProseMirror editor with decorations plugin
- ✅ Zustand store with persist middleware
- ✅ Mock semantic analysis (fallback)
- ✅ Playwright E2E tests (22 total)

**Issues**:
- ❌ 10/22 tests failing (semantic analysis decorations not applying)
- ⚠️ Backend has 4 TODOs (relationships, effects, assertions, contradictions)
- ⚠️ Frontend has 4 TODOs (constraint validation, solution space calc)
- ⚠️ OODA loops not explicitly documented
- ⚠️ State handling incomplete

---

## 2. OODA Loop Framework ✨

**User Requirement**: "All OODA loops are well represented"

### What is OODA?

**OODA** = Observe → Orient → Decide → Act (decision-making framework by John Boyd)

**Applied to ICS**: Every user workflow should have tight OODA cycles (target < 2 seconds) for rapid iteration on specifications.

### Primary OODA Loops

#### Loop 1: Real-Time Semantic Analysis

**Goal**: User writes specification and gets immediate semantic feedback

**Flow**:
```
USER ACTION: Types in editor
  ↓
OBSERVE (< 16ms):
  • Character count updates in toolbar
  • Text visible in editor with syntax

  ↓ (500ms debounce)

OBSERVE (< 1s):
  • "Analyzing..." status shown
  • Semantic elements highlighted (entities: blue, modals: green, constraints: amber, holes: red)
  • Symbols panel updates with detected elements

  ↓
ORIENT (< 500ms):
  • User scans highlighted text
  • Reads symbol counts (12 entities, 5 holes, 3 constraints)
  • Identifies missing or incorrect highlights

  ↓
DECIDE (< 1s):
  • Should I clarify this ambiguity?
  • Should I resolve this hole?
  • Should I rephrase to add constraint?

  ↓
ACT (< 500ms):
  • Edit text
  • Click hole to inspect
  • Hover element for tooltip

  ↓ LOOP REPEATS
```

**Performance Budget**:
- Keystroke → Visual update: < 16ms (60 FPS)
- Typing → Analysis start: 500ms (debounce)
- Analysis → Results: < 1s (backend) or < 200ms (mock)
- **Total OODA cycle**: < 2s from typing to actionable feedback

**States**:
- **Idle**: User not typing, no analysis pending
- **Typing**: User actively typing, debounce timer running
- **Analyzing**: Backend/mock processing text
- **Complete**: Results rendered, user can act

**Error Handling**:
- Backend timeout (> 5s): Fall back to mock analysis
- Backend error: Show warning, use mock, don't block user
- Invalid analysis response: Log error, use cached/mock

---

#### Loop 2: Hole Inspection & Resolution

**Goal**: User discovers hole, understands it, decides how to resolve

**Flow**:
```
USER ACTION: Clicks hole "H1: AuthMethod" in SymbolsPanel
  ↓
OBSERVE (< 100ms):
  • HoleInspector opens with full details
  • See: Type hint, description, status
  • See: Dependencies (blocks, blocked by)
  • See: Applied constraints
  • See: Solution space (before/after narrowing)
  • See: AI suggestions with rationale

  ↓
ORIENT (< 5s):
  • User reads: "This hole blocks H3, H5"
  • User reads: "Constraints: Must support Google OAuth, must handle token refresh"
  • User reads: "Solution space: 2 options (Google OAuth, GitHub OAuth)"
  • User reads: "AI suggests: Use Passport.js (92% confidence)"

  ↓
DECIDE (< 3s):
  • Accept AI suggestion?
  • Manually specify solution?
  • Add more constraints first?
  • Defer to later?

  ↓
ACT (< 1s):
  • Click "Apply" on AI suggestion → Resolves hole
  • Type manual refinement → Custom solution
  • Click "Add Constraint" → More specificity
  • Close inspector → Defer

  ↓
OBSERVE (< 500ms):
  • Hole status changes: unresolved → resolved
  • Dependent holes update (H3, H5 get new constraints)
  • Symbols panel refreshes
  • Constraint propagation visualized

  ↓ LOOP REPEATS or USER EXITS
```

**Performance Budget**:
- Hole selection → Inspector open: < 100ms
- Inspector render: < 200ms
- Resolve hole → Update propagation: < 500ms
- **Total OODA cycle**: < 10s from curiosity to resolution

**States**:
- **No Selection**: Inspector shows placeholder
- **Hole Selected**: Inspector shows full details
- **Loading Dependencies**: Calculating dependency graph
- **Resolving**: User action in progress
- **Resolved**: Success feedback, propagation shown

**Error Handling**:
- Missing hole data: Show "Incomplete data, refresh analysis"
- Circular dependency: Show warning, disallow resolution
- Invalid refinement: Validate before accepting

---

#### Loop 3: Autocomplete & Reference Linking

**Goal**: User types # or @ and quickly finds file/symbol

**Flow**:
```
USER ACTION: Types "#" in editor
  ↓
OBSERVE (< 50ms):
  • Autocomplete popup appears below cursor
  • Shows file tree or symbols based on trigger

USER ACTION: Types "doc"
  ↓
OBSERVE (< 100ms):
  • Results filter in real-time
  • Shows: "📄 docs/planning/HOLES.md", "📄 docs/supabase/SCHEMA.md"
  • Highlights matching text

  ↓
ORIENT (< 1s):
  • User scans list
  • Identifies target file

  ↓
DECIDE (< 500ms):
  • Is this the right file?

  ↓
ACT (< 200ms):
  • Press ↓ to select → Enter to insert
  • Or click with mouse

  ↓
OBSERVE (< 50ms):
  • Popup dismisses
  • Text inserted: "#docs/planning/HOLES.md"
  • FileReference created in semantic analysis

  ↓ LOOP REPEATS or USER CONTINUES TYPING
```

**Performance Budget**:
- Trigger (#/@) → Popup open: < 50ms
- Typing → Results filter: < 100ms
- Selection → Insert: < 50ms
- **Total OODA cycle**: < 1s from trigger to reference created

**States**:
- **Hidden**: No trigger detected
- **Open (Empty)**: Trigger detected, loading results
- **Open (Results)**: Results shown, user navigating
- **Inserting**: Selected, inserting text

**Error Handling**:
- No results: Show "No files/symbols match query"
- Invalid selection: Validate before insert
- Network error (if fetching remote symbols): Show cached results

---

#### Loop 4: Error Recovery

**Goal**: User encounters error and quickly recovers

**Flow**:
```
SYSTEM ERROR: Backend analysis fails (timeout, 500 error)
  ↓
OBSERVE (< 100ms):
  • Toast notification: "⚠️ Backend unavailable, using pattern matching"
  • Status: "Analysis by pattern matching (limited accuracy)"
  • Highlights still appear (mock analysis)

  ↓
ORIENT (< 2s):
  • User reads warning
  • Understands analysis is degraded but functional

  ↓
DECIDE (< 1s):
  • Continue with mock analysis?
  • Restart backend?
  • Report issue?

  ↓
ACT (< 1s):
  • Dismiss toast → Continue
  • Click "Try Again" → Retry backend
  • Click "Report" → Open issue form

  ↓
OBSERVE (< 500ms):
  • If retry: Backend health check → Analysis resumes
  • If continue: Mock analysis continues
  • If report: Issue form opens

  ↓ LOOP EXITS or CONTINUES
```

**Performance Budget**:
- Error → User notification: < 100ms
- Fallback activation: < 200ms
- Retry → Backend response: < 2s
- **Total OODA cycle**: < 5s from error to recovery

**States**:
- **Healthy**: Backend responsive
- **Degraded**: Using mock analysis
- **Retrying**: Backend health check in progress
- **Failed**: Error shown, user must intervene

**Error Handling**:
- Never block user workflow
- Always provide fallback (mock analysis)
- Always allow retry
- Always log errors for debugging

---

### OODA Loop Performance Summary

| Loop | Cycle Time | Target | Critical Path |
|------|-----------|--------|---------------|
| **Semantic Analysis** | < 2s | < 1.5s | Debounce (500ms) + Analysis (< 1s) + Render (< 500ms) |
| **Hole Inspection** | < 10s | < 8s | Selection (< 100ms) + Orient (< 5s) + Decide (< 3s) + Act (< 1s) + Propagate (< 500ms) |
| **Autocomplete** | < 1s | < 500ms | Trigger (< 50ms) + Filter (< 100ms) + Select (< 200ms) + Insert (< 50ms) |
| **Error Recovery** | < 5s | < 3s | Detect (< 100ms) + Notify (< 100ms) + Fallback (< 200ms) + Resume (< 2s) |

**Design Principle**: Every action should have **immediate visual feedback** (< 100ms) and **actionable results** (< 2s).

---

## 3. Component State Machines ✨

**User Requirement**: "All empty and error states are well handled"

### State Machine Pattern

Every component follows this state machine pattern:

```
States: [Idle, Loading, Success, Error, Empty]
Transitions: trigger → state change → side effects → new state
Error Handling: Always allow retry, never block UI
```

### 3.1 SemanticEditor

**Purpose**: Core ProseMirror editor with real-time semantic highlighting

**States**:
```
┌─────────┐
│  IDLE   │ ← Initial state, no analysis pending
└────┬────┘
     │ (user types)
     ↓
┌─────────┐
│ TYPING  │ ← Debounce timer running (500ms)
└────┬────┘
     │ (timer completes)
     ↓
┌──────────┐
│ANALYZING │ ← Backend API call or mock analysis in progress
└────┬─────┘
     │ (success)
     ↓
┌─────────┐
│ SUCCESS │ ← Semantic highlights applied, user sees results
└────┬────┘
     │ (error during analysis)
     ↓
┌─────────┐
│  ERROR  │ ← Fallback to mock, show warning
└────┬────┘
     │ (retry or continue)
     └─────→ ANALYZING or SUCCESS

┌─────────┐
│  EMPTY  │ ← No text in editor, show placeholder
└─────────┘
```

**State Transitions**:
| From | To | Trigger | Side Effects |
|------|-----|---------|--------------|
| IDLE | TYPING | User types character | Start debounce timer |
| TYPING | TYPING | User types again | Reset debounce timer |
| TYPING | ANALYZING | Debounce completes | Extract text, call API/mock |
| TYPING | IDLE | User stops typing > 5s | Cancel debounce |
| ANALYZING | SUCCESS | Analysis complete | Apply decorations, update store |
| ANALYZING | ERROR | API timeout/error | Show toast, fallback to mock |
| ERROR | ANALYZING | User clicks "Retry" | Re-attempt backend API |
| SUCCESS | TYPING | User types | Start new analysis cycle |
| * | EMPTY | User deletes all text | Clear decorations, show placeholder |

**UI Elements by State**:
| State | Editor | Toolbar Status | Decorations | Actions |
|-------|--------|----------------|-------------|---------|
| IDLE | Editable | "Ready" | Last analysis | None |
| TYPING | Editable | "Ready" | Last analysis | None |
| ANALYZING | Editable | "Analyzing..." + spinner | Last analysis (stale) | None |
| SUCCESS | Editable | "Analysis complete (87% confidence)" | Fresh decorations | View symbols, inspect holes |
| ERROR | Editable | "⚠️ Limited analysis" | Mock decorations | [Retry] button |
| EMPTY | Editable | "Type to begin..." | None | Paste, examples |

**Error States**:
- **Backend Timeout**: Show toast, use mock, don't block
- **Invalid Response**: Log error, use cached/mock
- **Network Error**: Show offline indicator, use mock
- **Parse Error**: Show "Could not parse text" inline

**Empty State**:
```
╔════════════════════════════════════════╗
║                                        ║
║   📝 Start writing your specification  ║
║                                        ║
║   Type naturally - the system will    ║
║   detect entities, constraints, and   ║
║   typed holes as you write.           ║
║                                        ║
║   Try:                                 ║
║   • "The system must authenticate..."  ║
║   • "???AuthMethod (OAuth provider)"   ║
║                                        ║
║   Press Ctrl+V to paste existing spec ║
║                                        ║
╚════════════════════════════════════════╝
```

---

### 3.2 SymbolsPanel

**Purpose**: List view of detected semantic elements (entities, holes, constraints)

**States**:
```
┌─────────┐
│  EMPTY  │ ← No semantic elements detected
└────┬────┘
     │ (analysis finds elements)
     ↓
┌─────────┐
│POPULATED│ ← Elements shown, user can click
└────┬────┘
     │ (all elements removed)
     └────→ EMPTY

┌─────────┐
│ LOADING │ ← Analysis in progress, show skeleton
└─────────┘
```

**State Transitions**:
| From | To | Trigger | Side Effects |
|------|-----|---------|--------------|
| EMPTY | LOADING | Analysis starts | Show skeleton loaders |
| LOADING | POPULATED | Analysis complete with elements | Render list |
| LOADING | EMPTY | Analysis complete, no elements | Show empty state |
| POPULATED | LOADING | New analysis starts | Show stale data + spinner |
| POPULATED | POPULATED | Elements change | Re-render list |

**UI Elements by State**:
| State | Content | Actions | Message |
|-------|---------|---------|---------|
| EMPTY | Placeholder | None | "No elements detected. Start writing to see entities, holes, and constraints appear here." |
| LOADING | Skeleton loaders (3-5 items) | None | "Analyzing..." |
| POPULATED | Tabbed lists (Entities, Holes, Constraints) | Click → Jump to position, Double-click hole → Inspect | Count badges (e.g., "Entities (12)") |

**Empty State**:
```
┌────────────────────────┐
│ Entities (0)           │
├────────────────────────┤
│                        │
│  No entities detected  │
│                        │
│  Entities are named    │
│  references in your    │
│  specification like:   │
│  • People (Alice, Bob) │
│  • Systems (API, DB)   │
│  • Functions (auth())  │
│                        │
└────────────────────────┘
```

---

### 3.3 HoleInspector

**Purpose**: Detailed view of selected typed hole

**States**:
```
┌─────────┐
│  EMPTY  │ ← No hole selected
└────┬────┘
     │ (user selects hole)
     ↓
┌─────────┐
│ LOADING │ ← Fetching dependencies, constraints
└────┬────┘
     │ (data loaded)
     ↓
┌─────────┐
│POPULATED│ ← Full hole details shown
└────┬────┘
     │ (user deselects or selects different hole)
     └────→ EMPTY or LOADING

┌──────────┐
│ RESOLVING│ ← User resolving hole, propagating constraints
└──────────┘
```

**State Transitions**:
| From | To | Trigger | Side Effects |
|------|-----|---------|--------------|
| EMPTY | LOADING | User selects hole | Fetch dependencies, constraints |
| LOADING | POPULATED | Data loaded | Render full inspector |
| POPULATED | RESOLVING | User clicks "Resolve" | Show resolution form |
| RESOLVING | POPULATED | User submits resolution | Update hole status, propagate constraints |
| POPULATED | EMPTY | User deselects hole | Clear inspector |

**UI Elements by State**:
| State | Content | Actions | Message |
|-------|---------|---------|---------|
| EMPTY | Placeholder | None | "Select a hole from the Symbols panel to view details" |
| LOADING | Skeleton loaders | None | "Loading hole details..." |
| POPULATED | Full details (type, deps, constraints, AI suggestions) | [Resolve], [Add Constraint], [View Provenance] | None |
| RESOLVING | Resolution form + preview | [Apply], [Cancel] | "Resolving will propagate constraints to dependent holes" |

**Empty State**:
```
┌────────────────────────────┐
│   Hole Inspector           │
├────────────────────────────┤
│                            │
│   🔍 No hole selected      │
│                            │
│   Click a hole in the      │
│   Symbols panel or in the  │
│   editor to view:          │
│   • Dependencies           │
│   • Constraints            │
│   • Solution space         │
│   • AI suggestions         │
│                            │
└────────────────────────────┘
```

---

### 3.4 AutocompletePopup

**Purpose**: Dropdown for file (#) and symbol (@) autocomplete

**States**:
```
┌─────────┐
│ HIDDEN  │ ← No trigger detected
└────┬────┘
     │ (user types # or @)
     ↓
┌─────────┐
│SEARCHING│ ← Fetching/filtering results
└────┬────┘
     │ (results found)
     ↓
┌─────────┐
│POPULATED│ ← Results shown, user navigating
└────┬────┘
     │ (no results)
     ↓
┌─────────┐
│  EMPTY  │ ← No matches found
└─────────┘
```

**State Transitions**:
| From | To | Trigger | Side Effects |
|------|-----|---------|--------------|
| HIDDEN | SEARCHING | User types # or @ | Fetch files/symbols |
| SEARCHING | POPULATED | Results found | Show popup |
| SEARCHING | EMPTY | No results | Show "No matches" |
| POPULATED | POPULATED | User types more | Filter results |
| POPULATED | HIDDEN | User selects item | Insert text, dismiss |
| * | HIDDEN | User presses Escape | Dismiss popup |

**UI Elements by State**:
| State | Content | Actions | Message |
|-------|---------|---------|---------|
| HIDDEN | None | None | N/A |
| SEARCHING | Spinner | None | "Searching..." |
| POPULATED | Filtered list (files or symbols) | ↓↑ to navigate, Enter to select, Click to select | None |
| EMPTY | Empty message | None | "No files/symbols match 'query'" |

**Empty State**:
```
┌─────────────────────────────┐
│ # Files                     │
├─────────────────────────────┤
│                             │
│  No files match "xyz"       │
│                             │
│  Try:                       │
│  • Different search term    │
│  • Check file exists        │
│                             │
└─────────────────────────────┘
```

---

### 3.5 FileExplorer

**Purpose**: Tree view of project files

**States**:
```
┌─────────┐
│ LOADING │ ← Fetching file tree
└────┬────┘
     │ (tree loaded)
     ↓
┌─────────┐
│POPULATED│ ← File tree shown
└────┬────┘
     │ (error fetching)
     ↓
┌─────────┐
│  ERROR  │ ← Could not load files
└─────────┘
```

**State Transitions**:
| From | To | Trigger | Side Effects |
|------|-----|---------|--------------|
| LOADING | POPULATED | Tree loaded | Render tree |
| LOADING | ERROR | Fetch failed | Show error message |
| ERROR | LOADING | User clicks "Retry" | Re-fetch tree |
| POPULATED | LOADING | User clicks "Refresh" | Re-fetch tree |

**UI Elements by State**:
| State | Content | Actions | Message |
|-------|---------|---------|---------|
| LOADING | Skeleton tree | None | "Loading files..." |
| POPULATED | Interactive file tree | Click file → Open, Click folder → Expand/collapse | None |
| ERROR | Error message | [Retry] button | "Could not load files. Check permissions or try again." |

**Error State**:
```
┌────────────────────────┐
│ Files                  │
├────────────────────────┤
│                        │
│  ⚠️ Could not load     │
│     file tree          │
│                        │
│  [Retry]               │
│                        │
└────────────────────────┘
```

---

### 3.6 AIChat

**Purpose**: AI assistant for specification help

**States**:
```
┌─────────┐
│  IDLE   │ ← No conversation started
└────┬────┘
     │ (user sends message)
     ↓
┌─────────┐
│ WAITING │ ← AI response in progress
└────┬────┘
     │ (response received)
     ↓
┌─────────┐
│  CHAT   │ ← Conversation active
└─────────┘
```

**State Transitions**:
| From | To | Trigger | Side Effects |
|------|-----|---------|--------------|
| IDLE | WAITING | User sends first message | Show "AI typing..." |
| WAITING | CHAT | Response received | Render message |
| CHAT | WAITING | User sends another message | Append to history, show typing |
| WAITING | ERROR | AI error | Show error message, allow retry |

**UI Elements by State**:
| State | Content | Actions | Message |
|-------|---------|---------|---------|
| IDLE | Welcome message | [Start conversation] or type | "Ask me about your specification..." |
| WAITING | Chat history + typing indicator | None | "AI is typing..." |
| CHAT | Chat history | Send new message, scroll, copy | None |
| ERROR | Error message | [Retry] button | "AI unavailable. Try again later." |

**Idle State**:
```
┌─────────────────────────────┐
│ AI Assistant                │
├─────────────────────────────┤
│                             │
│  👋 Hi! I can help you:     │
│                             │
│  • Refine specifications    │
│  • Resolve typed holes      │
│  • Analyze constraints      │
│  • Suggest improvements     │
│                             │
│  Try:                       │
│  "/refine H1"               │
│  "/analyze"                 │
│                             │
│  [Type your message...]     │
│                             │
└─────────────────────────────┘
```

---

### State Machine Summary

| Component | States | Empty Handled? | Error Handled? | Loading Handled? |
|-----------|--------|----------------|----------------|------------------|
| **SemanticEditor** | 5 (Idle, Typing, Analyzing, Success, Error) | ✅ Placeholder | ✅ Toast + fallback | ✅ Spinner |
| **SymbolsPanel** | 3 (Empty, Loading, Populated) | ✅ "No elements" | N/A | ✅ Skeleton |
| **HoleInspector** | 4 (Empty, Loading, Populated, Resolving) | ✅ "Select hole" | N/A | ✅ Skeleton |
| **AutocompletePopup** | 4 (Hidden, Searching, Populated, Empty) | ✅ "No matches" | N/A | ✅ Spinner |
| **FileExplorer** | 3 (Loading, Populated, Error) | N/A | ✅ Retry button | ✅ Skeleton |
| **AIChat** | 4 (Idle, Waiting, Chat, Error) | ✅ Welcome | ✅ Retry button | ✅ Typing indicator |

**Design Principle**: Never leave user guessing. Always show current state, always allow recovery.

---

## 4. MVP Scope Definition ✨

**Problem**: Original spec (1,548 lines) mixes Phase 1-2 MVP with Phase 3-5 future features.

**Solution**: Clear scope boundaries for iterative delivery.

### Phase 1: Core Editor & Analysis (MVP) ← **WE ARE HERE**

**Goal**: Get basic semantic editing working end-to-end

**Must Have** (Acceptance Criteria):
- ✅ User can type in ProseMirror editor
- ✅ Real-time semantic analysis (entities, modals, constraints, holes, ambiguities)
- ✅ Semantic highlights (colored decorations) appear in editor
- ✅ Symbols panel shows detected elements
- ✅ Hole inspector shows details when hole selected
- ✅ Autocomplete for file (#) and symbol (@) references
- ✅ Backend NLP API or mock fallback works
- ✅ All 22 Playwright tests pass
- ✅ Empty/error/loading states handled for all components

**Out of Scope (Defer to Phase 2+)**:
- ❌ Constraint propagation visualization (defer to Phase 2)
- ❌ AI chat assistant (defer to Phase 2)
- ❌ Dependency graph visualization (defer to Phase 3)
- ❌ Collaborative editing (defer to Phase 5)
- ❌ Version control integration (defer to Phase 4)

**Backend TODOs - Decision**:
- ✅ **Complete**: Entity extraction (done)
- ✅ **Complete**: Modal operator detection (done)
- ✅ **Complete**: Typed hole detection (done)
- ✅ **Complete**: Ambiguity detection (done)
- ⏸️ **Defer**: Relationship extraction (Phase 2)
- ⏸️ **Defer**: Effects detection (Phase 2)
- ⏸️ **Defer**: Assertions detection (Phase 2)
- ⏸️ **Defer**: Contradiction detection (Phase 3)

**Frontend TODOs - Decision**:
- ✅ **Complete**: Constraint type determination (Phase 1 - infer from text)
- ⏸️ **Defer**: Constraint validation (Phase 2 - requires solver)
- ⏸️ **Defer**: Conflict checking (Phase 2 - requires solver)
- ⏸️ **Defer**: Solution space recalculation (Phase 2 - requires constraint solver)

### Phase 2: Constraint Propagation & AI Chat

**Goal**: Add constraint flow visualization and AI assistant

**Includes**:
- Constraint propagation when resolving holes
- Solution space narrowing visualization
- AI chat with /refine, /analyze commands
- Relationship extraction (backend TODO)
- Effects detection (backend TODO)
- Assertions detection (backend TODO)

**Timeline**: After Phase 1 complete + 2 weeks

### Phase 3: Advanced Features

**Goal**: Dependency graphs, contradiction detection, search

**Includes**:
- Interactive dependency graph (D3.js)
- Contradiction detection (backend TODO)
- Semantic search across specs
- Conflict resolution UI

**Timeline**: After Phase 2 complete + 4 weeks

### Phase 4: Collaboration & Git

**Goal**: Multi-user editing, version control

**Includes**:
- Real-time collaborative editing (CRDT)
- Git integration
- Diff view
- Commit/push from ICS

**Timeline**: After Phase 3 complete + 6 weeks

### Phase 5: Enterprise Features

**Goal**: Team workflows, templates, analytics

**Includes**:
- Shared specifications
- Review workflows
- Commenting system
- Templates library
- Analytics dashboard

**Timeline**: After Phase 4 complete + 8 weeks

### MVP Success Metrics

**User Can**:
1. Write specification in natural language ✅
2. See semantic elements highlighted as they type ✅
3. Click element to see details (tooltip or inspector) ✅
4. Reference files and symbols with autocomplete ✅
5. View list of holes, constraints, entities ✅
6. System gracefully handles backend failures (mock fallback) ✅

**Technical**:
1. All 22 Playwright tests pass ✅
2. OODA cycles < 2s for primary loops ✅
3. No console errors in browser ✅
4. Decorations apply correctly to DOM ✅
5. State handling complete (empty, error, loading) ✅

---

## 5. Backend Implementation Plan ✨

**Current Status**: NLP pipeline exists (`lift_sys/nlp/pipeline.py`, 344 lines), functional but has 4 TODOs.

### 5.1 What Works

**Implemented**:
- ✅ spaCy integration (en_core_web_sm)
- ✅ HuggingFace NER (dslim/bert-large-NER, optional)
- ✅ Entity extraction (PERSON, ORG, TECHNICAL, etc.)
- ✅ Modal operator detection (must, should, may, cannot)
- ✅ Typed hole detection (??? syntax)
- ✅ Ambiguity detection (or, and/or, maybe, etc.)
- ✅ Constraint detection (temporal: when, if, before, after)
- ✅ FastAPI endpoints (/ics/analyze, /ics/health)
- ✅ Graceful error handling (health check, fallback)

### 5.2 TODOs & Decisions

**TODO 1: Relationship Extraction** (Line 232)
```python
def _extract_relationships(self, doc) -> list[dict[str, Any]]:
    """Extract relationships using dependency parsing."""
    relationships = []
    # TODO: Implement relationship extraction using spaCy dependencies
    return relationships
```

**Decision**: **Defer to Phase 2**

**Rationale**:
- Relationships add complexity but not critical for MVP
- MVP goal: Show semantic elements, not relationships between them
- Requires additional UI for relationship visualization
- spaCy dependency parsing works, but extraction logic non-trivial

**Phase 2 Plan**:
- Use spaCy dependency parsing (doc.ents, token.dep_)
- Identify subject-verb-object triples
- Link entities via relationships
- Add relationship view to SymbolsPanel

---

**TODO 2: Effects Detection** (Line 133)
```python
"effects": [],  # Future: effect detection
```

**Decision**: **Defer to Phase 2**

**Rationale**:
- Effects (side effects, I/O, state changes) require semantic understanding beyond NER
- MVP focuses on entities, modals, constraints - effects are advanced
- Requires heuristics or LLM (DSPy) for accurate detection
- Frontend UI for effects not designed yet

**Phase 2 Plan**:
- Use pattern matching for keywords: "write", "read", "modify", "delete", "create"
- Identify I/O operations: "save to", "load from", "fetch", "send"
- Use DSPy for semantic understanding of side effects
- Add effects tab to SymbolsPanel

---

**TODO 3: Assertions Detection** (Line 134)
```python
"assertions": [],  # Future: assertion detection
```

**Decision**: **Defer to Phase 2**

**Rationale**:
- Assertions (pre/postconditions, invariants) are advanced spec features
- Requires understanding of logical conditions, not just NER
- MVP focuses on simpler semantic elements first
- Frontend UI for assertions not designed

**Phase 2 Plan**:
- Use pattern matching: "precondition", "postcondition", "invariant", "assert"
- Identify conditional logic: "if...then", "when...must", "after...should"
- Use DSPy for extracting logical assertions
- Add assertions tab to SymbolsPanel

---

**TODO 4: Contradiction Detection** (Line 318)
```python
def _detect_contradictions(self, text: str) -> list[dict[str, Any]]:
    """Detect potential contradictions."""
    contradictions = []
    # TODO: Implement contradiction detection (requires semantic understanding)
    return contradictions
```

**Decision**: **Defer to Phase 3**

**Rationale**:
- Contradiction detection requires deep semantic understanding
- Needs to compare multiple statements for logical conflicts
- Likely requires LLM (DSPy) or advanced NLP (entailment models)
- Not critical for MVP - ambiguity detection covers some overlap
- Frontend UI for contradiction resolution not designed

**Phase 3 Plan**:
- Use DSPy signatures for contradiction detection
- Check for conflicting modal operators ("must X" vs "must not X")
- Check for conflicting constraints (temporal, type, value)
- Use textual entailment models (HuggingFace)
- Add contradiction resolution UI

---

### 5.3 Backend Test Plan

**Goal**: Verify backend works before blaming frontend

**Tests**:

1. **Startup Test**:
   ```bash
   uv run uvicorn lift_sys.api.server:app --reload
   # Expected: Server starts on port 8000, no errors
   ```

2. **Health Check Test**:
   ```bash
   curl http://localhost:8000/ics/health
   # Expected: {"status": "healthy", "models": "loaded"}
   ```

3. **Analyze Endpoint Test**:
   ```bash
   curl -X POST http://localhost:8000/ics/analyze \
     -H "Content-Type: application/json" \
     -d '{"text": "The system must authenticate users before processing requests.", "options": {}}'
   # Expected: JSON with entities, modalOperators, constraints, etc.
   ```

4. **Entity Detection Test**:
   ```bash
   # Verify response contains:
   # entities: [{type: "TECHNICAL", text: "system"}, {type: "TECHNICAL", text: "users"}]
   # modalOperators: [{modality: "necessity", text: "must"}]
   ```

5. **Error Handling Test**:
   ```bash
   curl -X POST http://localhost:8000/ics/analyze \
     -H "Content-Type: application/json" \
     -d '{"text": "", "options": {}}'
   # Expected: 400 error, {"detail": "Text cannot be empty"}
   ```

**Acceptance Criteria**:
- ✅ Backend starts without errors
- ✅ Health check returns healthy
- ✅ Analyze endpoint returns SemanticAnalysis with expected structure
- ✅ Entity detection works (finds TECHNICAL, PERSON, ORG)
- ✅ Modal detection works (finds must, should, may)
- ✅ Hole detection works (finds ??? syntax)
- ✅ Error handling works (400 for empty text, 500 for failures)

---

## 6. Frontend Fix Plan ✨

**Current Issues**: 10/22 Playwright tests failing - all semantic analysis tests.

**Root Cause Hypothesis**: Decorations not applying to DOM even though mock/backend returns data.

### 6.1 Issue Analysis

**Failing Tests** (from `/tmp/test_results_summary.md`):
1. ❌ Detect entities - `.entity` elements not found
2. ❌ Detect modal operators - `.modal` elements not found
3. ❌ Detect typed holes - `.hole` elements not found
4. ❌ Detect constraints - `.constraint` elements not found
5. ❌ Filter autocomplete results - `.autocomplete-popup` not appearing
6. ❌ Show tooltip on entity hover - entities not present
7. ❌ Show tooltip on modal operator hover - modals not present
8. ❌ Show tooltip on typed hole hover - holes not present
9. ❌ Hide tooltip when mouse moves away - timeout waiting for entities
10. ❌ Use backend or mock analysis gracefully - mock not providing highlights

**Evidence**:
- ✅ Basic editor works (typing, character count)
- ✅ Autocomplete triggers work (# and @)
- ✅ Autocomplete dismissal works
- ❌ Semantic highlights NOT appearing in DOM
- ❌ No `.entity`, `.modal`, `.hole`, `.constraint` CSS classes found

**Hypothesis**:
1. **Mock analysis IS generating data** (`mockSemanticAnalysis.ts` has pattern matching)
2. **Store IS receiving data** (Zustand setSemanticAnalysis called)
3. **Decorations plugin NOT recalculating** when store updates
4. **OR decorations created but NOT applied** to ProseMirror view

### 6.2 Diagnosis Plan

**Step 1: Verify Mock Analysis Generates Data**
```typescript
// frontend/src/lib/ics/mockSemanticAnalysis.ts
console.log('Mock analysis input:', text);
const analysis = generateMockAnalysis(text);
console.log('Mock analysis output:', analysis);
// Expected: entities, modalOperators, etc. with positions
```

**Step 2: Verify Store Receives Data**
```typescript
// frontend/src/lib/ics/store.ts
setSemanticAnalysis: (analysis) => {
  console.log('Store received analysis:', analysis);
  set({ semanticAnalysis: analysis });
}
```

**Step 3: Verify Decorations Plugin Reacts**
```typescript
// frontend/src/lib/ics/decorations.ts
export function createDecorationsPlugin(store: ICSStore) {
  return new Plugin({
    key: decorationsPluginKey,
    state: {
      init() { return DecorationSet.empty; },
      apply(tr, oldSet) {
        console.log('Decorations plugin apply called');
        const analysis = store.getState().semanticAnalysis;
        console.log('Current analysis:', analysis);
        // Expected: Create decorations from analysis
      }
    }
  });
}
```

**Step 4: Verify Decorations Applied to View**
```typescript
// frontend/src/components/ics/SemanticEditor.tsx
useEffect(() => {
  if (!editorView) return;
  console.log('Editor view state:', editorView.state);
  const decorations = decorationsPluginKey.getState(editorView.state);
  console.log('Decorations:', decorations);
}, [editorView, semanticAnalysis]);
```

### 6.3 Likely Root Cause

**Issue**: Decorations plugin doesn't re-run when Zustand store updates.

**Why**: ProseMirror plugins only recalculate on transactions, not external state changes.

**Solution**: Dispatch transaction when semantic analysis updates.

### 6.4 Fix Implementation

**File**: `frontend/src/components/ics/SemanticEditor.tsx`

**Current (Broken)**:
```typescript
useEffect(() => {
  // Semantic analysis updates, but ProseMirror doesn't know
  // Decorations plugin never recalculates
}, [semanticAnalysis]);
```

**Fix (Working)**:
```typescript
useEffect(() => {
  if (!editorView || !semanticAnalysis) return;

  // Dispatch transaction to trigger decorations plugin recalculation
  const tr = editorView.state.tr;
  tr.setMeta('semanticAnalysis', semanticAnalysis); // Pass analysis to plugin
  editorView.dispatch(tr);

}, [editorView, semanticAnalysis]);
```

**File**: `frontend/src/lib/ics/decorations.ts`

**Current (Broken)**:
```typescript
export function createDecorationsPlugin(store: ICSStore) {
  return new Plugin({
    state: {
      apply(tr, oldSet) {
        // Never gets analysis, returns old decorations
        return oldSet;
      }
    }
  });
}
```

**Fix (Working)**:
```typescript
export function createDecorationsPlugin() {
  return new Plugin({
    key: decorationsPluginKey,
    state: {
      init() { return DecorationSet.empty; },
      apply(tr, oldSet, oldState, newState) {
        // Check if transaction has semantic analysis metadata
        const analysis = tr.getMeta('semanticAnalysis');

        if (!analysis) {
          // No new analysis, check if document changed
          if (tr.docChanged) {
            // Map old decorations to new positions
            return oldSet.map(tr.mapping, tr.doc);
          }
          return oldSet;
        }

        // New analysis, create fresh decorations
        const decorations = [];

        // Entities
        analysis.entities?.forEach(entity => {
          decorations.push(createEntityDecoration(entity.from, entity.to, entity));
        });

        // Modal operators
        analysis.modalOperators?.forEach(modal => {
          decorations.push(createModalDecoration(modal.from, modal.to, modal));
        });

        // Constraints
        analysis.constraints?.forEach(constraint => {
          decorations.push(createConstraintDecoration(constraint.from, constraint.to, constraint));
        });

        // Ambiguities
        analysis.ambiguities?.forEach(ambiguity => {
          decorations.push(createAmbiguityDecoration(ambiguity.from, ambiguity.to, ambiguity));
        });

        // Typed holes (widget decorations)
        analysis.typedHoles?.forEach(hole => {
          decorations.push(createHoleWidget(hole.pos, hole));
        });

        return DecorationSet.create(tr.doc, decorations);
      }
    },
    props: {
      decorations(state) {
        return this.getState(state);
      }
    }
  });
}
```

### 6.5 Testing Fix

**Manual Test**:
1. Start frontend: `cd frontend && npm run dev`
2. Open ICS view
3. Type: "The system must authenticate users"
4. Wait 500ms
5. Inspect DOM:
   - Look for `<span class="entity">system</span>`
   - Look for `<span class="modal-operator modal-necessity">must</span>`
   - Look for `<span class="entity">users</span>`

**Automated Test**:
```bash
cd frontend && npx playwright test e2e/ics-semantic-editor.spec.ts
# Expected: All semantic tests pass
```

### 6.6 Additional Fixes

**Issue**: Autocomplete popup not appearing

**Likely Cause**: Autocomplete plugin not integrated with editor

**Fix**: Verify autocomplete plugin added to EditorState plugins array

**File**: `frontend/src/components/ics/SemanticEditor.tsx`
```typescript
const editorState = EditorState.create({
  schema: specSchema,
  plugins: [
    decorationsPlugin,
    autocompletePlugin, // ← Verify this exists
    keymap({
      // ... keyboard shortcuts
    })
  ]
});
```

---

**Issue**: Tooltips not showing

**Likely Cause**: No semantic elements to hover (fixed by decoration fix above)

**Secondary Issue**: Tooltip logic might need timing adjustment

**File**: `frontend/src/components/ics/SemanticTooltip.tsx`
```typescript
const handleMouseEnter = (e: MouseEvent) => {
  // Ensure 300ms delay before showing tooltip
  tooltipTimer = setTimeout(() => {
    const target = e.target as HTMLElement;
    const entityId = target.getAttribute('data-entity-id');
    const modalId = target.getAttribute('data-modal-id');
    // ... show tooltip
  }, 300);
};
```

---

### 6.7 Frontend TODO Completion Plan

**TODO 1: Constraint Validation** (store.ts line 158)
```typescript
// TODO: Validate refinement against constraints
// TODO: Check for conflicts
```

**Decision**: **Implement basic validation for Phase 1**

**Plan**:
- Simple validation: Check if refinement is non-empty string
- Check if refinement doesn't contradict existing constraints
- Full constraint solver deferred to Phase 2

**Implementation**:
```typescript
validateRefinement(holeId: string, refinement: string): boolean {
  if (!refinement || refinement.trim().length === 0) {
    throw new Error('Refinement cannot be empty');
  }

  const hole = get().holes.get(holeId);
  if (!hole) {
    throw new Error(`Hole ${holeId} not found`);
  }

  // Basic conflict check: if refinement contains words contradicting constraints
  const conflicts = hole.constraints?.filter(c => {
    // Example: if constraint says "must support OAuth" but refinement says "basic auth"
    return c.expression.toLowerCase().includes('oauth') &&
           refinement.toLowerCase().includes('basic auth');
  });

  if (conflicts && conflicts.length > 0) {
    throw new Error(`Refinement conflicts with constraints: ${conflicts.map(c => c.id).join(', ')}`);
  }

  return true;
}
```

---

**TODO 2: Constraint Type Determination** (store.ts line 187)
```typescript
type: 'return_constraint',  // TODO: Determine from propagation
```

**Decision**: **Implement heuristic for Phase 1**

**Plan**:
- Use pattern matching to infer constraint type from text
- Types: temporal, return_constraint, type_constraint, value_constraint
- Full semantic inference deferred to Phase 2 (DSPy)

**Implementation**:
```typescript
inferConstraintType(constraintText: string): ConstraintType {
  const lower = constraintText.toLowerCase();

  if (lower.match(/\b(when|if|before|after|during|while)\b/)) {
    return 'temporal';
  }

  if (lower.match(/\b(return|returns|output|result)\b/)) {
    return 'return_constraint';
  }

  if (lower.match(/\b(type|must be|should be|is a|typeof)\b/)) {
    return 'type_constraint';
  }

  if (lower.match(/\b(value|equal|greater|less|between)\b/)) {
    return 'value_constraint';
  }

  return 'semantic'; // Default
}
```

---

**TODO 3: Solution Space Recalculation** (store.ts line 204)
```typescript
// TODO: Recalculate solution space
```

**Decision**: **Defer to Phase 2** (requires constraint solver)

**Rationale**:
- Solution space calculation requires constraint satisfaction logic
- MVP doesn't show solution space narrowing percentage
- Displaying constraints and dependencies is sufficient for Phase 1
- Phase 2 will add constraint solver (Z3/MiniZinc) for accurate calculation

**Phase 1 Workaround**:
- Show constraints applied to hole
- Show dependent holes
- Don't calculate percentage reduction (just show "Constraints applied: 3")

---

### 6.8 Test Strategy

**Goal**: Get 22/22 Playwright tests passing

**Approach**:
1. Fix decoration application (priority 1)
2. Fix autocomplete popup (priority 2)
3. Fix tooltips (priority 3, depends on #1)
4. Run full test suite
5. Debug remaining failures

**Test Execution**:
```bash
# Run all tests
cd frontend && npx playwright test

# Run specific failing tests
npx playwright test e2e/ics-semantic-editor.spec.ts

# Run with debug
npx playwright test --debug

# Run with headed browser (see what's happening)
npx playwright test --headed
```

**Success Criteria**:
- ✅ 22/22 tests pass
- ✅ No console errors
- ✅ Manual testing confirms highlights visible
- ✅ Performance: OODA loops < 2s

---

## 7. Integration Validation ✨

**Goal**: Verify frontend ↔ backend integration works correctly

### 7.1 Integration Test Scenarios

**Scenario 1: Backend Available**
```
1. Start backend: uv run uvicorn lift_sys.api.server:app --reload
2. Start frontend: cd frontend && npm run dev
3. Open ICS view
4. Type: "The system must authenticate users"
5. Verify:
   ✅ Status: "Analyzing..." appears
   ✅ Status changes to "Analysis complete (87% confidence)"
   ✅ Highlights appear: "system" (blue), "must" (green), "users" (blue)
   ✅ Symbols panel shows: Entities (2), Modals (1)
   ✅ Console logs backend response
```

**Scenario 2: Backend Unavailable**
```
1. Stop backend
2. Start frontend: cd frontend && npm run dev
3. Open ICS view
4. Type: "The system must authenticate users"
5. Verify:
   ✅ Health check fails gracefully
   ✅ Toast: "⚠️ Backend unavailable, using pattern matching"
   ✅ Status: "Analysis by pattern matching (limited accuracy)"
   ✅ Highlights appear (from mock)
   ✅ Symbols panel shows elements
   ✅ No errors in console
```

**Scenario 3: Backend Error**
```
1. Start backend
2. Simulate error (modify backend to throw exception)
3. Start frontend
4. Type text
5. Verify:
   ✅ Error caught gracefully
   ✅ Toast: "Analysis failed, using fallback"
   ✅ Falls back to mock
   ✅ User not blocked
```

**Scenario 4: Backend Timeout**
```
1. Start backend
2. Simulate slow response (add sleep(10) in backend)
3. Start frontend
4. Type text
5. Verify:
   ✅ Timeout after 5s
   ✅ Fallback to mock
   ✅ Toast notification
```

### 7.2 Integration Checklist

**Frontend → Backend**:
- ✅ Health check endpoint called on mount
- ✅ Analyze endpoint called with correct payload
- ✅ Request timeout set (5s)
- ✅ Error handling for network failures
- ✅ Error handling for 400/500 responses
- ✅ Retry logic (optional, Phase 2)

**Backend → Frontend**:
- ✅ Response matches SemanticAnalysis TypeScript interface
- ✅ Field names match (camelCase in frontend, snake_case in backend with alias)
- ✅ Positions (from, to) are correct relative to input text
- ✅ IDs are unique
- ✅ Confidence scores present

**Graceful Degradation**:
- ✅ Mock analysis matches backend structure
- ✅ Mock analysis uses same field names
- ✅ Mock analysis provides reasonable data for testing
- ✅ User can't tell difference visually (except accuracy)

### 7.3 API Contract Validation

**Request Schema**:
```typescript
interface AnalyzeRequest {
  text: string;
  options?: {
    includeConfidence?: boolean;
    detectHoles?: boolean;
  };
}
```

**Response Schema**:
```typescript
interface AnalyzeResponse {
  entities: Entity[];
  relationships: Relationship[];
  modalOperators: ModalOperator[];
  constraints: Constraint[];
  effects: Effect[];
  assertions: Assertion[];
  ambiguities: Ambiguity[];
  contradictions: Contradiction[];
  typedHoles: TypedHole[];
  confidenceScores: Record<string, number>;
}
```

**Validation Tests**:
```bash
# Test 1: Valid request
curl -X POST http://localhost:8000/ics/analyze \
  -H "Content-Type: application/json" \
  -d '{"text": "Test", "options": {"includeConfidence": true}}'
# Expected: 200 OK, valid response

# Test 2: Empty text
curl -X POST http://localhost:8000/ics/analyze \
  -H "Content-Type: application/json" \
  -d '{"text": ""}'
# Expected: 400 Bad Request

# Test 3: Missing text field
curl -X POST http://localhost:8000/ics/analyze \
  -H "Content-Type: application/json" \
  -d '{}'
# Expected: 422 Unprocessable Entity

# Test 4: Text too long
curl -X POST http://localhost:8000/ics/analyze \
  -H "Content-Type: application/json" \
  -d "{\"text\": \"$(python -c 'print("a" * 100000)')\"}"
# Expected: 400 Bad Request (> 50k chars)
```

### 7.4 Performance Validation

**Metrics**:
| Operation | Target | Actual | Status |
|-----------|--------|--------|--------|
| Health check | < 100ms | ? | ⏳ Test |
| Analyze (backend) | < 1s | ? | ⏳ Test |
| Analyze (mock) | < 200ms | ? | ⏳ Test |
| Frontend debounce | 500ms | 500ms | ✅ Set |
| Decoration apply | < 100ms | ? | ⏳ Test |
| OODA cycle (total) | < 2s | ? | ⏳ Test |

**Load Testing** (Phase 2):
- Multiple concurrent analyses
- Large text inputs (10k+ words)
- Rapid typing simulation

---

## 8. Acceptance Criteria

**Phase 1 is COMPLETE when ALL of the following are TRUE**:

### 8.1 Functional Requirements

- ✅ **FR1**: User can type natural language specification in editor
- ✅ **FR2**: Semantic elements (entities, modals, constraints, holes, ambiguities) are detected
- ✅ **FR3**: Semantic elements are highlighted in editor with colored decorations
- ✅ **FR4**: Symbols panel shows list of detected elements (Entities, Holes, Constraints tabs)
- ✅ **FR5**: Clicking element in Symbols panel jumps to position in editor
- ✅ **FR6**: Selecting hole in Symbols panel opens HoleInspector with details
- ✅ **FR7**: Autocomplete triggers with # (files) and @ (symbols)
- ✅ **FR8**: Autocomplete shows results, filters as user types, inserts on selection
- ✅ **FR9**: Autocomplete dismisses on Escape
- ✅ **FR10**: Hovering over semantic element shows tooltip with details (300ms delay)
- ✅ **FR11**: System uses backend NLP API when available
- ✅ **FR12**: System falls back to mock analysis when backend unavailable
- ✅ **FR13**: User sees toast notification when backend unavailable
- ✅ **FR14**: Character count updates in real-time in toolbar

### 8.2 State Handling Requirements

- ✅ **SH1**: Empty state shown when no text in editor (placeholder message)
- ✅ **SH2**: Loading state shown during analysis ("Analyzing..." + spinner)
- ✅ **SH3**: Success state shown when analysis complete (confidence score)
- ✅ **SH4**: Error state shown when analysis fails (toast + fallback)
- ✅ **SH5**: Empty state shown in SymbolsPanel when no elements detected
- ✅ **SH6**: Loading state shown in SymbolsPanel during analysis (skeleton)
- ✅ **SH7**: Empty state shown in HoleInspector when no hole selected
- ✅ **SH8**: Empty state shown in autocomplete when no results match
- ✅ **SH9**: Error state shown in FileExplorer if tree fails to load (+ retry)

### 8.3 OODA Loop Requirements

- ✅ **OODA1**: Semantic analysis OODA cycle < 2s (typing → highlights visible)
- ✅ **OODA2**: Hole inspection OODA cycle < 10s (click → understand → decide → act)
- ✅ **OODA3**: Autocomplete OODA cycle < 1s (trigger → select → insert)
- ✅ **OODA4**: Error recovery OODA cycle < 5s (error → fallback → resume)
- ✅ **OODA5**: All user actions have immediate visual feedback (< 100ms)

### 8.4 Technical Requirements

- ✅ **TECH1**: All 22 Playwright E2E tests pass
- ✅ **TECH2**: No console errors in browser during normal operation
- ✅ **TECH3**: Backend NLP API starts without errors
- ✅ **TECH4**: Backend /ics/health endpoint returns healthy
- ✅ **TECH5**: Backend /ics/analyze endpoint returns valid SemanticAnalysis
- ✅ **TECH6**: Frontend decorations plugin applies CSS classes to DOM
- ✅ **TECH7**: Frontend mock analysis generates realistic data
- ✅ **TECH8**: Type checking passes (npm run type-check)
- ✅ **TECH9**: Linting passes (npm run lint)
- ✅ **TECH10**: Build succeeds (npm run build)

### 8.5 Code Quality Requirements

- ✅ **CQ1**: All state machines documented (this spec)
- ✅ **CQ2**: All OODA loops documented (this spec)
- ✅ **CQ3**: Frontend TODOs resolved or deferred with plan
- ✅ **CQ4**: Backend TODOs resolved or deferred with plan
- ✅ **CQ5**: Phase 1 scope clearly defined
- ✅ **CQ6**: Phase 2+ features clearly deferred
- ✅ **CQ7**: Integration tests pass (backend ↔ frontend)
- ✅ **CQ8**: Error handling comprehensive (no uncaught exceptions)

---

## 9. Reference: Original Spec

**Original**: `docs/ICS_INTERFACE_SPECIFICATION.md` (1,548 lines)

**Sections Retained**:
- Data Model (TypeScript types) → Use as-is
- Component Hierarchy → Use as-is
- File Structure → Use as-is
- Color Palette → Use as-is
- Typography → Use as-is
- Accessibility (WCAG 2.1 AA) → Use as-is
- Keyboard Shortcuts → Use as-is

**Sections Enhanced**:
- User Interactions → Added OODA loop mapping
- API Integration → Added integration validation
- State Management → Added state machines per component

**Sections Deferred**:
- Dependency Graph Visualization → Phase 3
- Constraint Solver Integration → Phase 2
- Collaborative Editing → Phase 5
- Version Control Integration → Phase 4
- AI-Powered Refinement → Phase 2
- Code Generation → Phase 4
- Semantic Search → Phase 3
- Team Collaboration → Phase 5
- Templates & Libraries → Phase 5
- Analytics & Insights → Phase 5

**Use Original Spec For**:
- Detailed TypeScript type definitions (Section 4)
- ProseMirror schema (Section 5.5)
- API endpoint contracts (Section 8)
- Visual design tokens (Section 10)
- Accessibility requirements (Section 11)

---

**End of Refined Specification v1**

**Next Steps**:
1. Review and approve this spec
2. Proceed to Phase 2: Create master spec + sub-specs
3. Generate execution plan (Phase 3)
4. Create Beads issues (Phase 4)
5. Begin implementation

**Document Status**: Phase 1 Complete, Ready for Review
