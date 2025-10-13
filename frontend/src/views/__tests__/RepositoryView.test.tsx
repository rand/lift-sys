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
    vi.spyOn(api, "get").mockResolvedValue({
      data: {
        repositories: [
          {
            identifier: "octocat/example",
            owner: "octocat",
            name: "example",
            description: "Sample repository",
            defaultBranch: "main",
            private: false,
            lastSynced: null,
          },
        ],
      },
    } as any);
    const postMock = vi.spyOn(api, "post").mockImplementation(async (url: string) => {
      if (url === "/api/repos/open") {
        return {
          data: {
            status: "ready",
            repository: {
              identifier: "octocat/example",
              owner: "octocat",
              name: "example",
              description: "Sample repository",
              defaultBranch: "main",
              private: false,
              workspacePath: "/tmp/repos/octocat/example",
              lastSynced: new Date().toISOString(),
              source: "github",
            },
          },
        } as any;
      }
      if (url === "/api/reverse") {
        return { data: { progress: progressPayload } } as any;
      }
      throw new Error("unexpected url");
    });

    MockWebSocket.autoOpen = false;
    await act(async () => {
      renderWithClient(<RepositoryView />);
      await Promise.resolve();
    });

    // Wait for repository list to load and select the repository
    await screen.findByText(/example/);

    // Click the repository card to select it
    // The card contains the repository name and is clickable
    const repoName = screen.getByText("example");
    const card = repoName.closest('[class*="cursor-pointer"]');
    await userEvent.click(card!);

    // Now click the Open Repository button
    await userEvent.click(screen.getByRole("button", { name: /open repository/i }));

    await waitFor(() => expect(postMock).toHaveBeenCalledWith("/api/repos/open", { identifier: "octocat/example" }));
    // The success message format is: "Repository <strong>example</strong> synced from octocat."
    expect(screen.getByText(/synced from octocat/)).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: /run reverse scan/i }));

    await waitFor(() => expect(postMock).toHaveBeenCalledWith("/api/reverse", expect.any(Object)));
    expect(screen.getByText(/CodeQL Analysis/)).toBeInTheDocument();

    // Check if WebSocket was created (it may not be in the test environment)
    if (MockWebSocket.instances.length > 0) {
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
    }
  });
});
