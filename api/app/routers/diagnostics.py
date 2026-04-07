import json
import logging
import os
import urllib.request

from app.auth.security import get_current_active_user
from app.database import engine
from app.opensearch import OpenSearchClient
from app.rediscli import RedisClient
from app.schemas import user as user_schemas
from app.settings import get_settings
from fastapi import APIRouter, Response, Security
from sqlalchemy import text

router = APIRouter()

logger = logging.getLogger(__name__)


@router.get("/health", tags=["Health"])
def health(response: Response, full: bool = False):
    """Unauthenticated liveness/readiness probe.

    Without `?full=true` returns immediately with `{"status": "ok"}` — suitable
    for fast liveness checks (load balancer, container restart policy).

    With `?full=true` probes every dependent service and returns per-service
    status. Returns HTTP 503 if any service is unreachable.
    """
    if not full:
        return {"status": "ok"}

    checks = {}

    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        checks["postgres"] = "ok"
    except Exception as e:
        logger.warning("Health check: postgres unavailable: %s", e)
        checks["postgres"] = "error"

    try:
        OpenSearchClient.cluster.health(timeout=2)
        checks["opensearch"] = "ok"
    except Exception as e:
        logger.warning("Health check: opensearch unavailable: %s", e)
        checks["opensearch"] = "error"

    try:
        RedisClient.ping()
        checks["redis"] = "ok"
    except Exception as e:
        logger.warning("Health check: redis unavailable: %s", e)
        checks["redis"] = "error"

    try:
        settings = get_settings()
        url = f"http://{settings.Modules.host}:{settings.Modules.port}/modules"
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        urllib.request.urlopen(req, timeout=3)
        checks["modules"] = "ok"
    except Exception as e:
        logger.warning("Health check: modules unavailable: %s", e)
        checks["modules"] = "error"

    try:
        settings = get_settings()
        if settings.Storage.engine == "s3":
            from app.s3cli import S3Client
            S3Client.head_bucket(Bucket=settings.Storage.s3.bucket)
        else:
            if not os.path.isdir("/tmp/attachments"):
                raise OSError("/tmp/attachments directory not found")
        checks["storage"] = "ok"
    except Exception as e:
        logger.warning("Health check: storage unavailable: %s", e)
        checks["storage"] = "error"

    try:
        from app.worker.tasks import celery_app
        active = celery_app.control.inspect(timeout=3).active()
        if not active:
            raise RuntimeError("no active workers")
        checks["workers"] = "ok"
    except Exception as e:
        logger.warning("Health check: workers unavailable: %s", e)
        checks["workers"] = "error"

    healthy = all(v == "ok" for v in checks.values())
    if not healthy:
        response.status_code = 503
    return {"status": "ok" if healthy else "degraded", "checks": checks}


def _format_bytes(b):
    if b is None:
        return None
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if b < 1024:
            return f"{b:.1f} {unit}"
        b /= 1024
    return f"{b:.1f} PB"


def _extract_node_stats(raw_nodes):
    nodes = []
    for node_id, n in raw_nodes.items():
        os_ = n.get("os", {})
        jvm = n.get("jvm", {})
        fs = n.get("fs", {}).get("total", {})
        nodes.append({
            "id": node_id,
            "name": n.get("name"),
            "cpu_percent": os_.get("cpu", {}).get("percent"),
            "mem_used_percent": os_.get("mem", {}).get("used_percent"),
            "mem_total": _format_bytes(os_.get("mem", {}).get("total_in_bytes")),
            "mem_used": _format_bytes(os_.get("mem", {}).get("used_in_bytes")),
            "heap_used_percent": jvm.get("mem", {}).get("heap_used_percent"),
            "heap_used": _format_bytes(jvm.get("mem", {}).get("heap_used_in_bytes")),
            "heap_max": _format_bytes(jvm.get("mem", {}).get("heap_max_in_bytes")),
            "disk_total": _format_bytes(fs.get("total_in_bytes")),
            "disk_available": _format_bytes(fs.get("available_in_bytes")),
        })
    return nodes


@router.get("/diagnostics/opensearch")
def get_opensearch_diagnostics(
    user: user_schemas.User = Security(get_current_active_user, scopes=["tasks:read"]),
):
    try:
        health = OpenSearchClient.cluster.health()
        indices = OpenSearchClient.cat.indices(
            index="misp-*",
            format="json",
            h="index,health,status,docs.count,docs.deleted,store.size",
        )
        raw_nodes = OpenSearchClient.nodes.stats(metric=["os", "jvm", "fs"])
        shards = OpenSearchClient.cat.shards(
            index="misp-*",
            format="json",
            h="index,shard,prirep,state,docs,store,node,unassigned.reason",
        )
        return {
            "connected": True,
            "cluster": health,
            "indices": indices,
            "nodes": _extract_node_stats(raw_nodes.get("nodes", {})),
            "shards": shards,
        }
    except Exception as e:
        logger.error("Failed to fetch OpenSearch diagnostics: %s", e)
        return {
            "connected": False,
            "error": str(e),
            "cluster": None,
            "indices": [],
            "nodes": [],
            "shards": [],
        }


@router.get("/diagnostics/redis")
def get_redis_diagnostics(
    user: user_schemas.User = Security(get_current_active_user, scopes=["tasks:read"]),
):
    try:
        info = RedisClient.info()
        keyspace = {k: v for k, v in info.items() if k.startswith("db")}
        return {
            "connected": True,
            "version": info.get("redis_version"),
            "mode": info.get("redis_mode"),
            "uptime_seconds": info.get("uptime_in_seconds"),
            "connected_clients": info.get("connected_clients"),
            "blocked_clients": info.get("blocked_clients"),
            "memory_used": info.get("used_memory_human"),
            "memory_peak": info.get("used_memory_peak_human"),
            "memory_fragmentation_ratio": info.get("mem_fragmentation_ratio"),
            "total_commands_processed": info.get("total_commands_processed"),
            "total_connections_received": info.get("total_connections_received"),
            "keyspace_hits": info.get("keyspace_hits"),
            "keyspace_misses": info.get("keyspace_misses"),
            "keyspace": keyspace,
        }
    except Exception as e:
        logger.error("Failed to fetch Redis diagnostics: %s", e)
        return {
            "connected": False,
            "error": str(e),
        }


@router.get("/diagnostics/postgres")
def get_postgres_diagnostics(
    user: user_schemas.User = Security(get_current_active_user, scopes=["tasks:read"]),
):
    try:
        with engine.connect() as conn:
            version = conn.execute(text("SELECT version()")).scalar()
            db_name = conn.execute(text("SELECT current_database()")).scalar()
            db_size = conn.execute(
                text("SELECT pg_size_pretty(pg_database_size(current_database()))")
            ).scalar()
            max_connections = conn.execute(
                text("SELECT setting::int FROM pg_settings WHERE name = 'max_connections'")
            ).scalar()
            conn_rows = conn.execute(
                text("""
                    SELECT state, count(*) as count
                    FROM pg_stat_activity
                    WHERE datname = current_database()
                    GROUP BY state
                """)
            ).fetchall()
            table_rows = conn.execute(
                text("""
                    SELECT
                        relname,
                        n_live_tup,
                        n_dead_tup,
                        pg_size_pretty(pg_total_relation_size(relid)) AS size,
                        pg_total_relation_size(relid) AS size_bytes
                    FROM pg_stat_user_tables
                    ORDER BY size_bytes DESC
                """)
            ).fetchall()

        connections = {row.state or "unknown": row.count for row in conn_rows}
        connections["max"] = max_connections
        connections["total"] = sum(v for k, v in connections.items() if k != "max")

        tables = [
            {
                "name": row.relname,
                "live_rows": row.n_live_tup,
                "dead_rows": row.n_dead_tup,
                "size": row.size,
            }
            for row in table_rows
        ]

        return {
            "connected": True,
            "version": version,
            "database": db_name,
            "db_size": db_size,
            "connections": connections,
            "tables": tables,
        }
    except Exception as e:
        logger.error("Failed to fetch PostgreSQL diagnostics: %s", e)
        return {
            "connected": False,
            "error": str(e),
        }


@router.get("/diagnostics/storage")
def get_storage_diagnostics(
    user: user_schemas.User = Security(get_current_active_user, scopes=["tasks:read"]),
):
    import shutil

    settings = get_settings()
    engine_name = settings.Storage.engine

    if engine_name == "local":
        path = "/tmp/attachments"
        path_exists = os.path.isdir(path)

        object_count = 0
        total_size = 0
        if path_exists:
            for entry in os.scandir(path):
                if entry.is_file(follow_symlinks=False):
                    object_count += 1
                    total_size += entry.stat().st_size

        try:
            disk = shutil.disk_usage(path if path_exists else "/tmp")
            disk_info = {
                "disk_total": _format_bytes(disk.total),
                "disk_used": _format_bytes(disk.used),
                "disk_free": _format_bytes(disk.free),
                "disk_used_percent": round(disk.used / disk.total * 100, 1),
            }
        except Exception:
            disk_info = {}

        return {
            "engine": "local",
            "path": path,
            "path_exists": path_exists,
            "object_count": object_count,
            "total_size": total_size,
            "total_size_human": _format_bytes(total_size),
            **disk_info,
        }

    if engine_name == "s3":
        s3 = settings.Storage.s3
        admin_url = os.environ.get("GARAGE_ADMIN_URL", "http://garage:3903")
        admin_token = os.environ.get("GARAGE_ADMIN_TOKEN", "")
        base = {"engine": "s3", "endpoint": s3.endpoint, "bucket": s3.bucket, "secure": s3.secure}

        try:
            from app.s3cli import S3Client

            S3Client.head_bucket(Bucket=s3.bucket)
        except Exception as e:
            logger.error("Failed to connect to S3 storage: %s", e)
            return {**base, "connected": False, "error": str(e)}

        try:
            req = urllib.request.Request(
                f"{admin_url}/v2/GetBucketInfo?globalAlias={s3.bucket}",
                headers={"Authorization": f"Bearer {admin_token}"},
            )
            with urllib.request.urlopen(req) as resp:
                info = json.loads(resp.read())

            objects = info.get("objects", 0)
            bytes_ = info.get("bytes", 0)
            return {
                **base,
                "connected": True,
                "object_count": objects,
                "total_size": bytes_,
                "total_size_human": _format_bytes(bytes_),
            }
        except Exception as e:
            logger.warning("Garage admin API unavailable, skipping bucket stats: %s", e)
            return {**base, "connected": True}

    return {"engine": engine_name}


@router.get("/diagnostics/modules")
def get_modules_diagnostics(
    user: user_schemas.User = Security(get_current_active_user, scopes=["tasks:read"]),
):
    settings = get_settings()
    host = settings.Modules.host
    port = settings.Modules.port
    url = f"http://{host}:{port}/modules"

    try:
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            modules = json.loads(resp.read())

        counts = {}
        for m in modules:
            mod_type = m.get("type", "unknown")
            counts[mod_type] = counts.get(mod_type, 0) + 1

        return {
            "connected": True,
            "url": url,
            "total": len(modules),
            "counts": counts,
            "modules": [
                {
                    "name": m.get("name"),
                    "type": m.get("type"),
                    "meta_name": m.get("meta", {}).get("name"),
                    "description": m.get("meta", {}).get("description"),
                    "version": m.get("meta", {}).get("version"),
                    "module_type": m.get("meta", {}).get("module-type", []),
                }
                for m in modules
            ],
        }
    except Exception as e:
        logger.error("Failed to fetch MISP modules diagnostics: %s", e)
        return {
            "connected": False,
            "url": url,
            "error": str(e),
        }
