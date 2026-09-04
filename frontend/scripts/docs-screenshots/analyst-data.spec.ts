import { test, expect, Page } from "@playwright/test";
import { applyTheme, capture, pinForCapture } from "./helpers";
import { EVENT_UUIDS } from "./fixtures";

const FEATURE = "analyst-data";

// Anchor stubs on the API port so the Vue routes don't get caught by the same
// path-only match.
const API_PORT = 8080;

const EVENT_UUID = EVENT_UUIDS.cobaltStrike;
// The relationship points at another docs fixture event, so its name resolves
// against the real API rather than needing a stub of its own.
const RELATED_EVENT_UUID = EVENT_UUIDS.wannacry;

// One of the Cobalt Strike event's seeded attributes. Only used as a key the
// stubs agree on, so the attribute row badge and its panel line up.
const ATTRIBUTE_UUID = "b2f30000-0001-4002-8000-000000000001";

const AUTHOR = "analyst@circl.lu";
const REVIEWER = "reviewer@circl.lu";

function node(uuid: string, analystType: string, data: object, children = {}) {
  return {
    uuid,
    analyst_type: analystType,
    object_uuid: EVENT_UUID,
    object_type: "Event",
    data: {
      uuid,
      analyst_type: analystType,
      object_uuid: EVENT_UUID,
      object_type: "Event",
      event_uuid: EVENT_UUID,
      distribution: 3,
      deleted: false,
      ...data,
    },
    notes: [],
    opinions: [],
    relationships: [],
    ...children,
  };
}

// A note carrying a reply and an opinion, plus an event level opinion and a
// relationship: the whole shape the feature renders, in one card.
const EVENT_THREADS = {
  notes: [
    node(
      "c0000000-0000-4000-8000-000000000001",
      "Note",
      {
        note:
          "Beacon configs across these hosts share a watermark, which puts " +
          "them on the same operator rather than three unrelated intrusions.",
        language: "en",
        authors: AUTHOR,
        created: "2026-05-19T09:12:00+00:00",
        modified: "2026-05-19T09:12:00+00:00",
      },
      {
        notes: [
          node("c0000000-0000-4000-8000-000000000002", "Note", {
            note: "Confirmed against the sandbox run from the 17th.",
            language: "en",
            authors: REVIEWER,
            created: "2026-05-19T11:40:00+00:00",
            modified: "2026-05-19T11:40:00+00:00",
            object_uuid: "c0000000-0000-4000-8000-000000000001",
            object_type: "Note",
          }),
        ],
        opinions: [
          node("c0000000-0000-4000-8000-000000000003", "Opinion", {
            opinion: 90,
            comment: "The watermark match is hard to argue with.",
            authors: REVIEWER,
            created: "2026-05-19T11:52:00+00:00",
            modified: "2026-05-19T11:52:00+00:00",
            object_uuid: "c0000000-0000-4000-8000-000000000001",
            object_type: "Note",
          }),
        ],
      },
    ),
  ],
  opinions: [
    node("c0000000-0000-4000-8000-000000000004", "Opinion", {
      opinion: 25,
      comment:
        "Low confidence in the attribution itself — the infrastructure is " +
        "rented and has been reused by unrelated actors before.",
      authors: AUTHOR,
      created: "2026-05-19T13:05:00+00:00",
      modified: "2026-05-19T13:05:00+00:00",
    }),
  ],
  relationships: [
    node("c0000000-0000-4000-8000-000000000005", "Relationship", {
      related_object_uuid: RELATED_EVENT_UUID,
      related_object_type: "Event",
      relationship_type: "similar-to",
      authors: AUTHOR,
      created: "2026-05-19T13:20:00+00:00",
      modified: "2026-05-19T13:20:00+00:00",
    }),
  ],
};

const ATTRIBUTE_THREADS = {
  notes: [
    {
      uuid: "c0000000-0000-4000-8000-000000000006",
      analyst_type: "Note",
      object_uuid: ATTRIBUTE_UUID,
      object_type: "Attribute",
      data: {
        uuid: "c0000000-0000-4000-8000-000000000006",
        analyst_type: "Note",
        object_uuid: ATTRIBUTE_UUID,
        object_type: "Attribute",
        event_uuid: EVENT_UUID,
        note: "Seen in unrelated samples as well — weak on its own.",
        language: "en",
        authors: AUTHOR,
        created: "2026-05-19T14:02:00+00:00",
        modified: "2026-05-19T14:02:00+00:00",
        distribution: 3,
        deleted: false,
      },
      notes: [],
      opinions: [],
      relationships: [],
    },
  ],
  opinions: [],
  relationships: [],
};

// Drives the badge on each attribute row, and the count on an object panel.
const COUNTS = {
  [EVENT_UUID]: 4,
  [ATTRIBUTE_UUID]: 1,
};

// The docs seed re-times its attributes on every run, so the timestamp column
// shifted between captures and CI would raise a screenshot diff PR each time.
// Stubbing the list pins it.
const ATTRIBUTES_PAGE = {
  total: 3,
  page: 1,
  size: 10,
  pages: 1,
  items: [
    {
      uuid: ATTRIBUTE_UUID,
      event_uuid: EVENT_UUID,
      object_uuid: null,
      object_relation: null,
      category: "Network activity",
      type: "ip-src",
      value: "185.220.101.42",
      to_ids: true,
      timestamp: 1779179400,
      distribution: 5,
      sharing_group_id: null,
      comment: "Cobalt Strike team server",
      deleted: false,
      disable_correlation: false,
      first_seen: null,
      last_seen: null,
      tags: [],
      correlations: [],
      correlation_count: 0,
      expanded: null,
    },
    {
      uuid: "b2f30000-0001-4002-8000-000000000002",
      event_uuid: EVENT_UUID,
      object_uuid: null,
      object_relation: null,
      category: "Payload delivery",
      type: "md5",
      value: "5d41402abc4b2a76b9719d911017c592",
      to_ids: true,
      timestamp: 1779120600,
      distribution: 5,
      sharing_group_id: null,
      comment: "",
      deleted: false,
      disable_correlation: false,
      first_seen: null,
      last_seen: null,
      tags: [],
      correlations: [],
      correlation_count: 0,
      expanded: null,
    },
    {
      uuid: "b2f30000-0001-4002-8000-000000000003",
      event_uuid: EVENT_UUID,
      object_uuid: null,
      object_relation: null,
      category: "Network activity",
      type: "domain",
      value: "c2.example-cobalt.net",
      to_ids: true,
      timestamp: 1779119100,
      distribution: 5,
      sharing_group_id: null,
      comment: "",
      deleted: false,
      disable_correlation: false,
      first_seen: null,
      last_seen: null,
      tags: [],
      correlations: [],
      correlation_count: 0,
      expanded: null,
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

async function stubAnalystData(page: Page) {
  await page.route(
    new RegExp(`:${API_PORT}/analyst-data/events/[^/]+/counts`),
    (route) =>
      route.request().method() === "GET"
        ? route.fulfill(json(COUNTS))
        : route.fallback(),
  );

  await page.route(
    new RegExp(`:${API_PORT}/analyst-data/events/[^/?]+(\\?|$)`),
    (route) =>
      route.request().method() === "GET"
        ? route.fulfill(json(EVENT_THREADS))
        : route.fallback(),
  );

  await page.route(
    new RegExp(`:${API_PORT}/analyst-data/objects/[^/?]+(\\?|$)`),
    (route) =>
      route.request().method() === "GET"
        ? route.fulfill(json(ATTRIBUTE_THREADS))
        : route.fallback(),
  );
}

async function stubAttributes(page: Page) {
  await page.route(new RegExp(`:${API_PORT}/attributes/\\?`), (route) =>
    route.request().method() === "GET"
      ? route.fulfill(json(ATTRIBUTES_PAGE))
      : route.fallback(),
  );
}

test.describe("Analyst data screenshots", () => {
  test("1 — analyst data on an event, with a thread", async ({ page }) => {
    await applyTheme(page);
    await stubAnalystData(page);

    // Analyst data has its own tab on the event view, and the tab is part of
    // the URL, so the panel is linked to directly and is itself the shot.
    await page.goto(`/events/${EVENT_UUID}/analyst-data`);

    const panel = page.locator('[data-tab-panel="analyst-data"]');
    await expect(panel).toBeVisible({ timeout: 15_000 });

    // the note, its reply and its opinion all rendered
    await expect(panel.getByText(/share a watermark/)).toBeVisible({
      timeout: 10_000,
    });
    await expect(
      panel.getByText(/Confirmed against the sandbox/),
    ).toBeVisible();
    await expect(panel.getByText("90/100")).toBeVisible();

    // the relationship resolves its target's name against the real API
    await expect(panel.getByRole("link", { name: /WannaCry/i })).toBeVisible({
      timeout: 10_000,
    });

    await pinForCapture(page);
    await capture(panel, FEATURE, "misp-workbench-1_analyst-data-event-thread");
  });

  test("2 — analyst data on an attribute row", async ({ page }) => {
    await applyTheme(page);
    await stubAnalystData(page);
    // pinned so the timestamp column does not shift between runs
    await stubAttributes(page);

    await page.goto(`/events/${EVENT_UUID}/attributes`);

    // the count badge sits on the toggle before anything is expanded
    const toggle = page.getByTitle("Show analyst data").first();
    await expect(toggle).toBeVisible({ timeout: 15_000 });
    await expect(toggle.locator(".analyst-count")).toHaveText(/1/, {
      timeout: 10_000,
    });

    await toggle.click();
    await expect(page.getByText(/Seen in unrelated samples/)).toBeVisible({
      timeout: 10_000,
    });

    await pinForCapture(page);

    // the attributes tab panel, so the row and its expanded panel read together
    const card = page.locator('[data-tab-panel="attributes"]');
    await capture(card, FEATURE, "misp-workbench-2_analyst-data-attribute");
  });
});
