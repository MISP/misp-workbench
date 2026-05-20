import { test, expect, Page } from "@playwright/test";
import { applyTheme, capture, pinForCapture } from "./helpers";
import { NOTEBOOKS, TREE_RESPONSE, USER_ME } from "./notebooks-fixtures";

const FEATURE = "tech-lab/notebooks";

/**
 * Stub the /tech-lab/* surface with canned notebooks. The lab-worker is not
 * required: cell_outputs are pre-populated on each notebook fixture, so the
 * OutputPanel renders them directly without a live kernel.
 *
 * The Vue route `/tech-lab/notebooks/:id` is identical to the API path —
 * a generic `:<port>/tech-lab/...` regex would intercept the SPA HTML
 * navigation too. Anchor on the API port (8080 — matches VITE_API_URL in
 * frontend/.env).
 */
const API_PORT = 8080;

async function stubNotebookRoutes(page: Page) {
  // GET /users/me — workspace component needs the user id for ownership
  await page.route(new RegExp(`:${API_PORT}/users/me$`), (route) => {
    if (route.request().method() !== "GET") return route.fallback();
    return route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(USER_ME),
    });
  });

  // GET /tech-lab/tree
  await page.route(new RegExp(`:${API_PORT}/tech-lab/tree$`), (route) => {
    if (route.request().method() !== "GET") return route.fallback();
    return route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(TREE_RESPONSE),
    });
  });

  // GET /tech-lab/notebooks/{id}
  await page.route(
    new RegExp(`:${API_PORT}/tech-lab/notebooks/\\d+$`),
    (route) => {
      if (route.request().method() !== "GET") return route.fallback();
      const url = route.request().url();
      const match = url.match(/\/notebooks\/(\d+)$/);
      const id = match ? Number(match[1]) : null;
      const nb = id != null ? NOTEBOOKS[id] : null;
      if (!nb) {
        return route.fulfill({ status: 404, body: "{}" });
      }
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(nb),
      });
    },
  );
}

/**
 * Hide the global app navbar for notebook captures. The notebook workspace
 * uses the full viewport minus 56px (navbar) — without trimming, every
 * screenshot has a chunk of unrelated top chrome.
 */
async function hideAppChrome(page: Page) {
  await page.addStyleTag({
    content: `
      nav.navbar { display: none !important; }
      .notebooks-workspace { height: 100vh !important; }
    `,
  });
}

async function openNotebook(page: Page, id: number) {
  await applyTheme(page);
  await stubNotebookRoutes(page);
  // Notebooks are dense — give the editor + outputs enough horizontal and
  // vertical room. The grid is 56px navbar + workspace.
  await page.setViewportSize({ width: 1600, height: 1100 });
  await page.goto(`/tech-lab/notebooks/${id}`);

  const editor = page.locator(".notebook-editor");
  await expect(editor).toBeVisible();
  await expect(
    editor.getByText(NOTEBOOKS[id].name, { exact: true }),
  ).toBeVisible({
    timeout: 10_000,
  });

  // Wait for at least one rendered output (markdown block or output-block)
  // so we don't capture the spinner state.
  await expect(
    page
      .locator(".output-panel .output-block, .output-panel .markdown-block")
      .first(),
  ).toBeVisible({ timeout: 10_000 });

  await hideAppChrome(page);
  await pinForCapture(page);
}

test.describe("Notebooks screenshots", () => {
  test("1 — mmdb_lookup quickstart fork", async ({ page }) => {
    await openNotebook(page, 1);
    await capture(
      page.locator(".notebooks-workspace"),
      FEATURE,
      "misp-workbench-1_tech-lab_notebooks",
    );
  });

  test("2 — search example", async ({ page }) => {
    await openNotebook(page, 2);
    await capture(
      page.locator(".notebooks-workspace"),
      FEATURE,
      "misp-workbench-2_tech-lab_notebooks_search",
    );
  });

  test("3 — geolocation example", async ({ page }) => {
    await openNotebook(page, 3);
    await capture(
      page.locator(".notebooks-workspace"),
      FEATURE,
      "misp-workbench-3_tech-lab_notebooks_geolocation",
    );
  });

  test("4 — timeline example", async ({ page }) => {
    await openNotebook(page, 4);
    await capture(
      page.locator(".notebooks-workspace"),
      FEATURE,
      "misp-workbench-4_tech-lab_notebooks_timeline",
    );
  });

  test("5 — tag cloud example", async ({ page }) => {
    await openNotebook(page, 5);
    await capture(
      page.locator(".notebooks-workspace"),
      FEATURE,
      "misp-workbench-5_tech-lab_notebooks_tag_cloud",
    );
  });

  test("6 — pivot attribute → event example", async ({ page }) => {
    await openNotebook(page, 6);
    await capture(
      page.locator(".notebooks-workspace"),
      FEATURE,
      "misp-workbench-6_tech-lab_notebooks_pivot",
    );
  });
});
