import { useEffect, useMemo, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
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
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Interactive IDE</CardTitle>
          <CardDescription>
            Compile the IR into generation constraints and preview payloads.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="flex gap-3 flex-wrap items-center">
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

          <Separator />

          <div className="space-y-4">
            <h3 className="text-lg font-semibold">Constraint Inspector</h3>
            {constraints.length === 0 ? (
              <p className="text-sm text-muted-foreground">Run forward mode to populate constraints.</p>
            ) : (
              <ul className="space-y-3">
                {constraints.map((constraint, index) => (
                  <li key={`${constraint.name}-${index}`}>
                    <Card className="bg-card/60">
                      <CardContent className="pt-6 space-y-2">
                        <div className="flex gap-2 items-center flex-wrap">
                          <Badge variant="secondary">{constraint.name}</Badge>
                          <span className="font-semibold text-sm">{constraint.value}</span>
                        </div>
                        {constraint.metadata && Object.keys(constraint.metadata).length > 0 && (
                          <dl className="space-y-1 text-sm">
                            {Object.entries(constraint.metadata).map(([key, value]) => (
                              <div key={key} className="flex gap-2">
                                <dt className="capitalize text-muted-foreground">{key}:</dt>
                                <dd>{value}</dd>
                              </div>
                            ))}
                          </dl>
                        )}
                      </CardContent>
                    </Card>
                  </li>
                ))}
              </ul>
            )}
          </div>

          <Separator />

          <div className="space-y-3">
            <div className="flex justify-between items-center">
              <h3 className="text-lg font-semibold">Execution Console</h3>
              {payload?.request_payload.telemetry && (
                <Badge variant="secondary">{payload.request_payload.telemetry.length} telemetry events</Badge>
              )}
            </div>
            <ScrollArea className="h-[280px] bg-slate-950 text-slate-200 p-4 rounded-lg" role="log" aria-live={isPaused ? "off" : "polite"}>
              {consoleMessages.length === 0 && <span className="text-muted-foreground">No runtime output yet.</span>}
              <div className="space-y-1">
                {consoleMessages.map((line, index) => (
                  <div key={`${line}-${index}`} className="font-mono text-sm">
                    {line}
                  </div>
                ))}
              </div>
            </ScrollArea>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
