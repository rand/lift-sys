/**
 * Type definitions for semantic analysis and ICS components
 */

/**
 * Hole kinds from the IR system
 */
export type HoleKind = 'intent' | 'signature' | 'effect' | 'assertion' | 'implementation';

/**
 * Hole status
 */
export type HoleStatus = 'unresolved' | 'in_progress' | 'resolved';

/**
 * Provenance source
 */
export type ProvenanceSource = 'human' | 'agent' | 'reverse' | 'verification' | 'merge' | 'refinement' | 'unknown';

/**
 * Constraint types
 */
export type ConstraintType = 'return_constraint' | 'loop_constraint' | 'position_constraint';

/**
 * Constraint severity
 */
export type ConstraintSeverity = 'error' | 'warning';

/**
 * Entity types detected by NLP
 */
export type EntityType =
  | 'PERSON'
  | 'ORG'
  | 'GPE'
  | 'LOC'
  | 'PRODUCT'
  | 'EVENT'
  | 'TECHNICAL'
  | 'FUNCTION'
  | 'CLASS'
  | 'VARIABLE'
  | 'TYPE';

/**
 * Relationship types
 */
export type RelationshipType =
  | 'causal'
  | 'temporal'
  | 'conditional'
  | 'dependency';

/**
 * Modal operator types
 */
export type ModalityType =
  | 'certainty'    // must, will, always
  | 'possibility'  // may, might, could
  | 'necessity'    // should, ought to
  | 'prohibition'; // must not, cannot

/**
 * Provenance information
 */
export interface Provenance {
  source: ProvenanceSource;
  confidence: number;
  timestamp: string;
  author: string | null;
  evidenceRefs: string[];
  metadata: Record<string, unknown>;
}

/**
 * Typed hole from IR
 */
export interface TypedHole {
  id: string;
  identifier: string;
  kind: HoleKind;
  typeHint: string;
  description: string;
  status: HoleStatus;
  confidence: number;
  evidence: string[];
  pos?: number;  // Position in document
  provenance?: Provenance;
  constraints?: string[];  // IDs of constraints applied to this hole
}

/**
 * Unified tooltip data for holes
 * Combines semantic analysis (TypedHole) with store metadata (HoleDetails)
 */
export interface TooltipHoleData {
  // Always available (from TypedHole)
  id: string;
  identifier: string;
  kind: HoleKind;
  typeHint: string;
  description: string;
  status: HoleStatus;
  confidence: number;

  // Optional store metadata (from HoleDetails when available)
  blocks?: Array<{ id: string; name: string; reason: string }>;
  blockedBy?: Array<{ id: string; name: string; reason: string }>;
  constraintCount?: number;
  priority?: 'critical' | 'high' | 'medium' | 'low';
}

/**
 * Constraint definition
 */
export interface Constraint {
  id: string;
  type: ConstraintType;
  description: string;
  severity: ConstraintSeverity;
  appliesTo: string[];  // Hole IDs
  source: string;  // Where this constraint came from
  impact: string;  // Description of impact
  locked: boolean;  // Design decision locked in?
  metadata?: Record<string, unknown>;
}

/**
 * Detected entity
 */
export interface Entity {
  id: string;
  type: EntityType;
  text: string;
  from: number;
  to: number;
  confidence: number;
  metadata?: Record<string, unknown>;
}

/**
 * NLP-detected relationship in text (position-based)
 * Used in semantic analysis to represent relationships extracted from natural language.
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

/**
 * IR-level relationship between entities (from RelationshipClause)
 * Represents semantic relationships in the Intermediate Representation,
 * not tied to specific text positions. Used in session IR responses.
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
 * Modal operator
 */
export interface ModalOperator {
  id: string;
  modality: ModalityType;
  text: string;
  from: number;
  to: number;
  scope: string;  // What this modal applies to
}

/**
 * Ambiguity marker
 */
export interface Ambiguity {
  id: string;
  text: string;
  from: number;
  to: number;
  reason: string;
  suggestions?: string[];
}

/**
 * Contradiction marker
 */
export interface Contradiction {
  id: string;
  text: string;
  from: number;
  to: number;
  conflicts: string[];  // IDs of conflicting elements
  severity: 'critical' | 'warning';
}

/**
 * Effect clause
 */
export interface Effect {
  id: string;
  description: string;
  from: number;
  to: number;
  type: 'side_effect' | 'io_effect' | 'state_change';
}

/**
 * Assertion (pre/post condition)
 */
export interface Assertion {
  id: string;
  predicate: string;
  from: number;
  to: number;
  type: 'precondition' | 'postcondition' | 'invariant';
  rationale?: string;
}

/**
 * Complete semantic analysis result
 */
export interface SemanticAnalysis {
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

/**
 * Dependency between holes
 */
export interface HoleDependency {
  id: string;
  name: string;
  reason: string;
  type: 'blocks' | 'blocked_by' | 'depends_on';
}

/**
 * Solution space evolution
 */
export interface SolutionSpace {
  before: string;
  after: string;
  reduction: number;
  remainingOptions: string[];
}

/**
 * Acceptance criterion
 */
export interface AcceptanceCriterion {
  description: string;
  status: 'pending' | 'passing' | 'failing';
  evidence?: string;
}

/**
 * AI refinement suggestion
 */
export interface RefinementSuggestion {
  suggestion: string;
  confidence: number;
  rationale: string;
  impact: string;
}

/**
 * Detailed hole information for inspector
 */
export interface HoleDetails {
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
  blocks: HoleDependency[];
  blockedBy: HoleDependency[];
  dependsOn: HoleDependency[];

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

/**
 * File reference (#filename)
 */
export interface FileReference {
  id: string;
  path: string;
  from: number;
  to: number;
  exists: boolean;
}

/**
 * Symbol reference (@symbol)
 */
export interface SymbolReference {
  id: string;
  name: string;
  type: 'function' | 'class' | 'variable' | 'hole' | 'entity';
  from: number;
  to: number;
  targetId?: string;  // ID of referenced element
}

/**
 * Layout configuration
 */
export interface LayoutConfig {
  leftPanelWidth: number;
  rightPanelWidth: number;
  inspectorHeight: number;
  chatHeight: number;
  showFileExplorer: boolean;
  showSymbolsPanel: boolean;
  showInspector: boolean;
  showChat: boolean;
}

/**
 * Panel visibility
 */
export interface PanelVisibility {
  fileExplorer: boolean;
  symbolsPanel: boolean;
  inspector: boolean;
  chat: boolean;
  terminal: boolean;
}
