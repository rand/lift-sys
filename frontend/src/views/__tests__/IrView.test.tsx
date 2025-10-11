import { act, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { IrView } from "../IrView";
import { createTestQueryClient, renderWithClient } from "../../test/utils";

const samplePlan = {
  ir: {
    intent: { summary: "Verify sample", rationale: "Ensure invariants" },
    signature: {
      name: "sample_module",
      parameters: [{ name: "x", type_hint: "int" }],
      returns: "int",
    },
    effects: [],
    assertions: [{ predicate: "x > 0" }],
  },
  telemetry: {
    invariants: [{ predicate: "x > 0", status: "pending" }],
    typed_holes: [
      {
        identifier: "gap",
        type_hint: "Predicate",
        description: "Clarify invariant",
        clause: "assertions",
        assist: "Investigate assertion gap",
      },
    ],
  },
};

describe("IrView", () => {
  it("supports progressive disclosure for IR sections", async () => {
    const client = createTestQueryClient();
    client.setQueryData(["plan"], samplePlan);
    await act(async () => {
      renderWithClient(<IrView />, client);
      await Promise.resolve();
    });

    expect(screen.getByText("Verify sample")).toBeInTheDocument();

    expect(screen.getByText("No side effects recorded.")).not.toBeVisible();

    await userEvent.click(screen.getByText("Effects"));

    expect(screen.getByText("No side effects recorded.")).toBeInTheDocument();
  });

  it("reveals planner assists when selecting typed hole chips", async () => {
    const client = createTestQueryClient();
    client.setQueryData(["plan"], samplePlan);
    await act(async () => {
      renderWithClient(<IrView />, client);
      await Promise.resolve();
    });

    const chip = screen.getByRole("button", { name: /<\?gap: Predicate>/i });
    await userEvent.click(chip);

    expect(screen.getByText("Planner Assist")).toBeInTheDocument();
    expect(screen.getByText("Investigate assertion gap")).toBeInTheDocument();
  });
});
