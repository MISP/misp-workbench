# Exports

Exports turn an OpenSearch query into a downloadable file. You supply a Lucene
query against the attributes or events index plus a target format; the export
runs asynchronously in a Celery task, transforms the matching documents, and
stores the artifact in local/Garage (S3) storage. The exports list tracks each
job's state and lets you download the produced file.

Exports can also be **scheduled** to re-run regularly. A scheduled export
re-runs in place — each run overwrites its own file — so a downstream consumer
can always fetch the same URL for the latest results.

## Concepts

| Term | Description |
|---|---|
| **Query** | Lucene query run against the selected index |
| **Index target** | Which index to export: `attributes` or `events` |
| **Format** | `json`, `misp` (MISP JSON), `csv`, `stix` (STIX 2.1), `ndjson`, `text` or `cdb` (Wazuh CDB list) |
| **Incremental** | `ndjson` attribute exports only: every run also stores a delta of what changed since the previous run (see [Incremental feeds](#incremental-feeds)) |
| **Status** | `queued`, `running`, `completed`, or `failed` |
| **Schedule** | Optional recurring cadence (crontab). When set, the export re-runs automatically and overwrites its previous file |
| **Schedule enabled** | Whether the schedule is active (`enabled`) or paused |

## Formats

| Format | Output | Notes |
|---|---|---|
| `json` | Raw OpenSearch `_source` documents | Passthrough dump |
| `csv` | Flattened rows of the most useful fields | Tags joined with `|` |
| `misp` | A single [MISP-schema](https://github.com/MISP/misp-rfc) event | All matches are merged into one event named after the export |
| `stix` | A STIX 2.1 bundle | Attributes are grouped into events and converted via the [misp-stix](https://github.com/MISP/misp-stix) library |
| `ndjson` | One `_source` document per line | Streamed; no record cap. Can be [incremental](#incremental-feeds) |
| `text` | One value per line | Attributes only. Streamed; no record cap. Multi-line values are skipped |
| `cdb` | A [Wazuh CDB list](https://documentation.wazuh.com/current/user-manual/ruleset/cdb-list.html), `value:type` per line | Attributes only. Streamed; no record cap. Keys containing `:` are quoted |

`ndjson`, `text` and `cdb` are streamed out of OpenSearch straight into storage, so they have no record cap and use constant memory however much matches. The other formats are built in memory and capped at 100,000 records.

!!! tip "Splunk lookups"
    The `csv` export has a header row and one indicator per row, so it can be
    used directly as a Splunk lookup table file.

!!! note "MISP format"
    The `misp` format collects every matching attribute into a **single MISP
    event** (named after the export), even when the attributes come from
    different misp-workbench events. It requires a **distribution** level and
    keeps correlation enabled. The `uuid` and `id` fields are stripped from the
    event and its attributes, so importing the file always creates fresh
    records rather than colliding with existing ones. `first_seen`/`last_seen`
    are emitted as microsecond ISO-8601 strings
    (e.g. `2026-06-19T00:00:00.000000+00:00`), and any field with a `null`
    value is omitted to keep the output compact.

!!! note "STIX limits"
    STIX 2.1 conversion is CPU-intensive, so STIX exports are capped at
    **10,000 records** — narrow the query (or use JSON/CSV) for larger result
    sets. All export jobs also have a server-side time limit; a job that exceeds
    it is marked `failed` rather than left running.

## Creating an _Export_

1. Go to ***internals*** → ***exports*** and click the ***+ New Export*** button.
2. Give the export a name, pick the search index and format, and enter the
   Lucene query. (Optional) Toggle ***Run on a schedule*** to make the export
   recurring — see [Scheduling](#scheduling) below.

    <img src="../../screenshots/exports/misp-workbench-1_exports_new-export.png#only-light" style="height: 500px;">
    <img src="../../screenshots/exports/misp-workbench-1_exports_new-export-dark.png#only-dark" style="height: 500px;">

3. Click ***Create Export***. The job is queued and runs immediately; the list
   polls until it settles to `completed` or `failed`.
4. Once `completed`, click ***Download*** to fetch the file.

Use ***Run now*** on any row to re-run an export on demand — it re-executes the
stored query and overwrites the existing file in place.

Alternatively, from the ***explore*** view use the ***Save as export…*** option
in the Download menu — it opens the export dialog pre-filled with the current
query.

<img src="../../screenshots/exports/misp-workbench-2_exports_save-as-export-menu.png#only-light" style="max-width: 100%; height: auto;">
<img src="../../screenshots/exports/misp-workbench-2_exports_save-as-export-menu-dark.png#only-dark" style="max-width: 100%; height: auto;">

<img src="../../screenshots/exports/misp-workbench-3_exports_save-as-export-modal.png#only-light" style="height: 500px;">
<img src="../../screenshots/exports/misp-workbench-3_exports_save-as-export-modal-dark.png#only-dark" style="height: 500px;">

## Scheduling

When ***Run on a schedule*** is enabled, the export is registered with the
periodic scheduler (redbeat) and re-runs on the chosen cadence. Each run reuses
the same storage location, so the **previous file is overwritten** and no extra
rows accumulate.

The schedule widget offers presets plus a custom option:

| Frequency | Runs |
|---|---|
| **Hourly** | Every hour at the chosen minute |
| **Daily** | Every day at the chosen time |
| **Weekly** | Every week on the chosen day and time |
| **Monthly** | Every month on the chosen day-of-month and time |
| **Custom** | A raw crontab expression (minute / hour / day-of-month / month / day-of-week) for full control |

Times are interpreted in the server timezone (UTC).

From the exports list you can manage a schedule at any time:

- **Pause / Resume** — temporarily stop a schedule without losing it.
- **Edit schedule** — change the cadence (or add one to an existing export).
- **Unschedule** — remove the schedule entirely; the export remains as a
  one-off and its last file is kept.

The list shows a summary of each schedule (e.g. `Daily · 02:00`), whether it is
paused, and when it last ran.

<img src="../../screenshots/exports/misp-workbench-4_exports_list.png#only-light" style="max-width: 100%; height: auto;">
<img src="../../screenshots/exports/misp-workbench-4_exports_list-dark.png#only-dark" style="max-width: 100%; height: auto;">

The ***Edit schedule*** action opens a dialog where you can change the cadence
(or add a schedule to a previously one-off export):

<img src="../../screenshots/exports/misp-workbench-5_exports_edit-schedule.png#only-light" style="height: 400px;">
<img src="../../screenshots/exports/misp-workbench-5_exports_edit-schedule-dark.png#only-dark" style="height: 400px;">

## Creating an _Export_ using the API

```json
POST /exports/
{
  "name": "Network IOCs — daily",
  "query": "type:ip-dst AND to_ids:true",
  "index_target": "attributes",
  "format": "json",
  "schedule": {
    "type": "crontab",
    "minute": "0",
    "hour": "2",
    "day_of_week": "*",
    "day_of_month": "*",
    "month_of_year": "*"
  },
  "schedule_enabled": true
}
```

`schedule` is optional — omit it (or send `null`) for a one-off export. For an
interval-based schedule instead of a crontab, use `{"type": "interval", "every": 3600}`.

Required scopes: `exports:create`

## Downloading an _Export_

```
GET /exports/{export_id}/download
```

Streams the stored artifact. Only `completed` exports can be downloaded;
otherwise the endpoint returns `409 Conflict`.

The response carries an `ETag` (the artifact's SHA-256) and `Last-Modified`
(the run that produced it). Send them back as `If-None-Match` /
`If-Modified-Since` to get a `304 Not Modified` when nothing changed. A
re-run that produces identical bytes keeps the same ETag.

Required scopes: `exports:read`

## Incremental feeds

A scheduled export is how to hand a curated indicator set to many SIEMs,
sensors or scripts. OpenSearch is queried once per run, and every consumer
downloads the stored file, so polling load on OpenSearch doesn't grow with the
number of consumers.

With **Incremental feed** enabled (`"incremental": true`; `ndjson` attribute
exports only), each run also stores a **delta**. It contains every matching
attribute written since the previous run, with soft-deleted ones included as
tombstones (`"deleted": true`). Consumers then download the full file once and
only the changes after that:

```
GET /exports/{export_id}/feed              # full feed
GET /exports/{export_id}/feed?since=CURSOR # changes since CURSOR
```

1. Fetch the full feed and keep its `X-Feed-Cursor` response header.
2. Poll with `?since=<cursor>`:
    - `200` (`X-Feed-Type: delta`): apply the records, upserting by `uuid` and removing those with `"deleted": true`. Then keep the new `X-Feed-Cursor`.
    - `304 Not Modified`: nothing new since the cursor.
    - `410 Gone`: the cursor is older than the oldest delta kept. Fetch the full feed again (step 1).

```bash
curl -s -D h.txt -H "Authorization: $API_KEY" "$API/exports/42/feed" > feed.ndjson
CURSOR=$(grep -i '^x-feed-cursor' h.txt | cut -d' ' -f2 | tr -d '\r')

curl -s -D h.txt -H "Authorization: $API_KEY" "$API/exports/42/feed?since=$CURSOR" > changes.ndjson
```

A record can appear in two consecutive deltas when it was written during a run.
Applying deltas is an upsert, so that is harmless.

Each export keeps the newest **96** deltas by default (runtime setting
`exports.delta_retention`). With an hourly schedule, a consumer can therefore
be offline for four days and still catch up from deltas.

!!! warning "What deltas can't see"
    Deltas track attribute writes. Hard deletes (force-deleting an event,
    retention purges) remove documents outright, and soft-deleting an *event*
    doesn't touch its attributes. Re-download the full feed periodically to
    resynchronise. The [streaming exports](api/streaming-exports.md#incremental-pulls)
    API has the same caveat.

The **Exports** list shows a copy button with the feed URL for incremental
exports that have run at least once.

## Managing a schedule

```json
PATCH /exports/{export_id}/schedule
{
  "schedule_enabled": false
}
```

- Send `schedule_enabled` to pause (`false`) or resume (`true`).
- Send a new `schedule` object to change the cadence.
- Send `"schedule": null` to remove the schedule (unschedule).

Required scopes: `exports:create`

## API reference

| Method | Path | Description | Scopes |
|---|---|---|---|
| `GET` | `/exports/` | List all exports (paginated) | `exports:read` |
| `POST` | `/exports/` | Create an export (runs immediately) | `exports:create` |
| `POST` | `/exports/{id}/run` | Re-run an export in place (overwrites its file) | `exports:create` |
| `GET` | `/exports/{id}` | Get an export | `exports:read` |
| `PATCH` | `/exports/{id}/schedule` | Set, pause/resume, or clear the schedule | `exports:create` |
| `GET` | `/exports/{id}/download` | Download the stored artifact | `exports:read` |
| `GET` | `/exports/{id}/feed` | Full feed or, with `?since=`, the deltas after a cursor (incremental exports) | `exports:read` |
| `DELETE` | `/exports/{id}` | Delete the export (removes its schedule and file) | `exports:delete` |
