import { test, expect } from "@playwright/test";
import { applyTheme, capture, pinForCapture } from "./helpers";

const FEATURE = "audit-logs";

test.describe("Audit logs screenshots", () => {
  test.beforeEach(async ({ page }) => {
    await applyTheme(page);
    await page.goto("/admin/audit-logs");
    await expect(
      page.getByRole("heading", { name: "Audit logs" }),
    ).toBeVisible();
    await pinForCapture(page);
  });

  test("1 — audit logs index", async ({ page }) => {
    // Wait for table rows to render (seeded fixture entries: login, api_key.created,
    // runtime_setting.updated, logout).
    await expect(
      page.locator("table tbody tr", { hasText: "user.login" }).first(),
    ).toBeVisible({ timeout: 10_000 });
    await expect(
      page.locator("table tbody tr", { hasText: "api_key.created" }).first(),
    ).toBeVisible();
    await expect(
      page
        .locator("table tbody tr", { hasText: "runtime_setting.updated" })
        .first(),
    ).toBeVisible();
    await expect(
      page.locator("table tbody tr", { hasText: "user.logout" }).first(),
    ).toBeVisible();

    // Expand the first row in the table so the details panel (user_agent +
    // metadata JSON) renders near the top of the screenshot, not below the
    // viewport. Rows are sorted by created_at desc, so this is the latest
    // fixture entry.
    await page
      .locator("table tbody tr")
      .first()
      .getByRole("button", { name: /show/i })
      .click();
    await expect(
      page.locator("table tbody tr", { hasText: "user agent" }).first(),
    ).toBeVisible();
    await pinForCapture(page);

    await capture(page, FEATURE, "misp-workbench-1_audit_logs");
  });
});
