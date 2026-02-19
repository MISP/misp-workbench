import logging

from app.auth.security import get_current_active_user
from app.opensearch import OpenSearchClient
from app.schemas import user as user_schemas
from fastapi import APIRouter, Security

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
