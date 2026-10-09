import { test, expect, Page } from "@playwright/test";
import { applyTheme, capture, pinForCapture } from "./helpers";
import { sinksList } from "./sinks-fixtures";

const FEATURE = "sinks";
// Anchoring stubs on the API port keeps SPA navigations to /sinks/* untouched.
const API_PORT = 8080;

async function stubSinkRoutes(page: Page) {
  // Pin the nav's unread-notifications badge so the chrome is reproducible.
  await page.route(
    new RegExp(`:${API_PORT}/notifications\\?read=false`),
    (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          items: [],
          total: 0,
          page: 1,
          size: 1,
          pages: 0,
        }),
      }),
  );
  await page.route(new RegExp(`:${API_PORT}/sinks/$`), (route) => {
    if (route.request().method() !== "GET") return route.fallback();
    return route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(sinksList()),
    });
  });
  await page.route(new RegExp(`:${API_PORT}/sinks/(\\d+)$`), (route) => {
    if (route.request().method() !== "GET") return route.fallback();
    const id = Number(route.request().url().split("/").pop());
    const sink = sinksList().find((s) => s.id === id);
    return route.fulfill({
      status: sink ? 200 : 404,
      contentType: "application/json",
      body: JSON.stringify(sink ?? { detail: "Sink not found" }),
    });
  });
}

test.describe("Sinks screenshots", () => {
  test.beforeEach(async ({ page }) => {
    await applyTheme(page);
    await stubSinkRoutes(page);
  });

  test("1 — sinks list with delivery status", async ({ page }) => {
    await page.goto("/sinks");
    await expect(page.getByText("Splunk production")).toBeVisible();
    await expect(page.getByText(/failing since/i)).toBeVisible();
    await pinForCapture(page);

    await capture(
      page.locator(".card").first(),
      FEATURE,
      "misp-workbench-1_sinks_list",
    );
  });

  test("2 — new Splunk HEC sink", async ({ page }) => {
    await page.setViewportSize({ width: 1200, height: 2000 });
    await page.goto("/sinks/add");
    await page.fill("#sink-name", "Splunk production");
    await page.fill(
      "#sink-url",
      "https://splunk.example.org:8088/services/collector/event",
    );
    await page.fill("#sink-token", "00000000-0000-0000-0000-000000000000");
    await page.fill("#sink-index", "threat_intel");
    await page.fill("#sink-types", "ip-src, ip-dst, domain, url, sha256");
    await pinForCapture(page);

    await capture(
      page.locator(".card").first(),
      FEATURE,
      "misp-workbench-2_sinks_new-splunk-hec",
    );
  });

  test("3 — edit a syslog sink", async ({ page }) => {
    await page.setViewportSize({ width: 1200, height: 2000 });
    await page.goto("/sinks/update/3");
    await expect(page.locator("#sink-name")).toHaveValue("Wazuh syslog");
    await pinForCapture(page);

    await capture(
      page.locator(".card").first(),
      FEATURE,
      "misp-workbench-3_sinks_edit-syslog",
    );
  });
});
