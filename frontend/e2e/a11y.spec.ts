import AxeBuilder from "@axe-core/playwright";
import { test, expect } from "@playwright/test";

/** Every page must pass automated accessibility checks (contrast, names, landmarks, headings) in
 * each light the room can be in. The light is forced with the "nova-light-mode" setting, which
 * accepts day or night, so dawn and dusk are forced by stamping the attribute directly. */
const ROUTES = ["/", "/welcome", "/today", "/story", "/keepsakes", "/memory", "/people", "/goals", "/errands", "/us", "/care", "/privacy", "/upkeep"];
const LIGHTS = ["day", "dawn", "dusk", "night"] as const;

for (const light of LIGHTS) {
  for (const route of ROUTES) {
    test(`${route} is accessible in ${light} light`, async ({ page }) => {
      await page.addInitScript((l) => {
        localStorage.setItem("nova-welcomed", "1");
        localStorage.setItem("nova-light-mode", l === "night" ? "night" : "day");
        window.addEventListener("DOMContentLoaded", () => document.documentElement.setAttribute("data-light", l));
      }, light);
      await page.goto(route);
      await page.locator("h1").first().waitFor();
      await page.evaluate((l) => document.documentElement.setAttribute("data-light", l), light);
      await page.waitForTimeout(1200);
      const results = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21aa"]).analyze();
      const serious = results.violations.filter((v) => v.impact === "serious" || v.impact === "critical");
      expect(serious.map((v) => `${v.id}: ${v.help} (${v.nodes.length} nodes)`)).toEqual([]);
    });
  }
}
