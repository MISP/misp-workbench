# Hunts

Hunts are saved searches that run against the OpenSearch index. Each hunt stores a Lucene query, an index target, and a run history so you can track how match counts evolve over time.

## Hunt types

### OpenSearch (`opensearch`)

Executes a Lucene query against one of the three OpenSearch indices (`attributes`, `events`, or `correlations`). Returns up to 100 matching documents per run.

### Rulezet (`rulezet`)

Looks up detection rules from [rulezet.org](https://rulezet.org) by Vuln ID. The `query` field must be a vulnerability identifier (e.g. `CVE-2021-44228`, `ghsa-q4qf-26fw-9qw6`). Results contain the detection rules published for that vulnerability. The `index_target` field is ignored for rulezet hunts.

```json
{
  "name": "Log4Shell detection rules",
  "query": "CVE-2021-44228",
  "hunt_type": "rulezet"
}
```

## Concepts

| Term | Description |
|---|---|
| **Query** | Lucene query (opensearch) or Vuln ID (rulezet) |
| **Index target** | Which index to search: `attributes`, `events`, or `correlations` (opensearch only) |
| **Hunt type** | `opensearch` for Lucene queries, `rulezet` for Vuln-ID-based rule lookup |
| **Status** | `active` or `paused` — paused hunts are skipped during scheduled runs |
| **Run history** | Each execution stores a timestamp and match count |

## Creating a hunt

A hunt requires a name and a Lucene query. All other fields are optional.

```json
POST /hunts/
{
  "name": "Suspicious PowerShell",
  "description": "Detect encoded PowerShell command lines",
  "query": "value:*powershell* AND value:*-enc*",
  "hunt_type": "opensearch",
  "index_target": "attributes",
  "status": "active"
}
```

Required scopes: `hunts:create`

## Running a hunt

```
POST /hunts/{hunt_id}/run
```

Executes the stored query immediately and returns matching hits. The result is also cached so it can be retrieved later without re-running the query.

Required scopes: `hunts:run`

## Retrieving results

```
GET /hunts/{hunt_id}/results
```

Returns the most recently cached result set (populated by the last `/run` call).

Required scopes: `hunts:read`

## Run history

```
GET /hunts/{hunt_id}/history
```

Returns a list of past run timestamps and match counts, useful for spotting spikes or regressions.

```json
[
  { "run_at": "2025-01-15T10:00:00Z", "match_count": 3 },
  { "run_at": "2025-01-16T10:00:00Z", "match_count": 7 }
]
```

Required scopes: `hunts:read`

## API reference

| Method | Path | Description | Scopes |
|---|---|---|---|
| `GET` | `/hunts/` | List all hunts (paginated) | `hunts:read` |
| `POST` | `/hunts/` | Create a hunt | `hunts:create` |
| `GET` | `/hunts/{id}` | Get a hunt | `hunts:read` |
| `PATCH` | `/hunts/{id}` | Update a hunt | `hunts:update` |
| `DELETE` | `/hunts/{id}` | Delete a hunt | `hunts:delete` |
| `POST` | `/hunts/{id}/run` | Run a hunt and cache results | `hunts:run` |
| `GET` | `/hunts/{id}/results` | Get cached results | `hunts:read` |
| `GET` | `/hunts/{id}/history` | Get run history | `hunts:read` |

## Index targets (opensearch hunts only)

### Attributes

Searches the `attributes` index — the most granular level. Useful for hunting specific indicator values.

```
value:192.168.1.0/24 AND type:ip-src
```

### Events

Searches the `events` index for event-level metadata.

```
info:*ransomware* AND threat_level_id:1
```

### Correlations

Searches the `correlations` index to find attribute values that appear across multiple events.

```
value:evil.example.com
```

## Rulezet hunt results

When a rulezet hunt runs, each hit in the results represents a detection rule returned by [rulezet.org](https://rulezet.org) for the given Vuln ID. The `total` field reflects the number of rules found.

```json
{
  "hunt": { "id": 5, "name": "Log4Shell detection rules", ... },
  "total": 3,
  "hits": [
    { "rule_id": "...", "format": "sigma", "content": "..." },
    ...
  ]
}
```
