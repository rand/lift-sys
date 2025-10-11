/**
 * TypeScript types for prompt-to-IR session management API
 */

export interface IRDraft {
  version: number;
  ir: Record<string, unknown>;
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
  ir?: Record<string, unknown>;
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
  ir: Record<string, unknown>;
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
