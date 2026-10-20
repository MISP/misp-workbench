import { defineConfig } from "@playwright/test";
import path from "node:path";

const FRONTEND_URL = process.env.DOCS_FRONTEND_URL ?? "http://localhost:3001";
const STORAGE_STATE = path.join(__dirname, ".auth", "user.json");

// Plays tutorial/workshop.md for real, as a participant would, and captures
// what each lab should look like when done right. Unlike the docs-screenshots
// suite nothing is stubbed: it writes feeds, events, a warninglist, a profile,
// review decisions, exports, an EDL and a notebook to the instance it points
// at. Run it against a dev stack loaded with `seed-demo`, never a real one.
export default defineConfig({
  testDir: __dirname,
  testMatch: /.*\.(spec|setup)\.ts$/,
  fullyParallel: false,
  workers: 1,
  retries: 0,
  reporter: [["list"]],
  // Feed ingestion and the 15-second indicator sync are waited for.
  timeout: 10 * 60_000,
  expect: { timeout: 15_000 },

  use: {
    baseURL: FRONTEND_URL,
    browserName: "chromium",
    viewport: { width: 1600, height: 1000 },
    deviceScaleFactor: 2,
    locale: "en-US",
    timezoneId: "UTC",
    colorScheme: "light",
    actionTimeout: 15_000,
    navigationTimeout: 30_000,
  },

  projects: [
    { name: "auth", testMatch: /auth\.setup\.ts/ },
    {
      name: "workshop",
      testMatch: /workshop\.spec\.ts/,
      dependencies: ["auth"],
      use: { storageState: STORAGE_STATE },
    },
  ],
});
