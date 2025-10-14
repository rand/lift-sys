import { useState } from "react";
import {
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Info,
  ChevronDown,
  ChevronRight,
  Check,
  X,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "./ui/card";
import { Badge } from "./ui/badge";
import { Button } from "./ui/button";
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "./ui/accordion";
import { ScrollArea } from "./ui/scroll-area";
import { Alert, AlertDescription, AlertTitle } from "./ui/alert";

type DiffCategory = "intent" | "signature" | "assertion" | "effect" | "metadata";
type DiffKind = string;
type DiffSeverity = "error" | "warning" | "info";

interface IRDiff {
  category: DiffCategory;
  kind: DiffKind;
  path: string;
  left_value: any;
  right_value: any;
  severity: DiffSeverity;
  message?: string;
}

interface CategoryComparison {
  category: DiffCategory;
  diffs: IRDiff[];
  matches: number;
  total_fields: number;
  similarity: number;
}

interface ComparisonResult {
  left_ir: any;
  right_ir: any;
  intent_comparison: CategoryComparison;
  signature_comparison: CategoryComparison;
  assertion_comparison: CategoryComparison;
  effect_comparison: CategoryComparison;
  metadata_comparison: CategoryComparison;
  overall_similarity: number;
}

interface IRDiffViewerProps {
  /**
   * The comparison result from the backend.
   */
  comparison: ComparisonResult;

  /**
   * Label for the left IR.
   */
  leftLabel?: string;

  /**
   * Label for the right IR.
   */
  rightLabel?: string;

  /**
   * Show side-by-side view.
   */
  sideBySide?: boolean;

  /**
   * Enable accept/reject actions.
   */
  enableActions?: boolean;

  /**
   * Callback when accepting a diff.
   */
  onAcceptDiff?: (diff: IRDiff) => void;

  /**
   * Callback when rejecting a diff.
   */
  onRejectDiff?: (diff: IRDiff) => void;

  /**
   * Callback when accepting all diffs.
   */
  onAcceptAll?: () => void;

  /**
   * Callback when rejecting all diffs.
   */
  onRejectAll?: () => void;
}

const CATEGORY_LABELS: Record<DiffCategory, string> = {
  intent: "Intent",
  signature: "Signature",
  assertion: "Assertions",
  effect: "Effects",
  metadata: "Metadata",
};

export function IRDiffViewer({
  comparison,
  leftLabel = "Original",
  rightLabel = "Compared",
  sideBySide = true,
  enableActions = false,
  onAcceptDiff,
  onRejectDiff,
  onAcceptAll,
  onRejectAll,
}: IRDiffViewerProps) {
  const [acceptedDiffs, setAcceptedDiffs] = useState<Set<string>>(new Set());
  const [rejectedDiffs, setRejectedDiffs] = useState<Set<string>>(new Set());

  const allDiffs: IRDiff[] = [
    ...comparison.intent_comparison.diffs,
    ...comparison.signature_comparison.diffs,
    ...comparison.assertion_comparison.diffs,
    ...comparison.effect_comparison.diffs,
    ...comparison.metadata_comparison.diffs,
  ];

  const getDiffKey = (diff: IRDiff) => `${diff.category}-${diff.path}`;

  const handleAcceptDiff = (diff: IRDiff) => {
    const key = getDiffKey(diff);
    setAcceptedDiffs((prev) => new Set(prev).add(key));
    setRejectedDiffs((prev) => {
      const next = new Set(prev);
      next.delete(key);
      return next;
    });
    onAcceptDiff?.(diff);
  };

  const handleRejectDiff = (diff: IRDiff) => {
    const key = getDiffKey(diff);
    setRejectedDiffs((prev) => new Set(prev).add(key));
    setAcceptedDiffs((prev) => {
      const next = new Set(prev);
      next.delete(key);
      return next;
    });
    onRejectDiff?.(diff);
  };

  const handleAcceptAll = () => {
    const allKeys = allDiffs.map(getDiffKey);
    setAcceptedDiffs(new Set(allKeys));
    setRejectedDiffs(new Set());
    onAcceptAll?.();
  };

  const handleRejectAll = () => {
    const allKeys = allDiffs.map(getDiffKey);
    setRejectedDiffs(new Set(allKeys));
    setAcceptedDiffs(new Set());
    onRejectAll?.();
  };

  const getSeverityIcon = (severity: DiffSeverity) => {
    switch (severity) {
      case "error":
        return <XCircle className="h-4 w-4 text-red-500" />;
      case "warning":
        return <AlertTriangle className="h-4 w-4 text-yellow-500" />;
      case "info":
        return <Info className="h-4 w-4 text-blue-500" />;
    }
  };

  const getSeverityBadge = (severity: DiffSeverity) => {
    const variants: Record<DiffSeverity, string> = {
      error: "bg-red-100 text-red-800 border-red-300",
      warning: "bg-yellow-100 text-yellow-800 border-yellow-300",
      info: "bg-blue-100 text-blue-800 border-blue-300",
    };

    return (
      <Badge variant="outline" className={variants[severity]}>
        {severity.toUpperCase()}
      </Badge>
    );
  };

  const getSimilarityColor = (similarity: number) => {
    if (similarity >= 0.9) return "text-green-600";
    if (similarity >= 0.7) return "text-yellow-600";
    return "text-red-600";
  };

  const getSimilarityBadge = (similarity: number) => {
    const percentage = Math.round(similarity * 100);
    if (similarity >= 0.9)
      return (
        <Badge className="bg-green-600">
          <CheckCircle2 className="mr-1 h-3 w-3" />
          {percentage}% Match
        </Badge>
      );
    if (similarity >= 0.7)
      return (
        <Badge className="bg-yellow-600">
          <AlertTriangle className="mr-1 h-3 w-3" />
          {percentage}% Match
        </Badge>
      );
    return (
      <Badge variant="destructive">
        <XCircle className="mr-1 h-3 w-3" />
        {percentage}% Match
      </Badge>
    );
  };

  const renderDiffValue = (value: any) => {
    if (value === null || value === undefined) {
      return <span className="text-muted-foreground italic">none</span>;
    }
    if (typeof value === "object") {
      return (
        <code className="text-xs bg-muted px-2 py-1 rounded">{JSON.stringify(value)}</code>
      );
    }
    return <code className="text-xs bg-muted px-2 py-1 rounded">{String(value)}</code>;
  };

  const renderDiff = (diff: IRDiff) => {
    const key = getDiffKey(diff);
    const isAccepted = acceptedDiffs.has(key);
    const isRejected = rejectedDiffs.has(key);

    return (
      <div
        key={key}
        className={`border rounded-lg p-4 space-y-3 ${
          isAccepted
            ? "border-green-300 bg-green-50"
            : isRejected
            ? "border-red-300 bg-red-50"
            : "border-gray-200"
        }`}
      >
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-2">
            {getSeverityIcon(diff.severity)}
            <div>
              <div className="font-semibold text-sm">{diff.kind.replace(/_/g, " ")}</div>
              <div className="text-xs text-muted-foreground">{diff.path}</div>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {getSeverityBadge(diff.severity)}
            {enableActions && (
              <div className="flex gap-1">
                <Button
                  size="sm"
                  variant={isAccepted ? "default" : "outline"}
                  onClick={() => handleAcceptDiff(diff)}
                  className="h-7 px-2"
                >
                  <Check className="h-3 w-3" />
                </Button>
                <Button
                  size="sm"
                  variant={isRejected ? "destructive" : "outline"}
                  onClick={() => handleRejectDiff(diff)}
                  className="h-7 px-2"
                >
                  <X className="h-3 w-3" />
                </Button>
              </div>
            )}
          </div>
        </div>

        {diff.message && (
          <div className="text-sm text-muted-foreground">{diff.message}</div>
        )}

        {sideBySide ? (
          <div className="grid grid-cols-2 gap-4">
            <div>
              <div className="text-xs font-semibold mb-1 text-red-600">{leftLabel}</div>
              {renderDiffValue(diff.left_value)}
            </div>
            <div>
              <div className="text-xs font-semibold mb-1 text-green-600">{rightLabel}</div>
              {renderDiffValue(diff.right_value)}
            </div>
          </div>
        ) : (
          <div className="space-y-2">
            <div>
              <span className="text-xs font-semibold text-red-600">{leftLabel}: </span>
              {renderDiffValue(diff.left_value)}
            </div>
            <div>
              <span className="text-xs font-semibold text-green-600">{rightLabel}: </span>
              {renderDiffValue(diff.right_value)}
            </div>
          </div>
        )}
      </div>
    );
  };

  const renderCategoryComparison = (categoryComp: CategoryComparison) => {
    const label = CATEGORY_LABELS[categoryComp.category];
    const hasDiffs = categoryComp.diffs.length > 0;

    return (
      <AccordionItem value={categoryComp.category}>
        <AccordionTrigger className="hover:no-underline">
          <div className="flex items-center justify-between w-full pr-4">
            <div className="flex items-center gap-2">
              <span className="font-semibold">{label}</span>
              {hasDiffs && (
                <Badge variant="outline">{categoryComp.diffs.length} differences</Badge>
              )}
            </div>
            <div className="flex items-center gap-2">
              <span className={`text-sm font-semibold ${getSimilarityColor(categoryComp.similarity)}`}>
                {Math.round(categoryComp.similarity * 100)}%
              </span>
              {!hasDiffs && <CheckCircle2 className="h-4 w-4 text-green-600" />}
            </div>
          </div>
        </AccordionTrigger>
        <AccordionContent>
          {hasDiffs ? (
            <div className="space-y-3 pt-2">
              {categoryComp.diffs.map((diff) => renderDiff(diff))}
            </div>
          ) : (
            <div className="text-sm text-muted-foreground py-4 text-center">
              No differences in this category
            </div>
          )}
        </AccordionContent>
      </AccordionItem>
    );
  };

  const errorCount = allDiffs.filter((d) => d.severity === "error").length;
  const warningCount = allDiffs.filter((d) => d.severity === "warning").length;
  const infoCount = allDiffs.filter((d) => d.severity === "info").length;

  return (
    <Card className="w-full">
      <CardHeader>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <CardTitle>IR Comparison</CardTitle>
            {getSimilarityBadge(comparison.overall_similarity)}
          </div>
          {enableActions && allDiffs.length > 0 && (
            <div className="flex gap-2">
              <Button size="sm" variant="outline" onClick={handleAcceptAll}>
                <Check className="h-4 w-4 mr-2" />
                Accept All
              </Button>
              <Button size="sm" variant="outline" onClick={handleRejectAll}>
                <X className="h-4 w-4 mr-2" />
                Reject All
              </Button>
            </div>
          )}
        </div>
        {allDiffs.length > 0 && (
          <div className="flex gap-2 mt-2">
            {errorCount > 0 && (
              <Badge variant="outline" className="bg-red-100 text-red-800">
                {errorCount} errors
              </Badge>
            )}
            {warningCount > 0 && (
              <Badge variant="outline" className="bg-yellow-100 text-yellow-800">
                {warningCount} warnings
              </Badge>
            )}
            {infoCount > 0 && (
              <Badge variant="outline" className="bg-blue-100 text-blue-800">
                {infoCount} info
              </Badge>
            )}
          </div>
        )}
      </CardHeader>
      <CardContent>
        {allDiffs.length === 0 ? (
          <Alert>
            <CheckCircle2 className="h-4 w-4" />
            <AlertTitle>IRs are identical</AlertTitle>
            <AlertDescription>
              No differences found between the two intermediate representations.
            </AlertDescription>
          </Alert>
        ) : (
          <ScrollArea className="h-[600px] pr-4">
            <Accordion type="multiple" defaultValue={["intent", "signature", "assertion"]}>
              {renderCategoryComparison(comparison.intent_comparison)}
              {renderCategoryComparison(comparison.signature_comparison)}
              {renderCategoryComparison(comparison.assertion_comparison)}
              {renderCategoryComparison(comparison.effect_comparison)}
              {renderCategoryComparison(comparison.metadata_comparison)}
            </Accordion>
          </ScrollArea>
        )}
      </CardContent>
    </Card>
  );
}
