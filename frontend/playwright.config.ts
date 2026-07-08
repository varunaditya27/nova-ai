import { defineConfig, devices } from "@playwright/test";

/**
 * One end-to-end smoke over the spine. Turns run on a local CPU model (~60s each), so the test
 * timeout is generous. Reuses an already-running dev server on :3000, and expects the FastAPI
 * backend live on :8000.
 */
export default defineConfig({
  testDir: "./e2e",
  timeout: 150_000,
  expect: { timeout: 15_000 },
  fullyParallel: false,
  reporter: "line",
  use: { baseURL: "http://localhost:3000", trace: "off" },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: {
    command: "npm run dev",
    url: "http://localhost:3000",
    reuseExistingServer: true,
    timeout: 60_000,
  },
});
