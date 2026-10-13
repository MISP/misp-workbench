import { test, expect, Page } from "@playwright/test";
import { applyTheme, capture, pinForCapture } from "./helpers";
import { SOURCE_QUALITY } from "./indicators-fixtures";

const FEATURE = "detection-profiles";
const API_PORT = 8080;

const now = new Date("2026-10-13T08:00:00Z").toISOString();
const PROFILES = [
  {
    id: 1,
    name: "SIEM alerting",
    description:
      "Indicators worth alerting on: flagged for IDS, scored 50 or more, not on a warninglist, no validation issues, TLP amber or less.",
    granularity: "indicators",
    rules: {
      types: [],
      categories: [],
      tlp_ceiling: "tlp:amber",
      tags: [],
      exclude_tags: [],
      min_score: 50,
      max_age_days: null,
      sources: [],
      exclude_sources: [],
      organisations: [],
      exclude_organisations: [],
      min_source_trust: null,
      to_ids: true,
      exclude_warninglisted: true,
      exclude_validation_issues: true,
    },
    created_at: now,
    updated_at: null,
  },
  {
    id: 2,
    name: "Firewall block list",
    description:
      "Network indicators safe to block: IPs, domains, hostnames and URLs flagged for IDS, scored 70 or more, seen in the last 90 days.",
    granularity: "indicators",
    rules: {
      types: ["ip-src", "ip-dst", "domain", "hostname", "url"],
      categories: [],
      tlp_ceiling: "tlp:amber",
      tags: [],
      exclude_tags: [],
      min_score: 70,
      max_age_days: 90,
      sources: [],
      exclude_sources: ["feed:3"],
      organisations: [],
      exclude_organisations: [],
      min_source_trust: null,
      to_ids: true,
      exclude_warninglisted: true,
      exclude_validation_issues: true,
    },
    created_at: now,
    updated_at: null,
  },
];
const COUNTS: Record<number, number> = { 1: 8412, 2: 2196 };
const SAMPLE = [
  { uuid: "a", type: "ip-dst", value: "198.51.100.23", score: 89 },
  { uuid: "b", type: "domain", value: "c2.example-cobalt.net", score: 89 },
  {
    uuid: "c",
    type: "url",
    value: "https://login-update.example.org/verify",
    score: 72,
  },
];

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
  await page.route(new RegExp(`:${API_PORT}/detection-profiles$`), (r) =>
    r.fulfill(json(PROFILES)),
  );
  await page.route(
    new RegExp(`:${API_PORT}/detection-profiles/(\\d+)$`),
    (r) => {
      const id = Number(
        r
          .request()
          .url()
          .match(/(\d+)$/)?.[1],
      );
      return r.fulfill(json(PROFILES.find((p) => p.id === id)));
    },
  );
  await page.route(
    new RegExp(`:${API_PORT}/detection-profiles/(\\d+)/count$`),
    (r) => {
      const id = Number(
        r
          .request()
          .url()
          .match(/\/(\d+)\/count$/)?.[1],
      );
      return r.fulfill(json({ count: COUNTS[id] ?? 0, sample: SAMPLE }));
    },
  );
  await page.route(
    new RegExp(`:${API_PORT}/detection-profiles/preview$`),
    (r) => r.fulfill(json({ count: 2196, sample: SAMPLE })),
  );
  await page.route(new RegExp(`:${API_PORT}/indicators/sources$`), (r) =>
    r.fulfill(json(SOURCE_QUALITY)),
  );
}

test.describe("Detection profiles screenshots", () => {
  test.beforeEach(async ({ page }) => {
    await applyTheme(page);
    await stubApi(page);
  });

  test("1 — profiles list", async ({ page }) => {
    await page.setViewportSize({ width: 1600, height: 900 });
    await page.goto("/detection-profiles");
    await expect(page.getByText("8,412")).toBeVisible();
    await pinForCapture(page);
    await capture(
      page.locator(".card").first(),
      FEATURE,
      "misp-workbench-1_detection-profiles_list",
    );
  });

  test("2 — profile editor with a live count", async ({ page }) => {
    await page.setViewportSize({ width: 1200, height: 2300 });
    await page.goto("/detection-profiles/update/2");
    await expect(page.locator("#profile-count")).toHaveText("2,196");
    await pinForCapture(page);
    await capture(
      page.locator(".card").first(),
      FEATURE,
      "misp-workbench-2_detection-profiles_editor",
    );
  });
});
