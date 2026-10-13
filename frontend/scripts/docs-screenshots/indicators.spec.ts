import { test, expect, Page } from "@playwright/test";
import { applyTheme, capture, pinForCapture } from "./helpers";
import { EVENT_UUIDS } from "./fixtures";
import {
  INDICATORS_PAGE,
  INDICATORS_STATUS,
  scoreFor,
} from "./indicators-fixtures";

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

  test("3 — scores on an event's attributes", async ({ page }) => {
    // Scores come from indicators a dev instance may not have built.
    await page.route(new RegExp(`:${API_PORT}/indicators/scores$`), (route) => {
      const { attributes } = route.request().postDataJSON();
      return route.fulfill(
        json({
          scores: attributes.map(
            (a: { type: string; value: string }, i: number) => {
              const score = scoreFor(a.type, a.value);
              return {
                uuid: `00000000-0000-5000-8000-${String(i).padStart(12, "0")}`,
                score,
                score_breakdown: [
                  { factor: "base", points: 70, detail: "local source" },
                  {
                    factor: "decay",
                    points: score - 70,
                    detail: "since last seen",
                  },
                ],
                scored_at: null,
              };
            },
          ),
        }),
      );
    });
    await page.setViewportSize({ width: 1600, height: 1100 });
    await page.goto(`/events/${EVENT_UUIDS.cobaltStrike}/attributes`);
    const table = page
      .locator('[data-tab-panel="attributes"] .table-responsive')
      .first();
    await expect(table.locator("td.value .score-badge").first()).toBeVisible();
    await pinForCapture(page);

    await capture(
      table,
      FEATURE,
      "misp-workbench-3_indicators_attribute-scores",
    );
  });

  test("4 — scoring settings", async ({ page }) => {
    await page.setViewportSize({ width: 1400, height: 2600 });
    await page.goto("/settings/runtime");
    await page.getByRole("button", { name: /^scoring$/i }).click();
    const form = page.locator(".accordion-item", {
      hasText: "Score indicators",
    });
    await expect(form.getByText("Half-life by attribute type")).toBeVisible();
    await pinForCapture(page);

    await capture(
      form,
      FEATURE,
      "misp-workbench-4_indicators_scoring-settings",
    );
  });
});
