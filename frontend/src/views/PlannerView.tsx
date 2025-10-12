import { useMemo } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ReactFlow, Background } from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from "@/components/ui/table";
import { Separator } from "@/components/ui/separator";
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
    <Card>
      <CardHeader>
        <CardTitle>Planner</CardTitle>
        <CardDescription>
          Visualize execution plan dependencies and resolve constraints
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        <div className="flex gap-3 flex-wrap">
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

        {!data && <p className="text-sm text-muted-foreground">No plan available.</p>}

        {data && (
          <div className="space-y-6">
            <div className="h-80 bg-slate-950 rounded-xl overflow-hidden">
              <ReactFlow nodes={plannerGraph.nodes} edges={plannerGraph.edges} fitView fitViewOptions={{ padding: 0.2 }}>
                <Background gap={16} size={1} color="rgba(148,163,184,0.1)" />
              </ReactFlow>
            </div>

            <section className="space-y-3">
              <h3 className="text-lg font-semibold m-0">Planner Assists</h3>
              <div className="flex flex-wrap gap-2">
                {data.telemetry?.assists?.length ? (
                  data.telemetry.assists.map((assist) => (
                    <Badge key={assist.target} variant="info">
                      {assist.message}
                    </Badge>
                  ))
                ) : (
                  <span className="text-sm text-muted-foreground">No assists pending.</span>
                )}
              </div>
            </section>

            <section className="space-y-3">
              <h3 className="text-lg font-semibold m-0">Conflict Log</h3>
              {data.telemetry?.conflicts && Object.keys(data.telemetry.conflicts).length > 0 ? (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Step</TableHead>
                      <TableHead>Reason</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {Object.entries(data.telemetry.conflicts).map(([step, reason]) => (
                      <TableRow key={step}>
                        <TableCell>{step}</TableCell>
                        <TableCell>{reason}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              ) : (
                <span className="text-sm text-muted-foreground">No conflicts captured.</span>
              )}
            </section>
          </div>
        )}
      </CardContent>
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
