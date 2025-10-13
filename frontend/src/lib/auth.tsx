import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  ReactNode,
} from "react";
import { api } from "./api";

export type OAuthProvider = "google" | "github";

export interface AuthUser {
  id: string;
  provider: OAuthProvider | string;
  email?: string | null;
  name?: string | null;
  avatarUrl?: string | null;
}

export type AuthStatus = "loading" | "authenticated" | "unauthenticated";

export interface AuthState {
  status: AuthStatus;
  user?: AuthUser;
  error?: string;
}

interface SessionResponse {
  authenticated: boolean;
  user?: AuthUser;
}

export interface AuthContextValue {
  state: AuthState;
  refresh: () => Promise<void>;
  signIn: (provider: OAuthProvider) => void;
  signOut: () => Promise<void>;
}

export const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AuthState>({ status: "loading" });

  const refresh = useCallback(async () => {
    setState((previous) => ({ ...previous, status: "loading" }));

    // In demo mode, check for existing demo user in localStorage
    // Respect explicit VITE_DEMO_MODE=false, otherwise default to dev mode
    const isDemoMode = import.meta.env.VITE_DEMO_MODE === 'false' ? false : (import.meta.env.VITE_DEMO_MODE === 'true' || import.meta.env.DEV);
    if (isDemoMode) {
      const demoUserJson = localStorage.getItem('demo_user');
      if (demoUserJson) {
        try {
          const demoUser = JSON.parse(demoUserJson) as AuthUser;
          setState({ status: "authenticated", user: demoUser });
          return;
        } catch {
          // Invalid demo user data, treat as unauthenticated
        }
      }
      setState({ status: "unauthenticated" });
      return;
    }

    // Production session fetch
    try {
      const { data } = await api.get<SessionResponse>("/api/auth/session");
      if (data.authenticated && data.user) {
        setState({ status: "authenticated", user: data.user });
      } else {
        setState({ status: "unauthenticated" });
      }
    } catch (error) {
      console.error("Failed to fetch session", error);
      setState({ status: "unauthenticated", error: "Unable to load session" });
      throw error;
    }
  }, []);

  useEffect(() => {
    refresh().catch(() => {
      // initial session fetch failures are handled via state
    });
  }, [refresh]);

  const signIn = useCallback(
    async (provider: OAuthProvider) => {
      // Check if demo mode is enabled
      // Respect explicit VITE_DEMO_MODE=false, otherwise default to dev mode
      const isDemoMode = import.meta.env.VITE_DEMO_MODE === 'false' ? false : (import.meta.env.VITE_DEMO_MODE === 'true' || import.meta.env.DEV);

      if (isDemoMode) {
        // In demo mode, create a mock authenticated session
        const demoUser: AuthUser = {
          id: `demo:${provider}-user`,
          provider: provider,
          email: `demo@${provider}.com`,
          name: `Demo ${provider.charAt(0).toUpperCase() + provider.slice(1)} User`,
          avatarUrl: null,
        };
        localStorage.setItem('demo_user', JSON.stringify(demoUser));
        setState({ status: "authenticated", user: demoUser });
        return;
      }

      // Production OAuth flow
      const callbackUrl = `${window.location.origin}/auth/callback`;
      const base = api.defaults.baseURL || window.location.origin;
      const loginUrl = new URL(`/api/auth/login/${provider}`, base);
      loginUrl.searchParams.set("redirect", callbackUrl);
      window.location.href = loginUrl.toString();
    },
    []
  );

  const signOut = useCallback(async () => {
    // Respect explicit VITE_DEMO_MODE=false, otherwise default to dev mode
    const isDemoMode = import.meta.env.VITE_DEMO_MODE === 'false' ? false : (import.meta.env.VITE_DEMO_MODE === 'true' || import.meta.env.DEV);

    if (isDemoMode) {
      // In demo mode, just clear localStorage and state
      localStorage.removeItem('demo_user');
      setState({ status: "unauthenticated" });
      return;
    }

    // Production logout
    try {
      await api.post("/api/auth/logout");
      setState({ status: "unauthenticated" });
    } catch (error) {
      console.error("Failed to log out", error);
      setState((previous) => ({ ...previous, error: "Unable to sign out" }));
    }
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({ state, refresh, signIn, signOut }),
    [state, refresh, signIn, signOut]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
