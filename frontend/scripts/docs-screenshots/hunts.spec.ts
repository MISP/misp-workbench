import { test, expect, Locator, Page } from "@playwright/test";
import { applyTheme, capture, pinForCapture } from "./helpers";
import { HUNT_NAMES } from "./fixtures";

const FEATURE = "hunts";

/**
 * The Hunt select renders options as `#<id> — <name>`. We don't know the id
 * ahead of time, so resolve the option's value from the DOM and select by
 * value (selectOption({label}) only accepts strings, not patterns).
 */
async function selectHuntByName(modal: Locator, name: string) {
  const select = modal.locator("#createHuntSelect");
  await expect(select).toBeVisible();
  const option = select.locator("option", { hasText: name }).first();
  await expect(option).toBeAttached({ timeout: 10_000 });
  const value = await option.getAttribute("value");
  if (!value) throw new Error(`Hunt option has no value attr: ${name}`);
  await select.selectOption(value);
}

/**
 * Navigate from /hunts to a specific hunt's detail page. Waits for the
 * hunts table to actually have rows (huntsStore.getAll() resolves async,
 * separately from the New Hunt button which renders immediately).
 */
async function openHuntByName(page: Page, name: string) {
  await expect(page.locator("table tbody tr").first()).toBeVisible({
    timeout: 15_000,
  });
  const link = page.locator("table tbody a", { hasText: name }).first();
  if ((await link.count()) === 0) {
    const names = await page
      .locator("table tbody a.fw-semibold")
      .allTextContents();
    throw new Error(
      `Hunt "${name}" not found on /hunts. Visible hunts: ${JSON.stringify(
        names.map((n) => n.trim()),
      )}. Run \`npm run docs:seed:reset\` to refresh fixtures.`,
    );
  }
  await link.click();
  await page.waitForURL(/\/hunts\/\d+/);
}

/**
 * Open the New Hunt modal and (optionally) switch to a non-default hunt type
 * by clicking its card in HuntTypeSelector. The hunt-type cards are styled
 * <label> elements with the literal type label text inside an <h6>.
 */
async function openNewHuntModal(page: Page, typeLabel?: string) {
  // The modal caps at calc(100vh - 4rem) with an internal scroll on .card-body.
  // Grow the viewport and lift the height caps so the full form renders.
  await page.setViewportSize({ width: 1600, height: 1600 });
  await page.addStyleTag({
    content: `
      .modal-card { max-height: none !important; }
      .modal-card .card-body { overflow-y: visible !important; max-height: none !important; }
    `,
  });

  await page.getByRole("button", { name: /new hunt/i }).click();

  const modal = page.locator(".modal-card");
  await expect(modal).toBeVisible();
  await expect(modal.getByText("New Hunt")).toBeVisible();

  if (typeLabel) {
    await modal.locator(".hunt-type-card", { hasText: typeLabel }).click();
  }
  await pinForCapture(page);
  return modal;
}

test.describe("Hunts screenshots", () => {
  test.beforeEach(async ({ page }) => {
    await applyTheme(page);
    await page.goto("/hunts");
    // The hunts index has no heading; wait for the "+ New Hunt" button instead.
    await expect(page.getByRole("button", { name: /new hunt/i })).toBeVisible();
    await pinForCapture(page);
  });

  test("1 — new opensearch hunt modal", async ({ page }) => {
    const modal = await openNewHuntModal(page);
    await capture(modal, FEATURE, "misp-workbench-1_hunts_new-opensearch-hunt");
  });

  test("2a — new CPE hunt modal", async ({ page }) => {
    const modal = await openNewHuntModal(page, "CPE vuln lookup");
    await capture(modal, FEATURE, "misp-workbench-2_hunts_new-cpe-hunt");
  });

  test("2b — new MITRE ATT&CK hunt modal", async ({ page }) => {
    const modal = await openNewHuntModal(page, "MITRE ATT&CK");
    await capture(
      modal,
      FEATURE,
      "misp-workbench-2_hunts_new-mitre-attack-hunt",
    );
  });

  test("2c — new Rulezet hunt modal", async ({ page }) => {
    const modal = await openNewHuntModal(page, "Rulezet vuln check");
    await capture(modal, FEATURE, "misp-workbench-2_hunts_new-rulezet-hunt");
  });

  test("3 — view opensearch hunt", async ({ page }) => {
    await openHuntByName(page, HUNT_NAMES.opensearch);
    await pinForCapture(page);
    await expect(page.getByText(HUNT_NAMES.opensearch).first()).toBeVisible();

    await capture(page, FEATURE, "misp-workbench-3_hunts_view-opensearch-hunt");
  });

  test("4 — view opensearch hunt with matches", async ({ page }) => {
    // Tall viewport so the results table fits in one shot alongside meta + schedule.
    await page.setViewportSize({ width: 1600, height: 1800 });

    await openHuntByName(page, HUNT_NAMES.opensearch);

    await page.getByRole("button", { name: /run now/i }).click();
    // Results table renders once huntsStore.run() resolves.
    await expect(page.locator("table.table-striped")).toBeVisible({
      timeout: 15_000,
    });
    // Give chart.js / cal-heatmap a beat to redraw after the run updates history.
    await page.waitForTimeout(500);
    await pinForCapture(page);

    await capture(
      page,
      FEATURE,
      "misp-workbench-4_hunts_view-opensearch-hunt-matches",
    );
  });

  test("6 — scheduled tasks: + New button", async ({ page }) => {
    await page.goto("/tasks");
    const card = page.locator(".card", { hasText: "Scheduled Tasks" }).first();
    await expect(card).toBeVisible();
    await expect(card.getByRole("button", { name: /\+\s*new/i })).toBeVisible();
    await pinForCapture(page);

    await capture(
      card,
      FEATURE,
      "misp-workbench-6_hunts_scheduled-task-add-button",
    );
  });

  test("7 — scheduled task create modal (run_hunt)", async ({ page }) => {
    await page.setViewportSize({ width: 1600, height: 1400 });
    await page.goto("/tasks");

    const card = page.locator(".card", { hasText: "Scheduled Tasks" }).first();
    await card.getByRole("button", { name: /\+\s*new/i }).click();

    const modal = page.locator("#createScheduledTaskModal .modal-dialog");
    await expect(modal).toBeVisible();
    // Pick run_hunt — that reveals the Hunt select
    await modal
      .locator("#createTaskSelect")
      .selectOption({ label: "run_hunt" });
    await expect(modal.locator("#createHuntSelect")).toBeVisible();
    await selectHuntByName(modal, HUNT_NAMES.opensearch);
    await pinForCapture(page);

    await capture(
      modal,
      FEATURE,
      "misp-workbench-7_hunts_scheduled-task-add-scheduled-hunt",
    );
  });

  test("8 — scheduled hunt created", async ({ page }) => {
    // Per-row cleanup at the end of prior runs was unreliable (only deleted
    // the first row and didn't wait on the confirm dialog), so over time
    // the scheduled-tasks table accumulated ten-plus `run_hunt` rows. Wipe
    // via the API before the test so the captured table always shows
    // exactly one freshly-created row.
    //
    // The JWT is in localStorage (auth store), not cookies — page.request
    // alone doesn't see it. Land on /events first so the app boots and
    // hydrates the token from storageState, then grab it.
    const apiBase = "http://localhost:8080";
    await page.goto("/events/a1f30000-0001-4001-8000-000000000001");
    const token = await page.evaluate(() =>
      localStorage.getItem("access_token"),
    );
    const auth = { Authorization: `Bearer ${token}` };
    const scheduled = await page.request
      .get(`${apiBase}/tasks/scheduled`, { headers: auth })
      .then((r) => (r.ok() ? r.json() : []))
      .catch(() => []);
    for (const t of scheduled || []) {
      if (t?.task_name === "app.worker.tasks.run_hunt") {
        await page.request
          .delete(`${apiBase}/tasks/scheduled/${t.id}`, { headers: auth })
          .catch(() => undefined);
      }
    }

    await page.goto("/tasks");

    const card = page.locator(".card", { hasText: "Scheduled Tasks" }).first();
    await card.getByRole("button", { name: /\+\s*new/i }).click();

    const modal = page.locator("#createScheduledTaskModal .modal-dialog");
    await expect(modal).toBeVisible();
    await modal
      .locator("#createTaskSelect")
      .selectOption({ label: "run_hunt" });
    await selectHuntByName(modal, HUNT_NAMES.opensearch);
    // The default schedule (interval, every=1 hour) is valid out of the box.
    await modal.getByRole("button", { name: /create|save/i }).click();
    await expect(modal).not.toBeVisible({ timeout: 10_000 });

    // The new row should appear; verify there's exactly one run_hunt row.
    await expect(
      card.locator("table tbody tr", { hasText: "run_hunt" }),
    ).toHaveCount(1, { timeout: 10_000 });
    await pinForCapture(page);

    await capture(
      card,
      FEATURE,
      "misp-workbench-8_hunts_scheduled-task-created-scheduled-hunt",
    );
  });

  test("5 — hunt matches notification row", async ({ page }) => {
    // Stub the notifications feed with a single hunt.result.changed entry
    // so we don't need a real Celery run to push one. The visible row
    // captures the user-facing surface of the notification — the original
    // shot was framed exactly the same way.
    const API_PORT = 8080;
    await page.route(
      new RegExp(`:${API_PORT}/notifications(\\?|$)`),
      (route) => {
        if (route.request().method() !== "GET") return route.fallback();
        return route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            total: 1,
            page: 1,
            size: 20,
            items: [
              {
                id: 901,
                user_id: 1,
                type: "hunt.result.changed",
                entity_uuid: null,
                entity_type: "hunt",
                read: false,
                // ~1 min ago so the relative-time label reads "a minute ago".
                created_at: new Date(Date.now() - 60_000).toISOString(),
                payload: {
                  hunt_id: 5,
                  hunt_name: "Suspicious IPs",
                  total: 12,
                  previous_total: 11,
                },
              },
            ],
          }),
        });
      },
    );

    await page.goto("/notifications");
    await expect(page.getByText("Suspicious IPs")).toBeVisible({
      timeout: 10_000,
    });
    await expect(page.getByText("hunt.result.changed")).toBeVisible();
    await pinForCapture(page);

    // Just the row — matches the original framing (no toolbar/header).
    await capture(
      page.locator("table tbody tr").first(),
      FEATURE,
      "misp-workbench-5_hunts_view-opensearch-hunt-matches-notification",
    );
  });
});
