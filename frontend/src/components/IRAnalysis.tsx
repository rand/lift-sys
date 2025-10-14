/**
 * IR Analysis Component
 *
 * Displays proactive analysis and improvement suggestions for IR specifications.
 */

import { useState } from "react";
import { AlertTriangle, CheckCircle, Info, Lightbulb, ShieldAlert } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Separator } from "@/components/ui/separator";
import { ScrollArea } from "@/components/ui/scroll-area";
import { api } from "@/lib/api";
import type { AnalysisReport, IRSuggestion } from "@/types/sessions";

interface IRAnalysisProps {
  sessionId: string;
}

export function IRAnalysis({ sessionId }: IRAnalysisProps) {
  const [report, setReport] = useState<AnalysisReport | null>(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [expandedSuggestions, setExpandedSuggestions] = useState<Set<number>>(new Set());

  const analyzeIR = async () => {
    setIsAnalyzing(true);
    setError(null);

    try {
      const response = await api.post<AnalysisReport>(`/api/spec-sessions/${sessionId}/analyze`);
      setReport(response.data);
    } catch (err) {
      console.error("Failed to analyze IR:", err);
      setError(err instanceof Error ? err.message : "Failed to analyze IR");
    } finally {
      setIsAnalyzing(false);
    }
  };

  const toggleSuggestion = (index: number) => {
    setExpandedSuggestions((prev) => {
      const next = new Set(prev);
      if (next.has(index)) {
        next.delete(index);
      } else {
        next.add(index);
      }
      return next;
    });
  };

  const getSeverityIcon = (severity: string) => {
    switch (severity) {
      case "critical":
        return <ShieldAlert className="h-4 w-4 text-red-600" />;
      case "high":
        return <AlertTriangle className="h-4 w-4 text-orange-500" />;
      case "medium":
        return <Info className="h-4 w-4 text-yellow-500" />;
      case "low":
        return <Lightbulb className="h-4 w-4 text-blue-500" />;
      default:
        return <Info className="h-4 w-4 text-gray-500" />;
    }
  };

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case "critical":
        return "destructive";
      case "high":
        return "default";
      case "medium":
        return "secondary";
      case "low":
        return "outline";
      default:
        return "outline";
    }
  };

  const getCategoryColor = (category: string) => {
    switch (category) {
      case "type_safety":
        return "bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200";
      case "documentation":
        return "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200";
      case "security":
        return "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200";
      case "error_handling":
        return "bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200";
      case "completeness":
        return "bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200";
      case "best_practices":
        return "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200";
      default:
        return "bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200";
    }
  };

  const formatCategoryName = (category: string) => {
    return category
      .split("_")
      .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
      .join(" ");
  };

  const getQualityColor = (score: number) => {
    if (score >= 0.8) return "text-green-600";
    if (score >= 0.6) return "text-yellow-600";
    return "text-red-600";
  };

  const groupSuggestionsByCategory = (suggestions: IRSuggestion[]) => {
    const grouped: Record<string, IRSuggestion[]> = {};
    for (const suggestion of suggestions) {
      if (!grouped[suggestion.category]) {
        grouped[suggestion.category] = [];
      }
      grouped[suggestion.category].push(suggestion);
    }
    return grouped;
  };

  return (
    <Card>
      <CardHeader>
        <div className="flex justify-between items-start">
          <div>
            <CardTitle>IR Quality Analysis</CardTitle>
            <CardDescription>
              Proactive suggestions to improve your specification
            </CardDescription>
          </div>
          <Button onClick={analyzeIR} disabled={isAnalyzing} variant="outline">
            {isAnalyzing ? "Analyzing..." : "Analyze IR"}
          </Button>
        </div>
      </CardHeader>
      <CardContent>
        {error && (
          <Alert variant="destructive" className="mb-4">
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        {report && (
          <div className="space-y-6">
            {/* Quality Score */}
            <div className="flex items-center justify-between p-4 bg-muted rounded-lg">
              <div className="flex items-center gap-3">
                <CheckCircle className="h-8 w-8 text-muted-foreground" />
                <div>
                  <p className="text-sm font-medium">Overall Quality Score</p>
                  <p className="text-xs text-muted-foreground">
                    Based on {report.summary_stats.total} suggestion(s)
                  </p>
                </div>
              </div>
              <div className={`text-4xl font-bold ${getQualityColor(report.overall_quality_score)}`}>
                {(report.overall_quality_score * 100).toFixed(0)}%
              </div>
            </div>

            {/* Summary Stats */}
            {report.summary_stats.total > 0 && (
              <div className="flex flex-wrap gap-2">
                {report.summary_stats.critical > 0 && (
                  <Badge variant="destructive">
                    {report.summary_stats.critical} Critical
                  </Badge>
                )}
                {report.summary_stats.high > 0 && (
                  <Badge variant="default">
                    {report.summary_stats.high} High
                  </Badge>
                )}
                {report.summary_stats.medium > 0 && (
                  <Badge variant="secondary">
                    {report.summary_stats.medium} Medium
                  </Badge>
                )}
                {report.summary_stats.low > 0 && (
                  <Badge variant="outline">
                    {report.summary_stats.low} Low
                  </Badge>
                )}
              </div>
            )}

            {/* Suggestions */}
            {report.suggestions.length > 0 ? (
              <ScrollArea className="h-[400px]">
                <div className="space-y-4 pr-4">
                  {Object.entries(groupSuggestionsByCategory(report.suggestions)).map(
                    ([category, suggestions]) => (
                      <div key={category} className="space-y-2">
                        <div className="flex items-center gap-2">
                          <Badge className={getCategoryColor(category)}>
                            {formatCategoryName(category)}
                          </Badge>
                          <span className="text-xs text-muted-foreground">
                            {suggestions.length} issue{suggestions.length !== 1 ? "s" : ""}
                          </span>
                        </div>

                        {suggestions.map((suggestion, idx) => {
                          const globalIdx = report.suggestions.indexOf(suggestion);
                          const isExpanded = expandedSuggestions.has(globalIdx);

                          return (
                            <Card
                              key={globalIdx}
                              className="cursor-pointer hover:bg-muted/50 transition-colors"
                              onClick={() => toggleSuggestion(globalIdx)}
                            >
                              <CardContent className="pt-4 pb-4">
                                <div className="flex items-start gap-3">
                                  {getSeverityIcon(suggestion.severity)}
                                  <div className="flex-1 space-y-2">
                                    <div className="flex items-start justify-between gap-2">
                                      <h4 className="font-medium text-sm">{suggestion.title}</h4>
                                      <Badge variant={getSeverityColor(suggestion.severity)}>
                                        {suggestion.severity}
                                      </Badge>
                                    </div>

                                    <p className="text-xs text-muted-foreground">
                                      📍 {suggestion.location}
                                    </p>

                                    {isExpanded && (
                                      <>
                                        <Separator className="my-2" />

                                        <div className="space-y-3 text-sm">
                                          <p className="text-muted-foreground">
                                            {suggestion.description}
                                          </p>

                                          {suggestion.current_value && (
                                            <div>
                                              <p className="font-medium text-xs mb-1">
                                                Current:
                                              </p>
                                              <code className="text-xs bg-muted px-2 py-1 rounded">
                                                {suggestion.current_value}
                                              </code>
                                            </div>
                                          )}

                                          {suggestion.suggested_value && (
                                            <div>
                                              <p className="font-medium text-xs mb-1">
                                                Suggested:
                                              </p>
                                              <code className="text-xs bg-muted px-2 py-1 rounded">
                                                {suggestion.suggested_value}
                                              </code>
                                            </div>
                                          )}

                                          {suggestion.rationale && (
                                            <div>
                                              <p className="font-medium text-xs mb-1">Why:</p>
                                              <p className="text-xs text-muted-foreground">
                                                {suggestion.rationale}
                                              </p>
                                            </div>
                                          )}

                                          {suggestion.examples.length > 0 && (
                                            <div>
                                              <p className="font-medium text-xs mb-1">
                                                Examples:
                                              </p>
                                              <ul className="list-disc list-inside space-y-1 text-xs text-muted-foreground">
                                                {suggestion.examples.map((example, exIdx) => (
                                                  <li key={exIdx}>{example}</li>
                                                ))}
                                              </ul>
                                            </div>
                                          )}

                                          {suggestion.references.length > 0 && (
                                            <div>
                                              <p className="font-medium text-xs mb-1">
                                                References:
                                              </p>
                                              <ul className="list-disc list-inside space-y-1 text-xs text-muted-foreground">
                                                {suggestion.references.map((ref, refIdx) => (
                                                  <li key={refIdx}>{ref}</li>
                                                ))}
                                              </ul>
                                            </div>
                                          )}
                                        </div>
                                      </>
                                    )}
                                  </div>
                                </div>
                              </CardContent>
                            </Card>
                          );
                        })}
                      </div>
                    )
                  )}
                </div>
              </ScrollArea>
            ) : (
              <Alert>
                <CheckCircle className="h-4 w-4" />
                <AlertDescription>
                  Great work! No issues found in your IR specification.
                </AlertDescription>
              </Alert>
            )}
          </div>
        )}

        {!report && !error && !isAnalyzing && (
          <p className="text-sm text-muted-foreground text-center py-8">
            Click "Analyze IR" to get quality insights and improvement suggestions.
          </p>
        )}
      </CardContent>
    </Card>
  );
}
