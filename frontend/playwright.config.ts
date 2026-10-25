import { defineConfig, devices } from "@playwright/test";

/**
 * End-to-end tests against the real stack: the Next app on :3000 talking to the FastAPI backend on
 * :8000. A turn on a local model can be slow, so timeouts are generous. Set PW_CHROMIUM to use a
 * specific Chromium binary (e.g. when the installed Playwright and browser versions differ).
 */
export default defineConfig({
  testDir: "./e2e",
  timeout: 150_000,
  expect: { timeout: 20_000 },
  fullyParallel: false,
  workers: 1,
  reporter: "line",
  use: { baseURL: "http://localhost:3000", trace: "off" },
  projects: [
    {
      name: "chromium",
      use: {
        ...devices["Desktop Chrome"],
        launchOptions: process.env.PW_CHROMIUM
          ? { executablePath: process.env.PW_CHROMIUM, args: ["--no-sandbox"] }
          : {},
      },
    },
  ],
  webServer: {
    command: "npm run dev",
    url: "http://localhost:3000",
    reuseExistingServer: true,
    timeout: 60_000,
  },
});
