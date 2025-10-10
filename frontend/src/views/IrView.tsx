import { useQuery } from "@tanstack/react-query";
import { Card } from "../components/ui/card";
import { Badge } from "../components/ui/badge";
import { api } from "../lib/api";

export function IrView() {
  const { data } = useQuery({
    queryKey: ["plan"],
    queryFn: async () => {
      try {
        const response = await api.get("/plan");
        return response.data;
      } catch (error: any) {
        if (error?.response?.status === 404) {
          return null;
        }
        throw error;
      }
    },
    staleTime: 1000 * 10,
  });

  return (
    <Card title="Intermediate Representation">
      {!data && <p>Run reverse mode to generate an IR.</p>}
      {data && (
        <div style={{ display: "grid", gap: "1rem" }}>
          <Badge variant="info">Plan Goals</Badge>
          <ul>
            {data.goals.map((goal: string) => (
              <li key={goal}>{goal}</li>
            ))}
          </ul>
        </div>
      )}
    </Card>
  );
}
