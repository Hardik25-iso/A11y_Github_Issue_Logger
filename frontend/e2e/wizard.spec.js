import { expect, test } from "@playwright/test";

// Shared scan/issue data used across the wizard
const SCAN_RESPONSE = {
  url: "https://example.com",
  source: "fallback",
  notice: "Demo results shown. Enable live scanning to audit the requested page.",
  issues: [
    {
      id: "image-alt",
      title: "Images must have alternative text",
      severity: "Critical",
      wcag_criterion: "1.1.1",
      wcag_url: "https://www.w3.org/WAI/WCAG22/Understanding/non-text-content.html",
      element: '<img src="/hero.jpg">',
      selector: "main .hero img",
      impact: "Screen reader users cannot understand the featured image.",
      description: "The image does not have an alt attribute.",
      occurrences: 2,
      tags: ["accessibility", "wcag-1.1.1"],
    },
    {
      id: "button-name",
      title: "Buttons must have discernible text",
      severity: "High",
      wcag_criterion: "4.1.2",
      wcag_url: "https://www.w3.org/WAI/WCAG22/Understanding/name-role-value.html",
      element: '<button class="search-icon"></button>',
      selector: "header button.search-icon",
      impact: "Screen reader users cannot determine the button action.",
      description: "The icon-only button has no accessible name.",
      occurrences: 1,
      tags: ["accessibility", "wcag-4.1.2"],
    },
  ],
  summary: { Critical: 1, High: 1, Medium: 0, Low: 0 },
};

const SEARCH_RESPONSE = {
  similar_issues: [
    {
      number: 42,
      title: "Images are missing alt text on product pages",
      state: "open",
      labels: ["accessibility", "bug"],
      assignee: null,
      created_at: "2026-05-01T10:00:00Z",
      body: "WCAG 1.1.1 violation: product images missing alt text.",
      html_url: "https://github.com/example/repo/issues/42",
      similarity_score: 8.5,
      similarity_explanation: "Matches the same WCAG criterion and element type.",
    },
  ],
  ai_summary: "Found 1 related issue in example/repo, ranked by keyword similarity.",
  source: "github",
};

const GENERATED_RESPONSE = {
  generated_issue: {
    title: "[A11y][WCAG 1.1.1] Images must have alternative text",
    description: "The featured image on https://example.com is missing an alt attribute.",
    repro_steps: [
      "Open https://example.com in Chrome.",
      "Run an axe scan via DevTools.",
      "Locate main .hero img.",
      "Observe the WCAG 1.1.1 violation.",
    ],
    expected_result: "The image has a descriptive alt attribute.",
    actual_result: "The image has no alt attribute and fails WCAG 1.1.1.",
    severity: "Critical",
    labels: ["accessibility", "bug", "wcag-1.1.1", "needs-triage"],
    acceptance_criteria: [
      "All hero images have descriptive alt text.",
      "The axe rule image-alt passes.",
      "Verified with screen reader.",
    ],
    environment: "Desktop Chrome; axe-core automated scan",
    wcag_reference: "https://www.w3.org/WAI/WCAG22/Understanding/non-text-content.html",
    assignee: "",
    milestone: "",
  },
  source: "template",
};

const LOG_RESPONSE = {
  issue_number: 101,
  html_url: "https://github.com/example/repo/issues/101",
};

function mockApi(page) {
  page.route("**/api/config", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        default_repo: "example/repo",
        github_configured: true,
        ai_provider: "template",
        ai_configured: true,
        live_scan_enabled: false,
      }),
    }),
  );
  page.route("**/api/scan", (route) =>
    route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(SCAN_RESPONSE) }),
  );
  page.route("**/api/search-issues", (route) =>
    route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(SEARCH_RESPONSE) }),
  );
  page.route("**/api/generate-issue", (route) =>
    route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(GENERATED_RESPONSE) }),
  );
  page.route("**/api/log-issue", (route) =>
    route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(LOG_RESPONSE) }),
  );
}

test.beforeEach(async ({ page }) => {
  mockApi(page);
  await page.goto("/");
});

// ── Step 1: Scan ─────────────────────────────────────────────────────────────

test("shows hero and scan form on step 1", async ({ page }) => {
  await expect(page.getByRole("heading", { level: 1 })).toContainText(
    "Turn accessibility findings into actionable GitHub issues",
  );
  await expect(page.getByLabel("Public page URL")).toBeVisible();
  await expect(page.getByRole("button", { name: "Scan page" })).toBeVisible();
});

test("displays scan results after form submission", async ({ page }) => {
  await page.getByLabel("Public page URL").fill("https://example.com");
  await page.getByRole("button", { name: "Scan page" }).click();
  await expect(page.getByText("Demo results shown")).toBeVisible();
  await expect(page.getByText("Images must have alternative text")).toBeVisible();
  await expect(page.getByText("Buttons must have discernible text")).toBeVisible();
});

test("severity filter hides non-matching issues", async ({ page }) => {
  await page.getByLabel("Public page URL").fill("https://example.com");
  await page.getByRole("button", { name: "Scan page" }).click();
  await page.getByLabel(/filter by severity/i).selectOption("High");
  await expect(page.getByText("Buttons must have discernible text")).toBeVisible();
  await expect(page.getByText("Images must have alternative text")).not.toBeVisible();
});

test("continue button is disabled until an issue is selected", async ({ page }) => {
  await page.getByLabel("Public page URL").fill("https://example.com");
  await page.getByRole("button", { name: "Scan page" }).click();
  const continueBtn = page.getByRole("button", { name: /find similar issues/i });
  await expect(continueBtn).toBeDisabled();
  await page.getByRole("button", { name: /images must have alternative text/i }).click();
  await expect(continueBtn).toBeEnabled();
});

// ── Step 2: Compare ───────────────────────────────────────────────────────────

test("navigates to compare step and shows similar issues", async ({ page }) => {
  await page.getByLabel("Public page URL").fill("https://example.com");
  await page.getByRole("button", { name: "Scan page" }).click();
  await page.getByRole("button", { name: /images must have alternative text/i }).click();
  await page.getByRole("button", { name: /find similar issues/i }).click();
  await expect(page.getByRole("heading", { name: /review similar github issues/i })).toBeVisible();
  await expect(page.getByText("Images are missing alt text on product pages")).toBeVisible();
});

test("can select a reference issue and proceed", async ({ page }) => {
  await page.getByLabel("Public page URL").fill("https://example.com");
  await page.getByRole("button", { name: "Scan page" }).click();
  await page.getByRole("button", { name: /images must have alternative text/i }).click();
  await page.getByRole("button", { name: /find similar issues/i }).click();
  const generateBtn = page.getByRole("button", { name: /generate issue/i });
  await expect(generateBtn).toBeDisabled();
  await page.getByRole("button", { name: /images are missing alt text/i }).click();
  await expect(generateBtn).toBeEnabled();
});

test("can select create from scratch and proceed", async ({ page }) => {
  await page.getByLabel("Public page URL").fill("https://example.com");
  await page.getByRole("button", { name: "Scan page" }).click();
  await page.getByRole("button", { name: /images must have alternative text/i }).click();
  await page.getByRole("button", { name: /find similar issues/i }).click();
  await page.getByRole("button", { name: /create from scratch/i }).click();
  await expect(page.getByRole("button", { name: /generate issue/i })).toBeEnabled();
});

// ── Step 3: Generate ──────────────────────────────────────────────────────────

test("shows generated issue draft", async ({ page }) => {
  // scan
  await page.getByLabel("Public page URL").fill("https://example.com");
  await page.getByRole("button", { name: "Scan page" }).click();
  await page.getByRole("button", { name: /images must have alternative text/i }).click();
  await page.getByRole("button", { name: /find similar issues/i }).click();
  // compare
  await page.getByRole("button", { name: /create from scratch/i }).click();
  await page.getByRole("button", { name: /generate issue/i }).click();
  // generate
  await expect(page.getByRole("textbox", { name: /title/i })).toHaveValue("[A11y][WCAG 1.1.1] Images must have alternative text");
  await expect(page.getByText("Template fallback — AI unavailable")).toBeVisible();
});

// ── Step 4: Review & log ──────────────────────────────────────────────────────

test("full wizard: scan → compare → generate → log → success", async ({ page }) => {
  // step 1
  await page.getByLabel("Public page URL").fill("https://example.com");
  await page.getByRole("button", { name: "Scan page" }).click();
  await page.getByRole("button", { name: /images must have alternative text/i }).click();
  await page.getByRole("button", { name: /find similar issues/i }).click();
  // step 2
  await page.getByRole("button", { name: /create from scratch/i }).click();
  await page.getByRole("button", { name: /generate issue/i }).click();
  // step 3
  await page.getByRole("button", { name: /review and log/i }).click();
  // step 4
  await expect(page.getByRole("heading", { name: /ready to log/i })).toBeVisible();
  const logBtn = page.getByRole("button", { name: /log issue to github/i });
  await expect(logBtn).toBeEnabled();
  await logBtn.click();
  await expect(page.getByText("Issue #101 created")).toBeVisible();
  await expect(page.getByRole("link", { name: /open on github/i })).toHaveAttribute(
    "href",
    "https://github.com/example/repo/issues/101",
  );
});

// ── Back navigation ───────────────────────────────────────────────────────────

test("back button from compare returns to scan with selection preserved", async ({ page }) => {
  await page.getByLabel("Public page URL").fill("https://example.com");
  await page.getByRole("button", { name: "Scan page" }).click();
  await page.getByRole("button", { name: /images must have alternative text/i }).click();
  await page.getByRole("button", { name: /find similar issues/i }).click();
  await page.getByRole("button", { name: /← back/i }).click();
  await expect(page.getByRole("heading", { level: 1 })).toContainText(
    "Turn accessibility findings into actionable GitHub issues",
  );
});

// ── Error handling ────────────────────────────────────────────────────────────

test("shows error alert when scan fails", async ({ page }) => {
  await page.unroute("**/api/scan");
  await page.route("**/api/scan", (route) =>
    route.fulfill({ status: 422, contentType: "application/json", body: JSON.stringify({ detail: "URL is not a public address." }) }),
  );
  await page.getByLabel("Public page URL").fill("https://example.com");
  await page.getByRole("button", { name: "Scan page" }).click();
  await expect(page.getByRole("alert")).toContainText("URL is not a public address.");
});
