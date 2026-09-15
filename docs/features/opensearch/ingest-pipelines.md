# Ingest Pipelines

Ingest pipelines process documents as they are indexed into OpenSearch. misp-workbench uses a chain of pipelines to extract and enrich IP address data in the `misp-attributes` index, and exposes the same mechanism to you as [transformation servos](../tech-lab/servos.md).

## How ingest pipelines work

If you have not met OpenSearch ingest pipelines before, this section is the short version. The [official ingest pipelines documentation](https://docs.opensearch.org/latest/ingest-pipelines/) is the full one.

### Processors and pipelines

A **processor** is one named transformation step — `set` a field, `grok` a value into parts, `lowercase` it, `date`-parse it. A **pipeline** is an ordered list of processors under a name.

```json
{
  "description": "what this pipeline is for",
  "processors": [
    { "grok":    { "field": "value", "patterns": ["..."] } },
    { "convert": { "field": "expanded.url.port", "type": "integer" } }
  ]
}
```

Each processor receives the document as `ctx` and may add, change or remove fields. The next processor sees the result of the previous one, so ordering is part of the design — `convert` above only works because `grok` has already produced the field it converts.

OpenSearch ships around forty processors. To see exactly which ones your cluster has, ask it:

```bash
GET _nodes/ingest?filter_path=nodes.*.ingest.processors
```

That matters more than it sounds: the processor list is version- and plugin-dependent, so a recipe written for Elasticsearch or for a different OpenSearch version may reference a processor you do not have.

### They run at index time, not at query time

This is the single most important thing to internalise. A pipeline runs **once**, as the document is written, and what it produces is what gets stored. It is not a view over your data.

Two consequences:

- Enriching is cheap at search time, because the work was already done and the result is a real indexed field you can query, aggregate and build a dashboard on.
- **Changing a pipeline does not change documents that are already indexed.** Adding a servo affects what arrives from that point on. Reprocessing what is already there is a separate, explicit operation ([`_update_by_query`](https://docs.opensearch.org/latest/api-reference/document-apis/update-by-query/) with a `pipeline` parameter).

### How a pipeline gets attached to an index

Three ways, and they interact:

| Mechanism | When it runs |
|---|---|
| `index.default_pipeline` setting | On every write that does not name its own pipeline |
| `index.final_pipeline` setting | On every write, after whichever of the above ran |
| `?pipeline=<name>` on the request | Instead of the default pipeline, for that request only |

Verified behaviour on OpenSearch 3.4: naming `?pipeline=` **replaces** the default pipeline but does **not** skip the final one. So a document written with an explicit pipeline still passes through `misp-attributes_final`, and therefore still through your servos.

An index setting applies to indices created *after* the template that carries it. Adding a template does not retro-fit an index that already exists — that needs an explicit `PUT /<index>/_settings`.

### Chaining

A processor can itself be a pipeline, via the [`pipeline` processor](https://docs.opensearch.org/latest/ingest-pipelines/processors/pipeline/). That is how misp-workbench keeps one named entry point per phase while splitting the actual work into small, separately readable pipelines.

!!! warning "A referenced pipeline must exist"
    OpenSearch's `pipeline` processor has no `ignore_missing_pipeline` option (unlike Elasticsearch's). If a chain references a pipeline that is not in the cluster, **every write to that index fails**. This is why `misp-attributes_servos.json` ships as a file with an empty processor list rather than being created on demand.

### Conditional execution

Every processor accepts an `if`, a [Painless](https://docs.opensearch.org/latest/api-reference/script-apis/index/) expression evaluated against the document. It matters here because every attribute type shares one index, so a processor that assumes a URL will meet plenty of hashes:

```json
{ "grok": { "field": "value", "patterns": ["..."],
            "if": "ctx.type == 'url' || ctx.type == 'uri'" } }
```

See [conditional execution](https://docs.opensearch.org/latest/ingest-pipelines/conditional-execution/).

### When a processor fails

By default a failing processor fails the whole document — the write is rejected and the data never lands. Three knobs change that:

| Option | Effect |
|---|---|
| `ignore_missing: true` | The field is absent → skip this processor quietly |
| `ignore_failure: true` | This processor threw → skip it and carry on |
| `on_failure: [ ... ]` | This processor threw → run these processors instead |

misp-workbench uses `on_failure` on every servo so a broken servo records the error on the document instead of stopping ingestion. See [handling pipeline failures](https://docs.opensearch.org/latest/ingest-pipelines/pipeline-failures/).

### Testing a pipeline before you deploy it

[`_simulate`](https://docs.opensearch.org/latest/ingest-pipelines/simulate-ingest/) runs a pipeline body against sample documents and returns the result without storing anything or creating the pipeline:

```bash
POST _ingest/pipeline/_simulate
{
  "pipeline": { "processors": [ ... ] },
  "docs": [ { "_source": { "type": "url", "value": "http://evil.com:8080/path" } } ]
}
```

This is exactly what the servo editor's **Dry run** button calls, and what the API runs before it will accept a servo.

## Pipeline chain

The `misp-attributes` index template attaches two pipelines:

- **Default pipeline** (`misp-attributes_default`) — runs before the document is stored
- **Final pipeline** (`misp-attributes_final`) — runs after the default pipeline completes

Each pipeline delegates to the next step in the chain:

```
Document indexed into misp-attributes
        │
        ▼
misp-attributes_default (default pipeline)
        │  calls ▼
misp-attributes_ip_extraction
   Extracts IP from ip-src / ip-dst attributes
   → expanded.ip (single IP)
   → expanded.ip_range (CIDR notation)
        │
        ▼
misp-attributes_final (final pipeline)
        │  calls ▼
misp-attributes_ip_geoip
   Enriches expanded.ip with GeoIP data
   → expanded.ip2geo (city, country, coordinates, …)
        │  then calls ▼
misp-attributes_servos
   Transformation servos, in position order
   → whatever fields they produce
```

## Pipeline details

### misp-attributes_default

Entry point. Delegates to the IP extraction pipeline.

```json
{
  "description": "Normalization pipeline wrapper",
  "processors": [
    { "pipeline": { "name": "misp-attributes_ip_extraction" } }
  ]
}
```

### misp-attributes_ip_extraction

A Painless script that runs for `ip-src` and `ip-dst` attribute types:

- If the value contains `/` (CIDR notation), it is stored in `expanded.ip_range` as an `ip_range` field
- Otherwise, the value is stored in `expanded.ip` as an `ip` field

This enables native IP range queries and aggregations in OpenSearch.

```json
{
  "description": "Extract IP addresses from specific types and store in expanded.ip",
  "processors": [
    {
      "script": {
        "lang": "painless",
        "source": "if (ctx.type == 'ip-src' || ctx.type == 'ip-dst') { if (ctx.expanded == null) { ctx.expanded = new HashMap(); } if (ctx.value.contains('/')) { ctx.expanded.ip_range = ctx.value; } else { ctx.expanded.ip = ctx.value; } }",
        "ignore_failure": true
      }
    }
  ]
}
```

### misp-attributes_ip_geoip

Uses OpenSearch's built-in [GeoIP processor](https://docs.opensearch.org/latest/ingest-pipelines/processors/ip2geo/) to enrich `expanded.ip` with geographic data. The result is stored in `expanded.ip2geo` with fields like `country_name`, `city_name`, `location` (geo_point), and `region_name`.

```json
{
  "description": "Enrich IP with GeoIP",
  "processors": [
    {
      "geoip": {
        "field": "expanded.ip",
        "target_field": "expanded.ip2geo",
        "ignore_missing": true,
        "ignore_failure": true
      }
    }
  ]
}
```

### misp-attributes_final

Exit point. Delegates to the GeoIP enrichment pipeline, then to the servo chain.

```json
{
  "description": "Enrichments pipeline wrapper",
  "processors": [
    { "pipeline": { "name": "misp-attributes_ip_geoip" } },
    { "pipeline": { "name": "misp-attributes_servos" } }
  ]
}
```

### misp-attributes_servos

The extension point for [transformation servos](../tech-lab/servos.md) — ingest pipelines authored from the Tech Lab UI. Unlike the pipelines above, its **content** is owned by the misp-workbench API, which rebuilds it from the enabled servos after every change and again at startup.

It ships with an empty processor list, and that file is what `setup-opensearch` applies on each stack start. The empty file is not optional: OpenSearch's `pipeline` processor has no `ignore_missing_pipeline` option, so a pipeline referenced from `misp-attributes_final` must always exist or every attribute write fails. Shipping it guarantees that on a fresh cluster.

```json
{
  "description": "Tech Lab transformation servos. Managed by the misp-workbench API …",
  "processors": []
}
```

Once servos exist, the API fills it in. Each entry carries an `on_failure` handler so a servo that throws records the message on the document rather than failing the write:

```json
{
  "pipeline": {
    "name": "servo_url_parts",
    "on_failure": [
      {
        "append": {
          "field": "expanded.servo_errors",
          "value": "servo_url_parts: {{{_ingest.on_failure_message}}}"
        }
      }
    ]
  }
}
```

## Index template

The pipeline chain is wired via an index template that matches the `misp-attributes` index:

```json
{
  "index_patterns": ["misp-attributes"],
  "template": {
    "settings": {
      "index.default_pipeline": "misp-attributes_default",
      "index.final_pipeline": "misp-attributes_final"
    }
  },
  "priority": 100
}
```

This ensures every document written to `misp-attributes` passes through both pipelines automatically.

## Pipeline files

All pipeline definitions are stored in the repository and applied on startup:

| File | Pipeline |
|---|---|
| `opensearch/pipelines/misp-attributes_default.json` | Default entry point |
| `opensearch/pipelines/misp-attributes_ip_extraction.json` | IP extraction script |
| `opensearch/pipelines/misp-attributes_ip_geoip.json` | GeoIP enrichment |
| `opensearch/pipelines/misp-attributes_final.json` | Final exit point |
| `opensearch/pipelines/misp-attributes_servos.json` | Servo chain (content managed by the API) |
| `opensearch/index-templates/misp-attributes-template.json` | Index template wiring |

## Further reading

Official OpenSearch documentation:

| Topic | Link |
|---|---|
| Ingest pipelines overview | <https://docs.opensearch.org/latest/ingest-pipelines/> |
| Creating a pipeline | <https://docs.opensearch.org/latest/ingest-pipelines/create-ingest/> |
| All processors | <https://docs.opensearch.org/latest/ingest-pipelines/processors/index-processors/> |
| Conditional execution (`if`) | <https://docs.opensearch.org/latest/ingest-pipelines/conditional-execution/> |
| Handling pipeline failures | <https://docs.opensearch.org/latest/ingest-pipelines/pipeline-failures/> |
| Simulating a pipeline | <https://docs.opensearch.org/latest/ingest-pipelines/simulate-ingest/> |
| Ingest APIs | <https://docs.opensearch.org/latest/api-reference/ingest-apis/index/> |
| Painless scripting | <https://docs.opensearch.org/latest/api-reference/script-apis/index/> |

The processors used by the pipelines and templates on this page:

| Processor | Link |
|---|---|
| `append` | <https://docs.opensearch.org/latest/ingest-pipelines/processors/append/> |
| `convert` | <https://docs.opensearch.org/latest/ingest-pipelines/processors/convert/> |
| `date` | <https://docs.opensearch.org/latest/ingest-pipelines/processors/date/> |
| `fingerprint` | <https://docs.opensearch.org/latest/ingest-pipelines/processors/fingerprint/> |
| `grok` | <https://docs.opensearch.org/latest/ingest-pipelines/processors/grok/> |
| `ip2geo` | <https://docs.opensearch.org/latest/ingest-pipelines/processors/ip2geo/> |
| `lowercase` | <https://docs.opensearch.org/latest/ingest-pipelines/processors/lowercase/> |
| `pipeline` | <https://docs.opensearch.org/latest/ingest-pipelines/processors/pipeline/> |
| `remove` | <https://docs.opensearch.org/latest/ingest-pipelines/processors/remove/> |
| `script` | <https://docs.opensearch.org/latest/ingest-pipelines/processors/script/> |
| `set` | <https://docs.opensearch.org/latest/ingest-pipelines/processors/set/> |
| `trim` | <https://docs.opensearch.org/latest/ingest-pipelines/processors/trim/> |
