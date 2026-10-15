# External dynamic lists

Firewalls and proxies read **external dynamic lists** (EDLs): a plain-text
URL they fetch on a schedule, one IP, domain, URL or hash per line. Palo
Alto, Fortinet, Check Point, Cisco and Squid all read them, and most can't
send an `Authorization` header. An EDL here is one
[detection profile](detection-profiles.md)'s values of one kind, written the
way a vendor reads them. The firewall fetches it from a URL with a token in
it, and that token opens that one list and nothing else.

Find them under ***Share*** → ***External dynamic lists***.

## Creating a list

| Setting | Meaning |
|---|---|
| **Detection profile** | what the list holds: its rules, review and approval gate all apply |
| **Vendor** | the format to write (below) |
| **Holds** | IP addresses and networks, domains, URLs or file hashes: one kind per list, as firewalls expect |
| **At most** | the size limit. Past it, the highest scored indicators stay in and the rest are left out. Empty: the vendor's limit |
| **Subdomains too** | for domain lists, where the vendor's format can say so |
| **Rebuilt every** | minutes between rebuilds (15 by default) |

Indicators of composite types give the part a list wants: the IP of an
`ip-dst|port` or `domain|ip`, the domain of a `domain|ip`, the hash of a
`filename|sha256`. Values a vendor can't take are skipped, and each entry is
written once.

Some values are never written, whatever the profile selects, because a
firewall blocking them would cut off more than an indicator:

- addresses and networks that aren't public (private, loopback, link-local,
  documentation, reserved), and networks broader than a `/16` (IPv4) or a
  `/32` (IPv6): a poisoned or mistaken `0.0.0.0/0` would block everything;
- URLs whose host a browser reads as such an address (`http://10.0.0.1/`,
  or numeric forms like `http://0x7f.1/`).

A URL is listed with the host a browser goes to: after any credentials
(`http://bank.example@evil.example/` lists `evil.example/`), with a backslash
read as a slash, and percent-encoding in the host decoded.

## Vendors

| Vendor | Lists | Size limit | Written as |
|---|---|---|---|
| **Palo Alto Networks PAN-OS** | IP, domain, URL | 50,000 | IPs and CIDRs. Domains as they are: PAN-OS covers subdomains with its list's own *Automatically expand to include subdomains*. URLs without their scheme and with a path of at least `/` (`bad.example/`, not `bad.example`, which would match `bad.example.com` too). URLs holding `*` or `^`, which PAN-OS reads as wildcards, and those over 255 characters are skipped |
| **Fortinet FortiGate threat feed** | IP, domain, URL, hash | 131,072 lines | IPs and CIDRs; domains, followed by `*.domain` with subdomains; URLs without their scheme; MD5, SHA-1 and SHA-256 hashes |
| **Check Point network feed** | IP, domain | none | one per line |
| **Cisco Secure Firewall security intelligence feed** | IP, domain, URL | none | one per line, URLs with their scheme |
| **Squid ACL file** | IP, domain, URL | none | IPs for a `dst` ACL; domains for `dstdomain`, as `.example.com` with subdomains; URLs as `url_regex` patterns (`^https?://bad\.example/x`), to load with `-i` |
| **Plain list** | IP, domain, URL, hash | none | one value per line |

## Tokens

Each list has its own tokens. A token:

- fetches its list only, read-only: no other endpoint accepts it, and it is no
  API key;
- is shown once, when it is created. Only its SHA-256 is kept;
- can expire, and can be limited to addresses or networks
  (`192.0.2.10`, `198.51.100.0/24`). Behind a reverse proxy, the address is
  the one uvicorn sees, which honours `X-Forwarded-For` only from
  `API_PROXY_IP`;
- is revoked at once from the list's page;
- is audited on every use (`edl.fetched`, and `edl.fetch_refused` when it is
  revoked, expired or used from elsewhere). The list's page shows each
  token's last use, address and count.

Give each firewall its own token, so one can be revoked without the others.
Tokens are kept out of the API's access log, but a proxy in front of it logs
URLs too: keep its logs as safe as the lists, or have it redact `/edl/`.

## What firewalls fetch

```
GET /edl/{token}
```

The list as plain text, from storage: requests never query the indicators,
however often firewalls poll. Its SHA-256 is its `ETag`, so a firewall
sending `If-None-Match` gets a `304` while nothing changed.

| Status | Meaning |
|---|---|
| `200` | The list |
| `304` | Unchanged since the `ETag` sent |
| `403` | The token can't be used from this address |
| `404` | No such token, or it was revoked or has expired, or the list was deleted |
| `503` | The list hasn't been built yet (`Retry-After: 60`) |

A build is a run of its profile, as an export's is: what an
[approval gate](detection-profiles.md#change-preview-and-approval-gate)
holds stays out until approved, and approving rebuilds the profile's lists
at once. If a build fails, the list built before it is still served, and the
error shows on the list's page.

## Palo Alto Networks, step by step

1. Create a list: the profile, vendor *Palo Alto Networks PAN-OS*, and
   *IP addresses* (or domains, or URLs).
2. On its page, create a token named after the firewall, limited to the
   firewall's management address, and copy the URL.
3. On the firewall, **Objects → External Dynamic Lists → Add**: type *IP
   List* (or *Domain List*, *URL List*), paste the URL as the source, and
   pick a check interval (*Five Minute*, say). With a TLS certificate PAN-OS
   doesn't trust yet, add a certificate profile with its CA.
4. **Test Source URL**, then use the list in a security policy rule (or a URL
   filtering profile, or anti-spyware DNS policy for domains) and commit.

## API

| Endpoint | Scope | |
|---|---|---|
| `GET /edls` | `edls:read` | Your organisation's lists (every one, for admins) |
| `GET /edls/vendors` | `edls:read` | Vendors, the lists each takes, its size limit |
| `POST /edls`, `PATCH /edls/{id}`, `DELETE /edls/{id}` | `edls:manage` | Create, edit (rebuilt at once), delete |
| `POST /edls/{id}/build` | `edls:manage` | Rebuild now |
| `GET /edls/{id}/preview` | `edls:read` | The first 50 lines as served |
| `GET /edls/{id}/tokens`, `POST /edls/{id}/tokens` | `edls:manage` | List tokens; create one (`name`, `expires_at`, `allowed_ips`): the response holds its `token` and `path`, once |
| `DELETE /edls/{id}/tokens/{token_id}` | `edls:manage` | Revoke |
| `GET /edl/{token}` | the token | The list |

Org Admin and Publisher hold `edls:manage`; User and Read Only, `edls:read`.
A detection profile a list reads can't be deleted until the list is.
