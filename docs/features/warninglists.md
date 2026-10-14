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

One list doesn't come from the submodule: **Rejected in review** holds the
values analysts rejected in the [review queue](review-queue.md#rejecting-onto-a-warninglist)
and put on it. It is created on the first such rejection, matched
like any other list, and left alone by updates. Taking the rejection back
takes the value off it.

<img src="../../screenshots/warninglists/misp-workbench-1_warninglists_page.png#only-light" alt="Warninglists page with a value check" style="max-width: 100%; height: auto;">
<img src="../../screenshots/warninglists/misp-workbench-1_warninglists_page-dark.png#only-dark" alt="Warninglists page with a value check" style="max-width: 100%; height: auto;">

Reading lists and checking values needs `warninglists:read`, which every
built-in role has. Updating and enabling or disabling lists needs
`warninglists:update`, which only admins have by default.

## Your organisation's lists

The MISP lists are global and generic. Every organisation also has values
it must never block or alert on in *its* environment: its own ranges and
domains, VPN egress, partners, critical SaaS. Under ***settings*** →
***warninglists***, **Your organisation's lists** keeps those.

<img src="../../screenshots/warninglists/misp-workbench-3_warninglists_organisation-list.png#only-light" alt="An organisation's own list" style="max-width: 100%; height: auto;">
<img src="../../screenshots/warninglists/misp-workbench-3_warninglists_organisation-list-dark.png#only-dark" alt="An organisation's own list" style="max-width: 100%; height: auto;">

- **Entries** are exact values, address ranges (`10.0.0.0/8`: an IP in it
  matches, in an `ip|port` too), domains with their subdomains
  (`*.corp.example`) or regexes (`/^vpn-\d+\./`), each with a comment and
  an optional expiry. Expired entries stop matching and are dropped.
- **Regexes** run on RE2: matching takes linear time whatever the pattern,
  so a regex can't stall the platform. Backreferences and lookarounds aren't
  supported. A regex is at most 256 characters, matched against the first
  1024 characters of a value.
- **Import and export** as plain lists, one entry per line
  (`entry  # comment`). Importing can replace the entries an earlier import
  brought.
- **Sync** from a URL serving such a list (your CMDB's ranges, say): give
  it when creating the list (**+ New list**, choose **Remote**), or later
  on the list's page.
  It is fetched at once, then daily, each sync replacing what the last one
  brought. Fetching from inside the network is
  the point, so where lists may sync from is an admin's call: only hosts in
  the runtime setting `warninglists.source_hosts` (exact names or
  `*.corp.example`), none by default. A host resolving to a loopback,
  link-local (cloud metadata), multicast or reserved address is refused
  whatever the setting, and redirects aren't followed.

**What a list matches stays private.** It isn't stored on attributes or
indicators, which anyone can search: which indicators each list matches is
kept apart, recomputed when the list changes and, for new indicators, every
minute. A [detection profile](detection-profiles.md#rules) leaves a list's
matches out only when it **attaches** the list, so one organisation's list
never silences another's outputs, and a value too new to have an indicator
is matched as it comes. Your lists show on an indicator's details, and
additions on them are flagged in a profile's
[change preview](detection-profiles.md#change-preview-and-approval-gate),
for you only. **Check values** tells you which entry of your lists a value
matches, and why (its comment).

Attaching a list to a profile others use makes its effect visible to them,
in what the profile's outputs leave out. So that nobody can probe it beyond
that, rules attaching a list you can't see can't be previewed, and a profile
attaching one can't be dry-run, nor have its rules changed, but by admins.
Explore's query for a profile can't leave a list's matches out (they're
private), and says so.

Reading needs `warninglists:read`; creating lists and changing entries needs
`local_warninglists:manage` (Org Admin and Publisher).

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
