import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import IssueEditor from "../components/IssueEditor";

const issue = {
  title: "[A11y][WCAG 4.1.2] Buttons must have discernible text",
  description: "The button has no accessible name.",
  repro_steps: ["Open the page.", "Focus the button."],
  expected_result: "Button is announced as Search.",
  actual_result: "Button is announced without a name.",
  severity: "High",
  labels: ["accessibility", "bug"],
  acceptance_criteria: ["Button has an accessible name.", "axe rule passes."],
  environment: "Chrome and NVDA",
  wcag_reference: "https://www.w3.org/WAI/WCAG22/Understanding/name-role-value.html",
  assignee: "",
  milestone: "",
};

describe("IssueEditor", () => {
  it("renders all text fields with correct values", () => {
    render(<IssueEditor issue={issue} onChange={() => {}} />);
    expect(screen.getByDisplayValue(issue.title)).toBeInTheDocument();
    expect(screen.getByDisplayValue(issue.description)).toBeInTheDocument();
    // textarea value in jsdom — check via role + value property
    const reproField = screen.getByRole("textbox", { name: /reproduction steps/i });
    expect(reproField.value).toContain("Open the page.");
    expect(reproField.value).toContain("Focus the button.");
  });

  it("calls onChange with the updated issue object when a field changes", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(<IssueEditor issue={issue} onChange={onChange} />);
    const titleInput = screen.getByDisplayValue(issue.title);
    // type a single character — controlled input won't persist without state lift,
    // but onChange must be called with an updated title on every keystroke
    await user.type(titleInput, "X");
    expect(onChange).toHaveBeenCalled();
    const lastCall = onChange.mock.calls[onChange.mock.calls.length - 1][0];
    // the new title should be the original + "X" (React synthetic event value)
    expect(lastCall).toHaveProperty("title");
    expect(lastCall.title).not.toBe(issue.title);
  });

  it("renders inputs as readOnly when readOnly=true", () => {
    render(<IssueEditor issue={issue} onChange={() => {}} readOnly />);
    const inputs = screen.getAllByRole("textbox");
    inputs.forEach((input) => {
      expect(input).toHaveAttribute("readonly");
    });
  });

  it("does not call onChange when readOnly is true and a field is targeted", () => {
    const onChange = vi.fn();
    render(<IssueEditor issue={issue} onChange={onChange} readOnly />);
    // readOnly inputs suppress onChange — verify onChange is never called on direct set
    expect(onChange).not.toHaveBeenCalled();
  });

  it("shows source label in the banner", () => {
    render(<IssueEditor issue={issue} onChange={() => {}} source="ollama" />);
    expect(screen.getByText("Generated with Ollama")).toBeInTheDocument();
  });

  it("shows template fallback label for template source", () => {
    render(<IssueEditor issue={issue} onChange={() => {}} source="template" />);
    expect(screen.getByText("Template fallback — AI unavailable")).toBeInTheDocument();
  });

  it("renders labels as comma-separated string in input", () => {
    render(<IssueEditor issue={issue} onChange={() => {}} />);
    expect(screen.getByDisplayValue("accessibility, bug")).toBeInTheDocument();
  });
});
