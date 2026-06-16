import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import IssueCard from "../components/IssueCard";

const issue = {
  id: "button-name",
  title: "Buttons must have discernible text",
  severity: "High",
  wcag_criterion: "4.1.2",
  impact: "Screen reader users cannot identify the button.",
  occurrences: 3,
  selector: "header button.search-icon",
};

describe("IssueCard", () => {
  it("renders the issue title, severity, and WCAG criterion", () => {
    render(<IssueCard issue={issue} selected={false} onClick={() => {}} />);
    expect(screen.getByText("Buttons must have discernible text")).toBeInTheDocument();
    expect(screen.getByText("High")).toBeInTheDocument();
    expect(screen.getByText("WCAG 4.1.2")).toBeInTheDocument();
  });

  it("shows occurrence count", () => {
    render(<IssueCard issue={issue} selected={false} onClick={() => {}} />);
    expect(screen.getByText("3 occurrences")).toBeInTheDocument();
  });

  it("uses singular occurrence for count of 1", () => {
    render(<IssueCard issue={{ ...issue, occurrences: 1 }} selected={false} onClick={() => {}} />);
    expect(screen.getByText("1 occurrence")).toBeInTheDocument();
  });

  it("calls onClick when clicked", async () => {
    const user = userEvent.setup();
    const handler = vi.fn();
    render(<IssueCard issue={issue} selected={false} onClick={handler} />);
    await user.click(screen.getByRole("button"));
    expect(handler).toHaveBeenCalledOnce();
  });

  it("has aria-pressed=true when selected", () => {
    render(<IssueCard issue={issue} selected={true} onClick={() => {}} />);
    expect(screen.getByRole("button")).toHaveAttribute("aria-pressed", "true");
  });

  it("has aria-pressed=false when not selected", () => {
    render(<IssueCard issue={issue} selected={false} onClick={() => {}} />);
    expect(screen.getByRole("button")).toHaveAttribute("aria-pressed", "false");
  });

  it("applies selected class when selected", () => {
    const { container } = render(<IssueCard issue={issue} selected={true} onClick={() => {}} />);
    expect(container.firstChild).toHaveClass("selected");
  });
});
