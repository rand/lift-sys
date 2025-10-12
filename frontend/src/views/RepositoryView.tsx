import { useMutation, useQuery } from "@tanstack/react-query";
import { useEffect, useMemo, useRef, useState } from "react";
import { RefreshCw, CheckCircle2, AlertCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Separator } from "@/components/ui/separator";
import { ScrollArea } from "@/components/ui/scroll-area";
import { api } from "../lib/api";
import { useProgressStream } from "../lib/useProgressStream";

type ProgressAction = { label: string; value?: string };
type ProgressCheckpoint = {
  id: string;
  label: string;
  status: string;
  message?: string;
  timestamp?: string;
  actions?: ProgressAction[];
};

type RepositorySummary = {
  identifier: string;
  owner: string;
  name: string;
  description?: string | null;
  defaultBranch: string;
  private: boolean;
  lastSynced?: string | null;
};

type RepositoryMetadata = RepositorySummary & {
  workspacePath?: string | null;
  source: string;
};

const statusBadges: Record<string, string> = {
  completed: "success",
  running: "info",
  ready: "warning",
  failed: "error",
};

export function RepositoryView() {
  const [selectedRepo, setSelectedRepo] = useState<RepositorySummary | null>(null);
  const [activeRepository, setActiveRepository] = useState<RepositoryMetadata | null>(null);
  const [moduleName, setModuleName] = useState("module.py");
  const [entrypoint, setEntrypoint] = useState("main");
  const [timeline, setTimeline] = useState<ProgressCheckpoint[]>([]);
  const [selectedAction, setSelectedAction] = useState<string | null>(null);
  const processedEvents = useRef(new Set<string>());
  const { events } = useProgressStream();
  const reverseEvents = useMemo(() => events.filter((event) => event.scope === "reverse"), [events]);

  const repositoriesQuery = useQuery({
    queryKey: ["repositories"],
    queryFn: async () => {
      const response = await api.get("/repos");
      return (response.data.repositories ?? []) as RepositorySummary[];
    },
  });

  useEffect(() => {
    if (!repositoriesQuery.data || repositoriesQuery.data.length === 0) {
      return;
    }
    setSelectedRepo((current) => current ?? repositoriesQuery.data[0]);
  }, [repositoriesQuery.data]);

  const openRepo = useMutation({
    mutationFn: async () => {
      if (!selectedRepo) {
        throw new Error("Repository selection required");
      }
      const response = await api.post("/repos/open", { identifier: selectedRepo.identifier });
      return response.data as { repository: RepositoryMetadata };
    },
    onSuccess: (data) => {
      setActiveRepository(data.repository);
      repositoriesQuery.refetch();
    },
  });

  const reverseMutation = useMutation({
    mutationFn: async () => {
      const response = await api.post("/reverse", {
        module: moduleName,
        queries: ["security/default"],
        entrypoint,
      });
      processedEvents.current = new Set();
      setTimeline(response.data.progress ?? []);
      return response.data;
    },
  });

  useEffect(() => {
    if (!timeline.length || !reverseEvents.length) {
      return;
    }
    setTimeline((previous) => {
      let changed = false;
      const next = previous.map((checkpoint) => {
        const latest = reverseEvents
          .filter((event) => event.stage === checkpoint.id)
          .find((event) => {
            const key = `${event.stage}-${event.status}-${event.timestamp}`;
            if (!processedEvents.current.has(key)) {
              processedEvents.current.add(key);
              return true;
            }
            return false;
          });
        if (!latest) {
          return checkpoint;
        }
        changed = true;
        return {
          ...checkpoint,
          status: latest.status ?? checkpoint.status,
          message: latest.message ?? checkpoint.message,
          timestamp: latest.timestamp ?? checkpoint.timestamp,
        };
      });
      return changed ? next : previous;
    });
  }, [reverseEvents, timeline.length]);

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Repository</CardTitle>
          <CardDescription>
            Connect one of your GitHub repositories to lift specifications.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="space-y-4">
            <div className="flex justify-between items-center flex-wrap gap-2">
              <h3 className="text-lg font-semibold">Repositories</h3>
              <Button
                variant="outline"
                size="sm"
                onClick={() => repositoriesQuery.refetch()}
                disabled={repositoriesQuery.isLoading}
              >
                <RefreshCw className="h-4 w-4 mr-2" />
                Refresh
              </Button>
            </div>
            {repositoriesQuery.isLoading ? (
              <p className="text-sm text-muted-foreground">Loading repositories…</p>
            ) : repositoriesQuery.isError ? (
              <Alert variant="destructive">
                <AlertCircle className="h-4 w-4" />
                <AlertDescription>
                  Unable to load repositories. Ensure GitHub access is configured.
                </AlertDescription>
              </Alert>
            ) : repositoriesQuery.data && repositoriesQuery.data.length > 0 ? (
              <div className="grid gap-3 grid-cols-1 md:grid-cols-2 lg:grid-cols-3">
                {repositoriesQuery.data.map((repo) => {
                  const isSelected = selectedRepo?.identifier === repo.identifier;
                  return (
                    <Card
                      key={repo.identifier}
                      className={`cursor-pointer transition-all ${
                        isSelected
                          ? "border-brand bg-accent"
                          : "hover:bg-accent/50"
                      }`}
                      onClick={() => setSelectedRepo(repo)}
                    >
                      <CardContent className="p-4 space-y-2">
                        <div className="font-semibold text-base">{repo.name}</div>
                        <div className="text-sm text-muted-foreground">{repo.owner}</div>
                        {repo.description && (
                          <p className="text-sm text-muted-foreground line-clamp-2">
                            {repo.description}
                          </p>
                        )}
                        <div className="text-xs text-muted-foreground pt-2">
                          Default branch: {repo.defaultBranch}
                          {repo.lastSynced && ` • Synced ${new Date(repo.lastSynced).toLocaleTimeString()}`}
                        </div>
                      </CardContent>
                    </Card>
                  );
                })}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">No repositories available. Connect GitHub to continue.</p>
            )}
          </div>

          <div className="grid gap-4 md:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor="module">Module</Label>
              <Input
                id="module"
                value={moduleName}
                onChange={(event) => setModuleName(event.target.value)}
                placeholder="module.py"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="entrypoint">Entrypoint</Label>
              <Input
                id="entrypoint"
                value={entrypoint}
                onChange={(event) => setEntrypoint(event.target.value)}
                placeholder="main"
              />
            </div>
          </div>

          <div className="flex gap-3 flex-wrap">
            <Button onClick={() => openRepo.mutate()} disabled={!selectedRepo || openRepo.isPending}>
              {openRepo.isPending ? "Opening…" : "Open Repository"}
            </Button>
            <Button
              variant="outline"
              onClick={() => reverseMutation.mutate()}
              disabled={reverseMutation.isPending || openRepo.isError || !activeRepository}
            >
              {reverseMutation.isPending ? "Scanning…" : "Run Reverse Scan"}
            </Button>
          </div>

          {openRepo.isSuccess && activeRepository && (
            <Alert variant="success">
              <CheckCircle2 className="h-4 w-4" />
              <AlertDescription>
                Repository <strong>{activeRepository.name}</strong> synced from {activeRepository.owner}.
              </AlertDescription>
            </Alert>
          )}
          {openRepo.isError && (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>
                Unable to open repository. Check your permissions and try again.
              </AlertDescription>
            </Alert>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Repository Scan Timeline</CardTitle>
        </CardHeader>
        <CardContent>
          {timeline.length === 0 ? (
            <p className="text-sm text-muted-foreground">Trigger reverse mode to view progress checkpoints.</p>
          ) : (
            <ScrollArea className="h-[400px]">
              <ol className="space-y-4">
                {timeline.map((checkpoint) => (
                  <li key={checkpoint.id} className="border-l-2 border-brand/50 pl-4 space-y-2">
                    <div className="flex items-center gap-2 flex-wrap">
                      <Badge variant={(statusBadges[checkpoint.status] as any) ?? "secondary"}>
                        {checkpoint.label}
                      </Badge>
                      <span className="text-sm">{checkpoint.message}</span>
                    </div>
                    {checkpoint.actions && checkpoint.actions.length > 0 && (
                      <div className="flex gap-2 flex-wrap">
                        {checkpoint.actions.map((action) => (
                          <Button
                            key={action.label}
                            variant="ghost"
                            size="sm"
                            onClick={() => setSelectedAction(`${checkpoint.label}: ${action.label}${action.value ? ` (${action.value})` : ""}`)}
                          >
                            {action.label}
                          </Button>
                        ))}
                      </div>
                    )}
                    <span className="text-xs text-muted-foreground">
                      {checkpoint.timestamp ? new Date(checkpoint.timestamp).toLocaleTimeString() : "Awaiting timestamp"}
                    </span>
                  </li>
                ))}
              </ol>
            </ScrollArea>
          )}
        </CardContent>
      </Card>

      {selectedAction && (
        <Card className="bg-accent/50">
          <CardContent className="pt-6 space-y-1">
            <div className="font-semibold">Action</div>
            <div className="text-sm text-muted-foreground">{selectedAction}</div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
