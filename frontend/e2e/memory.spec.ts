import { test, expect } from "@playwright/test";
import { returning } from "./helpers";

test("a memory can be opened and forgotten, with a receipt", async ({ page }) => {
  await returning(page);
  await page.goto("/memory");
  const entry = page.locator("main ul button").first();
  await entry.waitFor({ timeout: 8_000 }).catch(() => undefined);
  test.skip((await entry.count()) === 0, "no memories stored yet");
  await entry.click();
  const sheet = page.getByRole("dialog", { name: "A memory" });
  await expect(sheet).toBeVisible();
  await sheet.getByRole("button", { name: "Ask Nova to forget this" }).click();
  await expect(sheet.getByText("Forget this for good?")).toBeVisible();
  await sheet.getByRole("button", { name: "Yes, forget it" }).click();
  await expect(page.getByRole("dialog", { name: "Forgotten" })).toBeVisible();
  await expect(page.getByLabel("Receipt number")).not.toBeEmpty();
});
