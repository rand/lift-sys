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
    (provider: OAuthProvider) => {
      const callbackUrl = `${window.location.origin}/auth/callback`;
      const base = api.defaults.baseURL ?? window.location.origin;
      const loginUrl = new URL(`/api/auth/login/${provider}`, base);
      loginUrl.searchParams.set("redirect", callbackUrl);
      window.location.href = loginUrl.toString();
    },
    []
  );

  const signOut = useCallback(async () => {
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
