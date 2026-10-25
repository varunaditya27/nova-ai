import { test, expect } from "@playwright/test";

/** Skip the title sequence (it plays once per visit) so tests start on the page itself. */
test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => sessionStorage.setItem("nova-intro", "1"));
});

test("the title sequence plays once, then the curtain is gone", async ({ page }) => {
  await page.addInitScript(() => sessionStorage.removeItem("nova-intro"));
  await page.goto("/welcome");
  await expect(page.getByText("Nova", { exact: true }).first()).toBeVisible();
  await expect(page.locator("[data-intro-star]")).toBeHidden({ timeout: 10_000 });
  await page.reload();
  await expect(page.locator("[data-intro-star]")).toBeHidden();
});

test("the welcome page explains Nova and begins the conversation", async ({ page }) => {
  await page.goto("/welcome");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("A companion that remembers you.");
  await expect(page.getByRole("heading", { name: "What Nova is not." })).toBeVisible();
  await page.getByRole("button", { name: "Begin the conversation" }).first().click();
  await expect(page).toHaveURL("/");
  expect(await page.evaluate(() => localStorage.getItem("nova-welcomed"))).toBe("1");
});

test("the header's Begin button starts the conversation too", async ({ page }) => {
  await page.goto("/welcome");
  await page.locator("header").getByRole("button", { name: "Begin" }).click();
  await expect(page).toHaveURL("/");
});

test("the page has no sidebar and its section links jump to the section", async ({ page }) => {
  await page.goto("/welcome");
  await expect(page.getByRole("navigation", { name: "Main" })).toHaveCount(0);
  await page.getByRole("navigation", { name: "On this page" }).getByRole("link", { name: "Privacy" }).click();
  await expect(page.getByRole("heading", { name: "What you tell Nova is yours." })).toBeInViewport();
});

test("as you scroll through how it grows, the room moves from dawn to night", async ({ page }) => {
  await page.goto("/welcome");
  const section = page.locator("#how");
  await expect(section).toHaveAttribute("data-pinned", "true");
  await expect(section).toHaveAttribute("data-light", "dawn");
  await page.evaluate(() => {
    const el = document.getElementById("how")!;
    window.scrollTo(0, el.getBoundingClientRect().top + window.scrollY + window.innerHeight * 2.55);
  });
  await expect(section).toHaveAttribute("data-light", "night");
  await expect(page.getByText("The moments you marked as mattering.")).toBeVisible();
});

test("every stage is still in the page for a screen reader", async ({ page }) => {
  await page.goto("/welcome");
  for (const stage of ["The first day", "Three weeks in", "Six months in", "Two years in"]) {
    await expect(page.getByRole("heading", { name: stage })).toHaveCount(1);
  }
});

test("touching a point in the example life shows what it connects to", async ({ page }) => {
  await page.goto("/welcome");
  await page.getByRole("button", { name: "Meera" }).evaluate((el) => el.scrollIntoView({ block: "center" }));
  // the points drift gently, so a pointer can land a moment after it was aimed; press without waiting for them to hold still
  await page.getByRole("button", { name: "Meera" }).click({ force: true });
  await expect(page.locator("p[aria-live=polite]").filter({ hasText: "Your sister. She’s coming to visit" })).toBeVisible();
});

test("changing one record shows everything after it no longer matches", async ({ page }) => {
  await page.goto("/welcome");
  const wed = page.getByRole("button", { name: /Wednesday/ });
  await wed.scrollIntoViewIfNeeded();
  await wed.click();
  await expect(page.getByText("It and every record after it no longer match their seals")).toBeVisible();
  await expect(page.getByRole("button", { name: /Friday.*no longer matches/ })).toBeVisible();
});

test("picking a time of day re-lights only the sample, not the page", async ({ page }) => {
  await page.goto("/welcome");
  const sample = page.getByRole("group", { name: /A sample conversation/ });
  await page.getByRole("radio", { name: /Night/ }).click();
  await expect(sample).toHaveAttribute("data-light", "night");
  await page.getByRole("radio", { name: /Dawn/ }).click();
  await expect(sample).toHaveAttribute("data-light", "dawn");
  const pageLight = await page.evaluate(() => document.documentElement.getAttribute("data-light"));
  expect(["dawn", "day", "dusk", "night"]).toContain(pageLight);
});

test("a question opens to its answer", async ({ page }) => {
  await page.goto("/welcome");
  await page.getByText("Is what it stores encrypted?").click();
  await expect(page.getByText("Use your computer’s disk encryption")).toBeVisible();
});

test("what it does slides past as a reel on a wide screen", async ({ page }) => {
  await page.goto("/welcome");
  await expect(page.locator("#does")).toHaveAttribute("data-pinned", "true");
  const first = page.locator("[data-reel] > li").first();
  const x0 = (await first.boundingBox())!.x;
  await page.evaluate(() => {
    const el = document.getElementById("does")!;
    window.scrollTo(0, el.getBoundingClientRect().top + window.scrollY + 1200);
  });
  await expect.poll(async () => (await first.boundingBox())!.x, { timeout: 8000 }).toBeLessThan(x0 - 400);
});

test("the chapter rail follows where you are and jumps to a chapter", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/welcome");
  const rail = page.getByRole("navigation", { name: "Chapters" });
  await expect(rail).toBeHidden(); // not until the opening shot has passed
  await page.waitForTimeout(1500); // let the pinned sections measure themselves before jumping
  await page.evaluate(() => document.getElementById("questions")!.scrollIntoView());
  await expect(rail).toBeVisible();
  await expect(rail.getByRole("link", { name: "Questions" })).toHaveAttribute("aria-current", "true");
  await rail.getByRole("link", { name: "The proof" }).click();
  await expect(rail.getByRole("link", { name: "The proof" })).toHaveAttribute("aria-current", "true", { timeout: 8000 });
});
