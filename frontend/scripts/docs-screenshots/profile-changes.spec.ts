import { test, expect, Page } from "@playwright/test";
import { applyTheme, capture, pinForCapture } from "./helpers";

const FEATURE = "detection-profiles";
const API_PORT = 8080;

const at = (hours: number) =>
  new Date(Date.parse("2026-10-13T08:00:00Z") - hours * 3600e3).toISOString();

const GATE = {
  enabled: true,
  max_additions: 1000,
  max_removals: 500,
  hold_on_risk: ["popular_domain", "shared_infrastructure", "new_source"],
  spike_factor: 3,
  low_score: 40,
  new_source_days: 7,
};
const PROFILE = {
  id: 2,
  name: "Firewall block list",
  description: "Network indicators safe to block.",
  granularity: "indicators",
  rules: { types: ["ip-src", "ip-dst", "domain", "hostname", "url"] },
  auto_approve: false,
  gate: GATE,
  held: true,
  created_at: at(900),
  updated_at: null,
};

const sample = (
  value: string,
  type: string,
  score: number,
  detail?: string,
) => ({
  uuid: `${type}-${value}`,
  type,
  value,
  score,
  detail: detail ?? null,
});

const RUNS = [
  [4, "released", 0, 12, []],
  [
    4,
    "held",
    4870,
    0,
    [
      "4,870 additions, more than 1,000",
      "6 additions flagged shared infrastructure",
      "4,870 additions, 26.3× the usual 185",
    ],
  ],
  [10, "released", 212, 40, []],
  [16, "released", 185, 22, []],
  [22, "approved", 1310, 95, []],
  [28, "released", 160, 31, []],
  [34, "released", 190, 18, []],
  [40, "released", 171, 44, []],
  [46, "released", 230, 27, []],
  [52, "released", 140, 61, []],
  [58, "released", 205, 12, []],
].map(([hours, status, added, removed, reasons], i) => ({
  id: 100 - i,
  status,
  members: 21400 - i * 150,
  added,
  removed,
  reasons,
  user_email: status === "approved" ? "lead@acme-soc.example" : null,
  created_at: at(hours as number),
  updated_at: status === "held" ? at(0.5) : null,
}));

const PREVIEW = {
  generated_at: at(0),
  gate: GATE,
  held: true,
  held_since: at(4),
  reasons: RUNS[1].reasons,
  held_added: 4870,
  held_removed: 0,
  changes: {
    first: false,
    members: 26258,
    previous_members: 21400,
    added: 4870,
    removed: 12,
    added_by_type: { "ip-dst": 4211, domain: 512, url: 131, hostname: 16 },
    added_by_source: [
      { key: "feed:7", name: "Scanner noise feed", count: 4402 },
      { key: "feed:1", name: "CIRCL OSINT Feed", count: 311 },
      { key: "server:2", name: "Partner MISP", count: 142 },
      { key: "local", name: "local", count: 15 },
    ],
    removed_by_type: { domain: 7, "ip-dst": 5 },
    removed_by_reason: { expired: 8, score: 3, rejected: 1 },
    risks: {
      new_source: {
        count: 4402,
        sample: [
          sample("185.220.101.4", "ip-dst", 52, "Scanner noise feed"),
          sample("185.220.101.17", "ip-dst", 52, "Scanner noise feed"),
          sample("45.155.205.233", "ip-dst", 50, "Scanner noise feed"),
        ],
      },
      shared_infrastructure: {
        count: 6,
        sample: [
          sample(
            "104.16.132.229",
            "ip-dst",
            58,
            "List of known Cloudflare IP ranges",
          ),
          sample(
            "13.107.42.14",
            "ip-dst",
            55,
            "List of known Office 365 IP address ranges",
          ),
        ],
      },
      low_score: {
        count: 37,
        sample: [sample("login-check.example.net", "domain", 34, "score 34")],
      },
    },
    added_sample: [
      sample("185.220.101.4", "ip-dst", 52),
      sample("c2.example-cobalt.net", "domain", 89),
      sample("https://login-update.example.org/verify", "url", 72),
    ],
    removed_sample: [
      sample("old-c2.example.org", "domain", 22, "expired"),
      sample("198.51.100.77", "ip-dst", 44, "score"),
      sample("cdn.shared-hosting.example", "domain", 61, "rejected"),
    ],
    usual_added: 185,
  },
  releases: RUNS,
  consumers: [
    {
      kind: "export",
      id: 4,
      name: "Palo Alto EDL",
      status: "completed",
      gated: true,
    },
    {
      kind: "sink",
      id: 2,
      name: "Firewall manager",
      status: "keeps in step",
      gated: true,
    },
    {
      kind: "sink",
      id: 3,
      name: "SOC chat alerts",
      status: "sends published events",
      gated: false,
    },
  ],
};

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
  await page.route(new RegExp(`:${API_PORT}/detection-profiles/2$`), (r) =>
    r.fulfill(json(PROFILE)),
  );
  await page.route(
    new RegExp(`:${API_PORT}/detection-profiles/2/changes$`),
    (r) => r.fulfill(json(PREVIEW)),
  );
}

test.describe("Profile changes screenshots", () => {
  test.beforeEach(async ({ page }) => {
    await applyTheme(page);
    await stubApi(page);
  });

  test("3 — held changes, waiting for approval", async ({ page }) => {
    await page.setViewportSize({ width: 1500, height: 1700 });
    await page.goto("/detection-profiles/2/changes");
    await expect(page.getByText("Scanner noise feed").first()).toBeVisible();
    await pinForCapture(page);
    await capture(
      page.locator(".card").first(),
      FEATURE,
      "misp-workbench-3_detection-profiles_changes",
    );
  });
});
