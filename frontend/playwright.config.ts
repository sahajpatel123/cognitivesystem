import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./tests",
  timeout: 60000,
  retries: 0,
  use: {
    baseURL: "http://localhost:3000",
    headless: true,
  },
  webServer: {
    command: "npm run dev -- --hostname 0.0.0.0 --port 3000",
    port: 3000,
    timeout: 120000,
    reuseExistingServer: true,
  },
});
