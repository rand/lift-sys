import { useState } from "react";
import { ConfigurationView } from "./views/ConfigurationView";
import { RepositoryView } from "./views/RepositoryView";
import { IrView } from "./views/IrView";
import { PlannerView } from "./views/PlannerView";
import { IdeView } from "./views/IdeView";
import { Button } from "./components/ui/button";
import { useAuth } from "./lib/auth";
import { SignInView } from "./views/SignInView";
import { AuthCallbackView } from "./views/AuthCallbackView";
import "./styles.css";

type Section = "configuration" | "repository" | "ir" | "planner" | "ide";

export default function App() {
  const [section, setSection] = useState<Section>("configuration");
  const { state, signOut } = useAuth();

  const pathname = typeof window !== "undefined" ? window.location.pathname : "/";
  if (pathname === "/auth/callback") {
    return <AuthCallbackView />;
  }

  if (state.status === "loading") {
    return (
      <div className="main-shell" style={{ alignItems: "center", justifyContent: "center" }}>
        <p>Loading session…</p>
      </div>
    );
  }

  if (state.status === "unauthenticated") {
    return <SignInView />;
  }

  const userLabel = state.user?.name ?? state.user?.email ?? state.user?.id;

  return (
    <div className="main-shell">
      <aside style={{ padding: "1.5rem", background: "#111827", display: "grid", gap: "1.5rem" }}>
        <div>
          <h1 style={{ marginTop: 0 }}>lift-sys</h1>
          <p style={{ margin: 0, color: "#94a3b8", fontSize: "0.9rem" }}>Signed in as {userLabel}</p>
          <Button variant="ghost" style={{ marginTop: "0.5rem" }} onClick={() => void signOut()}>
            Sign out
          </Button>
        </div>
        <nav style={{ display: "grid", gap: "0.5rem" }}>
          <Button variant={section === "configuration" ? "default" : "ghost"} onClick={() => setSection("configuration")}>
            Configuration
          </Button>
          <Button variant={section === "repository" ? "default" : "ghost"} onClick={() => setSection("repository")}>
            Repository
          </Button>
          <Button variant={section === "ir" ? "default" : "ghost"} onClick={() => setSection("ir")}>
            IR Review
          </Button>
          <Button variant={section === "planner" ? "default" : "ghost"} onClick={() => setSection("planner")}>
            Planner
          </Button>
          <Button variant={section === "ide" ? "default" : "ghost"} onClick={() => setSection("ide")}>
            IDE
          </Button>
        </nav>
      </aside>
      <main style={{ padding: "2rem", background: "#0f172a" }}>
        {section === "configuration" && <ConfigurationView />}
        {section === "repository" && <RepositoryView />}
        {section === "ir" && <IrView />}
        {section === "planner" && <PlannerView />}
        {section === "ide" && <IdeView />}
      </main>
    </div>
  );
}
