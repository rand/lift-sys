import { useMemo } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ReactFlow, Background } from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { Card } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Badge } from "../components/ui/badge";
import { api } from "../lib/api";

type PlannerData = {
  steps: Array<{ identifier: string; description: string; prerequisites?: string[] }>;
  telemetry?: {
    nodes?: Array<{ id: string; label: string; status?: string }>;
    edges?: Array<{ source: string; target: string }>;
    assists?: Array<{ target: string; message: string }>;
    conflicts?: Record<string, string>;
  };
  ir?: Record<string, unknown> | null;
};

const statusColours: Record<string, string> = {
  completed: "#10b981",
  ready: "#facc15",
  blocked: "#ef4444",
  pending: "#475569",
};

export function PlannerView() {
  const queryClient = useQueryClient();
  const { data, refetch, isFetching } = useQuery<PlannerData | null>({
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

  const plannerGraph = useMemo(() => buildPlannerGraph(data), [data]);

  const forwardMutation = useMutation({
    mutationFn: async () => {
      if (!data?.ir) return null;
      const response = await api.post("/forward", { ir: data.ir });
      return response.data;
    },
  });

  const reverseMutation = useMutation({
    mutationFn: async () => {
      const response = await api.post("/reverse", {
        module: "module.py",
        queries: ["security/default"],
        entrypoint: "main",
      });
      queryClient.invalidateQueries({ queryKey: ["plan"] });
      return response.data;
    },
  });

  return (
    <Card title="Planner">
      <div style={toolbarStyle}>
        <Button variant="outline" onClick={() => reverseMutation.mutate()} disabled={reverseMutation.isPending}>
          {reverseMutation.isPending ? "Re-running Reverse…" : "Re-run Reverse"}
        </Button>
        <Button variant="outline" onClick={() => refetch()} disabled={isFetching}>
          Refresh Plan
        </Button>
        <Button variant="outline" onClick={() => forwardMutation.mutate()} disabled={forwardMutation.isPending || !data?.ir}>
          {forwardMutation.isPending ? "Generating…" : "Re-run Forward"}
        </Button>
        <Button
          variant="ghost"
          onClick={() => queryClient.invalidateQueries({ queryKey: ["plan"] })}
          disabled={!data?.telemetry?.assists?.length}
        >
          Resolve Holes
        </Button>
      </div>

      {!data && <p>No plan available.</p>}

      {data && (
        <div style={{ display: "grid", gap: "1.5rem" }}>
          <div style={{ height: 320, background: "#0f172a", borderRadius: "0.75rem", overflow: "hidden" }}>
            <ReactFlow nodes={plannerGraph.nodes} edges={plannerGraph.edges} fitView fitViewOptions={{ padding: 0.2 }}>
              <Background gap={16} size={1} color="rgba(148,163,184,0.1)" />
            </ReactFlow>
          </div>

          <section style={{ display: "grid", gap: "0.75rem" }}>
            <h3 style={{ margin: 0 }}>Planner Assists</h3>
            <div style={{ display: "flex", flexWrap: "wrap", gap: "0.5rem" }}>
              {data.telemetry?.assists?.length ? (
                data.telemetry.assists.map((assist) => (
                  <Badge key={assist.target} variant="info">
                    {assist.message}
                  </Badge>
                ))
              ) : (
                <span style={{ opacity: 0.7 }}>No assists pending.</span>
              )}
            </div>
          </section>

          <section style={{ display: "grid", gap: "0.75rem" }}>
            <h3 style={{ margin: 0 }}>Conflict Log</h3>
            {data.telemetry?.conflicts && Object.keys(data.telemetry.conflicts).length > 0 ? (
              <table style={tableStyle}>
                <thead>
                  <tr>
                    <th style={tableHeaderStyle}>Step</th>
                    <th style={tableHeaderStyle}>Reason</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(data.telemetry.conflicts).map(([step, reason]) => (
                    <tr key={step}>
                      <td style={tableCellStyle}>{step}</td>
                      <td style={tableCellStyle}>{reason}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <span style={{ opacity: 0.7 }}>No conflicts captured.</span>
            )}
          </section>
        </div>
      )}
    </Card>
  );
}

function buildPlannerGraph(data: PlannerData | null | undefined) {
  if (!data?.steps?.length) {
    return { nodes: [], edges: [] };
  }

  const stepLookup = new Map(data.steps.map((step) => [step.identifier, step]));
  const levelCache = new Map<string, number>();

  const computeLevel = (identifier: string, depth = 0): number => {
    if (depth > data.steps.length) {
      return 0;
    }
    if (levelCache.has(identifier)) {
      return levelCache.get(identifier)!;
    }
    const step = stepLookup.get(identifier);
    if (!step || !step.prerequisites || step.prerequisites.length === 0) {
      levelCache.set(identifier, 0);
      return 0;
    }
    const level = Math.max(
      ...step.prerequisites.map((dependency) => computeLevel(dependency, depth + 1))
    ) + 1;
    levelCache.set(identifier, level);
    return level;
  };

  const levelCounts = new Map<number, number>();
  const nodes = (data.telemetry?.nodes ?? data.steps.map((step) => ({ id: step.identifier, label: step.description }))).map(
    (node) => {
      const level = computeLevel(node.id);
      const positionIndex = levelCounts.get(level) ?? 0;
      levelCounts.set(level, positionIndex + 1);
      const status = node.status ?? "pending";
      return {
        id: node.id,
        data: { label: node.label },
        position: { x: level * 220, y: positionIndex * 120 },
        style: {
          background: statusColours[status] ?? "#1e293b",
          color: status === "pending" ? "#e2e8f0" : "#0f172a",
          borderRadius: 12,
          padding: 12,
          width: 200,
          boxShadow: "0 10px 20px rgba(15,23,42,0.3)",
          border: "1px solid rgba(148,163,184,0.25)",
        },
      };
    }
  );

  const edges = (data.telemetry?.edges ?? []).map((edge) => ({
    id: `${edge.source}-${edge.target}`,
    source: edge.source,
    target: edge.target,
    style: { stroke: "rgba(148,163,184,0.45)", strokeWidth: 2 },
  }));

  if (edges.length === 0) {
    for (const step of data.steps) {
      for (const dependency of step.prerequisites ?? []) {
        edges.push({
          id: `${dependency}-${step.identifier}`,
          source: dependency,
          target: step.identifier,
          style: { stroke: "rgba(148,163,184,0.45)", strokeWidth: 2 },
        });
      }
    }
  }

  return { nodes, edges };
}

const toolbarStyle: React.CSSProperties = {
  display: "flex",
  gap: "0.75rem",
  flexWrap: "wrap",
  marginBottom: "1.5rem",
};

const tableStyle: React.CSSProperties = {
  width: "100%",
  borderCollapse: "collapse",
  border: "1px solid rgba(148,163,184,0.25)",
};

const tableHeaderStyle: React.CSSProperties = {
  textAlign: "left",
  padding: "0.5rem 0.75rem",
  borderBottom: "1px solid rgba(148,163,184,0.25)",
  background: "rgba(15,23,42,0.6)",
};

const tableCellStyle: React.CSSProperties = {
  padding: "0.5rem 0.75rem",
  borderBottom: "1px solid rgba(148,163,184,0.15)",
};
