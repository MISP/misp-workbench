# CSV Feeds

CSV feeds ingest delimited text files where each row becomes a MISP attribute.

<img src="../../../screenshots/feeds/misp-workbench-1_csv-feed.png">

## Configuration

### Format options and preview

| Field | Options | Description |
|---|---|---|
| **Delimiter** | `,` `;` `\|` `\t` ` ` | Column separator |
| **First row is header** | on / off | Skip the first row during ingestion |

<img src="../../../screenshots/feeds/misp-workbench-2_csv-feed-preview.png">

### Attribute value mapping

Configure how CSV columns are mapped to MISP attribute fields. Select which column (by index or header name) contains the indicator value.

<img src="../../../screenshots/feeds/misp-workbench-3_csv-feed-value-mapping.png">

#### Type strategy

| Strategy | Description |
|---|---|
| **Fixed** | All rows use the same MISP attribute type |
| **Column** | Read the type from a designated column; optional mapping table to convert feed-specific strings to MISP types |

#### Optional properties

Each property can be:

- **Not mapped** — omitted
- **Fixed value** — same value applied to every row
- **From column** — read from a specific CSV column

| Property | Description |
|---|---|
| `timestamp` | Unix timestamp or ISO 8601 date |
| `to_ids` | Boolean — `yes`/`1`/`true` are treated as true |
| `tags` | Comma-separated tag list |
| `comment` | Free text |
| `first_seen` | Timestamp |
| `last_seen` | Timestamp |


<img src="../../../screenshots/feeds/misp-workbench-4_csv-feed-advanced-value-mapping.png">

## Example

A CSV feed with header `indicator,type,comment`:

```csv
indicator,type,comment
1.2.3.4,ip-dst,C2 server
evil.example.com,domain,Phishing domain
```

Configuration:

- Delimiter: `,`
- First row is header: **on**
- Value column: `indicator`
- Type strategy: **Column** → column `type`
- Comment: **Column** → column `comment`
