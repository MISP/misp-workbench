# Detection profiles

"What goes to which security control" used to be defined separately in
every output: an export's query, a feed's query, a sink's filters, `/lookup`
options, restSearch parameters. Keeping a firewall block list and the SIEM
alerting set consistent meant keeping all of those in step by hand.

A **detection profile** defines it once, by name: *Firewall block list*,
*SIEM alerting*. Every output can use a profile in place of its own filters.

<img src="../../screenshots/detection-profiles/misp-workbench-1_detection-profiles_list.png#only-light" alt="Detection profiles" style="max-width: 100%; height: auto;">
<img src="../../screenshots/detection-profiles/misp-workbench-1_detection-profiles_list-dark.png#only-dark" alt="Detection profiles" style="max-width: 100%; height: auto;">

## Rules

A profile selects [consolidated indicators](indicators.md). Every rule
narrows the selection, and an empty rule leaves nothing out.

| Rule | Keeps |
|---|---|
| **Types**, **categories** | indicators of one of these types or categories |
| **TLP ceiling** | indicators no more restrictive than this: `tlp:amber` keeps clear, green and amber. Indicators without a TLP are kept |
| **Only with tags** / **never with tags** | indicators with at least one of these tags / none of them. Patterns work: `misp-galaxy:threat-actor=*`, `workbench:validation=*` |
| **Minimum score** | a [confidence score](indicators.md#confidence-scores) at least this |
| **Last seen within** | last seen at most this many days ago |
| **Sources**: only / never | reported by one of these sources / not reported *only* by these. A value that a noisy feed and a trusted partner both report stays |
| **Organisations**: only / never | the same, for the organisations that created the events |
| **Minimum source trust** | reported by at least one feed or server whose [score modifier](indicators.md#source-trust) is at least this. Local and unknown sources count as 0 |
| **Only flagged for IDS** (on) | at least one attribute flagged `to_ids` |
| **Leave out warninglisted** (on) | not on an enabled [warninglist](warninglists.md) |
| **Leave out validation issues** (on) | no [validation issue](normalisation.md#validation-issues) |

A profile also says what outputs send: the **consolidated indicators**
(each value once, with its context), or the **attributes** behind them.

While you edit a profile, the editor shows how many indicators match, and a
few of them.

<img src="../../screenshots/detection-profiles/misp-workbench-2_detection-profiles_editor.png#only-light" alt="Editing a profile" style="height: 900px;">
<img src="../../screenshots/detection-profiles/misp-workbench-2_detection-profiles_editor-dark.png#only-dark" alt="Editing a profile" style="height: 900px;">

### Exploring a profile

**Explore** next to a profile, or **Explore them** in the editor, opens its
indicators in [Explore](explore.md)'s *Indicators* tab, written out as a
Lucene query you can read, refine and save like any other search:

```text
deleted:false AND NOT tlp:("tlp:amber+strict" OR "tlp:red") AND score:>=50
  AND to_ids:true AND NOT _exists_:warninglist_hits AND NOT _exists_:validation_issues
```

The query selects what the profile does. There is one exception: sources and
organisations to leave out, and minimum source trust, have no direct query
form. They are written as "reported by a source other than these", listing
the sources present at that moment, so a source that appears later isn't
covered by the query, though it is by the profile. Explore says so when it
happens. The query is also available from the API:
`GET /detection-profiles/{id}/query` returns `{query, snapshot}`, and
`POST /detection-profiles/query` does the same for unsaved rules.

Two profiles are created on install, to adjust or copy:

| Profile | Rules |
|---|---|
| **SIEM alerting** | flagged for IDS, score ≥ 50, TLP amber or less, no warninglisted values, no validation issues |
| **Firewall block list** | IPs, domains, hostnames and URLs; flagged for IDS, score ≥ 70, seen in the last 90 days, TLP amber or less, no warninglisted values, no validation issues |

## Using a profile

| Output | How |
|---|---|
| [Exports and feeds](exports.md) | Pick the profile in the export form (`profile_id` in the API). The query then only narrows it (`*` for all of it). Available as NDJSON, plain text and Wazuh CDB. An incremental feed needs a profile of indicators |
| [Streaming exports](api/streaming-exports.md) | `GET /indicators/export?profile=…` streams the indicators, `GET /attributes/export?profile=…` the attributes behind them. `since=` works on the indicator export |
| [Sinks](sinks.md) | Pick the profile in the sink form. It replaces the sink's selection filters, and its granularity decides between attributes and consolidated indicators. The sink's own exclusions (**Never with tags**, by default `tlp:red`, and **Leave out warninglisted**) still hold on top of the profile. Sends from notebooks and reactor scripts keep the profile's exclusions too: TLP ceiling, excluded tags, warninglists and validation issues |
| [Bulk lookup](api/lookup.md) | `profile` keeps only values the profile selects |
| [restSearch](api/rest-search.md) | `profile` keeps only attributes the profile selects. Like `excludeDecayed`, this applies after paging |
| Indicators | `GET /indicators?profile=…` |

`profile` takes a profile's id or its name.

Outputs that judge records one at a time (sinks, `/lookup`, restSearch) check
each value's indicator, and fail closed:

- **Values written in the last few seconds.** They may not have an indicator
  yet, so they are judged on one built from the attribute and its event:
  the event gives the source and organisation, and the score is computed
  the usual way. Every rule applies. A rule that can't be confirmed, such as
  a source rule for an attribute whose event isn't known, keeps the value
  out.
- **Values whose indicator hasn't caught up yet.** An indicator can be a
  sync behind its attributes. The rules that keep things out (TLP ceiling,
  excluded tags, warninglists, validation issues) are also checked on the
  attribute as it is now, so a value tagged `tlp:red` a second ago doesn't
  leave on a stale indicator.

## Membership deltas: telling consumers what left

A delta that only lists what was *written* since a cursor can't tell a
block list to drop anything: an indicator can leave a profile without being
written. Its score decays, it ages out, a source's trust changes, or the
profile's own rules change. Block lists would then only grow.

Profile feeds and synced sinks keep the **member set** they last delivered
and diff it with the current one on every run:

| Action | Meaning |
|---|---|
| `add` | Joined the profile: the full indicator record |
| `update` | Still a member, and its record changed (score, tags, sightings, ...) |
| `remove` | Left the profile: `uuid`, `type`, `value` and the `reason` |

A removal's `reason` is the rule the indicator now fails: `deleted`,
`type`, `category`, `tlp`, `tags`, `excluded_tag`, `no_longer_ids`,
`warninglisted`, `validation`, `score`, `expired`, `sources`,
`excluded_source`, `organisations`, `excluded_organisation` or `trust`.

Where it applies:

- **Incremental [profile feeds](exports.md#incremental-feeds).** Each delta
  is NDJSON with one record per line, each with its `action`. The previous
  member set is the previous run's full artifact, so nothing extra is
  stored.
- **[Sinks](sinks.md) with *Keep in step with the profile*.** Every five
  minutes the sink gets adds and removals. A removal is a record with
  `action: remove`; the `act` field in CEF, `_misp_action` in GELF. The
  first sync sends every member. A failed sync is retried with the same
  changes. Before an indicator is sent, its attributes' current state is
  checked against the exclusions (TLP, excluded tags, warninglists,
  validation). An indicator a sync behind, such as one tagged `tlp:red` a
  second ago, is held back until it catches up.
- **`GET /indicators/export?profile=…&since=…`** (NDJSON or JSON). Each
  record is an `upsert` or a `remove`. A stream keeps no state, so it covers
  what it can see from the indicators alone: anything written since the
  cursor, and indicators that aged past the profile's age limit. Removals
  caused only by a source's trust or by editing the profile need a feed or
  a synced sink. A stream can also report a removal for an indicator the
  consumer never had; ignore those. Because of that, a streamed removal is
  only the `uuid` and the `reason`, never the type and value. The stream
  can't know whether the consumer ever had the indicator, and its value
  (a `tlp:red` one, say) is exactly what the profile keeps from the
  consumer.

### The consumer contract

1. Key indicators on `uuid`. It is derived from type and value, so it is
   stable.
2. Apply every delta in order: `add` and `update` upsert, `remove` deletes.
   Both are idempotent, so receiving one twice is harmless.
3. Resync from the full artifact (or a full export) periodically, and
   whenever the feed says you are too far behind. Do it after editing the
   profile, too, if you consume a stream.

A profile used by an export or a sink can't be deleted: the output would
fall back to sending everything its own query matches.

## API

| Endpoint | Scope | Use |
|---|---|---|
| `GET /detection-profiles` | `detection_profiles:read` | All profiles |
| `GET /detection-profiles/{id}` | `detection_profiles:read` | One profile |
| `GET /detection-profiles/{id}/count` | `detection_profiles:read` | How many indicators it selects now, and a few of them |
| `POST /detection-profiles/preview` | `detection_profiles:read` | The same, for rules not saved yet (`{"rules": {…}}`) |
| `POST /detection-profiles` | `detection_profiles:create` | Create one (`name`, `description`, `granularity`, `rules`) |
| `PATCH /detection-profiles/{id}` | `detection_profiles:update` | Change one |
| `DELETE /detection-profiles/{id}` | `detection_profiles:delete` | Delete one (409 while an export or sink uses it) |

Every built-in role can read profiles. Changing them takes the create,
update or delete scope, which only admins have by default.

[Local allowlists](https://github.com/MISP/misp-workbench/issues/440) will
become a profile rule once they exist.
