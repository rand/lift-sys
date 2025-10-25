# ICS State Management Specification

**Version**: 1.0
**Date**: 2025-10-25
**Component**: State Layer (Zustand Store)
**Status**: Phase 2 Sub-Specification

---

## Document Purpose

This specification defines the complete state management architecture for ICS using Zustand, including:
- State shape and structure
- TypeScript type definitions
- Actions and state transitions
- Persistence strategy
- State machines (from Phase 1)

**Parent Spec**: `ics-master-spec.md` §3.3

---

## Table of Contents

1. [TypeScript Types](#1-typescript-types)
2. [Zustand Store Structure](#2-zustand-store-structure)
3. [Actions](#3-actions)
4. [Persistence](#4-persistence)
5. [State Machines](#5-state-machines)
6. [Constraints](#6-constraints)

---

## 1. TypeScript Types

### 1.1 Core Analysis Types

**File**: `frontend/src/types/ics/semantic.ts`

#### SemanticAnalysis

Complete result of semantic analysis.

```typescript
interface SemanticAnalysis {
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

---

#### Entity

Named entity detected by NLP.

```typescript
interface Entity {
  id: string;                       // Unique: "entity-0", "entity-1", ...
  type: EntityType;
  text: string;                     // Extracted text
  from: number;                     // Start position in document
  to: number;                       // End position in document
  confidence: number;               // 0.0 - 1.0
  metadata?: Record<string, unknown>;
}

type EntityType =
  | 'PERSON'      // People (Alice, Bob)
  | 'ORG'         // Organizations (Google, Company)
  | 'GPE'         // Geopolitical entities
  | 'LOC'         // Locations
  | 'PRODUCT'     // Products
  | 'EVENT'       // Events
  | 'TECHNICAL'   // Technical terms (system, API, function)
  | 'FUNCTION'    // Function names (authenticate, process)
  | 'CLASS'       // Class names (UserService)
  | 'VARIABLE'    // Variable names
  | 'TYPE';       // Type names
```

---

#### ModalOperator

Requirement strength indicator.

```typescript
interface ModalOperator {
  id: string;                       // Unique: "modal-0", "modal-1", ...
  modality: ModalityType;
  text: string;                     // "must", "should", "may", "cannot"
  from: number;
  to: number;
  scope: string;                    // What this modal applies to
}

type ModalityType =
  | 'certainty'     // must, will, always, shall
  | 'possibility'   // may, might, could, possibly
  | 'necessity'     // should, ought to, recommended
  | 'prohibition';  // must not, cannot, shall not, forbidden
```

---

#### TypedHole

Incomplete specification marker.

```typescript
interface TypedHole {
  id: string;                       // Unique: "hole-0", "hole-1", ...
  identifier: string;               // "H1", "AuthMethod", etc.
  kind: HoleKind;
  status: HoleStatus;
  typeHint: string;                 // Expected type (e.g., "???OAuthProvider")
  description?: string;             // What needs to be filled
  confidence?: number;
  evidence?: string[];              // Why this is a hole
  pos?: number;                     // Position in document
  provenance?: Provenance;
  dependencies?: HoleDependencies;
  constraints?: string[];           // Constraint IDs
  solutionSpace?: SolutionSpace;
  acceptanceCriteria?: AcceptanceCriterion[];
}

type HoleKind =
  | 'intent'           // High-level goal/intention
  | 'signature'        // Function/API signature
  | 'effect'           // Side effect specification
  | 'assertion'        // Pre/postcondition
  | 'implementation';  // Implementation detail

type HoleStatus =
  | 'unresolved'
  | 'in_progress'
  | 'resolved';

interface HoleDependencies {
  blocks: string[];           // Hole IDs blocked by this hole
  blockedBy: string[];        // Hole IDs blocking this hole
  dependsOn?: string[];       // Hole IDs this depends on
}

interface SolutionSpace {
  narrowed: boolean;
  refinements: Refinement[];
  estimatedOptions?: number;
  reductionPercentage?: number;
}

interface Refinement {
  source: 'user' | 'ai' | 'constraint';
  description: string;
  confidence?: number;
}

interface AcceptanceCriterion {
  criterion: string;
  satisfied: boolean;
}

interface Provenance {
  source: 'explicit' | 'inferred';
  createdAt: string;           // ISO 8601
  createdBy: 'user' | 'system';
}
```

---

#### Constraint

Requirement constraint (temporal, type, value).

```typescript
interface Constraint {
  id: string;                       // Unique: "constraint-0", ...
  type: ConstraintType;
  severity: ConstraintSeverity;
  description: string;
  appliesTo: string[];              // Entity/hole IDs
  expression: string;               // Constraint expression
  from?: number;                    // Position in document
  to?: number;
}

type ConstraintType =
  | 'temporal'          // when, if, before, after, during, while
  | 'return_constraint' // return type, output format
  | 'type_constraint'   // type requirements
  | 'value_constraint'  // value ranges, comparisons
  | 'position'          // at index, first, last
  | 'semantic';         // General semantic constraint

type ConstraintSeverity =
  | 'error'      // Must satisfy
  | 'warning'    // Should satisfy
  | 'info';      // Nice to satisfy
```

---

#### Ambiguity

Underspecified or ambiguous requirement.

```typescript
interface Ambiguity {
  id: string;                       // Unique: "ambiguity-0", ...
  reason: string;                   // Why this is ambiguous
  from: number;
  to: number;
  suggestions: string[];            // How to resolve
}
```

---

#### Contradiction

Conflicting requirements.

```typescript
interface Contradiction {
  id: string;                       // Unique: "contradiction-0", ...
  conflicts: string[];              // Conflicting statement IDs
  reason: string;
  severity: 'error' | 'warning';
}
```

---

#### Relationship

Relationship between entities.

```typescript
interface Relationship {
  id: string;                       // Unique: "rel-0", ...
  from: string;                     // Entity ID
  to: string;                       // Entity ID
  type: RelationshipType;
  confidence: number;
}

type RelationshipType =
  | 'calls'           // Function calls another
  | 'uses'            // Uses another entity
  | 'depends_on'      // Depends on another entity
  | 'contains'        // Contains another entity
  | 'is_a'            // Is a type of another entity
  | 'has_a';          // Has a relationship with another
```

---

#### Effect

Side effect specification.

```typescript
interface Effect {
  id: string;
  type: EffectType;
  description: string;
  from?: number;
  to?: number;
}

type EffectType =
  | 'io'              // I/O operation
  | 'state_change'    // State modification
  | 'network'         // Network call
  | 'file_system'     // File system access
  | 'database';       // Database operation
```

---

#### Assertion

Pre/postcondition or invariant.

```typescript
interface Assertion {
  id: string;
  type: AssertionType;
  expression: string;
  from?: number;
  to?: number;
}

type AssertionType =
  | 'precondition'
  | 'postcondition'
  | 'invariant';
```

---

## 2. Zustand Store Structure

### 2.1 Store Shape

**File**: `frontend/src/lib/ics/store.ts`

```typescript
interface ICSStore {
  // === Document State ===
  specification: ProseMirrorNode | null;
  specificationText: string;

  // === Semantic Analysis ===
  semanticAnalysis: SemanticAnalysis | null;
  isAnalyzing: boolean;
  analysisError: string | null;

  // === Holes & Constraints ===
  holes: Map<string, TypedHole>;
  constraints: Map<string, Constraint>;
  selectedHole: string | null;

  // === UI State ===
  layout: LayoutConfig;
  panelVisibility: PanelVisibility;
  activeTab: 'natural-language' | 'ir' | 'code' | 'split';
  theme: 'light' | 'dark';

  // === Actions ===
  // Document
  setSpecification: (node: ProseMirrorNode | null) => void;
  setSpecificationText: (text: string) => void;

  // Analysis
  setSemanticAnalysis: (analysis: SemanticAnalysis | null) => void;
  setIsAnalyzing: (analyzing: boolean) => void;
  setAnalysisError: (error: string | null) => void;

  // Holes
  addHole: (hole: TypedHole) => void;
  updateHole: (id: string, updates: Partial<TypedHole>) => void;
  removeHole: (id: string) => void;
  selectHole: (id: string | null) => void;
  resolveHole: (id: string, refinement: Refinement) => void;

  // Constraints
  addConstraint: (constraint: Constraint) => void;
  updateConstraint: (id: string, updates: Partial<Constraint>) => void;
  removeConstraint: (id: string) => void;
  propagateConstraints: (fromHoleId: string, toHoleIds: string[]) => void;

  // UI
  setLayout: (layout: Partial<LayoutConfig>) => void;
  togglePanel: (panel: keyof PanelVisibility) => void;
  setActiveTab: (tab: ICSStore['activeTab']) => void;
  setTheme: (theme: 'light' | 'dark') => void;
}
```

### 2.2 Layout Configuration

```typescript
interface LayoutConfig {
  leftPanelWidth: number;         // px, default: 300
  rightPanelWidth: number;        // px, default: 400
  inspectorHeight: number;        // px, default: 300
  chatHeight: number;             // px, default: 300
}
```

### 2.3 Panel Visibility

```typescript
interface PanelVisibility {
  fileExplorer: boolean;          // default: true
  symbolsPanel: boolean;          // default: true
  inspector: boolean;             // default: true
  chat: boolean;                  // default: false (Phase 2)
  terminal: boolean;              // default: false (future)
}
```

---

## 3. Actions

### 3.1 Document Actions

#### setSpecification
```typescript
setSpecification: (node: ProseMirrorNode | null) => {
  set({ specification: node });
}
```

#### setSpecificationText
```typescript
setSpecificationText: (text: string) => {
  set({ specificationText: text });
}
```

---

### 3.2 Analysis Actions

#### setSemanticAnalysis
```typescript
setSemanticAnalysis: (analysis: SemanticAnalysis | null) => {
  set({
    semanticAnalysis: analysis,
    isAnalyzing: false,
    analysisError: null,
  });

  // Update holes map from analysis
  if (analysis?.typedHoles) {
    const holesMap = new Map<string, TypedHole>();
    analysis.typedHoles.forEach(hole => {
      holesMap.set(hole.id, hole);
    });
    set({ holes: holesMap });
  }

  // Update constraints map from analysis
  if (analysis?.constraints) {
    const constraintsMap = new Map<string, Constraint>();
    analysis.constraints.forEach(constraint => {
      constraintsMap.set(constraint.id, constraint);
    });
    set({ constraints: constraintsMap });
  }
}
```

#### setIsAnalyzing
```typescript
setIsAnalyzing: (analyzing: boolean) => {
  set({ isAnalyzing: analyzing });
  if (analyzing) {
    set({ analysisError: null });
  }
}
```

#### setAnalysisError
```typescript
setAnalysisError: (error: string | null) => {
  set({
    analysisError: error,
    isAnalyzing: false,
  });
}
```

---

### 3.3 Hole Actions

#### resolveHole
```typescript
resolveHole: (id: string, refinement: Refinement) => {
  const { holes, propagateConstraints } = get();
  const hole = holes.get(id);

  if (!hole) {
    throw new Error(`Hole ${id} not found`);
  }

  // Validate refinement (basic)
  if (!refinement.description || refinement.description.trim().length === 0) {
    throw new Error('Refinement description cannot be empty');
  }

  // Update hole status
  const updatedHole: TypedHole = {
    ...hole,
    status: 'resolved',
    solutionSpace: {
      ...hole.solutionSpace,
      narrowed: true,
      refinements: [...(hole.solutionSpace?.refinements || []), refinement],
    },
  };

  const newHoles = new Map(holes);
  newHoles.set(id, updatedHole);
  set({ holes: newHoles });

  // Propagate constraints to dependent holes
  if (hole.dependencies?.blocks && hole.dependencies.blocks.length > 0) {
    propagateConstraints(id, hole.dependencies.blocks);
  }
}
```

#### propagateConstraints
```typescript
propagateConstraints: (fromHoleId: string, toHoleIds: string[]) => {
  const { holes, constraints, addConstraint } = get();
  const fromHole = holes.get(fromHoleId);

  if (!fromHole) return;

  toHoleIds.forEach(toHoleId => {
    const toHole = holes.get(toHoleId);
    if (!toHole) return;

    // Create new constraint propagated from resolved hole
    const newConstraint: Constraint = {
      id: `constraint-propagated-${Date.now()}-${Math.random()}`,
      type: 'semantic',  // TODO: Infer from refinement
      severity: 'error',
      description: `Constraint from ${fromHole.identifier}: ${fromHole.solutionSpace?.refinements[0]?.description || 'resolved'}`,
      appliesTo: [toHoleId],
      expression: fromHole.solutionSpace?.refinements[0]?.description || '',
    };

    addConstraint(newConstraint);

    // Add constraint to hole
    const updatedToHole: TypedHole = {
      ...toHole,
      constraints: [...(toHole.constraints || []), newConstraint.id],
      solutionSpace: {
        ...toHole.solutionSpace,
        narrowed: true,
        // TODO: Recalculate solution space reduction
      },
    };

    const newHoles = new Map(holes);
    newHoles.set(toHoleId, updatedToHole);
    set({ holes: newHoles });
  });
}
```

---

## 4. Persistence

### 4.1 Persisted State

**Strategy**: Use Zustand `persist` middleware with `localStorage`.

**Persisted**:
- ✅ `layout`: Layout configuration (panel sizes)
- ✅ `panelVisibility`: Which panels are open/closed
- ✅ `activeTab`: Last active tab
- ✅ `theme`: Light/dark theme preference

**NOT Persisted** (session only):
- ❌ `specification`: ProseMirror document (too large)
- ❌ `semanticAnalysis`: Analysis results (regenerated)
- ❌ `holes`: Typed holes (from analysis)
- ❌ `constraints`: Constraints (from analysis)
- ❌ `selectedHole`: Selection state

### 4.2 Implementation

```typescript
import { create } from 'zustand';
import { persist } from 'zustand/middleware';

const useICSStore = create<ICSStore>()(
  persist(
    (set, get) => ({
      // ... state and actions
    }),
    {
      name: 'ics-storage',
      partialize: (state) => ({
        layout: state.layout,
        panelVisibility: state.panelVisibility,
        activeTab: state.activeTab,
        theme: state.theme,
      }),
    }
  )
);
```

---

## 5. State Machines

**Reference**: See `ics-spec-v1.md` §3 for complete state machine diagrams.

### 5.1 Analysis State Machine

```
States: idle → analyzing → success | error
```

**Managed by**:
- `isAnalyzing`: boolean
- `analysisError`: string | null
- `semanticAnalysis`: SemanticAnalysis | null

**Transitions**:
```typescript
// Start analysis
set({ isAnalyzing: true, analysisError: null });

// Success
set({ semanticAnalysis: result, isAnalyzing: false });

// Error
set({ analysisError: errorMessage, isAnalyzing: false });
```

---

## 6. Constraints

### 6.1 Type Constraints

- **TC1**: All state must be typed (no `any`)
- **TC2**: TypeScript strict mode enabled
- **TC3**: Pydantic validation on backend types

### 6.2 Behavioral Constraints

- **BC1**: Store updates are synchronous (Zustand guarantee)
- **BC2**: Actions are idempotent where possible
- **BC3**: State transitions are logged (via devtools middleware)

### 6.3 Performance Constraints

- **PC1**: Store updates < 16ms (no blocking)
- **PC2**: Persist operations debounced (300ms)
- **PC3**: Map operations O(1) lookup (holes, constraints)

---

**End of State Management Specification**

**Next**: `ics-editor-spec.md` (ProseMirror integration)
