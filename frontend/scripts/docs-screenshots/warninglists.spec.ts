import { test, expect, Page } from "@playwright/test";
import { applyTheme, capture, pinForCapture } from "./helpers";
import { EVENT_UUIDS } from "./fixtures";
import {
  WARNINGLISTS,
  CHECK_RESULT,
  WARNINGLISTED_ATTRIBUTES,
} from "./warninglists-fixtures";

const FEATURE = "warninglists";
const API_PORT = 8080;

async function stubNotifications(page: Page) {
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
}

test.describe("Warninglists screenshots", () => {
  test.beforeEach(async ({ page }) => {
    await applyTheme(page);
    await stubNotifications(page);
  });

  test("1 — warninglists page with a value check", async ({ page }) => {
    await page.route(new RegExp(`:${API_PORT}/warninglists/$`), (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(WARNINGLISTS),
      }),
    );
    await page.route(new RegExp(`:${API_PORT}/warninglists/check$`), (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(CHECK_RESULT),
      }),
    );

    await page.setViewportSize({ width: 1600, height: 1600 });
    await page.goto("/settings/warninglists");
    await expect(page.getByText("List of RFC 1918 CIDR blocks")).toBeVisible();
    await page.fill(
      "#warninglist-check",
      "8.8.8.8 www.google.com 10.0.0.5 phish-login-update.xyz",
    );
    await page.getByRole("button", { name: "Check", exact: true }).click();
    await expect(page.getByText(/not on any enabled list/)).toBeVisible();
    await pinForCapture(page);

    await capture(
      page.locator(".card").first(),
      FEATURE,
      "misp-workbench-1_warninglists_page",
    );
  });

  test("2 — flagged attributes in an event", async ({ page }) => {
    const extra = WARNINGLISTED_ATTRIBUTES.map((a, i) => ({
      uuid: `f1a90000-0001-4001-8000-00000000000${i + 1}`,
      event_uuid: EVENT_UUIDS.phishing,
      category: "Network activity",
      to_ids: true,
      deleted: false,
      disable_correlation: false,
      distribution: 5,
      timestamp: Math.floor(Date.now() / 1000) - 3600,
      tags: [],
      ...a,
    }));

    // Warninglist hits are computed by a background job the screenshot
    // environment doesn't run: append flagged attributes to the event's real
    // ones, and keep the tab's count in step.
    await page.route(
      new RegExp(
        `:${API_PORT}/attributes/\\?.*event_uuid=${EVENT_UUIDS.phishing}`,
      ),
      async (route) => {
        const response = await route.fetch();
        const page_ = await response.json();
        page_.items = [...(page_.items ?? []), ...extra];
        page_.total = (page_.total ?? 0) + extra.length;
        return route.fulfill({ response, json: page_ });
      },
    );
    await page.route(
      new RegExp(`:${API_PORT}/events/${EVENT_UUIDS.phishing}$`),
      async (route) => {
        if (route.request().method() !== "GET") return route.fallback();
        const response = await route.fetch();
        const event = await response.json();
        event.attribute_count = (event.attribute_count ?? 0) + extra.length;
        return route.fulfill({ response, json: event });
      },
    );

    await page.goto(`/events/${EVENT_UUIDS.phishing}/attributes`);
    const table = page
      .locator('[data-tab-panel="attributes"] .table-responsive')
      .first();
    // The value cell, not the row's (hidden) enrich modal holding it too.
    await expect(
      table.locator("td.value", { hasText: "www.google.com" }),
    ).toBeVisible();
    await expect(table.locator("td.value .badge").first()).toBeVisible();
    await pinForCapture(page);

    await capture(
      table,
      FEATURE,
      "misp-workbench-2_warninglists_flagged-attributes",
    );
  });
});
