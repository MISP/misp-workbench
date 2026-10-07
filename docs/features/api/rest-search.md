# MISP-compatible restSearch

misp-workbench implements a subset of MISP's `restSearch` API so that tools built for MISP can query it without changes. This includes Splunk's MISP42 app, the Wazuh MISP integration, Graylog MISP lookup adapters and PyMISP's `search()`.

| Endpoint | Scope | Returns |
|---|---|---|
| `POST` / `GET /attributes/restSearch` | `attributes:read` | Matching attributes |
| `POST` / `GET /events/restSearch` | `events:read` | Matching events |

Parameters go in a JSON body (`POST`, MISP's usual form; the legacy `{"request": {...}}` wrapper is accepted) or in the query string (`GET`). Parameter names are case-insensitive.

Authenticate with an [API key](api-keys.md) sent MISP-style as the raw `Authorization` header value, or with a Bearer token.

```bash
curl -s https://workbench.example.com/attributes/restSearch \
  -H "Authorization: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"returnFormat": "csv", "to_ids": 1, "published": 1, "last": "7d", "type": ["ip-dst", "domain"]}'
```

Responses are streamed: the API pages through OpenSearch and writes results as it goes, so large result sets don't need to fit in memory.

## Filter syntax

Filters that take a list of values follow MISP's conventions:

- A scalar or a list is an **OR**: `"type": ["ip-dst", "domain"]`.
- A `!` prefix negates a value: `"tags": ["!tlp:red"]`.
- The explicit form is `{"OR": [...], "AND": [...], "NOT": [...]}`.
- `%` is a case-insensitive wildcard: `"value": "%.example.com"`.

Booleans accept `1`/`0`/`true`/`false`; `[0, 1]` means "either".

Timestamps accept epoch seconds, a relative age (`30m`, `12h`, `7d`, `2w`) or an ISO date. A single value means "since"; `[from, to]` is an inclusive window.

## Attribute filters

| Parameter | Matches |
|---|---|
| `value`, `type`, `category`, `object_relation` | Attribute fields (exact, or `%` wildcard) |
| `uuid` | Attribute uuid **or** its event's uuid |
| `to_ids` | IDS flag |
| `deleted` | Defaults to `0` (exclude soft-deleted attributes) |
| `timestamp`, `attribute_timestamp` | Attribute timestamp |
| `tags` | Attribute tags **or** tags of the attribute's event, as in MISP |
| `published`, `eventid`, `eventinfo`, `org`, `threat_level_id` | Event fields |
| `last`, `publish_timestamp` | Event publish timestamp |
| `event_timestamp` | Event timestamp |
| `from`, `to`, `date` | Event date |
| `limit`, `page` | Pagination (1-based page) |

`org` accepts an organisation name, numeric id or uuid. `eventid` accepts a numeric id or an event uuid.

Output options:

| Parameter | Effect |
|---|---|
| `returnFormat` | `json` (default), `csv` or `text` (one value per line) |
| `includeEventTags` | Adds the event's tags to each attribute's `Tag` list with `"inherited": 1` |
| `includeContext` | Adds event date, threat level, analysis, publication state, `Orgc` and event tags to the `Event` block |

The CSV columns match MISP's defaults: `uuid,event_id,category,type,value,comment,to_ids,date,object_relation,attribute_tag,object_uuid,object_name,object_meta-category`.

## Event filters

`/events/restSearch` accepts the event filters above, with `timestamp` meaning the event timestamp. `tags` matches event tags. Attribute filters (`value`, `type`, `category`, `object_relation`, `to_ids`, `attribute_timestamp`) select events that contain a matching attribute.

| Parameter | Effect |
|---|---|
| `metadata` | Return events without their attributes and objects |
| `withAttachments` | Inline the base64 payload of malware samples and attachments |

Only `returnFormat: json` is supported for events.

## Differences from MISP

- **Identifiers.** Events and attributes created in misp-workbench have no numeric MISP id; `id` and `event_id` then carry the uuid instead. MISP accepts uuids wherever an id is expected, so links back to the event still resolve. Data pulled from a MISP server keeps its original ids.
- **Unsupported parameters are ignored.** These include `enforceWarninglist`, `includeDecayScore`, `includeCorrelations`, `requested_attributes` and `searchall`. Warninglist filtering is tracked in [#413](https://github.com/MISP/misp-workbench/issues/413).
- **Return formats.** Formats other than `json`, `csv` and `text` (STIX, OpenIOC, Suricata, ...) return `400 Bad Request`. Use [Exports](../exports.md) for STIX.
- **No row-level filtering.** Results are not filtered by distribution or sharing group. Any key with the read scope sees all data.
