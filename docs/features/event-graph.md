# Event Graph

The event graph draws an event as a picture: the event at the centre, its
attributes and objects hanging off it, its tags shared between whatever
carries them, and the references between objects as labelled edges. It is the
view for the question a table answers badly — *how do these pieces connect?*

It lives on the ***Graph*** tab of any event.

<img src="../../screenshots/event-graph/misp-workbench-1_event-graph-tabs.png#only-light">
<img src="../../screenshots/event-graph/misp-workbench-1_event-graph-tabs-dark.png#only-dark">

## Reading the graph

| Node | What it is |
|---|---|
| Event | The root. Every attribute and object hangs off it. |
| Object | A MISP object, labelled with its name and its meta-category. |
| Attribute | An indicator, labelled with its value and its type. Object attributes hang off their object, not off the event. |
| Tag | A coloured chip, shared by everything that carries it — one node however many parents point at it. |
| Galaxy cluster | Drawn when the event carries structured galaxy data, grouped by galaxy type. |

Edges come in two kinds. Structural edges say *belongs to* — event to
attribute, object to its attributes. **Object references** are relationships
in their own right and are drawn in their own colour with their
`relationship_type` as the label, so `contains` and `communicates-with` read
as the chain they describe.

Click a node to see its details, double click to open it — an attribute node
takes you to that attribute, an object node to that object.

## View modes

A large event is unreadable if every leaf is drawn at once, so the toolbar
offers three ways to draw the same event.

### Detailed

Everything, flat: every attribute, object and tag as its own node. Best for
small events, and for seeing exactly what an event holds.

<img src="../../screenshots/event-graph/misp-workbench-2_event-graph-detailed.png#only-light">
<img src="../../screenshots/event-graph/misp-workbench-2_event-graph-detailed-dark.png#only-dark">

### Grouped

Each parent's attributes and tags collapse behind a single summary node
apiece, carrying a count and an expand handle. A large event reads as a
handful of clickable groups rather than a hairball. Objects and the event
itself are unaffected.

<img src="../../screenshots/event-graph/misp-workbench-3_event-graph-grouped.png#only-light">
<img src="../../screenshots/event-graph/misp-workbench-3_event-graph-grouped-dark.png#only-dark">

### Relations

Only what takes part in an object reference. No event root, no tags, no
standalone attributes — an object appears when it references something, is
referenced itself, or owns a referenced attribute, and nests its own
attributes behind its expand handle. This is the view for the structure of an
incident rather than its inventory.

<img src="../../screenshots/event-graph/misp-workbench-4_event-graph-relations.png#only-light">
<img src="../../screenshots/event-graph/misp-workbench-4_event-graph-relations-dark.png#only-dark">

An event with no object references produces an empty relations view, which
says so rather than showing a blank canvas.

## How it is built

The graph is rendered client-side by
[pivotick](https://github.com/Pivotick/Pivotick), with
[pivotick-graph-transformer](https://github.com/ecrou-exact/Pivotick-graph-transformer)
turning MISP JSON into the nodes and edges it draws. Both are git submodules
under `frontend/submodules/`.

The transformer reads MISP's own event format, so rather than teach it a
second schema the event is served in that shape:

```
GET /events/{event_uuid}/misp-json
```

This returns `{"Event": {...}}` with the capitalised `Attribute`, `Object`,
`Tag` and `ObjectReference` collections MISP uses, produced by the same
`Event.to_misp_format()` serializer that pushes events to a remote MISP
server — one canonical format, not two.

Two things separate it from `GET /events/{event_uuid}`:

- It pulls the event **full**. The graph needs every attribute and object,
  including the attributes inside objects and the references between them,
  not just the event header.
- It leaves **attachment payloads out**. The graph only draws metadata, and
  inlining base64 blobs would dwarf the rest of the response.

The tab is lazy: the graph code and the MISP icon set are only fetched the
first time someone opens it, and the tab is part of the URL
(`/events/{uuid}/graph`) so a particular view can be linked and refreshed.

### Tag colours

A tag chip is drawn in the tag's own `colour`. Tags created ad hoc — by typing
a name that no loaded taxonomy defines — get a colour derived from a hash of
their name, which is stable but arbitrary. Load the taxonomies before tagging
if you want `tlp:amber` to come out amber.

Note also that an event stores a copy of each tag as it was at tagging time,
so recolouring a tag does not retroactively change events already carrying it.
