# Indicators

Security controls want **unique indicators**. MISP data is **attributes**:
the same `198.51.100.7` can sit in dozens of events from several feeds and
MISP servers, with different tags, `to_ids` flags and timestamps. Rather than
leaving every consumer to de-duplicate it and merge the context itself,
misp-workbench keeps one **consolidated indicator** per type and value.

Under ***internals*** → ***indicators*** you can search them. Click a row to
see its organisations, sources, tags and events.

## What an indicator holds

An indicator is built from every live attribute with its type and value.
Attributes in deleted events don't count.

| Field | Content |
|---|---|
| `uuid` | Derived from type and value, so it is the same on every instance and across rebuilds |
| `type`, `value` | What it is. The same value with another type (`ip-src` and `ip-dst`) is another indicator |
| `to_ids` | `true` when at least one of its attributes is flagged for IDS (`ids_attribute_count` of `attribute_count`) |
| `categories` | The categories of its attributes |
| `first_seen`, `last_seen` | Across its attributes (their `first_seen`/`last_seen`, or else their timestamp) and the value's sightings |
| `event_count`, `events` | How many events it is in, and the 50 newest |
| `sources` | Where those events came from (a `feed`, a MISP `server`, `local`), with how many events each |
| `organisations` | The events' creator organisations, with how many events each |
| `tags` | Every tag of its attributes and their events, merged. Nothing is dropped, so an output that excludes any of them excludes the value |
| `tlp` | The **most restrictive TLP** among them (`tlp:red` over `tlp:amber+strict` over `tlp:amber` over `tlp:green` over `tlp:clear`) |
| `galaxies` | The `misp-galaxy:` tags among them |
| `sightings` | `positive`, `false_positive` and `expiration` counts, with the first and last sighting time |
| `warninglist_hits` | The enabled [warninglists](warninglists.md) any of its attributes is on |
| `deleted` | `true` on a **tombstone**: an indicator whose last live attribute went away |
| `updated_at` | When its content last changed |

Context types are not indicators and are skipped: `text`, `comment`,
`other`, `link`, `attachment`, `datetime`, `counter`, `float`, `boolean` and
`size-in-bytes`.

Sources are recorded on events from this release on. Events created earlier
count as `local` when created on this instance and `unknown` otherwise, until
their feed or server sends them again.

## How they stay current

| What | When |
|---|---|
| Attributes written (added, edited, tagged, deleted) | Within seconds: a sync every 15 seconds refreshes the values of attributes written since its last run |
| Sightings added | At the next sync |
| An event's own tags, organisation or source changed (an event tagged `tlp:red` makes its indicators red) | At the next sync |
| Hard deletes (retention, force-deleting an event) | At the hourly rebuild |

An indicator is only rewritten when its content changes, so `updated_at`
means *changed*, and incremental exports of indicators carry real changes
only. Indicators that lose their last live attribute are kept as tombstones
for 30 days, so incremental consumers learn about the removal, then purged.

To rebuild now, after restoring data or upgrading:

```bash
docker compose exec api poetry run python -m app.cli rebuild-indicators
```

## Using them

Every output can work with indicators instead of raw attributes:

| Output | How |
|---|---|
| [Exports](exports.md) | Index target **Indicators**, in `ndjson`, `text` or `cdb`. `ndjson` can be an [incremental feed](exports.md#incremental-feeds), tombstones included |
| [Streaming exports](api/streaming-exports.md) | `GET /indicators/export`, same parameters and formats as `/attributes/export` |
| [Sinks](sinks.md) | **Send consolidated indicators**: one record per value, carrying an `indicator` block |
| [Bulk lookup](api/lookup.md) | `include_indicators: true` adds each matched value's indicators |
| API | `GET /indicators` searches them, `GET /indicators/{uuid}` gets one |

## API

All endpoints need `attributes:read`.

| Endpoint | Use |
|---|---|
| `GET /indicators` | Search: `q` (Lucene; bare terms match the value), `type`, `to_ids`, `include_deleted`, `sort` (`last_seen`, `first_seen`, `event_count`, `updated_at`), `page`, `size` (up to 1,000; the first 10,000 results can be paged to) |
| `GET /indicators/{uuid}` | One indicator |
| `GET /indicators/export` | Everything matching, streamed (see [Streaming exports](api/streaming-exports.md)) |
| `GET /indicators/status` | Built, last sync, number of indicators and tombstones |

```bash
curl -s "https://workbench.example.com/indicators?q=sources.name:%22CIRCL%20OSINT%22&to_ids=true" \
  -H "Authorization: $API_KEY"
```

```json
{
  "total": 1,
  "page": 1,
  "size": 50,
  "items": [
    {
      "uuid": "67d6744d-0e83-5b7f-9c44-b28a78237fc3",
      "type": "ip-dst",
      "value": "198.51.100.7",
      "categories": ["Network activity"],
      "to_ids": true,
      "deleted": false,
      "attribute_count": 3,
      "ids_attribute_count": 2,
      "event_count": 3,
      "events": ["…", "…", "…"],
      "first_seen": 1600000000,
      "last_seen": 1748736000,
      "sources": [
        {"type": "feed", "id": 1, "name": "CIRCL OSINT", "event_count": 2},
        {"type": "server", "id": 2, "name": "Partner MISP", "event_count": 1}
      ],
      "organisations": [{"name": "CIRCL", "event_count": 3}],
      "tags": ["tlp:amber", "misp-galaxy:threat-actor=\"APT29\""],
      "tlp": "tlp:amber",
      "galaxies": ["misp-galaxy:threat-actor=\"APT29\""],
      "sightings": {"positive": 12, "false_positive": 1, "expiration": 0,
                    "first_at": 1700000000, "last_at": 1748736000},
      "warninglist_hits": [],
      "updated_at": 1748736012
    }
  ]
}
```
