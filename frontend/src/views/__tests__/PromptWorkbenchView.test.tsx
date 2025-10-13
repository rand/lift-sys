import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { vi, describe, it, expect, beforeEach } from "vitest";
import { PromptWorkbenchView } from "../PromptWorkbenchView";
import * as sessionApi from "../../lib/sessionApi";

// Mock the session API
vi.mock("../../lib/sessionApi");
vi.mock("../../lib/useProgressStream", () => ({
  useProgressStream: () => ({
    events: [],
    status: "open",
    clear: vi.fn(),
  }),
}));

const mockSessions = [
  {
    session_id: "session-123",
    status: "active",
    source: "prompt",
    created_at: "2025-01-01T00:00:00Z",
    updated_at: "2025-01-01T00:00:00Z",
    current_draft: {
      version: 1,
      ir: { intent: { summary: "Test function" } },
      validation_status: "incomplete",
      ambiguities: ["hole_1"],
      smt_results: [],
      created_at: "2025-01-01T00:00:00Z",
      metadata: {},
    },
    ambiguities: ["hole_1"],
    revision_count: 1,
    metadata: {},
  },
];

describe("PromptWorkbenchView", () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
        mutations: { retry: false },
      },
    });
    vi.clearAllMocks();
  });

  const renderWithProvider = (component: React.ReactElement) => {
    return render(
      <QueryClientProvider client={queryClient}>{component}</QueryClientProvider>
    );
  };

  it("renders prompt input and create button", () => {
    vi.mocked(sessionApi.listSessions).mockResolvedValue({ sessions: [] });

    renderWithProvider(<PromptWorkbenchView />);

    expect(screen.getByPlaceholderText(/e.g., A function/i)).toBeInTheDocument();
    expect(screen.getByText("Create Session")).toBeInTheDocument();
  });

  it("disables create button when no prompt is entered", async () => {
    vi.mocked(sessionApi.listSessions).mockResolvedValue({ sessions: [] });

    renderWithProvider(<PromptWorkbenchView />);

    const createButton = screen.getByText("Create Session");

    // Button should be disabled when prompt is empty
    expect(createButton).toBeDisabled();
  });

  it("creates session when prompt is provided", async () => {
    vi.mocked(sessionApi.listSessions).mockResolvedValue({ sessions: [] });
    vi.mocked(sessionApi.createSession).mockResolvedValue(mockSessions[0]);

    renderWithProvider(<PromptWorkbenchView />);

    const textarea = screen.getByPlaceholderText(/e.g., A function/i);
    const createButton = screen.getByText("Create Session");

    fireEvent.change(textarea, {
      target: { value: "A function that adds two numbers" },
    });
    fireEvent.click(createButton);

    await waitFor(() => {
      expect(sessionApi.createSession).toHaveBeenCalledWith({
        prompt: "A function that adds two numbers",
      });
    });
  });

  it("displays session list when sessions exist", async () => {
    vi.mocked(sessionApi.listSessions).mockResolvedValue({ sessions: mockSessions });

    renderWithProvider(<PromptWorkbenchView />);

    await waitFor(() => {
      // Session ID is truncated to first 8 chars: "session-"
      expect(screen.getByText(/session-/)).toBeInTheDocument();
      // Status and holes count are displayed separately with badges
      expect(screen.getByText("active")).toBeInTheDocument();
      expect(screen.getByText("1 holes")).toBeInTheDocument();
    });
  });

  it("shows active session details when selected", async () => {
    vi.mocked(sessionApi.listSessions).mockResolvedValue({ sessions: mockSessions });
    vi.mocked(sessionApi.getAssists).mockResolvedValue({
      session_id: "session-123",
      assists: [],
    });

    renderWithProvider(<PromptWorkbenchView />);

    // Find and click the session card
    await waitFor(() => {
      expect(screen.getByText(/session-/)).toBeInTheDocument();
    });

    const sessionText = screen.getByText(/session-/);
    const card = sessionText.closest('[class*="cursor-pointer"]');
    fireEvent.click(card!);

    await waitFor(() => {
      // Session title shows first 12 chars: "Session session-123"
      expect(screen.getByText(/Session session-123/)).toBeInTheDocument();
      expect(screen.getByText(/Intermediate Representation/i)).toBeInTheDocument();
    });
  });

  it("displays ambiguities when session has holes", async () => {
    vi.mocked(sessionApi.listSessions).mockResolvedValue({ sessions: mockSessions });
    vi.mocked(sessionApi.getAssists).mockResolvedValue({
      session_id: "session-123",
      assists: [
        {
          hole_id: "hole_1",
          suggestions: ["int", "float"],
          context: "Missing type annotation",
        },
      ],
    });

    renderWithProvider(<PromptWorkbenchView />);

    // Find and click the session card
    await waitFor(() => {
      expect(screen.getByText(/session-/)).toBeInTheDocument();
    });

    const sessionText = screen.getByText(/session-/);
    const card = sessionText.closest('[class*="cursor-pointer"]');
    fireEvent.click(card!);

    await waitFor(() => {
      expect(screen.getByText(/Ambiguities \(1\)/i)).toBeInTheDocument();
      expect(screen.getByText("hole_1")).toBeInTheDocument();
    });
  });

  it("allows resolving holes with suggestions", async () => {
    vi.mocked(sessionApi.listSessions).mockResolvedValue({ sessions: mockSessions });
    vi.mocked(sessionApi.getAssists).mockResolvedValue({
      session_id: "session-123",
      assists: [
        {
          hole_id: "hole_1",
          suggestions: ["int", "float"],
          context: "Missing type annotation",
        },
      ],
    });
    vi.mocked(sessionApi.resolveHole).mockResolvedValue({
      ...mockSessions[0],
      ambiguities: [],
    });

    renderWithProvider(<PromptWorkbenchView />);

    // Find and click the session card
    await waitFor(() => {
      expect(screen.getByText(/session-/)).toBeInTheDocument();
    });

    const sessionText = screen.getByText(/session-/);
    const card = sessionText.closest('[class*="cursor-pointer"]');
    fireEvent.click(card!);

    await waitFor(() => {
      const intSuggestion = screen.getByText("int");
      fireEvent.click(intSuggestion);
    });

    await waitFor(() => {
      const resolveButton = screen.getByText("Resolve");
      fireEvent.click(resolveButton);
    });

    await waitFor(() => {
      expect(sessionApi.resolveHole).toHaveBeenCalledWith(
        "session-123",
        "hole_1",
        {
          resolution_text: "int",
          resolution_type: "clarify_intent",
        }
      );
    });
  });

  it("shows finalize button when no ambiguities remain", async () => {
    const finalizedSession = {
      ...mockSessions[0],
      ambiguities: [],
    };

    vi.mocked(sessionApi.listSessions).mockResolvedValue({
      sessions: [finalizedSession],
    });

    renderWithProvider(<PromptWorkbenchView />);

    // Find and click the session card
    await waitFor(() => {
      expect(screen.getByText(/session-/)).toBeInTheDocument();
    });

    const sessionText = screen.getByText(/session-/);
    const card = sessionText.closest('[class*="cursor-pointer"]');
    fireEvent.click(card!);

    await waitFor(() => {
      expect(screen.getByText("Finalize")).toBeInTheDocument();
    });
  });

  it("finalizes session successfully", async () => {
    const finalizedSession = {
      ...mockSessions[0],
      ambiguities: [],
    };

    vi.mocked(sessionApi.listSessions).mockResolvedValue({
      sessions: [finalizedSession],
    });
    vi.mocked(sessionApi.finalizeSession).mockResolvedValue({
      ir: finalizedSession.current_draft!.ir,
      metadata: {},
    });
    vi.mocked(sessionApi.getSession).mockResolvedValue({
      ...finalizedSession,
      status: "finalized",
    });

    renderWithProvider(<PromptWorkbenchView />);

    // Find and click the session card
    await waitFor(() => {
      expect(screen.getByText(/session-/)).toBeInTheDocument();
    });

    const sessionText = screen.getByText(/session-/);
    const card = sessionText.closest('[class*="cursor-pointer"]');
    fireEvent.click(card!);

    await waitFor(() => {
      const finalizeButton = screen.getByText("Finalize");
      fireEvent.click(finalizeButton);
    });

    await waitFor(() => {
      expect(sessionApi.finalizeSession).toHaveBeenCalledWith("session-123");
    });
  });

  it("allows deleting sessions", async () => {
    vi.mocked(sessionApi.listSessions).mockResolvedValue({ sessions: mockSessions });
    vi.mocked(sessionApi.deleteSession).mockResolvedValue();

    renderWithProvider(<PromptWorkbenchView />);

    // Wait for session to be displayed
    await waitFor(() => {
      expect(screen.getByText(/session-/)).toBeInTheDocument();
    });

    // Find the delete button (it's an icon button within the session card)
    // There are two buttons: "Create Session" (disabled) and the delete button in the session card
    const buttons = screen.getAllByRole("button");
    // The delete button is the second one (index 1) - the first is "Create Session"
    const deleteButton = buttons[1];

    expect(deleteButton).toBeDefined();
    fireEvent.click(deleteButton);

    await waitFor(() => {
      expect(sessionApi.deleteSession).toHaveBeenCalledWith("session-123");
    });
  });
});
