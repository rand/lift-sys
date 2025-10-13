import { useMutation, useQuery } from "@tanstack/react-query";
import { useEffect, useMemo, useRef, useState } from "react";
import { RefreshCw, CheckCircle2, AlertCircle, Search, Filter, FileCode, File, ArrowLeft } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Separator } from "@/components/ui/separator";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
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
  const [analyzeMode, setAnalyzeMode] = useState<"project" | "file">("project");
  const [moduleName, setModuleName] = useState("module.py");
  const [entrypoint, setEntrypoint] = useState("main");
  const [timeline, setTimeline] = useState<ProgressCheckpoint[]>([]);
  const [selectedAction, setSelectedAction] = useState<string | null>(null);
  const [analysisResults, setAnalysisResults] = useState<any[] | null>(null);
  const [resultsSearchQuery, setResultsSearchQuery] = useState("");
  const [currentFileProgress, setCurrentFileProgress] = useState<{file: string, current: number, total: number} | null>(null);
  const [selectedIr, setSelectedIr] = useState<any | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [sortBy, setSortBy] = useState<"updated" | "created" | "pushed" | "full_name">("updated");
  const [sortDirection, setSortDirection] = useState<"asc" | "desc">("desc");
  const [filterPrivate, setFilterPrivate] = useState<"all" | "public" | "private">("all");
  const [page, setPage] = useState(1);
  const [allRepos, setAllRepos] = useState<RepositorySummary[]>([]);
  const processedEvents = useRef(new Set<string>());
  const { events } = useProgressStream();
  const reverseEvents = useMemo(() => events.filter((event) => event.scope === "reverse"), [events]);

  const repositoriesQuery = useQuery({
    queryKey: ["repositories", page, sortBy, sortDirection],
    queryFn: async () => {
      const response = await api.get("/api/repos", {
        params: {
          page,
          per_page: 30,
          sort: sortBy,
          direction: sortDirection,
        },
      });
      return (response.data.repositories ?? []) as RepositorySummary[];
    },
  });

  // Accumulate repos from all pages
  useEffect(() => {
    if (repositoriesQuery.data) {
      if (page === 1) {
        setAllRepos(repositoriesQuery.data);
      } else {
        setAllRepos((prev) => [...prev, ...repositoriesQuery.data]);
      }
    }
  }, [repositoriesQuery.data, page]);

  // Filter repos based on search query and privacy filter
  const filteredRepos = useMemo(() => {
    let repos = allRepos;

    // Filter by search query
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      repos = repos.filter(
        (repo) =>
          repo.name.toLowerCase().includes(query) ||
          repo.owner.toLowerCase().includes(query) ||
          repo.description?.toLowerCase().includes(query)
      );
    }

    // Filter by privacy
    if (filterPrivate !== "all") {
      repos = repos.filter((repo) =>
        filterPrivate === "private" ? repo.private : !repo.private
      );
    }

    return repos;
  }, [allRepos, searchQuery, filterPrivate]);

  // Filter analysis results based on search
  const filteredResults = useMemo(() => {
    if (!analysisResults) return null;

    if (!resultsSearchQuery) return analysisResults;

    const query = resultsSearchQuery.toLowerCase();
    return analysisResults.filter((ir) => {
      const sourcePath = ir.metadata?.source_path?.toLowerCase() || "";
      const summary = ir.intent?.summary?.toLowerCase() || "";
      const name = ir.signature?.name?.toLowerCase() || "";

      return sourcePath.includes(query) || summary.includes(query) || name.includes(query);
    });
  }, [analysisResults, resultsSearchQuery]);

  useEffect(() => {
    if (!filteredRepos || filteredRepos.length === 0) {
      return;
    }
    setSelectedRepo((current) => current ?? filteredRepos[0]);
  }, [filteredRepos]);

  const handleRefresh = () => {
    setPage(1);
    setAllRepos([]);
    repositoriesQuery.refetch();
  };

  const handleLoadMore = () => {
    setPage((prev) => prev + 1);
  };

  const hasMore = repositoriesQuery.data && repositoriesQuery.data.length === 30;

  const openRepo = useMutation({
    mutationFn: async () => {
      if (!selectedRepo) {
        throw new Error("Repository selection required");
      }
      const response = await api.post("/api/repos/open", { identifier: selectedRepo.identifier });
      return response.data as { repository: RepositoryMetadata };
    },
    onSuccess: (data) => {
      setActiveRepository(data.repository);
      repositoriesQuery.refetch();
    },
  });

  const reverseMutation = useMutation({
    mutationFn: async () => {
      const response = await api.post("/api/reverse", {
        module: analyzeMode === "project" ? null : moduleName,
        queries: ["security/default"],
        entrypoint,
        analyze_all: analyzeMode === "project",
      });
      processedEvents.current = new Set();
      setTimeline(response.data.progress ?? []);
      return response.data;
    },
    onSuccess: (data) => {
      if (data.irs && data.irs.length > 0) {
        setAnalysisResults(data.irs);
      }
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

  // Track real-time file analysis progress
  useEffect(() => {
    const fileAnalysisEvents = reverseEvents.filter((event) => event.stage === "file_analysis");
    if (fileAnalysisEvents.length === 0) {
      return;
    }

    const latest = fileAnalysisEvents[fileAnalysisEvents.length - 1];
    if (latest.status === "running" && latest.current && latest.total && latest.file) {
      setCurrentFileProgress({
        file: String(latest.file),
        current: Number(latest.current),
        total: Number(latest.total),
      });
    } else if (latest.status === "completed") {
      setCurrentFileProgress(null);
    }
  }, [reverseEvents]);

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
                onClick={handleRefresh}
                disabled={repositoriesQuery.isLoading}
              >
                <RefreshCw className="h-4 w-4 mr-2" />
                Refresh
              </Button>
            </div>

            {/* Search and Filter Controls */}
            <div className="grid gap-3 grid-cols-1 md:grid-cols-3">
              <div className="relative md:col-span-2">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="Search repositories..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-10"
                />
              </div>
              <div className="grid grid-cols-2 gap-2">
                <Select value={filterPrivate} onValueChange={(value: "all" | "public" | "private") => setFilterPrivate(value)}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Repos</SelectItem>
                    <SelectItem value="public">Public</SelectItem>
                    <SelectItem value="private">Private</SelectItem>
                  </SelectContent>
                </Select>
                <Select value={sortBy} onValueChange={(value: "updated" | "created" | "pushed" | "full_name") => { setSortBy(value); setPage(1); setAllRepos([]); }}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="updated">Recently Updated</SelectItem>
                    <SelectItem value="created">Recently Created</SelectItem>
                    <SelectItem value="pushed">Recently Pushed</SelectItem>
                    <SelectItem value="full_name">Name</SelectItem>
                  </SelectContent>
                </Select>
              </div>
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
            ) : filteredRepos && filteredRepos.length > 0 ? (
              <div className="space-y-4">
                <div className="grid gap-3 grid-cols-1 md:grid-cols-2 lg:grid-cols-3">
                  {filteredRepos.map((repo) => {
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
                          <div className="flex items-center gap-2">
                            <div className="font-semibold text-base">{repo.name}</div>
                            {repo.private && (
                              <Badge variant="secondary" className="text-xs">Private</Badge>
                            )}
                          </div>
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
                {hasMore && !searchQuery && (
                  <div className="flex justify-center">
                    <Button
                      variant="outline"
                      onClick={handleLoadMore}
                      disabled={repositoriesQuery.isLoading}
                    >
                      {repositoriesQuery.isLoading ? "Loading..." : "Load More"}
                    </Button>
                  </div>
                )}
                {searchQuery && allRepos.length > filteredRepos.length && (
                  <p className="text-sm text-muted-foreground text-center">
                    Showing {filteredRepos.length} of {allRepos.length} loaded repositories
                  </p>
                )}
              </div>
            ) : searchQuery ? (
              <p className="text-sm text-muted-foreground">No repositories match your search.</p>
            ) : (
              <p className="text-sm text-muted-foreground">No repositories available. Connect GitHub to continue.</p>
            )}
          </div>

          <Separator />

          <div className="space-y-4">
            <div>
              <h3 className="text-lg font-semibold mb-2">Reverse Mode Analysis</h3>
              <p className="text-sm text-muted-foreground">
                Extract specifications from existing code using static and dynamic analysis.
              </p>
            </div>

            {/* Analysis Mode Toggle */}
            <div className="space-y-2">
              <Label>Analysis Scope</Label>
              <div className="flex gap-2">
                <Button
                  variant={analyzeMode === "project" ? "default" : "outline"}
                  size="sm"
                  onClick={() => setAnalyzeMode("project")}
                  disabled={!activeRepository}
                >
                  <FileCode className="h-4 w-4 mr-2" />
                  Entire Project
                </Button>
                <Button
                  variant={analyzeMode === "file" ? "default" : "outline"}
                  size="sm"
                  onClick={() => setAnalyzeMode("file")}
                  disabled={!activeRepository}
                >
                  <File className="h-4 w-4 mr-2" />
                  Specific File
                </Button>
              </div>
            </div>

            {/* Conditional Inputs Based on Mode */}
            {analyzeMode === "project" ? (
              <Alert>
                <AlertDescription>
                  Will analyze all Python files in the repository, excluding common directories like venv, node_modules, and __pycache__.
                </AlertDescription>
              </Alert>
            ) : (
              <div className="grid gap-4 md:grid-cols-2">
                <div className="space-y-2">
                  <Label htmlFor="module">Target Module Path</Label>
                  <Input
                    id="module"
                    value={moduleName}
                    onChange={(event) => setModuleName(event.target.value)}
                    placeholder="src/main.py"
                    disabled={!activeRepository}
                  />
                  <p className="text-xs text-muted-foreground">
                    Path relative to repository root (e.g., src/main.py, lib/core.py)
                  </p>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="entrypoint">Entrypoint Function</Label>
                  <Input
                    id="entrypoint"
                    value={entrypoint}
                    onChange={(event) => setEntrypoint(event.target.value)}
                    placeholder="main"
                    disabled={!activeRepository}
                  />
                  <p className="text-xs text-muted-foreground">
                    Function name to analyze for dynamic invariants
                  </p>
                </div>
              </div>
            )}
          </div>

          <div className="space-y-3">
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

            {/* Real-time Progress Indicator */}
            {currentFileProgress && (
              <Alert>
                <AlertDescription>
                  <div className="space-y-2">
                    <div className="flex justify-between text-sm">
                      <span className="font-medium">Analyzing: {currentFileProgress.file}</span>
                      <span className="text-muted-foreground">
                        {currentFileProgress.current} / {currentFileProgress.total}
                      </span>
                    </div>
                    <div className="w-full bg-secondary rounded-full h-2">
                      <div
                        className="bg-brand h-2 rounded-full transition-all duration-300"
                        style={{
                          width: `${(currentFileProgress.current / currentFileProgress.total) * 100}%`,
                        }}
                      />
                    </div>
                  </div>
                </AlertDescription>
              </Alert>
            )}
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

      {/* Analysis Results */}
      {analysisResults && analysisResults.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Analysis Results</CardTitle>
            <CardDescription>
              {analysisResults.length === 1
                ? "Specification extracted from 1 file"
                : `Specifications extracted from ${analysisResults.length} files`}
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* Summary Statistics */}
            <div className="grid gap-4 md:grid-cols-3">
              <Card className="bg-accent/50">
                <CardContent className="pt-6">
                  <div className="text-2xl font-bold">{analysisResults.length}</div>
                  <div className="text-sm text-muted-foreground">Files Analyzed</div>
                </CardContent>
              </Card>
              <Card className="bg-accent/50">
                <CardContent className="pt-6">
                  <div className="text-2xl font-bold">
                    {analysisResults.reduce((acc, ir) => {
                      const holes = ir.intent?.holes?.length || 0;
                      return acc + holes;
                    }, 0)}
                  </div>
                  <div className="text-sm text-muted-foreground">Typed Holes Found</div>
                </CardContent>
              </Card>
              <Card className="bg-accent/50">
                <CardContent className="pt-6">
                  <div className="text-2xl font-bold">
                    {analysisResults.reduce((acc, ir) => {
                      const assertions = ir.assertions?.length || 0;
                      return acc + assertions;
                    }, 0)}
                  </div>
                  <div className="text-sm text-muted-foreground">Assertions Generated</div>
                </CardContent>
              </Card>
            </div>

            <Separator />

            {/* Results List */}
            <div className="space-y-2">
              <div className="flex justify-between items-center">
                <h3 className="text-sm font-semibold">Analyzed Files</h3>
                <div className="relative w-64">
                  <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                  <Input
                    placeholder="Search results..."
                    value={resultsSearchQuery}
                    onChange={(e) => setResultsSearchQuery(e.target.value)}
                    className="pl-10"
                  />
                </div>
              </div>
              {filteredResults && filteredResults.length > 0 ? (
                <>
                  <ScrollArea className="h-[300px]">
                    <div className="space-y-2">
                      {filteredResults.map((ir, idx) => (
                    <Card key={idx} className="p-4 hover:bg-accent/50 transition-colors">
                      <div className="space-y-2">
                        <div className="flex justify-between items-start gap-4">
                          <div className="flex-1 space-y-1">
                            <div className="font-mono text-sm font-semibold">
                              {ir.metadata?.source_path || `File ${idx + 1}`}
                            </div>
                            <div className="text-sm text-muted-foreground line-clamp-2">
                              {ir.intent?.summary || "No summary available"}
                            </div>
                          </div>
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => setSelectedIr(ir)}
                          >
                            View Details
                          </Button>
                        </div>
                        <div className="flex gap-2 flex-wrap">
                          <Badge variant="secondary" className="text-xs">
                            {ir.signature?.name || "Unknown"}
                          </Badge>
                          {ir.intent?.holes?.length > 0 && (
                            <Badge variant="warning" className="text-xs">
                              {ir.intent.holes.length} holes
                            </Badge>
                          )}
                          {ir.assertions?.length > 0 && (
                            <Badge variant="info" className="text-xs">
                              {ir.assertions.length} assertions
                            </Badge>
                          )}
                        </div>
                      </div>
                    </Card>
                      ))}
                    </div>
                  </ScrollArea>
                  {resultsSearchQuery && analysisResults.length > filteredResults.length && (
                    <p className="text-sm text-muted-foreground text-center">
                      Showing {filteredResults.length} of {analysisResults.length} results
                    </p>
                  )}
                </>
              ) : (
                <p className="text-sm text-muted-foreground text-center py-4">
                  No results match your search.
                </p>
              )}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Detailed IR View */}
      {selectedIr && (
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setSelectedIr(null)}
              >
                <ArrowLeft className="h-4 w-4 mr-2" />
                Back to Results
              </Button>
            </div>
            <CardTitle className="text-xl mt-4">
              {selectedIr.metadata?.source_path || "Specification Details"}
            </CardTitle>
            <CardDescription>
              {selectedIr.intent?.summary || "No summary available"}
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            {/* Signature Section */}
            {selectedIr.signature && (
              <div className="space-y-2">
                <h3 className="font-semibold text-sm">Signature</h3>
                <div className="bg-muted p-4 rounded-lg font-mono text-sm">
                  <div>
                    <span className="text-blue-600 dark:text-blue-400">def</span>{" "}
                    <span className="font-bold">{selectedIr.signature.name}</span>(
                    {selectedIr.signature.parameters?.map((p: any, idx: number) => (
                      <span key={idx}>
                        {idx > 0 && ", "}
                        <span>{p.name}</span>
                        {p.type_hint && (
                          <span className="text-gray-600 dark:text-gray-400">: {p.type_hint}</span>
                        )}
                      </span>
                    ))}
                    )
                    {selectedIr.signature.returns && (
                      <span className="text-gray-600 dark:text-gray-400">
                        {" "}
                        -&gt; {selectedIr.signature.returns}
                      </span>
                    )}
                  </div>
                </div>
              </div>
            )}

            {/* Intent Section */}
            {selectedIr.intent && (
              <div className="space-y-2">
                <h3 className="font-semibold text-sm">Intent</h3>
                <div className="bg-muted p-4 rounded-lg space-y-2">
                  <p className="text-sm">{selectedIr.intent.summary}</p>
                  {selectedIr.intent.rationale && (
                    <p className="text-sm text-muted-foreground italic">
                      {selectedIr.intent.rationale}
                    </p>
                  )}
                  {selectedIr.intent.holes && selectedIr.intent.holes.length > 0 && (
                    <div className="mt-3 space-y-1">
                      <div className="text-xs font-medium text-muted-foreground">
                        Typed Holes ({selectedIr.intent.holes.length}):
                      </div>
                      {selectedIr.intent.holes.map((hole: any, idx: number) => (
                        <Badge key={idx} variant="warning" className="text-xs mr-1">
                          {hole.identifier}
                        </Badge>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Effects Section */}
            {selectedIr.effects && selectedIr.effects.length > 0 && (
              <div className="space-y-2">
                <h3 className="font-semibold text-sm">Effects</h3>
                <div className="space-y-2">
                  {selectedIr.effects.map((effect: any, idx: number) => (
                    <div key={idx} className="bg-muted p-3 rounded-lg">
                      <p className="text-sm">{effect.description}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Assertions Section */}
            {selectedIr.assertions && selectedIr.assertions.length > 0 && (
              <div className="space-y-2">
                <h3 className="font-semibold text-sm">Assertions</h3>
                <div className="space-y-2">
                  {selectedIr.assertions.map((assertion: any, idx: number) => (
                    <div key={idx} className="bg-muted p-3 rounded-lg space-y-1">
                      <code className="text-sm font-mono">{assertion.predicate}</code>
                      {assertion.rationale && (
                        <p className="text-xs text-muted-foreground italic">
                          {assertion.rationale}
                        </p>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Metadata Section */}
            {selectedIr.metadata && (
              <div className="space-y-2">
                <h3 className="font-semibold text-sm">Metadata</h3>
                <div className="bg-muted p-3 rounded-lg">
                  <div className="grid grid-cols-2 gap-2 text-sm">
                    {selectedIr.metadata.origin && (
                      <div>
                        <span className="text-muted-foreground">Origin:</span>{" "}
                        <span className="font-medium">{selectedIr.metadata.origin}</span>
                      </div>
                    )}
                    {selectedIr.metadata.language && (
                      <div>
                        <span className="text-muted-foreground">Language:</span>{" "}
                        <span className="font-medium">{selectedIr.metadata.language}</span>
                      </div>
                    )}
                    {selectedIr.metadata.source_path && (
                      <div className="col-span-2">
                        <span className="text-muted-foreground">Path:</span>{" "}
                        <span className="font-mono text-xs">{selectedIr.metadata.source_path}</span>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      )}

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
