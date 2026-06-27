import { expect, test } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

/**
 * Self-audit: the product's top-level routes must pass their own accessibility
 * bar. Fails CI on any serious or critical axe violation.
 * (Inner wizard states are covered in axe-steps.spec.js.)
 */
const ROUTES = [
  { name: "landing page (/)", path: "/" },
  { name: "workspace (/app)", path: "/app" },
];

for (const route of ROUTES) {
  test(`${route.name} has no serious or critical axe violations`, async ({ page }) => {
    await page.goto(route.path);
    await page.waitForLoadState("networkidle");

    const results = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
      .analyze();

    const serious = results.violations.filter((v) =>
      ["serious", "critical"].includes(v.impact ?? ""),
    );

    if (serious.length > 0) {
      const summary = serious
        .map((v) => `  [${v.impact}] ${v.id}: ${v.help} (${v.nodes.length} node(s))`)
        .join("\n");
      throw new Error(`Found ${serious.length} serious/critical axe violation(s) on ${route.path}:\n${summary}`);
    }

    expect(serious).toHaveLength(0);
  });
}
