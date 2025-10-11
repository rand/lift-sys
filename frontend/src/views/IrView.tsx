import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Card } from "../components/ui/card";
import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import { api } from "../lib/api";

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

export function IrView() {
  const [activeHole, setActiveHole] = useState<string | null>(null);
  const { data, isLoading, error } = useQuery<PlanSnapshot | null>({
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
  });

  const ir = data?.ir;
  const typedHoles = data?.telemetry?.typed_holes ?? [];
  const invariants = data?.telemetry?.invariants ?? [];

  const sections = useMemo(() => {
    if (!ir) {
      return [];
    }
    return sectionOrder.map((section) => {
      switch (section.id) {
        case "intent":
          return {
            ...section,
            content: (
              <div style={{ display: "grid", gap: "0.5rem" }}>
                <p>{ir.intent.summary}</p>
                {ir.intent.rationale && <p style={{ opacity: 0.8 }}>Rationale: {ir.intent.rationale}</p>}
              </div>
            ),
          };
        case "signature":
          return {
            ...section,
            content: (
              <div style={{ display: "grid", gap: "0.5rem" }}>
                <div>
                  <strong>Name:</strong> {ir.signature.name}
                </div>
                <div>
                  <strong>Returns:</strong> {ir.signature.returns ?? "void"}
                </div>
                <div>
                  <strong>Parameters</strong>
                  <ul>
                    {ir.signature.parameters.length === 0 && <li>None</li>}
                    {ir.signature.parameters.map((parameter) => (
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
                {ir.effects.length === 0 && <li>No side effects recorded.</li>}
                {ir.effects.map((effect) => (
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
                {ir.assertions.length === 0 && <li>No invariants provided.</li>}
                {ir.assertions.map((assertion) => (
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
    return typedHoles.find((hole) => hole.identifier === activeHole) ?? null;
  }, [typedHoles, activeHole]);

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
      {isLoading && <p>Loading planner snapshot…</p>}
      {error && <p role="alert">Failed to load IR snapshot.</p>}
      {!isLoading && !error && !ir && <p>Run reverse mode to generate an IR.</p>}
      {ir && (
        <div style={{ display: "grid", gap: "1.5rem" }}>
          <div style={{ display: "flex", flexWrap: "wrap", gap: "0.5rem" }}>
            {invariantBadges.map((badge) => (
              <Badge key={badge.key} variant={badge.variant}>
                {badge.predicate}
              </Badge>
            ))}
            {invariantBadges.length === 0 && <Badge variant="warning">No invariants yet</Badge>}
          </div>

          <div style={{ display: "grid", gap: "1rem" }}>
            {sections.map((section, index) => {
              const clauseHoles = typedHoles.filter((hole) => hole.clause === section.id);
              return (
                <details key={section.id} open={index === 0} style={collapsibleStyle}>
                  <summary style={summaryStyle}>{section.title}</summary>
                  <div style={{ display: "grid", gap: "0.75rem" }}>
                    {section.content}
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
                  </div>
                </details>
              );
            })}
          </div>

          {activeHoleDetails && (
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
