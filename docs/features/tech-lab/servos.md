# Transformation Servos

A **transformation servo** is an [OpenSearch ingest pipeline](../opensearch/ingest-pipelines.md) that you author from the UI. It runs on every attribute as it is indexed into `misp-attributes`, so a servo is the place to normalise, parse and enrich messy inbound data before it reaches search, correlation and hunts.

misp-workbench already ships a chain of ingest pipelines (IP extraction, composite value splitting, GeoIP). Those are managed in the repository and are read-only. Servos are the extension point on top of them.

!!! tip "New to ingest pipelines?"
    [How ingest pipelines work](../opensearch/ingest-pipelines.md#how-ingest-pipelines-work) covers processors, conditional execution, failure handling and `_simulate` in a few minutes, and links the official OpenSearch documentation for the detail. Worth reading before writing your first servo.

!!! info "Where to find it"
    The **tech-lab** → **transformation servos** view splits into two tabs: **Custom servos**, where you create, dry-run, enable, disable and delete your own, and **System pipelines**, a read-only view of what misp-workbench ships. The active tab is in the URL (`?tab=system`), so a link to either survives a refresh.

The landing tab lists your servos and nothing else — the shipped pipelines never push them below the fold:

<img src="../../../screenshots/tech-lab/transformation-servos/misp-workbench-1_tech-lab_transformation-servos_index.png#only-light">
<img src="../../../screenshots/tech-lab/transformation-servos/misp-workbench-1_tech-lab_transformation-servos_index-dark.png#only-dark">

The second tab holds the shipped chain. Each entry expands to show its definition, and none of them can be edited from here:

<img src="../../../screenshots/tech-lab/transformation-servos/misp-workbench-2_tech-lab_transformation-servos_system-pipelines.png#only-light">
<img src="../../../screenshots/tech-lab/transformation-servos/misp-workbench-2_tech-lab_transformation-servos_system-pipelines-dark.png#only-dark">


!!! warning "This is ingestion logic"
    An enabled servo runs on **every** attribute written to `misp-attributes`. It only affects documents indexed **after** it is enabled — existing attributes are untouched.

## Concepts

### Servo

A servo is a name, a slug, and a list of OpenSearch [processors](https://docs.opensearch.org/latest/ingest-pipelines/processors/index-processors/). The definition lives in Postgres; misp-workbench compiles it into an ingest pipeline called `servo_<slug>` and keeps OpenSearch in step.

The slug is fixed once created (it names the pipeline) and may not start with `misp-`, which is reserved for the shipped system pipelines.

### The servo chain

Servos hang off a chain pipeline called `misp-attributes_servos`, which the shipped `misp-attributes_final` pipeline invokes as its last step:

```
Document indexed into misp-attributes
        │
        ▼
misp-attributes_default  → IP extraction, composite value splitting
        │
        ▼
misp-attributes_final    → GeoIP enrichment
        │  calls ▼
misp-attributes_servos       ← rebuilt by the API from your servos
        ├ servo_<slug>        (enabled, in position order)
        └ servo_<slug>
```

Because servos run last, a servo can read everything the system pipelines produced: `expanded.ip`, `expanded.ip_range`, `expanded.value_parts`, `expanded.ip2geo`.

Only **enabled** servos are in the chain. Disabling a servo removes both its chain entry and its pipeline; re-enabling puts them back.

### Order

Servos run in the order shown in the list, and order is part of the design: a servo can read a field an earlier one produced, exactly as the shipped pipelines do. Use the arrows in the **order** column to move one earlier or later. The whole order is sent in a single call, so the chain is rebuilt once rather than once per servo.

### Failure isolation

A servo that throws must never stop an attribute from being indexed. Every chain entry carries an `on_failure` handler that appends the message to `expanded.servo_errors` on the document and carries on. A mistake in a servo therefore degrades enrichment; it does not break ingestion.

Failures are counted per servo and shown as a red badge next to its status, with the distinct messages behind them in the tooltip — otherwise a servo erroring on every single document would still look healthy. To find the affected documents:

```
expanded.servo_errors:*
```

### Servos that discard attributes

A servo may use the [`drop` processor](https://docs.opensearch.org/latest/ingest-pipelines/processors/drop/) — deduplication is a legitimate reason to. Understand what it means first:

- A dropped attribute **never reaches `misp-attributes`**. It is not searchable, correlated, hunted or exported, and nothing recovers it short of re-importing the source.
- OpenSearch reports a dropped document as a *success* (HTTP 200, `result: noop`). misp-workbench checks that result, so `POST /attributes/` answers **422** with an explanation instead of a misleading 201, and no correlation, reactor or notification work is queued for a document that does not exist. An attribute arriving through a feed is counted as a failed row and logged.
- Any servo containing a `drop` — including one nested inside `foreach` or `on_failure` — is flagged with a **discards** badge in the list, and the editor shows a warning before you save.

If your aim is to *identify* duplicates rather than throw them away, use the **Deduplication fingerprint** template instead. It marks them and keeps the data.

### Dry run

Before a servo can be saved, OpenSearch must accept it. The editor's **Dry run** panel posts the processors to OpenSearch's `_simulate` endpoint together with a sample attribute document and shows the transformed result — or the exact parse error. Nothing is written by a dry run, and the **save** button stays disabled until one succeeds.

### Templates

The editor ships starter processor sets for the common cases. The picker lists them by a one-line summary; the full description below is what gets copied into the servo's own description when you apply one.

| Template | Summary |
|---|---|
| **URL parts** | Split url / uri into scheme, domain, port and path |
| **Canonical value** | Trim and lowercase case-insensitive indicator types |
| **Deduplication fingerprint** | Hash type + value so duplicates can be grouped |
| **Timestamp normalization** | Parse mixed first_seen formats into one date type |

Picking a template fills in the processors, the description and a matching sample document; edit from there.

#### What each one produces

**URL parts** — a `grok` pattern gated on `ctx.type`, followed by a `convert` so the port is a number rather than a string.

| Field | Example |
|---|---|
| `expanded.url.scheme` | `http` |
| `expanded.url.domain` | `evil.com` |
| `expanded.url.port` | `8080` (integer) |
| `expanded.url.path` | `/path?q=1` |

Only `url` and `uri` attributes are touched. A value that does not parse is skipped rather than failing, so a malformed URL still gets indexed.

**Canonical value** — copies `value`, trims it, then lowercases it for the types where case carries no meaning (`domain`, `hostname`, `url`, `uri`, `md5`, `sha1`, `sha256`, `sha512`, `email-src`, `email-dst`). Everything else keeps its case, because a `comment` or `text` attribute is not case-insensitive.

| Field | Example |
|---|---|
| `expanded.canonical` | `evil.com` (from `"  EVIL.com "`) |

The original `value` is never modified — this is a parallel field, so nothing about what the analyst entered is lost.

**Deduplication fingerprint** — builds a scratch object of type + value, hashes it with the `fingerprint` processor, then removes the scratch field.

| Field | Example |
|---|---|
| `expanded.fingerprint` | `SHA-1@2.16.0:z9QFx1EcWAHbVJflzndYKxQDhyI=` |

The same indicator arriving from five feeds gets one fingerprint, so a terms aggregation on that field counts distinct indicators rather than distinct documents. Nothing is dropped — this flags duplicates, it does not remove them.

**Timestamp normalization** — a `date` processor trying ISO 8601, `YYYY-MM-DD HH:MM:SS` and unix epoch seconds, in that order.

| Field | Example |
|---|---|
| `expanded.first_seen_normalized` | `2026-01-02T03:04:05.000Z` |

Ordering matters: epoch seconds are tried last, because a bare digit string would otherwise be read as milliseconds and land in 1970. Attributes with no `first_seen` are skipped.

The editor pairs the processor JSON with a dry run against a sample attribute document:

<img src="../../../screenshots/tech-lab/transformation-servos/misp-workbench-3_tech-lab_transformation-servos_editor.png#only-light">
<img src="../../../screenshots/tech-lab/transformation-servos/misp-workbench-3_tech-lab_transformation-servos_editor-dark.png#only-dark">


## Worked example

Feeds write URLs as opaque strings, so pivoting on the host means substring matching. A servo can split them at ingestion time:

```json
[
  {
    "grok": {
      "field": "value",
      "patterns": [
        "%{URIPROTO:expanded.url.scheme}://%{IPORHOST:expanded.url.domain}(?::%{POSINT:expanded.url.port})?%{URIPATHPARAM:expanded.url.path}?"
      ],
      "if": "ctx.type == 'url' || ctx.type == 'uri'",
      "ignore_missing": true,
      "ignore_failure": true
    }
  },
  {
    "convert": {
      "field": "expanded.url.port",
      "type": "integer",
      "ignore_missing": true,
      "ignore_failure": true
    }
  }
]
```

Indexing `http://EVIL.com:8080/path?q=1` then produces:

```json
{
  "type": "url",
  "value": "http://EVIL.com:8080/path?q=1",
  "expanded": {
    "url": { "scheme": "http", "domain": "EVIL.com", "port": 8080, "path": "/path?q=1" }
  }
}
```

`expanded.url.domain` is now a field you can search, aggregate and build a dashboard on.

A saved servo shows its compiled pipeline name, sync state and processors:

<img src="../../../screenshots/tech-lab/transformation-servos/misp-workbench-4_tech-lab_transformation-servos_view.png#only-light">
<img src="../../../screenshots/tech-lab/transformation-servos/misp-workbench-4_tech-lab_transformation-servos_view-dark.png#only-dark">


!!! tip "Guard every processor"
    Attributes of every type flow through the same pipeline. Gate a processor with an `if` on `ctx.type`, and set `ignore_missing` / `ignore_failure` where a field may legitimately be absent, so the servo is a no-op for the types it does not care about.

## Permissions

The feature is admin-level. Four scopes gate it:

| Scope | Grants |
|---|---|
| `servos:read` | See the pipeline inventory and servo definitions. Also gates the menu entry. |
| `servos:create` | Create servos and run dry runs. |
| `servos:update` | Edit, enable, disable and reorder servos. |
| `servos:delete` | Delete servos. |

Every create, update and delete is written to the [audit log](../api/audit-logs.md) as `servo.created` / `servo.updated` / `servo.reordered` / `servo.deleted`, with the compiled processors in the metadata.

## Operational notes

**Existing attributes are not reprocessed.** Enabling a servo changes what happens to documents indexed from that point on. Re-indexing what is already there is not yet available from the UI.

**The chain is rebuilt at API startup.** `setup-opensearch` re-applies every repo-managed pipeline on each stack start, which resets `misp-attributes_servos` to empty. The API re-syncs the chain as it boots, so enabled servos come back on their own. This doubles as the escape hatch: if a servo is misbehaving badly, restarting the stack falls back to the system pipelines until the API syncs again.

**A `servo_*` pipeline with no database row is left alone.** misp-workbench only ever deletes pipelines it knows it created, so a pipeline left behind by a restored database, or created by another tool, shows up at the bottom of the **System pipelines** tab under *Other pipelines* as read-only rather than being cleaned up. That section is only rendered when there is something in it.
