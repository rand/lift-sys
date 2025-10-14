import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { IRAnalysis } from "./IRAnalysis";
import { api } from "@/lib/api";

vi.mock("@/lib/api", () => ({
  api: {
    post: vi.fn(),
  },
}));

describe("IRAnalysis", () => {
  const mockSessionId = "test-session-123";

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders initial state with analyze button", () => {
    render(<IRAnalysis sessionId={mockSessionId} />);

    expect(screen.getByText("IR Quality Analysis")).toBeInTheDocument();
    expect(screen.getByText("Proactive suggestions to improve your specification")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /analyze ir/i })).toBeInTheDocument();
  });

  it("displays analysis report after clicking analyze", async () => {
    const mockReport = {
      session_id: mockSessionId,
      ir_summary: {
        intent_length: 50,
        parameter_count: 2,
        assertion_count: 1,
        effect_count: 0,
        has_rationale: true,
        has_return_type: true,
      },
      suggestions: [
        {
          category: "type_safety",
          severity: "high",
          title: "Overly broad type 'Any' for parameter 'data'",
          description: "Parameter 'data' uses the generic type 'Any', which reduces type safety.",
          location: "signature.parameters[0].type_hint",
          current_value: "Any",
          suggested_value: "str",
          rationale: "Specific types enable better validation.",
          examples: ["Use 'int' for numbers", "Use 'str' for text"],
          references: [],
        },
      ],
      summary_stats: {
        total: 1,
        critical: 0,
        high: 1,
        medium: 0,
        low: 0,
        info: 0,
      },
      overall_quality_score: 0.75,
    };

    vi.mocked(api.post).mockResolvedValue({ data: mockReport });

    render(<IRAnalysis sessionId={mockSessionId} />);

    const analyzeButton = screen.getByRole("button", { name: /analyze ir/i });
    fireEvent.click(analyzeButton);

    await waitFor(() => {
      expect(screen.getByText("Overall Quality Score")).toBeInTheDocument();
      expect(screen.getByText("75%")).toBeInTheDocument();
    });

    expect(screen.getByText("1 High")).toBeInTheDocument();
    expect(screen.getByText("Overly broad type 'Any' for parameter 'data'")).toBeInTheDocument();
  });

  it("displays perfect score message when no suggestions", async () => {
    const mockReport = {
      session_id: mockSessionId,
      ir_summary: {
        intent_length: 50,
        parameter_count: 2,
        assertion_count: 3,
        effect_count: 1,
        has_rationale: true,
        has_return_type: true,
      },
      suggestions: [],
      summary_stats: {
        total: 0,
        critical: 0,
        high: 0,
        medium: 0,
        low: 0,
        info: 0,
      },
      overall_quality_score: 1.0,
    };

    vi.mocked(api.post).mockResolvedValue({ data: mockReport });

    render(<IRAnalysis sessionId={mockSessionId} />);

    const analyzeButton = screen.getByRole("button", { name: /analyze ir/i });
    fireEvent.click(analyzeButton);

    await waitFor(() => {
      expect(screen.getByText("100%")).toBeInTheDocument();
      expect(screen.getByText("Great work! No issues found in your IR specification.")).toBeInTheDocument();
    });
  });

  it("expands suggestion details when clicked", async () => {
    const mockReport = {
      session_id: mockSessionId,
      ir_summary: {},
      suggestions: [
        {
          category: "security",
          severity: "critical",
          title: "SQL injection risk in parameter 'query'",
          description: "Parameter 'query' appears to be SQL-related but lacks injection protection.",
          location: "signature.parameters[0]",
          current_value: "query",
          suggested_value: "Add parameterized query assertion",
          rationale: "SQL injection is a critical vulnerability.",
          examples: ["Use parameterized queries", "Sanitize input"],
          references: ["OWASP SQL Injection Prevention"],
        },
      ],
      summary_stats: {
        total: 1,
        critical: 1,
        high: 0,
        medium: 0,
        low: 0,
        info: 0,
      },
      overall_quality_score: 0.6,
    };

    vi.mocked(api.post).mockResolvedValue({ data: mockReport });

    render(<IRAnalysis sessionId={mockSessionId} />);

    const analyzeButton = screen.getByRole("button", { name: /analyze ir/i });
    fireEvent.click(analyzeButton);

    await waitFor(() => {
      expect(screen.getByText("SQL injection risk in parameter 'query'")).toBeInTheDocument();
    });

    // Click to expand
    const suggestionCard = screen.getByText("SQL injection risk in parameter 'query'").closest("div[class*='cursor-pointer']");
    expect(suggestionCard).toBeInTheDocument();

    if (suggestionCard) {
      fireEvent.click(suggestionCard);
    }

    // Check that details are now visible
    await waitFor(() => {
      expect(screen.getByText("Parameter 'query' appears to be SQL-related but lacks injection protection.")).toBeInTheDocument();
      expect(screen.getByText("SQL injection is a critical vulnerability.")).toBeInTheDocument();
      expect(screen.getByText("Use parameterized queries")).toBeInTheDocument();
      expect(screen.getByText("OWASP SQL Injection Prevention")).toBeInTheDocument();
    });
  });

  it("handles API errors gracefully", async () => {
    vi.mocked(api.post).mockRejectedValue(new Error("API Error"));

    render(<IRAnalysis sessionId={mockSessionId} />);

    const analyzeButton = screen.getByRole("button", { name: /analyze ir/i });
    fireEvent.click(analyzeButton);

    await waitFor(() => {
      expect(screen.getByText("API Error")).toBeInTheDocument();
    });
  });

  it("groups suggestions by category", async () => {
    const mockReport = {
      session_id: mockSessionId,
      ir_summary: {},
      suggestions: [
        {
          category: "type_safety",
          severity: "high",
          title: "Type issue 1",
          description: "Description 1",
          location: "location1",
          current_value: null,
          suggested_value: null,
          rationale: null,
          examples: [],
          references: [],
        },
        {
          category: "type_safety",
          severity: "medium",
          title: "Type issue 2",
          description: "Description 2",
          location: "location2",
          current_value: null,
          suggested_value: null,
          rationale: null,
          examples: [],
          references: [],
        },
        {
          category: "documentation",
          severity: "low",
          title: "Doc issue 1",
          description: "Description 3",
          location: "location3",
          current_value: null,
          suggested_value: null,
          rationale: null,
          examples: [],
          references: [],
        },
      ],
      summary_stats: {
        total: 3,
        critical: 0,
        high: 1,
        medium: 1,
        low: 1,
        info: 0,
      },
      overall_quality_score: 0.7,
    };

    vi.mocked(api.post).mockResolvedValue({ data: mockReport });

    render(<IRAnalysis sessionId={mockSessionId} />);

    const analyzeButton = screen.getByRole("button", { name: /analyze ir/i });
    fireEvent.click(analyzeButton);

    await waitFor(() => {
      expect(screen.getByText("Type Safety")).toBeInTheDocument();
      expect(screen.getByText("2 issues")).toBeInTheDocument();
      expect(screen.getByText("Documentation")).toBeInTheDocument();
      expect(screen.getByText("1 issue")).toBeInTheDocument();
    });
  });

  it("displays severity badges correctly", async () => {
    const mockReport = {
      session_id: mockSessionId,
      ir_summary: {},
      suggestions: [
        {
          category: "security",
          severity: "critical",
          title: "Critical issue",
          description: "Description",
          location: "location",
          current_value: null,
          suggested_value: null,
          rationale: null,
          examples: [],
          references: [],
        },
      ],
      summary_stats: {
        total: 1,
        critical: 1,
        high: 0,
        medium: 0,
        low: 0,
        info: 0,
      },
      overall_quality_score: 0.5,
    };

    vi.mocked(api.post).mockResolvedValue({ data: mockReport });

    render(<IRAnalysis sessionId={mockSessionId} />);

    const analyzeButton = screen.getByRole("button", { name: /analyze ir/i });
    fireEvent.click(analyzeButton);

    await waitFor(() => {
      expect(screen.getByText("1 Critical")).toBeInTheDocument();
    });
  });
});
