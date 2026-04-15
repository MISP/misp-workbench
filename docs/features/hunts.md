# Hunts

Hunts are saved searches that can run against the OpenSearch index, an external vulnerability database, or a detection rule registry. Each hunt stores a query, an index target, and a run history so you can track how match counts evolve over time.

## Hunt types

### OpenSearch (`opensearch`)

Executes a Lucene query against one of the three OpenSearch indices (`attributes`, `events`, or `correlations`). Returns up to 100 matching documents per run.

### CPE (`cpe`)

Looks up CVEs affecting a product by its [CPE 2.3](https://nvd.nist.gov/products/cpe) string using [vulnerability.circl.lu](https://vulnerability.circl.lu). The `query` field must be a valid CPE string (e.g. `cpe:2.3:a:apache:log4j:2.14.1:*:*:*:*:*:*:*`). All matching CVEs are fetched across pages — there is no cap on result count. The `index_target` field is ignored for CPE hunts.

Each hit in the result contains:

| Field | Description |
|---|---|
| `cve_id` | CVE identifier (e.g. `CVE-2021-44228`) |
| `severity` | CVSS base severity (`CRITICAL`, `HIGH`, `MEDIUM`, `LOW`, or absent if not scored) |
| `description` | English description of the vulnerability |

### Rulezet (`rulezet`)

Looks up detection rules from [rulezet.org](https://rulezet.org) by Vuln ID. The `query` field must be a vulnerability identifier (e.g. `CVE-2021-44228`, `ghsa-q4qf-26fw-9qw6`). Results contain the detection rules published for that vulnerability. The `index_target` field is ignored for rulezet hunts.

### MITRE ATT&CK (`mitre-attack-pattern`)

Matches events and/or attributes tagged with one or more MITRE ATT&CK techniques. The `query` field is a comma- or newline-separated list of MITRE technique codes (e.g. `T1391`, `T1078.004`), cluster UUIDs, or full galaxy tag names. Technique codes and UUIDs are resolved against the `mitre-attack-pattern` galaxy clusters at run time — if a code cannot be resolved the hunt execution returns a `400 Bad Request`, so the `mitre-attack-pattern` galaxy must be imported and enabled first.

The `index_target` field selects where to look:

| Value | Meaning |
|---|---|
| `events` | Search the `misp-events` index only |
| `attributes` | Search the `misp-attributes` index only |
| `attributes_and_events` | Search both indices — each hit is annotated with a `_doc_kind` field (`event` or `attribute`) |

## Concepts

| Term | Description |
|---|---|
| **Query** | Lucene query (opensearch), CPE string (cpe), Vuln ID (rulezet), or MITRE technique codes (mitre-attack-pattern) |
| **Index target** | Which index to search: `attributes`, `events`, or `correlations` (opensearch); `attributes`, `events`, or `attributes_and_events` (mitre-attack-pattern) |
| **Hunt type** | `opensearch`, `cpe`, `rulezet`, or `mitre-attack-pattern` |
| **Status** | `active` or `paused` — paused hunts are skipped during scheduled runs |
| **Run history** | Each execution stores a timestamp and match count |


## Creating a _Hunt_
1. Go to the ***hunt*** menu option in the main nav bar and click the ***+ New Hunt*** button.
    - _OpenSearch_ hunt:
    
    <img src="../../screenshots/hunts/misp-workbench-1_hunts_new-opensearch-hunt.png" style="height: 500px;">
    
    - _Rulezet_ hunt:
    
    <img src="../../screenshots/hunts/misp-workbench-2_hunts_new-rulezet-hunt.png" style="height: 500px;">

    - _CPE_ hunt:
    
    <img src="../../screenshots/hunts/misp-workbench-2_hunts_new-cpe-hunt.png" style="height: 500px;">

    - _MITRE ATT&CK_ hunt:
    
    <img src="../../screenshots/hunts/misp-workbench-2_hunts_new-mitre-attack-hunt.png" style="height: 500px;">

2. Click the eye icon on the newly created hunt to view its details. To run the hunt immediately, click the ***Run Now*** button.
    <img src="../../screenshots/hunts/misp-workbench-3_hunts_view-opensearch-hunt.png" style="max-width: 100%; height: auto;">

3. Once results are available, you can see the matches and the delta compared to the previous run.

    <img src="../../screenshots/hunts/misp-workbench-4_hunts_view-opensearch-hunt-matches.png" style="max-width: 100%; height: auto;">

4. When a hunt produces a new match or its results differ from the previous run, the user receives a notification.

    <img src="../../screenshots/hunts/misp-workbench-5_hunts_view-opensearch-hunt-matches-notification.png" style="max-width: 100%; height: auto;">

5. You can schedule the hunt to run periodically using the ***Schedule*** widget, which supports hourly, daily, or weekly automatic runs. For more granular control, you can define a custom recurring scheduled task.

### Creating a scheduled task for a _Hunt_

1. Go to ***internals*** → ***tasks*** to open the scheduled tasks view, then click the ***+ New*** button.
    <img src="../../screenshots/hunts/misp-workbench-6_hunts_scheduled-task-add-button.png" style="max-width: 100%; height: auto;">
2. Select ***run_task*** as the task type, then select the hunt you want to run periodically. The run frequency can be defined using a fixed interval or a crontab expression for more granular scheduling.
    <img src="../../screenshots/hunts/misp-workbench-7_hunts_scheduled-task-add-scheduled-hunt.png" style="height: 500px;">
3. You can pause a scheduled task at any time.
    <img src="../../screenshots/hunts/misp-workbench-8_hunts_scheduled-task-created-scheduled-hunt.png" style="max-width: 100%; height: auto;">


## Creating a _Hunt_ using the API

### OpenSearch hunt

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

### CPE hunt

```json
POST /hunts/
{
  "name": "Apache Log4j 2.14.1 CVEs",
  "query": "cpe:2.3:a:apache:log4j:2.14.1:*:*:*:*:*:*:*",
  "hunt_type": "cpe",
  "status": "active"
}
```

The `index_target` field is not required for CPE hunts.

### MITRE ATT&CK hunt

```json
POST /hunts/
{
  "name": "Initial Access - Valid Accounts",
  "description": "Surface events tagged with T1078 or its sub-techniques",
  "query": "T1078, T1078.004",
  "hunt_type": "mitre-attack-pattern",
  "index_target": "attributes_and_events",
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

## Clearing history and results

```
DELETE /hunts/{hunt_id}/history
```

Deletes all run history entries and the cached result set for the hunt. The hunt itself is not deleted and can be run again. Useful for resetting a hunt after changing its query.

Required scopes: `hunts:delete`

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
| `DELETE` | `/hunts/{id}/history` | Clear run history and cached results | `hunts:delete` |

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

## CPE hunt results

When a CPE hunt runs, each hit represents a CVE affecting the specified product. All CVEs are returned — unlike OpenSearch hunts there is no 100-document cap.

```json
{
  "hunt": { "id": 7, "name": "Apache Log4j 2.14.1 CVEs", ... },
  "total": 12,
  "hits": [
    {
      "cve_id": "CVE-2021-44228",
      "severity": "CRITICAL",
      "description": "Apache Log4j2 2.0-beta9 through 2.15.0 ..."
    },
    ...
  ]
}
```

CVE IDs in the UI link directly to the corresponding record on [vulnerability.circl.lu](https://vulnerability.circl.lu).

## MITRE ATT&CK hunt results

When a MITRE ATT&CK hunt runs, each hit is an event or attribute carrying at least one of the requested technique tags. When `index_target` is `attributes_and_events`, each hit is annotated with a `_doc_kind` field so the UI can render the two kinds distinctly.

```json
{
  "hunt": { "id": 9, "name": "Initial Access - Valid Accounts", ... },
  "total": 2,
  "hits": [
    {
      "_doc_kind": "event",
      "uuid": "ba4b11b6-dcce-4315-8fd0-67b69160ea76",
      "info": "Phishing campaign targeting HR",
      "tags": [
        { "name": "misp-galaxy:mitre-attack-pattern=\"Valid Accounts - T1078\"" }
      ]
    },
    {
      "_doc_kind": "attribute",
      "uuid": "7f2fd15d-3c63-47ba-8a39-2c4b0b3314b0",
      "type": "email-src",
      "value": "attacker@example.com",
      "tags": [
        { "name": "misp-galaxy:mitre-attack-pattern=\"Cloud Accounts - T1078.004\"" }
      ]
    }
  ]
}
```

The `mitre-attack-pattern` galaxy must be imported and enabled (via `POST /galaxies/update` and `PATCH /galaxies/{id}`) before MITRE ATT&CK hunts can resolve technique codes.

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
