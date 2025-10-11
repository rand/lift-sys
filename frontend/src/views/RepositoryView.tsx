import { useMutation, useQuery } from "@tanstack/react-query";
import { useEffect, useMemo, useRef, useState } from "react";
import { Button } from "../components/ui/button";
import { Card } from "../components/ui/card";
import { Badge } from "../components/ui/badge";
import { api } from "../lib/api";
import { useProgressStream } from "../lib/useProgressStream";

type ProgressAction = { label: string; value?: string };
type ProgressCheckpoint = {
  id: string;
  label: string;
  status: string;
  message?: string;
  timestamp?: string;
  actions?: ProgressAction[];
};

type RepositorySummary = {
  identifier: string;
  owner: string;
  name: string;
  description?: string | null;
  defaultBranch: string;
  private: boolean;
  lastSynced?: string | null;
};

type RepositoryMetadata = RepositorySummary & {
  workspacePath?: string | null;
  source: string;
};

const statusBadges: Record<string, string> = {
  completed: "success",
  running: "info",
  ready: "warning",
  failed: "error",
};

export function RepositoryView() {
  const [selectedRepo, setSelectedRepo] = useState<RepositorySummary | null>(null);
  const [activeRepository, setActiveRepository] = useState<RepositoryMetadata | null>(null);
  const [moduleName, setModuleName] = useState("module.py");
  const [entrypoint, setEntrypoint] = useState("main");
  const [timeline, setTimeline] = useState<ProgressCheckpoint[]>([]);
  const [selectedAction, setSelectedAction] = useState<string | null>(null);
  const processedEvents = useRef(new Set<string>());
  const { events } = useProgressStream();
  const reverseEvents = useMemo(() => events.filter((event) => event.scope === "reverse"), [events]);

  const repositoriesQuery = useQuery({
    queryKey: ["repositories"],
    queryFn: async () => {
      const response = await api.get("/repos");
      return (response.data.repositories ?? []) as RepositorySummary[];
    },
  });

  useEffect(() => {
    if (!repositoriesQuery.data || repositoriesQuery.data.length === 0) {
      return;
    }
    setSelectedRepo((current) => current ?? repositoriesQuery.data[0]);
  }, [repositoriesQuery.data]);

  const openRepo = useMutation({
    mutationFn: async () => {
      if (!selectedRepo) {
        throw new Error("Repository selection required");
      }
      const response = await api.post("/repos/open", { identifier: selectedRepo.identifier });
      return response.data as { repository: RepositoryMetadata };
    },
    onSuccess: (data) => {
      setActiveRepository(data.repository);
      repositoriesQuery.refetch();
    },
  });

  const reverseMutation = useMutation({
    mutationFn: async () => {
      const response = await api.post("/reverse", {
        module: moduleName,
        queries: ["security/default"],
        entrypoint,
      });
      processedEvents.current = new Set();
      setTimeline(response.data.progress ?? []);
      return response.data;
    },
  });

  useEffect(() => {
    if (!timeline.length || !reverseEvents.length) {
      return;
    }
    setTimeline((previous) => {
      let changed = false;
      const next = previous.map((checkpoint) => {
        const latest = reverseEvents
          .filter((event) => event.stage === checkpoint.id)
          .find((event) => {
            const key = `${event.stage}-${event.status}-${event.timestamp}`;
            if (!processedEvents.current.has(key)) {
              processedEvents.current.add(key);
              return true;
            }
            return false;
          });
        if (!latest) {
          return checkpoint;
        }
        changed = true;
        return {
          ...checkpoint,
          status: latest.status ?? checkpoint.status,
          message: latest.message ?? checkpoint.message,
          timestamp: latest.timestamp ?? checkpoint.timestamp,
        };
      });
      return changed ? next : previous;
    });
  }, [reverseEvents, timeline.length]);

  return (
    <Card title="Repository">
      <p>Connect one of your GitHub repositories to lift specifications.</p>
      <section style={{ display: "grid", gap: "0.75rem" }}>
        <header style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "0.5rem" }}>
          <h3 style={{ margin: 0 }}>Repositories</h3>
          <Button variant="ghost" size="sm" onClick={() => repositoriesQuery.refetch()} disabled={repositoriesQuery.isLoading}>
            Refresh
          </Button>
        </header>
        {repositoriesQuery.isLoading ? (
          <p style={{ opacity: 0.7 }}>Loading repositories…</p>
        ) : repositoriesQuery.isError ? (
          <p role="alert">Unable to load repositories. Ensure GitHub access is configured.</p>
        ) : repositoriesQuery.data && repositoriesQuery.data.length > 0 ? (
          <div style={repoGridStyle}>
            {repositoriesQuery.data.map((repo) => {
              const isSelected = selectedRepo?.identifier === repo.identifier;
              return (
                <button
                  key={repo.identifier}
                  type="button"
                  onClick={() => setSelectedRepo(repo)}
                  style={{
                    ...repoButtonStyle,
                    borderColor: isSelected ? "#818cf8" : "#334155",
                    background: isSelected ? "rgba(129, 140, 248, 0.15)" : "#0f172a",
                  }}
                >
                  <strong style={{ fontSize: "1rem" }}>{repo.name}</strong>
                  <span style={{ opacity: 0.75 }}>{repo.owner}</span>
                  {repo.description && <p style={{ margin: 0, fontSize: "0.85rem", opacity: 0.8 }}>{repo.description}</p>}
                  <span style={{ fontSize: "0.75rem", opacity: 0.6 }}>
                    Default branch: {repo.defaultBranch}
                    {repo.lastSynced ? ` • Synced ${new Date(repo.lastSynced).toLocaleTimeString()}` : ""}
                  </span>
                </button>
              );
            })}
          </div>
        ) : (
          <p style={{ opacity: 0.7 }}>No repositories available. Connect GitHub to continue.</p>
        )}
      </section>
      <div style={formGridStyle}>
        <label style={labelStyle}>
          Module
          <input value={moduleName} onChange={(event) => setModuleName(event.target.value)} style={inputStyle} />
        </label>
        <label style={labelStyle}>
          Entrypoint
          <input value={entrypoint} onChange={(event) => setEntrypoint(event.target.value)} style={inputStyle} />
        </label>
      </div>

      <div style={{ display: "flex", gap: "0.75rem", marginTop: "1rem", flexWrap: "wrap" }}>
        <Button onClick={() => openRepo.mutate()} disabled={!selectedRepo || openRepo.isPending}>
          {openRepo.isPending ? "Opening…" : "Open Repository"}
        </Button>
        <Button
          variant="outline"
          onClick={() => reverseMutation.mutate()}
          disabled={reverseMutation.isPending || openRepo.isError || !activeRepository}
        >
          {reverseMutation.isPending ? "Scanning…" : "Run Reverse Scan"}
        </Button>
      </div>

      {openRepo.isSuccess && activeRepository && (
        <p style={{ marginTop: "0.75rem" }}>
          Repository <strong>{activeRepository.name}</strong> synced from {activeRepository.owner}.
        </p>
      )}
      {openRepo.isError && <p role="alert">Unable to open repository. Check your permissions and try again.</p>}

      <section style={{ marginTop: "1.5rem", display: "grid", gap: "1rem" }}>
        <h3 style={{ margin: 0 }}>Repository Scan Timeline</h3>
        {timeline.length === 0 ? (
          <p style={{ opacity: 0.7 }}>Trigger reverse mode to view progress checkpoints.</p>
        ) : (
          <ol style={timelineStyle}>
            {timeline.map((checkpoint) => (
              <li key={checkpoint.id} style={timelineItemStyle}>
                <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", flexWrap: "wrap" }}>
                  <Badge variant={(statusBadges[checkpoint.status] as any) ?? "info"}>{checkpoint.label}</Badge>
                  <span>{checkpoint.message}</span>
                </div>
                <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
                  {checkpoint.actions?.map((action) => (
                    <Button
                      key={action.label}
                      variant="ghost"
                      size="sm"
                      onClick={() => setSelectedAction(`${checkpoint.label}: ${action.label}${action.value ? ` (${action.value})` : ""}`)}
                    >
                      {action.label}
                    </Button>
                  ))}
                </div>
                <span style={{ fontSize: "0.75rem", opacity: 0.6 }}>
                  {checkpoint.timestamp ? new Date(checkpoint.timestamp).toLocaleTimeString() : "Awaiting timestamp"}
                </span>
              </li>
            ))}
          </ol>
        )}
      </section>

      {selectedAction && (
        <aside style={actionBannerStyle}>
          <strong>Action</strong>
          <span>{selectedAction}</span>
        </aside>
      )}
    </Card>
  );
}

const formGridStyle: React.CSSProperties = {
  display: "grid",
  gap: "1rem",
  gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
};

const repoGridStyle: React.CSSProperties = {
  display: "grid",
  gap: "0.75rem",
  gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
};

const repoButtonStyle: React.CSSProperties = {
  display: "grid",
  gap: "0.35rem",
  textAlign: "left",
  padding: "0.9rem",
  borderRadius: "0.9rem",
  border: "1px solid #334155",
  background: "#0f172a",
  color: "#e2e8f0",
  cursor: "pointer",
};

const labelStyle: React.CSSProperties = {
  display: "grid",
  gap: "0.35rem",
  fontSize: "0.9rem",
  color: "#cbd5f5",
};

const inputStyle: React.CSSProperties = {
  padding: "0.75rem",
  borderRadius: "0.75rem",
  border: "1px solid #334155",
  background: "#0f172a",
  color: "#e2e8f0",
};

const timelineStyle: React.CSSProperties = {
  listStyle: "none",
  margin: 0,
  padding: 0,
  display: "grid",
  gap: "1rem",
};

const timelineItemStyle: React.CSSProperties = {
  borderLeft: "2px solid rgba(99, 102, 241, 0.35)",
  paddingLeft: "1rem",
  display: "grid",
  gap: "0.5rem",
};

const actionBannerStyle: React.CSSProperties = {
  marginTop: "1.5rem",
  border: "1px solid rgba(148,163,184,0.35)",
  borderRadius: "0.75rem",
  padding: "0.75rem",
  display: "grid",
  gap: "0.35rem",
  background: "rgba(15,23,42,0.7)",
};
