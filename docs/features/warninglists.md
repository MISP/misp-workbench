# Warninglists

[MISP warninglists](https://github.com/MISP/misp-warninglists) list values
that are benign or too common to act on: public DNS resolvers, the top
million domains, cloud and CDN ranges, private networks, known-good file
hashes, and many more. An indicator that matches one would flood a SIEM with
false positives, or get a resolver blocked on a firewall.

misp-workbench flags every attribute that is on an enabled warninglist, and
leaves flagged attributes out of what it hands to security controls by
default.

## Managing lists

The lists ship with misp-workbench (the `misp-warninglists` submodule).
Under ***settings*** → ***warninglists***:

- **Update warninglists** loads new lists and new versions of existing ones.
  New lists start enabled, as in MISP. From the command line:
  `docker compose exec api poetry run python -m app.cli load-warninglists`.
- Each list can be **enabled or disabled**. Attributes are re-checked in the
  background whenever lists change.
- **Check values** tells you which enabled lists a set of values is on.

<img src="../../screenshots/warninglists/misp-workbench-1_warninglists_page.png#only-light" alt="Warninglists page with a value check" style="max-width: 100%; height: auto;">
<img src="../../screenshots/warninglists/misp-workbench-1_warninglists_page-dark.png#only-dark" alt="Warninglists page with a value check" style="max-width: 100%; height: auto;">

Reading lists and checking values needs `warninglists:read`, which every
built-in role has. Updating and enabling or disabling lists needs
`warninglists:update`, which only admins have by default.

## How attributes are flagged

Each attribute carries `warninglist_hits`: the names of the enabled lists its
value is on. In the event's attribute list, flagged values show a
**warninglist** badge whose tooltip names the lists.

<img src="../../screenshots/warninglists/misp-workbench-2_warninglists_flagged-attributes.png#only-light" alt="Warninglisted attributes in an event" style="max-width: 100%; height: auto;">
<img src="../../screenshots/warninglists/misp-workbench-2_warninglists_flagged-attributes-dark.png#only-dark" alt="Warninglisted attributes in an event" style="max-width: 100%; height: auto;">

A list applies to the attribute types it declares (`matching_attributes`).
Matching follows the list type:

| List type | An attribute matches when |
|---|---|
| `string` | Its value, or one of its parts (`domain\|ip`, `ip-dst\|port`, …), equals an entry |
| `hostname` | Its domain or hostname, including a URL's host, is an entry or a subdomain of one |
| `cidr` | Its IP address is inside an entry's range |
| `substring` | It contains an entry (case-insensitive) |
| `regex` | It matches an entry's pattern |

Flags are kept current without slowing ingestion. A background job checks
attributes written since its last run every minute, and a full re-check runs
whenever lists are updated, enabled or disabled. Entries are indexed in
OpenSearch (`misp-warninglist-entries`) rather than held in memory: the
largest lists have a million entries each.

## Where flagged attributes are left out

| Output | Default | How to change it |
|---|---|---|
| [Streaming exports](api/streaming-exports.md) (`/attributes/export`) | Left out | `enforce_warninglist=false` |
| Scheduled exports and [incremental feeds](exports.md#incremental-feeds) | Left out of full files | Runtime setting |
| [Sinks](sinks.md) | Left out | Per sink: "Leave out values on an enabled warninglist" |
| [Bulk lookup](api/lookup.md) | Not counted as matches | `include_warninglisted: true` |
| [restSearch](api/rest-search.md) | Included, as in MISP | `enforceWarninglist: 1`; `includeWarninglistHits: 1` adds the hits |

The runtime setting `warninglists.enforce_on_outputs` (default `true`) sets
the default for exports and feeds.

Deltas (`since=` exports, incremental feed deltas) **keep** flagged
attributes, with their `warninglist_hits`. When a value lands on a
warninglist after a consumer received it, the consumer learns about it. Treat
a record with `warninglist_hits` like a deletion.
