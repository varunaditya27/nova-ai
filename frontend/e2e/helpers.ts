import type { Page } from "@playwright/test";

/** Behave like a returning visitor: skip the first-run welcome redirect. */
export async function returning(page: Page) {
  await page.addInitScript(() => localStorage.setItem("nova-welcomed", "1"));
}
