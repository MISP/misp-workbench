# MISP Feeds

MISP feeds follow the standard MISP feed format: a `manifest.json` index file and individual event JSON files at the same base URL.

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

Use the **Preview** button on the Add Feed form to verify the URL is reachable and returns a valid manifest before saving.
