import { test, expect, Page } from "@playwright/test";
import { applyTheme, capture, pinForCapture } from "./helpers";

const FEATURE = "exports";
const API_BASE = process.env.DOCS_API_URL ?? "http://localhost:8080";

/**
 * The JWT lives in localStorage (auth store), not cookies — page.request
 * alone doesn't see it. Boot the app on a real page first so the token
 * hydrates from storageState, then read it.
 */
async function apiHeaders(page: Page): Promise<Record<string, string>> {
  const token = await page.evaluate(() => localStorage.getItem("access_token"));
  return { Authorization: `Bearer ${token}` };
}

/**
 * Exports have no seed fixtures and accumulate across runs, so wipe every
 * export (which also unregisters its redbeat schedule) before seeding the
 * deterministic rows a test needs.
 */
async function resetExports(page: Page) {
  const headers = await apiHeaders(page);
  const list = await page.request
    .get(`${API_BASE}/exports/?size=100`, { headers })
    .then((r) => (r.ok() ? r.json() : { items: [] }))
    .catch(() => ({ items: [] }));
  for (const item of list?.items ?? []) {
    await page.request
      .delete(`${API_BASE}/exports/${item.id}`, { headers })
      .catch(() => undefined);
  }
}

async function createExport(
  page: Page,
  body: Record<string, unknown>,
): Promise<void> {
  const headers = await apiHeaders(page);
  await page.request.post(`${API_BASE}/exports/`, { headers, data: body });
}

test.describe("Exports screenshots", () => {
  test.beforeEach(async ({ page }) => {
    await applyTheme(page);
  });

  test("1 — new export form with schedule", async ({ page }) => {
    // The create form is the full-page AddExport view, capped at 720px.
    await page.setViewportSize({ width: 1200, height: 1400 });
    await page.goto("/exports/add");

    await page.fill("#export-name", "Network IOCs — daily");
    await page.fill("#export-query", "type:ip-dst AND to_ids:true");
    await page.locator("#export-schedule-enabled").check();
    await expect(page.getByText(/run on a schedule/i)).toBeVisible();
    await pinForCapture(page);

    await capture(
      page.locator(".card").first(),
      FEATURE,
      "misp-workbench-1_exports_new-export",
    );
  });

  test("2 — save as export from Explore", async ({ page }) => {
    await page.goto("/explore");
    await expect(page.locator("input.form-control.text-console")).toBeVisible();
    await page.fill("input.form-control.text-console", "*");
    await page.locator("button.btn-primary >> svg").first().click();
    await page.waitForSelector(".card", { timeout: 10_000 });
    await pinForCapture(page);

    const resultSection = page.locator(".result-section").first();
    const downloadBtn = resultSection
      .locator("button.dropdown-toggle", { hasText: /download/i })
      .first();
    await downloadBtn.click();

    const menu = resultSection
      .locator(".dropdown-menu")
      .filter({ hasText: /save as export/i })
      .first();
    await expect(menu).toBeVisible();

    await capture(
      resultSection,
      FEATURE,
      "misp-workbench-2_exports_save-as-export-menu",
    );
  });

  test("3 — save as export modal with schedule", async ({ page }) => {
    await page.setViewportSize({ width: 1400, height: 1400 });
    await page.goto("/explore");
    await expect(page.locator("input.form-control.text-console")).toBeVisible();
    // Use "*" so the events tab has results — a query matching only
    // attributes auto-switches the active tab, re-rendering (and detaching)
    // the Download button mid-click.
    await page.fill("input.form-control.text-console", "*");
    await page.locator("button.btn-primary >> svg").first().click();
    await page.waitForSelector(".card", { timeout: 10_000 });

    const resultSection = page.locator(".result-section").first();
    const downloadBtn = resultSection
      .locator("button.dropdown-toggle", { hasText: /download/i })
      .first();
    await expect(downloadBtn).toBeVisible();
    // Let the post-search re-renders (tabs, timeline) settle before clicking.
    await page.waitForTimeout(700);
    await downloadBtn.click();
    await resultSection
      .getByRole("button", { name: /save as export/i })
      .click();

    const modal = page.locator(".modal-card");
    await expect(modal.getByText("New Export")).toBeVisible();
    await modal.locator("#modal-export-name").fill("Network IOCs — daily");
    await modal.locator("#export-schedule-enabled").check();
    await pinForCapture(page);

    await capture(
      modal,
      FEATURE,
      "misp-workbench-3_exports_save-as-export-modal",
    );
  });

  test("4 — exports list with a scheduled export", async ({ page }) => {
    await page.goto("/exports");
    await resetExports(page);
    await createExport(page, {
      name: "Network IOCs — daily",
      query: "type:ip-dst AND to_ids:true",
      index_target: "attributes",
      format: "json",
      schedule: {
        type: "crontab",
        minute: "0",
        hour: "2",
        day_of_week: "*",
        day_of_month: "*",
        month_of_year: "*",
      },
      schedule_enabled: true,
    });
    await createExport(page, {
      name: "Weekly event digest",
      query: "info:*ransomware*",
      index_target: "events",
      format: "csv",
    });

    await page.goto("/exports");
    await expect(
      page.locator("table tbody tr", { hasText: "Network IOCs — daily" }),
    ).toBeVisible({ timeout: 15_000 });
    await pinForCapture(page);

    await capture(
      page.locator(".table-responsive").first(),
      FEATURE,
      "misp-workbench-4_exports_list",
    );
  });

  test("5 — edit schedule modal", async ({ page }) => {
    await page.goto("/exports");
    await resetExports(page);
    await createExport(page, {
      name: "Network IOCs — daily",
      query: "type:ip-dst AND to_ids:true",
      index_target: "attributes",
      format: "json",
      schedule: {
        type: "crontab",
        minute: "0",
        hour: "2",
        day_of_week: "*",
        day_of_month: "*",
        month_of_year: "*",
      },
      schedule_enabled: true,
    });

    await page.goto("/exports");
    const row = page.locator("table tbody tr", {
      hasText: "Network IOCs — daily",
    });
    await expect(row).toBeVisible({ timeout: 15_000 });
    await row.getByRole("button", { name: /edit schedule/i }).click();

    const modal = page.locator(".modal-card");
    await expect(modal.getByText(/schedule —/i)).toBeVisible();
    await pinForCapture(page);

    await capture(modal, FEATURE, "misp-workbench-5_exports_edit-schedule");
  });

  test("6 — new incremental NDJSON feed", async ({ page }) => {
    await page.setViewportSize({ width: 1200, height: 1700 });
    await page.goto("/exports/add");

    await page.fill("#export-name", "SIEM IOC feed (incremental)");
    await page.fill("#export-query", "to_ids:true");
    await page.selectOption("#export-format", "ndjson");
    await page.locator("#export-incremental").check();
    await page.locator("#export-schedule-enabled").check();
    await expect(page.getByText(/incremental feed/i).first()).toBeVisible();
    await pinForCapture(page);

    await capture(
      page.locator(".card").first(),
      FEATURE,
      "misp-workbench-6_exports_new-incremental-feed",
    );
  });

  test("7 — exports list with an incremental feed", async ({ page }) => {
    // A feed URL only shows once the export has run (it needs a cursor), and
    // the screenshot environment has no worker to run it: serve the list.
    const hourly = {
      type: "crontab",
      minute: "0",
      hour: "*",
      day_of_week: "*",
      day_of_month: "*",
      month_of_year: "*",
    };
    const minutesAgo = (n: number) =>
      new Date(Date.now() - n * 60_000).toISOString();
    const base = {
      user_id: 1,
      status: "completed",
      error: null,
      celery_task_id: null,
      distribution: null,
      schedule_enabled: true,
      scheduled_task_name: "demo",
      created_at: minutesAgo(60 * 24 * 7),
      started_at: minutesAgo(21),
      finished_at: minutesAgo(20),
      last_run_at: minutesAgo(20),
      checksum: "0".repeat(64),
    };
    const items = [
      {
        ...base,
        id: 31,
        name: "SIEM IOC feed (incremental)",
        query: "to_ids:true",
        index_target: "attributes",
        format: "ndjson",
        incremental: true,
        cursor: Math.floor(Date.now() / 1000) - 20 * 60,
        record_count: 18342,
        file_size: 9_437_184,
        schedule: hourly,
      },
      {
        ...base,
        id: 32,
        name: "Wazuh CDB list: network IOCs",
        query: "to_ids:true AND (type:ip-src OR type:ip-dst OR type:domain)",
        index_target: "attributes",
        format: "cdb",
        incremental: false,
        cursor: null,
        record_count: 11207,
        file_size: 412_330,
        schedule: { ...hourly, minute: "30", hour: "*/6" },
      },
    ];
    await page.route(/:8080\/exports\/\?/, (route) => {
      if (route.request().method() !== "GET") return route.fallback();
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          items,
          total: items.length,
          page: 1,
          size: 50,
          pages: 1,
        }),
      });
    });

    await page.goto("/exports");
    await expect(page.getByText("feed URL")).toBeVisible();
    await pinForCapture(page);

    await capture(
      page.locator(".table-responsive").first(),
      FEATURE,
      "misp-workbench-7_exports_incremental-feed-list",
    );
  });
});
