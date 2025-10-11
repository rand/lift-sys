/**
 * Prompt Workbench View
 *
 * Interactive UI for creating and refining natural language specifications
 * into IR through iterative hole resolution.
 */

import { useState, useEffect } from "react";
import { Button } from "../components/ui/button";
import { useProgressStream } from "../lib/useProgressStream";
import {
  createSession,
  listSessions,
  getSession,
  resolveHole,
  finalizeSession,
  getAssists,
  deleteSession,
} from "../lib/sessionApi";
import type { PromptSession, AssistSuggestion } from "../types/sessions";

export function PromptWorkbenchView() {
  const [prompt, setPrompt] = useState("");
  const [sessions, setSessions] = useState<PromptSession[]>([]);
  const [activeSession, setActiveSession] = useState<PromptSession | null>(null);
  const [assists, setAssists] = useState<AssistSuggestion[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [resolutionInputs, setResolutionInputs] = useState<Record<string, string>>({});
  const { events } = useProgressStream();

  // Load sessions on mount
  useEffect(() => {
    void loadSessions();
  }, []);

  // Listen for session-related progress events
  useEffect(() => {
    const sessionEvents = events.filter(e => e.scope === "spec_sessions");
    if (sessionEvents.length > 0) {
      const latestEvent = sessionEvents[sessionEvents.length - 1];

      // Reload session if it was updated
      if (latestEvent.session_id && activeSession?.session_id === latestEvent.session_id) {
        void refreshActiveSession();
      }

      // Reload session list if a new session was created
      if (latestEvent.type === "session_created") {
        void loadSessions();
      }
    }
  }, [events, activeSession]);

  const loadSessions = async () => {
    try {
      const response = await listSessions();
      setSessions(response.sessions);
    } catch (err) {
      console.error("Failed to load sessions:", err);
    }
  };

  const refreshActiveSession = async () => {
    if (!activeSession) return;
    try {
      const updated = await getSession(activeSession.session_id);
      setActiveSession(updated);
    } catch (err) {
      console.error("Failed to refresh session:", err);
    }
  };

  const handleCreateSession = async () => {
    if (!prompt.trim()) {
      setError("Please enter a prompt");
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const session = await createSession({ prompt: prompt.trim() });
      setActiveSession(session);
      setSessions([session, ...sessions]);

      // Load assists if there are ambiguities
      if (session.ambiguities.length > 0) {
        await loadAssists(session.session_id);
      }

      setPrompt("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create session");
    } finally {
      setIsLoading(false);
    }
  };

  const handleSelectSession = async (session: PromptSession) => {
    setActiveSession(session);
    setError(null);

    if (session.ambiguities.length > 0) {
      await loadAssists(session.session_id);
    }
  };

  const loadAssists = async (sessionId: string) => {
    try {
      const response = await getAssists(sessionId);
      setAssists(response.assists);
    } catch (err) {
      console.error("Failed to load assists:", err);
    }
  };

  const handleResolveHole = async (holeId: string) => {
    if (!activeSession) return;

    const resolution = resolutionInputs[holeId];
    if (!resolution?.trim()) {
      setError(`Please enter a resolution for ${holeId}`);
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const updated = await resolveHole(activeSession.session_id, holeId, {
        resolution_text: resolution.trim(),
        resolution_type: "clarify_intent",
      });

      setActiveSession(updated);
      setResolutionInputs(prev => {
        const next = { ...prev };
        delete next[holeId];
        return next;
      });

      // Reload assists
      if (updated.ambiguities.length > 0) {
        await loadAssists(updated.session_id);
      } else {
        setAssists([]);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to resolve hole");
    } finally {
      setIsLoading(false);
    }
  };

  const handleFinalize = async () => {
    if (!activeSession) return;

    setIsLoading(true);
    setError(null);

    try {
      await finalizeSession(activeSession.session_id);
      const updated = await getSession(activeSession.session_id);
      setActiveSession(updated);
      setAssists([]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to finalize session");
    } finally {
      setIsLoading(false);
    }
  };

  const handleDelete = async (sessionId: string) => {
    try {
      await deleteSession(sessionId);
      setSessions(sessions.filter(s => s.session_id !== sessionId));

      if (activeSession?.session_id === sessionId) {
        setActiveSession(null);
        setAssists([]);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete session");
    }
  };

  return (
    <div style={{ display: "grid", gridTemplateColumns: "300px 1fr", gap: "1.5rem", height: "100%" }}>
      {/* Session List Sidebar */}
      <div style={{ display: "flex", flexDirection: "column", gap: "1rem", overflowY: "auto" }}>
        <div>
          <h2 style={{ marginTop: 0, marginBottom: "0.75rem", fontSize: "1.25rem" }}>Sessions</h2>
          <Button onClick={() => void loadSessions()} variant="ghost" style={{ width: "100%" }}>
            Refresh
          </Button>
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
          {sessions.length === 0 && (
            <p style={{ color: "#94a3b8", fontSize: "0.875rem", fontStyle: "italic" }}>
              No sessions yet. Create one to get started.
            </p>
          )}
          {sessions.map(session => (
            <div
              key={session.session_id}
              style={{
                padding: "0.75rem",
                background: activeSession?.session_id === session.session_id ? "#1e293b" : "#0f172a",
                border: "1px solid #334155",
                borderRadius: "0.375rem",
                cursor: "pointer",
              }}
              onClick={() => void handleSelectSession(session)}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "start" }}>
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: "0.875rem", fontWeight: 500 }}>
                    {session.session_id.substring(0, 8)}...
                  </div>
                  <div style={{ fontSize: "0.75rem", color: "#94a3b8", marginTop: "0.25rem" }}>
                    {session.status} • {session.ambiguities.length} holes
                  </div>
                </div>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={(e) => {
                    e.stopPropagation();
                    void handleDelete(session.session_id);
                  }}
                  style={{ padding: "0.25rem" }}
                >
                  ✕
                </Button>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Main Content */}
      <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem", overflowY: "auto" }}>
        {/* Create Session Form */}
        <div>
          <h2 style={{ marginTop: 0, marginBottom: "0.75rem", fontSize: "1.5rem" }}>Prompt Workbench</h2>
          <p style={{ color: "#94a3b8", marginBottom: "1rem" }}>
            Describe your specification in natural language. The system will translate it to IR and identify ambiguities.
          </p>

          <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
            <textarea
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              placeholder="e.g., A function that takes two integers and returns their sum..."
              style={{
                minHeight: "120px",
                padding: "0.75rem",
                background: "#1e293b",
                border: "1px solid #334155",
                borderRadius: "0.375rem",
                color: "#f1f5f9",
                fontSize: "0.875rem",
                fontFamily: "inherit",
                resize: "vertical",
              }}
            />
            <Button onClick={() => void handleCreateSession()} disabled={isLoading || !prompt.trim()}>
              {isLoading ? "Creating..." : "Create Session"}
            </Button>
          </div>

          {error && (
            <div style={{ marginTop: "0.75rem", padding: "0.75rem", background: "#7f1d1d", borderRadius: "0.375rem" }}>
              <p style={{ margin: 0, color: "#fca5a5", fontSize: "0.875rem" }}>{error}</p>
            </div>
          )}
        </div>

        {/* Active Session Details */}
        {activeSession && (
          <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
            {/* Session Info */}
            <div style={{ padding: "1rem", background: "#1e293b", borderRadius: "0.375rem", border: "1px solid #334155" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "start" }}>
                <div>
                  <h3 style={{ marginTop: 0, marginBottom: "0.5rem" }}>Session {activeSession.session_id.substring(0, 12)}</h3>
                  <div style={{ fontSize: "0.875rem", color: "#94a3b8" }}>
                    Status: <span style={{ color: "#f1f5f9", fontWeight: 500 }}>{activeSession.status}</span>
                    {" • "}
                    Draft: <span style={{ color: "#f1f5f9", fontWeight: 500 }}>v{activeSession.current_draft?.version ?? 0}</span>
                    {" • "}
                    Validation: <span style={{ color: "#f1f5f9", fontWeight: 500 }}>{activeSession.current_draft?.validation_status ?? "N/A"}</span>
                  </div>
                </div>
                {activeSession.status === "active" && activeSession.ambiguities.length === 0 && (
                  <Button onClick={() => void handleFinalize()} disabled={isLoading}>
                    Finalize
                  </Button>
                )}
              </div>
            </div>

            {/* IR Preview */}
            {activeSession.current_draft && (
              <div>
                <h3 style={{ marginTop: 0, marginBottom: "0.75rem" }}>Intermediate Representation</h3>
                <pre style={{
                  padding: "1rem",
                  background: "#0f172a",
                  border: "1px solid #334155",
                  borderRadius: "0.375rem",
                  overflow: "auto",
                  fontSize: "0.875rem",
                  maxHeight: "300px",
                }}>
                  {JSON.stringify(activeSession.current_draft.ir, null, 2)}
                </pre>
              </div>
            )}

            {/* Ambiguities & Resolution */}
            {activeSession.ambiguities.length > 0 && (
              <div>
                <h3 style={{ marginTop: 0, marginBottom: "0.75rem" }}>
                  Ambiguities ({activeSession.ambiguities.length})
                </h3>
                <p style={{ color: "#94a3b8", fontSize: "0.875rem", marginBottom: "1rem" }}>
                  Resolve these ambiguities to refine your specification.
                </p>

                <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
                  {activeSession.ambiguities.map(holeId => {
                    const assist = assists.find(a => a.hole_id === holeId);

                    return (
                      <div
                        key={holeId}
                        style={{
                          padding: "1rem",
                          background: "#1e293b",
                          border: "1px solid #334155",
                          borderRadius: "0.375rem",
                        }}
                      >
                        <div style={{ marginBottom: "0.75rem" }}>
                          <code style={{ fontSize: "0.875rem", fontWeight: 500 }}>{holeId}</code>
                          {assist && (
                            <p style={{ color: "#94a3b8", fontSize: "0.875rem", marginTop: "0.5rem" }}>
                              {assist.context}
                            </p>
                          )}
                        </div>

                        {assist && assist.suggestions.length > 0 && (
                          <div style={{ marginBottom: "0.75rem" }}>
                            <p style={{ fontSize: "0.75rem", color: "#94a3b8", marginBottom: "0.5rem" }}>Suggestions:</p>
                            <div style={{ display: "flex", flexWrap: "wrap", gap: "0.5rem" }}>
                              {assist.suggestions.map((suggestion, idx) => (
                                <button
                                  key={idx}
                                  onClick={() => setResolutionInputs(prev => ({ ...prev, [holeId]: suggestion }))}
                                  style={{
                                    padding: "0.25rem 0.5rem",
                                    background: "#334155",
                                    border: "1px solid #475569",
                                    borderRadius: "0.25rem",
                                    color: "#cbd5e1",
                                    fontSize: "0.75rem",
                                    cursor: "pointer",
                                  }}
                                >
                                  {suggestion}
                                </button>
                              ))}
                            </div>
                          </div>
                        )}

                        <div style={{ display: "flex", gap: "0.5rem" }}>
                          <input
                            type="text"
                            value={resolutionInputs[holeId] ?? ""}
                            onChange={(e) => setResolutionInputs(prev => ({ ...prev, [holeId]: e.target.value }))}
                            placeholder="Enter resolution..."
                            style={{
                              flex: 1,
                              padding: "0.5rem",
                              background: "#0f172a",
                              border: "1px solid #334155",
                              borderRadius: "0.375rem",
                              color: "#f1f5f9",
                              fontSize: "0.875rem",
                            }}
                          />
                          <Button
                            onClick={() => void handleResolveHole(holeId)}
                            disabled={isLoading || !resolutionInputs[holeId]?.trim()}
                            size="sm"
                          >
                            Resolve
                          </Button>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {/* Success State */}
            {activeSession.status === "finalized" && (
              <div style={{ padding: "1rem", background: "#14532d", borderRadius: "0.375rem", border: "1px solid #16a34a" }}>
                <p style={{ margin: 0, color: "#86efac", fontSize: "0.875rem" }}>
                  ✓ Session finalized! The IR is now ready for code generation.
                </p>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
