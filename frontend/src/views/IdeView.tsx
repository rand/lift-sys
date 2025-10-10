import { useState } from "react";
import { Card } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { api } from "../lib/api";

const placeholderIr = {
  intent: { summary: "Lifted spec" },
  signature: { name: "function", parameters: [], returns: "void", holes: [] },
  effects: [],
  assertions: [],
};

export function IdeView() {
  const [response, setResponse] = useState<any | null>(null);

  const runForward = async () => {
    const { data } = await api.post("/forward", { ir: placeholderIr });
    setResponse(data);
  };

  return (
    <Card title="Interactive IDE">
      <p>Compile the IR into generation constraints and preview payloads.</p>
      <Button onClick={runForward}>Generate Constraints</Button>
      {response && <pre style={preStyle}>{JSON.stringify(response, null, 2)}</pre>}
    </Card>
  );
}

const preStyle: React.CSSProperties = {
  marginTop: "1.5rem",
  background: "#020617",
  color: "#e2e8f0",
  padding: "1rem",
  borderRadius: "0.75rem",
  overflow: "auto",
  maxHeight: "320px",
};
