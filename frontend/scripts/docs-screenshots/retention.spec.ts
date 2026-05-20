import { test, expect } from "@playwright/test";
import { applyTheme, capture, pinForCapture } from "./helpers";

const FEATURE = "retention-period";

// Anchor on the API port so frontend navigations to /settings/runtime or
// /tasks/* aren't caught by the stub.
const API_PORT = 8080;

test.describe("Retention screenshots", () => {
  test("1 — runtime settings retention panel", async ({ page }) => {
    await applyTheme(page);

    // Stub /tasks/scheduled to return an empty list so the schedule editor
    // (Interval/Crontab tabs + Create Schedule button) renders instead of
    // the "schedule exists" view. Without this, the captured panel would
    // depend on whatever's already scheduled on the dev backend.
    await page.route(new RegExp(`:${API_PORT}/tasks/scheduled$`), (route) => {
      if (route.request().method() !== "GET") return route.fallback();
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify([]),
      });
    });

    // The page is tall — defaults card + 3 accordion items; retention is
    // last, expanding it doubles the card height.
    await page.setViewportSize({ width: 1400, height: 1600 });

    await page.goto("/settings/runtime");

    await expect(
      page.getByRole("heading", { name: "Runtime Settings" }),
    ).toBeVisible({ timeout: 15_000 });

    // Wait for at least one accordion item to appear (loadAll resolves).
    await expect(page.locator(".accordion-item").first()).toBeVisible({
      timeout: 10_000,
    });

    // Click the "retention" accordion button to expand it.
    const retentionToggle = page.getByRole("button", {
      name: /^retention$/i,
    });
    await retentionToggle.click();
    // Wait for the form to render — `Retention Period (days)` label is in
    // the expanded form section.
    await expect(page.getByText(/Retention Period \(days\)/i)).toBeVisible({
      timeout: 10_000,
    });
    await expect(page.getByText("Exempt Tags", { exact: true })).toBeVisible();
    // Schedule editor: `Create Schedule` is the CTA when no schedule exists.
    await expect(
      page.getByRole("button", { name: /Create Schedule/i }),
    ).toBeVisible();

    // The editor defaults to Crontab mode; the original screenshot has
    // Interval selected. Click the Interval label so the simpler form
    // (Every / Unit) is shown instead of the cron grid.
    await page.locator('label[for^="modeInterval_"]').click();
    await expect(page.getByLabel("Every", { exact: true })).toBeVisible();
    await pinForCapture(page);

    // Capture the Runtime Settings card.
    const card = page.locator(".card").first();
    await capture(card, FEATURE, "misp-workbench-1_runtime_settings_retention");
  });
});
