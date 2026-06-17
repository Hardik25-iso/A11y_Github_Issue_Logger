import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  workers: 1,
  reporter: process.env.CI ? "github" : "list",
  use: {
    baseURL: "http://localhost:5173",
    trace: "on-first-retry",
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
      testIgnore: ["**/axe-self.spec.js"],
    },
    {
      name: "axe",
      use: { ...devices["Desktop Chrome"], baseURL: "http://localhost:4173" },
      testMatch: ["**/axe-self.spec.js"],
    },
  ],
  webServer: [
    {
      command: "npm run dev",
      url: "http://localhost:5173",
      reuseExistingServer: !process.env.CI,
      timeout: 30_000,
    },
    {
      command: "npm run preview",
      url: "http://localhost:4173",
      reuseExistingServer: !process.env.CI,
      timeout: 30_000,
    },
  ],
});
