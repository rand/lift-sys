import { useMutation } from "@tanstack/react-query";
import { useCallback, useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardHeader, CardTitle, CardContent, CardFooter } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Separator } from "@/components/ui/separator";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { CheckCircle2 } from "lucide-react";
import { ProviderSelector } from "../components/ProviderSelector";
import { Provider } from "../types/providers";
import { api } from "../lib/api";

export function ConfigurationView() {
  const [endpoint, setEndpoint] = useState("http://localhost:8001");
  const [temperature, setTemperature] = useState(0);
  const [primaryProvider, setPrimaryProvider] = useState<Provider | null>(null);

  const mutation = useMutation({
    mutationFn: async () => {
      await api.post("/config", { model_endpoint: endpoint, temperature });
    },
  });

  const updatePrimaryProvider = useCallback(async (provider: Provider) => {
    setPrimaryProvider(provider);
    await fetch("/api/providers/primary", {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ provider }),
    });
  }, []);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Configuration</h1>
        <p className="text-muted-foreground mt-2">
          Configure model endpoints and AI provider settings
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Model Configuration</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="endpoint">Model Endpoint</Label>
            <Input
              id="endpoint"
              type="url"
              value={endpoint}
              onChange={(event) => setEndpoint(event.target.value)}
              placeholder="http://localhost:8001"
            />
            <p className="text-sm text-muted-foreground">
              URL for the local or remote model API endpoint
            </p>
          </div>

          <div className="space-y-2">
            <Label htmlFor="temperature">Temperature</Label>
            <Input
              id="temperature"
              type="number"
              step="0.1"
              min="0"
              max="2"
              value={temperature}
              onChange={(event) => setTemperature(Number(event.target.value))}
            />
            <p className="text-sm text-muted-foreground">
              Controls randomness: 0 is deterministic, higher values increase creativity
            </p>
          </div>
        </CardContent>
        <CardFooter className="flex gap-3">
          <Button
            onClick={() => mutation.mutate()}
            disabled={mutation.isPending}
          >
            {mutation.isPending ? "Saving..." : "Save Configuration"}
          </Button>
          {mutation.isSuccess && (
            <Alert className="flex-1">
              <CheckCircle2 className="h-4 w-4" />
              <AlertDescription>Configuration saved successfully</AlertDescription>
            </Alert>
          )}
        </CardFooter>
      </Card>

      <Separator />

      <Card>
        <CardHeader>
          <CardTitle>AI Providers</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <ProviderSelector onSelect={updatePrimaryProvider} />
          {primaryProvider && (
            <Alert variant="success" className="mt-4">
              <AlertDescription>
                Primary provider: <span className="font-semibold">{primaryProvider.toUpperCase()}</span>
              </AlertDescription>
            </Alert>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
