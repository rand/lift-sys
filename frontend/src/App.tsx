import { useState } from "react";
import { ConfigurationView } from "./views/ConfigurationView";
import { RepositoryView } from "./views/RepositoryView";
import { EnhancedIrView } from "./views/EnhancedIrView";
import { PlannerView } from "./views/PlannerView";
import { IdeView } from "./views/IdeView";
import { PromptWorkbenchView } from "./views/PromptWorkbenchView";
import { Button } from "./components/ui/button";
import { ModeToggle } from "./components/mode-toggle";
import { Separator } from "./components/ui/separator";
import { SkipLink } from "./components/skip-link";
import { useAuth } from "./lib/auth";
import { SignInView } from "./views/SignInView";
import { AuthCallbackView } from "./views/AuthCallbackView";
import "./styles.css";

type Section = "configuration" | "repository" | "prompt" | "ir" | "planner" | "ide";

export default function App() {
  const [section, setSection] = useState<Section>("configuration");
  const { state, signOut } = useAuth();

  const pathname = typeof window !== "undefined" ? window.location.pathname : "/";
  if (pathname === "/auth/callback") {
    return <AuthCallbackView />;
  }

  if (state.status === "loading") {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <p className="text-muted-foreground">Loading session…</p>
      </div>
    );
  }

  if (state.status === "unauthenticated") {
    return <SignInView />;
  }

  const userLabel = state.user?.name ?? state.user?.email ?? state.user?.id;

  return (
    <>
      <SkipLink href="#main-content">Skip to main content</SkipLink>
      <SkipLink href="#navigation">Skip to navigation</SkipLink>
      <div className="main-shell">
        <aside className="border-r bg-card p-6 flex flex-col gap-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold mt-0 mb-1">lift-sys</h1>
              <p className="text-sm text-muted-foreground m-0">Signed in as {userLabel}</p>
            </div>
            <ModeToggle />
          </div>
          <Separator />
          <nav id="navigation" className="flex flex-col gap-2">
          <Button variant={section === "configuration" ? "default" : "ghost"} onClick={() => setSection("configuration")} className="justify-start">
            Configuration
          </Button>
          <Button variant={section === "repository" ? "default" : "ghost"} onClick={() => setSection("repository")} className="justify-start">
            Repository
          </Button>
          <Button variant={section === "prompt" ? "default" : "ghost"} onClick={() => setSection("prompt")} className="justify-start">
            Prompt Workbench
          </Button>
          <Button variant={section === "ir" ? "default" : "ghost"} onClick={() => setSection("ir")} className="justify-start">
            IR Review
          </Button>
          <Button variant={section === "planner" ? "default" : "ghost"} onClick={() => setSection("planner")} className="justify-start">
            Planner
          </Button>
          <Button variant={section === "ide" ? "default" : "ghost"} onClick={() => setSection("ide")} className="justify-start">
            IDE
          </Button>
        </nav>
        <Separator />
        <Button variant="ghost" onClick={() => void signOut()} className="justify-start mt-auto">
          Sign out
        </Button>
        </aside>
        <main id="main-content" className="p-8 bg-background overflow-auto">
          {section === "configuration" && <ConfigurationView />}
          {section === "repository" && <RepositoryView />}
          {section === "prompt" && <PromptWorkbenchView />}
          {section === "ir" && <EnhancedIrView />}
          {section === "planner" && <PlannerView />}
          {section === "ide" && <IdeView />}
        </main>
      </div>
    </>
  );
}
