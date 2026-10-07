# Streaming exports

`GET /attributes/export` and `GET /events/export` dump everything that matches a search query. They are designed for SIEMs and scripts that pull indicator sets on a schedule:

- **Streamed.** Results are paged out of OpenSearch and written as they arrive, so memory stays flat however much matches.
- **Incremental.** `since=` returns only what changed, deletions included.
- **Cheap to poll.** Each response carries an `ETag` and `Last-Modified`. An unchanged poll is answered with `304 Not Modified` after a single aggregation query.

| Endpoint | Scope | Formats |
|---|---|---|
| `GET /attributes/export` | `attributes:read` | `json`, `ndjson`, `csv`, `text`, `cdb` |
| `GET /events/export` | `events:read` | `json`, `ndjson` |

For MISP-style filtering (tags, `to_ids`, published, ...) and MISP's response shape, use [restSearch](rest-search.md) instead.

## Parameters

| Parameter | Default | Description |
|---|---|---|
| `query` | all | Lucene query, as in Explore (e.g. `type:ip-dst AND to_ids:true`) |
| `format` | `json` | See below |
| `include_deleted` | `false` | Include soft-deleted records |
| `since` | — | Attributes only. Return only attributes written at or after this time, soft-deleted ones included (see [Incremental pulls](#incremental-pulls)) |

## Formats

| Format | Content |
|---|---|
| `json` | A JSON array of `{_index, _id, _source}` documents |
| `ndjson` | One document (`_source`) per line |
| `csv` | `uuid,event_uuid,object_uuid,category,type,value,comment,to_ids,deleted,timestamp,updated_at,tags` |
| `text` | One value per line |
| `cdb` | A [Wazuh CDB list](https://documentation.wazuh.com/current/user-manual/ruleset/cdb-list.html): `value:type` per line, with keys containing `:` (IPv6, URLs) quoted |

`text` and `cdb` skip values that span several lines (`text` attributes); `cdb` also skips values containing `"`.

## Incremental pulls

Every write to an attribute (create, edit, tag change, soft delete, servo reprocessing) is stamped into `updated_at` by the attributes' final ingest pipeline. `since` filters on it.

1. Do a full pull and keep the `X-Export-Timestamp` response header.
2. Next time, send that value as `since`. You get only the attributes written in between. Soft-deleted ones come back with `"deleted": true`, so you can remove them.
3. Repeat, each time using the latest `X-Export-Timestamp`.

```bash
curl -s -D headers.txt -H "Authorization: $API_KEY" \
  "https://workbench.example.com/attributes/export?format=ndjson&query=to_ids:true" > full.ndjson
SINCE=$(grep -i '^x-export-timestamp' headers.txt | cut -d' ' -f2 | tr -d '\r')

curl -s -H "Authorization: $API_KEY" \
  "https://workbench.example.com/attributes/export?format=ndjson&query=to_ids:true&since=$SINCE"
```

`X-Export-Timestamp` is taken by the server before reading begins. A write that lands during an export is picked up again by the next delta rather than lost, and client clock skew doesn't matter.

`since` also accepts an ISO date or a relative age (`30m`, `12h`, `7d`).

`since` needs a format that can express a deletion: `json`, `ndjson` or `csv`. With `text` or `cdb` it returns `400`. Rebuild those lists from a full pull instead.

!!! warning "Deltas don't see hard deletes"
    Force-deleting an event or retention purges remove documents outright, and a delta can't report what no longer exists. Soft-deleting an *event* also doesn't touch its attributes. Pair deltas with a periodic full pull (daily, say) to resynchronise.

Attributes indexed before `updated_at` was introduced have no write stamp until their next write. Full pulls return them; deltas pick them up once they change.

## Conditional requests

Send the `ETag` back as `If-None-Match`, or the `Last-Modified` as `If-Modified-Since`. If nothing matching the request has changed, the response is `304` with no body.

```bash
curl -s -o /dev/null -w '%{http_code}\n' -H "Authorization: $API_KEY" \
  -H 'If-None-Match: "3f2a..."' \
  "https://workbench.example.com/attributes/export?format=cdb&query=to_ids:true"
```

The ETag covers the request (query, format, filters), the number of matching documents and their newest `updated_at`. Any write to a matching attribute, or a hard delete, therefore changes it. Event exports don't carry a write stamp, so their ETag only changes when the number of matching events does.
