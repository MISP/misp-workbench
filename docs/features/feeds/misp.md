# MISP Feeds

MISP feeds follow the standard MISP feed format: a `manifest.json` index file and individual event JSON files at the same base URL.

<img src="../../../screenshots/feeds/misp-workbench-2_misp-feed.png">

Additional rules such a filtering based on _Organisations_, or _Tags_ or _Timestamp_. By default events from the last 30 days are fetched.

<img src="../../../screenshots/feeds/misp-workbench-3_misp-feed-rules.png">

## How it works

1. The worker fetches `<url>/manifest.json` to get the list of event UUIDs.
2. New or updated events are enqueued as individual fetch tasks.
3. Each event is downloaded, parsed, and stored including attributes, objects, tags, and galaxies.
4. The event is indexed in OpenSearch.

## Configuration

Beyond the [common settings](index.md#common-settings), MISP feeds support:

| Field | Description |
|---|---|
| **Rules** | Filter events by tags or organisations (JSON object, same format as MISP feed rules) |

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

<img src="../../../screenshots/feeds/misp-workbench-4_misp-feed-preview.png" style="height: 250px;">
