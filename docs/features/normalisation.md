# Normalisation

Synced data arrives in every shape. Values may be defanged (`hxxp://`,
`1.2.3[.]4`) or in mixed case, URLs may carry default ports and tracking
parameters, IPv6 addresses come written many ways, and hashes may be in
upper case. Some data is plainly wrong: hashes of the wrong length,
malformed CIDRs, or private addresses flagged for IDS. Left alone, these
fail silently downstream, miss correlations, or put a private address into
a firewall block list.

misp-workbench normalises and validates every attribute as it is written,
whether it comes from the API, a MISP server, a feed or a bulk import:

- **Values are rewritten into one canonical form**, so the same indicator
  always looks the same: correlations, warninglists and
  [consolidated indicators](indicators.md) find it, and outputs send it in a
  form controls understand. The value as received is kept in
  `original_value`.
- **Problems are flagged, never dropped.** They are listed in
  `validation_issues`, shown on the attribute, carried to its indicator as
  `workbench:validation="…"` tags, and lower the indicator's
  [score](indicators.md#confidence-scores).

<img src="../../screenshots/normalisation/misp-workbench-1_normalisation_attributes.png#only-light" alt="Normalised and flagged attributes" style="max-width: 100%; height: auto;">
<img src="../../screenshots/normalisation/misp-workbench-1_normalisation_attributes-dark.png#only-dark" alt="Normalised and flagged attributes" style="max-width: 100%; height: auto;">

A **normalised** badge shows the original value when you hover over it.

## Rules

All rules are on by default, except stripping tracking parameters.

| Rule | Applies to | Example |
|---|---|---|
| **Refang** | URLs, domains, hostnames, IPs, email addresses and their composites | `hxxps://evil[.]com` → `https://evil.com`, `1.2.3[.]4` → `1.2.3.4`, `bob[@]example.com` → `bob@example.com` |
| **Lower-case hostnames** | `domain`, `hostname`, the domain part of email addresses | `WWW.Example.COM.` → `www.example.com` |
| **Normalise URLs** | `url`, `link` | `HTTPS://Login.EXAMPLE.org:443/Verify` → `https://login.example.org/Verify` (the path keeps its case) |
| **Strip tracking parameters** (off by default) | `url`, `link` | `…/page?utm_source=x&id=7` → `…/page?id=7` |
| **Canonical IPs** | `ip-src`, `ip-dst` and composites | `2001:0DB8:0:0:0:0:0:1` → `2001:db8::1` (RFC 5952), `010.001.002.003` → `10.1.2.3` |
| **Lower-case hashes** | `md5`, `sha1`, `sha256`, …, and `filename\|<hash>` | `D41D8CD9…` → `d41d8cd9…` |

Other types (`text`, `comment`, `filename`, …) are left exactly as written.

## Validation issues

| Issue | Meaning |
|---|---|
| `invalid-ip` | not a valid IPv4 or IPv6 address |
| `invalid-cidr` | a CIDR whose prefix length is out of range |
| `invalid-port` | a port that isn't a number from 0 to 65535 |
| `invalid-hash` | a hash of the wrong length for its type, or not hexadecimal |
| `private-ip` | a private address (RFC 1918, carrier-grade NAT, IPv6 unique local) |
| `loopback-ip` | a loopback address |
| `link-local-ip` | a link-local address |
| `documentation-ip` | a documentation address (192.0.2.0/24, 198.51.100.0/24, 203.0.113.0/24, 2001:db8::/32) |
| `multicast-ip` | a multicast address |
| `reserved-ip` | a reserved or unspecified address |

The address-range issues (`private-ip` to `reserved-ip`) are only raised for
attributes flagged for IDS. A private address is valid context, but not
something to block or alert on.

Previously, an `ip-src` or `ip-dst` attribute that wasn't a valid IP was
rejected by the search index altogether. It is now stored, flagged
`invalid-ip`.

Validation issues can be searched (`validation_issues:"private-ip"` in
Explore or an export query) and filtered out. A sink's **Never with tags**
can exclude `workbench:validation=*`, and an indicator export can add
`NOT validation_issues:*` to its query. Each issue costs the indicator 40
points of score by default (`validation_penalty` in the scoring settings).

## Settings

Under ***internals*** → ***runtime settings*** → ***normalisation***, each
rule can be switched on or off, and normalisation as a whole can be turned
off. The tracking parameters list takes one name per line; a trailing `*`
matches a prefix (`utm_*`).

<img src="../../screenshots/normalisation/misp-workbench-2_normalisation_settings.png#only-light" alt="Normalisation settings" style="max-width: 100%; height: auto;">
<img src="../../screenshots/normalisation/misp-workbench-2_normalisation_settings-dark.png#only-dark" alt="Normalisation settings" style="max-width: 100%; height: auto;">

Settings apply to what is written from then on. **Apply to existing
attributes** runs every stored attribute through the rules again, in the
background. So does the CLI:

```bash
docker compose exec api poetry run python -m app.cli normalise-attributes
```

Run it once after upgrading, so attributes stored before normalisation
existed are normalised too.

## How it works

The rules are a Painless script (`api/app/services/normalisation/normalise.painless`),
run by the `misp-attributes_normalise` ingest pipeline. It is the first step
of the attributes' default pipeline, so it runs before IP extraction,
[servos](tech-lab/servos.md), warninglists and correlations, and on every
write path, `update_by_query` included. The settings are passed to the script
as parameters: the API re-applies them at startup and whenever they change.
A failure in the script never blocks indexing: it is recorded in
`normalisation_error` on the attribute.
