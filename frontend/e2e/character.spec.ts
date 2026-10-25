import { test, expect } from "@playwright/test";
import { returning } from "./helpers";

test.beforeEach(async ({ page }) => {
  await returning(page);
});

const PAGES = [
  "/today",
  "/goals",
  "/memory",
  "/people",
  "/story",
  "/keepsakes",
  "/errands",
  "/care",
  "/us",
  "/upkeep",
  "/privacy",
];

for (const path of PAGES) {
  test(`${path} has Nova's own voice in the margin`, async ({ page }) => {
    await page.goto(path);
    await expect(page.locator(".hand").first()).toBeVisible();
    await expect(page.locator("[data-mood]").first()).toBeAttached();
  });
}

test("a page that is not there is lost, and says so in plain words", async ({ page }) => {
  await page.goto("/nowhere-at-all");
  await expect(page.locator("[data-mood='lost']")).toBeAttached();
  await expect(page.getByRole("heading", { name: "I can’t find that page." })).toBeVisible();
});

test("the sidebar stamp falls asleep when you stop, and wakes when you return", async ({ page }) => {
  // Reduced motion keeps the fake-clock run cheap: the mood is carried by the attribute either way.
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.clock.install();
  await page.goto("/today");
  await expect(page.locator("aside [data-mood]").first()).toHaveAttribute("data-mood", "calm");
  // Pretend ninety quiet seconds have passed.
  await page.clock.runFor(100_000);
  await expect(page.locator("aside [data-mood]").first()).toHaveAttribute("data-mood", "sleepy");
  await page.mouse.move(400, 400);
  await expect(page.locator("aside [data-mood]").first()).toHaveAttribute("data-mood", /startled|calm/);
});
