// Canned notebook payloads used by notebooks.spec.ts. Each fixture stands
// in for what GET /tech-lab/notebooks/{id} returns — source + cell_outputs
// shaped exactly like the real backend so OutputPanel renders them without
// a live kernel.
//
// Cell IDs are real UUIDs (the source-parser regex demands hex). They must
// match the keys in cell_outputs for the OutputPanel to wire them up.

export interface CellOutput {
  output_type: "stream" | "execute_result" | "display_data" | "error";
  name?: string;
  text?: string;
  data?: Record<string, string>;
  execution_count?: number;
  traceback?: string[];
  ename?: string;
  evalue?: string;
}

export interface NotebookSummary {
  id: number;
  user_id: number;
  folder_id: number | null;
  visibility: "personal" | "global" | "library";
  name: string;
  description?: string | null;
  is_pinned?: boolean;
  last_executed_at?: string | null;
  created_at?: string;
  updated_at?: string | null;
}

export interface NotebookFull extends NotebookSummary {
  source: string;
  cell_outputs: Record<string, CellOutput[]>;
}

export const DOCS_USER_ID = 1;

const NOW = "2026-05-19T10:00:00+00:00";

// ─── helpers ──────────────────────────────────────────────────────────────

const dataframeHtml = (() => {
  const headers = [
    "date",
    "attribute_count",
    "objects",
    "organisation",
    "sharing_group",
    "distribution",
  ];
  const rows = [
    ["2025-06-20", "56", "[]", "None", "None", "3"],
    ["2026-03-13", "32", "[]", "None", "None", "3"],
    ["2017-08-25", "8", "[]", "None", "None", "3"],
    ["2026-02-12", "78", "[]", "None", "None", "3"],
    ["2026-02-18", "64", "[]", "None", "None", "3"],
  ];
  const ths = headers.map((h) => `<th>${h}</th>`).join("");
  const trs = rows
    .map(
      (r, i) =>
        `<tr><th>${i}</th>` + r.map((v) => `<td>${v}</td>`).join("") + "</tr>",
    )
    .join("");
  return (
    `<div><table class="dataframe"><thead><tr><th></th>${ths}</tr></thead>` +
    `<tbody>${trs}</tbody></table>` +
    `<p>5 rows × 27 columns</p></div>`
  );
})();

const timelineHtml = `<ul class="mwctipy-timeline">
<li><b>2026-03-13</b> — KadNap botnet IOC (mainly Asus router)</li>
<li><b>2026-02-18</b> — PFCloud - Bulletproof Hosting - Datacarry Ransomware</li>
<li><b>2026-02-12</b> — Fake 7-Zip downloads are turning home PCs into proxy nodes</li>
<li><b>2025-06-20</b> — Malicious File Creates Network Socket and Contacts fdh32fsdfhs.shop — Kunai Analysis Report sample - 2d266ab2597c72424aa21bc00718f9a13e5836e8</li>
<li><b>2017-08-25</b> — OSINT - New Arena Crysis Ransomware Variant Released</li>
</ul>`;

function tagCloudSpan(name: string, n: number, max: number): string {
  const size = (0.8 + 1.2 * (n / max)).toFixed(2);
  return `<span style="font-size:${size}em;margin:0 6px">${name} (${n})</span>`;
}

const tagCloudHtml = (() => {
  const items: Array<[string, number]> = [
    ["type:OSINT", 5],
    ["tlp:white", 5],
    ['osint:lifetime="perpetual"', 4],
    ['osint:certainty="50"', 4],
    ["tlp:clear", 4],
    ['misp-galaxy:mitre-attack-pattern="Web Protocols - T1071.001"', 2],
    ['misp-galaxy:ransomware="Dharma Ransomware"', 1],
    ['malware_classification:malware-category="Ransomware"', 1],
    ['osint:source-type="blog-post"', 1],
    ["JAG (1)", 1],
    [
      'misp-galaxy:mitre-attack-pattern="Domain Generation Algorithms - T1568.002"',
      1,
    ],
    [
      'misp-galaxy:mitre-attack-pattern="Match Legitimate Name or Location - T1036.005"',
      1,
    ],
    ['misp-galaxy:mitre-attack-pattern="Windows Service - T1543.003"', 1],
    ['misp-galaxy:mitre-attack-pattern="Code Signing - T1553.002"', 1],
    [
      'misp-galaxy:mitre-attack-pattern="System Information Discovery - T1082"',
      1,
    ],
    [
      'misp-galaxy:mitre-attack-pattern="Deobfuscate/Decode Files or Information - T1140"',
      1,
    ],
    ['misp-galaxy:mitre-attack-pattern="Masquerading - T1036"', 1],
    [
      'misp-galaxy:mitre-attack-pattern="Disable or Modify System Firewall - T1562.004"',
      1,
    ],
    [
      'misp-galaxy:mitre-attack-pattern="System Network Configuration Discovery - T1016"',
      1,
    ],
    [
      'misp-galaxy:mitre-attack-pattern="Virtualization/Sandbox Evasion - T1497"',
      1,
    ],
    ['misp-galaxy:mitre-attack-pattern="Process Discovery - T1057"', 1],
    [
      'misp-galaxy:mitre-attack-pattern="Registry Run Keys / Startup Folder - T1547.001"',
      1,
    ],
    [
      'misp-galaxy:mitre-attack-pattern="Obfuscated Files or Information - T1027"',
      1,
    ],
  ];
  const max = Math.max(...items.map(([, n]) => n));
  const spans = items.map(([name, n]) => tagCloudSpan(name, n, max)).join("");
  return `<div class="mwctipy-tag-cloud">${spans}</div>`;
})();

// ─── fixtures ─────────────────────────────────────────────────────────────

const C = {
  mmdb: {
    md1: "11111111-aaaa-4000-aaaa-000000000001",
    md2: "11111111-aaaa-4000-aaaa-000000000002",
    code1: "11111111-aaaa-4000-aaaa-000000000003",
    md3: "11111111-aaaa-4000-aaaa-000000000004",
    code2: "11111111-aaaa-4000-aaaa-000000000005",
  },
  search: { code: "22222222-aaaa-4000-aaaa-000000000001" },
  geo: { code: "33333333-aaaa-4000-aaaa-000000000001" },
  timeline: { code: "44444444-aaaa-4000-aaaa-000000000001" },
  tagcloud: { code: "55555555-aaaa-4000-aaaa-000000000001" },
  pivot: { code: "66666666-aaaa-4000-aaaa-000000000001" },
};

export const NOTEBOOKS: Record<number, NotebookFull> = {
  1: {
    id: 1,
    user_id: DOCS_USER_ID,
    folder_id: null,
    visibility: "personal",
    name: "mmdb_lookup_quickstart (fork)",
    description: "MaxMind GeoIP enrichment quickstart",
    created_at: NOW,
    updated_at: NOW,
    source: `# %% [id=${C.mmdb.md1}] markdown
# mmdb_lookup quickstart

Shows how to call an enrichment module from a notebook. We use
\`mmdb_lookup\` (MaxMind GeoIP) to resolve an IP to a country/ASN.

Fork this notebook to a personal copy before running.

# %% [id=${C.mmdb.md2}] markdown
## 1. List enabled modules

Sanity-check that \`mmdb_lookup\` is enabled in this workbench.

# %% [id=${C.mmdb.code1}] code
[m["name"] for m in mwlab.modules() if m["name"] == "mmdb_lookup"]

# %% [id=${C.mmdb.md3}] markdown
## 2. Look up a single IP

# %% [id=${C.mmdb.code2}] code
result = mwlab.enrich(value="8.8.8.8", type="ip-dst", module="mmdb_lookup")
rows = []
for obj in (result.get("results") or {}).get("Object", []):
    row = {"object": obj.get("name")}
    for attr in obj.get("Attribute", []):
        row[attr.get("object_relation")] = attr.get("value")
    rows.append(row)
mwlab.dataframe(rows)
`,
    cell_outputs: {
      [C.mmdb.code1]: [
        {
          output_type: "execute_result",
          execution_count: 1,
          data: { "text/plain": "['mmdb_lookup']" },
        },
      ],
      [C.mmdb.code2]: [
        {
          output_type: "execute_result",
          execution_count: 2,
          data: {
            "text/html": `<div><table class="dataframe"><thead><tr><th></th><th>object</th><th>country</th><th>countrycode</th><th>latitude</th><th>longitude</th><th>asn</th></tr></thead><tbody><tr><th>0</th><td>geolocation</td><td>United States</td><td>US</td><td>38</td><td>-97</td><td>NaN</td></tr><tr><th>1</th><td>geolocation</td><td>United States</td><td>US</td><td>38</td><td>-97</td><td>NaN</td></tr><tr><th>2</th><td>db_source: GeoOpen-Country, build_db: 2025-10-14</td><td></td><td></td><td></td><td></td><td>NaN</td></tr><tr><th>3</th><td>db_source: GeoOpen-Country-ASN, build_db: 2025-10-14</td><td></td><td></td><td></td><td></td><td>NaN</td></tr></tbody></table></div>`,
            "text/plain": "<pandas.DataFrame>",
          },
        },
      ],
    },
  },

  2: {
    id: 2,
    user_id: DOCS_USER_ID,
    folder_id: null,
    visibility: "personal",
    name: "search_example",
    description: "Find recent IOCs by tag",
    created_at: NOW,
    updated_at: NOW,
    source: `# %% [id=${C.search.code}] code
events = mwlab.search_events(tags=["tlp:white", "type:OSINT"], size=20)
mwlab.dataframe(events)
`,
    cell_outputs: {
      [C.search.code]: [
        {
          output_type: "execute_result",
          execution_count: 1,
          data: {
            "text/html": dataframeHtml,
            "text/plain": "<pandas.DataFrame>",
          },
        },
      ],
    },
  },

  3: {
    id: 3,
    user_id: DOCS_USER_ID,
    folder_id: null,
    visibility: "personal",
    name: "geolocation_example",
    description: "Geolocate an IP via mmdb_lookup",
    created_at: NOW,
    updated_at: NOW,
    source: `# %% [id=${C.geo.code}] code
result = mwlab.enrich("8.8.8.8", "ip-src", "mmdb_lookup")
for obj in (result.get("results") or {}).get("Object", []):
    for attr in obj.get("Attribute", []):
        print(obj.get("name"), attr.get("object_relation"), "=", attr.get("value"))
`,
    cell_outputs: {
      [C.geo.code]: [
        {
          output_type: "stream",
          name: "stdout",
          text: `geolocation country = United States
geolocation countrycode = US
geolocation latitude = 38
geolocation longitude = -97
geolocation country = United States
geolocation countrycode = US
geolocation latitude = 38
geolocation longitude = -97
geolocation text = db_source: GeoOpen-Country, build_db: 2025-10-14 11:57:45. Latitude and longitude are country average.
geolocation country = United States
geolocation countrycode = US
geolocation latitude = 38
geolocation longitude = -97
geolocation text = db_source: GeoOpen-Country-ASN, build_db: 2025-10-14 12:06:54. Latitude and longitude are country average.
asn asn = 15169
asn description = ASNorganization: GOOGLE. db_source: GeoOpen-Country-ASN, build_db: 2025-10-14 12:06:54.
`,
        },
      ],
    },
  },

  4: {
    id: 4,
    user_id: DOCS_USER_ID,
    folder_id: null,
    visibility: "personal",
    name: "timeline_example",
    description: "Build a timeline view",
    created_at: NOW,
    updated_at: NOW,
    source: `# %% [id=${C.timeline.code}] code
from IPython.display import HTML

events = mwlab.search_events(query="phishing", size=10)
HTML(render.timeline(events))
`,
    cell_outputs: {
      [C.timeline.code]: [
        {
          output_type: "execute_result",
          execution_count: 1,
          data: {
            "text/html": timelineHtml,
            "text/plain": "<IPython.core.display.HTML object>",
          },
        },
      ],
    },
  },

  5: {
    id: 5,
    user_id: DOCS_USER_ID,
    folder_id: null,
    visibility: "personal",
    name: "tag_cloud_example",
    description: "Tag cloud across recent events",
    created_at: NOW,
    updated_at: NOW,
    source: `# %% [id=${C.tagcloud.code}] code
from IPython.display import HTML

events = mwlab.search_events(size=100)
HTML(render.tag_cloud(events))
`,
    cell_outputs: {
      [C.tagcloud.code]: [
        {
          output_type: "execute_result",
          execution_count: 1,
          data: {
            "text/html": tagCloudHtml,
            "text/plain": "<IPython.core.display.HTML object>",
          },
        },
      ],
    },
  },

  6: {
    id: 6,
    user_id: DOCS_USER_ID,
    folder_id: null,
    visibility: "personal",
    name: "pivot_attribute_event_example",
    description: "Pivot from an attribute to its event",
    created_at: NOW,
    updated_at: NOW,
    source: `# %% [id=${C.pivot.code}] code
hits = mwlab.search_attributes(value="8.8.8.8")
for attr in hits:
    event = mwlab.get_event(attr["event_uuid"])
    print(attr["uuid"], "→", event["info"])
`,
    cell_outputs: {
      [C.pivot.code]: [
        {
          output_type: "stream",
          name: "stdout",
          text: `1d7c5f25-bf1c-4d8e-a20e1d0ff7c8e → Malicious File Creates Network Socket and Contacts fdh32fsdfhs.shop — Kunai Analysis Report sample - 2d266ab2597c72424aa21bc00718f9a13e5836e8
966c674f-628a-41a7-a063-00aae0ae8b65 → Fake 7-Zip downloads are turning home PCs into proxy nodes
02d09fb7-37c0-442e-a893-3eb47a7fa113 → Fake 7-Zip downloads are turning home PCs into proxy nodes
`,
        },
      ],
    },
  },
};

export const TREE_RESPONSE = {
  folders: [],
  notebooks: Object.values(NOTEBOOKS).map((n) => ({
    id: n.id,
    user_id: n.user_id,
    folder_id: n.folder_id,
    visibility: n.visibility,
    name: n.name,
    description: n.description,
    last_executed_at: n.last_executed_at,
    created_at: n.created_at,
    updated_at: n.updated_at,
  })),
  pinned_notebook_ids: [],
};

export const USER_ME = {
  id: DOCS_USER_ID,
  email: "admin@admin.test",
  role_id: 1,
  organisation_id: 1,
  disabled: false,
};
