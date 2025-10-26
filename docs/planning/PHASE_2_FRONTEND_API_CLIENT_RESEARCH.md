# Phase 2 Frontend API Client Research

**Date**: 2025-10-26
**Issue**: lift-sys-376
**Status**: Research Complete
**Complexity**: Low (2-3 hours)

## Executive Summary

The backend IR has been updated with Phase 2 NLP fields (Constraint enhancements and RelationshipClause). This research identifies exactly what frontend changes are needed to properly deserialize and display these new fields.

**Good news**: The frontend TypeScript interfaces already have most of the required fields! Only minor updates needed.

## Backend Changes Completed

### 1. Constraint Schema (Phase 2 Enhancement)

**File**: `lift_sys/ir/constraints.py`

**New fields added to all Constraint classes**:
```python
id: str = field(default_factory=lambda: str(uuid.uuid4()))
applies_to: list[str] = field(default_factory=list)  # Hole IDs
source: str = ""  # Origin of constraint
impact: str = ""  # Impact description
locked: bool = False  # Design decision locked?
metadata: dict[str, Any] = field(default_factory=dict)
```

**Serialization** (Line 144-156 in constraints.py):
```python
def to_dict(self) -> dict[str, Any]:
    return {
        "type": self.type.value,
        "description": self.description,
        "severity": self.severity.value,
        "id": self.id,
        "appliesTo": self.applies_to,  # ✅ Frontend camelCase
        "source": self.source,
        "impact": self.impact,
        "locked": self.locked,
        "metadata": self.metadata,
    }
```

**Constraint types**:
- `ReturnConstraint`: Additional fields `value_name`, `requirement`
- `LoopBehaviorConstraint`: Additional fields `search_type`, `requirement`, `loop_variable`
- `PositionConstraint`: Additional fields `elements`, `requirement`, `min_distance`, `max_distance`

### 2. RelationshipClause (New in Phase 2)

**File**: `lift_sys/ir/models.py` (Lines 230-284)

**Structure**:
```python
@dataclass(slots=True)
class RelationshipClause:
    from_entity: str
    to_entity: str
    relationship_type: str
    confidence: float = 0.8
    description: str = ""
    holes: list[TypedHole] = field(default_factory=list)
    provenance: Provenance | None = None
```

**Serialization** (Line 273-284):
```python
def to_dict(self) -> dict[str, object]:
    result = {
        "from_entity": self.from_entity,
        "to_entity": self.to_entity,
        "relationship_type": self.relationship_type,
        "confidence": self.confidence,
        "description": self.description,
        "holes": [hole.to_dict() for hole in self.holes],
    }
    if self.provenance:
        result["provenance"] = self.provenance.to_dict()
    return result
```

**Added to IR** (models.py Line 311):
```python
class IntermediateRepresentation:
    relationships: list[RelationshipClause] = field(default_factory=list)
```

**Included in IR serialization** (models.py Line 346-347):
```python
if self.relationships:
    result["relationships"] = [rel.to_dict() for rel in self.relationships]
```

## Frontend Current State

### 1. Type Definitions

**File**: `frontend/src/types/ics/semantic.ts`

**Constraint interface (Lines 117-127)** - ALREADY HAS ALL FIELDS! ✅
```typescript
export interface Constraint {
  id: string;
  type: ConstraintType;
  description: string;
  severity: ConstraintSeverity;
  appliesTo: string[];  // ✅ Already has this
  source: string;       // ✅ Already has this
  impact: string;       // ✅ Already has this
  locked: boolean;      // ✅ Already has this
  metadata?: Record<string, unknown>;  // ✅ Already has this
}
```

**Relationship interface (Lines 145-154)** - PARTIAL MATCH
```typescript
export interface Relationship {
  id: string;
  type: RelationshipType;  // ⚠️ Different from backend's relationship_type
  source: string;  // ⚠️ Backend uses from_entity
  target: string;  // ⚠️ Backend uses to_entity
  text: string;    // ⚠️ Backend uses description
  from: number;    // ❌ Backend doesn't have position fields
  to: number;      // ❌ Backend doesn't have position fields
  confidence: number;  // ✅ Matches
}
```

**RelationshipType enum (Lines 49-54)**:
```typescript
export type RelationshipType =
  | 'causal'
  | 'temporal'
  | 'conditional'
  | 'dependency';
```

### 2. API Client

**File**: `frontend/src/lib/ics/api.ts`

**Current structure** (Lines 5-44):
- Uses `SemanticAnalysis` type from `@/types/ics/semantic`
- Makes POST to `/ics/analyze`
- Returns `data as SemanticAnalysis`

**No modifications needed** - already returns full SemanticAnalysis

### 3. SemanticAnalysis Interface

**File**: `frontend/src/types/ics/semantic.ts` (Lines 218-229)

```typescript
export interface SemanticAnalysis {
  entities: Entity[];
  relationships: Relationship[];  // ✅ Already has this
  modalOperators: ModalOperator[];
  constraints: Constraint[];      // ✅ Already has this
  effects: Effect[];
  assertions: Assertion[];
  ambiguities: Ambiguity[];
  contradictions: Contradiction[];
  typedHoles: TypedHole[];
  confidenceScores: Record<string, number>;
}
```

## Discrepancies and Required Changes

### Issue 1: Relationship Interface Mismatch

**Problem**: Frontend `Relationship` interface doesn't match backend `RelationshipClause`

**Backend fields**:
```python
from_entity: str
to_entity: str
relationship_type: str
confidence: float
description: str
holes: list[TypedHole]
provenance: Provenance | None
```

**Frontend fields** (current):
```typescript
id: string
type: RelationshipType
source: string
target: string
text: string
from: number
to: number
confidence: number
```

**Analysis**: The frontend's `Relationship` interface appears to be designed for **NLP-detected relationships in text** (with position offsets), while the backend's `RelationshipClause` represents **semantic relationships in IR** (without position info).

**Two options**:

#### Option A: Separate Types (RECOMMENDED)
Create two distinct types:
1. `TextRelationship` - For NLP position-based relationships (current frontend type)
2. `IRRelationship` - For IR semantic relationships (backend type)

#### Option B: Merge Types
Extend frontend `Relationship` to support both use cases (position fields optional)

### Issue 2: ICS API Response Structure

**Backend API** (`lift_sys/api/routes/ics.py` Line 133):
```python
analysis = pipeline.analyze(request.text)
return AnalyzeResponse(**analysis)
```

**Backend pipeline output** (`lift_sys/nlp/pipeline.py` Line 128-144):
```python
return {
    "entities": entities,
    "relationships": relationships,  # ⚠️ These are NLP relationships
    "modalOperators": modals,
    "constraints": constraints,
    "effects": [],
    "assertions": [],
    "ambiguities": ambiguities,
    "contradictions": contradictions,
    "typedHoles": typed_holes,
    "confidenceScores": confidence_scores,
}
```

**Note**: The ICS API returns **NLP-extracted relationships** from text analysis, NOT IR RelationshipClauses. RelationshipClauses only appear in IR responses from `/spec-sessions` endpoints.

## Required Frontend Changes

### Change 1: Update Relationship Type (if needed)

**File**: `frontend/src/types/ics/semantic.ts`

**Option A: Create IRRelationship type** (RECOMMENDED):
```typescript
/**
 * IR-level relationship between entities (from RelationshipClause)
 */
export interface IRRelationship {
  fromEntity: string;
  toEntity: string;
  relationshipType: string;
  confidence: number;
  description: string;
  holes?: TypedHole[];
  provenance?: Provenance;
}

/**
 * NLP-detected relationship in text (existing)
 */
export interface Relationship {
  id: string;
  type: RelationshipType;
  source: string;  // Entity ID
  target: string;  // Entity ID
  text: string;
  from: number;
  to: number;
  confidence: number;
}
```

**Update SemanticAnalysis**:
```typescript
export interface SemanticAnalysis {
  entities: Entity[];
  relationships: Relationship[];  // Keep for NLP relationships
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

**Option B: Make Relationship support both**:
```typescript
export interface Relationship {
  // NLP fields (optional for IR)
  id?: string;
  from?: number;
  to?: number;
  text?: string;

  // IR fields (optional for NLP)
  fromEntity?: string;
  toEntity?: string;

  // Common fields
  type?: RelationshipType;
  relationshipType?: string;  // IR uses string, not enum
  source?: string;  // Entity ID or from_entity
  target?: string;  // Entity ID or to_entity
  confidence: number;
  description?: string;
  holes?: TypedHole[];
  provenance?: Provenance;
}
```

### Change 2: Add IR Types for Session Responses

**File**: `frontend/src/types/sessions.ts`

Currently, `IRResponse` interface (Line 54-57) uses `Record<string, unknown>`:
```typescript
export interface IRResponse {
  ir: Record<string, unknown>;
  metadata: Record<string, unknown>;
}
```

**Add typed IR interface**:
```typescript
export interface IRRelationship {
  from_entity: string;
  to_entity: string;
  relationship_type: string;
  confidence: number;
  description: string;
  holes?: TypedHole[];
  provenance?: Provenance;
}

export interface IntermediateRepresentation {
  intent: {
    summary: string;
    rationale?: string;
    holes?: TypedHole[];
    provenance?: Provenance;
  };
  signature: {
    name: string;
    parameters: Array<{
      name: string;
      type_hint: string;
      description?: string;
      provenance?: Provenance;
    }>;
    returns?: string;
    holes?: TypedHole[];
    provenance?: Provenance;
  };
  effects?: Array<{
    description: string;
    holes?: TypedHole[];
    provenance?: Provenance;
  }>;
  assertions?: Array<{
    predicate: string;
    rationale?: string;
    holes?: TypedHole[];
    provenance?: Provenance;
  }>;
  relationships?: IRRelationship[];  // ✅ Phase 2 addition
  metadata?: {
    source_path?: string;
    language?: string;
    origin?: string;
    evidence?: Array<Record<string, unknown>>;
  };
  constraints?: Constraint[];  // ✅ Uses existing Constraint type
}
```

**Update IRResponse**:
```typescript
export interface IRResponse {
  ir: IntermediateRepresentation;  // ✅ Now typed
  metadata: Record<string, unknown>;
}
```

### Change 3: Update IRDraft Type

**File**: `frontend/src/types/sessions.ts` (Line 5-13)

```typescript
export interface IRDraft {
  version: number;
  ir: IntermediateRepresentation;  // ✅ Change from Record<string, unknown>
  validation_status: "pending" | "incomplete" | "valid" | "contradictory";
  ambiguities: string[];
  smt_results: Array<Record<string, unknown>>;
  created_at: string;
  metadata: Record<string, unknown>;
}
```

### Change 4: Verify Constraint Deserialization

**No changes needed!** The frontend's `Constraint` interface already matches all backend fields perfectly.

**Verify in**:
- `frontend/src/types/ics/semantic.ts` (Lines 117-127) ✅
- API response from `/ics/analyze` already includes constraints ✅

### Change 5: Update Components Using Relationships (if needed)

**Files to check**:
- `frontend/src/components/ics/SymbolsPanel.tsx`
- `frontend/src/components/ics/SemanticTooltip.tsx`
- `frontend/src/components/ics/HoleInspector.tsx`
- `frontend/src/views/IdeView.tsx`

**Action**: Verify these components handle relationships correctly. If they use `Relationship` type and expect IR relationships, update them to use `IRRelationship`.

## Implementation Steps

### Step 1: Update Type Definitions (1 hour)

1. **In `frontend/src/types/ics/semantic.ts`**:
   - Add `IRRelationship` interface for IR-level relationships
   - Keep existing `Relationship` for NLP relationships
   - Add comprehensive JSDoc comments

2. **In `frontend/src/types/sessions.ts`**:
   - Add `IntermediateRepresentation` interface
   - Update `IRResponse.ir` type from `Record<string, unknown>` to `IntermediateRepresentation`
   - Update `IRDraft.ir` type similarly

3. **Verify type imports**:
   - Check if any components import `TypedHole`, `Provenance`, `Constraint` from sessions.ts
   - Ensure imports come from correct location (semantic.ts)

### Step 2: Verify API Client (30 minutes)

1. **In `frontend/src/lib/ics/api.ts`**:
   - No changes needed (already returns `SemanticAnalysis`)
   - Add JSDoc clarifying that `relationships` are NLP-detected, not IR

2. **In `frontend/src/lib/sessionApi.ts`**:
   - Verify `finalizeSession()` return type uses updated `IRResponse`
   - Verify `getSession()` return type uses updated `PromptSession` (which has IRDraft)

### Step 3: Update Components (1 hour)

1. **Search for `Relationship` usage**:
   ```bash
   grep -r "Relationship" frontend/src/components/
   grep -r "relationships" frontend/src/components/
   ```

2. **For each component**:
   - Determine if it uses NLP relationships or IR relationships
   - Update type annotations accordingly
   - Test rendering with new fields

3. **HoleInspector.tsx** (Lines 146-173):
   - Already handles constraints correctly
   - Verify constraint display shows new fields (source, impact, locked)

### Step 4: Add Display for New Fields (30 minutes)

1. **In `frontend/src/components/ics/HoleInspector.tsx`**:
   - Update constraint display to show `source`, `impact`, `locked` if present
   - Example:
     ```tsx
     {hole.constraints && hole.constraints.length > 0 ? (
       hole.constraints.map((constraint, index) => (
         <div key={index} className="text-xs p-2 rounded border border-border">
           <p className="font-medium">{constraint.description}</p>
           {constraint.source && (
             <p className="text-muted-foreground">Source: {constraint.source}</p>
           )}
           {constraint.impact && (
             <p className="text-muted-foreground">Impact: {constraint.impact}</p>
           )}
           {constraint.locked && (
             <Badge variant="outline" className="mt-1">Locked</Badge>
           )}
         </div>
       ))
     ) : (
       <p className="text-xs text-muted-foreground">No constraints applied</p>
     )}
     ```

2. **Create RelationshipView component** (optional):
   - If IR relationships need visualization
   - Display from_entity → to_entity with relationship_type
   - Show confidence, description

### Step 5: Testing (30 minutes)

1. **Unit tests**:
   - Add test for deserializing Constraint with new fields
   - Add test for deserializing IRRelationship
   - Verify camelCase conversion (appliesTo ↔ applies_to)

2. **Integration tests**:
   - Test `/ics/analyze` response with new constraint fields
   - Test `/spec-sessions/{id}/finalize` with relationships

3. **Manual testing**:
   - Create session with constraints
   - Verify constraint display in HoleInspector
   - Verify IR response includes relationships (if backend populates them)

## Files Modified Summary

### Type Definitions
- **`frontend/src/types/ics/semantic.ts`** (MODIFY)
  - Add `IRRelationship` interface
  - Add JSDoc to clarify `Relationship` vs `IRRelationship`
  - Lines affected: Insert after line 154

- **`frontend/src/types/sessions.ts`** (MODIFY)
  - Add `IntermediateRepresentation` interface
  - Update `IRResponse.ir` type
  - Update `IRDraft.ir` type
  - Lines affected: 5-13, 54-57, insert new interface

### Components (VERIFY, likely no changes)
- **`frontend/src/components/ics/HoleInspector.tsx`** (VERIFY)
  - Constraint display already works (lines 161-173)
  - Optionally enhance to show source, impact, locked

- **`frontend/src/components/ics/SymbolsPanel.tsx`** (VERIFY)
  - Check if uses relationships

- **`frontend/src/components/ics/SemanticTooltip.tsx`** (VERIFY)
  - Check if uses constraints/relationships

### API Clients (NO CHANGES)
- **`frontend/src/lib/ics/api.ts`** (NO CHANGE)
  - Already works correctly

- **`frontend/src/lib/sessionApi.ts`** (NO CHANGE)
  - Type updates propagate automatically

## Estimated Complexity

**Total: 2-3 hours**

- Type definitions: 1 hour
- API client verification: 30 minutes
- Component updates: 1 hour
- Testing: 30 minutes

**Risk level**: LOW
- Constraint interface already matches backend ✅
- Only need to add IRRelationship type
- Backend serializes to camelCase correctly ✅
- No breaking changes to existing code

## Next Steps

1. **Implement type definitions** (Step 1)
2. **Verify API clients** (Step 2)
3. **Update components if needed** (Step 3)
4. **Add optional enhanced displays** (Step 4)
5. **Test thoroughly** (Step 5)
6. **Create PR** with clear description of Phase 2 changes

## References

- Backend Constraint: `lift_sys/ir/constraints.py` (Lines 96-156)
- Backend RelationshipClause: `lift_sys/ir/models.py` (Lines 230-284)
- Frontend Constraint: `frontend/src/types/ics/semantic.ts` (Lines 117-127)
- Frontend Relationship: `frontend/src/types/ics/semantic.ts` (Lines 145-154)
- ICS API: `lift_sys/api/routes/ics.py` (Lines 65-141)
- Session API: `frontend/src/lib/sessionApi.ts`
