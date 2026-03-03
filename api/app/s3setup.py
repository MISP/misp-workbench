"""
Garage bootstrap: apply cluster layout, import S3 key, create bucket.
Run once at startup when STORAGE_ENGINE=s3.
"""
import json
import os
import sys
import time
import urllib.error
import urllib.request

ADMIN_URL = os.environ.get("GARAGE_ADMIN_URL", "http://garage:3903")
ADMIN_TOKEN = os.environ.get("GARAGE_ADMIN_TOKEN", "garage-dev-admin-token")
ACCESS_KEY = os.environ["S3_ACCESS_KEY"]
SECRET_KEY = os.environ["S3_SECRET_KEY"]
BUCKET = os.environ["S3_BUCKET"]
ENDPOINT = os.environ["S3_ENDPOINT"]
SECURE = os.environ.get("S3_SECURE", "false").lower() == "true"


def _admin(method, path, data=None):
    body = json.dumps(data).encode() if data is not None else None
    headers = {"Authorization": f"Bearer {ADMIN_TOKEN}"}
    if body:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(
        f"{ADMIN_URL}{path}",
        data=body,
        headers=headers,
        method=method,
    )
    try:
        with urllib.request.urlopen(req) as resp:
            content = resp.read()
            return json.loads(content) if content else {}, resp.status
    except urllib.error.HTTPError as e:
        content = e.read()
        try:
            return json.loads(content), e.code
        except Exception:
            return {}, e.code


def wait_for_garage(retries=30, delay=2):
    print("Waiting for Garage admin API...", flush=True)
    for _ in range(retries):
        try:
            _, code = _admin("GET", "/v2/GetClusterHealth")
            if code == 200:
                print("Garage is ready.", flush=True)
                return
        except Exception as e:
            # Ignore transient errors while waiting for Garage, but log them for troubleshooting.
            print(f"Waiting for Garage admin API failed with: {e!r}", file=sys.stderr, flush=True)
        time.sleep(delay)
    print("ERROR: Garage did not become ready.", file=sys.stderr)
    sys.exit(1)


def apply_layout():
    response, _ = _admin("GET", "/v2/GetClusterStatus")
    if response.get("layoutVersion", 0) > 0:
        print("Garage cluster layout already applied.", flush=True)
        return

    nodes = response.get("nodes", [])
    if not nodes:
        print("ERROR: No Garage nodes found in cluster status.", file=sys.stderr)
        sys.exit(1)

    node_id = nodes[0]["id"]
    current_version = response.get("layoutVersion", 0)
    print(f"Applying cluster layout for node {node_id[:12]}...", flush=True)
    _admin("POST", "/v2/UpdateClusterLayout", {
        "roles": [{"id": node_id, "zone": "dc1", "capacity": 1_000_000_000, "tags": []}]
    })
    _, code = _admin("POST", "/v2/ApplyClusterLayout", {"version": current_version + 1})
    if code not in (200, 204):
        print(f"WARNING: layout apply returned HTTP {code}", flush=True)
    else:
        print("Cluster layout applied.", flush=True)


def import_key():
    print(f"Importing S3 key {ACCESS_KEY}...", flush=True)
    response, code = _admin("POST", "/v2/ImportKey", {
        "name": "api",
        "accessKeyId": ACCESS_KEY,
        "secretAccessKey": SECRET_KEY,
    })
    if code in (200, 204):
        print("S3 key imported.", flush=True)
    elif code == 409:
        print("S3 key already exists.", flush=True)
    else:
        print(f"ERROR: key import failed HTTP {code}: {response}", file=sys.stderr)
        sys.exit(1)


def ensure_bucket():
    # Check if bucket already exists
    _, code = _admin("GET", f"/v2/GetBucketInfo?globalAlias={BUCKET}")
    if code == 200:
        print(f"Bucket '{BUCKET}' already exists.", flush=True)
    else:
        response, code = _admin("POST", "/v2/CreateBucket", {"globalAlias": BUCKET})
        if code not in (200, 204):
            print(f"ERROR: bucket creation failed HTTP {code}: {response}", file=sys.stderr)
            sys.exit(1)
        print(f"Bucket '{BUCKET}' created.", flush=True)

    # Grant the key read/write/owner access on the bucket
    bucket_info, _ = _admin("GET", f"/v2/GetBucketInfo?globalAlias={BUCKET}")
    bucket_id = bucket_info.get("id")
    if not bucket_id:
        print("ERROR: could not retrieve bucket ID.", file=sys.stderr)
        sys.exit(1)
    _, code = _admin("POST", "/v2/AllowBucketKey", {
        "bucketId": bucket_id,
        "accessKeyId": ACCESS_KEY,
        "permissions": {"read": True, "write": True, "owner": True},
    })
    if code not in (200, 204):
        print(f"WARNING: AllowBucketKey returned HTTP {code}", flush=True)
    else:
        print(f"Key permissions set on bucket '{BUCKET}'.", flush=True)


if __name__ == "__main__":
    wait_for_garage()
    apply_layout()
    import_key()
    ensure_bucket()
    print("Garage S3 setup complete.", flush=True)
