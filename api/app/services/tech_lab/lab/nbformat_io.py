"""Convert between our delimiter-source notebooks and ``nbformat`` JSON.

We store notebooks as a single text blob with ``# %% [id=...] code|markdown``
delimiters, but JupyterLab and downstream tooling speak nbformat. The
conversion is lossless for cell sources and ids; cell outputs are preserved
in export so a downloaded notebook can be opened with stored results, but
dropped on import (they will regenerate on the next run).
"""

from __future__ import annotations

import uuid as _uuid
from typing import Any

from app.models import lab as lab_models
from app.services.tech_lab.lab.cell_parser import (
    ParsedCell,
    parse_cells,
    serialize_cells,
)


def to_nbformat(nb: lab_models.LabNotebook) -> dict:
    """Build an nbformat 4.5 JSON-serializable dict from a notebook row."""
    cell_outputs = nb.cell_outputs or {}
    cells: list[dict[str, Any]] = []
    for c in parse_cells(nb.source or ""):
        base = {
            "cell_type": c.type,
            "id": c.cell_id,
            "metadata": {},
            "source": _split_for_nbformat(c.source),
        }
        if c.type == "code":
            base["outputs"] = cell_outputs.get(c.cell_id, [])
            base["execution_count"] = None
        cells.append(base)

    return {
        "nbformat": 4,
        "nbformat_minor": 5,
        "metadata": {
            "kernelspec": {
                "name": "python3",
                "display_name": "Python 3",
                "language": "python",
            },
            "language_info": {"name": "python"},
            "misp_workbench": {
                "notebook_id": nb.id,
                "name": nb.name,
                "visibility": nb.visibility,
            },
        },
        "cells": cells,
    }


def from_nbformat(blob: dict) -> tuple[str, str]:
    """Convert an nbformat dict to our delimiter-source format.

    Returns ``(source, name)``. Cell ids are preserved when present and
    regenerated otherwise. Cell outputs are intentionally dropped — they'll
    re-render on the next execution against a real kernel.
    """
    parsed: list[ParsedCell] = []
    for c in blob.get("cells") or []:
        cell_type = c.get("cell_type")
        if cell_type not in ("code", "markdown"):
            continue
        source = c.get("source") or ""
        if isinstance(source, list):
            source = "".join(source)
        parsed.append(
            ParsedCell(
                cell_id=str(c.get("id") or _uuid.uuid4()),
                type=cell_type,
                source=source,
            )
        )
    name = (
        ((blob.get("metadata") or {}).get("misp_workbench") or {}).get("name")
        or "imported notebook"
    )
    return serialize_cells(parsed), name


def _split_for_nbformat(text: str) -> list[str]:
    """nbformat expects ``source`` as a list of lines (each ending with ``\\n``).

    Splitting keeps diffs friendly when the file is opened in Jupyter and
    re-saved.
    """
    if not text:
        return []
    parts = text.splitlines(keepends=True)
    return parts
