import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import ScanPage from "../pages/ScanPage";
import { postJson } from "../services/api";

vi.mock("../services/api", () => ({
  postJson: vi.fn(),
  getJson: vi.fn(),
}));

const emptyScan = {
  url: "https://app.example.com/dashboard",
  issues: [],
  summary: { Critical: 0, High: 0, Medium: 0, Low: 0 },
  source: "live",
  notice: null,
};

const loginSuccess = {
  success: true,
  storage_state: { cookies: [{ name: "session", value: "abc" }], origins: [] },
  screenshot: "data:image/png;base64,ZmFrZQ==",
  final_url: "https://app.example.com/home",
  source: "live",
  notice: null,
};

function renderPage() {
  const setState = vi.fn();
  render(<ScanPage state={{}} setState={setState} next={() => {}} />);
  return setState;
}

async function fillLoginForm(user) {
  await user.type(screen.getByLabelText(/page url to audit/i), "https://app.example.com/dashboard");
  await user.click(screen.getByLabelText(/this page needs a login/i));
  await user.type(screen.getByLabelText(/login page url/i), "https://app.example.com/login");
  await user.type(screen.getByLabelText(/username or email/i), "tester@example.com");
  await user.type(screen.getByLabelText(/^password$/i), "hunter2");
}

describe("ScanPage authenticated scanning", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("hides login fields until the toggle is checked", async () => {
    const user = userEvent.setup();
    renderPage();
    expect(screen.queryByLabelText(/login page url/i)).not.toBeInTheDocument();
    await user.click(screen.getByLabelText(/this page needs a login/i));
    expect(screen.getByLabelText(/login page url/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/username or email/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/^password$/i)).toBeInTheDocument();
  });

  it("marks the credential fields with the right types and autocomplete", async () => {
    const user = userEvent.setup();
    renderPage();
    await user.click(screen.getByLabelText(/this page needs a login/i));
    const password = screen.getByLabelText(/^password$/i);
    expect(password).toHaveAttribute("type", "password");
    expect(password).toHaveAttribute("autocomplete", "current-password");
    expect(screen.getByLabelText(/username or email/i)).toHaveAttribute("autocomplete", "username");
  });

  it("states the SSO/MFA/CAPTCHA limitations", async () => {
    const user = userEvent.setup();
    renderPage();
    await user.click(screen.getByLabelText(/this page needs a login/i));
    expect(screen.getByText(/2FA\/MFA/)).toBeInTheDocument();
    expect(screen.getByText(/CAPTCHA/)).toBeInTheDocument();
  });

  it("logs in first, then scans with the captured storage_state and shows the proof screenshot", async () => {
    const user = userEvent.setup();
    postJson.mockResolvedValueOnce(loginSuccess).mockResolvedValueOnce(emptyScan);
    let latestState = {};
    const setState = vi.fn((updater) => {
      latestState = updater(latestState);
    });
    const { rerender } = render(<ScanPage state={{}} setState={setState} next={() => {}} />);
    await fillLoginForm(user);
    await user.click(screen.getByRole("button", { name: /run accessibility scan/i }));

    await waitFor(() => expect(postJson).toHaveBeenCalledTimes(2));
    expect(postJson).toHaveBeenNthCalledWith(1, "/api/login", {
      login_url: "https://app.example.com/login",
      username: "tester@example.com",
      password: "hunter2",
    });
    expect(postJson).toHaveBeenNthCalledWith(2, "/api/scan", {
      url: "https://app.example.com/dashboard",
      storage_state: loginSuccess.storage_state,
    });

    rerender(<ScanPage state={latestState} setState={setState} next={() => {}} />);
    expect(screen.getByText(/login verified/i)).toBeInTheDocument();
    const proof = screen.getByRole("img", { name: /captured after logging in/i });
    expect(proof).toHaveAttribute("src", loginSuccess.screenshot);
  });

  it("does not scan when the login fails, and surfaces the backend notice", async () => {
    const user = userEvent.setup();
    postJson.mockResolvedValueOnce({
      success: false,
      storage_state: null,
      screenshot: null,
      final_url: "https://app.example.com/login",
      source: "live",
      notice: "The page still shows a login form after submitting.",
    });
    renderPage();
    await fillLoginForm(user);
    await user.click(screen.getByRole("button", { name: /run accessibility scan/i }));

    await waitFor(() =>
      expect(screen.getByRole("alert")).toHaveTextContent(/still shows a login form/i),
    );
    expect(postJson).toHaveBeenCalledTimes(1);
    expect(postJson).toHaveBeenCalledWith("/api/login", expect.anything());
  });

  it("scans directly without calling /api/login when the toggle is off", async () => {
    const user = userEvent.setup();
    postJson.mockResolvedValueOnce(emptyScan);
    renderPage();
    await user.type(screen.getByLabelText(/page url to audit/i), "https://example.com");
    await user.click(screen.getByRole("button", { name: /run accessibility scan/i }));

    await waitFor(() => expect(postJson).toHaveBeenCalledTimes(1));
    expect(postJson).toHaveBeenCalledWith("/api/scan", { url: "https://example.com" });
  });
});
