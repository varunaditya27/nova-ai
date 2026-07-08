import { test, expect } from "@playwright/test";

test("the spine: threshold → desk → chat → send streams a reply", async ({ page }) => {
  // Threshold
  await page.goto("/");
  await expect(page.getByText("relationship, not a tool")).toBeVisible();
  await page.getByRole("link", { name: "Begin" }).click();

  // Desk
  await expect(page).toHaveURL(/\/desk/);
  const toChat = page.getByRole("link", { name: /Continue|Say the first thing/ });
  await expect(toChat).toBeVisible();
  await toChat.click();

  // Chat
  await expect(page).toHaveURL(/\/chat/);
  const composer = page.getByPlaceholder("Say something to Nova…");
  await expect(composer).toBeVisible();

  // Send a turn.
  await composer.fill("hey");
  await composer.press("Enter");

  // The stream connects fast (meta before the LLM runs) → the thinking pause shows...
  await expect(page.getByLabel("Nova is thinking")).toBeVisible({ timeout: 20_000 });
  // ...then resolves once the (slow, local) reply lands, proving the full turn completed.
  await expect(page.getByLabel("Nova is thinking")).toBeHidden({ timeout: 130_000 });
});
