import { test, expect, Page } from "@playwright/test";
import { applyTheme, capture, pinForCapture } from "./helpers";
import { INDICATORS_PAGE, INDICATORS_STATUS } from "./indicators-fixtures";

const FEATURE = "indicators";
const API_PORT = 8080;

function json(body: unknown) {
  return {
    status: 200,
    contentType: "application/json",
    body: JSON.stringify(body),
  };
}

async function stubApi(page: Page) {
  await page.route(new RegExp(`:${API_PORT}/notifications\\?read=false`), (r) =>
    r.fulfill(json({ items: [], total: 0, page: 1, size: 1, pages: 0 })),
  );
  // Served from fixtures: a dev instance's indicators depend on what it holds.
  await page.route(new RegExp(`:${API_PORT}/indicators/status$`), (r) =>
    r.fulfill(json(INDICATORS_STATUS)),
  );
  await page.route(new RegExp(`:${API_PORT}/indicators\\?`), (r) =>
    r.fulfill(json(INDICATORS_PAGE)),
  );
}

test.describe("Indicators screenshots", () => {
  test.beforeEach(async ({ page }) => {
    await applyTheme(page);
    await stubApi(page);
  });

  test("1 — indicators list", async ({ page }) => {
    await page.setViewportSize({ width: 1600, height: 1100 });
    await page.goto("/indicators");
    await expect(page.getByText("c2.example-cobalt.net")).toBeVisible();
    await pinForCapture(page);

    await capture(
      page.locator(".card").first(),
      FEATURE,
      "misp-workbench-1_indicators_list",
    );
  });

  test("2 — an indicator's consolidated context", async ({ page }) => {
    await page.setViewportSize({ width: 1600, height: 1300 });
    await page.goto("/indicators");
    await page.getByText("198.51.100.23").click();
    await expect(page.getByText("Partner CERT (1)")).toBeVisible();
    await pinForCapture(page);

    await capture(
      page.locator(".card").first(),
      FEATURE,
      "misp-workbench-2_indicators_detail",
    );
  });
});
