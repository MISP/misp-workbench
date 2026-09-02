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

All three read endpoints require the `analyst_data:read` scope.

### Relationship vocabulary

`GET /analyst-data/relationship-types` returns the MISP relationship
vocabulary shipped by the `misp-objects` submodule, which populates the
relationship type picker. A type outside that list is still accepted on
create -- MISP allows free-form relationship types, and one arriving over sync
must not be rejected.

## Writing analyst data

| Endpoint | Purpose | Scope |
|---|---|---|
| `POST /analyst-data/notes` | Add a note | `analyst_data:create` |
| `POST /analyst-data/opinions` | Add an opinion (0-100 plus a comment) | `analyst_data:create` |
| `POST /analyst-data/relationships` | Add a relationship | `analyst_data:create` |
| `PUT /analyst-data/{uuid}` | Partial update | `analyst_data:update` |
| `DELETE /analyst-data/{uuid}` | Soft delete | `analyst_data:delete` |

Every create takes `object_uuid` and `object_type` naming the parent. Replying
to a note means passing that note's uuid with `object_type: "Note"`.

### Who may change analyst data

Analyst data is attributed content -- it records its author and creating
organisation -- so it follows the ownership rule MISP applies rather than the
scope-only model used for events, attributes and objects:

- **Only the creating organisation may edit or delete it.** Anyone else gets a
  403, even holding `analyst_data:update` / `analyst_data:delete`. A role with
  the `*` scope bypasses this, matching how local tags are handled.
- **Analyst data pulled from a remote server or a feed therefore cannot be
  rewritten locally**, which is the point: it is another instance's
  commentary.
- Where no organisation was recorded, the check falls back to the author's
  email. Data with neither is not editable by anyone but an admin.

In the UI, edit and delete are shown to the author (and to admins) and hidden
otherwise. That is narrower than the API allows -- the token carries the
user's email, not their org uuid -- but it never offers an action that would
be refused.

Notes on behaviour:

- **Authorship is taken from the token**, never the request body.
- **The parent must exist.** A create against an unknown uuid is a 404 rather
  than analyst data pointing at nothing.
- **`event_uuid` is resolved server side** -- from the attribute or object, or
  inherited from the parent note when replying -- so the event scoped read
  finds everything belonging to an event however deeply it is nested.
- **Updates are partial**, and a field belonging to another type is rejected
  with a 400 rather than silently stored (an `opinion` on a `Note`, say).
- **Deletes are soft and cascade to replies** — but only to replies the caller
  owns. The document stays so a later sync of the same uuid does not resurrect
  it, and nested replies go with their parent rather than being left stranded
  under a note that no longer reads. Another organisation's reply on a shared
  thread is left intact rather than destroyed as collateral, so it survives
  even though it is no longer reachable from the thread it hung off.

## In the UI

Analyst data appears in three places, each with add, reply, edit and delete
where the user's scopes allow:

- **Event view** -- an *Analyst Data* card, alongside Reports.
- **Attribute rows** -- a toggle in the actions column expands the analyst data
  for that attribute. It loads only when expanded, so an event with many
  attributes does not fire a request per row.
- **Object cards** -- a collapsible *Analyst data* section in the card footer,
  loaded on the same terms.

Threads render nested under their parent, indented up to four levels so a deep
discussion stays readable. Opinions show their 0-100 score with the matching
MISP band (*Strongly disagree* through *Strongly agree*).

A relationship can point at an **event**, an **attribute** or an **object**.
The picker takes the target type first and then searches that index remotely,
so it works on instances with more records than a dropdown could hold.
Changing the type clears the selection, since the previous one belonged to a
different index.

Attribute and object search back this: `GET /attributes/search` already
existed, and `GET /objects/search` was added alongside it, matching an
object's template name, comment, description and uuid.

A rendered relationship shows the target's type, its name, and a link to it --
the event's info, the attribute's value with its type and category, or the
object's template name with its comment. Only the uuid and type are stored, so
the record is looked up and cached by type and uuid, which means several
relationships pointing at the same thing cost one request. A target that no
longer exists reads "no longer available" rather than linking into a 404, which
is what happens when a relationship arrives over sync ahead of what it points
at.
