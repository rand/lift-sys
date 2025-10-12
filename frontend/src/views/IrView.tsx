import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { AlertCircle, ChevronDown } from "lucide-react";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { api } from "@/lib/api";

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
              <div className="space-y-2">
                <p className="text-sm">{ir.intent.summary}</p>
                {ir.intent.rationale && (
                  <p className="text-sm text-muted-foreground">
                    Rationale: {ir.intent.rationale}
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
                  <strong>Name:</strong> {ir.signature.name}
                </div>
                <div>
                  <strong>Returns:</strong> {ir.signature.returns ?? "void"}
                </div>
                <div>
                  <strong>Parameters</strong>
                  <ul className="list-disc list-inside mt-1 space-y-1">
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
              <ul className="list-disc list-inside text-sm space-y-1">
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
              <ul className="space-y-2">
                {ir.assertions.length === 0 && <li className="text-sm">No invariants provided.</li>}
                {ir.assertions.map((assertion) => (
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
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Intermediate Representation</CardTitle>
          <CardDescription>
            View IR structure from reverse mode with typed holes and invariants
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {isLoading && <p className="text-sm text-muted-foreground">Loading planner snapshot…</p>}
          {error && (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>Failed to load IR snapshot.</AlertDescription>
            </Alert>
          )}
          {!isLoading && !error && !ir && (
            <p className="text-sm text-muted-foreground">Run reverse mode to generate an IR.</p>
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
              {invariantBadges.length === 0 && (
                <Badge variant="warning">No invariants yet</Badge>
              )}

              {/* IR Sections */}
              <div className="space-y-4">
                {sections.map((section, index) => {
                  const clauseHoles = typedHoles.filter((hole) => hole.clause === section.id);
                  const hasHoles = clauseHoles.length > 0;

                  return (
                    <Card key={section.id} className="bg-card/60">
                      <details open={index === 0}>
                        <summary className="cursor-pointer font-semibold flex items-center gap-2 p-6 hover:opacity-80 transition-opacity">
                          <ChevronDown className="h-4 w-4 transition-transform [[open]>&]:rotate-180" />
                          {section.title}
                          {hasHoles && (
                            <Badge variant="warning" className="ml-2 text-xs">
                              {clauseHoles.length} holes
                            </Badge>
                          )}
                        </summary>
                        <CardContent className="space-y-3 pt-0">
                          {section.content}
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
                        </CardContent>
                      </details>
                    </Card>
                  );
                })}
              </div>

              {/* Assist Panel */}
              {activeHoleDetails && (
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
