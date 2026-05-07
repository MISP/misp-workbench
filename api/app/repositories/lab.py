"""CRUD + visibility for Tech Lab notebooks and folders.

All read methods take ``current_user_id`` and apply visibility filtering:
``row.visibility == 'global' OR row.user_id == current_user_id``.
All write/delete methods enforce ownership: ``row.user_id == current_user_id``.
"""

import logging
import re
import uuid
from datetime import datetime, timezone
from typing import Optional

from app.models import lab as lab_models
from app.schemas import lab as lab_schemas
from sqlalchemy import or_
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────────
# Folders
# ──────────────────────────────────────────────────────────────────────────


def _user_can_see(row, current_user_id: int) -> bool:
    return row.visibility == "global" or row.user_id == current_user_id


def get_folder_by_id(
    db: Session, folder_id: int, current_user_id: int
) -> Optional[lab_models.LabFolder]:
    folder = (
        db.query(lab_models.LabFolder)
        .filter(lab_models.LabFolder.id == folder_id)
        .first()
    )
    if folder is None or not _user_can_see(folder, current_user_id):
        return None
    return folder


def create_folder(
    db: Session,
    payload: lab_schemas.LabFolderCreate,
    current_user_id: int,
) -> lab_models.LabFolder:
    if payload.parent_id is not None:
        parent = get_folder_by_id(db, payload.parent_id, current_user_id)
        if parent is None:
            raise ValueError("parent folder not found")
        if parent.visibility != payload.visibility:
            raise ValueError("parent folder visibility mismatch")
    folder = lab_models.LabFolder(
        user_id=current_user_id,
        parent_id=payload.parent_id,
        name=payload.name,
        visibility=payload.visibility,
        created_at=datetime.now(timezone.utc),
    )
    db.add(folder)
    db.commit()
    db.refresh(folder)
    return folder


def update_folder(
    db: Session,
    folder_id: int,
    payload: lab_schemas.LabFolderUpdate,
    current_user_id: int,
) -> Optional[lab_models.LabFolder]:
    folder = (
        db.query(lab_models.LabFolder)
        .filter(lab_models.LabFolder.id == folder_id)
        .first()
    )
    if folder is None or not _user_can_see(folder, current_user_id):
        return None
    if folder.user_id != current_user_id:
        raise PermissionError("only the owner can update this folder")

    data = payload.model_dump(exclude_unset=True)
    if "parent_id" in data:
        new_parent_id = data["parent_id"]
        if new_parent_id is not None:
            parent = get_folder_by_id(db, new_parent_id, current_user_id)
            if parent is None:
                raise ValueError("parent folder not found")
            if parent.visibility != folder.visibility:
                raise ValueError("parent folder visibility mismatch")
            if _would_create_cycle(db, folder.id, new_parent_id):
                raise ValueError("move would create a folder cycle")
        folder.parent_id = new_parent_id
    if "name" in data and data["name"] is not None:
        folder.name = data["name"]
    folder.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(folder)
    return folder


def delete_folder(
    db: Session, folder_id: int, current_user_id: int
) -> Optional[dict]:
    folder = (
        db.query(lab_models.LabFolder)
        .filter(lab_models.LabFolder.id == folder_id)
        .first()
    )
    if folder is None or not _user_can_see(folder, current_user_id):
        return None
    if folder.user_id != current_user_id:
        raise PermissionError("only the owner can delete this folder")
    db.delete(folder)
    db.commit()
    return {"status": "success"}


def _would_create_cycle(
    db: Session, folder_id: int, new_parent_id: int
) -> bool:
    """Return True if making folder_id a child of new_parent_id would form a cycle."""
    cursor = new_parent_id
    seen: set[int] = set()
    while cursor is not None:
        if cursor in seen:
            return True
        seen.add(cursor)
        if cursor == folder_id:
            return True
        parent = (
            db.query(lab_models.LabFolder.parent_id)
            .filter(lab_models.LabFolder.id == cursor)
            .first()
        )
        cursor = parent[0] if parent else None
    return False


# ──────────────────────────────────────────────────────────────────────────
# Notebooks
# ──────────────────────────────────────────────────────────────────────────


def get_notebook_by_id(
    db: Session, notebook_id: int, current_user_id: int
) -> Optional[lab_models.LabNotebook]:
    nb = (
        db.query(lab_models.LabNotebook)
        .filter(lab_models.LabNotebook.id == notebook_id)
        .first()
    )
    if nb is None or not _user_can_see(nb, current_user_id):
        return None
    return nb


def create_notebook(
    db: Session,
    payload: lab_schemas.LabNotebookCreate,
    current_user_id: int,
) -> lab_models.LabNotebook:
    if payload.folder_id is not None:
        folder = get_folder_by_id(db, payload.folder_id, current_user_id)
        if folder is None:
            raise ValueError("folder not found")
        if folder.visibility != payload.visibility:
            raise ValueError("folder visibility mismatch")
    nb = lab_models.LabNotebook(
        user_id=current_user_id,
        folder_id=payload.folder_id,
        visibility=payload.visibility,
        name=payload.name,
        description=payload.description,
        source=payload.source or "",
        cell_outputs={},
        created_at=datetime.now(timezone.utc),
    )
    db.add(nb)
    db.commit()
    db.refresh(nb)
    return nb


def update_notebook(
    db: Session,
    notebook_id: int,
    payload: lab_schemas.LabNotebookUpdate,
    current_user_id: int,
) -> Optional[lab_models.LabNotebook]:
    nb = (
        db.query(lab_models.LabNotebook)
        .filter(lab_models.LabNotebook.id == notebook_id)
        .first()
    )
    if nb is None or not _user_can_see(nb, current_user_id):
        return None
    if nb.user_id != current_user_id:
        raise PermissionError("only the owner can update this notebook")

    data = payload.model_dump(exclude_unset=True)
    if "folder_id" in data:
        new_folder_id = data["folder_id"]
        if new_folder_id is not None:
            folder = get_folder_by_id(db, new_folder_id, current_user_id)
            if folder is None:
                raise ValueError("folder not found")
            if folder.visibility != nb.visibility:
                raise ValueError("folder visibility mismatch")
        nb.folder_id = new_folder_id
    for key in ("name", "description", "source"):
        if key in data and data[key] is not None:
            setattr(nb, key, data[key])
    nb.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(nb)
    return nb


def delete_notebook(
    db: Session, notebook_id: int, current_user_id: int
) -> Optional[dict]:
    nb = (
        db.query(lab_models.LabNotebook)
        .filter(lab_models.LabNotebook.id == notebook_id)
        .first()
    )
    if nb is None or not _user_can_see(nb, current_user_id):
        return None
    if nb.user_id != current_user_id:
        raise PermissionError("only the owner can delete this notebook")
    db.delete(nb)
    db.commit()
    return {"status": "success"}


def fork_notebook(
    db: Session, notebook_id: int, current_user_id: int
) -> Optional[lab_models.LabNotebook]:
    """Duplicate a visible notebook into a new personal one owned by the current user.

    Cell ids inside ``source`` are regenerated so the original and the fork
    can be open simultaneously without execution conflicts; ``cell_outputs``
    is rewritten to use the new ids.
    """
    src = get_notebook_by_id(db, notebook_id, current_user_id)
    if src is None:
        return None

    new_source, id_map = _regenerate_cell_ids(src.source or "")
    new_outputs: dict[str, list[dict]] = {}
    for old_id, new_id in id_map.items():
        if old_id in (src.cell_outputs or {}):
            new_outputs[new_id] = src.cell_outputs[old_id]

    fork = lab_models.LabNotebook(
        user_id=current_user_id,
        folder_id=None,
        visibility="personal",
        name=f"{src.name} (fork)",
        description=src.description,
        source=new_source,
        cell_outputs=new_outputs,
        created_at=datetime.now(timezone.utc),
    )
    db.add(fork)
    db.commit()
    db.refresh(fork)
    return fork


_CELL_DELIMITER_RE = re.compile(
    r"^(#\s*%%)(?:\s*\[id=([0-9a-fA-F-]+)\])?(.*)$",
    re.MULTILINE,
)


def _regenerate_cell_ids(source: str) -> tuple[str, dict[str, str]]:
    """Replace every ``[id=<uuid>]`` in cell delimiters with a fresh uuid.

    Returns the rewritten source plus a map from old id → new id for any
    delimiter that had one. Delimiters without an id get a new id assigned.
    """
    id_map: dict[str, str] = {}

    def _sub(match: re.Match) -> str:
        prefix, old_id, suffix = match.group(1), match.group(2), match.group(3)
        new_id = str(uuid.uuid4())
        if old_id:
            id_map[old_id] = new_id
        return f"{prefix} [id={new_id}]{suffix}"

    rewritten = _CELL_DELIMITER_RE.sub(_sub, source)
    return rewritten, id_map


# ──────────────────────────────────────────────────────────────────────────
# Executions
# ──────────────────────────────────────────────────────────────────────────


def create_execution(
    db: Session,
    notebook_id: int,
    cell_id: str,
    current_user_id: int,
) -> lab_models.LabExecution:
    """Create a queued execution row.

    Caller is expected to have already verified the user can run the notebook
    (read-visibility check). Allowed for any reader: a global notebook's
    reader can run cells under their own kernel keyed by
    ``(running_user_id, notebook_id)``.
    """
    row = lab_models.LabExecution(
        notebook_id=notebook_id,
        user_id=current_user_id,
        cell_id=cell_id,
        status="queued",
        outputs=[],
        created_at=datetime.now(timezone.utc),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def get_execution(
    db: Session, execution_id: int, current_user_id: int
) -> Optional[lab_models.LabExecution]:
    row = (
        db.query(lab_models.LabExecution)
        .filter(lab_models.LabExecution.id == execution_id)
        .first()
    )
    if row is None:
        return None
    # Anyone who can see the notebook can poll its executions; private
    # notebook executions remain invisible.
    nb = (
        db.query(lab_models.LabNotebook)
        .filter(lab_models.LabNotebook.id == row.notebook_id)
        .first()
    )
    if nb is None or not _user_can_see(nb, current_user_id):
        return None
    return row


def write_cell_source(
    db: Session,
    notebook_id: int,
    cell_id: str,
    source: str,
    current_user_id: int,
) -> Optional[lab_models.LabNotebook]:
    """Replace the source of a single cell inside a notebook's blob.

    Used by ``POST /cells/execute`` to capture the editor-current source
    before queueing the run, so the executor can find the up-to-date slice.
    Owner-only — non-owners can't mutate a global notebook's source. They
    can still execute (their cell's source travels in the request body and
    is found by re-parsing the stored blob, which is OK because they ran
    Fork-to-personal first if they wanted a private copy to mutate).

    Returns the updated notebook, or ``None`` if not found / not permitted.
    For non-owner runs, a no-op success: returns the notebook unchanged.
    """
    from app.services.tech_lab.lab.cell_parser import (
        parse_cells,
        serialize_cells,
    )

    nb = get_notebook_by_id(db, notebook_id, current_user_id)
    if nb is None:
        return None
    if nb.user_id != current_user_id:
        return nb  # non-owner: don't mutate; return as-is

    cells = parse_cells(nb.source or "")
    found = False
    for c in cells:
        if c.cell_id == cell_id:
            c.source = source if source.endswith("\n") else source + "\n"
            found = True
            break
    if not found:
        return nb
    nb.source = serialize_cells(cells)
    nb.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(nb)
    return nb


# ──────────────────────────────────────────────────────────────────────────
# Tree
# ──────────────────────────────────────────────────────────────────────────


def get_tree(db: Session, current_user_id: int) -> lab_schemas.LabTree:
    folders = (
        db.query(lab_models.LabFolder)
        .filter(
            or_(
                lab_models.LabFolder.visibility == "global",
                lab_models.LabFolder.user_id == current_user_id,
            )
        )
        .order_by(lab_models.LabFolder.name.asc())
        .all()
    )
    notebooks = (
        db.query(lab_models.LabNotebook)
        .filter(
            or_(
                lab_models.LabNotebook.visibility == "global",
                lab_models.LabNotebook.user_id == current_user_id,
            )
        )
        .order_by(lab_models.LabNotebook.name.asc())
        .all()
    )
    return lab_schemas.LabTree(
        folders=[lab_schemas.LabFolder.model_validate(f) for f in folders],
        notebooks=[
            lab_schemas.LabNotebookSummary.model_validate(n) for n in notebooks
        ],
    )
