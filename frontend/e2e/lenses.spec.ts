import { test, expect } from "@playwright/test";

test("lenses: Desk → Lenses popover → Life timeline", async ({ page }) => {
  await page.goto("/desk");
  await page.getByRole("button", { name: "Lenses" }).click();
  await page.getByRole("link", { name: "Life", exact: true }).click();
  await expect(page).toHaveURL(/\/life/);
  await expect(page.getByText("Your life together")).toBeVisible();
  // sub-nav across the three life lenses
  await page.getByRole("link", { name: "Museum" }).click();
  await expect(page).toHaveURL(/\/life\/museum/);
});
