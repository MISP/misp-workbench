import logging

from app.auth.security import get_current_active_user
from app.database import engine
from app.opensearch import OpenSearchClient
from app.rediscli import RedisClient
from app.schemas import user as user_schemas
from fastapi import APIRouter, Security
from sqlalchemy import text

router = APIRouter()

logger = logging.getLogger(__name__)


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
