/**
 * Enhanced IR View with session integration and inline hole resolution
 *
 * Supports both:
 * - Plan-based IR (from reverse mode)
 * - Session-based IR (from prompt workbench)
 */

import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Card } from "../components/ui/card";
import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import { api } from "../lib/api";
import { getSession, resolveHole, listSessions } from "../lib/sessionApi";
import type { PromptSession } from "../types/sessions";

type IRSource = "plan" | "session";

type PlanSnapshot = {
  ir?: {
    intent: { summary: string; rationale?: string | null };
    signature: { name: string; parameters: { name: string; type_hint: string }[]; returns?: string | null };
    effects: { description: string }[];
    assertions: { predicate: string; rationale?: string | null }[];
  };
  telemetry?: {
    typed_holes?: TypedHoleTelemetry[];
    invariants?: { predicate: string; status: string }[];
  };
};

type TypedHoleTelemetry = {
  identifier: string;
  type_hint: string;
  description?: string;
  clause: string;
  assist?: string;
};

const sectionOrder: Array<{ id: keyof typeof clauseLabels; title: string }> = [
  { id: "intent", title: "Intent" },
  { id: "signature", title: "Signature" },
  { id: "effects", title: "Effects" },
  { id: "assertions", title: "Assertions" },
];

const clauseLabels = {
  intent: "Intent",
  signature: "Signature",
  effects: "Effect",
  assertions: "Assertion",
};

export function EnhancedIrView() {
  const [source, setSource] = useState<IRSource>("plan");
  const [selectedSessionId, setSelectedSessionId] = useState<string | null>(null);
  const [activeHole, setActiveHole] = useState<string | null>(null);
  const [resolutionText, setResolutionText] = useState("");
  const [isResolving, setIsResolving] = useState(false);

  // Fetch plan-based IR
  const { data: planData, isLoading: planLoading, error: planError } = useQuery<PlanSnapshot | null>({
    queryKey: ["plan"],
    queryFn: async () => {
      try {
        const response = await api.get("/plan");
        return response.data;
      } catch (err: any) {
        if (err?.response?.status === 404) {
          return null;
        }
        throw err;
      }
    },
    staleTime: 1000 * 10,
    enabled: source === "plan",
  });

  // Fetch sessions list
  const { data: sessionsData } = useQuery({
    queryKey: ["sessions"],
    queryFn: listSessions,
    enabled: source === "session",
  });

  // Fetch selected session
  const { data: sessionData, isLoading: sessionLoading, refetch: refetchSession } = useQuery<PromptSession | null>({
    queryKey: ["session", selectedSessionId],
    queryFn: () => (selectedSessionId ? getSession(selectedSessionId) : Promise.resolve(null)),
    enabled: source === "session" && selectedSessionId !== null,
  });

  const ir = source === "plan" ? planData?.ir : sessionData?.current_draft?.ir;
  const typedHoles = source === "plan" ? (planData?.telemetry?.typed_holes ?? []) : [];
  const sessionHoles = source === "session" ? (sessionData?.ambiguities ?? []) : [];
  const invariants = source === "plan" ? (planData?.telemetry?.invariants ?? []) : [];

  const isLoading = source === "plan" ? planLoading : sessionLoading;
  const error = source === "plan" ? planError : null;

  const handleResolveHole = async (holeId: string) => {
    if (!selectedSessionId || !resolutionText.trim()) return;

    setIsResolving(true);
    try {
      await resolveHole(selectedSessionId, holeId, {
        resolution_text: resolutionText.trim(),
        resolution_type: "clarify_intent",
      });
      setResolutionText("");
      setActiveHole(null);
      await refetchSession();
    } catch (err) {
      console.error("Failed to resolve hole:", err);
    } finally {
      setIsResolving(false);
    }
  };

  const sections = useMemo(() => {
    if (!ir) {
      return [];
    }

    const irData = ir as any; // Type assertion for flexibility

    return sectionOrder.map((section) => {
      switch (section.id) {
        case "intent":
          return {
            ...section,
            content: (
              <div style={{ display: "grid", gap: "0.5rem" }}>
                <p>{irData.intent?.summary || "No intent specified"}</p>
                {irData.intent?.rationale && <p style={{ opacity: 0.8 }}>Rationale: {irData.intent.rationale}</p>}
              </div>
            ),
          };
        case "signature":
          return {
            ...section,
            content: (
              <div style={{ display: "grid", gap: "0.5rem" }}>
                <div>
                  <strong>Name:</strong> {irData.signature?.name || "unknown"}
                </div>
                <div>
                  <strong>Returns:</strong> {irData.signature?.returns ?? "void"}
                </div>
                <div>
                  <strong>Parameters</strong>
                  <ul>
                    {(!irData.signature?.parameters || irData.signature.parameters.length === 0) && <li>None</li>}
                    {irData.signature?.parameters?.map((parameter: any) => (
                      <li key={parameter.name}>
                        {parameter.name}: {parameter.type_hint}
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            ),
          };
        case "effects":
          return {
            ...section,
            content: (
              <ul>
                {(!irData.effects || irData.effects.length === 0) && <li>No side effects recorded.</li>}
                {irData.effects?.map((effect: any) => (
                  <li key={effect.description}>{effect.description}</li>
                ))}
              </ul>
            ),
          };
        case "assertions":
          return {
            ...section,
            content: (
              <ul style={{ display: "grid", gap: "0.5rem" }}>
                {(!irData.assertions || irData.assertions.length === 0) && <li>No invariants provided.</li>}
                {irData.assertions?.map((assertion: any) => (
                  <li key={assertion.predicate}>
                    <div style={{ fontWeight: 600 }}>{assertion.predicate}</div>
                    {assertion.rationale && <div style={{ fontSize: "0.85rem", opacity: 0.8 }}>{assertion.rationale}</div>}
                  </li>
                ))}
              </ul>
            ),
          };
        default:
          return section;
      }
    });
  }, [ir]);

  const activeHoleDetails = useMemo(() => {
    if (!activeHole) {
      return null;
    }
    if (source === "plan") {
      return typedHoles.find((hole) => hole.identifier === activeHole) ?? null;
    }
    return null;
  }, [typedHoles, activeHole, source]);

  const invariantBadges = useMemo(() => {
    const statusVariant = (status: string): "info" | "success" | "error" => {
      if (status === "verified") return "success";
      if (status === "failed") return "error";
      return "info";
    };
    return invariants.map((invariant) => ({
      key: invariant.predicate,
      predicate: invariant.predicate,
      variant: statusVariant(invariant.status ?? "info"),
    }));
  }, [invariants]);

  return (
    <Card title="Intermediate Representation">
      {/* Source Selector */}
      <div style={{ marginBottom: "1rem", display: "flex", gap: "0.5rem", alignItems: "center" }}>
        <span style={{ fontSize: "0.875rem", color: "#94a3b8" }}>Source:</span>
        <Button
          size="sm"
          variant={source === "plan" ? "default" : "ghost"}
          onClick={() => setSource("plan")}
        >
          Plan (Reverse Mode)
        </Button>
        <Button
          size="sm"
          variant={source === "session" ? "default" : "ghost"}
          onClick={() => setSource("session")}
        >
          Session (Prompt)
        </Button>
      </div>

      {/* Session Selector */}
      {source === "session" && (
        <div style={{ marginBottom: "1rem" }}>
          <label style={{ display: "block", fontSize: "0.875rem", color: "#94a3b8", marginBottom: "0.5rem" }}>
            Select Session:
          </label>
          <select
            value={selectedSessionId ?? ""}
            onChange={(e) => setSelectedSessionId(e.target.value || null)}
            style={{
              width: "100%",
              padding: "0.5rem",
              background: "#1e293b",
              border: "1px solid #334155",
              borderRadius: "0.375rem",
              color: "#f1f5f9",
              fontSize: "0.875rem",
            }}
          >
            <option value="">-- Select a session --</option>
            {sessionsData?.sessions.map((session) => (
              <option key={session.session_id} value={session.session_id}>
                {session.session_id.substring(0, 12)}... ({session.status}, {session.ambiguities.length} holes)
              </option>
            ))}
          </select>
        </div>
      )}

      {/* Session Status */}
      {source === "session" && sessionData && (
        <div style={{ marginBottom: "1rem", padding: "0.75rem", background: "#1e293b", borderRadius: "0.375rem", fontSize: "0.875rem" }}>
          <div style={{ display: "flex", gap: "1rem" }}>
            <span>Status: <strong>{sessionData.status}</strong></span>
            <span>Draft: <strong>v{sessionData.current_draft?.version ?? 0}</strong></span>
            <span>Validation: <strong>{sessionData.current_draft?.validation_status ?? "N/A"}</strong></span>
            <span>Holes: <strong>{sessionData.ambiguities.length}</strong></span>
          </div>
        </div>
      )}

      {isLoading && <p>Loading IR…</p>}
      {error && <p role="alert">Failed to load IR.</p>}
      {!isLoading && !error && !ir && (
        <p>
          {source === "plan"
            ? "Run reverse mode to generate an IR."
            : "Select a session to view its IR."}
        </p>
      )}

      {ir && (
        <div style={{ display: "grid", gap: "1.5rem" }}>
          {/* Invariant Badges */}
          {invariantBadges.length > 0 && (
            <div style={{ display: "flex", flexWrap: "wrap", gap: "0.5rem" }}>
              {invariantBadges.map((badge) => (
                <Badge key={badge.key} variant={badge.variant}>
                  {badge.predicate}
                </Badge>
              ))}
            </div>
          )}

          {/* IR Sections */}
          <div style={{ display: "grid", gap: "1rem" }}>
            {sections.map((section, index) => {
              const clauseHoles = typedHoles.filter((hole) => hole.clause === section.id);
              const sessionClauseHoles = sessionHoles.filter((holeId) => holeId.includes(section.id));
              const hasHoles = clauseHoles.length > 0 || sessionClauseHoles.length > 0;

              return (
                <details key={section.id} open={index === 0} style={collapsibleStyle}>
                  <summary style={summaryStyle}>
                    {section.title}
                    {hasHoles && (
                      <Badge variant="warning" style={{ marginLeft: "0.5rem", fontSize: "0.75rem" }}>
                        {clauseHoles.length + sessionClauseHoles.length} holes
                      </Badge>
                    )}
                  </summary>
                  <div style={{ display: "grid", gap: "0.75rem" }}>
                    {section.content}

                    {/* Plan-based typed holes */}
                    {clauseHoles.length > 0 && (
                      <div style={{ display: "flex", flexWrap: "wrap", gap: "0.5rem" }}>
                        {clauseHoles.map((hole) => (
                          <Button
                            key={hole.identifier}
                            size="sm"
                            variant={activeHole === hole.identifier ? "default" : "outline"}
                            onClick={() => setActiveHole((current) => (current === hole.identifier ? null : hole.identifier))}
                            style={chipStyle}
                          >
                            {`<?${hole.identifier}: ${hole.type_hint}>`}
                          </Button>
                        ))}
                      </div>
                    )}

                    {/* Session-based holes with inline resolution */}
                    {source === "session" && sessionClauseHoles.length > 0 && (
                      <div style={{ display: "grid", gap: "0.75rem" }}>
                        {sessionClauseHoles.map((holeId) => (
                          <div
                            key={holeId}
                            style={{
                              padding: "0.75rem",
                              background: "#1e293b",
                              border: "1px solid #f59e0b",
                              borderRadius: "0.375rem",
                            }}
                          >
                            <div style={{ marginBottom: "0.5rem" }}>
                              <code style={{ fontSize: "0.875rem", fontWeight: 500, color: "#fbbf24" }}>
                                {holeId}
                              </code>
                            </div>
                            {activeHole === holeId ? (
                              <div style={{ display: "flex", gap: "0.5rem", alignItems: "end" }}>
                                <div style={{ flex: 1 }}>
                                  <input
                                    type="text"
                                    value={resolutionText}
                                    onChange={(e) => setResolutionText(e.target.value)}
                                    placeholder="Enter resolution..."
                                    style={{
                                      width: "100%",
                                      padding: "0.5rem",
                                      background: "#0f172a",
                                      border: "1px solid #334155",
                                      borderRadius: "0.375rem",
                                      color: "#f1f5f9",
                                      fontSize: "0.875rem",
                                    }}
                                    onKeyDown={(e) => {
                                      if (e.key === "Enter" && resolutionText.trim()) {
                                        void handleResolveHole(holeId);
                                      }
                                    }}
                                  />
                                </div>
                                <Button
                                  size="sm"
                                  onClick={() => void handleResolveHole(holeId)}
                                  disabled={isResolving || !resolutionText.trim()}
                                >
                                  Resolve
                                </Button>
                                <Button
                                  size="sm"
                                  variant="ghost"
                                  onClick={() => {
                                    setActiveHole(null);
                                    setResolutionText("");
                                  }}
                                >
                                  Cancel
                                </Button>
                              </div>
                            ) : (
                              <Button
                                size="sm"
                                variant="outline"
                                onClick={() => setActiveHole(holeId)}
                              >
                                Resolve hole
                              </Button>
                            )}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </details>
              );
            })}
          </div>

          {/* Assist Panel for Plan-based holes */}
          {activeHoleDetails && source === "plan" && (
            <aside style={assistPanelStyle} aria-live="polite">
              <h3 style={{ margin: 0 }}>Planner Assist</h3>
              <p style={{ margin: "0.5rem 0", opacity: 0.85 }}>
                {activeHoleDetails.description || "No description provided."}
              </p>
              <Badge variant="info">{clauseLabels[activeHoleDetails.clause as keyof typeof clauseLabels]}</Badge>
              {activeHoleDetails.assist && <p style={{ margin: "0.75rem 0 0" }}>{activeHoleDetails.assist}</p>}
              <Button style={{ marginTop: "0.75rem" }} size="sm" onClick={() => setActiveHole(null)}>
                Dismiss
              </Button>
            </aside>
          )}
        </div>
      )}
    </Card>
  );
}

const collapsibleStyle: React.CSSProperties = {
  background: "rgba(15, 23, 42, 0.6)",
  borderRadius: "0.75rem",
  padding: "0.75rem 1rem",
  border: "1px solid rgba(148, 163, 184, 0.2)",
};

const summaryStyle: React.CSSProperties = {
  fontWeight: 600,
  cursor: "pointer",
  outline: "none",
  display: "flex",
  alignItems: "center",
};

const chipStyle: React.CSSProperties = {
  borderRadius: "999px",
  paddingInline: "0.75rem",
  paddingBlock: "0.25rem",
};

const assistPanelStyle: React.CSSProperties = {
  border: "1px solid rgba(148,163,184,0.35)",
  borderRadius: "0.75rem",
  padding: "1rem",
  background: "rgba(15, 23, 42, 0.9)",
  display: "grid",
  gap: "0.5rem",
};
