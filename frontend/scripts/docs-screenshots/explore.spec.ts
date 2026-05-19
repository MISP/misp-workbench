import { test, expect } from "@playwright/test";
import { applyTheme, capture, pinForCapture } from "./helpers";

const FEATURE = "explore";

test.describe("Explore screenshots", () => {
  test.beforeEach(async ({ page }) => {
    await applyTheme(page);
    await page.goto("/explore");
    await expect(page.locator("input.form-control.text-console")).toBeVisible();
    await pinForCapture(page);
  });

  test("1 — default Explore view", async ({ page }) => {
    await page.fill("input.form-control.text-console", "*");
    await page.locator("button.btn-primary >> svg").first().click();
    await page.waitForSelector(".card", { timeout: 10_000 });

    // Timeline renders via chart.js into a <canvas> after its own fetch
    // resolves. Wait for the spinner to disappear and the canvas to appear,
    // then give chart.js a beat to finish drawing bars.
    await expect(
      page.locator(".explore-timeline", { hasText: "Loading timeline" }),
    ).toHaveCount(0, { timeout: 15_000 });
    await expect(page.locator(".explore-timeline canvas")).toBeVisible({
      timeout: 15_000,
    });
    await page.waitForTimeout(500);

    await capture(page, FEATURE, "misp-workbench-1_explore");
  });

  test("2 — Lucene cheatsheet modal", async ({ page }) => {
    await page
      .locator('button[data-bs-target="#luceneQuerySyntaxCheatsheetModal"]')
      .click();

    const modal = page.locator(
      "#luceneQuerySyntaxCheatsheetModal .modal-dialog",
    );
    await expect(modal).toBeVisible();
    // Bootstrap modal fades in; pinForCapture zeroes the transition but
    // re-apply after it's painted to catch the backdrop too.
    await pinForCapture(page);

    await capture(modal, FEATURE, "misp-workbench-2_explore_lucene_cheatsheet");
  });

  test("3 — relative time filter open", async ({ page }) => {
    await page.locator(".time-range-filter > button").click();

    const panel = page.locator(".time-range-panel");
    await expect(panel).toBeVisible();
    await panel.locator(".nav-link", { hasText: "Relative" }).click();

    await capture(
      panel,
      FEATURE,
      "misp-workbench-3_explore_time-filter-relative",
    );
  });

  test("4 — absolute time filter open", async ({ page }) => {
    await page.locator(".time-range-filter > button").click();

    const panel = page.locator(".time-range-panel");
    await expect(panel).toBeVisible();
    await panel.locator(".nav-link", { hasText: "Absolute" }).click();

    await capture(
      panel,
      FEATURE,
      "misp-workbench-4_explore_time-filter-absolute",
    );
  });

  test("5 — search history panel", async ({ page }) => {
    // Pre-populate recent searches so the expanded panel has content to show.
    await page.evaluate(() => {
      localStorage.setItem(
        "user_recent_explore_searches",
        JSON.stringify([
          "type.keyword:ip*",
          "info:banking",
          'tags.name.keyword:"tlp:amber"',
          "@timestamp:[2026-01-01 TO *]",
        ]),
      );
    });
    await page.reload();
    await expect(page.locator("input.form-control.text-console")).toBeVisible();
    await pinForCapture(page);

    // The component renders .card-body as position:absolute (it overlays
    // content below the panel). That puts it outside the panel's bounding
    // box, so locator.screenshot would crop it. Pin it back into normal
    // flow for the duration of the capture.
    await page.addStyleTag({
      content: `
        .saved-searches-panel .card-body {
          position: static !important;
        }
      `,
    });

    const panel = page.locator(".saved-searches-panel");
    await panel.locator(".card-header").click();
    await expect(panel.locator(".list-group")).toBeVisible();

    await capture(panel, FEATURE, "misp-workbench-5_explore_search-history");
  });

  test("6 — save-as-Hunt dropdown", async ({ page }) => {
    await page.fill("input.form-control.text-console", "type.keyword:ip*");

    // First dropdown in the search input-group is the floppy-disk "save" menu.
    await page
      .locator(".input-group .dropdown > button.dropdown-toggle")
      .first()
      .click();

    const menu = page
      .locator(".input-group .dropdown-menu.show, .input-group .dropdown-menu")
      .filter({ hasText: "Save as Hunt" })
      .first();
    await expect(menu).toBeVisible();

    // Capture the search bar row so the dropdown context is visible.
    const inputGroup = page.locator(".input-group").first();
    await capture(
      inputGroup,
      FEATURE,
      "misp-workbench-6_explore_save-search-as-hunt",
    );
  });

  test("7 — download results menu", async ({ page }) => {
    await page.fill("input.form-control.text-console", "*");
    await page.locator("button.btn-primary >> svg").first().click();
    await page.waitForSelector(".card", { timeout: 10_000 });

    const resultSection = page.locator(".result-section").first();
    const downloadBtn = resultSection
      .locator("button.dropdown-toggle", { hasText: /download/i })
      .first();
    await downloadBtn.click();

    const menu = resultSection
      .locator(".dropdown-menu")
      .filter({ hasText: /JSON/ })
      .first();
    await expect(menu).toBeVisible();

    await capture(
      resultSection,
      FEATURE,
      "misp-workbench-7_explore_save-search-results",
    );
  });
});
