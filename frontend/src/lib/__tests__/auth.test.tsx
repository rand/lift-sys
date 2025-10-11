import { describe, beforeEach, it, expect, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { AuthProvider, useAuth } from "../auth";
import { api } from "../../lib/api";

function AuthStatus() {
  const { state, signOut } = useAuth();
  return (
    <div>
      <span data-testid="status">{state.status}</span>
      <span data-testid="error">{state.error ?? ""}</span>
      <span data-testid="user">{state.user?.name ?? state.user?.id ?? ""}</span>
      <button type="button" onClick={() => void signOut()}>
        logout
      </button>
    </div>
  );
}

describe("AuthProvider", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("loads the current session on mount", async () => {
    vi.spyOn(api, "get").mockResolvedValue({
      data: { authenticated: true, user: { id: "github:1", provider: "github", name: "Ada" } },
    } as any);

    render(
      <AuthProvider>
        <AuthStatus />
      </AuthProvider>
    );

    expect(screen.getByTestId("status").textContent).toBe("loading");
    await waitFor(() => expect(screen.getByTestId("status").textContent).toBe("authenticated"));
    expect(screen.getByTestId("user").textContent).toBe("Ada");
  });

  it("clears session state on sign out", async () => {
    vi.spyOn(api, "get").mockResolvedValue({
      data: { authenticated: true, user: { id: "github:1", provider: "github", name: "Ada" } },
    } as any);
    const postMock = vi.spyOn(api, "post").mockResolvedValue({ data: {} } as any);

    render(
      <AuthProvider>
        <AuthStatus />
      </AuthProvider>
    );

    await waitFor(() => expect(screen.getByTestId("status").textContent).toBe("authenticated"));

    await userEvent.click(screen.getByText(/logout/i));
    expect(postMock).toHaveBeenCalledWith("/api/auth/logout");
    expect(screen.getByTestId("status").textContent).toBe("unauthenticated");
    expect(screen.getByTestId("user").textContent).toBe("");
  });

  it("records an error when the session request fails", async () => {
    vi.spyOn(api, "get").mockRejectedValue(new Error("network"));

    render(
      <AuthProvider>
        <AuthStatus />
      </AuthProvider>
    );

    await waitFor(() => expect(screen.getByTestId("status").textContent).toBe("unauthenticated"));
    expect(screen.getByTestId("error").textContent).toContain("Unable to load session");
  });
});
