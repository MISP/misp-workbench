# Hunts

Hunts are saved searches that run against the OpenSearch index. Each hunt stores a Lucene query, an index target, and a run history so you can track how match counts evolve over time.

## Hunt types

### OpenSearch (`opensearch`)

Executes a Lucene query against one of the three OpenSearch indices (`attributes`, `events`, or `correlations`). Returns up to 100 matching documents per run.

### Rulezet (`rulezet`)

Looks up detection rules from [rulezet.org](https://rulezet.org) by Vuln ID. The `query` field must be a vulnerability identifier (e.g. `CVE-2021-44228`, `ghsa-q4qf-26fw-9qw6`). Results contain the detection rules published for that vulnerability. The `index_target` field is ignored for rulezet hunts.

## Concepts

| Term | Description |
|---|---|
| **Query** | Lucene query (opensearch) or Vuln ID (rulezet) |
| **Index target** | Which index to search: `attributes`, `events`, or `correlations` (opensearch only) |
| **Hunt type** | `opensearch` for Lucene queries, `rulezet` for Vuln-ID-based rule lookup |
| **Status** | `active` or `paused` — paused hunts are skipped during scheduled runs |
| **Run history** | Each execution stores a timestamp and match count |


## Creating a _Hunt_
1. Go to the ***hunt*** menu option in the main nav bar and click the ***+ New Hunt*** button.
    - _OpenSearch_ hunt:
    
    <img src="../screenshots/hunts/misp-workbench-1_hunts_new-opensearch-hunt.png" style="height: 500px;">
    
    - _Rulezet_ hunt:
    
    <img src="../screenshots/hunts/misp-workbench-2_hunts_new-rulezet-hunt.png" style="height: 500px;">

2. Click the eye icon on the newly created hunt to view its details. To run the hunt immediately, click the ***Run Now*** button.
    <img src="../screenshots/hunts/misp-workbench-3_hunts_view-opensearch-hunt.png" style="max-width: 100%; height: auto;">

3. Once results are available, you can see the matches and the delta compared to the previous run.

    <img src="../screenshots/hunts/misp-workbench-4_hunts_view-opensearch-hunt-matches.png" style="max-width: 100%; height: auto;">

4. When a hunt produces a new match or its results differ from the previous run, the user receives a notification.

    <img src="../screenshots/hunts/misp-workbench-5_hunts_view-opensearch-hunt-matches-notification.png" style="max-width: 100%; height: auto;">

5. You can schedule the hunt to run periodically using the ***Schedule*** widget, which supports hourly, daily, or weekly automatic runs. For more granular control, you can define a custom recurring scheduled task.

### Creating a scheduled task for a _Hunt_

1. Go to ***Internals*** → ***Tasks*** to open the scheduled tasks view, then click the ***+ New*** button.
    <img src="../screenshots/hunts/misp-workbench-6_hunts_scheduled-task-add-button.png" style="max-width: 100%; height: auto;">
2. Select ***run_task*** as the task type, then select the hunt you want to run periodically. The run frequency can be defined using a fixed interval or a crontab expression for more granular scheduling.
    <img src="../screenshots/hunts/misp-workbench-7_hunts_scheduled-task-add-scheduled-hunt.png" style="height: 500px;">
3. You can pause a scheduled task at any time.
    <img src="../screenshots/hunts/misp-workbench-8_hunts_scheduled-task-created-scheduled-hunt.png" style="max-width: 100%; height: auto;">


## Creating a _Hunt_ using the API

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

## Running a _Hunt_

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
