// Canned reactor-script payloads used by reactor.spec.ts. These mirror the
// shapes returned by the /tech-lab/reactor/* endpoints; the spec stubs
// every read endpoint so the captures don't depend on a running
// reactor_sandbox worker or real run history.

export interface ReactorScriptDetail {
  id: number;
  name: string;
  description: string;
  entrypoint: string;
  status: string;
  timeout_seconds: number;
  max_writes: number;
  triggers: Array<{
    resource_type: string;
    action: string;
    filters: Record<string, unknown>;
  }>;
  last_run_at?: string | null;
  last_run_status?: string | null;
  source_sha256: string;
  created_at: string;
  updated_at: string;
}

export const SCRIPT_ID = 1;

export const SCRIPT: ReactorScriptDetail = {
  id: SCRIPT_ID,
  name: "Add geolocation via mmdb_lookup module",
  description:
    "When a new ip-src/ip-dst attribute is created, enrich it with the mmdb_lookup enrichment module.",
  entrypoint: "handle",
  status: "active",
  timeout_seconds: 60,
  max_writes: 10,
  triggers: [
    {
      resource_type: "attribute",
      action: "created",
      filters: {},
    },
    {
      resource_type: "attribute",
      action: "updated",
      filters: {},
    },
  ],
  last_run_at: "2026-05-18T17:25:32+00:00",
  last_run_status: "success",
  source_sha256:
    "31bd6e8ff-aff62-4f4d-b0b3-ba8d54cee62c5c9f54f9c89dabfb27e7e62b8e93",
  created_at: "2026-05-10T09:00:00+00:00",
  updated_at: "2026-05-18T17:25:32+00:00",
};

export const SCRIPT_SOURCE = `def handle(ctx, payload, trigger):
    """Resolve geolocation / ASN for new ip-src/ip-dst attributes."""
    if payload.get("type") not in ("ip-src", "ip-dst"):
        return

    result = ctx.enrich(
        value=payload["value"],
        type=payload["type"],
        module="mmdb_lookup",
    )

    # mmdb_lookup returns:
    #   {"results": {"Attribute": [echo], "Object": [
    #     {"name": "geolocation", "Attribute": [{object_relation, value, ...}]},
    #     {"name": "asn", "Attribute": [...]},
    #   ]}}
    for obj in (result.get("results") or {}).get("Object", []):
        for attr in obj.get("Attribute", []):
            relation = attr.get("object_relation") or attr.get("type")
            ctx.log(
                "mmdb_lookup",
                payload["value"],
                f"{obj.get('name')}.{relation}",
                "=",
                attr.get("value"),
            )
`;

// ─── runs ────────────────────────────────────────────────────────────────

interface Run {
  id: number;
  status: string;
  created_at: string;
  started_at: string;
  finished_at: string;
  writes_count: number;
  triggered_by: {
    resource_type: string;
    action: string;
    payload?: Record<string, unknown>;
  };
  error?: string | null;
  celery_task_id?: string;
}

function buildRun(
  id: number,
  offsetMinutes: number,
  status: string,
  durationMs: number,
  writes = 0,
): Run {
  const base = new Date("2026-05-18T17:00:00Z").getTime();
  const startedAt = new Date(base - offsetMinutes * 60_000);
  const finishedAt = new Date(startedAt.getTime() + durationMs);
  return {
    id,
    status,
    created_at: startedAt.toISOString(),
    started_at: startedAt.toISOString(),
    finished_at: finishedAt.toISOString(),
    writes_count: writes,
    triggered_by: {
      resource_type: "attribute",
      action: "created",
      payload: {
        type: "ip-src",
        value: "185.220.101.42",
        attribute_uuid: "b2f30000-0001-4002-8000-000000000001",
        event_uuid: "a1f30000-0001-4001-8000-000000000001",
      },
    },
    celery_task_id: `c0ffee${id.toString().padStart(4, "0")}`,
    error:
      status === "failed"
        ? "RuntimeError: enrichment temporarily unavailable"
        : null,
  };
}

// 40 runs total; mostly success, peppered with a few failures.
export const RUNS_PAGE = {
  total: 40,
  page: 1,
  size: 100,
  items: [
    buildRun(2030, 1, "success", 38, 2),
    buildRun(2029, 4, "success", 56, 2),
    buildRun(2028, 9, "success", 41, 2),
    buildRun(2027, 13, "failed", 23, 0),
    buildRun(2026, 22, "success", 48, 2),
    buildRun(2025, 30, "success", 35, 2),
    buildRun(2024, 41, "success", 39, 2),
    buildRun(2023, 55, "failed", 27, 0),
    buildRun(2022, 65, "success", 44, 2),
    buildRun(2021, 78, "success", 42, 2),
    buildRun(2020, 92, "success", 36, 2),
    buildRun(2019, 105, "success", 51, 2),
    buildRun(2018, 121, "failed", 31, 0),
    buildRun(2017, 138, "success", 47, 2),
    buildRun(2016, 152, "success", 43, 2),
    buildRun(2015, 168, "success", 39, 2),
    buildRun(2014, 181, "success", 45, 2),
    buildRun(2013, 198, "failed", 28, 0),
    buildRun(2012, 214, "success", 50, 2),
    buildRun(2011, 230, "success", 41, 2),
    buildRun(2010, 245, "success", 38, 2),
    buildRun(2009, 261, "success", 44, 2),
    buildRun(2008, 277, "failed", 32, 0),
    buildRun(2007, 294, "success", 46, 2),
    buildRun(2006, 310, "success", 39, 2),
    buildRun(2005, 328, "success", 42, 2),
    buildRun(2004, 344, "success", 37, 2),
    buildRun(2003, 360, "failed", 29, 0),
    buildRun(2002, 376, "success", 49, 2),
    buildRun(2001, 393, "success", 43, 2),
    buildRun(2000, 410, "success", 41, 2),
    buildRun(1999, 426, "success", 38, 2),
    buildRun(1998, 442, "failed", 31, 0),
    buildRun(1997, 459, "success", 45, 2),
    buildRun(1996, 476, "success", 40, 2),
    buildRun(1995, 492, "success", 44, 2),
    buildRun(1994, 510, "success", 38, 2),
    buildRun(1993, 526, "failed", 33, 0),
    buildRun(1992, 543, "success", 47, 2),
    buildRun(1991, 561, "success", 42, 2),
  ],
};

export const RUN_LOG = `[stdout]
mmdb_lookup 8.8.8.8 geolocation.country = United States
mmdb_lookup 8.8.8.8 geolocation.countrycode = US
mmdb_lookup 8.8.8.8 geolocation.latitude = 38
mmdb_lookup 8.8.8.8 geolocation.longitude = -97
mmdb_lookup 8.8.8.8 geolocation.text = db_source: GeoOpen-Country, build_db: 2025-10-14 11:57:45.
mmdb_lookup 8.8.8.8 asn.asn = 15169
mmdb_lookup 8.8.8.8 asn.description = ASNorganization: GOOGLE.

== profile run ==
Recorded: 18:08:18  Samples: 4
Duration: 0.231     CPU time: 0.169

Profile at /code/tmp/services/tech_lab/reactor/runner.py

0.231 <module>  services/tech_lab/reactor/runner.py:1
└─ 0.231 ReactorContext.run  services/tech_lab/reactor/runner.py:128
   └─ 0.231 handle  reactor_script.py:1
      └─ 0.231 ReactorContext.enrich  services/tech_lab/reactor/runner.py:212
`;

// Sketch a small flame tree mimicking pyinstrument output. The component
// only renders bars proportionally, so we keep the shape simple but
// nested enough to look real.
export const RUN_FLAME_TREE = {
  name: "handle",
  value: 0.231,
  children: [
    {
      name: "ReactorContext.enrich",
      value: 0.198,
      children: [
        {
          name: "requests.post",
          value: 0.182,
          children: [
            {
              name: "urllib3.connectionpool.HTTPConnectionPool.urlopen",
              value: 0.176,
            },
          ],
        },
      ],
    },
    { name: "ctx.log (×7)", value: 0.022 },
    { name: "payload.get", value: 0.005 },
  ],
};

export const TEST_RUN_RESPONSE = {
  id: 9999,
  status: "success",
  created_at: "2026-05-18T18:08:18+00:00",
  started_at: "2026-05-18T18:08:18+00:00",
  finished_at: "2026-05-18T18:08:18.231+00:00",
  writes_count: 0,
  triggered_by: {
    resource_type: "attribute",
    action: "created",
  },
};

export const SCRIPTS_LIST = {
  total: 1,
  page: 1,
  size: 50,
  items: [SCRIPT],
};
