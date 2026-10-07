# Sinks

A **sink** is an outbound destination that published indicators are pushed to.
When an event is published, the attributes of that event that pass the sink's
filters are sent to it, so a SIEM learns about new indicators within seconds
instead of on its next poll.

| Type | Protocol | Good for |
|---|---|---|
| `splunk_hec` | [Splunk HTTP Event Collector](https://docs.splunk.com/Documentation/Splunk/latest/Data/UsetheHTTPEventCollector), batched JSON events | Splunk |
| `gelf` | [GELF 1.1](https://go2docs.graylog.org/current/getting_in_log_data/gelf.html) over TCP, optionally TLS | Graylog |
| `syslog` | CEF in RFC 5424 syslog, UDP or TCP (TLS optional) | Wazuh, ArcSight, QRadar, any syslog collector |
| `webhook` | JSON `POST`, optionally HMAC-signed | SOAR platforms, custom scripts |

Sinks are managed under ***internals*** → ***sinks***. Because they send data
off the instance, they need the `sinks:*` scopes, which only the admin role has
by default.

## Filters

| Filter | Default | Effect |
|---|---|---|
| **Only attributes flagged for IDS** | on | Skip attributes without `to_ids` |
| **Attribute types** | all | Send only these types (e.g. `ip-src, ip-dst, domain, url`) |
| **Only with tags** | any | Send only attributes carrying at least one of these tags |
| **Never with tags** | `tlp:red` | Never send attributes carrying any of these tags |

Tag lists match the attribute's own tags **and** its event's tags, and accept
shell-style patterns (`tlp:*`, `misp-galaxy:threat-actor=*`). Soft-deleted
attributes are never sent.

## Delivery

- Each publish queues one delivery per enabled sink on the dedicated `sinks`
  Celery queue, served by its own `sinks-worker` container. A slow or
  unreachable SIEM never holds up ingestion or correlation.
- Attributes are sent in batches of 500. One HTTP request carries one batch;
  GELF and syslog over TCP reuse one connection for the whole delivery.
- A failed delivery is retried with exponential backoff: after about 30s, 1m,
  2m, 4m, 8m and 16m. After every failed attempt the error is shown on the
  sink. Once retries run out, the delivery is counted as failed.
- Delivery is **at least once**: a retry after a partial failure resends the
  batches that had already gone through. Receivers should de-duplicate on the
  attribute `uuid`.

The sinks list shows, per sink: the last successful delivery, the current
error if the last attempt failed, how many attributes have been sent and how
many deliveries failed for good.

**Test** sends a single synthetic indicator (`192.0.2.1`, a documentation
address) right away and reports whether the sink accepted it.

!!! note "What triggers a delivery"
    Publishing an event, from the UI or through `POST /events/{uuid}/publish`.
    Events pulled from MISP servers or ingested from feeds are not pushed
    automatically. Use the replay endpoint below to push one on demand, or
    give SIEMs an [incremental feed](exports.md#incremental-feeds).

## Payloads

Every indicator carries the attribute (`uuid`, `type`, `category`, `value`,
`to_ids`, `comment`, `timestamp`, `first_seen`, `last_seen`, `object_uuid`,
`object_relation`, `tags`) and its event context (`uuid`, `info`, `date`,
`threat_level_id`, `analysis`, `publish_timestamp`, `org`, `tags`).

- **Splunk HEC**: one HEC event per indicator, with the indicator as `event`,
  `time` set to the attribute timestamp, and the configured `index`,
  `sourcetype` (default `misp:attribute`) and `source`.
- **GELF**: `short_message` reads `MISP indicator <type>: <value>`. The
  fields are sent as `_misp_value`, `_misp_type`, `_misp_category`,
  `_misp_to_ids`, `_misp_tags`, `_misp_event_uuid`, `_misp_event_info`,
  `_misp_event_org`, ….
- **Syslog/CEF**: `CEF:0|MISP|misp-workbench|1.0|misp:<type>|MISP indicator|<severity>|…`.
  The severity is derived from the event threat level (high 8, medium 5, low
  3, undefined 1). The value goes in `cs1` (`mispValue`), and also in the
  matching CEF field for common types: `src`/`dst` for IPs, `dhost` for
  domains and hostnames, `request` for URLs, `fileHash` for hashes, `fname`
  for filenames.
- **Webhook**: one request per batch,
  `{"source": "misp-workbench", "event": {…}, "attributes": [ … ]}`. The
  headers include `X-Misp-Workbench-Delivery` (the same for every batch of one
  delivery) and, when a secret is set,
  `X-Misp-Workbench-Signature: sha256=<HMAC-SHA256 of the body>`.

## TLS

HTTP sinks always use the URL's scheme. GELF and TCP syslog can enable TLS.
Certificates are verified against the system trust store. For a self-signed
endpoint (Splunk HEC ships with one), paste its CA certificate in **CA
certificate (PEM)** instead of turning verification off. **Verify TLS
certificate** can be disabled per sink as a last resort.

Secrets (the HEC token, the webhook signing secret) are never returned by the
API; they read back as `********`. Sending that value back on an update keeps
the stored secret.

## API reference

| Method | Path | Description | Scopes |
|---|---|---|---|
| `GET` | `/sinks/` | List sinks with their delivery status | `sinks:read` |
| `POST` | `/sinks/` | Create a sink | `sinks:create` |
| `GET` | `/sinks/{id}` | Get a sink | `sinks:read` |
| `PATCH` | `/sinks/{id}` | Update name, enabled, config or filters (not the type) | `sinks:update` |
| `DELETE` | `/sinks/{id}` | Delete a sink | `sinks:delete` |
| `POST` | `/sinks/{id}/test` | Send one test indicator now; returns `{ok, error}` | `sinks:test` |
| `POST` | `/sinks/{id}/deliver/{event_uuid}` | Queue a delivery of one event, published or not (backfill, replay) | `sinks:test` |

```json
POST /sinks/
{
  "name": "Splunk production",
  "type": "splunk_hec",
  "config": {
    "url": "https://splunk.example.com:8088/services/collector/event",
    "token": "<HEC token>",
    "index": "threatintel"
  },
  "filters": {
    "to_ids_only": true,
    "types": ["ip-src", "ip-dst", "domain", "url"],
    "exclude_tags": ["tlp:red"]
  }
}
```
