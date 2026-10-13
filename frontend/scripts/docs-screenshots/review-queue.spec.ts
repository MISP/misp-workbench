import { test, expect, Page } from "@playwright/test";
import { applyTheme, capture, pinForCapture } from "./helpers";
import { INDICATORS } from "./indicators-fixtures";

const FEATURE = "review-queue";
const API_PORT = 8080;

const REVIEWED = [
  { id: 2, name: "Firewall block list" },
  { id: 4, name: "EDR hash block" },
];
const SUMMARY = {
  pending: 137,
  snoozed: 12,
  approved: 1840,
  rejected: 96,
  requiring_profiles: REVIEWED,
  auto_approve_profiles: [{ id: 3, name: "Auto-approve: trusted sources" }],
};

// Indicators waiting: low-trust sources, scores in the middle band.
const PENDING = INDICATORS.slice(0, 6).map((indicator, i) => ({
  ...indicator,
  score: [64, 58, 55, 52, 47, 41][i],
  pending_for:
    indicator.type === "md5" || indicator.type === "sha256"
      ? [REVIEWED[1]]
      : [REVIEWED[0]],
}));

const decidedAt = (hours: number) =>
  new Date(Date.parse("2026-10-13T08:00:00Z") - hours * 3600e3).toISOString();
const REJECTED = [
  [
    "domain",
    "cdn.shared-hosting.example",
    "shared hosting, hundreds of sites",
    true,
    1,
  ],
  ["ip-dst", "192.0.2.53", "public resolver", true, 3],
  [
    "url",
    "https://docs.example.org/setup",
    "documentation link from a report",
    false,
    7,
  ],
  ["domain", "sinkhole.example.net", "sinkholed since September", false, 26],
].map(([type, value, reason, allowlisted, hours], i) => ({
  indicator_uuid: `7e7e0000-2000-4000-8000-00000000000${i}`,
  type,
  value,
  status: "rejected",
  reason,
  snoozed_until: null,
  allowlisted,
  user_id: 1,
  user_email: i % 2 ? "analyst@acme-soc.example" : "lead@acme-soc.example",
  decided_at: decidedAt(hours as number),
}));

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
  await page.route(new RegExp(`:${API_PORT}/indicators/review/summary$`), (r) =>
    r.fulfill(json(SUMMARY)),
  );
  await page.route(new RegExp(`:${API_PORT}/indicators/review\\?`), (r) =>
    r.fulfill(json({ total: 137, page: 1, size: 50, items: PENDING })),
  );
  await page.route(
    new RegExp(`:${API_PORT}/indicators/review/decisions\\?`),
    (r) => r.fulfill(json({ total: 96, page: 1, size: 50, items: REJECTED })),
  );
  await page.route(new RegExp(`:${API_PORT}/indicators/[^/]+/review$`), (r) =>
    r.fulfill(
      json({
        decision: null,
        history: [
          {
            action: "reopened",
            at: decidedAt(30),
            user_email: "lead@acme-soc.example",
            reason: "seen again in a new campaign",
            snoozed_until: null,
            allowlisted: false,
          },
          {
            action: "snoozed",
            at: decidedAt(200),
            user_email: "analyst@acme-soc.example",
            reason: "waiting for the partner's confirmation",
            snoozed_until: null,
            allowlisted: false,
          },
        ],
      }),
    ),
  );
  await page.route(new RegExp(`:${API_PORT}/modules/\\?enabled=true`), (r) =>
    r.fulfill(
      json([
        {
          name: "dns",
          type: "expansion",
          enabled: true,
          config: {},
          misp_attributes: {
            input: ["domain", "hostname"],
            output: ["ip-dst"],
          },
          meta: { author: "", description: "", module_type: ["expansion"] },
        },
        {
          name: "shodan",
          type: "expansion",
          enabled: true,
          config: {},
          misp_attributes: { input: ["ip-dst", "ip-src"], output: ["text"] },
          meta: { author: "", description: "", module_type: ["expansion"] },
        },
      ]),
    ),
  );
}

test.describe("Review queue screenshots", () => {
  test.beforeEach(async ({ page }) => {
    await applyTheme(page);
    await stubApi(page);
  });

  test("1 — the queue, with an indicator's context", async ({ page }) => {
    await page.setViewportSize({ width: 1600, height: 1500 });
    await page.goto("/indicators/review");
    const rows = page.locator(".review-table tbody tr");
    await expect(rows.first()).toContainText(PENDING[0].value);
    // Two selected for a bulk action, the third open.
    await rows.nth(0).locator("input[type=checkbox]").check();
    await rows.nth(1).locator("input[type=checkbox]").check();
    await page.keyboard.press("j");
    await page.keyboard.press("j");
    await page.keyboard.press("Enter");
    await expect(page.getByText("seen again in a new campaign")).toBeVisible();
    await expect(page.getByText("2 selected")).toBeVisible();
    await pinForCapture(page);
    await capture(
      page.locator(".card").first(),
      FEATURE,
      "misp-workbench-1_review-queue_pending",
    );
  });

  test("2 — rejecting, with an allowlist entry", async ({ page }) => {
    await page.setViewportSize({ width: 1600, height: 900 });
    await page.goto("/indicators/review");
    await expect(page.locator(".review-table tbody tr").first()).toContainText(
      PENDING[0].value,
    );
    await page.keyboard.press("r");
    const dialog = page.getByRole("dialog");
    await dialog.locator("textarea").fill("shared hosting, hundreds of sites");
    await dialog.getByLabel("Also add to the allowlist").check();
    await pinForCapture(page);
    await capture(
      dialog.locator(".modal-content"),
      FEATURE,
      "misp-workbench-2_review-queue_reject",
    );
  });

  test("3 — rejected, with who and why", async ({ page }) => {
    await page.setViewportSize({ width: 1600, height: 900 });
    await page.goto("/indicators/review");
    await page.locator(".nav-tabs").getByText("rejected").click();
    await expect(page.getByText(REJECTED[0].value as string)).toBeVisible();
    await pinForCapture(page);
    await capture(
      page.locator(".card").first(),
      FEATURE,
      "misp-workbench-3_review-queue_rejected",
    );
  });
});
