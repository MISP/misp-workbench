import { test, expect, Page } from "@playwright/test";
import { applyTheme, capture, pinForCapture } from "./helpers";
import {
  SERVO,
  SERVO_ID,
  SERVOS_LIST,
  PIPELINES,
  FINAL_PIPELINE_DETAIL,
  TEMPLATES,
  SIMULATE_RESPONSE,
  SERVO_ERRORS,
  BACKFILL_PREVIEW,
  SERVO_RUNS,
} from "./servos-fixtures";

const FEATURE = "tech-lab/transformation-servos";

// API host port (matches VITE_API_URL in frontend/.env). Anchoring the stubs on
// the port keeps SPA navigations to /tech-lab/servos/* untouched — the Vue
// routes collide with the API paths otherwise.
const API_PORT = 8080;

async function stubServoRoutes(page: Page) {
  // GET /tech-lab/servos/pipelines
  await page.route(
    new RegExp(`:${API_PORT}/tech-lab/servos/pipelines$`),
    (route) => {
      if (route.request().method() !== "GET") return route.fallback();
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(PIPELINES),
      });
    },
  );

  // GET /tech-lab/servos/pipelines/{name}
  await page.route(
    new RegExp(`:${API_PORT}/tech-lab/servos/pipelines/.+`),
    (route) => {
      if (route.request().method() !== "GET") return route.fallback();
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(FINAL_PIPELINE_DETAIL),
      });
    },
  );

  // GET /tech-lab/servos/backfill/preview
  await page.route(
    new RegExp(`:${API_PORT}/tech-lab/servos/backfill/preview`),
    (route) => {
      if (route.request().method() !== "GET") return route.fallback();
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(BACKFILL_PREVIEW),
      });
    },
  );

  // GET /tech-lab/servos/runs
  await page.route(
    new RegExp(`:${API_PORT}/tech-lab/servos/runs$`),
    (route) => {
      if (route.request().method() !== "GET") return route.fallback();
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(SERVO_RUNS),
      });
    },
  );

  // GET /tech-lab/servos/errors
  await page.route(
    new RegExp(`:${API_PORT}/tech-lab/servos/errors$`),
    (route) => {
      if (route.request().method() !== "GET") return route.fallback();
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(SERVO_ERRORS),
      });
    },
  );

  // GET /tech-lab/servos/templates
  await page.route(
    new RegExp(`:${API_PORT}/tech-lab/servos/templates$`),
    (route) => {
      if (route.request().method() !== "GET") return route.fallback();
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(TEMPLATES),
      });
    },
  );

  // POST /tech-lab/servos/simulate
  await page.route(
    new RegExp(`:${API_PORT}/tech-lab/servos/simulate$`),
    (route) => {
      if (route.request().method() !== "POST") return route.fallback();
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(SIMULATE_RESPONSE),
      });
    },
  );

  // GET /tech-lab/servos/?... → paginated list
  await page.route(new RegExp(`:${API_PORT}/tech-lab/servos/\\?`), (route) => {
    if (route.request().method() !== "GET") return route.fallback();
    return route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(SERVOS_LIST),
    });
  });

  // GET/PATCH /tech-lab/servos/{id}
  await page.route(
    new RegExp(`:${API_PORT}/tech-lab/servos/\\d+$`),
    (route) => {
      const method = route.request().method();
      if (method !== "GET" && method !== "PATCH") return route.fallback();
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(SERVO),
      });
    },
  );
}

test.describe("Transformation servos screenshots", () => {
  test("1 — custom servos tab", async ({ page }) => {
    await applyTheme(page);
    await stubServoRoutes(page);
    await page.setViewportSize({ width: 1600, height: 900 });
    await page.goto("/tech-lab/servos");

    await expect(
      page.getByRole("heading", { level: 4, name: "Transformation Servos" }),
    ).toBeVisible();
    // The custom servos tab is the default landing tab.
    await expect(
      page.locator('[data-tab-panel="servos"] table tbody tr'),
    ).toHaveCount(2);
    await pinForCapture(page);

    await capture(
      page,
      FEATURE,
      "misp-workbench-1_tech-lab_transformation-servos_index",
      { fullPage: true },
    );
  });

  test("2 — system pipelines tab", async ({ page }) => {
    await applyTheme(page);
    await stubServoRoutes(page);
    await page.setViewportSize({ width: 1600, height: 1000 });
    await page.goto("/tech-lab/servos");

    await page.getByRole("button", { name: /System pipelines/ }).click();
    // Deep-linkable: switching tabs puts it in the query string.
    await expect(page).toHaveURL(/\?tab=system/);

    // Expand the final pipeline so the capture shows a read-only definition.
    await page.getByRole("button", { name: /misp-attributes_final/ }).click();
    await expect(page.locator("pre").first()).toContainText(
      "misp-attributes_servos",
      { timeout: 10_000 },
    );
    await pinForCapture(page);

    await capture(
      page,
      FEATURE,
      "misp-workbench-2_tech-lab_transformation-servos_system-pipelines",
      { fullPage: true },
    );
  });

  test("3 — backfill tab", async ({ page }) => {
    await applyTheme(page);
    await stubServoRoutes(page);
    await page.setViewportSize({ width: 1600, height: 1100 });
    await page.goto("/tech-lab/servos?tab=backfill");

    await expect(page.getByRole("button", { name: /Backfill/ })).toBeVisible();

    // Fill the filter and preview it, so the capture shows the count and the
    // servo list an operator sees before confirming rather than an empty form.
    await page.locator("input.font-monospace").fill("type:url");
    await page.getByRole("button", { name: "check" }).click();
    await expect(page.getByText(/attributes would be rewritten/)).toBeVisible({
      timeout: 10_000,
    });
    // Run history: one running, one success, one failed.
    await expect(
      page.locator('[data-tab-panel="backfill"] table tbody tr'),
    ).toHaveCount(3);
    // The tab badge counts runs, not pipelines -- it silently showed the
    // system-pipeline count until this pinned it.
    await expect(
      page.getByRole("button", { name: /Backfill/ }).locator(".badge"),
    ).toHaveText("3");
    await pinForCapture(page);

    await capture(
      page,
      FEATURE,
      "misp-workbench-3_tech-lab_transformation-servos_backfill",
      { fullPage: true },
    );
  });

  test("4 — servo editor with a dry run", async ({ page }) => {
    await applyTheme(page);
    await stubServoRoutes(page);
    // The editor is two dense columns: form + JSON editor beside the dry-run
    // panel. A tall viewport keeps both whole in the capture.
    await page.setViewportSize({ width: 1600, height: 1600 });
    await page.goto("/tech-lab/servos/add");

    await expect(
      page.getByRole("heading", { name: "New Transformation Servo" }),
    ).toBeVisible();

    await page.getByRole("button", { name: /start from a template/i }).click();
    await page.getByRole("button", { name: /URL parts/ }).click();
    await page.getByRole("button", { name: /dry run/i }).click();

    await expect(
      page.getByText("OpenSearch accepted these processors."),
    ).toBeVisible({ timeout: 10_000 });
    await pinForCapture(page);

    await capture(
      page,
      FEATURE,
      "misp-workbench-4_tech-lab_transformation-servos_editor",
      { fullPage: true },
    );
  });

  test("5 — servo detail", async ({ page }) => {
    await applyTheme(page);
    await stubServoRoutes(page);
    await page.setViewportSize({ width: 1600, height: 1200 });
    await page.goto(`/tech-lab/servos/${SERVO_ID}`);

    await expect(page.getByRole("heading", { name: SERVO.name })).toBeVisible();
    await expect(page.getByText("servo_url_parts")).toBeVisible();
    await pinForCapture(page);

    await capture(
      page,
      FEATURE,
      "misp-workbench-5_tech-lab_transformation-servos_view",
      { fullPage: true },
    );
  });
});
