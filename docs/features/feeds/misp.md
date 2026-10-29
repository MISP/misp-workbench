# MISP Feeds

MISP feeds follow the standard MISP feed format: a `manifest.json` index file and individual event JSON files at the same base URL.

<img src="../../../screenshots/feeds/misp-workbench-2_misp-feed.png#only-light">
<img src="../../../screenshots/feeds/misp-workbench-2_misp-feed-dark.png#only-dark">

Additional rules such a filtering based on _Organisations_, or _Tags_ or _Timestamp_. By default events from the last 30 days are fetched.

<img src="../../../screenshots/feeds/misp-workbench-3_misp-feed-rules.png#only-light">
<img src="../../../screenshots/feeds/misp-workbench-3_misp-feed-rules-dark.png#only-dark">

## How it works

1. The worker fetches `<url>/manifest.json` to get the list of event UUIDs.
2. New or updated events are queued for the feed's [ingestion run](index.md#ingestion-runs), which downloads them a batch at a time.
3. Each event is downloaded, parsed, and stored including attributes, objects, tags, and galaxies.
4. The event is indexed in OpenSearch.

## Configuration

Beyond the [common settings](index.md#common-settings), MISP feeds support:

| Field | Description |
|---|---|
| **Rules** | Filter events by publication time, tags or organisations (JSON object, same format as MISP feed rules). Set under **Filtering rules**, collapsed on the form; its header summarises the rules applied, e.g. *Last 30 days* |

### Rules format

```json
{
  "tags": {
    "OR": ["tlp:white", "tlp:green"],
    "NOT": ["tlp:red"]
  },
  "orgs": {
    "OR": ["CIRCL"]
  }
}
```

## Testing the connection

Use the **Preview** button on the Add Feed form to verify the URL is reachable and returns a valid manifest before saving. The preview will also show how many events will be dropped after applying the configured filtering rules.

<img src="../../../screenshots/feeds/misp-workbench-4_misp-feed-preview.png#only-light" style="height: 250px;">
<img src="../../../screenshots/feeds/misp-workbench-4_misp-feed-preview-dark.png#only-dark" style="height: 250px;">

## Exploring a feed

The magnifying glass on a MISP feed's row (Ingest → Feeds) lists the events in its manifest that match its rules, with a preview of each and a button to fetch one. Each event also shows whether it is already here, linking to the local copy:

| Badge | Meaning |
|---|---|
| **ingested** | Ingested from this feed, and up to date |
| **newer in feed** | Ingested from this feed; the feed has a newer version, which the next fetch picks up |
| **from \<source\>** | Already here from another feed, a MISP server, or created locally |
| *not ingested* | Not here |

The summary above the list counts how many of the matching events were ingested from this feed. `GET /feeds/{id}/explore` returns the same: a `local` object per event (`source`, `from_feed`, `timestamp`, `outdated`) and an `ingested` count.
