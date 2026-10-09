import { test, expect } from "@playwright/test";
import { applyTheme, capture, pinForCapture } from "./helpers";

const FEATURE = "api-keys";

test.describe("API keys screenshots", () => {
  test.beforeEach(async ({ page }) => {
    await applyTheme(page);
  });

  test("1 — new key with the SIEM integration preset", async ({ page }) => {
    await page.setViewportSize({ width: 1400, height: 1400 });
    await page.goto("/settings/api-keys");
    await page.getByRole("button", { name: /new api key/i }).click();

    const modal = page.locator(".modal-content");
    await expect(modal.getByText("New API key")).toBeVisible();
    await modal
      .getByRole("button", { name: /siem integration preset/i })
      .click();
    await modal
      .locator("textarea")
      .first()
      .fill("Splunk production: restSearch, feeds and sightings");
    await pinForCapture(page);

    await capture(modal, FEATURE, "misp-workbench-1_api-keys_siem-preset");
  });
});
