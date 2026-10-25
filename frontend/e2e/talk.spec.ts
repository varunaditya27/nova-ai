import { test, expect } from "@playwright/test";
import { returning } from "./helpers";

test("a turn streams in, and a reply can be saved and found in Keepsakes", async ({ page }) => {
  await returning(page);
  await page.goto("/");

  const note = `Remember this one ${Date.now()}`;
  const box = page.getByLabel("Say something to Nova");
  await box.fill(note);
  await box.press("Enter");

  // Your words appear at once; Nova's reply follows and is persisted into the thread.
  await expect(page.getByText(note).first()).toBeVisible();
  await expect(page.getByText("Nova is thinking…")).toBeHidden({ timeout: 120_000 });

  // The newest Nova reply: hover to reveal its actions, then save it under "Advice".
  const replies = page.locator("article").filter({ hasText: "Nova" });
  const latest = replies.last();
  await latest.hover();
  await latest.getByRole("button", { name: "Save", exact: true }).click();
  await latest.getByRole("button", { name: "Advice" }).click();
  await expect(page.getByText("Saved to Keepsakes")).toBeVisible();

  await page.goto("/keepsakes");
  await page.getByRole("tab", { name: "Saved messages" }).click();
  await expect(page.getByRole("heading", { name: "Advice" })).toBeVisible();
});
