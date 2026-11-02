import { expect, test } from "@playwright/test";

test("live readiness and all sidebar destinations", async ({ page }) => {
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "Chat", exact: true }),
  ).toBeVisible();
  await expect(page.locator(".dependency .ready")).toHaveCount(4);
  expect((await page.request.get("/docs")).status()).toBe(200);
  const schema = await page.request.get("/openapi.json");
  expect((await schema.json()).info.title).toBe("Memora AI API");
  for (const name of [
    "Knowledge Base",
    "Meetings",
    "Memory",
    "Tasks & Actions",
    "Presentations",
    "Settings",
  ]) {
    await page.getByRole("button", { name, exact: true }).click();
    await expect(
      page.getByRole("heading", {
        name: name === "Settings" ? "Workspace settings" : name,
        exact: true,
      }),
    ).toBeVisible();
  }
  await page.getByRole("button", { name: "Refresh service health" }).click();
  await expect(page.locator(".dependency .ready")).toHaveCount(4);
  expect(errors).toEqual([]);
  await page.screenshot({
    path: "test-results/phase-0-desktop.png",
    fullPage: true,
  });
});

test("health error is visible and retry recovers against real API", async ({
  page,
}) => {
  await page.route("**/api/health", (route) =>
    route.fulfill({
      status: 503,
      contentType: "application/json",
      body: JSON.stringify({
        code: "DEPENDENCIES_UNAVAILABLE",
        message: "Test dependency unavailable.",
        request_id: "browser-test",
      }),
    }),
  );
  await page.goto("/");
  await expect(page.getByRole("alert")).toContainText(
    "Test dependency unavailable.",
  );
  await page.unroute("**/api/health");
  await page.getByRole("button", { name: "Try again" }).click();
  await expect(page.locator(".dependency .ready")).toHaveCount(4);
});

test("mobile navigation fits viewport", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  await page.getByRole("button", { name: "Open navigation" }).click();
  await page
    .getByRole("button", { name: "Knowledge Base", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Knowledge Base", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Open navigation" }),
  ).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
  await page.screenshot({
    path: "test-results/phase-0-mobile.png",
    fullPage: true,
  });
});
