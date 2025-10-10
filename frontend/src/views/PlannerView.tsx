import { useQuery } from "@tanstack/react-query";
import { Card } from "../components/ui/card";
import { api } from "../lib/api";

export function PlannerView() {
  const { data, refetch, isFetching } = useQuery({
    queryKey: ["planner"],
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
    retry: false,
  });

  return (
    <Card title="Planner">
      <button onClick={() => refetch()} disabled={isFetching} style={buttonStyle}>
        Refresh Plan
      </button>
      {!data && <p>No plan available.</p>}
      {data && (
        <ul>
          {data.steps.map((step: any) => (
            <li key={step.identifier}>
              <strong>{step.identifier}</strong>: {step.description}
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}

const buttonStyle: React.CSSProperties = {
  marginBottom: "1rem",
  padding: "0.5rem 1rem",
  borderRadius: "0.5rem",
  border: "1px solid #6366f1",
  background: "transparent",
  color: "#e2e8f0",
  cursor: "pointer",
};
