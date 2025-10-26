/**
 * TypeScript types for prompt-to-IR session management API
 */

import type { TypedHole, Provenance, Constraint, IRRelationship } from './ics/semantic';

/**
 * Intermediate Representation structure matching backend IR serialization
 * Includes Phase 2 fields: relationships and enhanced constraint metadata
 */
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
  relationships?: IRRelationship[];  // Phase 2: IR-level semantic relationships
  metadata?: {
    source_path?: string;
    language?: string;
    origin?: string;
    evidence?: Array<Record<string, unknown>>;
  };
  constraints?: Constraint[];  // Phase 2: Enhanced with appliesTo, source, impact, locked
}

export interface IRDraft {
  version: number;
  ir: IntermediateRepresentation;  // Phase 2: Typed IR structure
  validation_status: "pending" | "incomplete" | "valid" | "contradictory";
  ambiguities: string[];
  smt_results: Array<Record<string, unknown>>;
  created_at: string;
  metadata: Record<string, unknown>;
}

export interface PromptSession {
  session_id: string;
  status: "active" | "finalized" | "abandoned";
  source: "prompt" | "reverse_mode";
  created_at: string;
  updated_at: string;
  current_draft: IRDraft | null;
  ambiguities: string[];
  revision_count: number;
  metadata: Record<string, unknown>;
}

export interface CreateSessionRequest {
  prompt?: string;
  ir?: IntermediateRepresentation;  // Phase 2: Typed IR structure
  source?: "prompt" | "reverse_mode";
  metadata?: Record<string, unknown>;
}

export interface ResolveHoleRequest {
  resolution_text: string;
  resolution_type?: string;
}

export interface SessionListResponse {
  sessions: PromptSession[];
}

export interface AssistSuggestion {
  hole_id: string;
  suggestions: string[];
  context: string;
}

export interface AssistsResponse {
  session_id: string;
  assists: AssistSuggestion[];
}

export interface IRResponse {
  ir: IntermediateRepresentation;  // Phase 2: Typed IR structure
  metadata: Record<string, unknown>;
}

export interface ProgressEvent {
  type: string;
  scope: string;
  session_id?: string;
  status?: string;
  ambiguities?: number;
  [key: string]: unknown;
}

export interface IRSuggestion {
  category: string;
  severity: string;
  title: string;
  description: string;
  location: string;
  current_value: string | null;
  suggested_value: string | null;
  rationale: string | null;
  examples: string[];
  references: string[];
}

export interface AnalysisReport {
  session_id: string;
  ir_summary: Record<string, unknown>;
  suggestions: IRSuggestion[];
  summary_stats: Record<string, number>;
  overall_quality_score: number;
}
