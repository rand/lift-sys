import { useState, useEffect } from "react";
import {
  Clock,
  User,
  GitBranch,
  RotateCcw,
  GitCompare,
  Tag,
  AlertCircle,
  CheckCircle,
  Bot,
  Code,
  Workflow,
} from "lucide-react";
import { Button } from "./ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "./ui/card";
import { Badge } from "./ui/badge";
import { ScrollArea } from "./ui/scroll-area";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "./ui/dialog";
import { Alert, AlertDescription, AlertTitle } from "./ui/alert";
import { Separator } from "./ui/separator";
import { IRDiffViewer } from "./IRDiffViewer";

interface ProvenanceSummary {
  human?: number;
  agent?: number;
  reverse?: number;
  merge?: number;
  verification?: number;
  refinement?: number;
  unknown?: number;
}

interface VersionInfo {
  version: number;
  created_at: string;
  author: string | null;
  change_summary: string | null;
  provenance_summary: ProvenanceSummary;
  tags: string[];
  has_holes: boolean;
  hole_count: number;
}

interface VersionHistoryData {
  session_id: string;
  current_version: number;
  versions: VersionInfo[];
  source: string;
}

interface VersionComparisonData {
  session_id: string;
  from_version: number;
  to_version: number;
  comparison: any;
  from_ir: any;
  to_ir: any;
}

interface VersionHistoryProps {
  sessionId: string;
  onVersionChange?: (version: number) => void;
}

export function VersionHistory({ sessionId, onVersionChange }: VersionHistoryProps) {
  const [history, setHistory] = useState<VersionHistoryData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedVersion, setSelectedVersion] = useState<number | null>(null);
  const [compareVersion, setCompareVersion] = useState<number | null>(null);
  const [comparisonData, setComparisonData] = useState<VersionComparisonData | null>(null);
  const [showComparison, setShowComparison] = useState(false);
  const [showRollbackDialog, setShowRollbackDialog] = useState(false);
  const [rollbackTarget, setRollbackTarget] = useState<number | null>(null);
  const [isRollingBack, setIsRollingBack] = useState(false);

  useEffect(() => {
    fetchVersionHistory();
  }, [sessionId]);

  const fetchVersionHistory = async () => {
    try {
      setLoading(true);
      const response = await fetch(`/api/spec-sessions/${sessionId}/versions`, {
        credentials: "include",
      });

      if (!response.ok) {
        throw new Error(`Failed to fetch version history: ${response.statusText}`);
      }

      const data = await response.json();
      setHistory(data);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load version history");
    } finally {
      setLoading(false);
    }
  };

  const handleCompare = async (fromVersion: number, toVersion: number) => {
    try {
      const response = await fetch(
        `/api/spec-sessions/${sessionId}/versions/${fromVersion}/compare/${toVersion}`,
        {
          credentials: "include",
        }
      );

      if (!response.ok) {
        throw new Error("Failed to compare versions");
      }

      const data = await response.json();
      setComparisonData(data);
      setShowComparison(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to compare versions");
    }
  };

  const handleRollback = async (targetVersion: number, createNew: boolean = true) => {
    try {
      setIsRollingBack(true);
      const response = await fetch(
        `/api/spec-sessions/${sessionId}/versions/${targetVersion}/rollback`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          credentials: "include",
          body: JSON.stringify({ target_version: targetVersion, create_new_version: createNew }),
        }
      );

      if (!response.ok) {
        throw new Error("Failed to rollback");
      }

      await fetchVersionHistory();
      if (onVersionChange) {
        onVersionChange(targetVersion);
      }
      setShowRollbackDialog(false);
      setRollbackTarget(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to rollback");
    } finally {
      setIsRollingBack(false);
    }
  };

  const getProvenanceIcon = (source: string) => {
    switch (source) {
      case "human":
        return <User className="h-3 w-3" />;
      case "agent":
        return <Bot className="h-3 w-3" />;
      case "reverse":
        return <Code className="h-3 w-3" />;
      case "merge":
        return <GitBranch className="h-3 w-3" />;
      case "verification":
        return <CheckCircle className="h-3 w-3" />;
      case "refinement":
        return <Workflow className="h-3 w-3" />;
      default:
        return <AlertCircle className="h-3 w-3" />;
    }
  };

  const getProvenanceColor = (source: string): string => {
    switch (source) {
      case "human":
        return "bg-blue-500";
      case "agent":
        return "bg-purple-500";
      case "reverse":
        return "bg-green-500";
      case "merge":
        return "bg-orange-500";
      case "verification":
        return "bg-teal-500";
      case "refinement":
        return "bg-indigo-500";
      default:
        return "bg-gray-500";
    }
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return new Intl.DateTimeFormat("en-US", {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    }).format(date);
  };

  const getDominantProvenance = (summary: ProvenanceSummary): string => {
    if (!summary) return "unknown";
    const entries = Object.entries(summary);
    if (entries.length === 0) return "unknown";
    const [source] = entries.reduce((max, entry) =>
      entry[1] > max[1] ? entry : max
    );
    return source;
  };

  if (loading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Clock className="h-5 w-5" />
            Version History
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center py-8">
            <div className="animate-spin h-8 w-8 border-4 border-primary border-t-transparent rounded-full" />
          </div>
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Alert variant="destructive">
        <AlertCircle className="h-4 w-4" />
        <AlertTitle>Error</AlertTitle>
        <AlertDescription>{error}</AlertDescription>
      </Alert>
    );
  }

  if (!history || history.versions.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Clock className="h-5 w-5" />
            Version History
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-muted-foreground text-center py-8">
            No version history available
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <>
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center justify-between">
            <span className="flex items-center gap-2">
              <Clock className="h-5 w-5" />
              Version History
            </span>
            <Badge variant="outline">
              {history.versions.length} version{history.versions.length !== 1 ? "s" : ""}
            </Badge>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <ScrollArea className="h-[600px] pr-4">
            <div className="space-y-4">
              {history.versions.map((version, index) => {
                const isCurrentVersion = version.version === history.current_version;
                const dominantSource = getDominantProvenance(version.provenance_summary);

                return (
                  <div key={version.version} className="relative">
                    {/* Timeline connector */}
                    {index < history.versions.length - 1 && (
                      <div className="absolute left-[19px] top-[60px] h-[calc(100%+16px)] w-[2px] bg-border" />
                    )}

                    <Card className={isCurrentVersion ? "border-primary" : ""}>
                      <CardContent className="pt-6">
                        <div className="flex items-start gap-4">
                          {/* Version indicator */}
                          <div
                            className={`flex-shrink-0 w-10 h-10 rounded-full flex items-center justify-center font-bold text-sm ${
                              isCurrentVersion ? "bg-primary text-primary-foreground" : "bg-muted"
                            }`}
                          >
                            v{version.version}
                          </div>

                          {/* Version details */}
                          <div className="flex-1 min-w-0">
                            <div className="flex items-start justify-between gap-4">
                              <div className="flex-1">
                                <h4 className="font-semibold flex items-center gap-2">
                                  {version.change_summary || `Version ${version.version}`}
                                  {isCurrentVersion && (
                                    <Badge variant="default" className="text-xs">
                                      Current
                                    </Badge>
                                  )}
                                </h4>

                                <div className="flex items-center gap-3 mt-1 text-sm text-muted-foreground">
                                  <span className="flex items-center gap-1">
                                    <Clock className="h-3 w-3" />
                                    {formatDate(version.created_at)}
                                  </span>

                                  {version.author && (
                                    <span className="flex items-center gap-1">
                                      {getProvenanceIcon(dominantSource)}
                                      {version.author}
                                    </span>
                                  )}
                                </div>

                                {/* Provenance badges */}
                                {Object.keys(version.provenance_summary).length > 0 && (
                                  <div className="flex flex-wrap gap-1 mt-2">
                                    {Object.entries(version.provenance_summary).map(([source, count]) => (
                                      <Badge
                                        key={source}
                                        variant="secondary"
                                        className="text-xs"
                                      >
                                        <span
                                          className={`inline-block w-2 h-2 rounded-full mr-1 ${getProvenanceColor(
                                            source
                                          )}`}
                                        />
                                        {source}: {count}
                                      </Badge>
                                    ))}
                                  </div>
                                )}

                                {/* Tags */}
                                {version.tags.length > 0 && (
                                  <div className="flex flex-wrap gap-1 mt-2">
                                    {version.tags.map((tag) => (
                                      <Badge key={tag} variant="outline" className="text-xs">
                                        <Tag className="h-3 w-3 mr-1" />
                                        {tag}
                                      </Badge>
                                    ))}
                                  </div>
                                )}

                                {/* Holes indicator */}
                                {version.has_holes && (
                                  <div className="mt-2">
                                    <Badge variant="secondary" className="text-xs">
                                      <AlertCircle className="h-3 w-3 mr-1" />
                                      {version.hole_count} unresolved hole{version.hole_count !== 1 ? "s" : ""}
                                    </Badge>
                                  </div>
                                )}
                              </div>

                              {/* Actions */}
                              <div className="flex items-center gap-2">
                                {!isCurrentVersion && (
                                  <>
                                    <Button
                                      size="sm"
                                      variant="outline"
                                      onClick={() => {
                                        setRollbackTarget(version.version);
                                        setShowRollbackDialog(true);
                                      }}
                                    >
                                      <RotateCcw className="h-4 w-4 mr-1" />
                                      Restore
                                    </Button>
                                    <Button
                                      size="sm"
                                      variant="outline"
                                      onClick={() =>
                                        handleCompare(version.version, history.current_version)
                                      }
                                    >
                                      <GitCompare className="h-4 w-4 mr-1" />
                                      Compare
                                    </Button>
                                  </>
                                )}
                              </div>
                            </div>
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  </div>
                );
              })}
            </div>
          </ScrollArea>
        </CardContent>
      </Card>

      {/* Comparison Dialog */}
      <Dialog open={showComparison} onOpenChange={setShowComparison}>
        <DialogContent className="max-w-6xl h-[80vh]">
          <DialogHeader>
            <DialogTitle>
              Version Comparison: v{comparisonData?.from_version} → v{comparisonData?.to_version}
            </DialogTitle>
            <DialogDescription>
              Showing changes between the two versions
            </DialogDescription>
          </DialogHeader>
          {comparisonData && (
            <ScrollArea className="flex-1">
              <IRDiffViewer
                fromIR={comparisonData.from_ir}
                toIR={comparisonData.to_ir}
                comparison={comparisonData.comparison}
              />
            </ScrollArea>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowComparison(false)}>
              Close
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Rollback Confirmation Dialog */}
      <Dialog open={showRollbackDialog} onOpenChange={setShowRollbackDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Restore Version {rollbackTarget}?</DialogTitle>
            <DialogDescription>
              This will create a new version based on version {rollbackTarget}. The current
              version will be preserved in history.
            </DialogDescription>
          </DialogHeader>
          <Alert>
            <AlertCircle className="h-4 w-4" />
            <AlertTitle>Note</AlertTitle>
            <AlertDescription>
              This action will create version {history.current_version + 1} as a copy of version{" "}
              {rollbackTarget}. All versions remain accessible in the history.
            </AlertDescription>
          </Alert>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setShowRollbackDialog(false)}
              disabled={isRollingBack}
            >
              Cancel
            </Button>
            <Button
              onClick={() => rollbackTarget && handleRollback(rollbackTarget, true)}
              disabled={isRollingBack}
            >
              {isRollingBack ? "Restoring..." : "Restore Version"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
