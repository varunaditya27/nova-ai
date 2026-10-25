import { test, expect } from "@playwright/test";
import { returning } from "./helpers";

const ROUTES = ["/", "/today", "/story", "/keepsakes", "/memory", "/people", "/goals", "/errands", "/us", "/care", "/privacy", "/upkeep"];

for (const route of ROUTES) {
  test(`${route} loads without errors and says what it is`, async ({ page }) => {
    await returning(page);
    const problems: string[] = [];
    page.on("pageerror", (e) => problems.push(e.message));
    await page.goto(route);
    await expect(page.locator("h1").first()).toBeVisible();
    await page.waitForTimeout(800);
    expect(problems).toEqual([]);
  });
}
