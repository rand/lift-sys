import { AlertCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { useAuth, OAuthProvider } from "../lib/auth";

const PROVIDER_LABELS: Record<OAuthProvider, string> = {
  google: "Google",
  github: "GitHub",
};

export function SignInView() {
  const { signIn, state } = useAuth();
  const errorMessage = state.error;

  return (
    <div className="min-h-screen flex items-center justify-center p-6 bg-background">
      <Card className="w-full max-w-md">
        <CardHeader className="text-center space-y-2">
          <CardTitle className="text-2xl">Welcome to lift-sys</CardTitle>
          <CardDescription>
            Sign in to connect your AI providers, manage repositories, and orchestrate code
            generation workflows.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-3">
            {(Object.keys(PROVIDER_LABELS) as OAuthProvider[]).map((provider) => (
              <Button key={provider} onClick={() => signIn(provider)} size="lg">
                Continue with {PROVIDER_LABELS[provider]}
              </Button>
            ))}
          </div>
          {errorMessage && (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>{errorMessage}</AlertDescription>
            </Alert>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
