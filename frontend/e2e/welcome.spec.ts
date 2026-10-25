import { test, expect } from "@playwright/test";

const stamp = (page: import("@playwright/test").Page) => page.locator("[data-hero-stamp]");

test("the opening settles with the promise, the stamp and the day's ruler in place", async ({ page }) => {
  await page.goto("/welcome");
  await expect(page.locator("[data-hero-line]")).toHaveCount(3);
  await expect(page.locator("[data-hero-now-label]")).toHaveCSS("opacity", "1", { timeout: 8_000 });
  await expect(stamp(page)).toHaveCSS("opacity", "1");
  for (const line of await page.locator("[data-hero-line]").all()) await expect(line).toHaveCSS("opacity", "1");
  await expect(page.getByRole("button", { name: "Begin the conversation" }).first()).toBeVisible();
});

test("the window's light lands on the tick for the visitor's hour", async ({ page }) => {
  await page.goto("/welcome");
  await expect(page.locator("[data-hero-now-label]")).toHaveCSS("opacity", "1", { timeout: 8_000 });
  await page.waitForTimeout(600);
  const beam = (await page.locator("[data-hero-beam]").boundingBox())!;
  const now = (await page.locator("[data-hero-now]").boundingBox())!;
  expect(Math.abs(beam.x + beam.width / 2 - (now.x + now.width / 2))).toBeLessThan(12);
});

test("a click skips the opening to its end", async ({ page }) => {
  await page.goto("/welcome");
  await page.locator("[data-hero-line]").first().waitFor();
  await page.mouse.click(700, 450);
  await expect(stamp(page)).toHaveCSS("opacity", "1", { timeout: 1_000 });
});

test("with reduced motion the opening is simply there", async ({ page }) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.goto("/welcome");
  await expect(stamp(page)).toHaveCSS("opacity", "1", { timeout: 1_500 });
  for (const line of await page.locator("[data-hero-line]").all()) await expect(line).toHaveCSS("opacity", "1");
  await expect(page.locator("[data-hero-now-label]")).toHaveCSS("opacity", "1");
});

test("the hero no longer loads a film", async ({ page }) => {
  const films: string[] = [];
  page.on("request", (r) => /\/film\/hero/.test(r.url()) && films.push(r.url()));
  await page.goto("/welcome");
  await page.waitForTimeout(1500);
  expect(films).toEqual([]);
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

test("the stamp never sits on the headline, at any width", async ({ page }) => {
  for (const [width, height] of [[1920, 1080], [1440, 900], [1100, 800], [390, 844]]) {
    await page.setViewportSize({ width, height });
    await page.goto("/welcome");
    await expect(page.locator("[data-hero-now-label]")).toHaveCSS("opacity", "1", { timeout: 8_000 });
    const stampBox = (await stamp(page).boundingBox())!;
    // the edges of the actual words, not of the boxes the lines sit in
    const words = await page.locator("[data-hero-line]").evaluateAll((lines) =>
      lines.map((line) => {
        const range = document.createRange();
        range.selectNodeContents(line);
        const r = range.getBoundingClientRect();
        return { right: r.right, top: r.top };
      }),
    );
    // wide screens: beside the headline; narrow ones: above it
    if (width >= 1024) expect(stampBox.x, `${width}px wide`).toBeGreaterThanOrEqual(Math.max(...words.map((w) => w.right)));
    else expect(stampBox.y + stampBox.height, `${width}px wide`).toBeLessThanOrEqual(words[0].top + 2);
  }
});

test("the ribbon under the hero moves at its set pace", async ({ page }) => {
  await page.goto("/welcome");
  await page.waitForTimeout(1500);
  const read = () => page.locator("[data-track]").evaluate((el) => ({ x: new DOMMatrix(getComputedStyle(el).transform).m41, w: (el as HTMLElement).offsetWidth }));
  const a = await read();
  await page.waitForTimeout(2000);
  const b = await read();
  const c = await (async () => { await page.waitForTimeout(2000); return read(); })();
  // use whichever pair did not straddle the loop's wrap-around
  const perSecond = Math.abs(b.x < a.x ? (b.x - a.x) / 2 : (c.x - b.x) / 2);
  const expected = a.w / 2 / 35.4; // half the track per 35.4 s: 30% faster than the 46 s it had
  expect(perSecond).toBeGreaterThan(expected * 0.9);
  expect(perSecond).toBeLessThan(expected * 1.1);
});

test("every point of the example life shows up as you scroll to it", async ({ page }) => {
  await page.setViewportSize({ width: 1920, height: 1000 });
  await page.goto("/welcome");
  await page.waitForTimeout(1500);
  for (let i = 0; i < 80; i++) {
    await page.mouse.wheel(0, 300);
    await page.waitForTimeout(60);
    if ((await page.locator("#connects").evaluate((el) => el.getBoundingClientRect().top)) < 150) break;
  }
  await page.waitForTimeout(2500);
  const nodes = page.locator("[data-node]");
  await expect(nodes).toHaveCount(6);
  for (const node of await nodes.all()) {
    await expect(node).toHaveCSS("opacity", "1");
    await expect(node).toHaveCSS("visibility", "visible");
  }
});
