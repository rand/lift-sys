import { useState } from "react";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { vscDarkPlus } from "react-syntax-highlighter/dist/esm/styles/prism";
import {
  Copy,
  Download,
  Check,
  AlertCircle,
  Code2,
  FileCode,
  SplitSquareVertical,
} from "lucide-react";
import { Button } from "./ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "./ui/card";
import { Badge } from "./ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "./ui/tabs";
import { ScrollArea } from "./ui/scroll-area";
import { Alert, AlertDescription, AlertTitle } from "./ui/alert";

interface ValidationStatus {
  isValid: boolean;
  fidelityScore?: number;
  differences?: Array<{
    kind: string;
    path: string;
    originalValue: any;
    extractedValue: any;
    severity: "error" | "warning" | "info";
  }>;
  warnings?: string[];
}

interface CodePreviewProps {
  /**
   * The generated code to display.
   */
  code: string;

  /**
   * Programming language for syntax highlighting.
   */
  language?: string;

  /**
   * Original IR for comparison view.
   */
  ir?: any;

  /**
   * Validation status from round-trip validation.
   */
  validation?: ValidationStatus;

  /**
   * Show side-by-side comparison view.
   */
  showComparison?: boolean;

  /**
   * Callback when copy button is clicked.
   */
  onCopy?: () => void;

  /**
   * Callback when download button is clicked.
   */
  onDownload?: () => void;

  /**
   * Filename for download.
   */
  filename?: string;

  /**
   * Additional metadata to display.
   */
  metadata?: Record<string, any>;
}

export function CodePreview({
  code,
  language = "python",
  ir,
  validation,
  showComparison = false,
  onCopy,
  onDownload,
  filename = "generated_code.py",
  metadata,
}: CodePreviewProps) {
  const [copied, setCopied] = useState(false);
  const [activeTab, setActiveTab] = useState<string>("code");

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(code);
      setCopied(true);
      onCopy?.();
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error("Failed to copy code:", err);
    }
  };

  const handleDownload = () => {
    const blob = new Blob([code], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
    onDownload?.();
  };

  const getValidationBadge = () => {
    if (!validation) return null;

    const { isValid, fidelityScore } = validation;
    const score = fidelityScore ?? 0;

    if (isValid && score === 1.0) {
      return (
        <Badge variant="default" className="bg-green-600">
          <Check className="mr-1 h-3 w-3" />
          Perfect Match
        </Badge>
      );
    } else if (isValid && score >= 0.8) {
      return (
        <Badge variant="default" className="bg-yellow-600">
          <AlertCircle className="mr-1 h-3 w-3" />
          High Fidelity ({(score * 100).toFixed(0)}%)
        </Badge>
      );
    } else if (isValid) {
      return (
        <Badge variant="default" className="bg-orange-600">
          <AlertCircle className="mr-1 h-3 w-3" />
          Partial Match ({(score * 100).toFixed(0)}%)
        </Badge>
      );
    } else {
      return (
        <Badge variant="destructive">
          <AlertCircle className="mr-1 h-3 w-3" />
          Validation Failed
        </Badge>
      );
    }
  };

  const renderValidationDetails = () => {
    if (!validation) return null;

    const { differences, warnings } = validation;

    return (
      <div className="space-y-4">
        {warnings && warnings.length > 0 && (
          <Alert>
            <AlertCircle className="h-4 w-4" />
            <AlertTitle>Warnings</AlertTitle>
            <AlertDescription>
              <ul className="list-disc list-inside space-y-1 mt-2">
                {warnings.map((warning, idx) => (
                  <li key={idx} className="text-sm">
                    {warning}
                  </li>
                ))}
              </ul>
            </AlertDescription>
          </Alert>
        )}

        {differences && differences.length > 0 && (
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertTitle>Differences Detected</AlertTitle>
            <AlertDescription>
              <div className="space-y-2 mt-2">
                {differences.map((diff, idx) => (
                  <div key={idx} className="text-sm border-l-2 border-red-400 pl-3">
                    <div className="font-semibold">{diff.kind}</div>
                    <div className="text-xs text-muted-foreground">{diff.path}</div>
                    <div className="grid grid-cols-2 gap-2 mt-1">
                      <div>
                        <span className="font-medium">Expected: </span>
                        <code className="text-xs bg-muted px-1 rounded">
                          {JSON.stringify(diff.originalValue)}
                        </code>
                      </div>
                      <div>
                        <span className="font-medium">Got: </span>
                        <code className="text-xs bg-muted px-1 rounded">
                          {JSON.stringify(diff.extractedValue)}
                        </code>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </AlertDescription>
          </Alert>
        )}
      </div>
    );
  };

  const renderIRComparison = () => {
    if (!ir) return <div className="p-4 text-muted-foreground">No IR data available</div>;

    return (
      <ScrollArea className="h-[500px]">
        <div className="p-4">
          <pre className="text-sm">
            <code>{JSON.stringify(ir, null, 2)}</code>
          </pre>
        </div>
      </ScrollArea>
    );
  };

  const renderMetadata = () => {
    if (!metadata || Object.keys(metadata).length === 0) {
      return <div className="p-4 text-muted-foreground">No metadata available</div>;
    }

    return (
      <div className="p-4 space-y-2">
        {Object.entries(metadata).map(([key, value]) => (
          <div key={key} className="flex items-start gap-2">
            <span className="font-medium text-sm">{key}:</span>
            <span className="text-sm text-muted-foreground">
              {typeof value === "object" ? JSON.stringify(value) : String(value)}
            </span>
          </div>
        ))}
      </div>
    );
  };

  return (
    <Card className="w-full">
      <CardHeader>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <CardTitle className="flex items-center gap-2">
              <FileCode className="h-5 w-5" />
              Generated Code
            </CardTitle>
            {getValidationBadge()}
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={handleCopy}
              disabled={copied}
              className="gap-2"
            >
              {copied ? (
                <>
                  <Check className="h-4 w-4" />
                  Copied
                </>
              ) : (
                <>
                  <Copy className="h-4 w-4" />
                  Copy
                </>
              )}
            </Button>
            <Button variant="outline" size="sm" onClick={handleDownload} className="gap-2">
              <Download className="h-4 w-4" />
              Download
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsList className="grid w-full grid-cols-4">
            <TabsTrigger value="code" className="gap-2">
              <Code2 className="h-4 w-4" />
              Code
            </TabsTrigger>
            <TabsTrigger value="validation" disabled={!validation}>
              <AlertCircle className="h-4 w-4 mr-2" />
              Validation
            </TabsTrigger>
            <TabsTrigger value="ir" disabled={!ir}>
              <SplitSquareVertical className="h-4 w-4 mr-2" />
              IR Comparison
            </TabsTrigger>
            <TabsTrigger value="metadata" disabled={!metadata}>
              Metadata
            </TabsTrigger>
          </TabsList>

          <TabsContent value="code" className="mt-4">
            <ScrollArea className="h-[500px] w-full rounded-md border">
              <SyntaxHighlighter
                language={language}
                style={vscDarkPlus}
                customStyle={{
                  margin: 0,
                  borderRadius: "0.375rem",
                  fontSize: "0.875rem",
                }}
                showLineNumbers
              >
                {code}
              </SyntaxHighlighter>
            </ScrollArea>
          </TabsContent>

          <TabsContent value="validation" className="mt-4">
            {renderValidationDetails()}
          </TabsContent>

          <TabsContent value="ir" className="mt-4">
            <div className="rounded-md border">
              {showComparison && ir ? (
                <div className="grid grid-cols-2 divide-x">
                  <div>
                    <div className="p-2 bg-muted font-semibold text-sm">Original IR</div>
                    {renderIRComparison()}
                  </div>
                  <div>
                    <div className="p-2 bg-muted font-semibold text-sm">Extracted IR</div>
                    {validation?.differences ? (
                      <ScrollArea className="h-[500px]">
                        <div className="p-4 text-sm text-muted-foreground">
                          See validation differences in the Validation tab
                        </div>
                      </ScrollArea>
                    ) : (
                      renderIRComparison()
                    )}
                  </div>
                </div>
              ) : (
                renderIRComparison()
              )}
            </div>
          </TabsContent>

          <TabsContent value="metadata" className="mt-4">
            <div className="rounded-md border">{renderMetadata()}</div>
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  );
}
