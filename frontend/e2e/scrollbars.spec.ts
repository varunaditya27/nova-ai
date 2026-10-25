import { test, expect } from "@playwright/test";
import { returning } from "./helpers";

// Playwright hides scrollbars by default, which would hide exactly what these tests are about.
test.use({
  launchOptions: {
    ignoreDefaultArgs: ["--hide-scrollbars"],
    ...(process.env.PW_CHROMIUM && { executablePath: process.env.PW_CHROMIUM, args: ["--no-sandbox"] }),
  },
});

test.beforeEach(async ({ page }) => {
  await returning(page);
});

test("/welcome never scrolls sideways, even after the page scrolls", async ({ page }) => {
  await page.goto("/welcome");
  await page.waitForTimeout(3500);
  for (const step of [0, 1500, 1500, 1500]) {
    await page.mouse.wheel(0, step);
    await page.waitForTimeout(800);
    const { scrollWidth, clientWidth } = await page.evaluate(() => ({
      scrollWidth: document.documentElement.scrollWidth,
      clientWidth: document.documentElement.clientWidth,
    }));
    expect(scrollWidth).toBeLessThanOrEqual(clientWidth);
  }
});

test("the chat box shows no scrollbar until its text outgrows it", async ({ page }) => {
  await page.goto("/");
  const say = page.locator("#say");
  const overflowY = () => say.evaluate((el) => getComputedStyle(el).overflowY);
  expect(await overflowY()).toBe("hidden");
  await say.fill("one line");
  expect(await overflowY()).toBe("hidden");
  await say.fill(Array.from({ length: 30 }, (_, i) => `line ${i}`).join("\n"));
  expect(await overflowY()).toBe("auto");
});

test("scrollbars are Nova's ruler, not the browser's grey bar", async ({ page }) => {
  await page.goto("/privacy");
  const width = await page.evaluate(() => getComputedStyle(document.documentElement, "::-webkit-scrollbar").width);
  expect(width).toBe("12px");
});

test("a tab strip has no scrollbar of its own", async ({ page }) => {
  await page.goto("/keepsakes");
  const strip = page.getByRole("tablist").first();
  await expect(strip).toBeVisible();
  const { scrollHeight, clientHeight, bar } = await strip.evaluate((el) => ({
    scrollHeight: el.scrollHeight,
    clientHeight: el.clientHeight,
    bar: (el as HTMLElement).offsetWidth - el.clientWidth,
  }));
  expect(scrollHeight).toBe(clientHeight);
  expect(bar).toBe(0);
});

test("the sidebar fits an ordinary 900px window without scrolling", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/today");
  const side = page.locator("aside").first();
  await expect(side).toBeVisible();
  const { scrollHeight, clientHeight } = await side.evaluate((el) => ({ scrollHeight: el.scrollHeight, clientHeight: el.clientHeight }));
  expect(scrollHeight).toBeLessThanOrEqual(clientHeight);
});
