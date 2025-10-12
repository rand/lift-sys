/**
 * Prompt Workbench View
 *
 * Interactive UI for creating and refining natural language specifications
 * into IR through iterative hole resolution.
 */

import { useState, useEffect } from "react";
import { CheckCircle2, X, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { ScrollArea } from "@/components/ui/scroll-area";
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
    <div className="grid grid-cols-[300px_1fr] gap-6 h-full">
      {/* Session List Sidebar */}
      <div className="flex flex-col gap-4">
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-xl">Sessions</CardTitle>
          </CardHeader>
          <CardContent>
            <Button onClick={() => void loadSessions()} variant="outline" className="w-full">
              <RefreshCw className="h-4 w-4 mr-2" />
              Refresh
            </Button>
          </CardContent>
        </Card>

        <ScrollArea className="flex-1">
          <div className="flex flex-col gap-2">
            {sessions.length === 0 && (
              <p className="text-sm text-muted-foreground italic px-2">
                No sessions yet. Create one to get started.
              </p>
            )}
            {sessions.map(session => (
              <Card
                key={session.session_id}
                className={`cursor-pointer transition-colors ${
                  activeSession?.session_id === session.session_id
                    ? "bg-accent border-brand"
                    : "hover:bg-accent/50"
                }`}
                onClick={() => void handleSelectSession(session)}
              >
                <CardContent className="p-3">
                  <div className="flex justify-between items-start gap-2">
                    <div className="flex-1 min-w-0">
                      <div className="text-sm font-medium truncate">
                        {session.session_id.substring(0, 8)}...
                      </div>
                      <div className="flex gap-2 mt-1">
                        <Badge variant="secondary" className="text-xs">
                          {session.status}
                        </Badge>
                        <span className="text-xs text-muted-foreground">
                          {session.ambiguities.length} holes
                        </span>
                      </div>
                    </div>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-6 w-6"
                      onClick={(e) => {
                        e.stopPropagation();
                        void handleDelete(session.session_id);
                      }}
                    >
                      <X className="h-4 w-4" />
                    </Button>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </ScrollArea>
      </div>

      {/* Main Content */}
      <ScrollArea className="flex-1">
        <div className="flex flex-col gap-6">
          {/* Create Session Form */}
          <Card>
            <CardHeader>
              <CardTitle className="text-2xl">Prompt Workbench</CardTitle>
              <CardDescription>
                Describe your specification in natural language. The system will translate it to IR and identify ambiguities.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <Textarea
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                placeholder="e.g., A function that takes two integers and returns their sum..."
                className="min-h-[120px] resize-y"
              />
              {error && (
                <Alert variant="destructive">
                  <AlertDescription>{error}</AlertDescription>
                </Alert>
              )}
            </CardContent>
            <CardFooter>
              <Button onClick={() => void handleCreateSession()} disabled={isLoading || !prompt.trim()} className="w-full">
                {isLoading ? "Creating..." : "Create Session"}
              </Button>
            </CardFooter>
          </Card>

          {/* Active Session Details */}
          {activeSession && (
            <>
              {/* Session Info */}
              <Card>
                <CardHeader>
                  <div className="flex justify-between items-start">
                    <div className="space-y-2">
                      <CardTitle>Session {activeSession.session_id.substring(0, 12)}</CardTitle>
                      <div className="flex flex-wrap gap-2 text-sm">
                        <div className="flex items-center gap-2">
                          <span className="text-muted-foreground">Status:</span>
                          <Badge>{activeSession.status}</Badge>
                        </div>
                        <Separator orientation="vertical" className="h-4" />
                        <div className="flex items-center gap-2">
                          <span className="text-muted-foreground">Draft:</span>
                          <Badge variant="secondary">v{activeSession.current_draft?.version ?? 0}</Badge>
                        </div>
                        <Separator orientation="vertical" className="h-4" />
                        <div className="flex items-center gap-2">
                          <span className="text-muted-foreground">Validation:</span>
                          <Badge variant="outline">{activeSession.current_draft?.validation_status ?? "N/A"}</Badge>
                        </div>
                      </div>
                    </div>
                    {activeSession.status === "active" && activeSession.ambiguities.length === 0 && (
                      <Button onClick={() => void handleFinalize()} disabled={isLoading}>
                        <CheckCircle2 className="h-4 w-4 mr-2" />
                        Finalize
                      </Button>
                    )}
                  </div>
                </CardHeader>
              </Card>

              {/* IR Preview */}
              {activeSession.current_draft && (
                <Card>
                  <CardHeader>
                    <CardTitle>Intermediate Representation</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <ScrollArea className="h-[300px]">
                      <pre className="text-sm font-mono bg-muted p-4 rounded-md">
                        {JSON.stringify(activeSession.current_draft.ir, null, 2)}
                      </pre>
                    </ScrollArea>
                  </CardContent>
                </Card>
              )}

              {/* Ambiguities & Resolution */}
              {activeSession.ambiguities.length > 0 && (
                <Card>
                  <CardHeader>
                    <CardTitle>
                      Ambiguities ({activeSession.ambiguities.length})
                    </CardTitle>
                    <CardDescription>
                      Resolve these ambiguities to refine your specification.
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    {activeSession.ambiguities.map(holeId => {
                      const assist = assists.find(a => a.hole_id === holeId);

                      return (
                        <Card key={holeId}>
                          <CardContent className="pt-6 space-y-4">
                            <div className="space-y-2">
                              <code className="text-sm font-semibold bg-muted px-2 py-1 rounded">
                                {holeId}
                              </code>
                              {assist && (
                                <p className="text-sm text-muted-foreground mt-2">
                                  {assist.context}
                                </p>
                              )}
                            </div>

                            {assist && assist.suggestions.length > 0 && (
                              <div className="space-y-2">
                                <p className="text-xs text-muted-foreground">Suggestions:</p>
                                <div className="flex flex-wrap gap-2">
                                  {assist.suggestions.map((suggestion, idx) => (
                                    <Button
                                      key={idx}
                                      variant="secondary"
                                      size="sm"
                                      className="text-xs h-7"
                                      onClick={() => setResolutionInputs(prev => ({ ...prev, [holeId]: suggestion }))}
                                    >
                                      {suggestion}
                                    </Button>
                                  ))}
                                </div>
                              </div>
                            )}

                            <div className="flex gap-2">
                              <Input
                                value={resolutionInputs[holeId] ?? ""}
                                onChange={(e) => setResolutionInputs(prev => ({ ...prev, [holeId]: e.target.value }))}
                                placeholder="Enter resolution..."
                                className="flex-1"
                              />
                              <Button
                                onClick={() => void handleResolveHole(holeId)}
                                disabled={isLoading || !resolutionInputs[holeId]?.trim()}
                                size="sm"
                              >
                                Resolve
                              </Button>
                            </div>
                          </CardContent>
                        </Card>
                      );
                    })}
                  </CardContent>
                </Card>
              )}

              {/* Success State */}
              {activeSession.status === "finalized" && (
                <Alert variant="success">
                  <CheckCircle2 className="h-4 w-4" />
                  <AlertDescription>
                    Session finalized! The IR is now ready for code generation.
                  </AlertDescription>
                </Alert>
              )}
            </>
          )}
        </div>
      </ScrollArea>
    </div>
  );
}
