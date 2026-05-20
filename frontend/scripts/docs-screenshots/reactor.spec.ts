import { test, expect, Page } from "@playwright/test";
import { applyTheme, capture, pinForCapture } from "./helpers";
import {
  SCRIPT,
  SCRIPT_ID,
  SCRIPT_SOURCE,
  SCRIPTS_LIST,
  RUNS_PAGE,
  RUN_LOG,
  RUN_FLAME_TREE,
  TEST_RUN_RESPONSE,
} from "./reactor-fixtures";

const FEATURE = "tech-lab/reactor-scripts";

// API host port (matches VITE_API_URL in frontend/.env). Required because the
// Vue route /tech-lab/reactor/:id collides with /tech-lab/reactor/scripts/{id}
// at the path level; anchoring on port keeps SPA navigations untouched.
const API_PORT = 8080;

async function stubReactorRoutes(page: Page) {
  // GET /tech-lab/reactor/scripts/?... → list (used by index page; harmless
  // if also requested elsewhere)
  await page.route(
    new RegExp(`:${API_PORT}/tech-lab/reactor/scripts/\\?`),
    (route) => {
      if (route.request().method() !== "GET") return route.fallback();
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(SCRIPTS_LIST),
      });
    },
  );

  // GET /tech-lab/reactor/scripts/{id}/source
  await page.route(
    new RegExp(`:${API_PORT}/tech-lab/reactor/scripts/\\d+/source$`),
    (route) => {
      if (route.request().method() !== "GET") return route.fallback();
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ source: SCRIPT_SOURCE }),
      });
    },
  );

  // GET /tech-lab/reactor/scripts/{id}/runs?...
  await page.route(
    new RegExp(`:${API_PORT}/tech-lab/reactor/scripts/\\d+/runs\\?`),
    (route) => {
      if (route.request().method() !== "GET") return route.fallback();
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(RUNS_PAGE),
      });
    },
  );

  // GET/PATCH /tech-lab/reactor/scripts/{id}
  await page.route(
    new RegExp(`:${API_PORT}/tech-lab/reactor/scripts/\\d+$`),
    (route) => {
      const method = route.request().method();
      if (method !== "GET" && method !== "PATCH") return route.fallback();
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(SCRIPT),
      });
    },
  );

  // POST /tech-lab/reactor/scripts/{id}/test (optionally ?profile=true)
  await page.route(
    new RegExp(`:${API_PORT}/tech-lab/reactor/scripts/\\d+/test`),
    (route) => {
      if (route.request().method() !== "POST") return route.fallback();
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(TEST_RUN_RESPONSE),
      });
    },
  );

  // GET /tech-lab/reactor/runs/{id}/log
  await page.route(
    new RegExp(`:${API_PORT}/tech-lab/reactor/runs/\\d+/log$`),
    (route) => {
      if (route.request().method() !== "GET") return route.fallback();
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ log: RUN_LOG }),
      });
    },
  );

  // GET /tech-lab/reactor/runs/{id}/profile
  await page.route(
    new RegExp(`:${API_PORT}/tech-lab/reactor/runs/\\d+/profile$`),
    (route) => {
      if (route.request().method() !== "GET") return route.fallback();
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ tree: RUN_FLAME_TREE }),
      });
    },
  );
}

async function gotoEditPage(page: Page) {
  await applyTheme(page);
  await stubReactorRoutes(page);
  // The edit page is dense — name/desc + triggers card + 1000px code editor
  // alongside a 1000px test sandbox. Set a tall viewport so everything fits.
  await page.setViewportSize({ width: 1600, height: 2400 });
  await page.goto(`/tech-lab/reactor/update/${SCRIPT_ID}`);
  await expect(
    page.getByRole("heading", { name: "Edit Reactor Script" }),
  ).toBeVisible();
  // Wait until the source has been pulled in
  await expect(page.getByText("if payload.get").first()).toBeVisible({
    timeout: 10_000,
  });
  await pinForCapture(page);
}

test.describe("Reactor scripts screenshots", () => {
  test("1 — edit script with test run + flame chart", async ({ page }) => {
    await gotoEditPage(page);

    // Enable the profile switch so the flame chart renders.
    await page.locator("#reactor-test-profile").check();
    // Click Run — saveAndTest patches the script then posts to /test, then
    // fetches log, then fetches profile. All four routes are stubbed.
    await page.getByRole("button", { name: /^Run$/ }).click();

    // Wait for the run result to land: status badge + log + flame chart svg.
    await expect(page.locator(".reactor-log").first()).toContainText(
      "mmdb_lookup 8.8.8.8 geolocation.country",
      { timeout: 10_000 },
    );
    // d3-flame-graph injects an <svg> inside .reactor-flame-chart once it
    // has the tree + container width.
    await expect(page.locator(".reactor-flame-chart svg")).toBeVisible({
      timeout: 10_000,
    });
    await pinForCapture(page);

    await capture(
      page,
      FEATURE,
      "misp-workbench-1_tech-lab_reactor-scripts_edit",
      { fullPage: true },
    );
  });

  test("2 — view script with run history", async ({ page }) => {
    await applyTheme(page);
    await stubReactorRoutes(page);
    await page.setViewportSize({ width: 1600, height: 2800 });
    await page.goto(`/tech-lab/reactor/${SCRIPT_ID}`);

    await expect(
      page.getByRole("heading", { name: SCRIPT.name }),
    ).toBeVisible();
    // Wait until the runs accordion has rendered at least a dozen entries
    await expect(page.locator(".accordion-item").nth(20)).toBeVisible({
      timeout: 10_000,
    });
    await pinForCapture(page);

    await capture(
      page,
      FEATURE,
      "misp-workbench-2_tech-lab_reactor-scripts_view",
      { fullPage: true },
    );
  });

  test("3 — reference modal (Docs tab)", async ({ page }) => {
    await gotoEditPage(page);

    // Open the reference modal via the "reference" button in the editor header.
    await page.getByRole("button", { name: /reference/i }).click();
    const modal = page.locator("#ctxDocsModal");
    await expect(modal).toBeVisible();
    await expect(
      modal.getByRole("heading", { name: /Reactor Scripts reference/i }),
    ).toBeVisible();
    // Docs tab is default — verify the parameter table is rendered
    await expect(
      modal.getByText("handle(ctx, payload, trigger)"),
    ).toBeVisible();
    await pinForCapture(page);

    await capture(
      modal.locator(".modal-content"),
      FEATURE,
      "misp-workbench-3_tech-lab_reactor-scripts_reference_docs",
    );
  });

  test("4 — reference modal (Library tab)", async ({ page }) => {
    await gotoEditPage(page);

    await page.getByRole("button", { name: /reference/i }).click();
    const modal = page.locator("#ctxDocsModal");
    await expect(modal).toBeVisible();
    // Click the Library tab
    await modal.getByRole("button", { name: /^Library$/ }).click();
    // Open the Attribute category accordion and pick the first example.
    await modal.getByRole("button", { name: /^Attribute/ }).click();
    await modal
      .getByRole("button", { name: /Tag suspicious IPs amber/ })
      .click();
    // The selected example shows the "Use as starting point" button + code
    await expect(
      modal.getByRole("button", { name: /Use as starting point/ }),
    ).toBeVisible();
    await pinForCapture(page);

    await capture(
      modal.locator(".modal-content"),
      FEATURE,
      "misp-workbench-4_tech-lab_reactor-scripts_reference_library",
    );
  });
});
