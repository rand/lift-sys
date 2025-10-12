/**
 * Enhanced IR View with session integration and inline hole resolution
 *
 * Supports both:
 * - Plan-based IR (from reverse mode)
 * - Session-based IR (from prompt workbench)
 */

import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { AlertCircle, ChevronDown } from "lucide-react";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Separator } from "@/components/ui/separator";
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
              <div className="space-y-2">
                <p className="text-sm">{irData.intent?.summary || "No intent specified"}</p>
                {irData.intent?.rationale && (
                  <p className="text-sm text-muted-foreground">
                    Rationale: {irData.intent.rationale}
                  </p>
                )}
              </div>
            ),
          };
        case "signature":
          return {
            ...section,
            content: (
              <div className="space-y-2 text-sm">
                <div>
                  <strong>Name:</strong> {irData.signature?.name || "unknown"}
                </div>
                <div>
                  <strong>Returns:</strong> {irData.signature?.returns ?? "void"}
                </div>
                <div>
                  <strong>Parameters</strong>
                  <ul className="list-disc list-inside mt-1 space-y-1">
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
              <ul className="list-disc list-inside text-sm space-y-1">
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
              <ul className="space-y-2">
                {(!irData.assertions || irData.assertions.length === 0) && <li className="text-sm">No invariants provided.</li>}
                {irData.assertions?.map((assertion: any) => (
                  <li key={assertion.predicate}>
                    <div className="font-semibold text-sm">{assertion.predicate}</div>
                    {assertion.rationale && (
                      <div className="text-xs text-muted-foreground mt-1">{assertion.rationale}</div>
                    )}
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
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Intermediate Representation</CardTitle>
          <CardDescription>
            View and resolve IR from reverse mode plans or prompt workbench sessions
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Source Selector */}
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-sm text-muted-foreground">Source:</span>
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
            <div className="space-y-2">
              <Label>Select Session</Label>
              <Select value={selectedSessionId ?? ""} onValueChange={(value) => setSelectedSessionId(value || null)}>
                <SelectTrigger>
                  <SelectValue placeholder="-- Select a session --" />
                </SelectTrigger>
                <SelectContent>
                  {sessionsData?.sessions.map((session) => (
                    <SelectItem key={session.session_id} value={session.session_id}>
                      {session.session_id.substring(0, 12)}... ({session.status}, {session.ambiguities.length} holes)
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          )}

          {/* Session Status */}
          {source === "session" && sessionData && (
            <Card className="bg-muted/50">
              <CardContent className="pt-6">
                <div className="flex flex-wrap gap-4 text-sm">
                  <div className="flex items-center gap-2">
                    <span className="text-muted-foreground">Status:</span>
                    <Badge>{sessionData.status}</Badge>
                  </div>
                  <Separator orientation="vertical" className="h-4" />
                  <div className="flex items-center gap-2">
                    <span className="text-muted-foreground">Draft:</span>
                    <Badge variant="secondary">v{sessionData.current_draft?.version ?? 0}</Badge>
                  </div>
                  <Separator orientation="vertical" className="h-4" />
                  <div className="flex items-center gap-2">
                    <span className="text-muted-foreground">Validation:</span>
                    <Badge variant="outline">{sessionData.current_draft?.validation_status ?? "N/A"}</Badge>
                  </div>
                  <Separator orientation="vertical" className="h-4" />
                  <div className="flex items-center gap-2">
                    <span className="text-muted-foreground">Holes:</span>
                    <Badge variant="warning">{sessionData.ambiguities.length}</Badge>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}

          {isLoading && <p className="text-sm text-muted-foreground">Loading IR…</p>}
          {error && (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>Failed to load IR.</AlertDescription>
            </Alert>
          )}
          {!isLoading && !error && !ir && (
            <p className="text-sm text-muted-foreground">
              {source === "plan"
                ? "Run reverse mode to generate an IR."
                : "Select a session to view its IR."}
            </p>
          )}

          {ir && (
            <>
              {/* Invariant Badges */}
              {invariantBadges.length > 0 && (
                <div className="flex flex-wrap gap-2">
                  {invariantBadges.map((badge) => (
                    <Badge key={badge.key} variant={badge.variant}>
                      {badge.predicate}
                    </Badge>
                  ))}
                </div>
              )}

              {/* IR Sections */}
              <div className="space-y-4">
                {sections.map((section, index) => {
                  const clauseHoles = typedHoles.filter((hole) => hole.clause === section.id);
                  const sessionClauseHoles = sessionHoles.filter((holeId) => holeId.includes(section.id));
                  const hasHoles = clauseHoles.length > 0 || sessionClauseHoles.length > 0;

                  return (
                    <Card key={section.id} className="bg-card/60">
                      <details open={index === 0}>
                        <summary className="cursor-pointer font-semibold flex items-center gap-2 p-6 hover:opacity-80 transition-opacity">
                          <ChevronDown className="h-4 w-4 transition-transform [[open]>&]:rotate-180" />
                          {section.title}
                          {hasHoles && (
                            <Badge variant="warning" className="ml-2 text-xs">
                              {clauseHoles.length + sessionClauseHoles.length} holes
                            </Badge>
                          )}
                        </summary>
                        <CardContent className="space-y-3 pt-0">
                          {section.content}

                          {/* Plan-based typed holes */}
                          {clauseHoles.length > 0 && (
                            <div className="flex flex-wrap gap-2">
                              {clauseHoles.map((hole) => (
                                <Button
                                  key={hole.identifier}
                                  size="sm"
                                  variant={activeHole === hole.identifier ? "default" : "outline"}
                                  onClick={() => setActiveHole((current) => (current === hole.identifier ? null : hole.identifier))}
                                  className="rounded-full"
                                >
                                  {`<?${hole.identifier}: ${hole.type_hint}>`}
                                </Button>
                              ))}
                            </div>
                          )}

                          {/* Session-based holes with inline resolution */}
                          {source === "session" && sessionClauseHoles.length > 0 && (
                            <div className="space-y-3">
                              {sessionClauseHoles.map((holeId) => (
                                <Card key={holeId} className="border-warning bg-warning/5">
                                  <CardContent className="pt-6 space-y-3">
                                    <code className="text-sm font-medium text-warning">
                                      {holeId}
                                    </code>
                                    {activeHole === holeId ? (
                                      <div className="flex gap-2 items-end">
                                        <div className="flex-1">
                                          <Input
                                            value={resolutionText}
                                            onChange={(e) => setResolutionText(e.target.value)}
                                            placeholder="Enter resolution..."
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
                                  </CardContent>
                                </Card>
                              ))}
                            </div>
                          )}
                        </CardContent>
                      </details>
                    </Card>
                  );
                })}
              </div>

              {/* Assist Panel for Plan-based holes */}
              {activeHoleDetails && source === "plan" && (
                <Card className="bg-accent/90" aria-live="polite">
                  <CardHeader>
                    <CardTitle className="text-base">Planner Assist</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    <p className="text-sm opacity-85">
                      {activeHoleDetails.description || "No description provided."}
                    </p>
                    <Badge variant="info">
                      {clauseLabels[activeHoleDetails.clause as keyof typeof clauseLabels]}
                    </Badge>
                    {activeHoleDetails.assist && (
                      <p className="text-sm mt-3">{activeHoleDetails.assist}</p>
                    )}
                    <Button size="sm" onClick={() => setActiveHole(null)}>
                      Dismiss
                    </Button>
                  </CardContent>
                </Card>
              )}
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
