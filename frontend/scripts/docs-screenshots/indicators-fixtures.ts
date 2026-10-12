/**
 * Stub data for the indicators screenshots: consolidated indicators as the
 * API returns them, built around the demo dataset's overlapping values
 * (documentation ranges and example domains only).
 */
const day = 86400;
const now = Math.floor(Date.UTC(2026, 9, 10, 9, 0, 0) / 1000);

const indicator = (
  n: number,
  type: string,
  value: string,
  extra: Record<string, unknown>,
) => ({
  uuid: `1d1c0000-0001-5001-8000-0000000000${String(n).padStart(2, "0")}`,
  type,
  value,
  categories: ["Network activity"],
  to_ids: true,
  deleted: false,
  attribute_count: 1,
  ids_attribute_count: 1,
  event_count: 1,
  events: [],
  first_seen: now - 30 * day,
  last_seen: now - day,
  sources: [],
  organisations: [],
  tags: [],
  tlp: null,
  galaxies: [],
  sightings: {
    positive: 0,
    false_positive: 0,
    expiration: 0,
    first_at: null,
    last_at: null,
  },
  warninglist_hits: [],
  updated_at: now - 600,
  ...extra,
});

const feed = (id: number, name: string, event_count: number) => ({
  type: "feed",
  id,
  name,
  event_count,
});
const server = (id: number, name: string, event_count: number) => ({
  type: "server",
  id,
  name,
  event_count,
});
const local = (event_count: number) => ({
  type: "local",
  id: null,
  name: "local",
  event_count,
});

const COBALT = [
  'misp-galaxy:tool="Cobalt Strike"',
  'misp-galaxy:threat-actor="Turla"',
  'misp-galaxy:mitre-attack-pattern="Application Layer Protocol - T1071"',
];

export const INDICATORS = [
  indicator(1, "ip-dst", "198.51.100.23", {
    attribute_count: 4,
    ids_attribute_count: 4,
    event_count: 4,
    events: [
      "d3110000-0001-4001-8000-000000000001",
      "a1f30000-0001-4001-8000-000000000001",
      "5e2b9c41-7d0a-4b6e-9f3c-2a8d1e6f4b70",
      "b84c1f07-3e9d-4a52-8c6b-0f7e2d9a1c35",
    ],
    first_seen: now - 41 * day,
    last_seen: now - 2 * 3600,
    sources: [
      feed(1, "CIRCL OSINT", 2),
      server(2, "Partner MISP", 1),
      local(1),
    ],
    organisations: [
      { name: "CIRCL", event_count: 2 },
      { name: "Partner CERT", event_count: 1 },
      { name: "ACME SOC", event_count: 1 },
    ],
    tags: [
      "kill-chain:Command and Control",
      ...COBALT,
      "tlp:amber",
      "tlp:green",
    ],
    tlp: "tlp:amber",
    galaxies: COBALT,
    sightings: {
      positive: 37,
      false_positive: 0,
      expiration: 0,
      first_at: now - 20 * day,
      last_at: now - 2 * 3600,
    },
  }),
  indicator(2, "domain", "c2.example-cobalt.net", {
    attribute_count: 3,
    ids_attribute_count: 3,
    event_count: 3,
    events: [
      "d3110000-0001-4001-8000-000000000001",
      "a1f30000-0001-4001-8000-000000000001",
    ],
    first_seen: now - 41 * day,
    last_seen: now - 5 * 3600,
    sources: [feed(1, "CIRCL OSINT", 2), local(1)],
    organisations: [
      { name: "CIRCL", event_count: 2 },
      { name: "ACME SOC", event_count: 1 },
    ],
    tags: [...COBALT, "tlp:amber"],
    tlp: "tlp:amber",
    galaxies: COBALT,
    sightings: {
      positive: 15,
      false_positive: 0,
      expiration: 0,
      first_at: now - 18 * day,
      last_at: now - 5 * 3600,
    },
  }),
  indicator(
    3,
    "sha256",
    "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08",
    {
      categories: ["Payload delivery"],
      attribute_count: 2,
      ids_attribute_count: 2,
      event_count: 2,
      sources: [server(2, "Partner MISP", 2)],
      organisations: [{ name: "Partner CERT", event_count: 2 }],
      tags: ['misp-galaxy:malpedia="Cobalt Strike"', "tlp:green"],
      tlp: "tlp:green",
      galaxies: ['misp-galaxy:malpedia="Cobalt Strike"'],
      last_seen: now - 26 * 3600,
    },
  ),
  indicator(4, "url", "https://login-update.example.org/secure/verify.php", {
    categories: ["Payload delivery"],
    event_count: 1,
    sources: [feed(3, "Phishing URLs", 1)],
    organisations: [{ name: "Phishing URLs", event_count: 1 }],
    tags: ["tlp:clear", "phishing"],
    tlp: "tlp:clear",
    last_seen: now - 2 * day,
    sightings: {
      positive: 4,
      false_positive: 1,
      expiration: 0,
      first_at: now - 6 * day,
      last_at: now - 2 * day,
    },
  }),
  indicator(5, "ip-src", "203.0.113.77", {
    attribute_count: 2,
    ids_attribute_count: 1,
    event_count: 2,
    sources: [feed(1, "CIRCL OSINT", 1), server(2, "Partner MISP", 1)],
    organisations: [
      { name: "CIRCL", event_count: 1 },
      { name: "Partner CERT", event_count: 1 },
    ],
    tags: ["tlp:green", "scanner"],
    tlp: "tlp:green",
    last_seen: now - 3 * day,
  }),
  indicator(6, "domain", "www.google.com", {
    event_count: 1,
    sources: [local(1)],
    organisations: [{ name: "ACME SOC", event_count: 1 }],
    tags: ["tlp:green"],
    tlp: "tlp:green",
    warninglist_hits: ["Top 1000 website from Alexa"],
    last_seen: now - 4 * day,
  }),
];

export const INDICATORS_PAGE = {
  total: INDICATORS.length,
  page: 1,
  size: 50,
  items: INDICATORS,
};

export const INDICATORS_STATUS = {
  built: true,
  built_at: now - 1800,
  synced_at: now - 10,
  indicators: 12408,
  tombstones: 37,
  pending_sighted_values: 0,
  pending_events: 0,
};
