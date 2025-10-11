import { Button } from "../components/ui/button";
import { useAuth, OAuthProvider } from "../lib/auth";

const PROVIDER_LABELS: Record<OAuthProvider, string> = {
  google: "Google",
  github: "GitHub",
};

export function SignInView() {
  const { signIn, state } = useAuth();
  const errorMessage = state.error;

  return (
    <div
      className="main-shell"
      style={{
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        gap: "1.5rem",
      }}
    >
      <div style={{ textAlign: "center", maxWidth: "420px" }}>
        <h1 style={{ margin: 0 }}>Welcome to lift-sys</h1>
        <p style={{ color: "#94a3b8" }}>
          Sign in to connect your AI providers, manage repositories, and orchestrate code
          generation workflows.
        </p>
      </div>
      <div style={{ display: "grid", gap: "1rem", minWidth: "280px" }}>
        {(Object.keys(PROVIDER_LABELS) as OAuthProvider[]).map((provider) => (
          <Button key={provider} onClick={() => signIn(provider)}>
            Continue with {PROVIDER_LABELS[provider]}
          </Button>
        ))}
      </div>
      {errorMessage && (
        <p role="alert" style={{ color: "#f87171" }}>
          {errorMessage}
        </p>
      )}
    </div>
  );
}
