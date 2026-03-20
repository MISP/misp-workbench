# Claude Code Integration

This page explains how to connect misp-workbench to [Claude Code](https://claude.ai/code) so you can query threat intelligence directly from the terminal.

## 1. Get your MCP token

Generate a scoped MCP token from the `/mcp/config` endpoint:

```bash
curl -s https://your-instance/mcp/config \
  -H "Authorization: Bearer <your-api-token>" | jq .
```

The response contains a ready-to-use configuration:

```json
{
  "mcpServers": {
    "misp-workbench": {
      "type": "http",
      "url": "https://your-instance/mcp",
      "headers": {
        "Authorization": "Bearer <mcp-scoped-token>"
      }
    }
  }
}
```

Copy the `Bearer` token value — you'll use it in the next step.

## 2. Add the MCP server

Run `claude mcp add` from any terminal:

```bash
claude mcp add --transport http \
  --header "Authorization: Bearer <mcp-scoped-token>" \
  misp-workbench https://your-instance/mcp
```

### Scope options

By default the server is added at **project scope** (stored in `.mcp.json` in the current directory, suitable for team repos). To add it at **user scope** instead (available in all projects, stored in `~/.claude.json`):

```bash
claude mcp add --transport http --scope user \
  --header "Authorization: Bearer <mcp-scoped-token>" \
  misp-workbench https://your-instance/mcp
```

!!! tip "Use an environment variable for the token"
    Avoid hardcoding the token in your shell history. Set it as an env var first:

    ```bash
    export MISP_MCP_TOKEN="<mcp-scoped-token>"

    claude mcp add --transport http --scope user \
      --header "Authorization: Bearer ${MISP_MCP_TOKEN}" \
      misp-workbench https://your-instance/mcp
    ```

## 3. Verify the connection

List registered MCP servers and confirm misp-workbench appears:

```bash
claude mcp list
```

<img src="../../../screenshots/claude-code/claude-code_1-list-mcp.png">

Then start a session and check the server is reachable:

```bash
claude
```

In the Claude Code session, type `/mcp` to see connected servers and their tool counts.


<video width="1080" controls>
  <source src="../../../screenshots/claude-code/claude-code_2-view-misp-workbench-mcp.webm" type="video/mp4">
</video>

## Local dev (no auth)

When running the dev stack locally with `MCP_AUTH_ENABLED=false` (the default), no token is needed:

```bash
claude mcp add --transport http misp-workbench http://localhost:8000/mcp
```

## Example session

Once connected, you can ask questions in natural language:

```
> search for ransomware events from the last 30 days
> look up the indicator 185.220.101.45 and check for correlations
> generate a threat report for APT28
> enrich 8.8.8.8 with geolocation
```

<video width="1080" controls>
  <source src="../../../screenshots/claude-code/claude-code_3-enrich-ioc-misp-workbench-mcp.webm" type="video/mp4">
</video>

Claude will automatically select the appropriate tools (`search_events`, `search_attributes`, `get_correlations`, `enrich_indicator`, etc.) and combine results into a response.

See [MCP Server Overview](index.md) for the full list of available tools, resources, and prompts.
