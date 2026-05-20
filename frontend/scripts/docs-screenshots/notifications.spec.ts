import { test, expect, Page } from "@playwright/test";
import { applyTheme, capture, pinForCapture } from "./helpers";
import { EVENT_UUIDS } from "./fixtures";

const FEATURE = "notifications";

// Anchor stubs on the API port so the Vue routes (/notifications,
// /settings/user) don't get caught by the same path-only match.
const API_PORT = 8080;

const FOLLOWED_EVENT_UUID = EVENT_UUIDS.cobaltStrike;

const HUNT_NOTIFICATION = {
  id: 901,
  user_id: 1,
  type: "hunt.result.changed",
  entity_uuid: null,
  entity_type: "hunt",
  read: false,
  created_at: "2026-05-19T04:00:00+00:00",
  payload: {
    hunt_id: 5,
    hunt_name: "Suspicious IPs",
    total: 12,
    previous_total: 11,
  },
};

const NOTIFICATIONS_LIST = {
  total: 1,
  page: 1,
  size: 20,
  items: [HUNT_NOTIFICATION],
};

const USER_SETTINGS_FOLLOWED = {
  notifications: {
    email_notifications: true,
    follow: {
      events: [FOLLOWED_EVENT_UUID],
    },
  },
  explore: {
    saved_searches: [],
  },
};

const USER_SETTINGS_EMPTY = {
  notifications: { email_notifications: true },
  explore: {},
};

async function stubNotificationRoutes(page: Page) {
  await page.route(new RegExp(`:${API_PORT}/notifications(\\?|$)`), (route) => {
    const method = route.request().method();
    if (method === "GET") {
      // The pill in the top navbar polls /notifications?read=false&size=1
      // for unread count; serve it with our single unread item too.
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(NOTIFICATIONS_LIST),
      });
    }
    return route.fallback();
  });
}

async function stubUserSettings(page: Page, followed: boolean) {
  await page.route(new RegExp(`:${API_PORT}/settings/user$`), (route) => {
    if (route.request().method() !== "GET") return route.fallback();
    return route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(
        followed ? USER_SETTINGS_FOLLOWED : USER_SETTINGS_EMPTY,
      ),
    });
  });
}

test.describe("Notifications screenshots", () => {
  test("1 — notifications index with hunt result", async ({ page }) => {
    await applyTheme(page);
    await stubNotificationRoutes(page);
    await stubUserSettings(page, false);

    await page.goto("/notifications");

    await expect(page.getByRole("button", { name: /^all$/i })).toBeVisible();
    // Wait for the hunt row to render
    await expect(page.getByText("Suspicious IPs")).toBeVisible({
      timeout: 10_000,
    });
    await expect(page.getByText("hunt.result.changed")).toBeVisible();
    await expect(page.getByText(/1 new match/)).toBeVisible();
    await pinForCapture(page);

    // The page is `.container > nav.navbar + .table-responsive-sm` — capture
    // the .container so we get filters + table without the global navbar.
    const container = page
      .locator(".container")
      .filter({ has: page.getByRole("button", { name: /^all$/i }) })
      .first();
    await capture(container, FEATURE, "misp-workbench-1_notifications-hunt");
  });

  test("2 — follow event toolbar (yellow star)", async ({ page }) => {
    await applyTheme(page);
    await stubUserSettings(page, true);

    // No /events listing page in the current UI — the Follow Event button
    // lives in the event view's toolbar. The user-settings stub above
    // marks cobaltStrike as followed, so the star renders text-warning.
    await page.goto(`/events/${FOLLOWED_EVENT_UUID}`);

    await expect(page.getByText(/Event #/).first()).toBeVisible({
      timeout: 15_000,
    });
    const followBtn = page
      .getByRole("button", { name: /follow event/i })
      .first();
    await expect(followBtn).toBeVisible({ timeout: 10_000 });
    // text-warning means the yellow-filled star (followed state)
    await expect(followBtn.locator("svg")).toHaveClass(/text-warning/);
    await pinForCapture(page);

    // Capture just the event-title header card, not the rest of the page.
    const titleCard = page.locator(".event-title").first();
    await capture(
      titleCard,
      FEATURE,
      "misp-workbench-2_notifications-follow-event",
    );
  });

  test("3 — user settings page with followed event", async ({ page }) => {
    await applyTheme(page);
    await stubUserSettings(page, true);
    // The Followed entities list + Explore section pushes past the default
    // viewport height — give it room so the screenshot doesn't cut off.
    await page.setViewportSize({ width: 1600, height: 1400 });

    await page.goto("/settings/user");

    await expect(
      page.getByRole("heading", { name: "User Settings" }),
    ).toBeVisible();
    await expect(page.getByText("Followed entities")).toBeVisible({
      timeout: 10_000,
    });
    await expect(page.getByText(FOLLOWED_EVENT_UUID)).toBeVisible();
    await pinForCapture(page);

    const card = page.locator(".card").first();
    await capture(
      card,
      FEATURE,
      "misp-workbench-3_notifications-user-settings",
    );
  });
});
