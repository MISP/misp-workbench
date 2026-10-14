# Alert webhooks

[Sightings](sightings.md) are the feedback loop that scoring,
[hit-rate expiry](detection-profiles.md) and false-positive feedback learn
from. SIEMs and SOARs raise alerts in their own shape, though, and reporting
those alerts as sightings used to take custom code on the sender's side. An
**alert webhook** takes alerts as the sender posts them. A mapping reads the
values each alert hit, and those values are reported as your organisation's
sightings.

Find them under **sources → alert webhooks**.

## Setting one up

1. Click **+ New webhook**, name it, and pick the **sender**: Splunk, Elastic,
   Graylog, Wazuh, Microsoft Sentinel or generic JSON. The sender's preset gives
   the mapping to start from and the setup steps.
2. Copy the URL shown once, `https://<api>/webhooks/alerts/awh_…`, into the
   sender's webhook settings. The token in the URL is the only credential,
   because senders' webhooks seldom send an `Authorization` header.
3. Have the sender post a test alert. On the webhook's page, **Last received**
   loads that alert into **Try it**, and **Read it** shows what the mapping
   reads from it: records, values, type, source and time. Nothing is reported
   when you try a mapping. Edit the mapping until the result is right, then
   **Save** it.

| Setting | Meaning |
|---|---|
| **Sender** | the preset: its mapping and setup steps |
| **Only values an attribute holds** | on by default. An alert also names the internal hosts it was raised for; with this on, only values that some attribute holds are reported |
| **Only from** | the sender's addresses or networks. Empty: any address |
| **At most (requests a minute)** | past this limit, the sender gets a `429` with `Retry-After` |
| **Enabled** | while it's off, requests get a `403` |

## Presets

| Sender | Reads |
|---|---|
| **Splunk webhook alert action** | `result.src_ip`, `dest_ip`, `src`, `dest`, `url`, `domain`, `query`, `file_hash`, `md5`, `sha1`, `sha256`; the source is the search name, and the time is `_time`. Splunk posts the first result row only, so set the alert's Trigger to *For each result* to report every row |
| **Elastic / Kibana rule action** | a Webhook connector with the body `{"rule": "{{rule.name}}", "alerts": {{context.alerts}}}`. From each alert it reads the ECS fields `source.ip`, `destination.ip`, `url.full`, `url.domain`, `dns.question.name` and `file.hash.*`, nested or dotted. The source is the rule name |
| **Graylog HTTP notification** | the event's custom fields, its group-by fields and its key, plus the indicator fields of the backlog messages. The source is the event definition's title |
| **Wazuh integration** | an `<integration>` posting JSON alerts (for example the `shuffle` integration with this URL as `hook_url`). It reads the `data` and `syscheck` indicator fields, whether the alert arrives wrapped in `all_fields` or not. The source is the rule's description |
| **Microsoft Sentinel playbook** | an HTTP action in an incident-triggered playbook that posts the incident's title, its classification and its `relatedEntities`. It reads IP, URL, file hash and DNS entities. An incident classified `FalsePositive` reports false positives |
| **Generic JSON** | an object, or an array of objects, each with `value` or `values`, and optionally `type`, `source`, `timestamp` and `uuid` |

## Mappings

A mapping is a set of [JMESPath](https://jmespath.org/tutorial.html)
expressions:

| Field | Reads | Empty |
|---|---|---|
| **Records** | the alerts in a request | `@`: the body, or each element when the body is an array |
| **Values** | the values an alert hit: a string, or arrays of them, nested or not | required |
| **Type** | `positive`, `false-positive` or `expiration`, or MISP's `0`, `1`, `2` (`false_positive` and `fp` also work) | `positive` |
| **Source** | the rule or sensor that raised the alert | the webhook's name |
| **Timestamp** | epoch seconds, milliseconds or microseconds, or ISO 8601 | when the request arrives |
| **Attribute uuid** | an attribute's uuid, which makes the alert a sighting of that attribute | – |

Every field except Records is read from each record. `root()` reads from the
whole body instead: the Elastic preset reads its source with `root().rule`,
because the rule name sits outside the alerts. Use a JMESPath condition to
derive the type, for example:

```
classification == 'FalsePositive' && 'false-positive' || 'positive'
```

Values are converted to strings, and repeats within one alert count once.
Objects, booleans and values over 2,048 characters are skipped. A time more
than five minutes in the future is replaced by the current time, so a sender
with a wrong clock can't keep an indicator alive past its hit-rate expiry.

## What senders get back

| Status | When |
|---|---|
| `202` | taken: `{"records": 2}`. How many values became sightings is shown on the webhook's page and not in the response, because the counts would tell anyone holding the token which values this instance tracks |
| `400` | the body isn't JSON |
| `403` | the webhook is disabled, or the request came from an address not in **Only from** |
| `404` | no webhook has this token |
| `413` | the body is over 1 MiB, or it holds more than 10,000 sightings, more than 1,000 attribute uuids or more than 200 values over 256 characters (each of those costs its own lookup) |
| `422` | the mapping can't read the body; the response names the record and field that failed |
| `429` | over the rate limit; wait `Retry-After` seconds |

A request is all or nothing: if one record can't be read, none of the
request's sightings are reported. A sender retrying the request therefore
doesn't report the other records twice. The webhook's page shows the last
refusal and its reason until a request succeeds again.

Reported sightings go through the same bulk path as `POST /sightings`. They
are attributed to the webhook's organisation, with the mapped source and with
`metadata.sensor_type` set to the preset.

## Tokens and privacy

- Only the token's SHA-256 hash is stored. **New URL** replaces the token, and
  the old one stops working at once.
- Tokens are replaced by `<token>` in the API's access log.
- The token works for posting alerts and nothing else; no other endpoint
  accepts it.
- The last body received, cut to 64 KiB, is kept so you can try the mapping
  against it. Alerts can carry more than indicators, so only users who can
  manage webhooks can read it.
- Creating, editing, deleting a webhook and replacing its URL are recorded in
  the [audit log](api/audit-logs.md). Individual alerts are not: the request and
  sighting counters and the last refusal are shown on the webhook's page
  instead.

## Permissions

| Scope | Allows | Roles |
|---|---|---|
| `alert_receivers:read` | seeing the webhooks. Trying a mapping also requires `attributes:read`, because the result shows which values attributes hold | Org Admin, User, Publisher, Read Only |
| `alert_receivers:manage` | creating, editing and deleting webhooks, and replacing their URLs. Also requires `sightings:create`, because a webhook reports sightings for its organisation | Org Admin, Publisher |

Users see their organisation's webhooks; admins see every organisation's.
