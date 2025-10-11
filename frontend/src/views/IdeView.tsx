import { useEffect, useMemo, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Card } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Badge } from "../components/ui/badge";
import { api } from "../lib/api";
import { useProgressStream } from "../lib/useProgressStream";

type PlanSnapshot = {
  ir?: Record<string, unknown>;
};

type ForwardResponse = {
  request_payload: {
    prompt: { constraints: Array<{ name: string; value: string; metadata?: Record<string, string> }> };
    stream?: string[];
    telemetry?: Array<Record<string, unknown>>;
  };
};

export function IdeView() {
  const { data: plan } = useQuery<PlanSnapshot | null>({
    queryKey: ["plan"],
    queryFn: async () => {
      try {
        const response = await api.get("/plan");
        return response.data;
      } catch (error: any) {
        if (error?.response?.status === 404) {
          return null;
        }
        throw error;
      }
    },
    staleTime: 1000 * 10,
  });
  const { events, status, clear } = useProgressStream();
  const [payload, setPayload] = useState<ForwardResponse | null>(null);
  const [isPaused, setIsPaused] = useState(false);
  const consoleBuffer = useRef(new Set<string>());
  const [consoleMessages, setConsoleMessages] = useState<string[]>([]);

  const runForward = async () => {
    if (!plan?.ir) {
      return;
    }
    const { data } = await api.post<ForwardResponse>("/forward", { ir: plan.ir });
    setPayload(data);
    consoleBuffer.current.clear();
    setConsoleMessages([]);
  };

  const constraints = useMemo(() => payload?.request_payload.prompt.constraints ?? [], [payload]);
  const forwardEvents = useMemo(() => events.filter((event) => event.scope === "forward"), [events]);

  useEffect(() => {
    if (isPaused) {
      return;
    }
    setConsoleMessages((previous) => {
      const next = [...previous];
      for (const event of forwardEvents) {
        const key = `${event.timestamp}-${event.stage}-${event.status}-${event.message}`;
        if (!consoleBuffer.current.has(key)) {
          consoleBuffer.current.add(key);
          const label = event.stage ?? event.type;
          const statusLabel = event.status ? ` (${event.status})` : "";
          next.push(`${label}${statusLabel}: ${event.message ?? ""}`.trim());
        }
      }
      const tokens = payload?.request_payload.stream ?? [];
      tokens.forEach((token, index) => {
        const key = `token-${index}-${token}`;
        if (!consoleBuffer.current.has(key)) {
          consoleBuffer.current.add(key);
          next.push(`token ▸ ${token}`);
        }
      });
      return next.slice(-200);
    });
  }, [forwardEvents, payload, isPaused]);

  const pauseToggleLabel = isPaused ? "Resume" : "Pause";

  return (
    <Card title="Interactive IDE">
      <p>Compile the IR into generation constraints and preview payloads.</p>
      <div style={{ display: "flex", gap: "0.75rem", flexWrap: "wrap", alignItems: "center" }}>
        <Button onClick={runForward} disabled={!plan?.ir}>
          {plan?.ir ? "Generate Constraints" : "Load IR to continue"}
        </Button>
        <Button variant="ghost" onClick={() => setIsPaused((previous) => !previous)}>
          {pauseToggleLabel} Console
        </Button>
        <Button variant="ghost" onClick={() => { clear(); consoleBuffer.current.clear(); setConsoleMessages([]); }}>
          Clear Console
        </Button>
        <Badge variant="info">Stream: {status}</Badge>
      </div>

      <section style={inspectorSectionStyle}>
        <h3 style={{ marginTop: 0 }}>Constraint Inspector</h3>
        {constraints.length === 0 ? (
          <p style={{ opacity: 0.7 }}>Run forward mode to populate constraints.</p>
        ) : (
          <ul style={{ display: "grid", gap: "0.75rem", listStyle: "none", padding: 0, margin: 0 }}>
            {constraints.map((constraint, index) => (
              <li key={`${constraint.name}-${index}`} style={constraintItemStyle}>
                <div style={{ display: "flex", gap: "0.5rem", alignItems: "center", flexWrap: "wrap" }}>
                  <Badge variant="secondary">{constraint.name}</Badge>
                  <span style={{ fontWeight: 600 }}>{constraint.value}</span>
                </div>
                {constraint.metadata && Object.keys(constraint.metadata).length > 0 && (
                  <dl style={constraintMetaStyle}>
                    {Object.entries(constraint.metadata).map(([key, value]) => (
                      <div key={key} style={{ display: "flex", gap: "0.5rem" }}>
                        <dt style={{ textTransform: "capitalize", opacity: 0.7 }}>{key}</dt>
                        <dd style={{ margin: 0 }}>{value}</dd>
                      </div>
                    ))}
                  </dl>
                )}
              </li>
            ))}
          </ul>
        )}
      </section>

      <section style={consoleSectionStyle}>
        <header style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <h3 style={{ margin: 0 }}>Execution Console</h3>
          {payload?.request_payload.telemetry && (
            <Badge variant="secondary">{payload.request_payload.telemetry.length} telemetry events</Badge>
          )}
        </header>
        <div style={consoleLogStyle} role="log" aria-live={isPaused ? "off" : "polite"}>
          {consoleMessages.length === 0 && <span style={{ opacity: 0.7 }}>No runtime output yet.</span>}
          {consoleMessages.map((line, index) => (
            <div key={`${line}-${index}`} style={{ fontFamily: "monospace" }}>
              {line}
            </div>
          ))}
        </div>
      </section>
    </Card>
  );
}

const inspectorSectionStyle: React.CSSProperties = {
  marginTop: "1.5rem",
  display: "grid",
  gap: "1rem",
};

const constraintItemStyle: React.CSSProperties = {
  border: "1px solid rgba(148,163,184,0.25)",
  borderRadius: "0.75rem",
  padding: "0.75rem",
  background: "rgba(15,23,42,0.6)",
  display: "grid",
  gap: "0.5rem",
};

const constraintMetaStyle: React.CSSProperties = {
  margin: 0,
  display: "grid",
  gap: "0.35rem",
};

const consoleSectionStyle: React.CSSProperties = {
  marginTop: "1.5rem",
  display: "grid",
  gap: "0.75rem",
};

const consoleLogStyle: React.CSSProperties = {
  background: "#020617",
  color: "#e2e8f0",
  padding: "1rem",
  borderRadius: "0.75rem",
  minHeight: "200px",
  maxHeight: "280px",
  overflow: "auto",
  display: "grid",
  gap: "0.35rem",
};
