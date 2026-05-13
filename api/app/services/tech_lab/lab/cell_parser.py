"""Parse the notebook ``source`` blob into cells, and inverse.

The on-disk format is a single text document with ``# %% [id=<uuid>] code|markdown``
delimiter lines (Jupytext "percent format", augmented with stable cell ids).
The frontend Monaco editor edits this directly; the server parses it on demand
(for ``execute_all`` and import/export). Permissive: missing ``[id=...]`` gets
a fresh uuid; missing type defaults to ``code``; trailing whitespace is preserved.
"""

import re
import uuid
from dataclasses import dataclass
from typing import Literal


CellType = Literal["code", "markdown"]

_DELIMITER_RE = re.compile(
    r"^#\s*%%(?:\s*\[id=([0-9a-fA-F-]+)\])?(?:\s+(code|markdown))?\s*(.*)$"
)


@dataclass
class ParsedCell:
    cell_id: str
    type: CellType
    source: str
    """The cell body, **without** the delimiter line. Trailing newline preserved."""


def parse_cells(source: str) -> list[ParsedCell]:
    """Split ``source`` into cells on ``# %% ...`` delimiter lines.

    Content before the first delimiter is treated as an implicit code cell
    (with a fresh id) so notebooks that don't start with ``# %%`` still
    behave sensibly.
    """
    if source is None:
        return []
    lines = source.splitlines(keepends=True)
    cells: list[ParsedCell] = []
    cur_id: str | None = None
    cur_type: CellType = "code"
    cur_body: list[str] = []

    def _flush() -> None:
        if cur_id is None and not cur_body:
            return
        cells.append(
            ParsedCell(
                cell_id=cur_id or str(uuid.uuid4()),
                type=cur_type,
                source="".join(cur_body),
            )
        )

    for line in lines:
        stripped = line.rstrip("\r\n")
        m = _DELIMITER_RE.match(stripped)
        if m is not None:
            _flush()
            cur_id = m.group(1) or str(uuid.uuid4())
            cur_type = m.group(2) or "code"  # type: ignore[assignment]
            cur_body = []
            continue
        cur_body.append(line)
    _flush()
    return cells


def serialize_cells(cells: list[ParsedCell]) -> str:
    """Inverse of ``parse_cells`` — emit canonical delimiter lines.

    Always writes the explicit ``[id=...] <type>`` header so subsequent parses
    are stable.
    """
    out: list[str] = []
    for c in cells:
        out.append(f"# %% [id={c.cell_id}] {c.type}\n")
        out.append(c.source)
        if c.source and not c.source.endswith("\n"):
            out.append("\n")
    return "".join(out)
