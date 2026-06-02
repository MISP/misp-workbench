# Local File Feeds

In addition to fetching feeds from a remote URL, every feed type can also be sourced from a **file uploaded directly to misp-workbench**. This is useful for:

- One-off ingestion of an IOC list received over email or chat.
- Importing an offline MISP feed export from another instance.
- Replaying an archived snapshot of a feed for testing or comparison.

## Choosing the input source

When adding a feed, the **Input source** selector at the top of the Feed Settings card switches the form between two modes:

| Mode | When to use |
|---|---|
| **Network (fetch from URL)** | The feed is hosted on an HTTP(S) endpoint that misp-workbench can reach. This is the default. |
| **Upload file** | The feed data is provided as a file uploaded through the UI. |

Switching to **Upload file** replaces the URL field with a drag-and-drop dropzone, and hides the *Update interval* and *Fetch immediately* controls — uploaded feeds are **one-shot**: they are ingested once when the feed is created.

## How uploads are stored

Uploaded files are written to the project's configured storage backend (Garage S3 by default, or local filesystem when `STORAGE_ENGINE=local`) under the `feed-uploads/` prefix.

The stored key is recorded as the feed's `url` field and the original filename/size is preserved in `feed.settings.localFile`, so the UI can display it on the Update Feed page.

The maximum upload size is **2 GB**.

## Supported file formats by feed type

| Feed type | Accepted file types |
|---|---|
| [CSV](csv.md) | `.csv`, `.txt` (plain text, optionally with `#` comment lines) |
| [JSON](json.md) | `.json`, `.ndjson` |
| [Freetext](freetext.md) | `.txt`, `.csv` (one indicator per line) |
| [MISP](misp.md) | `.zip` or `.tar.gz` archive (see below) |

### MISP feed archives

A MISP feed is a directory tree rather than a single file (`manifest.json` + one `<event-uuid>.json` per event + optional `hashes.csv`). To upload a MISP feed, package it as a **`.zip` or `.tar.gz` archive** containing at least a `manifest.json` at the root.

On upload, the archive is extracted server-side and each relevant member is stored individually under the feed's storage prefix:

- `<key>/manifest.json` — the event index
- `<key>/<event-uuid>.json` — one per event
- `<key>/hashes.csv` — optional value-hash index

Files inside the archive that are not `manifest.json`, `hashes.csv`, or `.json` are ignored. Path-traversal entries (`../escape.json`) are stripped. An archive without a `manifest.json` at the root is rejected with HTTP 400.

## Previewing an uploaded feed

Once a file is uploaded, the per-type preview behaves the same as for network feeds — the CSV table, JSON sample items, Freetext type-detection table, and MISP manifest summary are all rendered from the uploaded data. The **Preview** button at the bottom of the Add Feed form opens the same preview in a modal.

## Ingestion semantics

When the feed is created:

1. The file (or extracted MISP archive members) is persisted to storage.
2. The feed is saved with `input_source = "local"` and `url` set to the storage key.
3. A one-shot ingestion job is enqueued (no recurring schedule).
4. Subsequent automatic fetches are **not scheduled** for upload-mode feeds — to re-ingest with updated data, replace the file on the Update Feed page.

## Replacing the file later

The Update Feed page shows the currently-uploaded filename next to a **Replace** button. Clicking Replace opens the file picker, uploads the new file, and on save the feed's `url` and `settings.localFile` are updated to point at the new blob. The next manual fetch will read the new file.

## API endpoint

Uploads are accepted by:

```http
POST /feeds/upload
Content-Type: multipart/form-data

file=<file>
source_format=<csv|json|freetext|misp>
```

Returns:

```json
{
  "key": "feed-uploads/<uuid>",
  "filename": "ioc.csv",
  "size": 4823,
  "source_format": "csv"
}
```

The returned `key` is what gets stored in `feed.url` when subsequently calling `POST /feeds/` with `input_source: "local"`.

## Limitations

- Upload feeds are **one-shot**: they do not run on a schedule. Re-uploading replaces the file but does not retroactively re-ingest past data.
- The 2 GB limit applies to the raw upload; for very large MISP archives consider splitting them or using the network URL mode instead.
- The file is read into memory before being stored — uploads do not stream.
