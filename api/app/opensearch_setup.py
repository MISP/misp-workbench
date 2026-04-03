"""
OpenSearch bootstrap: provision a dedicated API user via the Security API.

Runs when OPENSEARCH_USERNAME is set to something other than 'admin'.
Uses OPENSEARCH_INITIAL_ADMIN_PASSWORD to authenticate as admin and create
the user with OPENSEARCH_PASSWORD and all_access backend role.
"""
import json
import os
import ssl
import sys
import time
import urllib.error
import urllib.request

HOSTNAME = os.environ.get("OPENSEARCH_HOSTNAME", "opensearch")
PORT = os.environ.get("OPENSEARCH_PORT", "9200")
USE_SSL = os.environ.get("ENVIRONMENT", "prod") == "prod"
BASE_URL = f"{'https' if USE_SSL else 'http'}://{HOSTNAME}:{PORT}"

USERNAME = os.environ.get("OPENSEARCH_USERNAME", "")
PASSWORD = os.environ.get("OPENSEARCH_PASSWORD", "")
ADMIN_PASSWORD = os.environ.get("OPENSEARCH_INITIAL_ADMIN_PASSWORD", "")

_ssl_ctx = ssl.create_default_context()
_ssl_ctx.check_hostname = False
_ssl_ctx.verify_mode = ssl.CERT_NONE


def _request(method, path, data=None, *, auth_user="admin", auth_pass=ADMIN_PASSWORD):
    import base64

    body = json.dumps(data).encode() if data is not None else None
    creds = base64.b64encode(f"{auth_user}:{auth_pass}".encode()).decode()
    headers = {"Authorization": f"Basic {creds}"}
    if body:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(
        f"{BASE_URL}{path}", data=body, headers=headers, method=method
    )
    try:
        with urllib.request.urlopen(req, context=_ssl_ctx if USE_SSL else None) as resp:
            content = resp.read()
            return json.loads(content) if content else {}, resp.status
    except urllib.error.HTTPError as e:
        content = e.read()
        try:
            return json.loads(content), e.code
        except Exception:
            return {}, e.code


def wait_for_opensearch(retries=30, delay=2):
    print("Waiting for OpenSearch...", flush=True)
    for _ in range(retries):
        try:
            _, code = _request("GET", "/_cluster/health")
            if code == 200:
                print("OpenSearch is ready.", flush=True)
                return
        except Exception as e:
            print(f"Waiting for OpenSearch failed with: {e!r}", file=sys.stderr, flush=True)
        time.sleep(delay)
    print("ERROR: OpenSearch did not become ready.", file=sys.stderr)
    sys.exit(1)


def provision_user():
    _, code = _request("GET", f"/_plugins/_security/api/internalusers/{USERNAME}")
    if code == 200:
        print(f"OpenSearch user '{USERNAME}' already exists.", flush=True)
        return

    print(f"Creating OpenSearch user '{USERNAME}'...", flush=True)
    _, code = _request(
        "PUT",
        f"/_plugins/_security/api/internalusers/{USERNAME}",
        {
            "password": PASSWORD,
            "backend_roles": ["all_access"],
            "description": "misp-workbench API service account",
        },
    )
    if code in (200, 201):
        print(f"OpenSearch user '{USERNAME}' created.", flush=True)
    else:
        print(
            f"ERROR: failed to create OpenSearch user '{USERNAME}' (HTTP {code}).",
            file=sys.stderr,
        )
        sys.exit(1)


if __name__ == "__main__":
    if not USERNAME or USERNAME == "admin":
        sys.exit(0)

    if not ADMIN_PASSWORD:
        print(
            "ERROR: OPENSEARCH_INITIAL_ADMIN_PASSWORD must be set to provision an OpenSearch user.",
            file=sys.stderr,
        )
        sys.exit(1)

    wait_for_opensearch()
    provision_user()
