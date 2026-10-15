// @vitest-environment node
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";
import {
  ACCOUNT,
  MENU,
  entryOf,
  guardFor,
  searchablePages,
  visibleAccount,
  visibleMenu,
} from "@/components/menu/menu";

const allEntries = [...MENU.flatMap((c) => c.entries), ...ACCOUNT];

// The router's paths, read as text: importing it would load every view.
const routerSource = readFileSync(
  fileURLToPath(new URL("../../../router/index.js", import.meta.url)),
  "utf8",
);
const routePaths = [...routerSource.matchAll(/path:\s*"([^"]+)"/g)].map(
  (m) => m[1],
);

// Pages reached from outside the menus: the login form, the empty home page,
// notifications, which have the bell, and the page the router guard sends a
// page the user can't open to.
const OUTSIDE_MENU = ["/", "/login", "/notifications", "/forbidden"];

describe("menu definition", () => {
  it("lists every page once", () => {
    const routes = allEntries.map((e) => e.to);
    expect(new Set(routes).size).toBe(routes.length);
    const ids = allEntries.map((e) => e.id);
    expect(new Set(ids).size).toBe(ids.length);
  });

  it("points at routes that exist", () => {
    const routes = routePaths.map(
      (path) =>
        new RegExp(`^${path.replace(/:[a-z_]+(\([^)]*\))?\??/gi, "[^/]+")}$`),
    );
    for (const entry of allEntries) {
      expect(
        routes.some((route) => route.test(entry.to)),
        entry.id,
      ).toBe(true);
    }
  });

  it("gives every route a place", () => {
    const unplaced = routePaths
      // A param's own value: /events/:id is placed by its prefix.
      .map((path) => path.replace(/\/:.*$/, ""))
      .filter((path) => !OUTSIDE_MENU.includes(path))
      .filter((path) => !entryOf(path));
    expect(unplaced).toEqual([]);
  });

  it("describes every entry", () => {
    for (const entry of allEntries) {
      expect(entry.label, entry.id).toBeTruthy();
      expect(entry.icon, entry.id).toBeTruthy();
      expect(entry.description, entry.id).toBeTruthy();
      expect(entry.scope, entry.id).toMatch(/^[a-z_]+:[a-z_]+$/);
    }
  });
});

describe("visibleMenu", () => {
  it("shows everything to an admin", () => {
    expect(visibleMenu(["*"]).map((c) => c.id)).toEqual(MENU.map((c) => c.id));
  });

  it("hides what the scopes don't open, and empty categories", () => {
    const menu = visibleMenu(["events:read", "attributes:read", "feeds:read"]);
    expect(menu.map((c) => c.id)).toEqual(["hunt", "intel", "ingest"]);
    expect(menu[0].entries.map((e) => e.id)).toEqual(["explore"]);
    expect(menu[1].entries.map((e) => e.id)).toEqual([
      "indicators",
      "review-queue",
      "source-quality",
    ]);
    expect(menu.find((c) => c.id === "admin")).toBeUndefined();
  });

  it("takes namespace wildcards", () => {
    const menu = visibleMenu(["tasks:*"]);
    expect(menu.map((c) => c.id)).toEqual(["admin"]);
    expect(menu[0].entries.map((e) => e.id)).toEqual(["tasks", "diagnostics"]);
  });

  it("shows nothing without scopes", () => {
    expect(visibleMenu([])).toEqual([]);
    expect(visibleAccount([])).toEqual([]);
  });
});

describe("entryOf", () => {
  it.each([
    ["/explore", "hunt", "explore"],
    ["/events/0f3c/attributes", "hunt", "explore"],
    ["/attributes/abc", "hunt", "explore"],
    ["/indicators", "intel", "indicators"],
    ["/indicators/review", "intel", "review-queue"],
    ["/settings/warninglists", "intel", "warninglists"],
    ["/feeds/3", "ingest", "feeds"],
    ["/detection-profiles/2/changes", "share", "detection-profiles"],
    ["/tech-lab/reactor/add", "tech-lab", "reactor"],
    ["/settings/modules", "tech-lab", "modules"],
    ["/users/7", "admin", "users"],
    ["/admin/audit-logs", "admin", "audit-logs"],
  ])("%s is under %s → %s", (path, category, entry) => {
    const found = entryOf(path);
    expect(found.category.id).toBe(category);
    expect(found.entry.id).toBe(entry);
  });

  it("puts account pages in no category", () => {
    expect(entryOf("/users/me").category).toBeNull();
    expect(entryOf("/users/me").entry.id).toBe("profile");
    expect(entryOf("/settings/api-keys").entry.id).toBe("api-keys");
  });

  it("matches whole path segments", () => {
    // /feedsomething isn't /feeds.
    expect(entryOf("/feedsomething")).toBeNull();
    expect(entryOf("/")).toBeNull();
  });
});

describe("searchablePages", () => {
  it("lists what the user can open, with its category", () => {
    const pages = searchablePages(["sinks:read", "users:me"]);
    expect(pages.map((p) => [p.id, p.category])).toEqual([
      ["sinks", "Share"],
      ["profile", "Account"],
    ]);
  });
});

describe("guardFor", () => {
  it.each([
    ["/settings/runtime", "settings:read"],
    ["/users", "users:read"],
    ["/users/7", "users:read"],
    ["/users/update/7", "users:read"],
    ["/users/me", "users:me"],
    ["/indicators/review", "attributes:read"],
    ["/tech-lab/reactor/add", "reactor:read"],
    ["/admin/audit-logs", "audit_logs:admin"],
  ])("%s needs %s", (path, scope) => {
    expect(guardFor(path).scope).toBe(scope);
  });

  it("leaves pages placed in a section to their own API", () => {
    // Under Explore for the menu, but an attribute isn't Explore's.
    expect(guardFor("/attributes/abc")).toBeNull();
    expect(guardFor("/events/0f3c/graph")).toBeNull();
  });

  it("leaves pages outside the menus alone", () => {
    for (const path of ["/", "/login", "/notifications", "/forbidden"]) {
      expect(guardFor(path)).toBeNull();
    }
  });
});
