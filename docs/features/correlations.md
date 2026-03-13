# Correlations
Correlations identify attributes that share a common value across different events. They are stored in the `misp-attribute-correlations` OpenSearch index and can be queried, regenerated, or deleted via the API.

<img src="../../screenshots/correlations/misp-workbench-1_correlations-view.png">

Correlations are computed automatically when an attribute is added or updated. To force a full re-run across all your data, go to ***internals*** → ***correlations*** and click the ***Re-run Correlations*** button. This may take some time depending on how large is your dataset.

## How it works

When a correlation job runs, every attribute in the `misp-attributes` index is compared against all other attributes from different events using one or more match strategies. Matches are written to the `misp-attribute-correlations` index as correlation documents.

Each correlation document records:

| Field | Description |
|---|---|
| `source_attribute_uuid` | UUID of the attribute that triggered the match |
| `source_event_uuid` | Event the source attribute belongs to |
| `target_attribute_uuid` | UUID of the matching attribute |
| `target_attribute_type` | MISP type of the target attribute |
| `target_attribute_value` | Value of the target attribute |
| `target_event_uuid` | Event the target attribute belongs to |
| `match_type` | How the match was found (`term`, `prefix`, `fuzzy`, `cidr`) |
| `score` | OpenSearch relevance score |


## Correlating Events
When attributes within an _Event_ have correlations, a _Related Events_ widget displays the number of correlations and the UUID of each related _Event_.

<img src="../../screenshots/correlations/misp-workbench-2_correlations-event-view.png">


When an _Attribute_ has a correlation, it displays a <span style="color: rgb(255, 193, 7);">:fontawesome-solid-sitemap:</span> icon.

<img src="../../screenshots/correlations/misp-workbench-3_correlations-attribute-row.png" style="height: 150px;">

Clicking the <span style="color: rgb(255, 193, 7);">:fontawesome-solid-sitemap:</span> icon opens a modal with the correlation details for that _Attribute_.

<img src="../../screenshots/correlations/misp-workbench-4_correlations-attribute-correlation-modal.png" style="height: 300px;">

## Match types

| Type | Description |
|---|---|
| `term` | Exact value match |
| `prefix` | Shared value prefix (configurable length, default 10 characters) |
| `fuzzy` | Approximate match using edit distance (default `AUTO` fuzziness) |
| `cidr` | IP-in-CIDR containment for IP attribute types |

Active match types and tuning parameters are controlled by runtime settings:

| Setting key | Default | Description |
|---|---|---|
| `correlations.matchTypes` | `["term", "cidr"]` | Which match strategies to apply |
| `correlations.prefixLength` | `10` | Characters compared for prefix matches |
| `correlations.fuzzynessAlgo` | `"AUTO"` | OpenSearch fuzziness value |
| `correlations.maxCorrelationsPerDoc` | `1000` | Max matches stored per attribute |
| `correlations.opensearchFlushBulkSize` | `100` | Bulk write buffer size |

## Running correlations via the API

Enqueues a Celery task that scans all attributes and generates correlation documents.

```
POST /correlations/run
```

Returns a task object with a `task_id` you can use to monitor progress via the tasks API.

Required scopes: `correlations:create`

## Querying correlations

```
GET /correlations/
```

Supports optional filters:

| Parameter | Description |
|---|---|
| `source_attribute_uuid` | Filter by source attribute |
| `source_event_uuid` | Filter by source event |
| `target_attribute_uuid` | Filter by target attribute |
| `target_event_uuid` | Filter by target event |
| `match_type` | Filter by match strategy |
| `page` | Page number (default 1) |
| `size` | Page size (default 10, max 100) |

Required scopes: `correlations:read`

## Top correlated events

Returns the 10 events most correlated with a given source event, ranked by correlation count.

```
GET /correlations/events/{source_event_uuid}/top
```

Required scopes: `correlations:read`

## Stats

Returns aggregate statistics: total correlation count, top 10 correlating events, and top 10 correlating attributes.

```
GET /correlations/stats
```

Required scopes: `correlations:read`

## Deleting correlations

Drops and recreates the `misp-attribute-correlations` index, removing all stored correlations. Run `POST /correlations/run` afterwards to regenerate.

```
DELETE /correlations/
```

Required scopes: `correlations:delete`

## API reference

| Method | Path | Description | Scopes |
|---|---|---|---|
| `GET` | `/correlations/` | List correlations (paginated, filterable) | `correlations:read` |
| `POST` | `/correlations/run` | Enqueue a full correlation scan | `correlations:create` |
| `GET` | `/correlations/stats` | Aggregate statistics | `correlations:read` |
| `GET` | `/correlations/events/{uuid}/top` | Top events correlated with a given event | `correlations:read` |
| `DELETE` | `/correlations/` | Delete all correlations | `correlations:delete` |
