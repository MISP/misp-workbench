import re
from typing import Optional

from app.repositories import feeds as feeds_repository
from fastapi import HTTPException, status

# Ordered most-specific first to avoid false matches
_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("sha512", re.compile(r"^[a-fA-F0-9]{128}$")),
    ("sha256", re.compile(r"^[a-fA-F0-9]{64}$")),
    ("sha1", re.compile(r"^[a-fA-F0-9]{40}$")),
    ("md5", re.compile(r"^[a-fA-F0-9]{32}$")),
    ("ip-src", re.compile(r"^\d{1,3}(\.\d{1,3}){3}(/\d{1,2})?$")),
    (
        "ip-src",
        re.compile(
            r"^([0-9a-fA-F]{1,4}:){2,7}[0-9a-fA-F]{1,4}(/\d{1,3})?$"
        ),
    ),  # IPv6
    ("url", re.compile(r"^https?://", re.IGNORECASE)),
    ("email-src", re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")),
    ("cve", re.compile(r"^CVE-\d{4}-\d+$", re.IGNORECASE)),
    (
        "domain",
        re.compile(
            r"^(?:[a-zA-Z0-9](?:[a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}$"
        ),
    ),
]


def detect_type(value: str) -> Optional[str]:
    """Detect the most likely MISP attribute type for a freetext value."""
    value = value.strip()
    for type_name, pattern in _PATTERNS:
        if pattern.match(value):
            return type_name
    return "other"


def preview_freetext_feed(settings: dict, limit: int = 10):
    if settings.get("input_source") != "network":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Local file preview is not yet supported",
        )

    lines = feeds_repository.fetch_csv_content_from_network(settings["url"])
    freetext_config = (settings.get("settings") or {}).get("freetextConfig", {})
    type_detection = freetext_config.get("type_detection", "automatic")
    fixed_type = freetext_config.get("fixed_type")

    rows = []
    for line in lines[:limit]:
        value = line.strip()
        if not value:
            continue
        detected = detect_type(value)
        attr_type = fixed_type if type_detection == "fixed" and fixed_type else detected
        rows.append({"value": value, "detected_type": detected, "type": attr_type})

    return {"result": "success", "rows": rows}
