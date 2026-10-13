import { test, expect } from "@playwright/test";
import { applyTheme, capture, pinForCapture } from "./helpers";
import { EVENT_UUIDS } from "./fixtures";

const FEATURE = "normalisation";
const API_PORT = 8080;

// Attributes as normalisation leaves them: rewritten values keep their
// original, problems are flagged. Appended to a fixture event's own.
const NORMALISED = [
  {
    type: "url",
    value: "https://login-update.example.org/verify",
    original_value: "hxxps://Login-Update.EXAMPLE.org:443/verify",
  },
  { type: "ip-dst", value: "10.20.30.40", validation_issues: ["private-ip"] },
  {
    type: "domain",
    value: "c2.evil.example",
    original_value: "c2[.]Evil[.]Example",
  },
  { type: "sha256", value: "abc123", validation_issues: ["invalid-hash"] },
];

test.describe("Normalisation screenshots", () => {
  test.beforeEach(async ({ page }) => {
    await applyTheme(page);
  });

  test("1 — normalised and flagged attributes", async ({ page }) => {
    const extra = NORMALISED.map((a, i) => ({
      uuid: `40a10000-0001-4001-8000-00000000000${i + 1}`,
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

    await page.goto(`/events/${EVENT_UUIDS.phishing}/attributes`);
    const table = page
      .locator('[data-tab-panel="attributes"] .table-responsive')
      .first();
    await expect(
      table.locator("td.value", { hasText: "c2.evil.example" }),
    ).toBeVisible();
    await pinForCapture(page);

    await capture(table, FEATURE, "misp-workbench-1_normalisation_attributes");
  });

  test("2 — normalisation settings", async ({ page }) => {
    await page.setViewportSize({ width: 1400, height: 1800 });
    await page.goto("/settings/runtime");
    await page.getByRole("button", { name: /^normalisation$/i }).click();
    const form = page.locator(".accordion-item", {
      hasText: "Normalise and validate attributes",
    });
    await expect(
      form.getByText("Tracking parameters", { exact: true }),
    ).toBeVisible();
    await pinForCapture(page);

    await capture(form, FEATURE, "misp-workbench-2_normalisation_settings");
  });
});
