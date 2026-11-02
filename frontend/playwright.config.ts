import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./tests",
  use: {
    baseURL: process.env.TEST_BASE_URL || "http://127.0.0.1:55173",
    browserName: "chromium",
    channel: process.env.PLAYWRIGHT_CHANNEL,
    screenshot: "only-on-failure",
    trace: "retain-on-failure",
  },
  reporter: "list",
});
