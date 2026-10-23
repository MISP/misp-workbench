import {
  test,
  expect,
  APIRequestContext,
  Locator,
  Page,
} from "@playwright/test";
import fs from "node:fs";
import path from "node:path";
import { pinForCapture } from "../docs-screenshots/helpers";

/**
 * Walks tutorial/workshop.md as a participant does, filling in exactly what
 * each lab asks for, and captures the screens the guide shows. Each test is
 * one lab and they share one page: Lab 2 reads the indicators Lab 1 ingested.
 *
 * It writes real data and waits on real background jobs (feed ingestion, the
 * 15-second indicator sync). A previous run's workshop records are removed
 * first, by name, so it can be rerun.
 */

const API_URL = process.env.WORKSHOP_API_URL ?? "http://localhost:8080";
const SHOTS_DIR = path.resolve(
  __dirname,
  "..",
  "..",
  "..",
  "tutorial",
  "screenshots",
  "workshop",
);

// The lab files of section 0, as participants save them.
const LAB_FILES = path.resolve(
  __dirname,
  "..",
  "..",
  "..",
  "tutorial",
  "files",
);
const VENDOR_REPORT = fs.readFileSync(
  path.join(LAB_FILES, "vendor-report.txt"),
  "utf8",
);

const NAMES = {
  feed: "Paste-site C2 list",
  event: "Phishing: ACME treasury",
  orgList: "ACME own infrastructure",
  profile: "Perimeter block",
  edl: "Perimeter block: domains",
  exports: ["ids-perimeter-block", "dns-firewall"],
  notebook: "Retro-hunt: ACME treasury",
};

// Lab 2e: what the participant approves, and the one value they reject.
const APPROVE = [
  "c2.example-cobalt.net",
  "invoice-portal.test",
  "http://update-service.test/agent/setup.exe",
];
const REJECT = "https://invoice-portal.test/download/48812";

const NOTEBOOK_CELLS = [
  `campaign = [
    "c2.example-cobalt.net",
    "invoice-portal.test",
    "http://update-service.test/agent/setup.exe",
    "9f2b8c1d4e5a67380b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f708192a3b4c5d6",
    "185.220.101.42",
]

rows = []
for value in campaign:
    for attr in mwlab.search_attributes(value=value, size=200):
        if attr.get("value") != value:
            continue  # the search is full-text; keep exact hits only
        event = mwlab.get_event(attr["event_uuid"]) or {}
        rows.append({
            "value": value,
            "type": attr.get("type"),
            "event": event.get("info"),
            "event_uuid": attr["event_uuid"],
            "date": event.get("date"),
            "warninglisted": bool(attr.get("warninglist_hits")),
        })

hits = mwlab.dataframe(rows)
hits.sort_values(["value", "date"])`,
  `hits.groupby("value")["event_uuid"].nunique().sort_values(ascending=False)`,
  `shared = hits.groupby(["event_uuid", "event"])["value"].nunique()
shared[shared >= 2].sort_values(ascending=False)`,
  `from IPython.display import HTML
events = [mwlab.get_event(u) for u in hits["event_uuid"].unique()]
HTML(render.timeline([e for e in events if e]))`,
];

async function shot(target: Page | Locator, name: string, fullPage = false) {
  fs.mkdirSync(SHOTS_DIR, { recursive: true });
  const page = "page" in target ? target.page() : target;
  await pinForCapture(page);
  await target.screenshot({
    path: path.join(SHOTS_DIR, `${name}.png`),
    animations: "disabled",
    caret: "hide",
    ...("page" in target ? {} : { fullPage }),
  });
}

/** Reload until `locator` shows: for what background jobs bring in. */
async function untilVisible(
  page: Page,
  locator: Locator,
  {
    timeout = 180_000,
    refresh = async (): Promise<unknown> => page.reload(),
  }: { timeout?: number; refresh?: () => Promise<unknown> } = {},
) {
  const deadline = Date.now() + timeout;
  for (;;) {
    // first(): isVisible() throws, rather than answers, on several matches.
    if (
      await locator
        .first()
        .isVisible()
        .catch(() => false)
    )
      return;
    if (Date.now() > deadline) {
      await page.screenshot({
        path: test.info().outputPath("timed-out.png"),
        fullPage: true,
      });
      await expect(locator.first()).toBeVisible({ timeout: 1 });
    }
    await page.waitForTimeout(5_000);
    await refresh();
  }
}

class Api {
  constructor(
    private request: APIRequestContext,
    private token: string,
  ) {}

  private headers() {
    return { Authorization: `Bearer ${this.token}` };
  }

  // API payloads are read loosely: the script only picks a few fields.
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  async get<T = any>(url: string): Promise<T> {
    const response = await this.request.get(`${API_URL}${url}`, {
      headers: this.headers(),
    });
    expect(response.ok(), `GET ${url}: ${response.status()}`).toBeTruthy();
    return response.json();
  }

  async post(url: string, data: unknown) {
    const response = await this.request.post(`${API_URL}${url}`, {
      headers: this.headers(),
      data,
    });
    expect(response.ok(), `POST ${url}: ${response.status()}`).toBeTruthy();
  }

  async delete(url: string) {
    const response = await this.request.delete(`${API_URL}${url}`, {
      headers: this.headers(),
    });
    expect(
      response.ok() || response.status() === 404,
      `DELETE ${url}: ${response.status()}`,
    ).toBeTruthy();
  }

  /** Removes what a previous run of this script left behind. */
  async cleanUp() {
    for (const feed of await this.get("/feeds/")) {
      if (feed.name !== NAMES.feed) continue;
      if (feed.event_uuid) await this.delete(`/events/${feed.event_uuid}`);
      await this.delete(`/feeds/${feed.id}`);
    }
    const events = await this.get(
      `/events/?info=${encodeURIComponent(NAMES.event)}&size=100`,
    );
    for (const event of events.items) {
      if (event.info === NAMES.event && !event.deleted) {
        await this.delete(`/events/${event.uuid}`);
      }
    }
    // Outputs use the profile, and the profile the organisation list: they go
    // in that order, or the API refuses (409).
    const exports = await this.get("/exports/?size=100");
    for (const exp of exports.items) {
      if (NAMES.exports.includes(exp.name)) {
        await this.delete(`/exports/${exp.id}`);
      }
    }
    for (const edl of await this.get("/edls")) {
      if (edl.name === NAMES.edl) await this.delete(`/edls/${edl.id}`);
    }
    for (const profile of await this.get("/detection-profiles")) {
      if (profile.name === NAMES.profile) {
        await this.delete(`/detection-profiles/${profile.id}`);
      }
    }
    // Review decisions are per indicator, not per profile: they outlive the
    // profile. Reopen them so the queue shows the campaign again.
    for (const status of ["approved", "rejected", "snoozed"]) {
      for (const value of [...APPROVE, REJECT]) {
        const page = await this.get(
          `/indicators/review/decisions?status=${status}&q=${encodeURIComponent(value)}`,
        );
        const uuids = page.items
          .filter((d: { value: string }) => d.value === value)
          .map((d: { indicator_uuid: string }) => d.indicator_uuid);
        if (uuids.length) {
          await this.post("/indicators/review/decisions", {
            indicators: uuids,
            action: "reopen",
          });
        }
      }
    }
    for (const list of await this.get("/local-warninglists")) {
      if (list.name === NAMES.orgList) {
        await this.delete(`/local-warninglists/${list.id}`);
      }
      // Lab 2e's rejection lands on this list; take it off again.
      if (list.name === "Rejected in review") {
        const entries = await this.get(
          `/local-warninglists/${list.id}/entries?q=${encodeURIComponent(REJECT)}`,
        );
        const ids = entries.items
          .filter((e: { value: string }) => e.value === REJECT)
          .map((e: { id: number }) => e.id);
        if (ids.length) {
          await this.post(`/local-warninglists/${list.id}/entries/delete`, {
            ids,
          });
        }
      }
    }
    const tree = await this.get("/tech-lab/tree");
    for (const notebook of tree.notebooks) {
      if (notebook.name === NAMES.notebook) {
        await this.delete(`/tech-lab/notebooks/${notebook.id}`);
      }
    }
  }
}

let page: Page;
let api: Api;
let eventUuid: string;

test.describe.configure({ mode: "serial" });

test.beforeAll(async ({ browser, playwright }) => {
  page = await browser.newPage();
  await page.goto("/explore");
  const token = await page.evaluate(() => localStorage.getItem("access_token"));
  expect(token, "not logged in: delete .auth and rerun").toBeTruthy();
  api = new Api(await playwright.request.newContext(), token as string);
  // WORKSHOP_CLEANUP=0 keeps a previous run's records, to re-shoot a single
  // lab that only reads them (the notebook) with --grep.
  if (process.env.WORKSHOP_CLEANUP !== "0") await api.cleanUp();
});

test.afterAll(async () => {
  await page?.close();
});

test("0 — an API key with the SIEM preset", async () => {
  await page.setViewportSize({ width: 1400, height: 1400 });
  await page.goto("/settings/api-keys");
  await page.getByRole("button", { name: /new api key/i }).click();
  const modal = page.locator(".modal.d-block .modal-content");
  await modal.getByRole("button", { name: /siem integration preset/i }).click();
  // The preset names the key when it is empty: name it after.
  await modal.getByPlaceholder("e.g. Splunk integration").fill("workshop");
  await shot(modal, "00-api-key-siem-preset");
  // The script calls the API with the session; the key itself isn't needed.
  await page.keyboard.press("Escape");
});

test("1a — upload the blocklist as an offline feed", async () => {
  await page.setViewportSize({ width: 1600, height: 1800 });
  await page.goto("/feeds/add");
  await page.locator(".feed-type-card", { hasText: "Freetext" }).click();

  await page.locator('[id="feed.name"]').fill(NAMES.feed);
  await page.locator('[id="feed.provider"]').fill("pastebin (unverified)");
  await page.locator("#inputSourceLocal").check();
  await page
    .locator('.feed-file-upload input[type="file"]')
    .setInputFiles(path.join(LAB_FILES, "c2-blocklist.txt"));
  await expect(
    page.locator(".feed-file-upload").getByText("c2-blocklist.txt"),
  ).toBeVisible();
  await page.locator("#feedFixedEvent").check();
  await page.locator("#typeAutomatic").check();

  // The settings card previews the uploaded file once it is stored.
  const settings = page.locator(".card", { hasText: "Freetext Settings" });
  await expect(settings.getByText("c2.example-cobalt").first()).toBeVisible();
  await shot(page, "01-freetext-feed-upload");

  await page.getByRole("button", { name: "Add Feed", exact: true }).click();
  await page.waitForURL((url) => !url.pathname.endsWith("/feeds/add"));

  // Ingested by a background job: wait for its fixed event.
  await expect
    .poll(
      async () =>
        (await api.get("/feeds/")).find(
          (f: { name: string }) => f.name === NAMES.feed,
        )?.event_uuid ?? null,
      { timeout: 120_000, intervals: [2_000] },
    )
    .not.toBeNull();
});

test("1b — import the vendor report", async () => {
  await page.setViewportSize({ width: 1400, height: 1500 });
  await page.goto("/events/add");
  await page.locator('[id="event.info"]').fill(NAMES.event);
  await page
    .locator('select[name="event.threat_level"]')
    .selectOption({ label: "HIGH" });
  await page.getByRole("button", { name: "Create", exact: true }).click();
  await page.waitForURL(/\/events\/[0-9a-f-]{36}$/);
  eventUuid = page.url().split("/").pop() as string;

  await page.locator('button[title="Import"]').click();
  const modal = page.locator(`#importDataEventModal_${eventUuid}`);
  await expect(modal).toHaveClass(/show/);
  await modal
    .locator('textarea[placeholder^="Paste indicators"]')
    .fill(VENDOR_REPORT);
  await expect(modal.getByText(/8 valid/)).toBeVisible();
  await expect(modal.getByText(/sha256 · 1/)).toBeVisible();
  await shot(modal.locator(".modal-content"), "02-batch-import");

  await modal.getByRole("button", { name: "Import", exact: true }).click();
  await expect(modal).toBeHidden();
});

test("1c — what normalisation did", async () => {
  await page.setViewportSize({ width: 1600, height: 1100 });
  await page.goto(`/events/${eventUuid}/attributes`);
  const table = page
    .locator('[data-tab-panel="attributes"] .table-responsive')
    .first();
  await expect(
    table.locator("td.value", { hasText: "c2.example-cobalt.net" }),
  ).toBeVisible();
  await expect(table.getByText("normalised").first()).toBeVisible();
  // The private-ip flag on the victim's workstation.
  await untilVisible(
    page,
    table.locator("td.value", { hasText: "10.20.30.40" }).locator(".badge"),
  );
  await shot(table, "03-normalised-attributes");
});

async function searchIndicators(query: string) {
  const search = page.locator('input[aria-label="Search indicators"]');
  await search.fill(query);
  await search.press("Enter");
}

test("2a — read a score", async () => {
  await page.setViewportSize({ width: 1600, height: 1400 });
  await page.goto("/indicators");
  await searchIndicators("value:*cobalt*");

  const row = page.locator("tr[role=button]", {
    hasText: "c2.example-cobalt.net",
  });
  // 70 + 5 corroboration + 15 sightings - 20 for the seeded false positive,
  // once both the event and the feed reached the index.
  await untilVisible(
    page,
    row.locator(".score-badge").filter({ hasText: /^\s*70\s*$/ }),
    {
      timeout: 300_000,
      // Searching the same query again doesn't refetch: reload first.
      refresh: async () => {
        await page.reload();
        await searchIndicators("value:*cobalt*");
      },
    },
  );
  await row.click();
  await expect(
    page.locator("td[colspan] dt", { hasText: "score" }),
  ).toBeVisible();
  await shot(page.locator(".card").first(), "04-indicator-detail");
});

test("2b — trust the feed for what it is", async () => {
  const feed = (await api.get("/feeds/")).find(
    (f: { name: string }) => f.name === NAMES.feed,
  );
  await page.goto(`/feeds/update/${feed.id}`);
  await page.locator("#feed-score-modifier").fill("-10");
  await page.locator("#feed-score-cap").fill("60");
  await page.getByRole("button", { name: "Save", exact: true }).click();
  await page.waitForURL(new RegExp(`/feeds/${feed.id}$`));

  await page.setViewportSize({ width: 1600, height: 1100 });
  await page.goto("/indicators/sources");
  const card = page.locator(".card").first();
  await expect(card.getByText(NAMES.feed).first()).toBeVisible();
  await shot(card, "05-source-quality");
});

test("2c — protect your own infrastructure", async () => {
  await page.setViewportSize({ width: 1500, height: 1200 });
  await page.goto("/settings/warninglists");
  await page.locator('[data-bs-target="#newLocalWarninglistModal"]').click();
  const modal = page.locator("#newLocalWarninglistModal");
  await expect(modal).toHaveClass(/show/);
  await modal.locator("#nlw-name").fill(NAMES.orgList);
  await modal
    .locator("#nlw-description")
    .fill("Egress, VPN and corporate domains. Never block.");
  await modal.getByRole("button", { name: "Create", exact: true }).click();
  await expect(modal).toBeHidden();

  await page.getByRole("link", { name: NAMES.orgList }).click();
  await page
    .locator('textarea[aria-label="Entries to import"]')
    .fill(
      [
        "203.0.113.0/24     # VPN egress",
        "198.51.100.10      # mail relay",
        "*.acme-bank.test   # corporate domains",
      ].join("\n"),
    );
  await page.getByRole("button", { name: "Import", exact: true }).click();
  const card = page.locator(".card").first();
  await expect(card.getByText("3 entries")).toBeVisible();
  await shot(card, "06-organisation-warninglist");
});

test("2d — a detection profile for perimeter blocking", async () => {
  await page.setViewportSize({ width: 1200, height: 2400 });
  await page.goto("/detection-profiles/add");
  const form = page.locator(".card.mx-auto");
  await form.locator("#profile-name").fill(NAMES.profile);

  const types = form
    .locator("label", { hasText: /^Types$/ })
    .locator("xpath=following::div[contains(@class,'ts-wrapper')][1]");
  for (const type of ["ip-src", "ip-dst", "domain", "hostname", "url"]) {
    await types.locator(".ts-control").click();
    await types.locator(".ts-control input").fill(type);
    await types.locator(`.ts-dropdown .option[data-value="${type}"]`).click();
  }
  await page.keyboard.press("Escape");

  await form.locator("#profile-to-ids").check();
  await form.locator("#profile-min-score").fill("60");
  await form.locator("#profile-max-age").fill("30");
  await form.locator("#profile-tlp").selectOption("tlp:amber");
  await form.locator("#profile-warninglisted").check();
  await form.locator("#profile-validation").check();
  await form.getByLabel(new RegExp(`^${NAMES.orgList}`)).check();
  await form.locator("#profile-require-approval").check();

  // The live count follows the rules after a debounce.
  await expect(form.locator("#profile-count")).toHaveText(/^[\d,]+$/);
  await expect(
    form.locator(".alert span.font-monospace").first(),
  ).toBeVisible();
  await shot(form, "07-detection-profile-editor");

  await form.getByRole("button", { name: "Create profile" }).click();
  await page.waitForURL(/\/detection-profiles$/);

  const profile = (await api.get("/detection-profiles")).find(
    (p: { name: string }) => p.name === NAMES.profile,
  );
  await page.setViewportSize({ width: 1600, height: 1400 });
  await page.goto(`/detection-profiles/${profile.id}/changes`);
  const changes = page.locator(".card").first();
  await expect(changes.getByText("selected now").first()).toBeVisible();
  await shot(changes, "08-profile-changes");
});

/** A queue row's checkbox, labelled "Select <value>". */
function rowBox(value: string) {
  return page.locator(
    `.review-table input[type=checkbox][aria-label=${JSON.stringify(`Select ${value}`)}]`,
  );
}

test("2e — approve what goes out", async () => {
  await page.setViewportSize({ width: 1600, height: 1400 });
  const openQueue = async () => {
    const summary = page.waitForResponse(/\/indicators\/review\/summary/);
    await page.goto("/indicators/review");
    await summary;
    // Picking a profile refetches, with a spinner in place of the table.
    const filtered = page.waitForResponse(
      /\/indicators\/review\?.*profile_id=/,
    );
    await page
      .locator('select[aria-label="Profile"]')
      .selectOption({ label: NAMES.profile });
    await filtered;
    await expect(page.locator(".review-table")).toBeVisible();
  };
  await openQueue();
  await untilVisible(page, rowBox(APPROVE[0]), {
    timeout: 360_000,
    refresh: openQueue,
  });
  for (const value of APPROVE) {
    await rowBox(value).check();
  }
  await expect(page.getByText(`${APPROVE.length} selected`)).toBeVisible();
  await shot(page.locator(".card").first(), "09-review-queue");

  await page
    .locator(".review-actions")
    .getByRole("button", { name: "Approve" })
    .click();
  await expect(rowBox(APPROVE[0])).toBeHidden();

  await rowBox(REJECT).check();
  await page
    .locator(".review-actions")
    .getByRole("button", { name: /^Reject/ })
    .click();
  const dialog = page.locator('.modal.d-block[role="dialog"]');
  await dialog
    .locator("#reject-reason")
    .fill("Per-victim download link; the domain is already blocked.");
  await dialog.locator("#reject-warninglist").check();
  await shot(dialog.locator(".modal-content"), "10-review-reject");
  await dialog.getByRole("button", { name: "Reject", exact: true }).click();
  await expect(dialog).toBeHidden();
});

test("3a — a Palo Alto external dynamic list", async () => {
  await page.goto("/edls");
  await page.getByRole("button", { name: /new edl/i }).click();
  const modal = page.locator("#edlFormModal");
  await expect(modal).toHaveClass(/show/);
  await modal.locator("#edl-name").fill(NAMES.edl);
  await modal.locator("#edl-profile").selectOption({ label: NAMES.profile });
  await modal.locator("#edl-vendor").selectOption("paloalto");
  await modal.locator("#edl-list-type").selectOption("domain");
  await modal.locator("#edl-refresh").fill("15");
  await modal.getByRole("button", { name: "Create", exact: true }).click();
  await page.waitForURL(/\/edls\/\d+$/);

  await page.getByRole("button", { name: /rebuild now/i }).click();
  await expect(page.locator("pre#edl-preview")).toContainText(APPROVE[0]);
});

test("3b — Suricata rules and a DNS RPZ zone", async () => {
  await page.setViewportSize({ width: 1400, height: 1600 });
  const newExport = async (name: string, format: string) => {
    await page.goto("/exports/add");
    const form = page.locator(".card.mx-auto");
    await form.locator("#export-name").fill(name);
    // Options read "<name> (<granularity>)".
    const profile = form
      .locator("#export-profile option")
      .filter({ hasText: NAMES.profile });
    await form
      .locator("#export-profile")
      .selectOption({ label: (await profile.textContent())!.trim() });
    await form.locator("#export-query").fill("*");
    await form.locator("#export-format").selectOption(format);
    await form.locator("#export-schedule-enabled").check();
    await form
      .locator('select:has(option[value="hourly"])')
      .selectOption("hourly");
    return form;
  };

  const suricata = await newExport(NAMES.exports[0], "suricata");
  await suricata.locator("#export-rule-action").selectOption("alert");
  await shot(suricata, "11-new-export-suricata");
  await suricata.getByRole("button", { name: "Create Export" }).click();
  await page.waitForURL(/\/exports$/);

  const rpz = await newExport(NAMES.exports[1], "rpz");
  await rpz.locator("#export-rpz-policy").selectOption("redirect");
  await rpz.locator("#export-rpz-redirect").fill("blocked.acme-bank.test");
  await rpz.getByRole("button", { name: "Create Export" }).click();
  await page.waitForURL(/\/exports$/);

  for (const name of NAMES.exports) {
    const row = page.locator("tr", {
      has: page.locator("span.fw-semibold", { hasText: name }),
    });
    await expect(
      row.locator("span.badge", { hasText: "completed" }),
    ).toBeVisible({
      timeout: 120_000,
    });
  }
});

async function runCell(code: string) {
  const footers = page.locator(".output-panel .output-block-footer");
  const before = await footers.count();
  const toolbar = page.locator(".editor-pane-toolbar");
  await toolbar.getByRole("button", { name: /add/i }).click();
  await page.locator(".dropdown-item", { hasText: "Code" }).click();
  // Inserted through Monaco's API at the cursor, which "Add" left in the new
  // cell: typed, it would auto-indent and auto-close brackets, and a
  // headless clipboard paste doesn't reach it.
  await page.evaluate((text) => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const editor = (window as any).monaco.editor.getEditors()[0];
    editor.focus();
    editor.executeEdits("workshop", [
      { range: editor.getSelection(), text, forceMoveMarkers: true },
    ]);
  }, code);
  await page.keyboard.press("Shift+Enter");
  await expect(footers).toHaveCount(before + 1, { timeout: 120_000 });
}

test("5a — notebook: has this campaign hit us before?", async () => {
  await page.setViewportSize({ width: 1600, height: 1100 });
  await page.goto("/tech-lab/notebooks");
  await page
    .locator(
      'button[title="New notebook"][data-bs-target="#newNotebookModal-personal"]',
    )
    .click();
  const modal = page.locator("#newNotebookModal-personal");
  await expect(modal).toHaveClass(/show/);
  await modal.locator("#nn-name").fill(NAMES.notebook);
  await modal.getByRole("button", { name: "Create", exact: true }).click();
  await page.waitForURL(/\/tech-lab\/notebooks\/\d+$/);
  await expect(page.locator(".monaco-editor").first()).toBeVisible();
  await page.locator(".monaco-editor .view-lines").first().click();

  await runCell(NOTEBOOK_CELLS[0]);
  await expect(page.locator(".output-panel .cell-output-error")).toHaveCount(0);
  await shot(page.locator(".notebooks-workspace"), "12-notebook-retro-hunt");

  for (let i = 1; i < NOTEBOOK_CELLS.length; i++) {
    await runCell(NOTEBOOK_CELLS[i]);
  }
  await expect(page.locator(".output-panel .cell-output-error")).toHaveCount(0);
  await page
    .locator(".output-panel .output-block")
    .last()
    .scrollIntoViewIfNeeded();
  await shot(page.locator(".notebooks-workspace"), "13-notebook-timeline");
});
