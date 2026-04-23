# API keys

Long-lived API keys let third-party integrations — Splunk, SOAR platforms, custom scripts, CI pipelines — authenticate against the misp-workbench REST API without going through the interactive OAuth2 flow.

A key is a 40-character hex string (MISP-compatible) stored only as a SHA-256 hash. The raw token is shown **once** at creation time and cannot be retrieved later.

## When to use an API key vs. an OAuth2 token

| Use case | Recommended |
|---|---|
| Browser session / interactive user | OAuth2 (`/auth/token`) |
| Long-running integration, script, or daemon | API key |
| Machine-to-machine with short-lived credentials | OAuth2 refresh token |
| MCP client configuration | `/mcp/config` (generates an MCP-scoped JWT) |

API keys are the right fit when you need a credential that survives across restarts, can be rotated independently of user passwords, and carries a narrowly scoped set of permissions.

## Creating a key

Navigate to ***internals*** → ***API keys*** and click **New API key**.

| Field | Description |
|---|---|
| **Name** | Human-readable label (e.g. "Splunk production"). Required. |
| **Comment** | Free-form notes — what the key is for, who owns the integration. |
| **Expires at** | Optional. After this timestamp the key stops authenticating. Leave empty for a non-expiring key. |
| **Scopes** | The permissions the key carries. Only scopes your role allows are selectable. |

After you click **Create**, the raw token is displayed in a banner. **Copy it immediately** — once dismissed, it is gone forever. If lost, delete the key and create a new one.

### Creating via the API

```
POST /api-keys/
Authorization: Bearer <your-oauth2-token>
Required scope: api_keys:create
```

```json
{
  "name": "Splunk production",
  "comment": "SIEM correlation feed",
  "scopes": ["events:read", "attributes:read"],
  "expires_at": "2027-01-01T00:00:00Z"
}
```

The response includes the raw `token` field. It is not returned by any subsequent call.

```json
{
  "id": 42,
  "user_id": 7,
  "name": "Splunk production",
  "scopes": ["events:read", "attributes:read"],
  "expires_at": "2027-01-01T00:00:00+00:00",
  "disabled": false,
  "admin_disabled": false,
  "created_at": "2026-04-22T10:15:00+00:00",
  "token": "4f3a9d12c8b7e6a5f4d3c2b1a0e9f8d7c6b5a4e3"
}
```

## Using a key

Send the raw token in the `Authorization` header. Both forms are accepted:

=== "Bearer scheme (recommended)"

    ```bash
    curl https://your-instance/events/ \
      -H "Authorization: Bearer 4f3a9d12c8b7e6a5f4d3c2b1a0e9f8d7c6b5a4e3"
    ```

=== "MISP-compatible (raw)"

    ```bash
    curl https://your-instance/events/ \
      -H "Authorization: 4f3a9d12c8b7e6a5f4d3c2b1a0e9f8d7c6b5a4e3"
    ```

The raw form (no `Bearer` prefix) exists for drop-in compatibility with MISP clients. Non-Bearer schemes like `Basic` are rejected even if the credentials happen to match the 40-hex format.

!!! warning "TLS only"
    API keys are bearer credentials — anyone who intercepts one can use it until it's revoked. Always use HTTPS, and never paste tokens into issue trackers, logs, or shared chat.

## Scopes

A key's effective permission set is the **intersection** of:

1. Its own `scopes` list (what you requested at creation time), and
2. The owner's role scopes at the time of each request.

If the owner is later downgraded, or the role loses a scope, the key silently stops being able to call the affected endpoints — no re-issue needed.

### Available scopes

Scopes follow a `<resource>:<action>` pattern. Common examples:

| Scope | Grants |
|---|---|
| `events:read` | Read events and their attributes |
| `events:create` | Create new events |
| `events:publish` | Publish events to synced servers |
| `attributes:read` | Read attributes across events |
| `feeds:fetch` | Trigger feed fetches |
| `hunts:run` | Execute saved hunts |
| `mcp:*` | All MCP server tools and resources |

You can request wildcards (`events:*`) if your role grants them. See the [API reference](./index.md) for the full scope list, or `GET /auth/scopes` to enumerate.

### Principle of least privilege

Issue a separate key per integration, scoped only to what that integration needs. A Splunk correlator only reads — give it `events:read` and `attributes:read`, nothing else. A CI job that imports events needs `events:create`; it does not need `events:publish` or `events:delete`.

## Lifecycle

| Action | Scope | Effect |
|---|---|---|
| Disable | `api_keys:update` | Key stops authenticating; can be re-enabled later |
| Enable | `api_keys:update` | Clears the owner's disable flag |
| Delete | `api_keys:delete` | Irreversible; the hash is removed |
| Expire | _(automatic)_ | Key stops authenticating at `expires_at` |

### Rotation

There is no in-place rotation. To rotate:

1. Create a new key with the same name + scopes.
2. Update your integration to use the new token.
3. Delete the old key.

Using disjoint names (e.g. `splunk-prod-2026-04`) makes this traceable in the audit log.

## Audit log

Every security-relevant action on a key is recorded in the audit log:

| Action | When |
|---|---|
| `api_key.created` | A key is minted |
| `api_key.authenticated` | The key authenticates a request (debounced to once per minute per key) |
| `api_key.disabled` / `api_key.enabled` | Owner toggles the disable flag |
| `api_key.deleted` | Owner deletes the key |
| `api_key.admin_locked` / `api_key.admin_unlocked` | Admin sets or clears an admin hold |
| `api_key.admin_deleted` | Admin deletes a key they do not own |

Each entry captures the actor (user id + `user`/`api_key`/`system`), IP address, user agent, and action-specific metadata. The raw token is **never** logged.

See [Audit logs](./audit-logs.md) for how to browse and filter these entries.

## Administrative controls (incident response)

Users with the `api_keys:admin` scope can manage any user's keys from ***internals*** → ***API keys (admin)***. This is intended for incident response when a key may be compromised.

The admin hold is tracked by a separate `admin_disabled` flag that the owner cannot clear:

- Admin **locks** a key: `admin_disabled = true`. The key stops authenticating. The owner sees a **locked by admin** badge, cannot re-enable, and cannot delete the key — preserving it for forensic inspection.
- Admin **unlocks**: clears `admin_disabled`. If the owner had also disabled the key, it remains `disabled` until the owner re-enables it.
- Admin **deletes**: hard-deletes the key. Use only when forensic evidence is no longer needed.

Both owner and admin flags are independent — a key authenticates only when **both** are `false` and the key has not expired.

By default only users with the `*` scope (admin role 1) have `api_keys:admin`. Grant it to additional roles via the roles API when you need separate incident-response personas.

## API reference

| Method | Path | Description | Scopes |
|---|---|---|---|
| `GET` | `/api-keys/` | List your own keys | `api_keys:read` |
| `POST` | `/api-keys/` | Create a key | `api_keys:create` |
| `PATCH` | `/api-keys/{id}` | Enable/disable your own key | `api_keys:update` |
| `DELETE` | `/api-keys/{id}` | Delete your own key | `api_keys:delete` |
| `GET` | `/admin/api-keys/` | List any user's keys (optional `?user_id=`) | `api_keys:admin` |
| `PATCH` | `/admin/api-keys/{id}` | Lock/unlock a key | `api_keys:admin` |
| `DELETE` | `/admin/api-keys/{id}` | Delete any user's key | `api_keys:admin` |

## FAQ

**Can I retrieve the raw token after creation?**
No. Only the SHA-256 hash is stored. If you lose the token, delete the key and create a new one.

**Can a key outlive its owner?**
No. If the owner account is deleted or disabled, all their keys stop authenticating.

**Does the key give me everything my role can do?**
No. It gives you the intersection of the key's scopes and the owner's current role scopes. Requesting more scopes than your role permits is rejected at creation time.

**What happens if an admin locks my key?**
It stops authenticating immediately. You will see a **locked by admin** badge in the UI, cannot re-enable or delete it yourself, and should contact an administrator. The key is preserved so the admin can audit recent usage via the `api_key.authenticated` entries.

**Can I scope a key to a specific IP address or network?**
Not today. Rotate narrowly scoped keys and rely on the audit log (IP + user agent are captured) to detect misuse.
