# Detection engine formats

Network sensors and DNS resolvers don't read IOC lists: they read rules and
zones in their own formats. Three [export](exports.md) formats write the
indicators an export holds in those formats, so no script sits between
misp-workbench and the engine:

| Format | For | Extension |
|---|---|---|
| `suricata` | [Suricata](https://suricata.io) rules | `.rules` |
| `zeek` | A [Zeek Intel framework](https://docs.zeek.org/en/master/frameworks/intel.html) file | `.intel` |
| `rpz` | A DNS [Response Policy Zone](https://dnsrpz.info) for BIND, Unbound, PowerDNS or Infoblox | `.rpz` |

They work wherever `text` and `cdb` do. You can use them in scheduled
exports, in exports driven by a [detection profile](detection-profiles.md),
and on the [streaming export endpoints](api/streaming-exports.md), from
attributes or [indicators](indicators.md). Each value is written once, as
whatever its types turn it into: rules, intel items or zone records. A type
an engine has no use for writes nothing. So does a value the engine couldn't
load, such as a domain with a space in it, so one bad value can't stop a
sensor from loading the file.

## What a value may block

Values come from feeds and from other organisations' events, and with `drop`
rules or an RPZ zone a single value turns into a block. So none of them may
block more than an indicator:

- networks broader than IPv4 `/16` or IPv6 `/48` are left out;
- special-purpose addresses are left out: loopback (sinkholed domains resolve
  to `127.0.0.1`), unspecified (`0.0.0.0`), multicast, link-local and
  reserved;
- domains and hostnames on MISP's `tlds` and `second-level-tlds` warninglists
  (`co.uk`, `github.io`) are left out, since their record would cover every
  name under them;
- addresses must be plain notation: a scoped IPv6 address (`fe80::1%eth0`) is
  left out.
- IPv6 ranges that embed IPv4 addresses (`::ffff:0:0/96`, `::/96`,
  `64:ff9b::/96`) are left out: `::ffff:0:0/96` would be every IPv4 address.

Private addresses (`10.1.2.3`) are kept; leave them out with the RFC 1918
warninglist or a [detection profile](detection-profiles.md).

Each output was validated with the engine's own parser and replayed against
traffic or queries: `suricata -T` and a pcap for Suricata, Zeek's Intel
framework reading the file, and `named-checkzone` plus a resolver using the
zone for RPZ.

## Suricata rules

| Type | Rules |
|---|---|
| `ip-dst` | `alert ip $HOME_NET any -> [address] any` |
| `ip-src` | `alert ip [address] any -> $HOME_NET any` |
| `domain` | `dns.query`, `tls.sni` and `http.host`, the domain and its subdomains (`dotprefix; content:".evil.com"; endswith`) |
| `hostname` | the same three buffers, the name exactly (`startswith; endswith`) |
| `url` | `http.host` and `http.uri.raw`, both exactly, for `http://` URLs and URLs without a scheme |
| `user-agent` | `http.user_agent`, exactly |
| `ja3-fingerprint-md5` | `ja3.hash` |

Networks (`10.0.0.0/8`) and IPv6 addresses work wherever an address does.
Composite types (`domain|ip`, `ip-dst|port`, `hostname|port`) write rules for
the parts that have rules. An `https://` URL writes no rule, because its path
travels encrypted where a sensor can't see it. Record its host as a `domain`
or `hostname` instead.

Every rule carries:

- `msg`: `MISP <type> (<buffer>) <value>`;
- `metadata`: `misp_type`, `misp_uuid` (the attribute's or indicator's uuid),
  `misp_event`, and for indicators `misp_score` and `misp_source` (the first
  source);
- `sid`: derived from what the rule matches, from 1,000,000,000 up, clear of
  the ranges that published rulesets use. A rule keeps its SID from one run to
  the next, so suppressions and thresholds keyed on it keep working. In the
  rare case two rules hash to the same SID, the second takes the next free one.

**Rule action**, an export option, is `alert` or `drop` (IPS mode). Load the
file with `suricata -S <file>`, or list it under `rule-files` and reload rules.

Content bytes that Suricata can't take as they are (`"`, `;`, `\`, `|`,
anything outside printable ASCII) are written as `|hex|`. Domains are written
lowercased and IDNA-encoded (`bücher.example` → `xn--bcher-kva.example`), as
they travel on the wire.

## Zeek Intel

A tab-separated file with the header
`#fields indicator indicator_type meta.source meta.desc`:

| Type | Intel type |
|---|---|
| `ip-dst`, `ip-src` | `Intel::ADDR`, or `Intel::SUBNET` for a network |
| `domain`, `hostname` | `Intel::DOMAIN` |
| `url` | `Intel::URL`, without the scheme (Zeek's URLs have none) |
| `md5`, `sha1`, `sha256` | `Intel::FILE_HASH` |
| `filename` | `Intel::FILE_NAME` |
| `email`, `email-src`, `email-dst`, `target-email` | `Intel::EMAIL` |
| `x509-fingerprint-sha1` | `Intel::CERT_HASH` |
| `user-agent` | `Intel::SOFTWARE` |

`meta.source` is the indicator's first source (`misp-workbench` for
attributes). `meta.desc` gives the type, the score and the event. Load the
file with:

```zeek
@load frameworks/intel/seen
redef Intel::read_files += { "/opt/zeek/intel/misp.intel" };
```

Zeek re-reads the file when it changes.

## DNS RPZ

A zone a resolver applies as a response policy:

```
$TTL 300
@ SOA localhost. hostmaster.localhost. 1792000000 3600 600 2592000 300
@ NS localhost.
evil.com CNAME .
*.evil.com CNAME .
c2.bad-host.net CNAME .
32.42.101.220.185.rpz-ip CNAME .
128.1.zz.db8.2001.rpz-ip CNAME .
```

| Type | Triggers |
|---|---|
| `domain` | the domain and its subdomains (`evil.com`, `*.evil.com`) |
| `hostname` | the name itself |
| `ip-dst`, `ip-src` | `rpz-ip`: any answer that resolves to the address or network |

**Answer**, an export option, is what the resolver answers for a listed name:

| Answer | Record | The client gets |
|---|---|---|
| NXDOMAIN (default) | `CNAME .` | the name doesn't exist |
| NODATA | `CNAME *.` | the name exists but has no records |
| No answer (drop) | `CNAME rpz-drop.` | nothing; it times out |
| Walled garden | `CNAME blocked.example.org.` | the walled garden's address, so a block page can explain |

The zone's serial is the time of the run, so every run's zone is newer than
the one before it. A schedule plus a fetch of the export's download URL keeps
a resolver current:

```
# named.conf
options { response-policy { zone "rpz.misp"; }; };
zone "rpz.misp" { type primary; file "/var/named/rpz.misp"; };
```

```bash
curl -fsS -H "Authorization: Bearer $TOKEN" \
  https://workbench.example.com/exports/42/download -o /var/named/rpz.misp \
  && rndc reload rpz.misp
```

Domains are IDNA-encoded. Names longer than 230 characters are left out, so
that a name plus the zone's own name fits DNS's 255-octet limit. The zone is
served as a file. misp-workbench does not serve it by zone transfer (AXFR or
IXFR).

## API

```json
POST /exports/
{
  "name": "DNS firewall",
  "query": "*",
  "index_target": "indicators",
  "format": "rpz",
  "format_options": {"rpz_policy": "redirect", "rpz_redirect": "blocked.example.org"},
  "profile_id": 3,
  "schedule": {"type": "interval", "every": 900},
  "schedule_enabled": true
}
```

| Option | Format | Values |
|---|---|---|
| `rule_action` | `suricata` | `alert` (default), `drop` |
| `rpz_policy` | `rpz` | `nxdomain` (default), `nodata`, `drop`, `redirect` |
| `rpz_redirect` | `rpz` | the walled garden's host name, for `redirect` |

The [streaming endpoints](api/streaming-exports.md)
(`/indicators/export?format=suricata`, say) write the defaults.

These formats can't express a deletion, so they can't be incremental. Each run
writes the whole set, and the engine replaces what it had.
