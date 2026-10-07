# Sightings

A **sighting** records that an indicator was seen somewhere: a SIEM rule
fired, a sensor matched a value, an analyst confirmed it. A **false positive**
sighting records the opposite: the indicator matched something benign.
Sightings are how detection results flow back into misp-workbench, and they
feed prevalence ("how often has this been seen?") and the sightings histogram
and stats.

Sightings are stored by **value**, in the `misp-sightings` index, so a sighting
of `198.51.100.7` applies to every attribute holding that value.

| Type | MISP type | Meaning |
|---|---|---|
| `positive` | `0` | The indicator was seen |
| `false-positive` | `1` | The indicator matched something benign |
| `expiration` | `2` | The indicator should no longer be considered valid |

## Reporting sightings

### Native API

```
POST /sightings/
Required scope: sightings:create
```

The body is one sighting or a list of them, up to **10,000** per request
(more returns `413`):

```json
[
  {"value": "198.51.100.7", "type": "positive", "timestamp": 1760000000},
  {"value": "evil.example.com", "type": "false-positive",
   "observer": {"source": "splunk-prod"}}
]
```

The reporting organisation defaults to the caller's.

### MISP-compatible API

Tools built for MISP can report sightings unmodified, in MISP's own format:

```
POST /sightings/add
POST /sightings/add/{attribute}
Required scope: sightings:create
```

| Field | Description |
|---|---|
| `value` / `values` | Value(s) to sight |
| `uuid` / `id` | Sight one attribute: its uuid, or the numeric id of an attribute pulled from MISP |
| `type` | `0` sighting (default), `1` false positive, `2` expiration |
| `source` | Free text, stored as `observer.source` (e.g. the sensor or SIEM) |
| `timestamp` | Epoch seconds; defaults to now |

`/sightings/add/{attribute}` takes the attribute uuid or MISP id in the URL.

```bash
curl -s https://workbench.example.com/sightings/add \
  -H "Authorization: $API_KEY" -H "Content-Type: application/json" \
  -d '{"values": ["198.51.100.7", "203.0.113.9"], "type": "1", "source": "wazuh"}'
```

The response mirrors MISP's:
`{"saved": true, "success": true, "message": "2 sightings successfully added.", …}`.

## Throughput

Sightings are written to OpenSearch in a single bulk request. Their
post-processing runs in background tasks, **one per 1,000 sightings** rather
than one per sighting: following-user notifications, reactor `sighting.created`
triggers and false-positive feedback. Each task looks up the attributes for
all of its values in one query. A SIEM can report thousands of hits per
minute without flooding the task queue.

## False-positive feedback

When indicators keep matching benign activity, misp-workbench can stop
flagging them for detection on its own:

| Runtime setting | Default | Effect |
|---|---|---|
| `sightings.false_positive_threshold` | `0` (off) | Once this many **distinct organisations** have reported a value as a false positive, `to_ids` is turned off on every attribute holding it |

Turning `to_ids` off removes the value from IDS-only exports, feeds and
[sinks](sinks.md), so SIEMs stop alerting on it. Attributes and their history
are kept; only the flag changes. Set `to_ids` back by hand if the value becomes
relevant again; further reports will turn it off again while the threshold is
still met.

The threshold counts organisations, not sightings, and the reporting
organisation is always the authenticated caller's (a client can name its
`source`, not report on another organisation's behalf). One reporter, or one
compromised sensor, can't switch off detection on its own by repeating
itself.

!!! warning "Single-organisation instances"
    With one organisation, only a threshold of `1` can ever be met, which means
    any user allowed to report sightings can switch off detection for a value.
    Leave the feedback off unless that is acceptable.
