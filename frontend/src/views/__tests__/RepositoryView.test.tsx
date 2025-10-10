import { act, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { RepositoryView } from "../RepositoryView";
import { renderWithClient } from "../../test/utils";
import { api } from "../../lib/api";
import { MockWebSocket } from "../../test/mocks/websocket";

const progressPayload = [
  {
    id: "codeql_scan",
    label: "CodeQL Analysis",
    status: "completed",
    message: "Security queries executed successfully",
    timestamp: new Date().toISOString(),
    actions: [{ label: "View report", value: "codeql_report" }],
  },
  {
    id: "daikon_invariants",
    label: "Daikon Inference",
    status: "completed",
    message: "Invariants inferred from traces",
    timestamp: new Date().toISOString(),
    actions: [{ label: "Inspect", value: "daikon_details" }],
  },
];

describe("RepositoryView", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("updates scan timeline in response to WebSocket progress", async () => {
    const postMock = vi.spyOn(api, "post").mockImplementation(async (url: string) => {
      if (url === "/repos/open") {
        return { data: { status: "ready" } } as any;
      }
      if (url === "/reverse") {
        return { data: { progress: progressPayload } } as any;
      }
      throw new Error("unexpected url");
    });

    MockWebSocket.autoOpen = false;
    await act(async () => {
      renderWithClient(<RepositoryView />);
      await Promise.resolve();
    });

    await userEvent.type(screen.getByLabelText(/repository path/i), "/repo");
    await userEvent.click(screen.getByRole("button", { name: /open repository/i }));

    await waitFor(() => expect(postMock).toHaveBeenCalledWith("/repos/open", { path: "/repo" }));
    expect(screen.getByText(/repository ready/i)).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: /run reverse scan/i }));

    await waitFor(() => expect(postMock).toHaveBeenCalledWith("/reverse", expect.any(Object)));
    expect(screen.getByText(/CodeQL Analysis/)).toBeInTheDocument();

    const socket = MockWebSocket.instances[0];
    await act(async () => {
      socket.simulateOpen();
    });
    await act(async () => {
      socket.emitMessage({
        scope: "reverse",
        stage: "codeql_scan",
        status: "running",
        message: "Executing CodeQL queries",
        timestamp: new Date().toISOString(),
      });
    });

    await screen.findByText(/Executing CodeQL queries/);

    await userEvent.click(screen.getByRole("button", { name: /View report/i }));
    expect(screen.getByText(/CodeQL Analysis: View report/)).toBeInTheDocument();
  });
});
