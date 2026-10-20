import { test as setup, expect } from "@playwright/test";
import path from "node:path";
import { DOCS_USER } from "../docs-screenshots/fixtures";

const STORAGE_STATE = path.join(__dirname, ".auth", "user.json");

setup("authenticate as the workshop participant", async ({ page }) => {
  await page.goto("/login");
  await page.fill('input[name="username"]', DOCS_USER.email);
  await page.fill('input[name="password"]', DOCS_USER.password);
  await page.click('button[type="submit"]');
  await expect(page).toHaveURL(/\/explore/, { timeout: 15_000 });
  await page.context().storageState({ path: STORAGE_STATE });
});
