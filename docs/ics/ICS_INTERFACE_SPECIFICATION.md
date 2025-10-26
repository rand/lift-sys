# ICS (Integrated Context Studio) - Complete Interface Specification

**Version**: 1.0
**Date**: 2025-10-25
**Status**: Phase 1 & 2 Complete
**Branch**: `feature/ics-implementation`

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [System Overview](#system-overview)
3. [Architecture](#architecture)
4. [Data Model](#data-model)
5. [UI Components](#ui-components)
6. [Semantic Analysis](#semantic-analysis)
7. [User Interactions](#user-interactions)
8. [API Integration](#api-integration)
9. [State Management](#state-management)
10. [Visual Design](#visual-design)
11. [Accessibility](#accessibility)
12. [Performance](#performance)
13. [Future Enhancements](#future-enhancements)

---

## 1. Executive Summary

### Purpose
ICS (Integrated Context Studio) is a semantic-aware specification editor that enables developers to write natural language requirements with real-time analysis, typed hole tracking, and constraint propagation for the lift-sys project.

### Key Features
- **Semantic Text Editor**: ProseMirror-based rich text editor with NLP-powered highlighting
- **Real-time Analysis**: Detects entities, modal operators, constraints, holes, and ambiguities
- **Hole-Driven Development**: Visual tracking of typed holes with dependency graphs
- **Constraint Propagation**: Automatic constraint flow visualization
- **4-Panel Layout**: File explorer, editor, symbols panel, hole inspector, AI chat
- **Autocomplete**: Context-aware file (#) and symbol (@) references
- **Hover Tooltips**: Detailed information on hover over semantic elements
- **Graceful Degradation**: Works with or without backend NLP service

### Technology Stack
- **Framework**: React 18 + TypeScript
- **Editor**: ProseMirror (extensible rich text)
- **UI Library**: shadcn/ui (Radix UI + Tailwind CSS)
- **State Management**: Zustand (with persist + devtools)
- **Layout**: react-resizable-panels
- **Backend**: FastAPI + spaCy NLP (optional)
- **Styling**: Tailwind CSS + custom ICS theme

---

## 2. System Overview

### System Context

```
┌─────────────────────────────────────────────────────────────┐
│                    lift-sys Platform                         │
│  ┌───────────────┐  ┌─────────────┐  ┌──────────────┐      │
│  │ Configuration │  │ Repository  │  │ Prompt       │      │
│  │ View          │  │ View        │  │ Workbench    │      │
│  └───────────────┘  └─────────────┘  └──────────────┘      │
│                                                               │
│  ┌──────────────────────────────────────────────────────┐   │
│  │                 ICS (New) ◄── THIS SPEC              │   │
│  │  Natural Language → IR → Code Pipeline Integration   │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                               │
│  ┌───────────┐  ┌──────────┐  ┌─────────────┐              │
│  │ IR Review │  │ Planner  │  │ IDE         │              │
│  └───────────┘  └──────────┘  └─────────────┘              │
└─────────────────────────────────────────────────────────────┘
         │                                │
         │                                │
    ┌───▼────────┐                  ┌────▼─────────┐
    │ Backend    │                  │ Modal.com    │
    │ NLP API    │                  │ GPU Workers  │
    │ (FastAPI)  │                  │ (LLM)        │
    └────────────┘                  └──────────────┘
```

### User Workflow

```
1. User opens ICS view
2. Writes natural language specification in semantic editor
3. System analyzes text (500ms debounce)
   → Detects entities (PERSON, ORG, TECHNICAL, etc.)
   → Identifies modal operators (must, may, should, cannot)
   → Extracts constraints (temporal, return, position)
   → Finds typed holes (???, TODO markers)
   → Flags ambiguities (underspecified requirements)
4. Real-time visual feedback:
   → Semantic highlights (color-coded by type)
   → Hover tooltips with details
   → Autocomplete for file/symbol refs
5. Hole Inspector shows:
   → Dependencies (blocks, blocked by)
   → Constraints applied
   → Solution space reduction
   → AI refinement suggestions
6. Constraint propagation:
   → Resolving one hole propagates to dependents
   → Visual feedback on constraint flow
7. Export to IR/code when ready
```

---

## 3. Architecture

### High-Level Architecture

```
┌────────────────────────────────────────────────────────────┐
│                      ICS Frontend                           │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              React Application                        │  │
│  │  ┌────────┐  ┌──────────┐  ┌─────────┐  ┌─────────┐ │  │
│  │  │ Menu   │  │ File     │  │ Active  │  │ Right   │ │  │
│  │  │ Bar    │  │ Explorer │  │ Editor  │  │ Panels  │ │  │
│  │  └────────┘  └──────────┘  └─────────┘  └─────────┘ │  │
│  │      │             │             │             │      │  │
│  │      └─────────────┴─────────────┴─────────────┘      │  │
│  │                        │                              │  │
│  │                   ┌────▼──────┐                       │  │
│  │                   │ Zustand   │                       │  │
│  │                   │ Store     │                       │  │
│  │                   └────┬──────┘                       │  │
│  │                        │                              │  │
│  │      ┌─────────────────┼─────────────────┐            │  │
│  │      │                 │                 │            │  │
│  │ ┌────▼───┐       ┌────▼─────┐      ┌───▼────┐       │  │
│  │ │ProseMir│       │Semantic  │      │Auto    │       │  │
│  │ │Editor  │       │Analysis  │      │complete│       │  │
│  │ └────────┘       └──────────┘      └────────┘       │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────┬──────────────────────────────────┘
                          │ REST API
                          │
┌─────────────────────────▼──────────────────────────────────┐
│                  Backend NLP Service (Optional)             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              FastAPI Application                      │  │
│  │  ┌─────────────┐  ┌──────────────┐  ┌────────────┐  │  │
│  │  │ spaCy NLP   │  │ Constraint   │  │ Hole       │  │  │
│  │  │ Pipeline    │  │ Detector     │  │ Detector   │  │  │
│  │  └─────────────┘  └──────────────┘  └────────────┘  │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### Component Hierarchy

```
ICSView
└── ICSLayout
    ├── MenuBar
    │   └── Icon buttons (Files, Search, Git, Terminal, Settings)
    │
    ├── PanelGroup (horizontal)
    │   ├── Panel (left): FileExplorer
    │   │   └── FileTreeNode (recursive)
    │   │
    │   ├── Panel (center): ActiveEditor
    │   │   └── SemanticEditor
    │   │       ├── ProseMirror EditorView
    │   │       ├── AutocompletePopup
    │   │       └── SemanticTooltip
    │   │
    │   └── Panel (right): PanelGroup (vertical)
    │       ├── Panel (top): PanelGroup (vertical)
    │       │   ├── SymbolsPanel
    │       │   └── HoleInspector
    │       │
    │       └── Panel (bottom): AIChat
    │
    └── (Keyboard shortcuts, global state)
```

### File Structure

```
frontend/src/
├── views/
│   └── ICSView.tsx                    # Main view entry point
│
├── components/ics/
│   ├── ICSLayout.tsx                  # 4-panel layout
│   ├── MenuBar.tsx                    # Left icon bar
│   ├── FileExplorer.tsx               # File tree
│   ├── ActiveEditor.tsx               # Editor wrapper
│   ├── SemanticEditor.tsx             # ProseMirror editor
│   ├── SymbolsPanel.tsx               # Symbols list
│   ├── HoleInspector.tsx              # Hole details
│   ├── AIChat.tsx                     # AI assistant
│   ├── AutocompletePopup.tsx          # # and @ autocomplete
│   └── SemanticTooltip.tsx            # Hover tooltips
│
├── lib/ics/
│   ├── store.ts                       # Zustand state management
│   ├── schema.ts                      # ProseMirror schema
│   ├── decorations.ts                 # Semantic highlighting
│   ├── autocomplete.ts                # Autocomplete logic
│   ├── api.ts                         # Backend API client
│   └── mockSemanticAnalysis.ts        # Fallback mock data
│
├── types/ics/
│   └── semantic.ts                    # TypeScript types
│
└── styles/
    └── ics.css                        # ICS-specific styles
```

---

## 4. Data Model

### Core Types

#### SemanticAnalysis
Complete result of NLP analysis on the specification text.

```typescript
interface SemanticAnalysis {
  entities: Entity[];               // Detected named entities
  relationships: Relationship[];    // Entity relationships
  modalOperators: ModalOperator[];  // must, may, should, cannot
  constraints: Constraint[];        // Extracted constraints
  effects: Effect[];                // Side effects, IO, state changes
  assertions: Assertion[];          // Pre/post conditions
  ambiguities: Ambiguity[];         // Underspecified areas
  contradictions: Contradiction[];  // Conflicting statements
  typedHoles: TypedHole[];          // Typed holes (???)
  confidenceScores: Record<string, number>;
}
```

#### Entity
Named entities detected by NLP (people, organizations, technical terms, etc.)

```typescript
interface Entity {
  id: string;                       // Unique identifier
  type: EntityType;                 // PERSON, ORG, TECHNICAL, etc.
  text: string;                     // Extracted text
  from: number;                     // Start position in doc
  to: number;                       // End position in doc
  confidence: number;               // 0.0 - 1.0
  metadata?: Record<string, unknown>;
}

type EntityType =
  | 'PERSON' | 'ORG' | 'GPE' | 'LOC' | 'PRODUCT' | 'EVENT'
  | 'TECHNICAL' | 'FUNCTION' | 'CLASS' | 'VARIABLE' | 'TYPE';
```

#### ModalOperator
Modal logic operators indicating requirements strength.

```typescript
interface ModalOperator {
  id: string;
  modality: ModalityType;           // certainty, possibility, necessity, prohibition
  text: string;                     // "must", "may", "should", "cannot"
  from: number;
  to: number;
  scope: string;                    // What this modal applies to
}

type ModalityType =
  | 'certainty'     // must, will, always
  | 'possibility'   // may, might, could
  | 'necessity'     // should, ought to
  | 'prohibition';  // must not, cannot
```

#### TypedHole
Typed holes representing incomplete specifications (??? markers or inferred gaps).

```typescript
interface TypedHole {
  id: string;
  identifier: string;               // Hole name (e.g., "H1", "AuthHole")
  kind: HoleKind;                   // intent, signature, effect, assertion, implementation
  typeHint: string;                 // Expected type
  description: string;              // What needs to be filled
  status: HoleStatus;               // unresolved, in_progress, resolved
  confidence: number;               // Detection confidence
  evidence: string[];               // Why this is a hole
  pos?: number;                     // Position in document
  provenance?: Provenance;          // Where it came from
  constraints?: string[];           // Applied constraint IDs
}

type HoleKind = 'intent' | 'signature' | 'effect' | 'assertion' | 'implementation';
type HoleStatus = 'unresolved' | 'in_progress' | 'resolved';
```

#### Constraint
Constraints that limit the solution space for holes.

```typescript
interface Constraint {
  id: string;
  type: ConstraintType;             // return_constraint, loop_constraint, position_constraint
  description: string;              // Human-readable constraint
  severity: ConstraintSeverity;     // error, warning
  appliesTo: string[];              // Hole IDs this constrains
  source: string;                   // Where constraint originated
  impact: string;                   // Effect on solution space
  locked: boolean;                  // Design decision locked in?
  metadata?: Record<string, unknown>;
}

type ConstraintType = 'return_constraint' | 'loop_constraint' | 'position_constraint';
type ConstraintSeverity = 'error' | 'warning';
```

#### Ambiguity
Underspecified or unclear areas in the specification.

```typescript
interface Ambiguity {
  id: string;
  text: string;                     // Ambiguous text
  from: number;
  to: number;
  reason: string;                   // Why it's ambiguous
  suggestions?: string[];           // How to resolve
}
```

#### HoleDetails
Extended information for hole inspector view.

```typescript
interface HoleDetails {
  // Basic info
  identifier: string;
  kind: HoleKind;
  typeHint: string;
  description: string;

  // Status
  status: HoleStatus;
  phase: number;
  priority: 'critical' | 'high' | 'medium' | 'low';

  // Dependencies
  blocks: HoleDependency[];         // Holes this blocks
  blockedBy: HoleDependency[];      // Holes blocking this
  dependsOn: HoleDependency[];      // Dependencies

  // Constraints
  constraints: Constraint[];
  propagatesTo: Array<{
    targetId: string;
    targetName: string;
    constraint: string;
    impact: string;
  }>;

  // Solution space
  solutionSpace: SolutionSpace;

  // Provenance
  provenance: Provenance;

  // Acceptance criteria
  acceptanceCriteria: AcceptanceCriterion[];

  // AI suggestions
  refinements: RefinementSuggestion[];
}
```

### State Management

#### ICSStore (Zustand)

```typescript
interface ICSStore {
  // Document state
  specification: ProseMirrorNode | null;
  specificationText: string;

  // Semantic analysis
  semanticAnalysis: SemanticAnalysis | null;
  isAnalyzing: boolean;

  // Holes & constraints
  holes: Map<string, HoleDetails>;
  constraints: Map<string, Constraint>;
  selectedHole: string | null;

  // UI state
  layout: LayoutConfig;
  panelVisibility: PanelVisibility;
  activeTab: 'natural-language' | 'ir' | 'code' | 'split';

  // Actions
  setSpecification: (doc: ProseMirrorNode, text: string) => void;
  updateSemanticAnalysis: (analysis: SemanticAnalysis) => void;
  setIsAnalyzing: (analyzing: boolean) => void;
  selectHole: (id: string | null) => void;
  resolveHole: (id: string, refinement: unknown) => Promise<void>;
  propagateConstraints: (holeId: string) => void;
  setLayout: (layout: Partial<LayoutConfig>) => void;
  setPanelVisibility: (panel: keyof PanelVisibility, visible: boolean) => void;
  setActiveTab: (tab: 'natural-language' | 'ir' | 'code' | 'split') => void;

  // Computed getters
  unresolvedHoles: () => HoleDetails[];
  criticalPathHoles: () => HoleDetails[];
  blockedHoles: () => HoleDetails[];
}
```

---

## 5. UI Components

### 5.1 ICSLayout

**Purpose**: Main container with 4-panel resizable layout.

**Layout Structure**:
```
┌────┬──────────┬─────────────────────────┬──────────────────┐
│    │          │                         │                  │
│ M  │   File   │      Active Editor      │   Symbols        │
│ e  │   Tree   │                         │   Panel          │
│ n  │          │  (Semantic Editor)      │                  │
│ u  │          │                         ├──────────────────┤
│    │          │                         │   Hole           │
│ B  │          │                         │   Inspector      │
│ a  │          │                         │                  │
│ r  │          │                         ├──────────────────┤
│    │          │                         │   AI Chat        │
│    │          │                         │                  │
└────┴──────────┴─────────────────────────┴──────────────────┘
```

**Panel Configuration**:
- **MenuBar**: Fixed 48px width, left side
- **FileExplorer**: Resizable 15-40%, min 15%, default 20%
- **ActiveEditor**: Flexible, min 30%
- **RightPanel**: Resizable 20-50%, min 20%, default 25%
  - **SymbolsPanel**: Top, resizable
  - **HoleInspector**: Middle, resizable
  - **AIChat**: Bottom, resizable

**Visibility Controls**:
All panels except editor are toggleable via:
- MenuBar icons
- Keyboard shortcuts
- State persisted in localStorage

---

### 5.2 MenuBar

**Purpose**: Icon-based navigation bar for toggling panels.

**Items**:
| Icon | Label | Action | Shortcut |
|------|-------|--------|----------|
| 📄 | Files | Toggle file explorer | Ctrl+B |
| 🔍 | Search | Open search panel | Ctrl+Shift+F |
| 🌿 | Source Control | Open Git panel | Ctrl+Shift+G |
| 💻 | Terminal | Toggle terminal | Ctrl+` |
| ⚙️ | Settings | Open settings | Ctrl+, |

**Visual States**:
- **Default**: Ghost variant, gray icon
- **Active**: Secondary background, highlighted icon
- **Hover**: Tooltip appears after 300ms

---

### 5.3 FileExplorer

**Purpose**: Tree view of project files and specifications.

**Features**:
- Recursive folder expansion/collapse
- File type icons (folder, file)
- Click to open file
- Lazy loading for large trees
- Search/filter (future)

**Mock Data**:
Currently shows mock file tree with:
- `docs/` (planning, supabase)
- `lift_sys/` (ir, dspy_signatures)
- `specifications/` (example specs)

**Interactions**:
- Click folder: Toggle expand/collapse
- Click file: Open in editor
- Right-click: Context menu (future)
- Drag: Reorder/move files (future)

---

### 5.4 ActiveEditor

**Purpose**: Container for the main semantic editor with toolbar.

**Components**:
- **Toolbar**: Character count, analysis status, view mode
- **SemanticEditor**: ProseMirror editor instance
- **Status Bar**: Cursor position, word count (future)

**Toolbar Elements**:
```
┌─────────────────────────────────────────────────────────┐
│ 📝 Character count: 1,234  │  Status: Analyzing...      │
│ [NL] [IR] [Code] [Split]   │  [Save] [Export]           │
└─────────────────────────────────────────────────────────┘
```

**View Modes**:
- **NL (Natural Language)**: Semantic editor only
- **IR**: Show generated IR alongside
- **Code**: Show generated code
- **Split**: All three views side-by-side

---

### 5.5 SemanticEditor

**Purpose**: Core ProseMirror-based rich text editor with semantic analysis.

#### Editor Schema

```typescript
// ProseMirror Schema
const specSchema = schema({
  nodes: {
    doc: { content: "block+" },
    paragraph: {
      content: "inline*",
      group: "block",
      parseDOM: [{ tag: "p" }],
      toDOM: () => ["p", 0]
    },
    text: { group: "inline" },
  },
  marks: {
    // Semantic marks (applied dynamically via decorations)
    entity: { attrs: { entityId: {}, type: {} } },
    modal: { attrs: { modalId: {} } },
    constraint: { attrs: { constraintId: {} } },
    hole: { attrs: { holeId: {} } },
    ambiguity: { attrs: { ambiguityId: {} } },
    fileRef: { attrs: { fileId: {} } },
    symbolRef: { attrs: { symbolId: {} } },
  }
});
```

#### Semantic Highlighting

Elements are highlighted using ProseMirror decorations:

```typescript
// Decoration plugin applies CSS classes based on semantic analysis
const decorationsPlugin = createDecorationsPlugin({
  onUpdate: (semanticAnalysis) => {
    // Apply decorations for each semantic element type
    const decorations = [
      ...createEntityDecorations(semanticAnalysis.entities),
      ...createModalDecorations(semanticAnalysis.modalOperators),
      ...createConstraintDecorations(semanticAnalysis.constraints),
      ...createHoleDecorations(semanticAnalysis.typedHoles),
      ...createAmbiguityDecorations(semanticAnalysis.ambiguities),
    ];
    return DecorationSet.create(doc, decorations);
  }
});
```

**CSS Classes**:
```css
.entity          { background: rgba(59, 130, 246, 0.2); }  /* Blue */
.modal           { background: rgba(16, 185, 129, 0.2); }  /* Green */
.constraint      { background: rgba(245, 158, 11, 0.2); }  /* Amber */
.hole            { background: rgba(239, 68, 68, 0.2); }   /* Red */
.ambiguity       { background: rgba(168, 85, 247, 0.2); }  /* Purple */
```

#### Real-Time Analysis Flow

```
User types
  ↓
Debounce (500ms)
  ↓
Extract text from ProseMirror doc
  ↓
Check backend health
  ├─ Available: POST /ics/analyze
  └─ Unavailable: Use mock analysis
  ↓
Parse SemanticAnalysis response
  ↓
Update Zustand store
  ↓
Decorations plugin reacts
  ↓
Apply semantic highlights
  ↓
User sees colored text
```

#### Autocomplete System

**Triggers**:
- `#` → File autocomplete
- `@` → Symbol autocomplete

**Flow**:
```
User types # or @
  ↓
Autocomplete plugin detects trigger
  ↓
Extract query after trigger (e.g., "#doc" → query="doc")
  ↓
Search files or symbols
  ↓
Show AutocompletePopup with results
  ↓
User selects item (click or Enter)
  ↓
Insert text at cursor position
  ↓
Dismiss popup
```

**Keyboard Navigation**:
- `ArrowDown`: Next item
- `ArrowUp`: Previous item
- `Enter`: Select current item
- `Escape`: Dismiss popup

---

### 5.6 AutocompletePopup

**Purpose**: Dropdown showing autocomplete results for # and @ triggers.

**Position**: Appears below cursor at trigger position.

**Structure**:
```
┌─────────────────────────────┐
│ # Files                     │
│ ──────────────────────────  │
│ 📄 docs/planning/HOLES.md   │  ← selected
│ 📄 docs/supabase/SCHEMA.md  │
│ 📁 specifications/          │
└─────────────────────────────┘
```

**Features**:
- Fuzzy search filtering
- Icon indicators (file type, symbol type)
- Keyboard navigation
- Click or Enter to select
- Auto-dismissal on blur or Escape

---

### 5.7 SemanticTooltip

**Purpose**: Hover tooltips showing detailed information about semantic elements.

**Trigger**: Hover over any highlighted element for 300ms.

**Content by Element Type**:

**Entity**:
```
┌──────────────────────────┐
│ Entity: PERSON           │
│ ───────────────────────  │
│ Text: "Alice"            │
│ Confidence: 95%          │
│ Type: Named entity       │
└──────────────────────────┘
```

**Modal Operator**:
```
┌──────────────────────────┐
│ Modal: Certainty         │
│ ───────────────────────  │
│ Text: "must"             │
│ Modality: MUST           │
│ Scope: "authenticate"    │
└──────────────────────────┘
```

**Typed Hole**:
```
┌────────────────────────────┐
│ Hole: H1 (Intent)          │
│ ─────────────────────────  │
│ Type: ???AuthMethod        │
│ Status: Unresolved         │
│ Confidence: 87%            │
│ Description: Auth method   │
│                            │
│ [View in Inspector] →      │
└────────────────────────────┘
```

**Constraint**:
```
┌────────────────────────────┐
│ Constraint: Return Type    │
│ ─────────────────────────  │
│ Type: return_constraint    │
│ Severity: Error            │
│ Applies to: H3, H5         │
│ Impact: Must return bool   │
└────────────────────────────┘
```

**Ambiguity**:
```
┌──────────────────────────────┐
│ Ambiguity Detected           │
│ ───────────────────────────  │
│ Text: "quickly process"      │
│ Reason: Vague performance    │
│                              │
│ Suggestions:                 │
│ • Process in < 100ms         │
│ • Process in < 1s            │
│ • Specify exact SLA          │
└──────────────────────────────┘
```

---

### 5.8 SymbolsPanel

**Purpose**: Outline view of detected symbols and references.

**Tabs**:
- **Entities**: All detected entities
- **Holes**: All typed holes
- **Constraints**: All constraints
- **Symbols**: Functions, classes, variables

**Entity List View**:
```
┌──────────────────────────┐
│ Entities (12)            │
│ ───────────────────────  │
│ 👤 Alice          PERSON │
│ 🏢 Google         ORG    │
│ 💻 authenticate() FUNC   │
│ 📦 UserService    CLASS  │
└──────────────────────────┘
```

**Holes List View**:
```
┌──────────────────────────┐
│ Holes (5)                │
│ ───────────────────────  │
│ 🔴 H1: AuthMethod        │
│ 🔴 H2: StorageBackend    │
│ 🟡 H3: ErrorHandler      │
│ 🟢 H4: Logger ✓          │
└──────────────────────────┘
```

**Interactions**:
- Click item: Jump to position in editor
- Double-click hole: Open in inspector
- Right-click: Context menu (future)

---

### 5.9 HoleInspector

**Purpose**: Detailed view of selected typed hole with dependencies, constraints, and refinements.

**Header**:
```
┌────────────────────────────────┐
│ Hole Inspector                 │
│ ─────────────────────────────  │
│ 🔴 H1: AuthenticationMethod    │
│ [intent] [unresolved] [P0]     │
│ Type: ???OAuthProvider         │
│ Description: Choose OAuth...   │
└────────────────────────────────┘
```

**Sections** (collapsible):

**1. Dependencies**:
```
Blocks:
  • H3: SessionManager (needs auth first)
  • H5: TokenValidator (depends on auth)

Blocked By:
  (none)

Depends On:
  • H2: CredentialStore (stores OAuth tokens)
```

**2. Constraints**:
```
Applied Constraints (3):
  1. Must support Google OAuth
     [Source: User requirement]
     [Severity: Error]

  2. Must handle token refresh
     [Source: Security policy]
     [Severity: Warning]

  3. Return type: OAuthProvider
     [Source: Type inference]
     [Severity: Error]
```

**3. Constraint Propagation**:
```
Resolving this hole will propagate to:
  • H3: SessionManager
    Constraint: Must use OAuthProvider type
    Impact: 40% solution space reduction

  • H5: TokenValidator
    Constraint: Must validate OAuth tokens
    Impact: 60% solution space reduction
```

**4. Solution Space**:
```
Before resolution:
  ["Google OAuth", "GitHub OAuth", "SAML", "Custom", ...]
  (estimated 50+ options)

Current constraints applied:
  ✓ Must support Google OAuth
  ✓ Must handle token refresh

After constraints:
  ["Google OAuth", "GitHub OAuth"]
  (2 options, 96% reduction)
```

**5. Acceptance Criteria**:
```
[ ] Supports Google OAuth login
[ ] Handles token refresh automatically
[✓] Returns OAuthProvider type
[ ] Tested with 100+ concurrent users
```

**6. AI Refinements**:
```
💡 Suggestion 1 (Confidence: 92%)
   "Use Passport.js with Google strategy"
   Rationale: Industry standard, well-tested
   Impact: Reduces implementation time by 50%
   [Apply]

💡 Suggestion 2 (Confidence: 78%)
   "Implement custom OAuth2 client"
   Rationale: More control, fewer dependencies
   Impact: Increases flexibility but adds complexity
   [Apply]
```

**Actions**:
- **Resolve Hole**: Opens refinement dialog
- **Mark In Progress**: Changes status
- **Add Constraint**: Manual constraint addition
- **View Provenance**: Shows hole origin

---

### 5.10 AIChat

**Purpose**: AI assistant for specification refinement and Q&A.

**Interface**:
```
┌─────────────────────────────────────┐
│ AI Assistant                        │
│ ──────────────────────────────────  │
│ You: How should I implement H1?     │
│                                     │
│ AI: Based on your constraints, I    │
│ recommend using Passport.js with... │
│                                     │
│ [Type your message...]       [Send] │
└─────────────────────────────────────┘
```

**Features**:
- Context-aware: Knows current specification
- Hole-aware: Can reference typed holes
- Refinement suggestions
- Constraint analysis
- Code generation previews (future)

**Commands**:
- `/refine H1` → Suggest refinement for H1
- `/analyze` → Analyze current specification
- `/constraints H1` → Show constraints for H1
- `/explain <term>` → Explain technical term

---

## 6. Semantic Analysis

### Analysis Pipeline

```
Input: Natural language specification text
  ↓
1. Tokenization (spaCy)
  ↓
2. Entity Recognition (NER)
   → Detects: PERSON, ORG, GPE, TECHNICAL, FUNCTION, CLASS
  ↓
3. Dependency Parsing
   → Identifies relationships between entities
  ↓
4. Modal Operator Detection
   → Pattern matching: "must", "may", "should", "cannot"
   → Contextual analysis: scope of modal
  ↓
5. Constraint Extraction
   → Return type hints
   → Temporal constraints ("before X", "when Y")
   → Position constraints ("at index 0", "last item")
  ↓
6. Typed Hole Detection
   → Explicit: "???" markers
   → Implicit: Underspecified areas
  ↓
7. Ambiguity Detection
   → Vague quantifiers ("quickly", "many")
   → Missing specifics ("store data" → where?)
  ↓
8. Contradiction Detection
   → Conflicting requirements
   → Impossible constraints
  ↓
Output: SemanticAnalysis object
```

### Backend API

**Endpoint**: `POST /ics/analyze`

**Request**:
```json
{
  "text": "The system must authenticate users before granting access...",
  "options": {
    "includeConfidence": true,
    "detectHoles": true
  }
}
```

**Response**:
```json
{
  "entities": [
    {
      "id": "e1",
      "type": "FUNCTION",
      "text": "authenticate",
      "from": 15,
      "to": 27,
      "confidence": 0.95
    }
  ],
  "modalOperators": [
    {
      "id": "m1",
      "modality": "certainty",
      "text": "must",
      "from": 11,
      "to": 15,
      "scope": "authenticate users"
    }
  ],
  "constraints": [...],
  "typedHoles": [...],
  "ambiguities": [...],
  "contradictions": [],
  "effects": [],
  "assertions": [],
  "relationships": [],
  "confidenceScores": {
    "overall": 0.87
  }
}
```

**Health Check**: `GET /ics/health`
```json
{
  "status": "healthy",
  "nlp_model": "en_core_web_sm",
  "version": "1.0.0"
}
```

### Mock Analysis (Fallback)

When backend is unavailable, `mockSemanticAnalysis.ts` provides:
- Pattern-based entity detection (regex for common names)
- Modal keyword detection (must/may/should/cannot)
- Simple hole detection (??? markers)
- Probabilistic ambiguity detection (30% sampling)

**Limitations**:
- Lower accuracy than backend NLP
- No advanced relationship detection
- No constraint inference
- Fixed confidence scores

---

## 7. User Interactions

### 7.1 Typing Flow

```
1. User types in editor
   ↓
2. ProseMirror captures input
   ↓
3. Document state updates (Zustand)
   ↓
4. Debounce timer starts (500ms)
   ↓
5. Timer completes → Trigger analysis
   ↓
6. API call or mock analysis
   ↓
7. Update semanticAnalysis in store
   ↓
8. Decorations plugin recalculates
   ↓
9. Editor re-renders with highlights
   ↓
10. User sees semantic colors
```

**Character Count Updates**:
- Real-time display in toolbar
- Format: "1,234 characters"
- Updates on every keystroke (no debounce)

**Status Display**:
- Focused: "Editing..."
- Analyzing: "Analyzing..." (with spinner)
- Complete: "Ready" or confidence score

### 7.2 Autocomplete Flow

**File Reference** (`#`):
```
User types: "See #d"
  ↓
Autocomplete triggers
  ↓
Search files matching "d"
  → docs/planning/HOLES.md
  → docs/supabase/SCHEMA.md
  ↓
Show popup with results
  ↓
User selects with ↓↑ or clicks
  ↓
Insert: "See #docs/planning/HOLES.md"
  ↓
Create FileReference in semantic analysis
```

**Symbol Reference** (`@`):
```
User types: "Call @au"
  ↓
Autocomplete triggers
  ↓
Search symbols matching "au"
  → @authenticate (function)
  → @AuthService (class)
  ↓
Show popup with results
  ↓
User selects
  ↓
Insert: "Call @authenticate"
  ↓
Create SymbolReference in semantic analysis
```

### 7.3 Hover Tooltip Flow

```
User hovers over "must"
  ↓
300ms delay
  ↓
Check if element has semantic data
  ↓
Found: ModalOperator "must"
  ↓
Calculate tooltip position
  ↓
Show SemanticTooltip with details
  ↓
User moves mouse away
  ↓
Hide tooltip
```

### 7.4 Hole Selection Flow

```
User clicks hole in SymbolsPanel
  ↓
setSelectedHole(holeId)
  ↓
HoleInspector updates
  ↓
Shows full hole details
  ↓
User can:
  • View dependencies
  • See constraints
  • Read AI suggestions
  • Resolve hole
```

### 7.5 Constraint Propagation

```
User resolves H1 (AuthMethod)
  ↓
resolveHole(H1, "Google OAuth")
  ↓
System checks H1.blocks
  → [H3: SessionManager, H5: TokenValidator]
  ↓
For each blocked hole:
  • Add constraint from H1
  • Reduce solution space
  • Update acceptance criteria
  ↓
Visual feedback in inspector
  ↓
Update dependency graph (future: visualization)
```

---

## 8. API Integration

### Backend Endpoints

**Base URL**: `http://localhost:8000` (configurable via `VITE_API_BASE_URL`)

#### Analyze Text
```
POST /ics/analyze
Content-Type: application/json

Request:
{
  "text": "string",
  "options": {
    "includeConfidence": boolean,
    "detectHoles": boolean
  }
}

Response: SemanticAnalysis (200 OK)
Error: { "detail": "string" } (400/500)
```

#### Health Check
```
GET /ics/health

Response:
{
  "status": "healthy",
  "nlp_model": "en_core_web_sm",
  "version": "1.0.0"
}
```

### Graceful Degradation

```typescript
async function analyzeText(text: string): Promise<SemanticAnalysis> {
  try {
    // Try backend first
    const healthy = await checkBackendHealth();
    if (healthy) {
      return await callBackendAPI(text);
    }
  } catch (error) {
    console.warn('Backend unavailable, using mock analysis');
  }

  // Fallback to mock
  return generateMockAnalysis(text);
}
```

**User Indication**:
- Backend available: "Analysis by NLP service"
- Mock mode: "Analysis by pattern matching (limited accuracy)"

---

## 9. State Management

### Zustand Store Structure

```typescript
{
  // Document
  specification: ProseMirrorNode | null,
  specificationText: string,

  // Analysis
  semanticAnalysis: SemanticAnalysis | null,
  isAnalyzing: boolean,

  // Holes
  holes: Map<string, HoleDetails>,
  constraints: Map<string, Constraint>,
  selectedHole: string | null,

  // UI
  layout: {
    leftPanelWidth: 300,      // px
    rightPanelWidth: 400,     // px
    inspectorHeight: 300,     // px
    chatHeight: 300,          // px
  },
  panelVisibility: {
    fileExplorer: true,
    symbolsPanel: true,
    inspector: true,
    chat: true,
    terminal: false,
  },
  activeTab: 'natural-language',
}
```

### Persistence

**LocalStorage** (via Zustand persist middleware):
- Layout configuration
- Panel visibility
- Active tab preference

**Session Storage** (not persisted):
- Specification text
- Semantic analysis
- Selected hole

---

## 10. Visual Design

### Color Palette

**Semantic Highlighting**:
```css
--entity-color:      rgba(59, 130, 246, 0.2);    /* Blue-500 @ 20% */
--modal-color:       rgba(16, 185, 129, 0.2);    /* Green-500 @ 20% */
--constraint-color:  rgba(245, 158, 11, 0.2);    /* Amber-500 @ 20% */
--hole-color:        rgba(239, 68, 68, 0.2);     /* Red-500 @ 20% */
--ambiguity-color:   rgba(168, 85, 247, 0.2);    /* Purple-500 @ 20% */
```

**Hole Status**:
```css
--unresolved:   #EF4444  /* Red-500 */
--in-progress:  #3B82F6  /* Blue-500 */
--resolved:     #10B981  /* Green-500 */
```

**Hole Priority**:
```css
--critical:  #DC2626  /* Red-600 */
--high:      #F59E0B  /* Amber-500 */
--medium:    #3B82F6  /* Blue-500 */
--low:       #6B7280  /* Gray-500 */
```

### Typography

```css
--font-sans: 'Inter', system-ui, sans-serif;
--font-mono: 'JetBrains Mono', 'Fira Code', monospace;
--font-editor: 'GeistMono', 'JetBrains Mono', monospace;
```

**Sizes**:
- Body: 14px
- Editor: 15px
- Headers: 16-24px
- Tooltips: 13px
- Code: 14px

### Spacing

Based on 4px grid:
```css
--spacing-1: 4px;
--spacing-2: 8px;
--spacing-3: 12px;
--spacing-4: 16px;
--spacing-6: 24px;
--spacing-8: 32px;
```

### Border Radius

```css
--radius-sm: 4px;   /* Buttons, inputs */
--radius-md: 8px;   /* Cards, panels */
--radius-lg: 12px;  /* Modals */
```

---

## 11. Accessibility

### WCAG 2.1 AA Compliance

**Keyboard Navigation**:
- All interactive elements are keyboard accessible
- Tab order follows logical reading flow
- Focus indicators clearly visible
- Keyboard shortcuts documented

**Screen Readers**:
- Semantic HTML (`<nav>`, `<main>`, `<aside>`)
- ARIA labels on icons
- ARIA live regions for analysis status
- Alt text on all images/icons

**Color Contrast**:
- Text: Minimum 4.5:1 ratio
- Interactive elements: Minimum 3:1 ratio
- Semantic highlights: Sufficient contrast with background

**Focus Management**:
- Focus trapped in modals
- Focus returns to trigger after dialog close
- Skip links for main content

### Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+B` | Toggle file explorer |
| `Ctrl+Shift+F` | Focus search |
| `Ctrl+/` | Toggle AI chat |
| `Ctrl+Shift+I` | Toggle hole inspector |
| `Ctrl+S` | Save specification |
| `Ctrl+E` | Export to IR |
| `Escape` | Close autocomplete/tooltip |
| `Ctrl+Z` | Undo |
| `Ctrl+Y` | Redo |

---

## 12. Performance

### Optimization Strategies

**Debouncing**:
- Text analysis: 500ms debounce
- Layout resize: 100ms debounce
- Search filtering: 300ms debounce

**Code Splitting**:
- Lazy load views: `React.lazy()`
- Dynamic imports for heavy components
- Bundle size target: < 500KB per chunk

**Virtualization**:
- File tree: Render only visible nodes
- Symbols list: Virtual scrolling for > 100 items
- Chat history: Virtual scrolling

**Memoization**:
```typescript
const decorations = useMemo(
  () => createDecorations(semanticAnalysis),
  [semanticAnalysis]
);

const filteredHoles = useMemo(
  () => holes.filter(h => h.status === 'unresolved'),
  [holes]
);
```

**Caching**:
- Semantic analysis cached by text hash
- File tree cached in memory
- Autocomplete results cached

### Performance Metrics

**Target Metrics**:
- Initial load: < 2s
- Editor interaction: < 16ms (60 FPS)
- Analysis response: < 1s (with backend)
- Analysis response: < 200ms (mock)
- Panel resize: < 16ms (smooth 60 FPS)

**Monitoring** (future):
- Core Web Vitals (LCP, FID, CLS)
- Custom metrics (analysis latency, etc.)
- Real User Monitoring (RUM)

---

## 13. Future Enhancements

### Phase 3: Advanced Features

**Dependency Graph Visualization**:
- Interactive graph of hole dependencies
- D3.js force-directed layout
- Click to navigate, zoom/pan

**Constraint Solver Integration**:
- Real-time constraint satisfaction
- Solution space visualization
- Conflict detection and resolution

**Collaborative Editing**:
- Real-time multi-user editing (CRDT)
- Presence indicators
- Conflict resolution

**Version Control Integration**:
- Git integration in file explorer
- Diff view for specifications
- Commit/push from ICS

### Phase 4: AI Enhancements

**AI-Powered Refinement**:
- Automatic hole filling suggestions
- Constraint inference from text
- Ambiguity resolution proposals

**Code Generation**:
- Direct IR to code generation
- Multiple language targets
- Test generation from specs

**Semantic Search**:
- Natural language search across specs
- Similarity-based recommendation
- Cross-reference detection

### Phase 5: Enterprise Features

**Team Collaboration**:
- Shared specifications
- Review workflows
- Commenting system

**Templates & Libraries**:
- Specification templates
- Reusable hole patterns
- Constraint libraries

**Analytics & Insights**:
- Specification quality metrics
- Hole resolution velocity
- Team productivity analytics

---

## Appendix

### Related Documentation

- **Project Planning**: `docs/planning/META_FRAMEWORK_DESIGN_BY_HOLES.md`
- **Hole Inventory**: `docs/planning/HOLE_INVENTORY.md`
- **Test Status**: `docs/testing/E2E_TEST_STATUS.md`
- **API Reference**: `docs/API_REFERENCE.md` (future)

### Technology References

- **ProseMirror**: https://prosemirror.net/docs/
- **Zustand**: https://github.com/pmndrs/zustand
- **shadcn/ui**: https://ui.shadcn.com/
- **spaCy**: https://spacy.io/usage/linguistic-features

### Glossary

- **ICS**: Integrated Context Studio
- **IR**: Intermediate Representation
- **NLP**: Natural Language Processing
- **Typed Hole**: Explicit gap in specification marked with ???
- **Modal Operator**: Requirement strength indicator (must, may, should)
- **Constraint Propagation**: Flow of constraints from resolved holes to dependents
- **Solution Space**: Set of possible implementations for a hole
- **Provenance**: Origin and history of a specification element

---

**End of Specification**

**Document Version**: 1.0
**Last Updated**: 2025-10-25
**Maintained by**: lift-sys Development Team
**Status**: Living Document
