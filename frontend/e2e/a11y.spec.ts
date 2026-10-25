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
      await page.addInitScript(() => sessionStorage.setItem("nova-intro", "1"));
      await page.goto(route);
      await page.locator("h1").first().waitFor();
      await page.evaluate((l) => document.documentElement.setAttribute("data-light", l), light);
      await page.waitForTimeout(route === "/welcome" ? 4500 : 1200); // the landing page's opening shot takes a few seconds to settle
      const scan = async (exclude: string[] = []) => {
        let axe = new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21aa"]);
        for (const e of exclude) axe = axe.exclude(e);
        const results = await axe.analyze();
        const serious = results.violations.filter((v) => v.impact === "serious" || v.impact === "critical");
        expect(serious.map((v) => `${v.id}: ${v.help} (${v.nodes.length} nodes)`)).toEqual([]);
      };
      if (route !== "/welcome") return scan();
      // The landing page is paced by scrolling: headings read in word by word, and the opening copy
      // fades as you leave it. Check each in the position where it is meant to be read.
      await scan(["[data-scrub]"]);
      await page.evaluate(() => window.scrollTo(0, document.documentElement.scrollHeight));
      await page.waitForTimeout(1500);
      await scan(["[data-hero-copy]"]);
    });
  }
}
