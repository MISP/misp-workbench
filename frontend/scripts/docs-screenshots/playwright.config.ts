import { defineConfig } from "@playwright/test";
import path from "node:path";

const FRONTEND_URL = process.env.DOCS_FRONTEND_URL ?? "http://localhost:3001";
const STORAGE_STATE = path.join(__dirname, ".auth", "user.json");

export default defineConfig({
  testDir: __dirname,
  testMatch: /.*\.spec\.ts$/,
  fullyParallel: false,
  workers: 1,
  retries: 0,
  reporter: [["list"]],

  // Seeds docs fixtures once per suite invocation. The audit-logs spec
  // depends on the four `_docs_fixture` audit rows landing on page 1; this
  // hook re-times them at every run so the umbrella `docs:screenshots`
  // works as reliably as `docs:screenshots:audit-logs` used to.
  // Disable with DOCS_SCREENSHOTS_SKIP_SEED=1.
  globalSetup: path.join(__dirname, "global-setup.ts"),

  // NOTE: don't spread devices["Desktop Chrome"] into the projects —
  // its preset viewport (1280x720) and deviceScaleFactor (1) override
  // the values we want here.
  use: {
    baseURL: FRONTEND_URL,
    browserName: "chromium",
    viewport: { width: 1600, height: 1000 },
    deviceScaleFactor: 3,
    locale: "en-US",
    timezoneId: "UTC",
    actionTimeout: 10_000,
    navigationTimeout: 30_000,
  },

  projects: [
    {
      name: "auth",
      testMatch: /auth\.setup\.ts/,
    },
    {
      name: "screenshots-light",
      dependencies: ["auth"],
      metadata: { theme: "light" },
      use: {
        storageState: STORAGE_STATE,
        colorScheme: "light",
      },
    },
    {
      name: "screenshots-dark",
      dependencies: ["auth"],
      metadata: { theme: "dark" },
      use: {
        storageState: STORAGE_STATE,
        colorScheme: "dark",
      },
    },
  ],
});
