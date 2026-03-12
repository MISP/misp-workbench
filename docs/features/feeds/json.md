# JSON Feeds

JSON feeds ingest structured JSON data where each item in a collection becomes a MISP attribute. Nested fields are accessed using dot-notation paths.

<img src="../../../screenshots/feeds/misp-workbench-1_json-feed.png">

## Supported formats

| Format | Description |
|---|---|
| **JSON array** | The feed URL returns a JSON array (or an array nested inside an object) |
| **JSON object** | The URL returns a single JSON object, treated as one item |
| **NDJSON** | Newline-delimited JSON — one JSON object per line |

## Configuration

### Items path

Dot-notation path to the array or object within the JSON document. Leave empty if the root element is the array.

<img src="../../../screenshots/feeds/misp-workbench-2_csv-feed-preview.png">

After the items path is configured, the preview is re-rendered.

<img src="../../../screenshots/feeds/misp-workbench-3_json-feed-preview-with-json-path.png">

**Examples:**

| JSON structure | Items path |
|---|---|
| `[{...}, {...}]` | *(empty)* |
| `{"data": [{...}]}` | `data` |
| `{"response": {"iocs": [{...}]}}` | `response.iocs` |

Not applicable for NDJSON (each line is always one item).

### Attribute mapping

#### Value field

Dot-notation path to the attribute value within each item.

- `"value"` — reads `item.value`
- `"data.indicator"` — reads `item.data.indicator`
- *(empty)* — use the item itself directly (for primitive arrays like `["1.2.3.4", "5.6.7.8"]`)

<img src="../../../screenshots/feeds/misp-workbench-4_json-feed-attribute-mapping.png">

#### Type strategy

| Strategy | Description |
|---|---|
| **Fixed** | All items use the same MISP attribute type |
| **From field** | Read type from a field path; optional mapping table to convert feed-specific strings to MISP types |

#### Optional properties

Each of `comment`, `tags`, and `to_ids` can be:

- **None** — omitted
- **Fixed value** — same value for every item
- **From field** — dot-notation path within each item

## Examples

=== "Array with fixed type"
    Feed: `[{"ioc": "1.2.3.4"}, {"ioc": "evil.example.com"}]`

    - Format: **JSON array**
    - Items path: *(empty)*
    - Value field: `ioc`
    - Type: **Fixed** → `ip-dst`

=== "Nested array with field type"
    Feed:
    ```json
    {
      "data": {
        "indicators": [
          {"value": "1.2.3.4", "type": "ip-dst"},
          {"value": "evil.com", "type": "domain"}
        ]
      }
    }
    ```

    - Format: **JSON array**
    - Items path: `data.indicators`
    - Value field: `value`
    - Type: **From field** → `type`

=== "Primitive array"
    Feed: `["1.2.3.4", "5.6.7.8", "evil.example.com"]`

    - Format: **JSON array**
    - Items path: *(empty)*
    - Value field: *(empty — use item directly)*
    - Type: **Fixed** → `ip-dst`

=== "NDJSON"
    Feed (one object per line):
    ```
    {"indicator": "1.2.3.4", "type": "ip-dst"}
    {"indicator": "evil.com", "type": "domain"}
    ```

    - Format: **NDJSON**
    - Value field: `indicator`
    - Type: **From field** → `type`
