import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import Steps from "../components/Steps";

describe("Steps", () => {
  it("marks the current step as active with aria-current=step", () => {
    render(<Steps step={2} />);
    const activeStep = screen.getByText("Compare").closest("[aria-current]");
    expect(activeStep).toHaveAttribute("aria-current", "step");
  });

  it("marks completed steps as done", () => {
    render(<Steps step={3} />);
    const scanStep = screen.getByText("Scan").closest(".step");
    const compareStep = screen.getByText("Compare").closest(".step");
    expect(scanStep).toHaveClass("done");
    expect(compareStep).toHaveClass("done");
  });

  it("does not mark future steps as active or done", () => {
    render(<Steps step={1} />);
    const reviewStep = screen.getByText("Review & Log").closest(".step");
    expect(reviewStep).not.toHaveClass("active");
    expect(reviewStep).not.toHaveClass("done");
  });

  it("renders all four step labels", () => {
    render(<Steps step={1} />);
    ["Scan", "Compare", "Generate", "Review & Log"].forEach((label) => {
      expect(screen.getByText(label)).toBeInTheDocument();
    });
  });

  it("has accessible nav landmark with label", () => {
    render(<Steps step={1} />);
    expect(screen.getByRole("navigation", { name: /workflow progress/i })).toBeInTheDocument();
  });
});
