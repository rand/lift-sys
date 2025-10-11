import { useMutation } from "@tanstack/react-query";
import { useCallback, useState } from "react";
import { Button } from "../components/ui/button";
import { Card } from "../components/ui/card";
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
    <Card title="Configuration">
      <label style={{ display: "grid", gap: "0.5rem" }}>
        Endpoint
        <input value={endpoint} onChange={(event) => setEndpoint(event.target.value)} style={inputStyle} />
      </label>
      <label style={{ display: "grid", gap: "0.5rem", marginTop: "1rem" }}>
        Temperature
        <input
          type="number"
          step="0.1"
          value={temperature}
          onChange={(event) => setTemperature(Number(event.target.value))}
          style={inputStyle}
        />
      </label>
      <Button style={{ marginTop: "1.5rem" }} onClick={() => mutation.mutate()}>
        Save
      </Button>
      {mutation.isSuccess && <p>Configuration saved.</p>}
      <section style={{ marginTop: "2rem" }}>
        <h2>AI Providers</h2>
        <ProviderSelector onSelect={updatePrimaryProvider} />
        {primaryProvider && <p>Primary provider: {primaryProvider.toUpperCase()}</p>}
      </section>
    </Card>
  );
}

const inputStyle: React.CSSProperties = {
  padding: "0.75rem",
  borderRadius: "0.75rem",
  border: "1px solid #334155",
  background: "#0f172a",
  color: "#e2e8f0",
};
