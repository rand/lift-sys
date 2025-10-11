/**
 * API client for prompt-to-IR session management
 */

import { api } from "./api";
import type {
  CreateSessionRequest,
  PromptSession,
  SessionListResponse,
  ResolveHoleRequest,
  AssistsResponse,
  IRResponse,
} from "../types/sessions";

/**
 * Create a new prompt refinement session
 */
export async function createSession(
  request: CreateSessionRequest
): Promise<PromptSession> {
  const response = await api.post<PromptSession>("/spec-sessions", request);
  return response.data;
}

/**
 * List all active sessions
 */
export async function listSessions(): Promise<SessionListResponse> {
  const response = await api.get<SessionListResponse>("/spec-sessions");
  return response.data;
}

/**
 * Get details of a specific session
 */
export async function getSession(sessionId: string): Promise<PromptSession> {
  const response = await api.get<PromptSession>(`/spec-sessions/${sessionId}`);
  return response.data;
}

/**
 * Resolve a typed hole in a session
 */
export async function resolveHole(
  sessionId: string,
  holeId: string,
  request: ResolveHoleRequest
): Promise<PromptSession> {
  const response = await api.post<PromptSession>(
    `/spec-sessions/${sessionId}/holes/${holeId}/resolve`,
    request
  );
  return response.data;
}

/**
 * Finalize a session and return the completed IR
 */
export async function finalizeSession(sessionId: string): Promise<IRResponse> {
  const response = await api.post<IRResponse>(
    `/spec-sessions/${sessionId}/finalize`
  );
  return response.data;
}

/**
 * Get actionable suggestions for resolving holes
 */
export async function getAssists(sessionId: string): Promise<AssistsResponse> {
  const response = await api.get<AssistsResponse>(
    `/spec-sessions/${sessionId}/assists`
  );
  return response.data;
}

/**
 * Delete a session
 */
export async function deleteSession(sessionId: string): Promise<void> {
  await api.delete(`/spec-sessions/${sessionId}`);
}
