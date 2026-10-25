import { test, expect } from "@playwright/test";

test("the welcome page explains Nova and begins the conversation", async ({ page }) => {
  await page.goto("/welcome");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("A companion that remembers you.");
  await expect(page.getByRole("heading", { name: "What Nova is not" })).toBeVisible();
  await page.getByRole("button", { name: "Begin the conversation" }).first().click();
  await expect(page).toHaveURL("/");
  expect(await page.evaluate(() => localStorage.getItem("nova-welcomed"))).toBe("1");
});
