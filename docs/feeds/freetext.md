# Freetext Feeds

Freetext feeds ingest plain text files with one indicator per line. The attribute type is either detected automatically using heuristics or set to a fixed value.

## Type detection

When set to **Automatic**, each line is classified in order:

| Type | Detection rule |
|---|---|
| `ip-src` | Valid IPv4/IPv6 address or CIDR range |
| `url` | Starts with `http://` or `https://` (case-insensitive) |
| `email-src` | Matches `user@domain.tld` |
| `cve` | Matches `CVE-YYYY-NNNNN` (case-insensitive) |
| `sha512` | 128 hex characters |
| `sha256` | 64 hex characters |
| `sha1` | 40 hex characters |
| `md5` | 32 hex characters |
| `domain` | Valid domain name |
| `other` | Fallback — does not match any of the above |

## Configuration

| Option | Description |
|---|---|
| **Automatic** | Detect type per line using the heuristics above |
| **Fixed type** | Assign the same MISP attribute type to every line |

## Example

A freetext feed mixing different indicator types:

```
# Malicious IPs
1.2.3.4
2001:db8::1
192.168.0.0/24

# Domains
evil.example.com
phishing.test.org

# Hashes
d41d8cd98f00b204e9800998ecf8427e
e3b0c44298fc1c149afbf4c8996fb924...
```

Lines starting with `#` and blank lines are ignored. With **Automatic** detection each indicator will receive the appropriate type.
