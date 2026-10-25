import { test, expect, type Page } from "@playwright/test";
import { returning } from "./helpers";

test.beforeEach(async ({ page }) => {
  await returning(page);
  await page.goto("/privacy");
});

const cursorOf = (page: Page, selector: string) =>
  page.locator(selector).first().evaluate((el) => getComputedStyle(el).cursor);

/** Things the app doesn't have on every page, added so each state can be read in isolation. */
const plant = (page: Page, html: string) =>
  page.evaluate(
    (h) =>
      document.body.insertAdjacentHTML(
        "beforeend",
        `<div style="position:fixed;top:30vh;right:24px;z-index:9999;display:flex;flex-direction:column;gap:8px">${h}</div>`,
      ),
    html,
  );

test("the pointer is drawn, and changes with what is under it", async ({ page }) => {
  await plant(page, '<button id="t-press">Press</button><button id="t-off" disabled>Off</button><textarea id="t-field"></textarea>');
  const rest = await cursorOf(page, "main p");
  const press = await cursorOf(page, "#t-press");
  const blocked = await cursorOf(page, "#t-off");
  for (const c of [rest, press, blocked]) expect(c).toContain("data:image/svg+xml");
  expect(new Set([rest, press, blocked]).size).toBe(3);
  expect(await cursorOf(page, "#t-field")).toBe("text");
});

test("while Nova writes, resting things show the busy pointer but pressable things stay pressable", async ({ page }) => {
  await plant(page, '<button id="t-press">Press</button>');
  const rest = await cursorOf(page, "main p");
  const press = await cursorOf(page, "#t-press");
  await page.evaluate(() => (document.documentElement.dataset.busy = "true"));
  expect(await cursorOf(page, "main p")).not.toBe(rest);
  expect(await cursorOf(page, "#t-press")).toBe(press);
});

test("night uses the night drawings, even inside a page that is day", async ({ page }) => {
  // the app's own setting, so the page is day whatever the clock says
  await page.addInitScript(() => localStorage.setItem("nova-light-mode", "day"));
  await page.goto("/privacy");
  await expect(page.locator("html")).toHaveAttribute("data-light", "day");
  await plant(page, '<p id="t-day">day</p><section data-light="night"><p id="t-night">night</p></section>');
  expect(await cursorOf(page, "#t-night")).not.toBe(await cursorOf(page, "#t-day"));
});

test("the corner of a button opens on hover and snaps flat on press, but a card's does not", async ({ page }) => {
  await plant(page, '<button id="t-fold" class="fold-sm">Fold</button><div id="t-card" class="fold-sm">Card</div>');
  const corner = (sel: string) => page.locator(sel).evaluate((el) => getComputedStyle(el).getPropertyValue("--c").trim());
  expect(await corner("#t-fold")).toBe("9px");
  await page.locator("#t-fold").hover();
  await expect.poll(() => corner("#t-fold")).toBe("13px");
  await page.mouse.down();
  await expect.poll(() => corner("#t-fold")).toBe("0px");
  await page.mouse.up();
  await page.locator("#t-card").hover();
  expect(await corner("#t-card")).toBe("9px");
});

test("the sidebar offers a room light but no pointer or sound settings", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/today");
  await expect(page.getByRole("radiogroup", { name: "Room light" })).toBeVisible();
  await expect(page.getByRole("button", { name: /pointer|soft sounds/i })).toHaveCount(0);
});
