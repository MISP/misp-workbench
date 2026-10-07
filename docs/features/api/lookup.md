# Bulk lookup

`/lookup` answers the question a SIEM asks when it enriches an alert: *are any
of these values known indicators, and what do we know about them?* It is
built for high request rates where nearly every value is **not** an indicator.

| Endpoint | Use |
|---|---|
| `POST /lookup` | Up to 10,000 values per request |
| `GET /lookup?value=…` | One value per request, for per-key lookup adapters such as Graylog's HTTP JSONPath adapter |
| `GET /lookup/cache` | Prefilter status: built, last sync, number of values |

Required scope: `attributes:read`.

```bash
curl -s https://workbench.example.com/lookup \
  -H "Authorization: $API_KEY" -H "Content-Type: application/json" \
  -d '{"values": ["198.51.100.10", "192.0.2.1", "evil.example.com"]}'
```

```json
{
  "checked": 3,
  "matched": 1,
  "candidates": 1,
  "source": "cache",
  "took_ms": 4.2,
  "matches": [
    {
      "value": "198.51.100.10",
      "attribute_count": 2,
      "attributes": [
        {
          "uuid": "…", "type": "ip-dst", "category": "Network activity",
          "to_ids": true, "comment": "", "timestamp": 1700000002,
          "first_seen": null, "last_seen": null, "tags": ["tlp:amber"],
          "event": {
            "uuid": "…", "info": "APT29 campaign", "threat_level_id": 1,
            "published": true, "org": "CIRCL", "tags": ["misp-galaxy:threat-actor=\"APT29\""]
          }
        }
      ]
    }
  ]
}
```

Only matched values are listed. Values are compared exactly (case-sensitive),
as in MISP.

| Parameter | Default | Description |
|---|---|---|
| `values` | — | Values to check (`POST`), duplicates ignored, at most 10,000 (`413` above) |
| `value` | — | The value to check (`GET`) |
| `to_ids_only` | `true` | Only attributes flagged for IDS count as matches. `false` matches any live attribute |
| `max_attributes` | `10` | Attributes returned per matched value, newest first (up to 100). `attribute_count` always has the total. A response carries at most 50,000 attributes overall, so large batches get fewer per value (5 for 10,000 candidates) |

## How it stays fast

A Redis set holds the value of every live `to_ids` attribute. A lookup first
asks Redis which of its values are in the set, in a single `SMISMEMBER` round
trip, and only those **candidates** reach OpenSearch. OpenSearch confirms each
one and returns its context. A batch of misses never touches OpenSearch at
all.

The set is a prefilter, never the source of truth. It must never miss a real
indicator, but it may hold stale values; those are filtered out when
OpenSearch verifies them.

- **New indicators** are added by a background sync **every 15 seconds**. It
  reads the attributes whose `updated_at` moved since the previous sync, so it
  sees every write path: the API, server pulls, feeds, bulk ingest, servos,
  false-positive feedback. An indicator can be invisible to `/lookup` for up
  to about 15 seconds after it is written.
- **Removed indicators** (deleted, or `to_ids` turned off) stay in the set
  until the **hourly rebuild**, which builds a fresh set and swaps it in
  atomically. Until then they cost one OpenSearch check and are not
  returned.
- **Before the first build** (a fresh install, or after Redis was flushed),
  every lookup goes to OpenSearch (`"source": "opensearch"`) and a rebuild is
  queued.
- **If Redis is unreachable**, lookups fall back to OpenSearch rather than
  fail.

`to_ids_only: false` bypasses the prefilter, since it only holds IDS values,
and asks OpenSearch about every value.

To rebuild the set immediately, for example after restoring data:

```bash
docker compose exec api poetry run python -m app.cli rebuild-lookup-cache
```

!!! note
    Attributes indexed before the `updated_at` stamp existed are only picked up
    by the rebuild, not by the 15-second sync. The first rebuild after an
    upgrade covers them.
