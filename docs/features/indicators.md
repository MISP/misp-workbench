# Indicators

Security controls want **unique indicators**. MISP data is **attributes**:
the same `198.51.100.7` can sit in dozens of events from several feeds and
MISP servers, with different tags, `to_ids` flags and timestamps. Rather than
leaving every consumer to de-duplicate it and merge the context itself,
misp-workbench keeps one **consolidated indicator** per type and value.

Under ***internals*** → ***indicators*** you can search them. Click a row to
see its organisations, sources, tags and events. [Explore](explore.md) has
an *Indicators* tab too, searched with the same query as events and
attributes; its time range applies to when they were last seen.

<img src="../../screenshots/indicators/misp-workbench-1_indicators_list.png#only-light" alt="Indicators list" style="max-width: 100%; height: auto;">
<img src="../../screenshots/indicators/misp-workbench-1_indicators_list-dark.png#only-dark" alt="Indicators list" style="max-width: 100%; height: auto;">

<img src="../../screenshots/indicators/misp-workbench-2_indicators_detail.png#only-light" alt="An indicator's consolidated context" style="max-width: 100%; height: auto;">
<img src="../../screenshots/indicators/misp-workbench-2_indicators_detail-dark.png#only-dark" alt="An indicator's consolidated context" style="max-width: 100%; height: auto;">

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
| `last_reported` | When a source last reported it: its attributes alone, sightings aside. [Hit-rate expiry](detection-profiles.md#hit-rate-expiry) counts from it |
| `event_count`, `events` | How many events it is in, and the 50 newest |
| `sources` | Where those events came from (a `feed`, a MISP `server`, `local`), with how many events each |
| `organisations` | The events' creator organisations, with how many events each |
| `source_keys`, `organisation_ids` | One key per source (`feed:3`, `server:2`, `local`) and the organisations' ids, for queries that must match one source exactly: `source_keys:"feed:3"` |
| `tags` | Every tag of its attributes and their events, merged. Nothing is dropped, so an output that excludes any of them excludes the value |
| `tlp` | The **most restrictive TLP** among them (`tlp:red` over `tlp:amber+strict` over `tlp:amber` over `tlp:green` over `tlp:clear`) |
| `galaxies` | The `misp-galaxy:` tags among them |
| `sightings` | `positive`, `false_positive` and `expiration` counts, with the first and last sighting time |
| `warninglist_hits` | The enabled [warninglists](warninglists.md) any of its attributes is on |
| `validation_issues` | The [validation issues](normalisation.md#validation-issues) of its attributes, also as `workbench:validation="…"` tags |
| `review` | An analyst's decision in the [review queue](review-queue.md): `status` (approved, rejected, snoozed), `until` for a snooze, and `at`. Absent while undecided |
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

## Confidence scores

Every indicator carries a **confidence score** from 0 to 100, and the steps
that produced it (`score_breakdown`), so "why is this 42?" has an answer.
Indicators don't expire on their own in MISP. The score is what lets an IP
that was a C2 node two years ago fade out of block lists, while a malware
hash keeps its value.

The score is an indicator's, never an attribute's: attributes are left as
they are. An event's attribute list shows each attribute's indicator score
next to its value, and hovering over the badge shows the breakdown.

<img src="../../screenshots/indicators/misp-workbench-3_indicators_attribute-scores.png#only-light" alt="Scores in an event's attributes" style="max-width: 100%; height: auto;">
<img src="../../screenshots/indicators/misp-workbench-3_indicators_attribute-scores-dark.png#only-dark" alt="Scores in an event's attributes" style="max-width: 100%; height: auto;">

| Step | Default |
|---|---|
| **Base**: the best source it comes from | `local` 70, `server` 60, `feed` 50, `unknown` 50 |
| **Source trust**: that source's score modifier (see below) | 0 |
| **Organisation trust**: the most favourable modifier among the organisations that reported it | 0 |
| **Corroboration**: per further independent source | +5, up to +15 |
| **Decay**: halved every half-life of its type, counted from `last_seen` (which positive sightings move) | IPs and URLs 30 days, domains, hostnames and email addresses 90 days, hashes never, other types 180 days |
| **Sightings**: positive ones | +5 for one, +10 for three, +15 for seven or more |
| **False positives**: per false-positive sighting | −20, up to −60 |
| **Warninglist**: on an enabled [warninglist](warninglists.md) | −50 |
| **Validation**: one of its attributes has a [validation issue](normalisation.md#validation-issues) (private IP, malformed hash, ...) | −40 |
| **Cap**: when every source reporting it is capped (see below) | none |
| **Expiration**: an expiration sighting newer than any positive one | caps the score at 10 |

Below **30** an indicator counts as *decayed*, the threshold restSearch's
`excludeDecayed` uses. To keep only confident values in an output, use
`score:>=60` in an Indicators export's query, a sink's **Minimum score**,
or `min_score` in `/lookup` and `/indicators`.

Scores are computed whenever an indicator is, and the hourly rebuild applies
decay. A stored score is only rewritten when it moves by 5 points or more, or
crosses the decayed threshold. Hourly decay doesn't rewrite every indicator,
so incremental exports carry real changes.

### Settings

Under ***internals*** → ***runtime settings*** → ***scoring***, every
number above can be changed, including the half-life of each attribute type.
Scoring can also be turned off. Saving re-scores every indicator.

<img src="../../screenshots/indicators/misp-workbench-4_indicators_scoring-settings.png#only-light" alt="Scoring settings" style="max-width: 100%; height: auto;">
<img src="../../screenshots/indicators/misp-workbench-4_indicators_scoring-settings-dark.png#only-dark" alt="Scoring settings" style="max-width: 100%; height: auto;">

### Source trust

Feeds, MISP servers and organisations each have a **score modifier**
(−100 to +100) and an optional **score cap**, in their edit forms under
*Indicator scoring*. A noisy OSINT feed can be lowered and capped at 40, and
a trusted partner's MISP server raised.

An indicator is as trustworthy as its most trusted source:

- **Base.** The source with the highest base plus modifier sets it.
- **Organisations.** The most favourable organisation modifier applies. An organisation with no modifier counts as 0, so a negative modifier only matters when no other organisation reports the value.
- **Caps.** A cap holds only when every feed, server or local source reporting the value is capped. Organisation caps are combined separately: a feed capped at 40 stays capped whatever the organisations are, unless another uncapped source reports the value too.

Changing a source's trust re-scores every indicator.

### Source quality

Under ***internals*** → ***source quality***, every feed, MISP server,
local source and organisation is listed with how its indicators hold up:

| Column | Meaning |
|---|---|
| **indicators** | Live indicators it reports |
| **overlap** | Share of those also reported by another source, and which ones it overlaps with most |
| **hit rate** | Share sighted (positive sighting) within the window, 30 days by default |
| **false positives** | Share reported benign (false-positive sighting) within the window |
| **avg score**, **decayed** | Their average score, and the share below the decayed threshold |
| **trust** | Its score modifier and cap |
| **adaptive** | What adaptive trust takes off (see below) |

Each feed's, server's and organisation's own page shows the same figures in
an *Indicator quality* card. `GET /indicators/sources` returns them all, and
`GET /indicators/sources/{feed|server|organisation|local}/{id}` returns one.

<img src="../../screenshots/indicators/misp-workbench-5_indicators_source-quality.png#only-light" alt="Source quality" style="max-width: 100%; height: auto;">
<img src="../../screenshots/indicators/misp-workbench-5_indicators_source-quality-dark.png#only-dark" alt="Source quality" style="max-width: 100%; height: auto;">

### Adaptive trust

With **adaptive trust** on (*runtime settings* → *scoring*), a feed's,
server's or organisation's false-positive rate lowers its trust. The
penalty is 1 point per percent of its indicators reported benign within the
window, up to 30, and only applies once it has at least 20 indicators. A
feed with 12% of its values reported benign this month loses 12 points. The
penalty shows in each affected score's breakdown and on the source quality
page.

It is **off by default**: anyone who can report sightings can report false
positives against a source's values, and so lower its trust. The source
quality page shows what it would take off either way. Penalties are
recomputed at most every 10 minutes, and saving the scoring settings
re-scores everything.

!!! warning "Organisation trust follows what the data claims"
    Organisations are matched by their record, never by name. A feed can
    create an organisation with any name, but that doesn't make it the
    organisation you trust. Data from feeds and MISP servers does, however,
    name its own creator organisation (by uuid), so a source could attribute
    its data to an organisation you trust. To limit what an untrusted feed or
    server can reach whatever it claims, give it a **score cap**: a cap holds
    unless another uncapped source reports the same value.

## Using them

Every output can work with indicators instead of raw attributes:

| Output | How |
|---|---|
| [Exports](exports.md) | Index target **Indicators**, in `ndjson`, `text`, `cdb` or a [detection engine format](detection-formats.md) (`suricata`, `zeek`, `rpz`). `ndjson` can be an [incremental feed](exports.md#incremental-feeds), tombstones included |
| [Streaming exports](api/streaming-exports.md) | `GET /indicators/export`, same parameters and formats as `/attributes/export` |
| [Sinks](sinks.md) | **Send consolidated indicators**: one record per value, carrying an `indicator` block (with its `score`). **Minimum score** leaves out low-confidence values |
| [Bulk lookup](api/lookup.md) | `include_indicators: true` adds each matched value's indicators; `min_score` leaves out low-confidence ones |
| [restSearch](api/rest-search.md) | MISP's `includeDecayScore`, `excludeDecayed` and `score` |
| API | `GET /indicators` searches them, `GET /indicators/{uuid}` gets one |

## API

All endpoints need `attributes:read`.

| Endpoint | Use |
|---|---|
| `GET /indicators` | Search: `q` (Lucene; bare terms match the value), `type`, `to_ids`, `min_score`, `include_deleted`, `sort` (`score`, `last_seen`, `first_seen`, `event_count`, `updated_at`), `page`, `size` (up to 1,000; the first 10,000 results can be paged to) |
| `POST /indicators/scores` | The score of the indicator behind each of up to 1,000 attributes (`{"attributes": [{"type", "value"}]}`), in order |
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
