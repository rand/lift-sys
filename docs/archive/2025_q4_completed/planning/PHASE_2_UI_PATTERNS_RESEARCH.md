# Phase 2 UI Patterns Research: Semantic Relationships Display

**Date**: 2025-10-26
**Status**: Research Complete
**Task**: lift-sys-377
**Context**: ICS Phase 2 semantic analysis enhancement - UI patterns for relationships/effects/assertions

---

## Executive Summary

This research explores UI/UX patterns for displaying semantic relationships, enhanced effects, and enhanced assertions in the ICS Phase 2 frontend. The goal is to visualize complex entity relationships extracted from natural language specifications with strong accessibility, clear visual encoding, and seamless integration with existing ICS components.

**Key Recommendations**:
1. **List-based relationship view** with color coding and confidence badges (immediate implementation)
2. **Interactive graph visualization** using ReactFlow/Visx for complex networks (future enhancement)
3. **Dual encoding** (color + icons/patterns) for WCAG 2.1 AA compliance
4. **Inline relationship highlights** in ProseMirror editor
5. **Expandable relationship inspector panel** similar to HoleInspector pattern

**Estimated Implementation**: 8-12 hours for core features, 16-20 hours with graph visualization

---

## Phase 2 Semantic Data Structures

### 1. Relationships (Primary Focus)

**Backend**: `lift_sys/ir/models.py` - `RelationshipClause`
```python
@dataclass
class RelationshipClause:
    from_entity: str          # Source entity
    to_entity: str            # Target entity
    relationship_type: str    # USES, PRODUCES, DEPENDS_ON, MODIFIES, PRECEDES, etc.
    confidence: float         # 0.0-1.0
    description: str          # Human-readable description
```

**Frontend**: `frontend/src/types/ics/semantic.ts` - `Relationship`
```typescript
interface Relationship {
  id: string;
  type: RelationshipType;    // 'causal' | 'temporal' | 'conditional' | 'dependency'
  source: string;            // Entity ID
  target: string;            // Entity ID
  text: string;              // Original text
  from: number;              // Character position
  to: number;
  confidence: number;        // 0.0-1.0
}
```

**Relationship Types**:
- **USES**: Entity A uses entity B
- **PRODUCES**: Entity A produces entity B
- **DEPENDS_ON**: Entity A depends on entity B
- **MODIFIES**: Entity A modifies entity B
- **PRECEDES**: Entity A happens before entity B (temporal)
- **OPERATES_ON**: Entity A operates on entity B
- **CONTAINS**: Entity A contains entity B (composition)
- **CAUSES**: Entity A causes entity B (causal)

### 2. Enhanced Effects

**Backend**: `lift_sys/ir/models.py` - `EffectClause`
```python
@dataclass
class EffectClause:
    action: str               # Structured action
    target: str               # What is affected
    type: EffectType          # side_effect, io_effect, state_change
    description: str
```

**Frontend**: `frontend/src/types/ics/semantic.ts` - `Effect`
```typescript
interface Effect {
  id: string;
  description: string;
  from: number;
  to: number;
  type: 'side_effect' | 'io_effect' | 'state_change';
}
```

### 3. Enhanced Assertions

**Backend**: `lift_sys/ir/models.py` - `AssertClause`
```python
@dataclass
class AssertClause:
    predicate: str            # Structured predicate
    operator: str             # Comparison operator
    value: str                # Expected value
    type: AssertionType       # precondition, postcondition, invariant
```

**Frontend**: `frontend/src/types/ics/semantic.ts` - `Assertion`
```typescript
interface Assertion {
  id: string;
  predicate: string;
  from: number;
  to: number;
  type: 'precondition' | 'postcondition' | 'invariant';
  rationale?: string;
}
```

---

## Existing Frontend Architecture Analysis

### Current Semantic Display Components

#### 1. **SemanticEditor.tsx** - Core editor with inline highlighting
- **Pattern**: ProseMirror decorations for inline semantic elements
- **Highlights**: Entities, constraints, holes, ambiguities, contradictions, modals
- **Interaction**: Hover tooltips via `handleMouseMove`, clickable holes
- **Relationships**: Currently has CSS class `.relationship` (lines 147-156 in ics.css) but NO implementation
- **Opportunity**: Extend decoration system to highlight relationship spans inline

#### 2. **SemanticTooltip.tsx** - Hover tooltip system
- **Pattern**: Tooltip per element type (entity, constraint, hole, ambiguity, contradiction, modal)
- **Components**: `EntityTooltip`, `ConstraintTooltip`, `HoleTooltip`, etc.
- **Missing**: `RelationshipTooltip`, `EffectTooltip`, `AssertionTooltip`
- **Opportunity**: Add new tooltip types following existing pattern

#### 3. **HoleInspector.tsx** - Detailed panel for selected holes
- **Pattern**: Right sidebar with expandable sections
- **Sections**: Dependencies, Constraints, Solution Space, Acceptance Criteria, AI Suggestions
- **Features**: Collapsible sections, badges, status icons, confidence display
- **Missing**: Relationship display in dependencies
- **Opportunity**: Create `RelationshipInspector` following same collapsible pattern

### Available shadcn/ui Components

**Already installed** (from `/Users/rand/src/lift-sys/frontend/src/components/ui/`):
- ✅ `badge.tsx` - For confidence scores, relationship types
- ✅ `card.tsx` - For relationship cards/groupings
- ✅ `accordion.tsx` - For collapsible relationship sections
- ✅ `table.tsx` - For tabular relationship display
- ✅ `tooltip.tsx` - For inline hover details
- ✅ `scroll-area.tsx` - For scrollable relationship lists
- ✅ `separator.tsx` - For visual separation
- ✅ `progress.tsx` - For confidence visualization

**Not available** (would need custom implementation):
- ❌ Graph/network visualization components
- ❌ Force-directed layout components
- ❌ Tree/hierarchy components
- ❌ Flowchart/diagram components

### Current Visual Encoding (from ics.css)

**Color palette established**:
- Entities: Blues (#3b82f6), purples (#8b5cf6), teals (#14b8a6, #06b6d4)
- Constraints: Orange (#f97316)
- Holes: Orange (#fb923c) with dashed borders
- Relationships (defined but unused):
  - Causal: Purple (#8b5cf6)
  - Temporal: Cyan (#06b6d4)
  - Conditional: Amber (#f59e0b)
  - Dependency: Teal (#14b8a6)

**Confidence display pattern**:
- Green (#22c55e) for high confidence
- Percentage display (e.g., "85%")
- Used in `EntityTooltip`, `HoleTooltip`

---

## Recommended UI Patterns

### Pattern 1: List-Based Relationship View (Immediate Implementation)

**Rationale**: Simple, accessible, integrates with existing components, no external dependencies.

**Design**:
```typescript
// Component structure
<RelationshipPanel>
  <ScrollArea>
    {relationships.map(rel => (
      <RelationshipCard
        key={rel.id}
        relationship={rel}
        entities={entities}
        onClick={() => selectRelationship(rel.id)}
      />
    ))}
  </ScrollArea>
</RelationshipPanel>

// RelationshipCard visual structure
[Entity A] --[RELATIONSHIP_TYPE]--> [Entity B]
         Confidence: 85% | Description: "validates operates on email"
```

**Visual Encoding**:
- **Relationship type**: Badge with color coding
  - USES: Blue badge
  - PRODUCES: Green badge
  - DEPENDS_ON: Teal badge
  - MODIFIES: Orange badge
  - PRECEDES: Cyan badge
  - OPERATES_ON: Purple badge
- **Confidence**: Progress bar + percentage (dual encoding)
  - High (>0.8): Green
  - Medium (0.5-0.8): Yellow
  - Low (<0.5): Orange
- **Entities**: Highlighted with entity type colors (existing palette)
- **Arrow direction**: Visual arrow (→) or directional icon

**Accessibility**:
- ARIA labels: "Relationship: validate operates on email, confidence 85%"
- Keyboard navigation: Tab through relationships, Enter to select
- Screen reader: Announces relationship type, entities, confidence
- Color + text: Relationship type shown as text + color-coded badge
- Focus indicators: 2px outline on focus (WCAG 2.4.7)

**Example UI**:
```
╔════════════════════════════════════════╗
║ Relationships (5)                      ║
╠════════════════════════════════════════╣
║ [validate] →OPERATES_ON→ [email]       ║
║ ▓▓▓▓▓▓▓▓░░ 85%                        ║
║ Validate operates on email input       ║
║                                        ║
║ [User] →MODIFIES→ [profile]           ║
║ ▓▓▓▓▓▓▓▓▓░ 92%                        ║
║ User modifies their profile            ║
║                                        ║
║ [report] →DEPENDS_ON→ [database]      ║
║ ▓▓▓▓▓▓░░░░ 67%                        ║
║ Report generation depends on database  ║
╚════════════════════════════════════════╝
```

**Implementation Steps**:
1. Create `RelationshipCard.tsx` component (1-2 hours)
2. Create `RelationshipPanel.tsx` container (1 hour)
3. Add relationship filtering/grouping (1 hour)
4. Integrate with ICS store and semantic analysis (1 hour)
5. Add click-to-highlight in editor (1 hour)
6. Accessibility testing and ARIA labels (1 hour)

**Total Estimate**: 6-8 hours

---

### Pattern 2: Inline Relationship Highlights (Editor Integration)

**Rationale**: Show relationships contextually in the specification text, consistent with existing entity/constraint highlighting.

**Design**:
- Extend ProseMirror decorations to highlight relationship spans
- Use existing `.relationship` CSS classes (already defined but unused)
- Hover to show tooltip with full relationship details

**Visual Encoding**:
```
"The system validates user email addresses"
           --------  ---- ----- ---------
           |         |    |     |
           v         v    v     v
        [validate] OPERATES_ON [email]
```

**CSS Enhancement** (extend existing `ics.css` lines 147-156):
```css
.relationship {
  position: relative;
  padding: 0 0.125rem;
  border-bottom: 2px dotted;
  cursor: help;
  transition: all 0.2s;
}

.relationship:hover {
  background: rgba(139, 92, 246, 0.1);
  border-bottom-style: solid;
}

/* Relationship type colors (already defined) */
.relationship-causal { border-bottom-color: #8b5cf6; }
.relationship-temporal { border-bottom-color: #06b6d4; }
.relationship-conditional { border-bottom-color: #f59e0b; }
.relationship-dependency { border-bottom-color: #14b8a6; }
.relationship-uses { border-bottom-color: #3b82f6; }
.relationship-produces { border-bottom-color: #22c55e; }
.relationship-modifies { border-bottom-color: #f97316; }
.relationship-operates { border-bottom-color: #a855f7; }
```

**Tooltip Enhancement** (add to `SemanticTooltip.tsx`):
```typescript
function RelationshipTooltip({ relationship, entities }: { relationship: Relationship; entities: Entity[] }) {
  const sourceEntity = entities.find(e => e.id === relationship.source);
  const targetEntity = entities.find(e => e.id === relationship.target);

  return (
    <div className="tooltip-content">
      <div className="tooltip-header">
        <span className="tooltip-badge">{relationship.type}</span>
        <span className="tooltip-confidence">{Math.round(relationship.confidence * 100)}%</span>
      </div>
      <div className="tooltip-body">
        <div className="tooltip-relationship-flow">
          <div className="tooltip-entity">
            <span className="entity-badge">{sourceEntity?.type}</span>
            {sourceEntity?.text}
          </div>
          <div className="tooltip-arrow">
            <ArrowRight className="h-4 w-4" />
            <span className="relationship-label">{relationship.type}</span>
          </div>
          <div className="tooltip-entity">
            <span className="entity-badge">{targetEntity?.type}</span>
            {targetEntity?.text}
          </div>
        </div>
        <div className="tooltip-hint">{relationship.text}</div>
      </div>
    </div>
  );
}
```

**Implementation Steps**:
1. Extend `createDecorationsPlugin` to handle relationships (2 hours)
2. Add relationship detection in `handleMouseMove` (1 hour)
3. Implement `RelationshipTooltip` component (1-2 hours)
4. Update CSS for relationship highlights (0.5 hour)
5. Test with real semantic analysis data (1 hour)

**Total Estimate**: 5-6 hours

---

### Pattern 3: Relationship Inspector Panel (Detailed View)

**Rationale**: Provide deep dive into selected relationship, similar to `HoleInspector`.

**Design**:
- Right sidebar panel (mirrors HoleInspector pattern)
- Triggered by clicking relationship in list or inline highlight
- Shows relationship details, connected entities, confidence breakdown

**Component Structure**:
```typescript
interface RelationshipInspectorProps {
  selectedRelationship: string | null;
  relationships: Relationship[];
  entities: Entity[];
}

function RelationshipInspector({ selectedRelationship, relationships, entities }: RelationshipInspectorProps) {
  const relationship = relationships.find(r => r.id === selectedRelationship);

  if (!relationship) {
    return <EmptyState icon={<GitBranch />} message="Select a relationship to inspect" />;
  }

  return (
    <ScrollArea>
      <div className="p-3 space-y-4">
        {/* Header */}
        <div className="space-y-2">
          <h3 className="text-lg font-bold">{relationship.type}</h3>
          <Badge variant="secondary">{Math.round(relationship.confidence * 100)}% confidence</Badge>
        </div>

        <Separator />

        {/* Flow Visualization */}
        <div className="relationship-flow">
          <EntityCard entity={sourceEntity} />
          <ArrowRight />
          <Badge>{relationship.type}</Badge>
          <ArrowRight />
          <EntityCard entity={targetEntity} />
        </div>

        <Separator />

        {/* Details */}
        <Accordion type="single" collapsible>
          <AccordionItem value="description">
            <AccordionTrigger>Description</AccordionTrigger>
            <AccordionContent>{relationship.text}</AccordionContent>
          </AccordionItem>

          <AccordionItem value="entities">
            <AccordionTrigger>Connected Entities</AccordionTrigger>
            <AccordionContent>
              <div className="space-y-2">
                <EntityDetails entity={sourceEntity} role="source" />
                <EntityDetails entity={targetEntity} role="target" />
              </div>
            </AccordionContent>
          </AccordionItem>

          <AccordionItem value="evidence">
            <AccordionTrigger>Evidence</AccordionTrigger>
            <AccordionContent>
              <div className="text-sm">
                <p>Position: {relationship.from}-{relationship.to}</p>
                <p>Text: "{relationship.text}"</p>
                <p>Confidence: {(relationship.confidence * 100).toFixed(1)}%</p>
              </div>
            </AccordionContent>
          </AccordionItem>
        </Accordion>
      </div>
    </ScrollArea>
  );
}
```

**Visual Layout**:
```
╔════════════════════════════════════════╗
║ Relationship Inspector                 ║
╠════════════════════════════════════════╣
║ OPERATES_ON                      85% ◎ ║
║                                        ║
║ ┌──────────┐    ┌──────────┐          ║
║ │ validate │ →  │  email   │          ║
║ │ FUNCTION │    │ VARIABLE │          ║
║ └──────────┘    └──────────┘          ║
║                                        ║
║ > Description                          ║
║   Validate operates on email input     ║
║                                        ║
║ > Connected Entities                   ║
║   Source: validate (FUNCTION)          ║
║   Target: email (VARIABLE)             ║
║                                        ║
║ > Evidence                             ║
║   Position: 12-35                      ║
║   Text: "validates user email"         ║
║   Confidence: 85.0%                    ║
╚════════════════════════════════════════╝
```

**Implementation Steps**:
1. Create `RelationshipInspector.tsx` (2-3 hours)
2. Create `EntityCard.tsx` mini component (1 hour)
3. Add relationship selection to ICS store (1 hour)
4. Integrate with ICSLayout (1 hour)
5. Add relationship navigation (prev/next) (1 hour)

**Total Estimate**: 6-8 hours

---

### Pattern 4: Graph Visualization (Future Enhancement)

**Rationale**: For complex specifications with many relationships, a visual graph provides better overview than lists.

**Recommended Libraries** (from research):

#### Option A: **ReactFlow** (Recommended)
- **Pros**:
  - Purpose-built for React (not a wrapper)
  - Built-in accessibility features
  - Extensive customization
  - Good TypeScript support
  - Active maintenance (2025)
- **Cons**:
  - Larger bundle size (~200KB)
  - Steeper learning curve
- **Best for**: Interactive diagrams, editable graphs, complex workflows
- **License**: MIT
- **Installation**: `npm install reactflow`

**Example Implementation**:
```typescript
import ReactFlow, { Node, Edge, Controls, Background } from 'reactflow';
import 'reactflow/dist/style.css';

function RelationshipGraph({ relationships, entities }: RelationshipGraphProps) {
  const nodes: Node[] = entities.map(entity => ({
    id: entity.id,
    data: {
      label: entity.text,
      type: entity.type,
      confidence: entity.confidence
    },
    position: { x: 0, y: 0 }, // Auto-layout via dagre/elkjs
    type: 'entity',
  }));

  const edges: Edge[] = relationships.map(rel => ({
    id: rel.id,
    source: rel.source,
    target: rel.target,
    label: rel.type,
    type: 'smoothstep',
    animated: rel.confidence < 0.7, // Animate low-confidence relationships
    style: {
      stroke: getRelationshipColor(rel.type),
      strokeWidth: rel.confidence * 3 + 1, // Width = confidence
    },
  }));

  return (
    <ReactFlow
      nodes={nodes}
      edges={edges}
      fitView
      nodeTypes={customNodeTypes}
      edgeTypes={customEdgeTypes}
    >
      <Controls />
      <Background />
    </ReactFlow>
  );
}
```

**Accessibility Considerations**:
- ReactFlow supports keyboard navigation out-of-box
- Custom ARIA labels for nodes/edges
- Provide alternative list view (Pattern 1) for screen readers
- Zoom controls with ARIA labels
- High contrast mode support

#### Option B: **Visx** (by Airbnb)
- **Pros**:
  - Low-level D3 primitives in React
  - Small bundle (tree-shakable)
  - Complete control over rendering
  - No external dependencies
- **Cons**:
  - Requires more manual work
  - No built-in interactivity
  - Need to implement accessibility manually
- **Best for**: Custom visualizations, static graphs, small bundle requirements
- **License**: MIT
- **Installation**: `npm install @visx/network @visx/group @visx/responsive`

**Example Implementation**:
```typescript
import { Network } from '@visx/network';
import { Group } from '@visx/group';

function RelationshipNetwork({ relationships, entities }: RelationshipNetworkProps) {
  const graph = {
    nodes: entities.map(e => ({ id: e.id, ...e })),
    links: relationships.map(r => ({
      source: r.source,
      target: r.target,
      ...r
    }))
  };

  return (
    <svg width={800} height={600}>
      <Network
        graph={graph}
        nodeComponent={CustomNode}
        linkComponent={CustomEdge}
      />
    </svg>
  );
}
```

#### Option C: **Nivo** (Ready-made charts)
- **Pros**:
  - Beautiful defaults
  - Built-in responsive design
  - D3-powered
  - Network diagram support
- **Cons**:
  - Less customization
  - Not ideal for force-directed layouts
- **Best for**: Standard charts, quick prototypes
- **License**: MIT
- **Installation**: `npm install @nivo/network`

**Recommendation**: Start with **Pattern 1 (List View)** for immediate value, add **ReactFlow** graph visualization when complexity justifies it (>10 entities, >15 relationships).

**Graph Implementation Estimate**: 8-12 hours (ReactFlow setup, custom nodes/edges, layout, accessibility)

---

### Pattern 5: Effects & Assertions Display

**Design Philosophy**: Follow same patterns as relationships (list view + inspector + inline highlights).

#### Enhanced Effects Display

**List View**:
```
╔════════════════════════════════════════╗
║ Effects (3)                            ║
╠════════════════════════════════════════╣
║ [IO_EFFECT] Database write             ║
║ Target: user_profile                   ║
║ ▓▓▓▓▓▓▓▓▓░ 90%                        ║
║                                        ║
║ [STATE_CHANGE] Update session          ║
║ Target: session_state                  ║
║ ▓▓▓▓▓▓▓▓░░ 85%                        ║
║                                        ║
║ [SIDE_EFFECT] Log event                ║
║ Target: audit_log                      ║
║ ▓▓▓▓▓▓▓░░░ 75%                        ║
╚════════════════════════════════════════╝
```

**Color Coding**:
- `io_effect`: Blue (#3b82f6)
- `state_change`: Orange (#f97316)
- `side_effect`: Purple (#8b5cf6)

**Inline Highlighting**:
```css
.effect {
  border-bottom: 2px solid;
  cursor: help;
}

.effect-io { border-bottom-color: #3b82f6; }
.effect-state { border-bottom-color: #f97316; }
.effect-side { border-bottom-color: #8b5cf6; }
```

#### Enhanced Assertions Display

**List View**:
```
╔════════════════════════════════════════╗
║ Assertions (4)                         ║
╠════════════════════════════════════════╣
║ [PRECONDITION] email IS NOT empty      ║
║ Rationale: Input validation required   ║
║ ▓▓▓▓▓▓▓▓▓▓ 95%                        ║
║                                        ║
║ [POSTCONDITION] user_created IS true   ║
║ Rationale: Confirms successful create  ║
║ ▓▓▓▓▓▓▓▓░░ 88%                        ║
║                                        ║
║ [INVARIANT] email IS unique            ║
║ Rationale: Database constraint         ║
║ ▓▓▓▓▓▓▓▓▓░ 92%                        ║
╚════════════════════════════════════════╝
```

**Color Coding**:
- `precondition`: Yellow (#eab308)
- `postcondition`: Green (#22c55e)
- `invariant`: Red (#ef4444)

**Inline Highlighting**:
```css
.assertion {
  border-bottom: 2px solid;
  cursor: help;
}

.assertion-precondition { border-bottom-color: #eab308; }
.assertion-postcondition { border-bottom-color: #22c55e; }
.assertion-invariant { border-bottom-color: #ef4444; }
```

**Implementation**: Follow same component structure as relationships (1:1 mapping).

**Estimate**: 4-6 hours per semantic type (effects + assertions = 8-12 hours)

---

## Accessibility Compliance (WCAG 2.1 AA)

### Critical Requirements

#### 1. **Color + Non-Color Encoding** (WCAG 1.4.1 Use of Color - Level A)
- ✅ Relationship types: Color badge + text label
- ✅ Confidence: Color progress bar + percentage text
- ✅ Entity types: Color highlight + type badge
- ✅ Effects: Color border + type icon
- ✅ Assertions: Color border + type label

**Example Dual Encoding**:
```typescript
<Badge className={getRelationshipColor(type)}>
  <Icon className="mr-1" /> {/* Visual icon */}
  {type} {/* Text label */}
</Badge>
```

#### 2. **Contrast Ratios** (WCAG 1.4.3 Contrast - Level AA)
- Text: 4.5:1 minimum (7:1 for Level AAA)
- Non-text (badges, icons): 3:1 minimum
- All colors in ics.css already meet requirements
- Test with: Chrome DevTools Lighthouse, axe DevTools

#### 3. **Keyboard Navigation** (WCAG 2.1.1 Keyboard - Level A)
- Tab order: List → Relationships → Inspector
- Enter: Select relationship
- Arrow keys: Navigate list
- Escape: Deselect/close
- Focus indicators: 2px outline (WCAG 2.4.7)

**Implementation**:
```typescript
<div
  tabIndex={0}
  role="button"
  aria-label={`Relationship: ${type} from ${source} to ${target}`}
  onKeyDown={(e) => {
    if (e.key === 'Enter' || e.key === ' ') {
      selectRelationship(id);
    }
  }}
>
  {/* Content */}
</div>
```

#### 4. **ARIA Labels** (WCAG 4.1.2 Name, Role, Value - Level A)
```typescript
// List container
<div role="list" aria-label="Semantic relationships">
  {/* Items */}
</div>

// Relationship item
<div
  role="listitem"
  aria-label="OPERATES_ON relationship from validate to email with 85% confidence"
>
  {/* Content */}
</div>

// Confidence indicator
<Progress
  value={85}
  aria-label="Confidence score: 85 percent"
  aria-valuemin={0}
  aria-valuemax={100}
  aria-valuenow={85}
/>

// Graph (if implemented)
<svg role="img" aria-label="Relationship graph showing 5 entities and 8 relationships">
  <title>Relationship graph</title>
  <desc>Interactive graph showing semantic relationships between entities</desc>
  {/* Nodes and edges */}
</svg>
```

#### 5. **Screen Reader Support**
- Provide text alternatives for visual graphs
- Announce relationship details on focus
- Live region for dynamic updates (e.g., new relationships detected)
- Alternative list view always available

**Example Live Region**:
```typescript
<div aria-live="polite" aria-atomic="true" className="sr-only">
  {relationshipCount} relationships detected in specification
</div>
```

#### 6. **Focus Management** (WCAG 2.4.7 Focus Visible - Level AA)
```css
.relationship-card:focus {
  outline: 2px solid hsl(var(--primary));
  outline-offset: 2px;
  box-shadow: 0 0 0 4px hsl(var(--primary) / 0.2);
}

.relationship-card:focus:not(:focus-visible) {
  outline: none;
  box-shadow: none;
}
```

### Testing Checklist
- [ ] Run axe DevTools accessibility scan (0 critical issues)
- [ ] Test with NVDA/JAWS screen readers
- [ ] Verify keyboard-only navigation
- [ ] Check color contrast (Lighthouse)
- [ ] Test with zoom up to 200% (WCAG 1.4.4)
- [ ] Verify focus indicators visible
- [ ] Test reduced motion preference (WCAG 2.3.3)

---

## Integration Points with Existing ICS Components

### 1. **ICSLayout.tsx** - Main layout container
**Integration**: Add relationship panel to layout
```typescript
interface ICSLayoutProps {
  // ... existing props
  showRelationshipPanel?: boolean; // New prop
}

function ICSLayout({ showRelationshipPanel = false, ... }: ICSLayoutProps) {
  return (
    <div className="ics-layout">
      {/* ... existing panels */}
      {showRelationshipPanel && (
        <div className="ics-relationship-panel">
          <RelationshipPanel />
        </div>
      )}
    </div>
  );
}
```

**Layout Options**:
- **Option A**: Right sidebar (like HoleInspector) - conflicts with inspector
- **Option B**: Bottom panel - works well for lists
- **Option C**: Tabbed inspector (Holes | Relationships | Effects | Assertions)
- **Recommendation**: Option C (tabbed inspector) for space efficiency

### 2. **ICS Store** (`frontend/src/lib/ics/store.ts`)
**New State**:
```typescript
interface ICSStore {
  // ... existing state
  selectedRelationship: string | null;
  selectedEffect: string | null;
  selectedAssertion: string | null;
  relationshipFilter: RelationshipType | 'all';
  effectFilter: EffectType | 'all';
  assertionFilter: AssertionType | 'all';
}

interface ICSStoreActions {
  // ... existing actions
  selectRelationship: (id: string | null) => void;
  selectEffect: (id: string | null) => void;
  selectAssertion: (id: string | null) => void;
  setRelationshipFilter: (filter: RelationshipType | 'all') => void;
  highlightRelationship: (id: string) => void; // Scroll to and highlight in editor
}
```

### 3. **SemanticEditor.tsx** - ProseMirror editor
**Decoration Extension**:
```typescript
// In createDecorationsPlugin
function createRelationshipDecorations(analysis: SemanticAnalysis): Decoration[] {
  const decorations: Decoration[] = [];

  analysis.relationships.forEach(rel => {
    decorations.push(
      Decoration.inline(rel.from, rel.to, {
        class: `relationship relationship-${rel.type.toLowerCase()}`,
        'data-relationship-id': rel.id,
        title: `${rel.type}: ${rel.source} → ${rel.target}`,
      })
    );
  });

  return decorations;
}
```

**Tooltip Handler Update**:
```typescript
// In handleMouseMove
if (target.dataset.relationshipId && semanticAnalysis) {
  const relationship = semanticAnalysis.relationships.find(
    r => r.id === target.dataset.relationshipId
  );
  if (relationship) {
    tooltipData = { type: 'relationship', data: relationship };
  }
}
```

### 4. **NLP Pipeline** (`lift_sys/nlp/pipeline.py`)
**Already produces relationships** (lines 114):
```python
relationships = self._extract_relationships(doc)
```

**Enhancement needed**: Ensure relationship extraction returns Phase 2 format
```python
def _extract_relationships(self, doc) -> list[dict]:
    """Extract relationships with enhanced structure."""
    relationships = []

    # Dependency parsing for relationships
    for token in doc:
        if token.dep_ in ['nsubj', 'dobj', 'pobj']:
            # Extract relationship based on syntactic dependencies
            rel_type = self._infer_relationship_type(token.head, token)

            relationships.append({
                'id': f'rel-{len(relationships)}',
                'type': rel_type,
                'source': token.head.text,  # Should be entity ID
                'target': token.text,       # Should be entity ID
                'text': token.sent.text,
                'from': token.sent.start_char,
                'to': token.sent.end_char,
                'confidence': 0.75,  # Confidence scoring
            })

    return relationships
```

### 5. **API Integration** (`lift_sys/api/server.py`)
**Endpoint enhancement**:
```python
@app.post("/analyze")
async def analyze_text(request: AnalyzeRequest) -> SemanticAnalysis:
    """Analyze text and return enhanced semantic analysis."""
    analysis = pipeline.analyze(request.text)

    # Ensure relationships are included
    return SemanticAnalysis(
        entities=analysis['entities'],
        relationships=analysis['relationships'],  # Phase 2 addition
        effects=analysis['effects'],              # Phase 2 addition
        assertions=analysis['assertions'],        # Phase 2 addition
        # ... other fields
    )
```

---

## Mock-up Descriptions

### Mock-up 1: Relationship List View
```
┌─────────────────────────────────────────────────────┐
│ Relationships (8)                    [Filter ▾]     │
├─────────────────────────────────────────────────────┤
│                                                     │
│ ┌─────────────────────────────────────────────────┐│
│ │ [validate] →OPERATES_ON→ [email]                ││
│ │ ████████░░ 85%                                  ││
│ │ Validate operates on email input                ││
│ └─────────────────────────────────────────────────┘│
│                                                     │
│ ┌─────────────────────────────────────────────────┐│
│ │ [User] →MODIFIES→ [profile]                     ││
│ │ █████████░ 92%                                  ││
│ │ User modifies their profile                     ││
│ └─────────────────────────────────────────────────┘│
│                                                     │
│ ┌─────────────────────────────────────────────────┐│
│ │ [report] →DEPENDS_ON→ [database]                ││
│ │ ██████░░░░ 67%                                  ││
│ │ Report generation depends on database           ││
│ └─────────────────────────────────────────────────┘│
│                                                     │
└─────────────────────────────────────────────────────┘
```

**Features**:
- Scrollable list with shadcn/ui ScrollArea
- Each item is a Card with hover effect
- Color-coded relationship type badges
- Progress bar + percentage for confidence
- Click to select, opens inspector
- Filter dropdown (All, USES, PRODUCES, etc.)

### Mock-up 2: Inline Editor Highlights
```
The system validates user email addresses and stores
            --------      ----- ---------
            |              |     |
            OPERATES_ON    |     DEPENDS_ON
                           |
                          USER

them in the database. The report generation process
                         ------ ----------
                         |      |
                         PRODUCES
```

**Features**:
- Dotted underline for relationship spans
- Color-coded by relationship type
- Hover shows tooltip with full details
- Click scrolls to relationship in list panel

### Mock-up 3: Tabbed Inspector
```
┌─────────────────────────────────────────────────────┐
│ Inspector                                           │
├─────────────────────────────────────────────────────┤
│ [Holes] [Relationships] [Effects] [Assertions]      │
├─────────────────────────────────────────────────────┤
│                                                     │
│ OPERATES_ON                             85% ●      │
│                                                     │
│ ┌─────────────┐        ┌─────────────┐            │
│ │  validate   │   →    │    email    │            │
│ │  FUNCTION   │        │  VARIABLE   │            │
│ └─────────────┘        └─────────────┘            │
│                                                     │
│ ▼ Description                                      │
│   Validate operates on email input                 │
│                                                     │
│ ▼ Connected Entities                               │
│   Source: validate (FUNCTION)                      │
│   • Type: FUNCTION                                 │
│   • Confidence: 90%                                │
│                                                     │
│   Target: email (VARIABLE)                         │
│   • Type: VARIABLE                                 │
│   • Confidence: 85%                                │
│                                                     │
│ ▼ Evidence                                         │
│   Position: 12-35                                  │
│   Text: "validates user email"                     │
│   Confidence: 85.0%                                │
│   Derived from: dependency_parsing                 │
│                                                     │
└─────────────────────────────────────────────────────┘
```

**Features**:
- Tabs for different semantic types (Holes, Relationships, Effects, Assertions)
- Collapsible sections with Accordion
- Entity cards with type badges
- Visual flow diagram (source → relationship → target)
- Evidence section with provenance

### Mock-up 4: Graph View (Future)
```
┌─────────────────────────────────────────────────────┐
│ Relationship Graph                   [Zoom] [Reset] │
├─────────────────────────────────────────────────────┤
│                                                     │
│         ┌──────────┐                               │
│         │   User   │                               │
│         └────┬─────┘                               │
│              │ MODIFIES                            │
│              ↓                                     │
│         ┌──────────┐        DEPENDS_ON            │
│    ┌───│ profile  │←──────────────────┐          │
│    │   └──────────┘                    │          │
│    │                                   │          │
│    │CONTAINS         ┌──────────┐    ┌┴────────┐ │
│    │                 │ validate │    │ database│ │
│    └────────────────→│          │────┤         │ │
│                      └──────┬───┘    └─────────┘ │
│                             │OPERATES_ON          │
│                             ↓                     │
│                      ┌──────────┐                │
│                      │  email   │                │
│                      └──────────┘                │
│                                                   │
│ Legend: ──USES── ──PRODUCES── ──DEPENDS_ON──     │
│         ──MODIFIES── ──OPERATES_ON──             │
└─────────────────────────────────────────────────────┘
```

**Features**:
- Force-directed graph layout (ReactFlow)
- Interactive nodes (click to select, drag to reposition)
- Edge labels for relationship types
- Color-coded edges by relationship type
- Zoom/pan controls
- Legend for relationship types
- Alternative list view for accessibility

---

## Performance Considerations

### Rendering Optimization

**Problem**: Large specifications may have 50+ relationships, causing lag.

**Solutions**:
1. **Virtualized List** (React Virtual or Tanstack Virtual)
   - Only render visible items
   - Smooth scrolling for long lists
   - ~100-500 items no lag
   ```typescript
   import { useVirtualizer } from '@tanstack/react-virtual';

   function RelationshipList({ relationships }) {
     const rowVirtualizer = useVirtualizer({
       count: relationships.length,
       getScrollElement: () => parentRef.current,
       estimateSize: () => 80, // Estimated height
     });

     return (
       <div ref={parentRef} style={{ height: '400px', overflow: 'auto' }}>
         <div style={{ height: `${rowVirtualizer.getTotalSize()}px` }}>
           {rowVirtualizer.getVirtualItems().map(virtualRow => (
             <RelationshipCard
               key={relationships[virtualRow.index].id}
               relationship={relationships[virtualRow.index]}
             />
           ))}
         </div>
       </div>
     );
   }
   ```

2. **Memoization** (React.memo)
   ```typescript
   export const RelationshipCard = React.memo(({ relationship, onClick }) => {
     // Component implementation
   }, (prevProps, nextProps) => {
     return prevProps.relationship.id === nextProps.relationship.id;
   });
   ```

3. **Debounced Filter** (for search/filter)
   ```typescript
   import { useDebouncedValue } from '@/hooks/useDebouncedValue';

   const [filterText, setFilterText] = useState('');
   const debouncedFilter = useDebouncedValue(filterText, 300);

   const filteredRelationships = useMemo(() => {
     return relationships.filter(rel =>
       rel.type.includes(debouncedFilter) ||
       rel.description.includes(debouncedFilter)
     );
   }, [relationships, debouncedFilter]);
   ```

4. **Code Splitting** (lazy load graph visualization)
   ```typescript
   const RelationshipGraph = lazy(() => import('./RelationshipGraph'));

   <Suspense fallback={<Skeleton className="h-96" />}>
     <RelationshipGraph relationships={relationships} />
   </Suspense>
   ```

**Bundle Size Impact**:
- Base components (List + Inspector): ~10-15KB
- ReactFlow (if added): ~200KB (lazy load recommended)
- Visx (if added): ~50-80KB (tree-shakable)

---

## Implementation Roadmap

### Phase 1: Core List View (6-8 hours)
**Priority**: P0 (Essential)
**Dependencies**: None
**Components**:
1. RelationshipCard.tsx
2. RelationshipPanel.tsx
3. RelationshipTooltip in SemanticTooltip.tsx
4. ICS store updates (relationship selection)
5. CSS styles for relationship cards

**Deliverables**:
- [ ] Scrollable list of relationships
- [ ] Click to select relationship
- [ ] Hover tooltip with details
- [ ] Confidence visualization (progress bar + %)
- [ ] Filter by relationship type

### Phase 2: Inline Editor Highlights (5-6 hours)
**Priority**: P1 (High value)
**Dependencies**: Phase 1
**Components**:
1. Extend createDecorationsPlugin
2. Relationship tooltip in SemanticTooltip
3. CSS for inline highlights
4. Click handler for editor highlights

**Deliverables**:
- [ ] Dotted underline for relationship spans
- [ ] Color-coded by relationship type
- [ ] Hover shows tooltip
- [ ] Click highlights in list panel

### Phase 3: Relationship Inspector (6-8 hours)
**Priority**: P1 (High value)
**Dependencies**: Phase 1
**Components**:
1. RelationshipInspector.tsx
2. EntityCard.tsx (mini component)
3. Tabbed inspector layout
4. Relationship navigation (prev/next)

**Deliverables**:
- [ ] Detailed relationship view
- [ ] Entity details for source/target
- [ ] Evidence section
- [ ] Collapsible sections
- [ ] Tab integration with HoleInspector

### Phase 4: Effects & Assertions (8-12 hours)
**Priority**: P1 (High value)
**Dependencies**: Phases 1-3 (reuse patterns)
**Components**:
1. EffectCard.tsx, EffectPanel.tsx, EffectInspector.tsx
2. AssertionCard.tsx, AssertionPanel.tsx, AssertionInspector.tsx
3. Inline highlights for effects/assertions
4. Tooltips for effects/assertions

**Deliverables**:
- [ ] Effects list, inspector, inline highlights
- [ ] Assertions list, inspector, inline highlights
- [ ] Color-coded by type
- [ ] Same UX as relationships

### Phase 5: Accessibility & Polish (4-6 hours)
**Priority**: P0 (Essential)
**Dependencies**: Phases 1-4
**Tasks**:
1. ARIA labels for all interactive elements
2. Keyboard navigation testing
3. Screen reader testing (NVDA/JAWS)
4. Focus indicators
5. Color contrast verification
6. Axe DevTools scan (fix all issues)

**Deliverables**:
- [ ] WCAG 2.1 AA compliance
- [ ] Keyboard navigation works
- [ ] Screen reader announces correctly
- [ ] 0 critical axe issues

### Phase 6: Graph Visualization (8-12 hours) - OPTIONAL
**Priority**: P2 (Nice to have)
**Dependencies**: Phases 1-5
**Components**:
1. Install ReactFlow or Visx
2. RelationshipGraph.tsx
3. Custom node/edge components
4. Layout algorithm (dagre or elkjs)
5. Zoom/pan controls
6. Alternative list view for a11y

**Deliverables**:
- [ ] Interactive graph visualization
- [ ] Force-directed or hierarchical layout
- [ ] Click node to select entity
- [ ] Click edge to select relationship
- [ ] Zoom/pan controls
- [ ] Accessible alternative

**Total Estimated Time**:
- **Core (Phases 1-5)**: 29-40 hours
- **With Graph (Phases 1-6)**: 37-52 hours

---

## Acceptance Criteria

### Functional Requirements
- [ ] Display all relationships from semantic analysis
- [ ] Show relationship type, entities, confidence
- [ ] Filter relationships by type
- [ ] Select relationship to see details
- [ ] Click relationship in list highlights in editor
- [ ] Hover over relationship in editor shows tooltip
- [ ] Display effects with action/target/type
- [ ] Display assertions with predicate/operator/value
- [ ] Confidence visualization (progress bar + percentage)

### Accessibility Requirements
- [ ] WCAG 2.1 AA compliance verified
- [ ] Keyboard navigation works (Tab, Enter, Arrow keys)
- [ ] ARIA labels on all interactive elements
- [ ] Screen reader announces relationship details
- [ ] Color + non-color encoding (icons, text, patterns)
- [ ] Focus indicators visible (2px outline)
- [ ] Contrast ratios meet 4.5:1 (text) and 3:1 (UI)
- [ ] Alternative text-based view for graphs

### Performance Requirements
- [ ] <100ms render time for 50 relationships
- [ ] Smooth scrolling with virtualized list
- [ ] No lag on filter/search (debounced)
- [ ] Lazy load graph visualization (if implemented)
- [ ] Memoized components to prevent re-renders

### Integration Requirements
- [ ] Works with existing ICSLayout
- [ ] Integrates with ICS store (Zustand)
- [ ] Uses existing shadcn/ui components
- [ ] Follows existing CSS patterns (ics.css)
- [ ] Compatible with SemanticEditor decorations
- [ ] Backend API returns Phase 2 data

---

## Risk Assessment

### High Risk
- **Risk**: Relationship extraction quality from NLP pipeline
  - **Mitigation**: Use mock data for frontend development, improve NLP separately
  - **Impact**: Medium (affects accuracy, not functionality)

- **Risk**: Performance with large graphs (>100 nodes)
  - **Mitigation**: Virtualization, code splitting, lazy loading
  - **Impact**: Low (unlikely in typical specs)

### Medium Risk
- **Risk**: Accessibility compliance for graph visualization
  - **Mitigation**: Provide alternative list view, extensive testing
  - **Impact**: Medium (could block Phase 6)

- **Risk**: Bundle size increase with graph library
  - **Mitigation**: Lazy load, tree-shaking, code splitting
  - **Impact**: Low (acceptable for optional feature)

### Low Risk
- **Risk**: Color blindness affecting relationship type distinction
  - **Mitigation**: Dual encoding (color + text + icons)
  - **Impact**: Very Low (mitigated by design)

---

## Conclusion

**Recommended Approach**:
1. **Start with Phase 1 (List View)** - Immediate value, no external dependencies, 6-8 hours
2. **Add Phase 2 (Inline Highlights)** - High UX value, integrates with existing editor, 5-6 hours
3. **Implement Phase 3 (Inspector)** - Deep dive into relationships, follows HoleInspector pattern, 6-8 hours
4. **Extend to Phase 4 (Effects/Assertions)** - Reuse patterns, consistent UX, 8-12 hours
5. **Polish with Phase 5 (Accessibility)** - Ensure compliance, 4-6 hours
6. **Optionally add Phase 6 (Graph)** - When complexity justifies it, 8-12 hours

**Total Core Implementation**: 29-40 hours
**Total with Graph**: 37-52 hours

**Next Steps**:
1. Review this research with team
2. Prioritize phases based on user needs
3. Create implementation plan with beads
4. Start Phase 1 development
5. Iterate based on user feedback

**Files to Create**:
- `frontend/src/components/ics/RelationshipCard.tsx`
- `frontend/src/components/ics/RelationshipPanel.tsx`
- `frontend/src/components/ics/RelationshipInspector.tsx`
- `frontend/src/components/ics/EntityCard.tsx`
- `frontend/src/components/ics/EffectCard.tsx`, `EffectPanel.tsx`, `EffectInspector.tsx`
- `frontend/src/components/ics/AssertionCard.tsx`, `AssertionPanel.tsx`, `AssertionInspector.tsx`

**Files to Modify**:
- `frontend/src/components/ics/SemanticTooltip.tsx` (add RelationshipTooltip, EffectTooltip, AssertionTooltip)
- `frontend/src/components/ics/ICSLayout.tsx` (add relationship panel integration)
- `frontend/src/lib/ics/store.ts` (add relationship selection state)
- `frontend/src/lib/ics/decorations.ts` (add relationship decorations)
- `frontend/src/styles/ics.css` (relationship card styles, tooltip enhancements)
- `lift_sys/nlp/pipeline.py` (ensure Phase 2 relationship format)

---

**Research Complete**: Ready for implementation planning and task breakdown.
