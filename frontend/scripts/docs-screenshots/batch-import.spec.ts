import { test, expect } from "@playwright/test";
import { applyTheme, capture, pinForCapture } from "./helpers";
import { EVENT_UUIDS } from "./fixtures";

const FEATURE = "batch-import";

// The Import Data modal lives in EventActions and is opened from any event
// view via the file-import icon button (title="Import"). No backend stubs
// are needed — the auto-detection runs entirely client-side on the textarea.

const PASTE = [
  "153.172.237.200",
  "172.165.116.110",
  "c7d2e6c549e4dd86c00fc1cbea40ff6f",
  "evil.com",
].join("\n");

test.describe("Batch import screenshots", () => {
  test("1 — Import Data modal with detected types", async ({ page }) => {
    await applyTheme(page);
    // Modal is modal-lg + tall once the preview list renders. 1100px viewport
    // crops the Discard/Import footer.
    await page.setViewportSize({ width: 1400, height: 1400 });

    await page.goto(`/events/${EVENT_UUIDS.cobaltStrike}`);
    // Wait for the event toolbar to render before clicking Import.
    await expect(
      page.getByRole("button", { name: /^Import$/ }).first(),
    ).toBeVisible({ timeout: 15_000 });
    await page
      .getByRole("button", { name: /^Import$/ })
      .first()
      .click();

    const modal = page.locator(
      `#importDataEventModal_${EVENT_UUIDS.cobaltStrike}`,
    );
    await expect(modal).toBeVisible();
    await expect(
      modal.getByRole("heading", { name: "Import Data" }),
    ).toBeVisible();

    // Fill the textarea — detection is debounced; the preview / badges appear
    // once parsing finishes.
    await modal.locator("textarea").fill(PASTE);

    await expect(modal.getByText("4 valid")).toBeVisible({ timeout: 10_000 });
    // Detection badges (one per detected type, plus counts)
    await expect(modal.getByText(/ip-dst · 2/)).toBeVisible();
    await expect(modal.getByText(/md5 · 1/)).toBeVisible();
    await expect(modal.getByText(/domain · 1/)).toBeVisible();
    // Preview rows
    await expect(modal.getByText("153.172.237.200")).toBeVisible();
    await expect(modal.getByText("evil.com")).toBeVisible();
    await pinForCapture(page);

    await capture(
      modal.locator(".modal-content"),
      FEATURE,
      "misp-workbench_1-batch-import-modal",
    );
  });
});
