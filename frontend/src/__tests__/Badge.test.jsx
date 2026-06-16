import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import Badge from "../components/Badge";

describe("Badge", () => {
  it("renders children", () => {
    render(<Badge>Critical</Badge>);
    expect(screen.getByText("Critical")).toBeInTheDocument();
  });

  it("applies tone class in lowercase", () => {
    const { container } = render(<Badge tone="Critical">Critical</Badge>);
    expect(container.firstChild).toHaveClass("badge", "critical");
  });

  it("renders without tone class when tone is empty", () => {
    const { container } = render(<Badge>Open</Badge>);
    expect(container.firstChild).toHaveClass("badge");
    expect(container.firstChild.className.trim()).toBe("badge");
  });

  it("lowercases mixed-case tone", () => {
    const { container } = render(<Badge tone="High">High</Badge>);
    expect(container.firstChild).toHaveClass("high");
  });
});
