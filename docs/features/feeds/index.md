# Feeds

misp-workbench supports four feed source formats. Each feed is fetched either on demand or on a configurable schedule (hourly, daily, weekly). Feeds can be sourced either from a remote URL or from a file [uploaded directly to misp-workbench](local-files.md).

| Format | Description |
|---|---|
| [MISP](misp.md) | Full MISP feed — events with attributes, objects, tags, and galaxies |
| [CSV](csv.md) | Delimited text file — one indicator per row, configurable column mapping |
| [JSON](json.md) | JSON array, object, or NDJSON — dot-notation field mapping |
| [Freetext](freetext.md) | Plain text — one indicator per line, type auto-detected or fixed |

## Common settings

All feed types share a set of base settings:

| Field | Description |
|---|---|
| **Name** | Display name for the feed |
| **Provider** | Organisation or source name |
| **Input source** | `Network` (fetch from URL) or `Upload file` — see [Local File Feeds](local-files.md) |
| **URL** | Remote URL of the feed (network mode only) |
| **Distribution** | MISP distribution level for ingested attributes |
| **Enabled** | Whether the feed is active |
| **Fixed Event** | If on, all fetches append to a single event; if off, a new event is created per fetch |
| **Update interval** | Automatic fetch schedule (hourly / daily / weekly / disabled) — hidden in upload mode |
| **Fetch immediately** | Enqueue an immediate fetch when the feed is created — hidden in upload mode |
| **Advanced settings** | A separate, collapsed section: **Authentication** (an auth header sent with every request; network mode only) and indicator scoring (a score modifier and cap for what the feed reports). Its header shows what is set, e.g. *auth header: Authorization · score cap 80* |

## Default feed list

A curated list of well-known public feeds is bundled at `api/app/defaults/default-feeds.json`. When adding a feed, click **Select from defaults** to browse and auto-populate the form.

<img src="../../screenshots/feeds/misp-workbench-1_default-feeds.png#only-light">
<img src="../../screenshots/feeds/misp-workbench-1_default-feeds-dark.png#only-dark">

## Scheduled tasks

Each feed with an update interval creates a **RedBeat** scheduled task in Redis. Scheduled tasks can be viewed and managed in the Tasks section of the UI or directly in Flower at http://localhost:5555.

Deleting a feed also deletes all its associated scheduled tasks.

## Ingestion runs

Each fetch of a feed (and each pull of a MISP server) is an **ingestion run**, ingested by the dedicated `ingest-worker` so that a large feed never holds up user actions or periodic jobs:

- **One run per feed.** Fetching a feed that is already queued or being fetched is skipped, so a schedule firing during a long fetch doesn't ingest the feed twice.
- **A limited number at once.** At most `ingest.max_concurrent_runs` runs (runtime setting, default 2; 0 for no limit) ingest at the same time. The others wait as *queued* and start as slots free up.
- **In batches.** A MISP feed's events are ingested a few at a time, and concurrent runs take turns, rather than every event being queued up front.
- **Stoppable.** Disabling or deleting a feed cancels its run; `DELETE /feeds/{id}/run` (or `/servers/{id}/run`) cancels it explicitly. The run closes as *cancelled* at once; only a batch being ingested at that moment still completes. Events a run did not get to are fetched by the next one.
- **Self-healing.** A run that makes no progress for 45 minutes (its worker was killed mid-batch) is restarted, or closed if it has nothing left, by a periodic watchdog, so it doesn't hold its slot until it expires. Stopping the `ingest-worker` normally lets the batches in progress finish first (`stop_grace_period: 5m`).
- **Pausable.** Setting `ingest.paused` stops taking events from every source; runs keep their place and carry on when it is unset.

The feeds and servers lists show each source's run in progress, or how its last one ended. A feed's or server's page shows the run's progress, with a **Cancel** button, and the last run's outcome and error. `GET /feeds/{id}/run` (and `/servers/{id}/run`) returns the same: the run in progress, with how many events it listed, ingested, failed and has left, and the last finished run. Feed and server requests time out instead of waiting on an unresponsive source.

**Admin → Runtime settings → ingest** sets the limit and pauses ingestion. **Admin → Diagnostics → Queues** shows the messages waiting on each background queue, the workers consuming it (a queue with none is flagged: its tasks never run), and every run in progress or waiting for a slot (`GET /diagnostics/queues`).

## A feed's events

A feed's page lists its 10 most recently ingested events, linking to each, and **See all in Explore** opens Explore on every event from the feed (`source.type:feed AND source.id:<id>`) over all time rather than Explore's default last 30 days. `GET /feeds/{id}/events?limit=10` returns the list and the total.

Events record where they came from (`source`) and when they were first written here (`created_at`, epoch seconds; never changed by updates). Their `timestamp` is the source's own, so it says when an event last changed upstream, not when it arrived. Events ingested before `created_at` was recorded have none, and are listed after those that do.

For MISP feeds, the magnifying glass on the feed's row opens the [feed explorer](misp.md#exploring-a-feed).
