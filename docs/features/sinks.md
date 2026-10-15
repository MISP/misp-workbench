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
| `sentinel` | STIX 2.1 indicators through the [upload API](https://learn.microsoft.com/en-us/azure/sentinel/stix-objects-api) | Microsoft Sentinel |
| `defender` | Custom indicators through the [indicators API](https://learn.microsoft.com/en-us/defender-endpoint/api/import-ti-indicators) | Microsoft Defender for Endpoint |
| `elastic` | ECS `threat.indicator.*` documents, bulk-indexed | Elastic Security indicator match rules |

The last three are [vendor APIs](#vendor-apis): platforms that take threat intel
only through their own API.

Sinks are managed under ***internals*** → ***sinks***. Because they send data
off the instance, they need the `sinks:*` scopes, which only the admin role has
by default.

The list shows each sink's destination, what it sends, and how its last
delivery went:

<img src="../../screenshots/sinks/misp-workbench-1_sinks_list.png#only-light" alt="Sinks list with delivery status" style="max-width: 100%; height: auto;">
<img src="../../screenshots/sinks/misp-workbench-1_sinks_list-dark.png#only-dark" alt="Sinks list with delivery status" style="max-width: 100%; height: auto;">

**New Sink** opens a form with the destination fields for the chosen type,
followed by the filters:

<img src="../../screenshots/sinks/misp-workbench-2_sinks_new-splunk-hec.png#only-light" alt="New Splunk HEC sink form" style="height: 900px;">
<img src="../../screenshots/sinks/misp-workbench-2_sinks_new-splunk-hec-dark.png#only-dark" alt="New Splunk HEC sink form" style="height: 900px;">

## Filters

| Filter | Default | Effect |
|---|---|---|
| **Only attributes flagged for IDS** | on | Skip attributes without `to_ids` |
| **Attribute types** | all | Send only these types (e.g. `ip-src, ip-dst, domain, url`) |
| **Only with tags** | any | Send only attributes carrying at least one of these tags |
| **Never with tags** | `tlp:red` | Never send attributes carrying any of these tags |
| **Leave out values on an enabled warninglist** | on | Never send attributes on an enabled [warninglist](warninglists.md) |
| **Send consolidated indicators** | off | Send each value once, as its [consolidated indicator](indicators.md) (see below) |
| **Detection profile** | none | A [detection profile](detection-profiles.md) in place of the filters here, except **Never with tags** and **Leave out values on an enabled warninglist**, which still hold |
| **Keep in step with the profile** | off | With a profile of indicators: every five minutes, send what [joined and left](detection-profiles.md#membership-deltas-telling-consumers-what-left) the profile (removals as `action: remove`, with their reason), instead of each published event |
| **Minimum score** | 0 | Leave out values whose indicator's [confidence score](indicators.md#confidence-scores) is below this. Values too new to be scored are sent |

Tag lists match the attribute's own tags **and** its event's tags, and accept
shell-style patterns (`tlp:*`, `misp-galaxy:threat-actor=*`). An attribute's
[validation issues](normalisation.md#validation-issues) count as
`workbench:validation="…"` tags, so `workbench:validation=*` in **Never with
tags** keeps private IPs and malformed hashes out. Soft-deleted
attributes are never sent.

With **Send consolidated indicators**, a delivery sends one record per type
and value, however many of the event's attributes carry it. Each record gets
an `indicator` block (its uuid, first and last seen, event count, TLP,
galaxies, sources, organisations and sighting counts), and its `tags` gain
the indicator's merged tags: those of every attribute and event carrying the
value. Tag filters then judge the value rather than the
one attribute: with `tlp:red` excluded, a value that is `tlp:red` in any event
is not sent, even from a `tlp:green` event. Text and comment attributes are
not indicators and are left out. GELF adds `_misp_indicator_uuid`,
`_misp_first_seen`, `_misp_last_seen`, `_misp_event_count`, `_misp_tlp`,
`_misp_sources`, `_misp_sightings` and `_misp_false_positives`, and CEF adds
`cn2` (event count) and `cn3` (sightings). A value indexed in the last few
seconds may not have its indicator yet; it goes out as its attribute's record.

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

When editing a sink, secrets read back masked: leave them as they are to keep
them (see [TLS](#tls)). The tag filters accept existing tags or patterns such
as `tlp:*`:

<img src="../../screenshots/sinks/misp-workbench-3_sinks_edit-syslog.png#only-light" alt="Editing a syslog/CEF sink" style="height: 900px;">
<img src="../../screenshots/sinks/misp-workbench-3_sinks_edit-syslog-dark.png#only-dark" alt="Editing a syslog/CEF sink" style="height: 900px;">

## Sending from code

Notebooks (`mwlab.send_to_sink`) and reactor scripts (`ctx.send_to_sink`) can send attributes, whole events or their own records to a sink by name. That's useful for hunt results, enrichment output, or triggers other than publish. Sends need the **`sinks:send`** scope, are queued on the same sinks worker, are rate-limited and audited, and never expose the sink's configuration. See [Notebooks](tech-lab/notebooks.md#sinks) and [Reactor scripts](tech-lab/reactor.md#sinks).

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

## Vendor APIs

!!! warning "Beta"
    These three sink types are in beta, and the UI marks them so. They follow
    each vendor's documented API, and the Elastic sink has been run against
    Elasticsearch 8. The Microsoft sinks have yet to be run against live
    tenants. Check what they deliver before relying on them.

These sinks write each value as the platform's own indicator object. A value
that becomes several objects (`domain|ip`) is written as each of its parts.
With **Keep in step with the profile**, a value that leaves the profile is
taken out again:

| Sink | Writes | Batches | A removal |
|---|---|---|---|
| `sentinel` | a STIX indicator per value: `[ipv4-addr:value = '…']`, `domain-name`, `url`, `email-addr`, `file:hashes`, `file:name`, `x509-certificate:hashes`. The confidence is the score, the TLP becomes a marking, and the tags become labels | 100 objects a request | expires the indicator (`valid_until` now). It isn't revoked: revoking is permanent in STIX, and the value may come back |
| `defender` | an indicator per value: `IpAddress`, `DomainName`, `Url`, `FileMd5`, `FileSha1`, `FileSha256`, `CertificateThumbprint` | 500 a call | deletes it. Only indicators carrying the sink's **Application** are looked up and deleted |
| `elastic` | an ECS document per value in the sink's index: `threat.indicator.ip`, `url.domain`, `url.full`, `email.address`, `file.hash.*`, `file.name` | 500 a request | deletes the document |

Each object's id is derived from the value. Sending a value again updates its
object rather than adding another, and a removal finds it.

**Score, severity and expiry.** Severity is High from a score of 80, Medium
from 50, Low from 20, and Informational below. Without a score (an attribute
sent outside indicator mode), the event's threat level stands in for it. An
indicator stays valid for **Valid** / **Expires** days (30 by default) after
its value was last seen, and at least a day from the time it is sent. A value
nobody reports any more drops out of the platform on its own.

**What they never get.** On these platforms an indicator can block, so the
same limits as the [detection engine formats](detection-formats.md#what-a-value-may-block)
apply: no network broader than an IPv4 /16 or IPv6 /48, no loopback,
multicast or reserved address, and no public suffix such as `co.uk`. Defender
and Elastic take single addresses only. Defender also needs public addresses:
a private one would match your own hosts.

**Throttling.** A throttled request (`429`, `503`) waits as long as the API
asks, up to a minute, at most three times. If it is still throttled, the
delivery fails and its task retries with backoff. Sentinel allows 100 requests
a minute, and Defender 30 imports a minute.

**Test** doesn't send these sinks an indicator: there, it could block. It
checks instead that the credentials work. For Sentinel, Entra ID issues a
token. For Defender, the token can read indicators. For Elastic, the
credentials authenticate.

### Microsoft Sentinel

1. Register an app in Microsoft Entra ID and give it a client secret.
2. Give the app the **Microsoft Sentinel Contributor** role on the workspace.
3. Create a `sentinel` sink with the tenant ID, client ID, client secret and
   the workspace ID.

Indicators show in Sentinel's threat intelligence, under the **Source system**
(`misp-workbench` by default).

### Microsoft Defender for Endpoint

1. Register an app in Microsoft Entra ID and give it a client secret.
2. Grant it the **WindowsDefenderATP** application permission
   `Ti.ReadWrite.All`, with admin consent.
3. Create a `defender` sink and pick the **Action**:

| Action | Defender action | Alert |
|---|---|---|
| Audit only | `Audit` | no |
| Alert (default) | `Audit` | yes |
| Block and alert | `Block`, or `BlockAndRemediate` for file hashes | yes |

**Device groups** limits the indicators to those groups; empty means every
device. Defender holds at most 15,000 indicators per tenant, so send it a
[detection profile](detection-profiles.md) rather than everything. Its token
is issued for `https://api.securitycenter.microsoft.com`, the resource the
API still expects.

For sovereign clouds, **Show endpoints** changes the login URL, the API URL and
the token scope for both Microsoft sinks.

### Elastic Security

1. Create an API key whose role has `create_index`, `index` and `delete` on
   the index (`misp-workbench-indicators` by default). A username and
   password also work.
2. Create an `elastic` sink with the Elasticsearch URL and the key.
3. In an **Indicator match** rule, add the index to the indicator index
   patterns, and map event fields to the indicator fields, for example
   `source.ip` and `destination.ip` to `threat.indicator.ip`.

If the index doesn't exist, the sink creates it with the ECS field types: an
address is an `ip`, the rest are `keyword`s, and indicator match compares
like with like. An index that already exists, from a template of your own, is
left as it is. Don't use a data stream (`logs-*-*`): a removal needs to
delete documents by id.

## TLS

HTTP sinks always use the URL's scheme. GELF and TCP syslog can enable TLS.
Certificates are verified against the system trust store. For a self-signed
endpoint (Splunk HEC ships with one), paste its CA certificate in **CA
certificate (PEM)** instead of turning verification off. **Verify TLS
certificate** can be disabled per sink as a last resort.

Secrets (the HEC token, the webhook signing secret, the Microsoft client
secret, the Elastic API key or password) are never returned by the API; they
read back as `********`. Sending that value back on an update keeps the stored
secret, but only while the connection settings stay the same: the URL (or host
and port), TLS, certificate verification and CA certificate, and for the
vendor APIs the login URL, API URL, tenant, client ID, token scope, workspace
and username.
Pointing a sink somewhere else, or weakening how its connection is
authenticated, requires re-entering its secret, so a stored token can't be
redirected to a host that shouldn't have it.

HTTP sinks don't follow redirects: they deliver to their configured URL only.
Errors report the HTTP status, never the endpoint's response body.

## API reference

| Method | Path | Description | Scopes |
|---|---|---|---|
| `GET` | `/sinks/` | List sinks with their delivery status | `sinks:read` |
| `POST` | `/sinks/` | Create a sink | `sinks:create` |
| `GET` | `/sinks/{id}` | Get a sink | `sinks:read` |
| `PATCH` | `/sinks/{id}` | Update name, enabled, config or filters (not the type) | `sinks:update` |
| `DELETE` | `/sinks/{id}` | Delete a sink | `sinks:delete` |
| `POST` | `/sinks/{id}/test` | Send one test indicator now (vendor APIs: check the credentials); returns `{ok, error}` | `sinks:test` |
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
