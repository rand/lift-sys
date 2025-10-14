import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { VersionHistory } from "./VersionHistory";

describe("VersionHistory", () => {
  const mockSessionId = "test-session-123";
  const mockVersionHistory = {
    session_id: mockSessionId,
    current_version: 3,
    source: "prompt",
    versions: [
      {
        version: 1,
        created_at: "2025-01-15T10:00:00Z",
        author: "human",
        change_summary: "Initial version",
        provenance_summary: { human: 5 },
        tags: [],
        has_holes: true,
        hole_count: 3,
      },
      {
        version: 2,
        created_at: "2025-01-15T11:00:00Z",
        author: "agent",
        change_summary: "Refined specifications",
        provenance_summary: { agent: 3, human: 2 },
        tags: ["reviewed"],
        has_holes: true,
        hole_count: 1,
      },
      {
        version: 3,
        created_at: "2025-01-15T12:00:00Z",
        author: "human",
        change_summary: "Final review",
        provenance_summary: { human: 5 },
        tags: ["milestone"],
        has_holes: false,
        hole_count: 0,
      },
    ],
  };

  beforeEach(() => {
    global.fetch = vi.fn();
  });

  it("renders loading state initially", () => {
    (global.fetch as any).mockImplementationOnce(() =>
      new Promise(() => {}) // Never resolves
    );

    render(<VersionHistory sessionId={mockSessionId} />);

    expect(screen.getByText("Version History")).toBeInTheDocument();
    // Check for loading spinner by class instead of role
    const spinner = document.querySelector('.animate-spin');
    expect(spinner).toBeInTheDocument();
  });

  it("fetches and displays version history", async () => {
    (global.fetch as any).mockResolvedValueOnce({
      ok: true,
      json: async () => mockVersionHistory,
    });

    render(<VersionHistory sessionId={mockSessionId} />);

    await waitFor(() => {
      expect(screen.getByText("3 versions")).toBeInTheDocument();
    });

    expect(screen.getByText("Initial version")).toBeInTheDocument();
    expect(screen.getByText("Refined specifications")).toBeInTheDocument();
    expect(screen.getByText("Final review")).toBeInTheDocument();
  });

  it("marks current version with badge", async () => {
    (global.fetch as any).mockResolvedValueOnce({
      ok: true,
      json: async () => mockVersionHistory,
    });

    render(<VersionHistory sessionId={mockSessionId} />);

    await waitFor(() => {
      const currentBadges = screen.getAllByText("Current");
      expect(currentBadges).toHaveLength(1);
    });
  });

  it("displays provenance summary badges", async () => {
    (global.fetch as any).mockResolvedValueOnce({
      ok: true,
      json: async () => mockVersionHistory,
    });

    render(<VersionHistory sessionId={mockSessionId} />);

    await waitFor(() => {
      expect(screen.getByText(/human: 5/)).toBeInTheDocument();
      expect(screen.getByText(/agent: 3/)).toBeInTheDocument();
    });
  });

  it("displays tags for versions", async () => {
    (global.fetch as any).mockResolvedValueOnce({
      ok: true,
      json: async () => mockVersionHistory,
    });

    render(<VersionHistory sessionId={mockSessionId} />);

    await waitFor(() => {
      expect(screen.getByText("reviewed")).toBeInTheDocument();
      expect(screen.getByText("milestone")).toBeInTheDocument();
    });
  });

  it("shows hole count for versions with holes", async () => {
    (global.fetch as any).mockResolvedValueOnce({
      ok: true,
      json: async () => mockVersionHistory,
    });

    render(<VersionHistory sessionId={mockSessionId} />);

    await waitFor(() => {
      expect(screen.getByText("3 unresolved holes")).toBeInTheDocument();
      expect(screen.getByText("1 unresolved hole")).toBeInTheDocument();
    });
  });

  it("shows restore buttons for non-current versions", async () => {
    (global.fetch as any).mockResolvedValueOnce({
      ok: true,
      json: async () => mockVersionHistory,
    });

    render(<VersionHistory sessionId={mockSessionId} />);

    await waitFor(() => {
      const restoreButtons = screen.getAllByText("Restore");
      // Should have 2 restore buttons (for versions 1 and 2, not for current version 3)
      expect(restoreButtons).toHaveLength(2);
    });
  });

  it("shows compare buttons for non-current versions", async () => {
    (global.fetch as any).mockResolvedValueOnce({
      ok: true,
      json: async () => mockVersionHistory,
    });

    render(<VersionHistory sessionId={mockSessionId} />);

    await waitFor(() => {
      const compareButtons = screen.getAllByText("Compare");
      expect(compareButtons).toHaveLength(2);
    });
  });

  it("handles error state", async () => {
    (global.fetch as any).mockRejectedValueOnce(new Error("Network error"));

    render(<VersionHistory sessionId={mockSessionId} />);

    await waitFor(() => {
      expect(screen.getByText("Error")).toBeInTheDocument();
      expect(screen.getByText(/Network error/)).toBeInTheDocument();
    });
  });

  it("handles empty version history", async () => {
    (global.fetch as any).mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        session_id: mockSessionId,
        current_version: 0,
        versions: [],
        source: "prompt",
      }),
    });

    render(<VersionHistory sessionId={mockSessionId} />);

    await waitFor(() => {
      expect(screen.getByText("No version history available")).toBeInTheDocument();
    });
  });

  it("opens rollback dialog when restore button clicked", async () => {
    (global.fetch as any).mockResolvedValueOnce({
      ok: true,
      json: async () => mockVersionHistory,
    });

    render(<VersionHistory sessionId={mockSessionId} />);

    await waitFor(() => {
      const restoreButtons = screen.getAllByText("Restore");
      fireEvent.click(restoreButtons[0]);
    });

    await waitFor(() => {
      expect(screen.getByText(/Restore Version/)).toBeInTheDocument();
    });
  });

  it("fetches comparison data when compare button clicked", async () => {
    const mockComparison = {
      session_id: mockSessionId,
      from_version: 1,
      to_version: 3,
      comparison: {
        has_changes: true,
        diffs: [],
        categories: {},
      },
      from_ir: { intent: { summary: "Test" }, signature: { name: "test", parameters: [], returns: "str" } },
      to_ir: { intent: { summary: "Test Updated" }, signature: { name: "test", parameters: [], returns: "str" } },
    };

    (global.fetch as any)
      .mockResolvedValueOnce({
        ok: true,
        json: async () => mockVersionHistory,
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => mockComparison,
      });

    render(<VersionHistory sessionId={mockSessionId} />);

    await waitFor(() => {
      const compareButtons = screen.getAllByText("Compare");
      fireEvent.click(compareButtons[0]);
    });

    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining("/versions/1/compare/3"),
        expect.any(Object)
      );
    });
  });

  it("calls onVersionChange after successful rollback", async () => {
    const onVersionChange = vi.fn();

    (global.fetch as any)
      .mockResolvedValueOnce({
        ok: true,
        json: async () => mockVersionHistory,
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({}),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => mockVersionHistory,
      });

    render(<VersionHistory sessionId={mockSessionId} onVersionChange={onVersionChange} />);

    await waitFor(() => {
      const restoreButtons = screen.getAllByText("Restore");
      fireEvent.click(restoreButtons[0]);
    });

    await waitFor(() => {
      const confirmButton = screen.getByText("Restore Version");
      fireEvent.click(confirmButton);
    });

    await waitFor(() => {
      expect(onVersionChange).toHaveBeenCalledWith(1);
    });
  });

  it("formats dates correctly", async () => {
    (global.fetch as any).mockResolvedValueOnce({
      ok: true,
      json: async () => mockVersionHistory,
    });

    render(<VersionHistory sessionId={mockSessionId} />);

    await waitFor(() => {
      // Date should be formatted as "Jan 15, 10:00 AM" or similar
      expect(screen.getByText(/Jan 15/)).toBeInTheDocument();
    });
  });
});
