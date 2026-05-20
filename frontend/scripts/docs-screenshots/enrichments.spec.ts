import { test, expect, Page } from "@playwright/test";
import { applyTheme, capture, pinForCapture } from "./helpers";
import { EVENT_UUIDS } from "./fixtures";

const FEATURE = "enrichments";

const COBALT_FIRST_ATTRIBUTE_UUID = "b2f30000-0001-4002-8000-000000000001";
const SHODAN_OBJECT_UUID = "2e568367-1621-48cc-8224-06b2b3051823";

/**
 * Modules returned by GET /modules/. The dev stack doesn't run misp-modules
 * by default and we don't want screenshots to depend on whichever modules
 * happen to be deployed there, so we stub the whole /modules/* surface and
 * pin a tiny known set.
 *
 * Order matters: the listing screenshot expects nextcloud_talk and slack at
 * the top. shodan stays in the set so it shows up in the enrich modal
 * (filtered by enabled=true) and on /settings/modules for the configure /
 * query screenshots.
 */
const FAKE_MODULES = [
  {
    name: "nextcloud_talk",
    type: "action",
    misp_attributes: { input: ["text"], output: [], format: "misp_standard" },
    meta: {
      version: "0.1",
      author: "Jeroen Pinoy",
      description:
        "Simplistic module to send a message to a Nextcloud talk conversation.",
      module_type: ["action"],
      config: ["nextcloudUrl", "user", "password", "roomToken"],
    },
    enabled: false,
    config: null,
  },
  {
    name: "slack",
    type: "action",
    misp_attributes: { input: ["text"], output: [], format: "misp_standard" },
    meta: {
      version: "0.1",
      author: "goodlandsecurity",
      description: "Simplistic module to send messages to a Slack channel.",
      module_type: ["action"],
      config: ["slack_bot_token", "channel_id"],
    },
    enabled: false,
    config: null,
  },
  {
    name: "shodan",
    type: "expansion",
    misp_attributes: {
      input: ["ip-src", "ip-dst"],
      output: ["ip-src", "ip-dst", "text"],
      format: "misp_standard",
    },
    meta: {
      version: "0.2",
      author: "Raphaël Vinot",
      description: "Module to query on Shodan.",
      module_type: ["expansion"],
      config: ["apikey"],
    },
    enabled: true,
    config: { apikey: "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx" },
  },
];

/**
 * Shodan-style enrichment response. Shape matches what EnrichAttributeModal
 * reads (`response.results.{Attribute, Object}`); QueryModuleModal just
 * stringifies whatever comes back, so the same payload feeds both screens.
 */
function shodanQueryResponse(attributeUuid: string) {
  return {
    results: {
      Attribute: [],
      Object: [
        {
          uuid: SHODAN_OBJECT_UUID,
          name: "ip-api-address",
          "meta-category": "network",
          template_uuid: "4336f124-6264-4f72-943e-cc3797e4122b",
          description:
            "IP Address information. Useful if you are pulling your ip information from ip-api.com",
          template_version: "2",
          ObjectReference: [
            {
              uuid: "b6e0e0d2-1111-2222-3333-444444444444",
              object_uuid: SHODAN_OBJECT_UUID,
              referenced_uuid: attributeUuid,
              relationship_type: "describes",
            },
          ],
          Attribute: [
            {
              uuid: "c1000000-0000-0000-0000-000000000001",
              value: "AS15169",
              type: "AS",
              to_ids: false,
              disable_correlation: true,
            },
            {
              uuid: "c1000000-0000-0000-0000-000000000002",
              value: "Mountain View",
              type: "text",
              to_ids: false,
              disable_correlation: true,
            },
            {
              uuid: "c1000000-0000-0000-0000-000000000003",
              value: "US",
              type: "text",
              to_ids: false,
              disable_correlation: true,
            },
            {
              uuid: "c1000000-0000-0000-0000-000000000004",
              value: "United States",
              type: "text",
              to_ids: false,
              disable_correlation: true,
            },
            {
              uuid: "c1000000-0000-0000-0000-000000000005",
              value: "Google LLC",
              type: "text",
              to_ids: false,
              disable_correlation: true,
            },
            {
              uuid: "c1000000-0000-0000-0000-000000000006",
              value: "38.00881",
              type: "float",
              to_ids: false,
              disable_correlation: true,
            },
            {
              uuid: "c1000000-0000-0000-0000-000000000007",
              value: "-122.11746",
              type: "float",
              to_ids: false,
              disable_correlation: true,
            },
            {
              uuid: "c1000000-0000-0000-0000-000000000008",
              value: "Google LLC",
              type: "text",
              to_ids: false,
              disable_correlation: true,
            },
            {
              uuid: "c1000000-0000-0000-0000-000000000009",
              value: "CA",
              type: "text",
              to_ids: false,
              disable_correlation: true,
            },
          ],
        },
      ],
    },
  };
}

/**
 * Stub every /modules/* endpoint the frontend talks to so screenshots don't
 * depend on a live misp-modules. Playwright matches routes in reverse
 * registration order (last-added wins), so register the broadest match
 * first and narrow down — POST /modules/query must override the generic
 * /modules/{name} handler.
 */
async function stubModuleRoutes(page: Page, attributeUuid: string) {
  // Anchor on `:<port>/modules` so we don't intercept the Vue route
  // `/settings/modules` (the SPA navigation also fires an HTML fetch
  // whose URL ends in `/modules` and would otherwise match).

  // GET /modules and /modules/?enabled=...
  await page.route(/:\d+\/modules\/?(\?.*)?$/, (route) => {
    if (route.request().method() !== "GET") return route.fallback();
    const url = route.request().url();
    const onlyEnabled = /enabled=true/i.test(url);
    const body = onlyEnabled
      ? FAKE_MODULES.filter((m) => m.enabled)
      : FAKE_MODULES;
    return route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(body),
    });
  });

  // PATCH /modules/{name} — accept config/enabled updates silently
  await page.route(/:\d+\/modules\/[^/?]+$/, (route) => {
    if (route.request().method() !== "PATCH") return route.fallback();
    return route.fulfill({
      status: 200,
      contentType: "application/json",
      body: "{}",
    });
  });

  // POST /modules/query — registered LAST so it wins over /modules/{name}
  await page.route(/:\d+\/modules\/query$/, (route) => {
    return route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(shodanQueryResponse(attributeUuid)),
    });
  });
}

/**
 * Locate the AttributesIndex card on an event view. The outer event card
 * also wraps a .table-responsive-sm (via this same component), so
 * `:has()` matches two nested elements; the inner (attributes) card is
 * last in DOM order.
 */
function attributesCard(page: Page) {
  return page.locator(".card:has(.table-responsive-sm)").last();
}

async function openEnrichModalOnFirstAttribute(page: Page) {
  await page.goto(`/events/${EVENT_UUIDS.cobaltStrike}`);
  const card = attributesCard(page);
  await expect(card.locator("table tbody tr").first()).toBeVisible();

  // Icon-only button — title= drives the accessible name. Each attribute
  // mounts its own EnrichAttributeModal with id `enrichAttributeModal_{uuid}`,
  // so target the one matching the first attribute deterministically.
  await page
    .locator(`button[title="Enrich Attribute"]`)
    .first()
    .scrollIntoViewIfNeeded();
  await page.locator(`button[title="Enrich Attribute"]`).first().click();

  const modal = page.locator(
    `#enrichAttributeModal_${COBALT_FIRST_ATTRIBUTE_UUID}`,
  );
  await expect(modal).toBeVisible();
  await expect(modal.getByText("enabled modules")).toBeVisible();
  // shodan is the only enabled module in the stub
  await expect(
    modal.locator("table tbody tr", { hasText: "shodan" }),
  ).toBeVisible();
  return modal;
}

/**
 * Shrink the attributes table to a single visible row. The original
 * screenshot framed exactly one row to highlight the action toolbar; with
 * three fixture attributes the row of interest would be lost in a wall of
 * other entries. Hide every row past the first while we capture.
 */
async function showOnlyFirstAttributeRow(page: Page): Promise<void> {
  await page.addStyleTag({
    content: `
      .table-responsive-sm table tbody tr:not(:first-child) {
        display: none !important;
      }
    `,
  });
}

test.describe("Enrichments screenshots", () => {
  test("1 — attribute row with enrich action", async ({ page }) => {
    await applyTheme(page);
    await stubModuleRoutes(page, COBALT_FIRST_ATTRIBUTE_UUID);
    await page.goto(`/events/${EVENT_UUIDS.cobaltStrike}`);

    const card = attributesCard(page);
    await expect(card.locator("table tbody tr").first()).toBeVisible();
    await showOnlyFirstAttributeRow(page);
    await pinForCapture(page);

    await capture(card, FEATURE, "misp-workbench-1_enrichment-attribute");
  });

  test("2 — enrichment modal (pre-query)", async ({ page }) => {
    await applyTheme(page);
    // Modal is modal-xl with attribute card + module table; default 1000px
    // viewport crops the Discard/Add footer.
    await page.setViewportSize({ width: 1600, height: 1400 });
    await stubModuleRoutes(page, COBALT_FIRST_ATTRIBUTE_UUID);

    const modal = await openEnrichModalOnFirstAttribute(page);
    await pinForCapture(page);

    await capture(
      modal.locator(".modal-content"),
      FEATURE,
      "misp-workbench-2_enrichment-modal",
    );
  });

  test("3 — enrichment results", async ({ page }) => {
    await applyTheme(page);
    await page.setViewportSize({ width: 1600, height: 1800 });
    await stubModuleRoutes(page, COBALT_FIRST_ATTRIBUTE_UUID);

    const modal = await openEnrichModalOnFirstAttribute(page);

    // Toggle shodan on (form-switch checkbox in the rightmost cell)
    const shodanRow = modal.locator("table tbody tr", { hasText: "shodan" });
    await shodanRow.locator(".form-check-input").click();

    await modal.getByRole("button", { name: /^query$/i }).click();

    // Wait for the results card to render
    await expect(modal.getByText("AS15169")).toBeVisible({ timeout: 10_000 });
    await expect(modal.getByText("ip-api-address")).toBeVisible();
    await pinForCapture(page);

    // The "preview enrichment results" block lives inside .text-start.m-3
    const resultsSection = modal.locator(".text-start.m-3").first();
    await capture(
      resultsSection,
      FEATURE,
      "misp-workbench-3_enrichment-results",
    );
  });

  test("4 — modules listing", async ({ page }) => {
    await applyTheme(page);
    await stubModuleRoutes(page, COBALT_FIRST_ATTRIBUTE_UUID);
    await page.goto("/settings/modules");

    // First two cards are nextcloud_talk and slack
    await expect(
      page.locator(".card .card-header", { hasText: "nextcloud_talk" }),
    ).toBeVisible();
    await expect(
      page.locator(".card .card-header", { hasText: "slack" }),
    ).toBeVisible();
    await pinForCapture(page);

    await capture(page, FEATURE, "misp-workbench-4_modules");
  });

  test("5 — configure module modal", async ({ page }) => {
    await applyTheme(page);
    await stubModuleRoutes(page, COBALT_FIRST_ATTRIBUTE_UUID);
    await page.goto("/settings/modules");

    // Card titles are <h5 class="card-header">name <badge>v…</badge></h5>;
    // anchor on the header text to pick the shodan card unambiguously.
    const shodanCard = page
      .locator(".card")
      .filter({ has: page.locator("h5.card-header", { hasText: "shodan" }) })
      .first();
    await expect(shodanCard).toBeVisible();
    // "configure" has a trailing count badge in its accessible name; match
    // by substring rather than exact equality.
    await shodanCard.getByRole("button", { name: /configure/i }).click();

    const modal = page.locator("#configureModuleModal");
    await expect(modal).toBeVisible();
    // input is prefilled with the stubbed apikey
    await expect(modal.locator("input#apikey")).toHaveValue(/x+/);
    await pinForCapture(page);

    await capture(
      modal.locator(".modal-content"),
      FEATURE,
      "misp-workbench-5_module-settings",
    );
  });

  test("6 — query module modal", async ({ page }) => {
    await applyTheme(page);
    await stubModuleRoutes(page, COBALT_FIRST_ATTRIBUTE_UUID);
    await page.goto("/settings/modules");

    const shodanCard = page
      .locator(".card")
      .filter({ has: page.locator("h5.card-header", { hasText: "shodan" }) })
      .first();
    await shodanCard.getByRole("button", { name: /^query$/i }).click();

    const modal = page.locator("#queryModuleModal");
    await expect(modal).toBeVisible();
    await expect(modal.locator("textarea#request")).toBeVisible();

    // Run the query (icon-only btn-primary in the footer)
    await modal.locator(".modal-footer .btn-primary").click();

    // The response textarea is bound via v-model to a computed that
    // stringifies the store's moduleResponse — assert on its value
    // attribute (toContainText reads textContent which a <textarea> updates
    // via .value, not children).
    await expect(modal.locator("textarea#response")).toHaveValue(
      /ip-api-address/,
      { timeout: 10_000 },
    );
    await pinForCapture(page);

    await capture(
      modal.locator(".modal-content"),
      FEATURE,
      "misp-workbench-6_module-settings-test",
    );
  });
});
