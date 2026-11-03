import { expect, test } from "@playwright/test";

test("missing key presents configuration and disables sending", async ({
  page,
}) => {
  // Keyless status is an explicit browser test fixture, never a product provider.
  await page.route("**/api/chat/config", (route) =>
    route.fulfill({
      json: {
        configured: false,
        missing: ["LLM_API_KEY"],
        provider: "openai_compatible",
        model: "",
        message: "Configure backend .env: LLM_API_KEY",
      },
    }),
  );
  await page.goto("/");
  await expect(
    page.getByText("Chat configuration required / 请配置模型"),
  ).toBeVisible();
  await page.getByLabel("Message", { exact: true }).fill("Hello");
  await expect(
    page.getByRole("button", { name: "Send", exact: true }),
  ).toBeDisabled();
  await expect(page.getByLabel("assistant message")).toHaveCount(0);
});

test("streams, reloads, switches and separates conversations", async ({
  page,
}) => {
  test.skip(
    process.env.MEMORA_CHAT_TEST !== "1",
    "Requires isolated test-only upstream",
  );
  const prompt = `browser-${Date.now()}`;
  await page.goto("/");
  await page.getByLabel("Message", { exact: true }).fill(prompt);
  await page.getByRole("button", { name: "Send", exact: true }).click();
  await expect(
    page.getByRole("button", { name: "Stop response" }),
  ).toBeVisible();
  await expect(page.getByLabel("assistant message")).toContainText(
    "Test fixture:",
  );
  await expect(
    page.getByRole("button", { name: "Send", exact: true }),
  ).toBeVisible();
  const url = page.url();
  await page.reload();
  await expect(page.getByLabel("assistant message")).toContainText(prompt);
  await page.getByRole("button", { name: "New conversation" }).click();
  await expect(page.getByLabel("assistant message")).toHaveCount(0);
  await page
    .getByLabel("Message", { exact: true })
    .fill("Independent second chat");
  await page.getByRole("button", { name: "Send", exact: true }).click();
  await expect(page.getByLabel("assistant message")).toContainText(
    "Independent second chat",
  );
  await expect(
    page.getByRole("button", { name: "Send", exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: prompt, exact: true }).click();
  await expect(page.getByLabel("assistant message")).toContainText(prompt);
  expect(page.url()).toBe(url);
  await expect(page.getByLabel("Message history")).not.toContainText(
    "Independent second chat",
  );
  await page.screenshot({
    path: "test-results/phase-1-chat.png",
    fullPage: true,
  });
});

test("failure is honest and explicit retry reuses the user message", async ({
  page,
}) => {
  test.skip(
    process.env.MEMORA_CHAT_TEST !== "1",
    "Requires isolated test-only upstream",
  );
  await page.goto("/");
  await page
    .getByLabel("Message", { exact: true })
    .fill(`[fail-once] ${Date.now()}`);
  await page.getByRole("button", { name: "Send", exact: true }).click();
  await expect(page.getByRole("alert")).toContainText("PROVIDER_AUTH_ERROR");
  await expect(page.getByLabel("assistant message")).toContainText(
    "No answer was generated.",
  );
  await page.getByRole("button", { name: "Retry last response" }).click();
  await expect(page.getByLabel("assistant message").last()).toContainText(
    "Test fixture:",
  );
  await expect(
    page.getByRole("button", { name: "Send", exact: true }),
  ).toBeVisible();
  await expect(page.getByLabel("user message", { exact: true })).toHaveCount(1);
  await expect(page.getByLabel("assistant message")).toHaveCount(2);
});

test("stop retains a partial answer after reload", async ({ page }) => {
  test.skip(
    process.env.MEMORA_CHAT_TEST !== "1",
    "Requires isolated test-only upstream",
  );
  await page.goto("/");
  await page
    .getByLabel("Message", { exact: true })
    .fill(`[slow] ${Date.now()}`);
  await page.getByRole("button", { name: "Send", exact: true }).click();
  await expect(page.getByLabel("assistant message")).toContainText(
    "Test fixture:",
  );
  await page.getByRole("button", { name: "Stop response" }).click();
  await expect(page.getByLabel("assistant message")).toContainText("cancelled");
  await page.reload();
  await expect(page.getByLabel("assistant message")).toContainText(
    "Test fixture:",
  );
  await expect(page.getByLabel("assistant message")).toContainText("cancelled");
});
