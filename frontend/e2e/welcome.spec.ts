import { test, expect } from "@playwright/test";

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

test("the growth example changes as time passes", async ({ page }) => {
  await page.goto("/welcome");
  await page.getByRole("tab", { name: "First day" }).click();
  await expect(page.getByText("Nova listens more than it talks.")).toBeVisible();
  await page.getByRole("tab", { name: "Two years" }).click();
  await expect(page.getByText("The moments you marked as mattering.")).toBeVisible();
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
