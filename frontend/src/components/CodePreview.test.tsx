import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { CodePreview } from "./CodePreview";

describe("CodePreview", () => {
  const mockCode = `def hello(name: str) -> str:
    """Greet someone."""
    return f"Hello, {name}!"`;

  const mockIR = {
    intent: { summary: "Greet someone" },
    signature: {
      name: "hello",
      parameters: [{ name: "name", type_hint: "str" }],
      returns: "str",
    },
  };

  const mockValidation = {
    isValid: true,
    fidelityScore: 1.0,
    differences: [],
    warnings: [],
  };

  beforeEach(() => {
    // Mock clipboard API
    Object.defineProperty(navigator, "clipboard", {
      value: {
        writeText: vi.fn(() => Promise.resolve()),
      },
      writable: true,
      configurable: true,
    });

    // Mock URL.createObjectURL
    global.URL.createObjectURL = vi.fn(() => "blob:mock-url");
    global.URL.revokeObjectURL = vi.fn();
  });

  it("renders code with syntax highlighting", () => {
    render(<CodePreview code={mockCode} />);
    expect(screen.getByText("Generated Code")).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: /code/i })).toBeInTheDocument();
  });

  it("displays copy button", () => {
    render(<CodePreview code={mockCode} />);
    expect(screen.getByRole("button", { name: /copy/i })).toBeInTheDocument();
  });

  it("displays download button", () => {
    render(<CodePreview code={mockCode} />);
    expect(screen.getByRole("button", { name: /download/i })).toBeInTheDocument();
  });

  it("copies code to clipboard when copy button is clicked", async () => {
    const user = userEvent.setup();
    const writeTextMock = vi.fn(() => Promise.resolve());
    Object.defineProperty(navigator, "clipboard", {
      value: {
        writeText: writeTextMock,
      },
      writable: true,
      configurable: true,
    });

    render(<CodePreview code={mockCode} />);

    const copyButton = screen.getByRole("button", { name: /copy/i });
    await user.click(copyButton);

    expect(writeTextMock).toHaveBeenCalledWith(mockCode);
    await waitFor(() => {
      expect(screen.getByText("Copied")).toBeInTheDocument();
    });
  });

  it("calls onCopy callback when copy is successful", async () => {
    const user = userEvent.setup();
    const onCopy = vi.fn();
    render(<CodePreview code={mockCode} onCopy={onCopy} />);

    const copyButton = screen.getByRole("button", { name: /copy/i });
    await user.click(copyButton);

    await waitFor(() => {
      expect(onCopy).toHaveBeenCalledTimes(1);
    });
  });

  it("downloads code when download button is clicked", async () => {
    const user = userEvent.setup();
    const createElementSpy = vi.spyOn(document, "createElement");
    render(<CodePreview code={mockCode} filename="test.py" />);

    const downloadButton = screen.getByRole("button", { name: /download/i });
    await user.click(downloadButton);

    expect(createElementSpy).toHaveBeenCalledWith("a");
    expect(global.URL.createObjectURL).toHaveBeenCalled();
  });

  it("calls onDownload callback when download button is clicked", async () => {
    const user = userEvent.setup();
    const onDownload = vi.fn();
    render(<CodePreview code={mockCode} onDownload={onDownload} />);

    const downloadButton = screen.getByRole("button", { name: /download/i });
    await user.click(downloadButton);

    expect(onDownload).toHaveBeenCalledTimes(1);
  });

  it("displays perfect match badge for 100% fidelity", () => {
    render(<CodePreview code={mockCode} validation={mockValidation} />);
    expect(screen.getByText("Perfect Match")).toBeInTheDocument();
  });

  it("displays high fidelity badge for 80-99% fidelity", () => {
    const validation = {
      ...mockValidation,
      fidelityScore: 0.85,
    };
    render(<CodePreview code={mockCode} validation={validation} />);
    expect(screen.getByText(/High Fidelity \(85%\)/)).toBeInTheDocument();
  });

  it("displays partial match badge for <80% fidelity", () => {
    const validation = {
      ...mockValidation,
      fidelityScore: 0.65,
    };
    render(<CodePreview code={mockCode} validation={validation} />);
    expect(screen.getByText(/Partial Match \(65%\)/)).toBeInTheDocument();
  });

  it("displays validation failed badge when validation fails", () => {
    const validation = {
      isValid: false,
      fidelityScore: 0.5,
      differences: [],
      warnings: [],
    };
    render(<CodePreview code={mockCode} validation={validation} />);
    expect(screen.getByText("Validation Failed")).toBeInTheDocument();
  });

  it("renders code tab by default", () => {
    render(<CodePreview code={mockCode} />);
    expect(screen.getByRole("tab", { name: /code/i })).toHaveAttribute("data-state", "active");
  });

  it("switches to validation tab when clicked", async () => {
    const user = userEvent.setup();
    const validation = {
      isValid: true,
      fidelityScore: 0.95,
      differences: [],
      warnings: ["Type annotation missing"],
    };
    render(<CodePreview code={mockCode} validation={validation} />);

    const validationTab = screen.getByRole("tab", { name: /validation/i });
    await user.click(validationTab);

    expect(validationTab).toHaveAttribute("data-state", "active");
    expect(screen.getByText("Warnings")).toBeInTheDocument();
    expect(screen.getByText("Type annotation missing")).toBeInTheDocument();
  });

  it("displays differences in validation tab", async () => {
    const user = userEvent.setup();
    const validation = {
      isValid: false,
      fidelityScore: 0.8,
      differences: [
        {
          kind: "PARAMETER_TYPE",
          path: "signature.parameters[0].type_hint",
          originalValue: "str",
          extractedValue: "Any",
          severity: "warning" as const,
        },
      ],
      warnings: [],
    };
    render(<CodePreview code={mockCode} validation={validation} />);

    const validationTab = screen.getByRole("tab", { name: /validation/i });
    await user.click(validationTab);

    expect(screen.getByText("Differences Detected")).toBeInTheDocument();
    expect(screen.getByText("PARAMETER_TYPE")).toBeInTheDocument();
    expect(screen.getByText("signature.parameters[0].type_hint")).toBeInTheDocument();
  });

  it("disables validation tab when no validation data", () => {
    render(<CodePreview code={mockCode} />);
    const validationTab = screen.getByRole("tab", { name: /validation/i });
    expect(validationTab).toBeDisabled();
  });

  it("switches to IR comparison tab when clicked", async () => {
    const user = userEvent.setup();
    render(<CodePreview code={mockCode} ir={mockIR} />);

    const irTab = screen.getByRole("tab", { name: /ir comparison/i });
    await user.click(irTab);

    expect(irTab).toHaveAttribute("data-state", "active");
    expect(screen.getByText(/"intent"/)).toBeInTheDocument();
  });

  it("disables IR comparison tab when no IR data", () => {
    render(<CodePreview code={mockCode} />);
    const irTab = screen.getByRole("tab", { name: /ir comparison/i });
    expect(irTab).toBeDisabled();
  });

  it("displays side-by-side comparison when showComparison is true", async () => {
    const user = userEvent.setup();
    render(<CodePreview code={mockCode} ir={mockIR} showComparison={true} />);

    const irTab = screen.getByRole("tab", { name: /ir comparison/i });
    await user.click(irTab);

    expect(screen.getByText("Original IR")).toBeInTheDocument();
    expect(screen.getByText("Extracted IR")).toBeInTheDocument();
  });

  it("switches to metadata tab when clicked", async () => {
    const user = userEvent.setup();
    const metadata = {
      language: "python",
      target_version: "3.10",
      generated_at: "2025-10-13T00:00:00Z",
    };
    render(<CodePreview code={mockCode} metadata={metadata} />);

    const metadataTab = screen.getByRole("tab", { name: /metadata/i });
    await user.click(metadataTab);

    expect(metadataTab).toHaveAttribute("data-state", "active");
    expect(screen.getByText("language:")).toBeInTheDocument();
    expect(screen.getByText("python")).toBeInTheDocument();
  });

  it("disables metadata tab when no metadata", () => {
    render(<CodePreview code={mockCode} />);
    const metadataTab = screen.getByRole("tab", { name: /metadata/i });
    expect(metadataTab).toBeDisabled();
  });

  it("displays no metadata message when metadata is empty", async () => {
    const user = userEvent.setup();
    render(<CodePreview code={mockCode} metadata={{}} />);

    const metadataTab = screen.getByRole("tab", { name: /metadata/i });
    await user.click(metadataTab);

    expect(screen.getByText("No metadata available")).toBeInTheDocument();
  });

  it("uses custom filename for download", async () => {
    const user = userEvent.setup();
    const clickSpy = vi.fn();
    const originalCreateElement = document.createElement;

    document.createElement = vi.fn((tagName: string) => {
      const element = originalCreateElement.call(document, tagName) as HTMLAnchorElement;
      if (tagName === "a") {
        element.click = clickSpy;
      }
      return element;
    });

    render(<CodePreview code={mockCode} filename="custom.py" />);

    const downloadButton = screen.getByRole("button", { name: /download/i });
    await user.click(downloadButton);

    await waitFor(() => {
      expect(clickSpy).toHaveBeenCalled();
    });

    document.createElement = originalCreateElement;
  });

  it("renders with different language syntax highlighting", () => {
    const jsCode = "function hello() { return 'Hello'; }";
    render(<CodePreview code={jsCode} language="javascript" />);
    expect(screen.getByText("Generated Code")).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: /code/i })).toBeInTheDocument();
  });

  it("displays multiple warnings in validation tab", async () => {
    const user = userEvent.setup();
    const validation = {
      isValid: true,
      fidelityScore: 0.9,
      differences: [],
      warnings: ["Warning 1", "Warning 2", "Warning 3"],
    };
    render(<CodePreview code={mockCode} validation={validation} />);

    const validationTab = screen.getByRole("tab", { name: /validation/i });
    await user.click(validationTab);

    expect(screen.getByText("Warning 1")).toBeInTheDocument();
    expect(screen.getByText("Warning 2")).toBeInTheDocument();
    expect(screen.getByText("Warning 3")).toBeInTheDocument();
  });

  it("handles copy failure gracefully", async () => {
    const user = userEvent.setup();
    const consoleErrorSpy = vi.spyOn(console, "error").mockImplementation(() => {});
    Object.defineProperty(navigator, "clipboard", {
      value: {
        writeText: vi.fn(() => Promise.reject(new Error("Copy failed"))),
      },
      writable: true,
      configurable: true,
    });

    render(<CodePreview code={mockCode} />);

    const copyButton = screen.getByRole("button", { name: /copy/i });
    await user.click(copyButton);

    await waitFor(() => {
      expect(consoleErrorSpy).toHaveBeenCalled();
    });

    consoleErrorSpy.mockRestore();
  });
});
