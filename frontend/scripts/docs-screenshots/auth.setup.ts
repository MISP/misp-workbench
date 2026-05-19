import { test as setup, expect } from "@playwright/test";
import path from "node:path";
import { DOCS_USER } from "./fixtures";

const STORAGE_STATE = path.join(__dirname, ".auth", "user.json");

setup("authenticate as docs user", async ({ page }) => {
  await page.goto("/login");
  await page.fill('input[name="username"]', DOCS_USER.email);
  await page.fill('input[name="password"]', DOCS_USER.password);
  await page.click('button[type="submit"]');

  // Auth store redirects to /events on success; wait for that
  await expect(page).toHaveURL(/\/events/, { timeout: 15_000 });

  await page.context().storageState({ path: STORAGE_STATE });
});
