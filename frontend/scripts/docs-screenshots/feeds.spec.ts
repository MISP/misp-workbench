import { test, expect, Page } from "@playwright/test";
import { applyTheme, capture, pinForCapture } from "./helpers";

const FEATURE = "feeds";

type FeedType = "MISP Format" | "CSV" | "Freetext" | "JSON";

/**
 * Install canned responses for the /feeds/{type}/preview endpoints. The
 * dev stack can't reach the example URLs we fill into the form, and we'd
 * rather not pin tests to live third-party feeds. The shapes here mirror
 * what api/app/repositories/feeds.py returns (see preview_csv_feed,
 * preview_json_feed, test_misp_feed_connection in routers/feeds.py).
 */
async function stubFeedPreviewRoutes(page: Page) {
  await page.route("**/feeds/misp/test-connection", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        message: "Feed reachable. 412 events found in manifest.",
        total_events: 412,
        total_filtered_events: 38,
      }),
    }),
  );

  await page.route("**/feeds/csv/preview", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        result: "success",
        rows: [
          ["indicator", "type", "comment"],
          ["1.2.3.4", "ip-dst", "C2 server"],
          ["evil.example.com", "domain", "Phishing domain"],
          ["5d41402abc4b2a76b9719d911017c592", "md5", "Loader sample"],
          ["http://payment.fake-banking.com/transfer", "url", "Drop URL"],
        ],
        preview: [
          { value: "1.2.3.4", type: "ip-dst", comment: "C2 server" },
          {
            value: "evil.example.com",
            type: "domain",
            comment: "Phishing domain",
          },
          {
            value: "5d41402abc4b2a76b9719d911017c592",
            type: "md5",
            comment: "Loader sample",
          },
          {
            value: "http://payment.fake-banking.com/transfer",
            type: "url",
            comment: "Drop URL",
          },
        ],
      }),
    }),
  );

  await page.route("**/feeds/json/preview", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        result: "success",
        items: [
          {
            value: "1.2.3.4",
            type: "ip-dst",
            tags: ["tlp:white"],
            first_seen: "2026-05-01T10:14:22Z",
          },
          {
            value: "evil.example.com",
            type: "domain",
            tags: ["tlp:white"],
            first_seen: "2026-05-02T09:01:11Z",
          },
          {
            value: "5d41402abc4b2a76b9719d911017c592",
            type: "md5",
            tags: ["tlp:amber"],
            first_seen: "2026-05-03T18:42:00Z",
          },
        ],
        preview: [
          { value: "1.2.3.4", type: "ip-dst" },
          { value: "evil.example.com", type: "domain" },
          { value: "5d41402abc4b2a76b9719d911017c592", type: "md5" },
        ],
      }),
    }),
  );

  await page.route("**/feeds/freetext/preview", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        result: "success",
        preview: [
          { value: "1.2.3.4", type: "ip-src" },
          { value: "evil.example.com", type: "domain" },
          { value: "CVE-2024-3400", type: "vulnerability" },
        ],
      }),
    }),
  );
}

/**
 * Open /feeds/add and (optionally) click a FeedTypeSelector card so the
 * type-specific form section renders. The selector cards are labeled with
 * the literal text inside an <h6> (e.g. "MISP Format", "CSV", "JSON",
 * "Freetext").
 */
async function openAddFeed(page: Page, type?: FeedType): Promise<void> {
  await applyTheme(page);
  await stubFeedPreviewRoutes(page);
  // Tall viewport — the form has multiple cards stacked (FeedTypeSelector +
  // Feed Settings + type-specific section). Default 1000px crops the bottom.
  await page.setViewportSize({ width: 1600, height: 1700 });
  await page.goto("/feeds/add");
  await expect(page.getByRole("heading", { name: "Add Feed" })).toBeVisible();
  if (type) {
    await page.locator(".feed-type-card", { hasText: type }).click();
  }
  await pinForCapture(page);
}

async function fillBaseFeedConfig(page: Page) {
  // Fill enough of the base form that the form looks lived-in in the shot,
  // and previews don't error on empty URL fields.
  const settings = page.locator(".card", { hasText: "Feed Settings" }).first();
  await settings
    .locator('input[id*="name"], input[placeholder*="Name" i]')
    .first()
    .fill("Example threat feed")
    .catch(() => undefined);
  await settings
    .locator('input[id*="provider"], input[placeholder*="Provider" i]')
    .first()
    .fill("ExampleProvider")
    .catch(() => undefined);
  await settings
    .locator('input[id*="url"], input[placeholder*="URL" i]')
    .first()
    .fill("https://example.org/feed/manifest.json")
    .catch(() => undefined);
}

test.describe("Feeds screenshots", () => {
  test("index — Select from defaults picker", async ({ page }) => {
    await openAddFeed(page);
    await page.getByRole("button", { name: /select from defaults/i }).click();
    await expect(
      page.getByRole("button", { name: /hide defaults/i }),
    ).toBeVisible();
    await pinForCapture(page);
    await capture(page, FEATURE, "misp-workbench-1_default-feeds");
  });

  test("misp 1 — MISP feed type form", async ({ page }) => {
    await openAddFeed(page, "MISP Format");
    await fillBaseFeedConfig(page);
    await pinForCapture(page);
    await capture(page, FEATURE, "misp-workbench-2_misp-feed");
  });

  test("misp 2 — MISP feed rules card", async ({ page }) => {
    await openAddFeed(page, "MISP Format");
    const rules = page.locator(".card", { hasText: "MISP Feed Rules" }).first();
    await expect(rules).toBeVisible();
    await capture(rules, FEATURE, "misp-workbench-3_misp-feed-rules");
  });

  test("csv 1 — CSV feed type form", async ({ page }) => {
    await openAddFeed(page, "CSV");
    await fillBaseFeedConfig(page);
    await pinForCapture(page);
    await capture(page, FEATURE, "misp-workbench-1_csv-feed");
  });

  test("csv 3 — CSV value mapping card", async ({ page }) => {
    await openAddFeed(page, "CSV");
    const mapping = page
      .locator(".card", { hasText: "Attribute Mapping" })
      .first();
    await expect(mapping).toBeVisible();
    await capture(mapping, FEATURE, "misp-workbench-3_csv-feed-value-mapping");
  });

  test("csv 4 — CSV advanced value mapping", async ({ page }) => {
    await openAddFeed(page, "CSV");
    const advancedToggle = page.getByRole("button", {
      name: /advanced property mappings/i,
    });
    await advancedToggle.click();
    // Bootstrap collapse animates open; wait for the collapse container to
    // expose its content.
    await expect(page.locator("#advancedCardBody")).toHaveClass(/show/);
    await pinForCapture(page);
    const mapping = page
      .locator(".card", { hasText: "Attribute Mapping" })
      .first();
    await capture(
      mapping,
      FEATURE,
      "misp-workbench-4_csv-feed-advanced-value-mapping",
    );
  });

  test("json 1 — JSON feed type form", async ({ page }) => {
    await openAddFeed(page, "JSON");
    await fillBaseFeedConfig(page);
    await pinForCapture(page);
    await capture(page, FEATURE, "misp-workbench-1_json-feed");
  });

  test("json 4 — JSON attribute mapping card", async ({ page }) => {
    await openAddFeed(page, "JSON");
    const mapping = page
      .locator(".card", { hasText: "Attribute Mapping" })
      .first();
    await expect(mapping).toBeVisible();
    await capture(
      mapping,
      FEATURE,
      "misp-workbench-4_json-feed-attribute-mapping",
    );
  });

  test("freetext 1 — Freetext feed type form", async ({ page }) => {
    await openAddFeed(page, "Freetext");
    await fillBaseFeedConfig(page);
    await pinForCapture(page);
    await capture(page, FEATURE, "misp-workbench-1_freetext-feed");
  });

  test("freetext 2 — Freetext settings card", async ({ page }) => {
    await openAddFeed(page, "Freetext");
    const card = page
      .locator(".card", { hasText: "Freetext Settings" })
      .first();
    await expect(card).toBeVisible();
    await capture(card, FEATURE, "misp-workbench-2_freetext-feed-settings");
  });

  test("misp 4 — MISP feed preview modal", async ({ page }) => {
    await openAddFeed(page, "MISP Format");
    await fillBaseFeedConfig(page);
    await page.getByRole("button", { name: /^preview$/i }).click();

    const modal = page.locator(".preview-modal");
    await expect(modal).toBeVisible();
    await expect(modal.getByText(/total events in feed/i)).toBeVisible();
    await pinForCapture(page);

    await capture(modal, FEATURE, "misp-workbench-4_misp-feed-preview");
  });

  test("csv 2 — CSV feed preview modal", async ({ page }) => {
    await openAddFeed(page, "CSV");
    await fillBaseFeedConfig(page);
    await page.getByRole("button", { name: /^preview$/i }).click();

    const modal = page.locator(".test-modal");
    await expect(modal).toBeVisible();
    await expect(modal.getByText("CSV Feed Test Result")).toBeVisible();
    // Wait for the row table to render
    await expect(modal.locator("table tbody tr").first()).toBeVisible();
    await pinForCapture(page);

    await capture(modal, FEATURE, "misp-workbench-2_csv-feed-preview");
  });

  test("json 2 — JSON preview card (no items_path)", async ({ page }) => {
    await openAddFeed(page, "JSON");
    await fillBaseFeedConfig(page);

    const previewCard = page
      .locator(".card", { hasText: "JSON Preview" })
      .first();
    await previewCard.getByRole("button", { name: /reload preview/i }).click();
    await expect(previewCard.getByText(/first .* items?/i)).toBeVisible({
      timeout: 10_000,
    });
    await pinForCapture(page);

    await capture(previewCard, FEATURE, "misp-workbench-2_json-feed-preview");
  });

  test("json 3 — JSON preview card with items_path filled", async ({
    page,
  }) => {
    await openAddFeed(page, "JSON");
    await fillBaseFeedConfig(page);

    const previewCard = page
      .locator(".card", { hasText: "JSON Preview" })
      .first();
    // Fill items_path then trigger preview via Enter (the input handles
    // @keyup.enter="loadPreview").
    const itemsPath = previewCard
      .locator(
        'input[placeholder*="items_path" i], input[placeholder*="data.indicators" i]',
      )
      .first();
    await itemsPath.fill("data.indicators");
    await itemsPath.press("Enter");

    // Wait for the preview list to render (it shows "First N items …").
    await expect(previewCard.getByText(/first .* items?/i)).toBeVisible({
      timeout: 10_000,
    });
    await pinForCapture(page);

    await capture(
      previewCard,
      FEATURE,
      "misp-workbench-3_json-feed-preview-with-json-path",
    );
  });
});
