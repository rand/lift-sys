import { useState } from "react";
import { ConfigurationView } from "./views/ConfigurationView";
import { RepositoryView } from "./views/RepositoryView";
import { IrView } from "./views/IrView";
import { PlannerView } from "./views/PlannerView";
import { IdeView } from "./views/IdeView";
import { Button } from "./components/ui/button";
import "./styles.css";

type Section = "configuration" | "repository" | "ir" | "planner" | "ide";

export default function App() {
  const [section, setSection] = useState<Section>("configuration");

  return (
    <div className="main-shell">
      <aside style={{ padding: "1.5rem", background: "#111827" }}>
        <h1 style={{ marginTop: 0 }}>lift-sys</h1>
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
