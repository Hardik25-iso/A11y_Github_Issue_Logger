import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import IssueTable from "../components/IssueTable";

const issues = [
  { id: "image-alt", title: "Images must have alternative text", severity: "Critical", wcag_criterion: "1.1.1", occurrences: 14, selector: "main .hero img" },
  { id: "button-name", title: "Buttons must have discernible text", severity: "High", wcag_criterion: "4.1.2", occurrences: 3, selector: "header button.search-icon" },
];

describe("IssueTable", () => {
  it("renders a listbox with one option per issue", () => {
    render(<IssueTable issues={issues} selectedId={null} onSelect={() => {}} />);
    expect(screen.getByRole("listbox", { name: /accessibility issues/i })).toBeInTheDocument();
    expect(screen.getAllByRole("option")).toHaveLength(2);
  });

  it("shows title, severity, WCAG and selector", () => {
    render(<IssueTable issues={issues} selectedId={null} onSelect={() => {}} />);
    expect(screen.getByText("Images must have alternative text")).toBeInTheDocument();
    expect(screen.getByText("Critical")).toBeInTheDocument();
    expect(screen.getByText("1.1.1")).toBeInTheDocument();
    expect(screen.getByText("main .hero img")).toBeInTheDocument();
  });

  it("calls onSelect when a row is clicked", async () => {
    const user = userEvent.setup();
    const onSelect = vi.fn();
    render(<IssueTable issues={issues} selectedId={null} onSelect={onSelect} />);
    await user.click(screen.getByRole("option", { name: /images must have alternative text/i }));
    expect(onSelect).toHaveBeenCalledWith(issues[0]);
  });

  it("marks the selected row with aria-selected", () => {
    render(<IssueTable issues={issues} selectedId="button-name" onSelect={() => {}} />);
    expect(screen.getByRole("option", { name: /buttons must have discernible text/i })).toHaveAttribute("aria-selected", "true");
    expect(screen.getByRole("option", { name: /images must have alternative text/i })).toHaveAttribute("aria-selected", "false");
  });

  it("moves focus with ArrowDown and selects with Enter (keyboard)", async () => {
    const user = userEvent.setup();
    const onSelect = vi.fn();
    render(<IssueTable issues={issues} selectedId={null} onSelect={onSelect} />);
    const first = screen.getByRole("option", { name: /images must have alternative text/i });
    first.focus();
    await user.keyboard("{ArrowDown}");
    expect(screen.getByRole("option", { name: /buttons must have discernible text/i })).toHaveFocus();
    await user.keyboard("{Enter}");
    expect(onSelect).toHaveBeenCalledWith(issues[1]);
  });

  it("uses roving tabindex — exactly one row is tabbable", () => {
    render(<IssueTable issues={issues} selectedId={null} onSelect={() => {}} />);
    const tabbable = screen.getAllByRole("option").filter((el) => el.getAttribute("tabindex") === "0");
    expect(tabbable).toHaveLength(1);
  });
});
