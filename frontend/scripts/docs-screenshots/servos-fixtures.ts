// Canned servo / ingest-pipeline payloads used by servos.spec.ts. These mirror
// the shapes returned by the /tech-lab/servos/* endpoints; the spec stubs every
// read endpoint so the captures don't depend on what happens to be in the
// cluster.

export interface ServoDetail {
  id: number;
  user_id: number;
  slug: string;
  name: string;
  description: string;
  processors: Array<Record<string, unknown>>;
  target_index: string;
  enabled: boolean;
  position: number;
  created_at: string;
  updated_at: string | null;
  last_synced_at: string | null;
}

export const SERVO_ID = 1;

export const URL_PARTS_PROCESSORS = [
  {
    grok: {
      field: "value",
      patterns: [
        "%{URIPROTO:expanded.url.scheme}://%{IPORHOST:expanded.url.domain}(?::%{POSINT:expanded.url.port})?%{URIPATHPARAM:expanded.url.path}?",
      ],
      if: "ctx.type == 'url' || ctx.type == 'uri'",
      ignore_missing: true,
      ignore_failure: true,
    },
  },
  {
    convert: {
      field: "expanded.url.port",
      type: "integer",
      ignore_missing: true,
      ignore_failure: true,
    },
  },
];

export const SERVO: ServoDetail = {
  id: SERVO_ID,
  user_id: 1,
  slug: "url_parts",
  name: "URL parts",
  description:
    "Split url / uri attributes into scheme, domain, port and path so infrastructure can be pivoted on without substring matching.",
  processors: URL_PARTS_PROCESSORS,
  target_index: "misp-attributes",
  enabled: true,
  position: 0,
  created_at: "2026-02-10T09:12:00Z",
  updated_at: "2026-02-11T14:03:00Z",
  last_synced_at: "2026-02-11T14:03:00Z",
};

export const CANONICAL_SERVO: ServoDetail = {
  id: 2,
  user_id: 1,
  slug: "canonical_value",
  name: "Canonical value",
  description:
    "Trim whitespace and lowercase case-insensitive indicator types into expanded.canonical, so the same indicator written two ways lines up.",
  processors: [
    {
      set: {
        field: "expanded.canonical",
        value: "{{{value}}}",
        ignore_empty_value: true,
      },
    },
    { trim: { field: "expanded.canonical", ignore_missing: true } },
  ],
  target_index: "misp-attributes",
  enabled: false,
  position: 1,
  created_at: "2026-02-12T08:00:00Z",
  updated_at: null,
  last_synced_at: null,
};

export const SERVOS_LIST = {
  items: [SERVO, CANONICAL_SERVO],
  total: 2,
  page: 1,
  size: 50,
  pages: 1,
};

export const PIPELINES = [
  {
    name: "misp-attributes_default",
    kind: "system",
    description: "Normalization pipeline wrapper",
    processor_types: [
      "pipeline:misp-attributes_ip_extraction",
      "pipeline:misp-attributes_value_parts",
    ],
    processor_count: 2,
    read_only: true,
    updated_at: null,
    servo_id: null,
    enabled: null,
  },
  {
    name: "misp-attributes_final",
    kind: "system",
    description: "Enrichments pipeline wrapper",
    processor_types: [
      "pipeline:misp-attributes_ip_geoip",
      "pipeline:misp-attributes_servos",
    ],
    processor_count: 2,
    read_only: true,
    updated_at: null,
    servo_id: null,
    enabled: null,
  },
  {
    name: "misp-attributes_ip_extraction",
    kind: "system",
    description:
      "Extract IP addresses from specific types and store in expanded.ip",
    processor_types: ["script"],
    processor_count: 1,
    read_only: true,
    updated_at: null,
    servo_id: null,
    enabled: null,
  },
  {
    name: "misp-attributes_ip_geoip",
    kind: "system",
    description: "Enrich IP with GeoIP",
    processor_types: ["geoip"],
    processor_count: 1,
    read_only: true,
    updated_at: null,
    servo_id: null,
    enabled: null,
  },
  {
    name: "misp-attributes_servos",
    kind: "system",
    description:
      "Tech Lab transformation servos. Managed by the misp-workbench API.",
    processor_types: ["pipeline:servo_url_parts"],
    processor_count: 1,
    read_only: true,
    updated_at: null,
    servo_id: null,
    enabled: null,
  },
  {
    name: "servo_url_parts",
    kind: "servo",
    description: SERVO.description,
    processor_types: ["grok", "convert"],
    processor_count: 2,
    read_only: false,
    updated_at: SERVO.updated_at,
    servo_id: SERVO_ID,
    enabled: true,
  },
];

export const FINAL_PIPELINE_DETAIL = {
  ...PIPELINES[1],
  definition: {
    description: "Enrichments pipeline wrapper",
    processors: [
      { pipeline: { name: "misp-attributes_ip_geoip" } },
      { pipeline: { name: "misp-attributes_servos" } },
    ],
  },
};

export const TEMPLATES = [
  {
    slug: "url_parts",
    name: "URL parts",
    summary: "Split url / uri into scheme, domain, port and path",
    description: SERVO.description,
    processors: URL_PARTS_PROCESSORS,
    sample_doc: { type: "url", value: "http://evil.com:8080/path?q=1" },
  },
  {
    slug: "canonical_value",
    name: "Canonical value",
    summary: "Trim and lowercase case-insensitive indicator types",
    description: CANONICAL_SERVO.description,
    processors: CANONICAL_SERVO.processors,
    sample_doc: { type: "domain", value: "  EVIL.com " },
  },
];

export const SIMULATE_RESPONSE = {
  ok: true,
  docs: [
    {
      type: "url",
      value: "http://evil.com:8080/path?q=1",
      expanded: {
        url: {
          scheme: "http",
          domain: "evil.com",
          port: 8080,
          path: "/path?q=1",
        },
      },
    },
  ],
  error: null,
};
