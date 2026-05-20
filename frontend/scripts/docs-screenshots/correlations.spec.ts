import { test, expect, Page } from "@playwright/test";
import { applyTheme, capture, pinForCapture } from "./helpers";
import { EVENT_UUIDS } from "./fixtures";

const FEATURE = "correlations";

// Pretend the cobalt strike event correlates with the wannacry event — only
// used by the Related Events widget and the per-attribute modal. The actual
// OpenSearch correlation index is not touched.
const SOURCE_EVENT_UUID = EVENT_UUIDS.cobaltStrike;
const SOURCE_ATTRIBUTE_UUID = "b2f30000-0001-4002-8000-000000000001"; // ip-src 185.220.101.42
const CORRELATED_EVENT_UUID = EVENT_UUIDS.wannacry;
const CORRELATED_ATTRIBUTE_UUID = "b2f30000-0001-4002-8000-000000000099";

const FAKE_CORRELATION_HIT = {
  _id: "corr-doc-1",
  _index: "misp-attribute-correlations",
  _score: 1,
  _source: {
    "@timestamp": "2026-05-19T10:59:41.947726+00:00",
    source_attribute_uuid: SOURCE_ATTRIBUTE_UUID,
    source_event_uuid: SOURCE_EVENT_UUID,
    target_attribute_uuid: CORRELATED_ATTRIBUTE_UUID,
    target_attribute_type: "ip-src",
    target_attribute_value: "185.220.101.42",
    target_event_uuid: CORRELATED_EVENT_UUID,
    match_type: "term",
    score: 1,
  },
};

/**
 * Shape returned by GET /correlations/stats — top_correlated_attributes
 * carries the OpenSearch `top_hits` aggregation nested all the way down
 * (hits.hits[0]._source.*) which the index page reaches into directly.
 */
const FAKE_STATS = {
  total_correlations: 2,
  top_correlated_attributes: [
    {
      key: SOURCE_ATTRIBUTE_UUID,
      doc_count: 1,
      top_attribute_info: {
        hits: {
          hits: [
            {
              _source: {
                target_attribute_type: "ip-src",
                target_attribute_value: "185.220.101.42",
                target_event_uuid: CORRELATED_EVENT_UUID,
              },
            },
          ],
        },
      },
    },
    {
      key: CORRELATED_ATTRIBUTE_UUID,
      doc_count: 1,
      top_attribute_info: {
        hits: {
          hits: [
            {
              _source: {
                target_attribute_type: "ip-src",
                target_attribute_value: "185.220.101.42",
                target_event_uuid: SOURCE_EVENT_UUID,
              },
            },
          ],
        },
      },
    },
  ],
  top_correlated_events: [
    { key: CORRELATED_EVENT_UUID, doc_count: 1 },
    { key: SOURCE_EVENT_UUID, doc_count: 1 },
  ],
};

const FAKE_TOP_FOR_COBALT = [{ key: CORRELATED_EVENT_UUID, doc_count: 1 }];

/**
 * Stub /correlations/* endpoints and rewrite GET /attributes/ responses so
 * the cobalt-strike event's first attribute appears to have a correlation
 * (drives the sitemap icon + the modal). The actual API still serves the
 * attribute row data; we only inject the `correlations` field.
 */
async function stubCorrelationRoutes(page: Page) {
  // GET /correlations/stats
  await page.route(/:\d+\/correlations\/stats$/, (route) => {
    if (route.request().method() !== "GET") return route.fallback();
    return route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(FAKE_STATS),
    });
  });

  // GET /correlations/events/{uuid}/top — Related Events widget
  await page.route(/:\d+\/correlations\/events\/[^/]+\/top$/, (route) => {
    if (route.request().method() !== "GET") return route.fallback();
    return route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(FAKE_TOP_FOR_COBALT),
    });
  });

  // Intercept the attributes listing for the cobalt strike event and graft
  // the fake correlation onto the first item. Fall through to the real API
  // for everything else.
  await page.route(/:\d+\/attributes\/\?[^"]*$/, async (route) => {
    if (route.request().method() !== "GET") return route.fallback();
    const url = route.request().url();
    if (!url.includes(`event_uuid=${SOURCE_EVENT_UUID}`)) {
      return route.fallback();
    }
    const response = await route.fetch();
    const json = await response.json();
    if (json?.items?.length) {
      json.items[0].correlations = [FAKE_CORRELATION_HIT];
    }
    return route.fulfill({
      response,
      contentType: "application/json",
      body: JSON.stringify(json),
    });
  });
}

/**
 * Hide everything below the event title + first 3-column row inside the
 * outer event card so only the "Related Events" portion is visible for
 * the event-view screenshot.
 */
async function trimEventViewToHeader(page: Page) {
  await page.addStyleTag({
    content: `
      /* Hide the Reports column that sits inside the same row.m-1 */
      .card > .row.m-1 > .col.col-sm-12 { display: none !important; }
      /* Hide the objects + attributes row beneath */
      .card > .row:not(.m-1) { display: none !important; }
    `,
  });
}

/**
 * Inner attributes card on event view. Same trick as enrichments.spec.ts —
 * `.card:has(.table-responsive-sm)` matches both the outer wrapper and
 * the inner card; the inner one is last in DOM order.
 */
function attributesCard(page: Page) {
  return page.locator(".card:has(.table-responsive-sm)").last();
}

async function showOnlyFirstAttributeRow(page: Page) {
  await page.addStyleTag({
    content: `
      .table-responsive-sm table tbody tr:not(:first-child) {
        display: none !important;
      }
    `,
  });
}

test.describe("Correlations screenshots", () => {
  test("1 — correlations index view", async ({ page }) => {
    await applyTheme(page);
    await stubCorrelationRoutes(page);
    await page.goto("/correlations");

    await expect(
      page.getByRole("heading", { name: "Correlations", exact: true }),
    ).toBeVisible();
    await expect(page.getByText("Top Attribute Correlations")).toBeVisible();
    // Wait for at least one stats row to render
    await expect(
      page.locator("table tbody tr").filter({ hasText: "ip-src" }).first(),
    ).toBeVisible({ timeout: 10_000 });
    await pinForCapture(page);

    await capture(page, FEATURE, "misp-workbench-1_correlations-view");
  });

  test("2 — event view with Related Events", async ({ page }) => {
    await applyTheme(page);
    await stubCorrelationRoutes(page);
    await page.goto(`/events/${SOURCE_EVENT_UUID}`);

    // The outer event card also contains "Related Events" via this widget;
    // .last() picks the inner widget card (DOM order, innermost wins).
    const relatedEvents = page
      .locator(".card")
      .filter({ hasText: "Related Events" })
      .last();
    await expect(relatedEvents).toBeVisible();
    await expect(relatedEvents.getByText(CORRELATED_EVENT_UUID)).toBeVisible({
      timeout: 10_000,
    });

    await trimEventViewToHeader(page);
    await pinForCapture(page);

    // Capture the outer event card (already trimmed by the styles above)
    const eventCard = page.locator(".card").first();
    await capture(
      eventCard,
      FEATURE,
      "misp-workbench-2_correlations-event-view",
    );
  });

  test("3 — attribute row with correlations icon", async ({ page }) => {
    await applyTheme(page);
    await stubCorrelationRoutes(page);
    await page.goto(`/events/${SOURCE_EVENT_UUID}`);

    const card = attributesCard(page);
    await expect(card.locator("table tbody tr").first()).toBeVisible();
    // Wait for the sitemap icon to appear (correlations field populated)
    await expect(
      card.locator("table tbody tr").first().getByTitle("View Correlations"),
    ).toBeVisible({ timeout: 10_000 });

    await showOnlyFirstAttributeRow(page);
    await pinForCapture(page);

    await capture(card, FEATURE, "misp-workbench-3_correlations-attribute-row");
  });

  test("4 — correlation modal", async ({ page }) => {
    await applyTheme(page);
    await stubCorrelationRoutes(page);
    await page.goto(`/events/${SOURCE_EVENT_UUID}`);

    const card = attributesCard(page);
    await expect(card.locator("table tbody tr").first()).toBeVisible();
    const sitemap = card
      .locator("table tbody tr")
      .first()
      .getByTitle("View Correlations");
    await expect(sitemap).toBeVisible({ timeout: 10_000 });
    await sitemap.click();

    const modal = page.locator(
      `#correlatedAttributesModal${SOURCE_ATTRIBUTE_UUID}`,
    );
    await expect(modal).toBeVisible();
    // The modal body lists the correlation; presence of these labels means
    // attribute.correlations was populated and the row rendered.
    await expect(modal.getByText("Match Type:")).toBeVisible({
      timeout: 10_000,
    });
    await expect(modal.getByText("Score:")).toBeVisible();
    await pinForCapture(page);

    await capture(
      modal.locator(".modal-content"),
      FEATURE,
      "misp-workbench-4_correlations-attribute-correlation-modal",
    );
  });
});
