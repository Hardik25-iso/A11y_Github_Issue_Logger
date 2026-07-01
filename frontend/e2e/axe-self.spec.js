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

const VIEWPORTS = [
  { name: "desktop", size: { width: 1280, height: 900 } },
  { name: "mobile 390px", size: { width: 390, height: 844 } },
];

for (const route of ROUTES) {
  for (const vp of VIEWPORTS) {
    test(`${route.name} @ ${vp.name} has no serious or critical axe violations`, async ({ page }) => {
      await page.setViewportSize(vp.size);
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
        throw new Error(`Found ${serious.length} serious/critical axe violation(s) on ${route.path} @ ${vp.name}:\n${summary}`);
      }

      expect(serious).toHaveLength(0);
    });
  }
}
