import { test, expect } from "@playwright/test";
import { returning } from "./helpers";

test("Ctrl+K jumps to any page by name", async ({ page }) => {
  await returning(page);
  await page.goto("/today");
  await page.keyboard.press("Control+k");
  await expect(page.getByRole("dialog", { name: "Jump to" })).toBeVisible();
  await page.keyboard.type("goals");
  await page.keyboard.press("Enter");
  await expect(page).toHaveURL(/\/goals$/);
  await expect(page.getByRole("heading", { level: 1, name: "Goals" })).toBeVisible();
});

test("on a phone, four tabs plus More reach everything", async ({ page }) => {
  await returning(page);
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/today");
  const nav = page.getByRole("navigation", { name: "Main" });
  await expect(nav.getByRole("link", { name: "Goals" })).toBeVisible();
  await nav.getByRole("button", { name: "More" }).click();
  await page.getByRole("link", { name: /^Privacy/ }).click();
  await expect(page).toHaveURL(/\/privacy$/);
});
