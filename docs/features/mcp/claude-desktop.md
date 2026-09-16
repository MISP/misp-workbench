# Claude Desktop Integration

Claude Desktop installs MCP servers as **bundles** — a `.mcpb` file you
double-click. This repository ships one under `mcpb/`.

## Why a bundle and not a connector

Claude Desktop can add a remote MCP server directly under
**Settings → Connectors → Add custom connector**, but that path expects the
server to authenticate with OAuth. misp-workbench's MCP endpoint authenticates
with a scoped bearer token instead, and a custom connector gives you nowhere to
put one.

The `.mcpb` format cannot declare a remote HTTP server either — its four server
types (`node`, `python`, `binary`, `uv`) all run locally. So the bundle ships a
small Node bridge that Claude Desktop runs over stdio and that forwards to your
instance over HTTP.

The bridge is ~120 lines with no dependencies. It is written out rather than
delegating to `npx mcp-remote` so the bundle pulls nothing from npm at launch,
puts nothing third-party in the path of a credential, and avoids the bug where
Claude Desktop on Windows mangles a header argument containing a space.

Your token is passed to the bridge as an environment variable, never as a
command-line argument, so it does not appear in the process list.

## Install

1. **Build the bundle** (or take one from a release):

    ```bash
    cd mcpb
    npx @anthropic-ai/mcpb pack .
    ```

    This writes `mcpb/misp-workbench.mcpb`.

2. **Get an MCP token** from your instance:

    ```bash
    curl -s https://your-instance/mcp/config \
      -H "Authorization: Bearer <your-api-token>" | jq -r '.mcpServers["misp-workbench"].headers.Authorization'
    ```

3. **Install it**: double-click the `.mcpb`, or drag it onto Claude Desktop's
   **Settings → Extensions**.

4. **Fill in the two settings** Claude Desktop prompts for:

    | Setting | Value |
    |---|---|
    | Instance URL | `https://your-instance` — the base URL, with or without a trailing `/mcp` |
    | MCP token | The token from step 2, without the `Bearer ` prefix |

    The token field is marked `sensitive`, so Claude Desktop stores it in the OS
    keychain and masks it in the UI.

## What you get

22 tools, including:

- `search_events` / `search_attributes` — Lucene queries over the index
- `get_event`, `get_correlations`, `get_sightings`
- `detect_indicator_type`, `enrich_indicator`
- `list_hunts`, `run_hunt`, `get_hunt_results`
- `search_galaxy`, `search_taxonomy`, `get_tags`
- `create_event_report`, `get_event_reports`

Each tool is gated by the scopes on the token, so a read-only token yields a
read-only connector.

## Troubleshooting

The bridge reports problems as MCP errors, which Claude Desktop surfaces in the
extension's log.

| Message | Cause |
|---|---|
| `MISP_WORKBENCH_URL is not set` | The extension settings were left blank |
| `Instance URL must start with http:// or https://` | URL entered without a scheme |
| `Cannot reach <url>` | Instance unreachable — wrong host, VPN down, or the stack is not running |
| `MISP Workbench rejected the token` | Token expired or revoked; regenerate it from `/mcp/config` |

For Claude Code rather than Claude Desktop, see [Claude Code](claude.md) — it
talks to the HTTP endpoint directly and needs no bridge.
