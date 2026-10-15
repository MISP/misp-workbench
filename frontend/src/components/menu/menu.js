// The navigation, described once. The desktop menu, the mobile menu and the
// quick switcher (Ctrl+K) are all rendered from it, so a new page is one new
// entry here.
//
// Entries are grouped by what the user is doing. Each names the scope its page
// needs (its list endpoint's): entries the user can't open are hidden, and so
// is a category left with none.

import {
  faBook,
  faBuilding,
  faBullseye,
  faCircleNodes,
  faClipboardList,
  faCrosshairs,
  faDownload,
  faFileExport,
  faFilter,
  faFlask,
  faGears,
  faIdBadge,
  faKey,
  faLayerGroup,
  faListCheck,
  faListUl,
  faMagnifyingGlass,
  faPaperPlane,
  faPlug,
  faPuzzlePiece,
  faRobot,
  faRss,
  faScaleBalanced,
  faServer,
  faShareNodes,
  faShieldHalved,
  faSlidersH,
  faStar,
  faStethoscope,
  faTags,
  faTriangleExclamation,
  faUser,
  faUserShield,
  faUsers,
  faWrench,
} from "@fortawesome/free-solid-svg-icons";
import { authHelper } from "@/helpers/auth";

export const MENU = [
  {
    id: "hunt",
    label: "Hunt",
    icon: faCrosshairs,
    description: "Search and investigate",
    entries: [
      {
        id: "explore",
        label: "Explore",
        to: "/explore",
        icon: faMagnifyingGlass,
        description: "Search events, attributes, indicators and correlations",
        scope: "events:read",
        // Pages reached from search results belong here too.
        sections: ["/events", "/attributes", "/objects"],
      },
      {
        id: "hunts",
        label: "Hunts",
        to: "/hunts",
        icon: faCrosshairs,
        description: "Saved searches that run on a schedule and alert on hits",
        scope: "hunts:read",
      },
      {
        id: "correlations",
        label: "Correlations",
        to: "/correlations",
        icon: faCircleNodes,
        description: "Values seen in more than one event",
        scope: "correlations:read",
      },
    ],
  },
  {
    id: "intel",
    label: "Intel",
    icon: faShieldHalved,
    description: "Curate what the indicators say",
    entries: [
      {
        id: "indicators",
        label: "Indicators",
        to: "/indicators",
        icon: faBullseye,
        description: "Each value once, with its sources, score and sightings",
        scope: "attributes:read",
      },
      {
        id: "review-queue",
        label: "Review queue",
        to: "/indicators/review",
        icon: faListCheck,
        description: "Indicators waiting for an analyst's decision",
        scope: "attributes:read",
      },
      {
        id: "source-quality",
        label: "Source quality",
        to: "/indicators/sources",
        icon: faScaleBalanced,
        description: "How each feed and organisation's indicators hold up",
        scope: "attributes:read",
      },
      {
        id: "warninglists",
        label: "Warninglists",
        to: "/settings/warninglists",
        icon: faTriangleExclamation,
        description: "Benign and overly common values kept out of outputs",
        scope: "warninglists:read",
      },
      {
        id: "taxonomies",
        label: "Taxonomies",
        to: "/settings/taxonomies",
        icon: faTags,
        description: "Tag vocabularies such as TLP and PAP",
        scope: "taxonomies:read",
        sections: ["/taxonomies"],
      },
      {
        id: "galaxies",
        label: "Galaxies",
        to: "/settings/galaxies",
        icon: faStar,
        description: "Threat actors, malware and ATT&CK techniques",
        scope: "galaxies:read",
        sections: ["/galaxies"],
      },
    ],
  },
  {
    id: "ingest",
    label: "Ingest",
    icon: faDownload,
    description: "Where intelligence comes from",
    entries: [
      {
        id: "feeds",
        label: "Feeds",
        to: "/feeds",
        icon: faRss,
        description: "MISP, CSV, JSON and freetext feeds pulled on a schedule",
        scope: "feeds:read",
      },
      {
        id: "servers",
        label: "MISP servers",
        to: "/servers",
        icon: faServer,
        description: "Remote MISP instances to pull from and push to",
        scope: "servers:read",
      },
      {
        id: "alert-receivers",
        label: "Alert webhooks",
        to: "/alert-receivers",
        icon: faPlug,
        description: "SIEM and SOAR alerts reported back as sightings",
        scope: "alert_receivers:read",
      },
    ],
  },
  {
    id: "share",
    label: "Share",
    icon: faShareNodes,
    description: "Send indicators to security controls",
    entries: [
      {
        id: "detection-profiles",
        label: "Detection profiles",
        to: "/detection-profiles",
        icon: faFilter,
        description: "What goes to which control, defined once",
        scope: "detection_profiles:read",
      },
      {
        id: "exports",
        label: "Exports",
        to: "/exports",
        icon: faFileExport,
        description: "Files and feeds: CSV, STIX, Suricata, Zeek, RPZ and more",
        scope: "exports:read",
      },
      {
        id: "sinks",
        label: "Sinks",
        to: "/sinks",
        icon: faPaperPlane,
        description: "Push to SIEMs and vendor APIs as events are published",
        scope: "sinks:read",
      },
      {
        id: "edls",
        label: "External dynamic lists",
        to: "/edls",
        icon: faListUl,
        description: "Block lists firewalls and proxies fetch",
        scope: "edls:read",
      },
    ],
  },
  {
    id: "tech-lab",
    label: "Tech lab",
    icon: faFlask,
    description: "Automate and extend",
    entries: [
      {
        id: "notebooks",
        label: "Notebooks",
        to: "/tech-lab/notebooks",
        icon: faBook,
        description: "Python notebooks over the platform's data",
        scope: "lab:read",
      },
      {
        id: "reactor",
        label: "Reactor scripts",
        to: "/tech-lab/reactor",
        icon: faRobot,
        description:
          "Scripts that run when events, attributes or sightings change",
        scope: "reactor:read",
      },
      {
        id: "servos",
        label: "Transformation servos",
        to: "/tech-lab/servos",
        icon: faGears,
        description: "Ingest pipelines that enrich and normalise attributes",
        scope: "servos:read",
      },
      {
        id: "modules",
        label: "Enrichment modules",
        to: "/settings/modules",
        icon: faPuzzlePiece,
        description: "MISP modules for enrichment, import and export",
        scope: "modules:read",
      },
    ],
  },
  {
    id: "admin",
    label: "Administration",
    shortLabel: "Admin",
    icon: faWrench,
    description: "Run the instance",
    entries: [
      {
        id: "users",
        label: "Users",
        to: "/users",
        icon: faUsers,
        description: "Accounts and their roles",
        scope: "users:read",
        // Your own profile is an account page, not this one.
        excludes: ["/users/me"],
      },
      {
        id: "organisations",
        label: "Organisations",
        to: "/organisations",
        icon: faBuilding,
        description: "The organisations users and events belong to",
        scope: "organisations:read",
      },
      {
        id: "roles",
        label: "Roles",
        to: "/roles",
        icon: faIdBadge,
        description: "Scopes each role grants",
        scope: "roles:read",
      },
      {
        id: "runtime-settings",
        label: "Runtime settings",
        to: "/settings/runtime",
        icon: faSlidersH,
        description:
          "Instance-wide settings: scoring, retention, normalisation",
        scope: "settings:read",
      },
      {
        id: "admin-api-keys",
        label: "API keys (admin)",
        to: "/admin/api-keys",
        icon: faUserShield,
        description: "Every user's API keys",
        scope: "api_keys:admin",
      },
      {
        id: "audit-logs",
        label: "Audit logs",
        to: "/admin/audit-logs",
        icon: faClipboardList,
        description: "Who changed what, and from where",
        scope: "audit_logs:admin",
      },
      {
        id: "tasks",
        label: "Tasks",
        to: "/tasks",
        icon: faLayerGroup,
        description: "Background jobs, workers and schedules",
        scope: "tasks:read",
      },
      {
        id: "diagnostics",
        label: "Diagnostics",
        to: "/diagnostics",
        icon: faStethoscope,
        description: "Health of Redis, PostgreSQL, storage and modules",
        scope: "tasks:read",
      },
    ],
  },
];

// The user menu: pages about your own account only.
export const ACCOUNT = [
  {
    id: "profile",
    label: "Profile",
    to: "/users/me",
    icon: faUser,
    description: "Your account",
    scope: "users:me",
  },
  {
    id: "api-keys",
    label: "My API keys",
    to: "/settings/api-keys",
    icon: faKey,
    description: "Keys for scripts and integrations",
    scope: "api_keys:read",
  },
  {
    id: "user-settings",
    label: "User settings",
    to: "/settings/user",
    icon: faSlidersH,
    description: "Your preferences and notifications",
    scope: "user_settings:read",
  },
];

const allowed = (scopes, entry) =>
  !entry.scope || authHelper.hasScope(scopes || [], entry.scope);

/** The categories and entries ``scopes`` can open; empty categories go. */
export function visibleMenu(scopes) {
  return MENU.map((category) => ({
    ...category,
    entries: category.entries.filter((entry) => allowed(scopes, entry)),
  })).filter((category) => category.entries.length > 0);
}

export function visibleAccount(scopes) {
  return ACCOUNT.filter((entry) => allowed(scopes, entry));
}

function within(path, prefix) {
  return path === prefix || path.startsWith(`${prefix}/`);
}

/** The entry a path belongs to: the one with the longest matching prefix. */
export function entryOf(path, menu = MENU, account = ACCOUNT) {
  let best = null;
  let bestLength = -1;
  const candidates = [
    ...menu.flatMap((category) =>
      category.entries.map((entry) => ({ entry, category })),
    ),
    ...account.map((entry) => ({ entry, category: null })),
  ];
  for (const { entry, category } of candidates) {
    if ((entry.excludes || []).some((prefix) => within(path, prefix))) {
      continue;
    }
    for (const prefix of [entry.to, ...(entry.sections || [])]) {
      if (within(path, prefix) && prefix.length > bestLength) {
        best = { entry, category };
        bestLength = prefix.length;
      }
    }
  }
  return best;
}

/** Every page, flat, for the quick switcher. */
export function searchablePages(scopes) {
  return [
    ...visibleMenu(scopes).flatMap((category) =>
      category.entries.map((entry) => ({ ...entry, category: category.label })),
    ),
    ...visibleAccount(scopes).map((entry) => ({
      ...entry,
      category: "Account",
    })),
  ];
}
