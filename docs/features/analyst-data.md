# Analyst Data

Analyst data is the commentary MISP carries alongside indicators: free-text
**notes**, scored **opinions**, and typed **relationships** between objects.
misp-workbench captures all three when it pulls from a remote MISP server or
fetches a MISP-format feed, and exposes them for reading through the API.

## What is captured

Analyst data is captured wherever MISP can attach it to a synced event:

- the event itself
- its attributes, including attributes inside objects
- its objects
- its event reports
- other analyst data — a note can carry notes and opinions of its own

Each note, opinion, and relationship is stored as its own document in the
`misp-analyst-data` OpenSearch index, keyed by its `uuid` and pointed at its
parent by `object_uuid` and `object_type`. Threads are reconstructed on read
rather than nested in the index, which keeps a reply addressable on its own
and matches how MISP models the data.

Documents are upserted by uuid, so re-pulling or re-fetching an event refreshes
the analyst data already stored for it instead of duplicating it.

### Type-specific fields

| Type | Fields |
|---|---|
| `Note` | `note`, `language`, `note_type_name` |
| `Opinion` | `opinion` (0–100), `comment` |
| `Relationship` | `related_object_uuid`, `related_object_type`, `relationship_type` |

Every document also carries `uuid`, `object_uuid`, `object_type`,
`event_uuid`, `authors`, `org_uuid`, `orgc_uuid`, `created`, `modified`,
`distribution`, and `sharing_group_id`.

## Ingestion

### Server sync

`pull_event_by_uuid` requests analyst data from the remote instance with
`includeAnalystData`, and captures it after the event's attributes and objects
have landed locally.

Analyst data pulled from an **external** server has its distribution
downgraded the same way the event, its attributes, and its objects are:
community-only becomes organisation-only, and connected-communities becomes
community-only. The downgrade is skipped for servers marked internal that
belong to the host organisation. Nested analyst data is downgraded along with
its parent.

### Feed fetch

`process_feed_event` captures analyst data present in the feed's event JSON, on
both the create and the update path. Feed data is not distribution-downgraded —
a feed is already a publication decision made by its author.

## Reading analyst data

| Endpoint | Returns |
|---|---|
| `GET /analyst-data/events/{event_uuid}` | Analyst data attached directly to an event, threaded |
| `GET /analyst-data/events/{event_uuid}/all` | Every analyst data document for an event, flat |
| `GET /analyst-data/objects/{object_uuid}` | Analyst data attached to an attribute, object, event report, or any other MISP object type, threaded |

`GET /analyst-data/objects/{object_uuid}` accepts an optional `object_type`
query parameter (`Attribute`, `Object`, `EventReport`, …) to disambiguate when
the same uuid could be carried by more than one object type. Omit it to match
any type.

The threaded responses return `notes`, `opinions`, and `relationships`, each
entry carrying its own `notes`, `opinions`, and `relationships` for replies at
any depth.

All three endpoints require the `analyst_data:read` scope.
