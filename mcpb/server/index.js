#!/usr/bin/env node
/**
 * stdio -> streamable-HTTP bridge for the MISP Workbench MCP endpoint.
 *
 * Claude Desktop launches bundle servers over stdio, but MISP Workbench serves
 * MCP over HTTP with a bearer token. `.mcpb` cannot declare a remote server, so
 * something local has to bridge the two.
 *
 * Written here rather than shelling out to `npx mcp-remote` so the bundle has
 * no runtime dependency, no npm fetch on first launch, and nothing third-party
 * in the path of a credential. It also sidesteps the header-with-a-space bug
 * that mangles `Authorization: Bearer ...` when Claude Desktop on Windows
 * invokes npx.
 *
 * The token arrives by environment variable, never as an argument, so it does
 * not show up in the process list.
 */

const BASE = (process.env.MISP_WORKBENCH_URL || "").trim().replace(/\/+$/, "");
const TOKEN = (process.env.MISP_WORKBENCH_TOKEN || "").trim();

function fail(message) {
  process.stderr.write(`[misp-workbench] ${message}\n`);
  process.exit(1);
}

if (!BASE) fail("MISP_WORKBENCH_URL is not set. Set the instance URL in the extension settings.");
if (!TOKEN) fail("MISP_WORKBENCH_TOKEN is not set. Generate one from /mcp/config and paste it into the extension settings.");
if (!/^https?:\/\//i.test(BASE)) fail(`Instance URL must start with http:// or https:// (got "${BASE}").`);

// Accept either the bare instance URL or one that already ends in /mcp.
const ENDPOINT = BASE.endsWith("/mcp") ? BASE : `${BASE}/mcp`;

// Captured from the initialize response and echoed on every later request;
// without it the server treats each call as a new session.
let sessionId = null;

function send(message) {
  process.stdout.write(`${JSON.stringify(message)}\n`);
}

function protocolError(id, code, message) {
  if (id === undefined || id === null) return; // notifications get no reply
  send({ jsonrpc: "2.0", id, error: { code, message } });
}

/** Pull JSON-RPC payloads out of an SSE body. */
function parseEventStream(body) {
  const messages = [];
  for (const block of body.split(/\r?\n\r?\n/)) {
    const data = block
      .split(/\r?\n/)
      .filter((line) => line.startsWith("data:"))
      .map((line) => line.slice(5).trim())
      .join("");
    if (!data) continue;
    try {
      messages.push(JSON.parse(data));
    } catch {
      // A non-JSON data frame is a keep-alive or comment; ignore it.
    }
  }
  return messages;
}

async function forward(request) {
  const headers = {
    "Content-Type": "application/json",
    // The server may answer with either shape, so accept both.
    Accept: "application/json, text/event-stream",
    Authorization: `Bearer ${TOKEN}`,
  };
  if (sessionId) headers["Mcp-Session-Id"] = sessionId;

  let response;
  try {
    response = await fetch(ENDPOINT, {
      method: "POST",
      headers,
      body: JSON.stringify(request),
    });
  } catch (error) {
    protocolError(request.id, -32001, `Cannot reach ${ENDPOINT}: ${error.message}`);
    return;
  }

  const newSession = response.headers.get("mcp-session-id");
  if (newSession) sessionId = newSession;

  if (response.status === 401 || response.status === 403) {
    protocolError(request.id, -32002, "MISP Workbench rejected the token. Regenerate it from /mcp/config and update the extension settings.");
    return;
  }

  // 202 with no body is the correct answer to a notification.
  if (response.status === 202) return;

  const text = await response.text();
  if (!response.ok) {
    protocolError(request.id, -32003, `HTTP ${response.status} from ${ENDPOINT}: ${text.slice(0, 200)}`);
    return;
  }
  if (!text) return;

  const contentType = response.headers.get("content-type") || "";
  const messages = contentType.includes("text/event-stream")
    ? parseEventStream(text)
    : [JSON.parse(text)];

  for (const message of messages) send(message);
}

// Requests are forwarded in the order they arrive: the initialize response
// carries the session id every later call depends on, so overlapping them
// would race.
let queue = Promise.resolve();
let buffer = "";

process.stdin.setEncoding("utf8");
process.stdin.on("data", (chunk) => {
  buffer += chunk;
  let newline;
  while ((newline = buffer.indexOf("\n")) !== -1) {
    const line = buffer.slice(0, newline).trim();
    buffer = buffer.slice(newline + 1);
    if (!line) continue;

    let request;
    try {
      request = JSON.parse(line);
    } catch {
      process.stderr.write(`[misp-workbench] ignoring unparseable line from client\n`);
      continue;
    }
    queue = queue.then(() => forward(request)).catch((error) => {
      protocolError(request.id, -32603, `Bridge error: ${error.message}`);
    });
  }
});

process.stdin.on("end", () => queue.then(() => process.exit(0)));
