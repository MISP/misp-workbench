import { test, expect } from "@playwright/test";
import { capture, pinForCapture } from "./helpers";
import { HUNT_NAMES } from "./fixtures";

const FEATURE = "hunts";

test.describe("Hunts screenshots", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/hunts");
    // The hunts index has no heading; wait for the "+ New Hunt" button instead.
    await expect(page.getByRole("button", { name: /new hunt/i })).toBeVisible();
    await pinForCapture(page);
  });

  test("1 — new opensearch hunt modal", async ({ page }) => {
    // The modal caps at calc(100vh - 4rem) with an internal scroll on
    // .card-body. Grow the viewport and lift the height caps so the full
    // form renders for the screenshot.
    await page.setViewportSize({ width: 1600, height: 1600 });
    await page.addStyleTag({
      content: `
        .modal-card { max-height: none !important; }
        .modal-card .card-body { overflow-y: visible !important; max-height: none !important; }
      `,
    });

    await page.getByRole("button", { name: /new hunt/i }).click();

    // AddHuntModal opens in-page (not a route change). Default hunt_type is opensearch.
    const modal = page.locator(".modal-card");
    await expect(modal).toBeVisible();
    await expect(modal.getByText("New Hunt")).toBeVisible();
    await pinForCapture(page);

    await capture(modal, FEATURE, "misp-workbench-1_hunts_new-opensearch-hunt");
  });

  test("3 — view opensearch hunt", async ({ page }) => {
    await page.getByRole("link", { name: HUNT_NAMES.opensearch }).click();
    await page.waitForURL(/\/hunts\/\d+/);
    await pinForCapture(page);
    // Hunt detail page renders the hunt name as page content
    await expect(page.getByText(HUNT_NAMES.opensearch).first()).toBeVisible();

    await capture(page, FEATURE, "misp-workbench-3_hunts_view-opensearch-hunt");
  });

  // Stubs for remaining shots — wire selectors when extending coverage:
  //   2_hunts_new-cpe-hunt — click "CPE vuln lookup" card in HuntTypeSelector
  //   2_hunts_new-mitre-attack-hunt — click "MITRE ATT&CK" card
  //   2_hunts_new-rulezet-hunt — click "Rulezet vuln check" card
  //   4_hunts_view-opensearch-hunt-matches — view hunt, click "Run" and wait for matches
  //   5_hunts_view-opensearch-hunt-matches-notification — toast/snackbar capture
  //   6_hunts_scheduled-task-add-button — locate the schedule button on view hunt
  //   7_hunts_scheduled-task-add-scheduled-hunt — open scheduled-hunt modal
  //   8_hunts_scheduled-task-created-scheduled-hunt — confirm dialog after submit
});
