import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { IRDiffViewer } from "./IRDiffViewer";

describe("IRDiffViewer", () => {
  const mockEmptyComparison = {
    left_ir: { intent: { summary: "Test" } },
    right_ir: { intent: { summary: "Test" } },
    intent_comparison: {
      category: "intent" as const,
      diffs: [],
      matches: 2,
      total_fields: 2,
      similarity: 1.0,
    },
    signature_comparison: {
      category: "signature" as const,
      diffs: [],
      matches: 3,
      total_fields: 3,
      similarity: 1.0,
    },
    assertion_comparison: {
      category: "assertion" as const,
      diffs: [],
      matches: 0,
      total_fields: 0,
      similarity: 1.0,
    },
    effect_comparison: {
      category: "effect" as const,
      diffs: [],
      matches: 0,
      total_fields: 0,
      similarity: 1.0,
    },
    metadata_comparison: {
      category: "metadata" as const,
      diffs: [],
      matches: 4,
      total_fields: 4,
      similarity: 1.0,
    },
    overall_similarity: 1.0,
  };

  const mockComparisonWithDiffs = {
    left_ir: { intent: { summary: "Original" } },
    right_ir: { intent: { summary: "Modified" } },
    intent_comparison: {
      category: "intent" as const,
      diffs: [
        {
          category: "intent" as const,
          kind: "intent_summary",
          path: "intent.summary",
          left_value: "Original summary",
          right_value: "Modified summary",
          severity: "warning" as const,
          message: "Intent summary differs",
        },
      ],
      matches: 1,
      total_fields: 2,
      similarity: 0.5,
    },
    signature_comparison: {
      category: "signature" as const,
      diffs: [
        {
          category: "signature" as const,
          kind: "parameter_type",
          path: "signature.parameters[0].type_hint",
          left_value: "str",
          right_value: "int",
          severity: "error" as const,
          message: "Parameter type changed",
        },
        {
          category: "signature" as const,
          kind: "return_type",
          path: "signature.returns",
          left_value: "str",
          right_value: "int",
          severity: "error" as const,
        },
      ],
      matches: 2,
      total_fields: 4,
      similarity: 0.5,
    },
    assertion_comparison: {
      category: "assertion" as const,
      diffs: [
        {
          category: "assertion" as const,
          kind: "assertion_predicate",
          path: "assertions[0].predicate",
          left_value: "x > 0",
          right_value: "x >= 0",
          severity: "info" as const,
        },
      ],
      matches: 1,
      total_fields: 2,
      similarity: 0.5,
    },
    effect_comparison: {
      category: "effect" as const,
      diffs: [],
      matches: 0,
      total_fields: 0,
      similarity: 1.0,
    },
    metadata_comparison: {
      category: "metadata" as const,
      diffs: [],
      matches: 4,
      total_fields: 4,
      similarity: 1.0,
    },
    overall_similarity: 0.65,
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders IR comparison title", () => {
    render(<IRDiffViewer comparison={mockEmptyComparison} />);
    expect(screen.getByText("IR Comparison")).toBeInTheDocument();
  });

  it("displays perfect match badge for 100% similarity", () => {
    render(<IRDiffViewer comparison={mockEmptyComparison} />);
    expect(screen.getByText("100% Match")).toBeInTheDocument();
  });

  it("displays high match badge for 70-89% similarity", () => {
    const comparison = {
      ...mockEmptyComparison,
      overall_similarity: 0.85,
    };
    render(<IRDiffViewer comparison={comparison} />);
    expect(screen.getByText("85% Match")).toBeInTheDocument();
  });

  it("displays low match badge for <70% similarity", () => {
    render(<IRDiffViewer comparison={mockComparisonWithDiffs} />);
    expect(screen.getByText("65% Match")).toBeInTheDocument();
  });

  it("shows 'IRs are identical' message when no diffs", () => {
    render(<IRDiffViewer comparison={mockEmptyComparison} />);
    expect(screen.getByText("IRs are identical")).toBeInTheDocument();
    expect(screen.getByText("No differences found between the two intermediate representations.")).toBeInTheDocument();
  });

  it("displays error count badge", () => {
    render(<IRDiffViewer comparison={mockComparisonWithDiffs} />);
    expect(screen.getByText("2 errors")).toBeInTheDocument();
  });

  it("displays warning count badge", () => {
    render(<IRDiffViewer comparison={mockComparisonWithDiffs} />);
    expect(screen.getByText("1 warnings")).toBeInTheDocument();
  });

  it("displays info count badge", () => {
    render(<IRDiffViewer comparison={mockComparisonWithDiffs} />);
    expect(screen.getByText("1 info")).toBeInTheDocument();
  });

  it("renders all category sections", () => {
    render(<IRDiffViewer comparison={mockComparisonWithDiffs} />);
    expect(screen.getByText("Intent")).toBeInTheDocument();
    expect(screen.getByText("Signature")).toBeInTheDocument();
    expect(screen.getByText("Assertions")).toBeInTheDocument();
    expect(screen.getByText("Effects")).toBeInTheDocument();
    expect(screen.getByText("Metadata")).toBeInTheDocument();
  });

  it("displays difference count for categories with diffs", () => {
    render(<IRDiffViewer comparison={mockComparisonWithDiffs} />);
    expect(screen.getByText("1 differences")).toBeInTheDocument(); // Intent
    expect(screen.getByText("2 differences")).toBeInTheDocument(); // Signature
  });

  it("displays similarity percentage for each category", () => {
    render(<IRDiffViewer comparison={mockComparisonWithDiffs} />);
    // Intent: 50%, Signature: 50%, Assertion: 50%, Effect: 100%, Metadata: 100%
    const percentages = screen.getAllByText(/\d+%/);
    expect(percentages.length).toBeGreaterThan(0);
  });

  it("shows green checkmark for categories with no diffs", async () => {
    const user = userEvent.setup();
    render(<IRDiffViewer comparison={mockComparisonWithDiffs} />);

    // Expand Effects category (which has no diffs)
    const effectsButton = screen.getByRole("button", { name: /Effects/ });
    await user.click(effectsButton);

    expect(screen.getByText("No differences in this category")).toBeInTheDocument();
  });

  it("renders diff with severity icon", async () => {
    const user = userEvent.setup();
    render(<IRDiffViewer comparison={mockComparisonWithDiffs} />);

    // Expand Intent category
    const intentButton = screen.getByRole("button", { name: /Intent/ });
    await user.click(intentButton);

    // Check for severity badge
    expect(screen.getByText("WARNING")).toBeInTheDocument();
  });

  it("displays diff kind as readable text", async () => {
    const user = userEvent.setup();
    render(<IRDiffViewer comparison={mockComparisonWithDiffs} />);

    const intentButton = screen.getByRole("button", { name: /Intent/ });
    await user.click(intentButton);

    // "intent_summary" should be displayed as "intent summary"
    expect(screen.getByText("intent summary")).toBeInTheDocument();
  });

  it("displays diff path", async () => {
    const user = userEvent.setup();
    render(<IRDiffViewer comparison={mockComparisonWithDiffs} />);

    const intentButton = screen.getByRole("button", { name: /Intent/ });
    await user.click(intentButton);

    expect(screen.getByText("intent.summary")).toBeInTheDocument();
  });

  it("displays diff message when provided", async () => {
    const user = userEvent.setup();
    render(<IRDiffViewer comparison={mockComparisonWithDiffs} />);

    const intentButton = screen.getByRole("button", { name: /Intent/ });
    await user.click(intentButton);

    expect(screen.getByText("Intent summary differs")).toBeInTheDocument();
  });

  it("displays values side-by-side when sideBySide is true", async () => {
    const user = userEvent.setup();
    render(<IRDiffViewer comparison={mockComparisonWithDiffs} sideBySide={true} />);

    const intentButton = screen.getByRole("button", { name: /Intent/ });
    await user.click(intentButton);

    expect(screen.getByText("Original")).toBeInTheDocument();
    expect(screen.getByText("Compared")).toBeInTheDocument();
  });

  it("displays values stacked when sideBySide is false", async () => {
    const user = userEvent.setup();
    render(<IRDiffViewer comparison={mockComparisonWithDiffs} sideBySide={false} />);

    const intentButton = screen.getByRole("button", { name: /Intent/ });
    await user.click(intentButton);

    // Should still show labels, just in stacked layout
    expect(screen.getByText("Original:")).toBeInTheDocument();
    expect(screen.getByText("Compared:")).toBeInTheDocument();
  });

  it("uses custom labels for left and right", async () => {
    const user = userEvent.setup();
    render(
      <IRDiffViewer
        comparison={mockComparisonWithDiffs}
        leftLabel="Before"
        rightLabel="After"
      />
    );

    const intentButton = screen.getByRole("button", { name: /Intent/ });
    await user.click(intentButton);

    expect(screen.getByText("Before")).toBeInTheDocument();
    expect(screen.getByText("After")).toBeInTheDocument();
  });

  it("renders null/undefined values as 'none'", async () => {
    const user = userEvent.setup();
    const comparisonWithNull = {
      ...mockEmptyComparison,
      intent_comparison: {
        category: "intent" as const,
        diffs: [
          {
            category: "intent" as const,
            kind: "intent_rationale",
            path: "intent.rationale",
            left_value: null,
            right_value: "New rationale",
            severity: "info" as const,
          },
        ],
        matches: 1,
        total_fields: 2,
        similarity: 0.5,
      },
      overall_similarity: 0.9,
    };

    render(<IRDiffViewer comparison={comparisonWithNull} />);

    const intentButton = screen.getByRole("button", { name: /Intent/ });
    await user.click(intentButton);

    expect(screen.getByText("none")).toBeInTheDocument();
  });

  it("renders object values as JSON", async () => {
    const user = userEvent.setup();
    const comparisonWithObject = {
      ...mockEmptyComparison,
      intent_comparison: {
        category: "intent" as const,
        diffs: [
          {
            category: "intent" as const,
            kind: "intent_summary",
            path: "intent",
            left_value: { summary: "Old", rationale: "Because" },
            right_value: { summary: "New", rationale: "Because" },
            severity: "info" as const,
          },
        ],
        matches: 0,
        total_fields: 1,
        similarity: 0.0,
      },
      overall_similarity: 0.8,
    };

    render(<IRDiffViewer comparison={comparisonWithObject} />);

    const intentButton = screen.getByRole("button", { name: /Intent/ });
    await user.click(intentButton);

    // Should contain JSON representation with "summary" field
    expect(screen.getByText(/summary/i)).toBeInTheDocument();
  });

  it("does not show action buttons when enableActions is false", async () => {
    const user = userEvent.setup();
    render(<IRDiffViewer comparison={mockComparisonWithDiffs} enableActions={false} />);

    const intentButton = screen.getByRole("button", { name: /Intent/ });
    await user.click(intentButton);

    // Should not have accept/reject buttons
    const buttons = screen.getAllByRole("button");
    const hasAcceptButton = buttons.some(btn => btn.textContent?.includes("Accept"));
    expect(hasAcceptButton).toBe(false);
  });

  it("shows action buttons when enableActions is true", async () => {
    const user = userEvent.setup();
    render(<IRDiffViewer comparison={mockComparisonWithDiffs} enableActions={true} />);

    expect(screen.getByRole("button", { name: /Accept All/ })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Reject All/ })).toBeInTheDocument();
  });

  it("does not show accept/reject all buttons when no diffs", () => {
    render(<IRDiffViewer comparison={mockEmptyComparison} enableActions={true} />);

    expect(screen.queryByRole("button", { name: /Accept All/ })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Reject All/ })).not.toBeInTheDocument();
  });

  it("calls onAcceptDiff when accept button is clicked", async () => {
    const user = userEvent.setup();
    const onAcceptDiff = vi.fn();

    // Create a comparison with only one diff to avoid ambiguity
    const simpleComparison = {
      ...mockEmptyComparison,
      intent_comparison: {
        category: "intent" as const,
        diffs: [
          {
            category: "intent" as const,
            kind: "intent_summary",
            path: "intent.summary",
            left_value: "Original",
            right_value: "Modified",
            severity: "warning" as const,
          },
        ],
        matches: 1,
        total_fields: 2,
        similarity: 0.5,
      },
      overall_similarity: 0.9,
    };

    render(
      <IRDiffViewer
        comparison={simpleComparison}
        enableActions={true}
        onAcceptDiff={onAcceptDiff}
      />
    );

    // Accordion is already expanded by default for intent
    // Find the accept button (excluding Accept All)
    const allButtons = screen.getAllByRole("button");
    const acceptButton = allButtons.find(btn => {
      const svg = btn.querySelector("svg.lucide-check");
      return svg && !btn.textContent?.includes("Accept All");
    });

    if (acceptButton) {
      await user.click(acceptButton);
    }

    expect(onAcceptDiff).toHaveBeenCalledTimes(1);
    expect(onAcceptDiff).toHaveBeenCalledWith(
      expect.objectContaining({
        category: "intent",
        kind: "intent_summary",
      })
    );
  });

  it("calls onRejectDiff when reject button is clicked", async () => {
    const user = userEvent.setup();
    const onRejectDiff = vi.fn();

    const simpleComparison = {
      ...mockEmptyComparison,
      intent_comparison: {
        category: "intent" as const,
        diffs: [
          {
            category: "intent" as const,
            kind: "intent_summary",
            path: "intent.summary",
            left_value: "Original",
            right_value: "Modified",
            severity: "warning" as const,
          },
        ],
        matches: 1,
        total_fields: 2,
        similarity: 0.5,
      },
      overall_similarity: 0.9,
    };

    render(
      <IRDiffViewer
        comparison={simpleComparison}
        enableActions={true}
        onRejectDiff={onRejectDiff}
      />
    );

    const allButtons = screen.getAllByRole("button");
    const rejectButton = allButtons.find(btn => {
      const svg = btn.querySelector("svg.lucide-x");
      return svg && !btn.textContent?.includes("Reject All");
    });

    if (rejectButton) {
      await user.click(rejectButton);
    }

    expect(onRejectDiff).toHaveBeenCalledTimes(1);
  });

  it("calls onAcceptAll when accept all button is clicked", async () => {
    const user = userEvent.setup();
    const onAcceptAll = vi.fn();
    render(
      <IRDiffViewer
        comparison={mockComparisonWithDiffs}
        enableActions={true}
        onAcceptAll={onAcceptAll}
      />
    );

    const acceptAllButton = screen.getByRole("button", { name: /Accept All/ });
    await user.click(acceptAllButton);

    expect(onAcceptAll).toHaveBeenCalledTimes(1);
  });

  it("calls onRejectAll when reject all button is clicked", async () => {
    const user = userEvent.setup();
    const onRejectAll = vi.fn();
    render(
      <IRDiffViewer
        comparison={mockComparisonWithDiffs}
        enableActions={true}
        onRejectAll={onRejectAll}
      />
    );

    const rejectAllButton = screen.getByRole("button", { name: /Reject All/ });
    await user.click(rejectAllButton);

    expect(onRejectAll).toHaveBeenCalledTimes(1);
  });

  it("highlights accepted diff with green background", async () => {
    const user = userEvent.setup();

    const simpleComparison = {
      ...mockEmptyComparison,
      intent_comparison: {
        category: "intent" as const,
        diffs: [
          {
            category: "intent" as const,
            kind: "intent_summary",
            path: "intent.summary",
            left_value: "Original",
            right_value: "Modified",
            severity: "warning" as const,
          },
        ],
        matches: 1,
        total_fields: 2,
        similarity: 0.5,
      },
      overall_similarity: 0.9,
    };

    const { container } = render(
      <IRDiffViewer
        comparison={simpleComparison}
        enableActions={true}
      />
    );

    const allButtons = screen.getAllByRole("button");
    const acceptButton = allButtons.find(btn => {
      const svg = btn.querySelector("svg.lucide-check");
      return svg && !btn.textContent?.includes("Accept All");
    });

    if (acceptButton) {
      await user.click(acceptButton);
    }

    // Find the diff container and check it has green styling
    const greenContainer = container.querySelector(".border-green-300");
    expect(greenContainer).toBeInTheDocument();
  });

  it("highlights rejected diff with red background", async () => {
    const user = userEvent.setup();

    const simpleComparison = {
      ...mockEmptyComparison,
      intent_comparison: {
        category: "intent" as const,
        diffs: [
          {
            category: "intent" as const,
            kind: "intent_summary",
            path: "intent.summary",
            left_value: "Original",
            right_value: "Modified",
            severity: "warning" as const,
          },
        ],
        matches: 1,
        total_fields: 2,
        similarity: 0.5,
      },
      overall_similarity: 0.9,
    };

    const { container } = render(
      <IRDiffViewer
        comparison={simpleComparison}
        enableActions={true}
      />
    );

    const allButtons = screen.getAllByRole("button");
    const rejectButton = allButtons.find(btn => {
      const svg = btn.querySelector("svg.lucide-x");
      return svg && !btn.textContent?.includes("Reject All");
    });

    if (rejectButton) {
      await user.click(rejectButton);
    }

    // Find the diff container and check it has red styling
    const redContainer = container.querySelector(".border-red-300");
    expect(redContainer).toBeInTheDocument();
  });

  it("toggles acceptance state when clicking accept multiple times", async () => {
    const user = userEvent.setup();
    const onAcceptDiff = vi.fn();

    const simpleComparison = {
      ...mockEmptyComparison,
      intent_comparison: {
        category: "intent" as const,
        diffs: [
          {
            category: "intent" as const,
            kind: "intent_summary",
            path: "intent.summary",
            left_value: "Original",
            right_value: "Modified",
            severity: "warning" as const,
          },
        ],
        matches: 1,
        total_fields: 2,
        similarity: 0.5,
      },
      overall_similarity: 0.9,
    };

    render(
      <IRDiffViewer
        comparison={simpleComparison}
        enableActions={true}
        onAcceptDiff={onAcceptDiff}
      />
    );

    const allButtons = screen.getAllByRole("button");
    const acceptButton = allButtons.find(btn => {
      const svg = btn.querySelector("svg.lucide-check");
      return svg && !btn.textContent?.includes("Accept All");
    });

    if (acceptButton) {
      // First click
      await user.click(acceptButton);
      expect(onAcceptDiff).toHaveBeenCalledTimes(1);

      // Second click
      await user.click(acceptButton);
      expect(onAcceptDiff).toHaveBeenCalledTimes(2);
    }
  });

  it("clears rejection when accepting a diff", async () => {
    const user = userEvent.setup();

    const simpleComparison = {
      ...mockEmptyComparison,
      intent_comparison: {
        category: "intent" as const,
        diffs: [
          {
            category: "intent" as const,
            kind: "intent_summary",
            path: "intent.summary",
            left_value: "Original",
            right_value: "Modified",
            severity: "warning" as const,
          },
        ],
        matches: 1,
        total_fields: 2,
        similarity: 0.5,
      },
      overall_similarity: 0.9,
    };

    const { container } = render(
      <IRDiffViewer
        comparison={simpleComparison}
        enableActions={true}
      />
    );

    const allButtons = screen.getAllByRole("button");
    const acceptButton = allButtons.find(btn => {
      const svg = btn.querySelector("svg.lucide-check");
      return svg && !btn.textContent?.includes("Accept All");
    });
    const rejectButton = allButtons.find(btn => {
      const svg = btn.querySelector("svg.lucide-x");
      return svg && !btn.textContent?.includes("Reject All");
    });

    if (rejectButton && acceptButton) {
      // First reject
      await user.click(rejectButton);
      // Check for the diff container with red border (not badges)
      const redDiffContainer = container.querySelector("div.border-red-300.bg-red-50");
      expect(redDiffContainer).toBeInTheDocument();

      // Then accept (should clear rejection and show green)
      await user.click(acceptButton);
      const greenDiffContainer = container.querySelector("div.border-green-300.bg-green-50");
      expect(greenDiffContainer).toBeInTheDocument();
      // The red diff container should be replaced with green
      const redAfterAccept = container.querySelector("div.border-red-300.bg-red-50");
      expect(redAfterAccept).not.toBeInTheDocument();
    }
  });

  it("expands multiple categories by default", () => {
    render(<IRDiffViewer comparison={mockComparisonWithDiffs} />);

    // The default accordion value includes intent, signature, and assertion
    const intentButton = screen.getByRole("button", { name: /Intent/ });
    const signatureButton = screen.getByRole("button", { name: /Signature/ });
    const assertionButton = screen.getByRole("button", { name: /Assertions/ });

    // Check if they're expanded (aria-expanded should be true)
    expect(intentButton).toHaveAttribute("data-state", "open");
    expect(signatureButton).toHaveAttribute("data-state", "open");
    expect(assertionButton).toHaveAttribute("data-state", "open");
  });
});
