import { expect, test } from "@playwright/test";

test("PDF upload, RQ indexing, duplicate, citation and reload", async ({
  page,
}) => {
  test.skip(
    process.env.MEMORA_PDF_TEST !== "1",
    "Requires isolated PDF test upstream and RQ worker",
  );
  await page.goto("/");
  await page
    .getByRole("button", { name: "Knowledge Base", exact: true })
    .click();
  await page.getByLabel(/Upload PDF/).setInputFiles(process.env.TEST_PDF_PATH!);
  const card = page.locator(".document-card").filter({
    has: page.getByRole("heading", {
      name: "project_brief.pdf",
      exact: true,
    }),
  });
  await expect(card.locator(".document-status")).toHaveText("ready", {
    timeout: 60000,
  });
  await expect(card).toContainText("2 pages");
  await page.getByLabel(/Upload PDF/).setInputFiles(process.env.TEST_PDF_PATH!);
  await expect(
    page.getByText("Duplicate PDF: existing document and job reused."),
  ).toBeVisible();
  await expect(card).toHaveCount(1);
  await card.getByRole("button", { name: "Rebuild index" }).click();
  await expect(card.locator(".document-status")).toHaveText("ready", {
    timeout: 60000,
  });
  await card.getByRole("button", { name: "Ask this PDF" }).click();
  await page
    .getByLabel("Message", { exact: true })
    .fill("What is the API deadline?");
  await page.getByRole("button", { name: "Send", exact: true }).click();
  await expect(page.getByLabel("assistant message")).toContainText(
    "November 5, 2026",
    { timeout: 30000 },
  );
  await expect(page.locator(".citation-card").first()).toContainText(
    "project_brief.pdf · Page 1",
  );
  await expect(
    page.getByRole("button", { name: "Send", exact: true }),
  ).toBeVisible();
  await page.reload();
  await expect(page.locator(".citation-card").first()).toContainText(
    "project_brief.pdf · Page 1",
  );
  const href = await page
    .locator(".citation-card")
    .first()
    .getAttribute("href");
  expect((await page.request.get(href!.split("#")[0])).status()).toBe(200);
  await page.screenshot({
    path: "test-results/phase-2-rag.png",
    fullPage: true,
  });
});

test("corrupt PDF fails visibly and can be retried", async ({ page }) => {
  test.skip(process.env.MEMORA_PDF_TEST !== "1", "Requires isolated RQ worker");
  await page.goto("/");
  await page
    .getByRole("button", { name: "Knowledge Base", exact: true })
    .click();
  await page.getByLabel(/Upload PDF/).setInputFiles({
    name: "broken.pdf",
    mimeType: "application/pdf",
    buffer: Buffer.from("%PDF-corrupt"),
  });
  const card = page.locator(".document-card").filter({
    has: page.getByRole("heading", { name: "broken.pdf", exact: true }),
  });
  await expect(card).toContainText("PDF_CORRUPT", { timeout: 60000 });
  await card
    .getByRole("button", { name: "Retry processing", exact: true })
    .click();
  await expect(card.locator(".document-status")).toHaveText("failed", {
    timeout: 60000,
  });
  await expect(card.getByRole("button", { name: "Ask this PDF" })).toHaveCount(
    0,
  );
});

test("missing embedding configuration is explicit in Knowledge Base", async ({
  page,
}) => {
  await page.route("**/api/documents/config", (route) =>
    route.fulfill({
      json: {
        configured: false,
        missing: [
          "EMBEDDING_API_KEY",
          "EMBEDDING_MODEL",
          "EMBEDDING_DIMENSIONS",
        ],
        model: "",
        dimensions: 0,
        profile: "missing",
        max_upload_bytes: 20971520,
        message:
          "Configure backend .env: EMBEDDING_API_KEY, EMBEDDING_MODEL, EMBEDDING_DIMENSIONS",
      },
    }),
  );
  await page.goto("/");
  await page
    .getByRole("button", { name: "Knowledge Base", exact: true })
    .click();
  await expect(
    page.getByText("Embedding configuration required / 请配置 Embedding"),
  ).toBeVisible();
  await expect(page.getByText(/No mock embeddings are used/)).toBeVisible();
});
