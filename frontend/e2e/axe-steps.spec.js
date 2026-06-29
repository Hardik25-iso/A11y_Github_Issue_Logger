import { expect, test } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

/**
 * Self-audit beyond the home page: the tool must pass its own accessibility
 * bar on every wizard step (and on mobile), not just the landing screen.
 * Fails on any serious/critical axe violation.
 */

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
      body: "WCAG 1.1.1 violation.",
      html_url: "https://github.com/example/repo/issues/42",
      similarity_score: 8.5,
      similarity_explanation: "Matches the same WCAG criterion and element type.",
    },
  ],
  ai_summary: "Found 1 related issue, ranked by AI relevance.",
  source: "github",
};

const GENERATED_RESPONSE = {
  generated_issue: {
    title: "[A11y][WCAG 1.1.1] Images must have alternative text",
    description: "The featured image is missing an alt attribute.",
    repro_steps: ["Open the page.", "Run an axe scan.", "Observe the violation."],
    expected_result: "The image has a descriptive alt attribute.",
    actual_result: "The image has no alt attribute.",
    severity: "Critical",
    labels: ["accessibility", "bug", "wcag-1.1.1"],
    acceptance_criteria: ["All images have alt text.", "axe rule image-alt passes."],
    environment: "Desktop Chrome; axe-core automated scan",
    wcag_reference: "https://www.w3.org/WAI/WCAG22/Understanding/non-text-content.html",
    assignee: "",
    milestone: "",
  },
  source: "template",
};

function mockApi(page) {
  page.route("**/api/config", (route) =>
    route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ default_repo: "example/repo", github_configured: true, ai_provider: "template", ai_configured: true, live_scan_enabled: false }) }),
  );
  page.route("**/api/scan", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(SCAN_RESPONSE) }));
  page.route("**/api/search-issues", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(SEARCH_RESPONSE) }));
  page.route("**/api/generate-issue", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(GENERATED_RESPONSE) }));
}

async function expectNoSeriousViolations(page) {
  const results = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
    .analyze();
  const serious = results.violations.filter((v) => ["serious", "critical"].includes(v.impact ?? ""));
  const summary = serious.map((v) => `  [${v.impact}] ${v.id}: ${v.help} (${v.nodes.length} node(s))`).join("\n");
  expect(serious, `Serious/critical axe violations:\n${summary}`).toHaveLength(0);
}

async function gotoScanResults(page) {
  await page.goto("/app");
  await page.getByLabel("Page URL to audit").fill("https://example.com");
  await page.getByRole("button", { name: /run accessibility scan/i }).click();
  await expect(page.getByText("Images must have alternative text")).toBeVisible();
}
async function gotoCompare(page) {
  await gotoScanResults(page);
  await page.getByRole("option", { name: /images must have alternative text/i }).click();
  await page.getByRole("button", { name: /find similar github issues/i }).click();
  await expect(page.getByRole("heading", { name: /similar github issues/i })).toBeVisible();
}
async function gotoReview(page) {
  await gotoCompare(page);
  await page.getByRole("button", { name: /create from scratch/i }).click();
  await page.getByRole("button", { name: /generate github issue/i }).click();
  await page.getByRole("button", { name: /review and log/i }).click();
  await expect(page.getByRole("heading", { name: /ready to log/i })).toBeVisible();
}

test.beforeEach(({ page }) => mockApi(page));

test("scan results step has no serious/critical violations", async ({ page }) => {
  await gotoScanResults(page);
  await expectNoSeriousViolations(page);
});

test("compare step has no serious/critical violations", async ({ page }) => {
  await gotoCompare(page);
  await expectNoSeriousViolations(page);
  // and with the collapsible current-finding closed
  await page.locator(".finding > summary").click();
  await expectNoSeriousViolations(page);
});

test("generate step has no serious/critical violations", async ({ page }) => {
  await gotoCompare(page);
  await page.getByRole("button", { name: /create from scratch/i }).click();
  await page.getByRole("button", { name: /generate github issue/i }).click();
  await expect(page.getByRole("textbox", { name: /title/i })).toBeVisible();
  await expectNoSeriousViolations(page);
});

test("review step has no serious/critical violations", async ({ page }) => {
  await gotoReview(page);
  await expectNoSeriousViolations(page);
});

test("compare step on mobile (390px) has no serious/critical violations", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await gotoCompare(page);
  await expectNoSeriousViolations(page);
});
