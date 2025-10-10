import { useMutation } from "@tanstack/react-query";
import { useState } from "react";
import { Button } from "../components/ui/button";
import { Card } from "../components/ui/card";
import { api } from "../lib/api";

export function RepositoryView() {
  const [path, setPath] = useState("");
  const mutation = useMutation({
    mutationFn: async () => {
      await api.post("/repos/open", { path });
    },
  });

  return (
    <Card title="Repository">
      <p>Connect a local Git repository to lift specifications.</p>
      <input value={path} onChange={(event) => setPath(event.target.value)} style={inputStyle} placeholder="/repo" />
      <Button style={{ marginTop: "1rem" }} onClick={() => mutation.mutate()}>
        Open Repository
      </Button>
      {mutation.isSuccess && <p>Repository ready.</p>}
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
