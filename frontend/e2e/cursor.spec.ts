import { test, expect } from "@playwright/test";
import { returning } from "./helpers";

test.beforeEach(async ({ page }) => {
  await returning(page);
});

/** Hover the middle of an element until the cursor (which wakes after hydration) reports the expected mode. */
async function hoverUntil(page: import("@playwright/test").Page, selector: string, mode: string) {
  await expect(async () => {
    const box = await page.locator(selector).first().boundingBox();
    if (!box) throw new Error(`${selector} not visible`);
    await page.mouse.move(box.x + box.width / 2 + Math.random() * 4, box.y + box.height / 2, { steps: 3 });
    await expect(page.locator("[data-nova-cursor]")).toHaveAttribute("data-mode", mode, { timeout: 500 });
  }).toPass();
}

test("the pen cursor changes with what is under it", async ({ page }) => {
  await page.goto("/privacy");
  await hoverUntil(page, "nav a", "press");
  await hoverUntil(page, "main p", "read");
});

test("the cursor can be switched off and the standard one returns", async ({ page }) => {
  await page.goto("/privacy");
  // The cursor wakes on the first pointer move after the page has hydrated.
  await expect(async () => {
    await page.mouse.move(300 + Math.random() * 50, 300, { steps: 2 });
    await expect(page.locator("html")).toHaveClass(/nova-cursor/, { timeout: 500 });
  }).toPass();
  await page.getByRole("button", { name: /pen cursor is on/i }).click();
  await expect(page.locator("html")).not.toHaveClass(/nova-cursor/);
  await expect(page.locator("[data-nova-cursor]")).toHaveCount(0);
});
