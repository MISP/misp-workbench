"""Drive a single cell execution end-to-end.

Loads a ``LabExecution`` row, sends its source to the appropriate kernel,
drains IOPub messages until ``status == idle`` (or ``timeout_seconds``
elapses), persists outputs onto the row, and — only when the running user
is the notebook owner — writes them back into ``notebook.cell_outputs`` so
they survive a reload.
"""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import Any, Optional

from app.models import lab as lab_models
from app.services.tech_lab.lab import kernel_manager as km
from app.services.tech_lab.lab.cell_parser import parse_cells
from sqlalchemy.orm import Session


logger = logging.getLogger(__name__)


def execute_cell(
    db: Session,
    execution_id: int,
    *,
    timeout_seconds: int = 60,
    registry: Optional[km.LabKernelRegistry] = None,
) -> None:
    """Run one queued execution to completion (success / error / interrupted).

    Idempotent on terminal status: if the row is already finished, no-op
    (covers Celery retries).
    """
    row = (
        db.query(lab_models.LabExecution)
        .filter(lab_models.LabExecution.id == execution_id)
        .first()
    )
    if row is None:
        logger.warning("lab_execute_cell: execution id=%s not found", execution_id)
        return
    if row.status not in ("queued", "running"):
        logger.info(
            "lab_execute_cell: execution id=%s already terminal (%s); skipping",
            execution_id,
            row.status,
        )
        return

    nb = (
        db.query(lab_models.LabNotebook)
        .filter(lab_models.LabNotebook.id == row.notebook_id)
        .first()
    )
    if nb is None:
        row.status = "error"
        row.error = "notebook not found"
        row.finished_at = datetime.now(timezone.utc)
        db.commit()
        return

    cell_source = _find_cell_source(nb.source or "", row.cell_id)
    if cell_source is None:
        row.status = "error"
        row.error = f"cell {row.cell_id} not present in notebook source"
        row.finished_at = datetime.now(timezone.utc)
        db.commit()
        return

    row.status = "running"
    row.started_at = datetime.now(timezone.utc)
    db.commit()

    reg = registry or km.get_default_registry()
    key = (row.user_id, row.notebook_id)
    timeout = max(1, int(timeout_seconds))

    outputs: list[dict[str, Any]] = []
    execution_count: Optional[int] = None
    error_text: Optional[str] = None
    status = "success"

    try:
        entry = reg.get_or_start(key)
        with entry.lock:
            client = entry.client
            msg_id = client.execute(  # type: ignore[attr-defined]
                cell_source, silent=False, store_history=True
            )
            outputs, execution_count, error_text, status, timed_out = _drain_iopub(
                client, msg_id, timeout=timeout
            )
            if timed_out:
                # Send SIGINT so the runaway cell raises KeyboardInterrupt and
                # stops emitting IOPub. If we don't, the kernel keeps running
                # and the *next* execution drains its leftover messages.
                reg.interrupt(key)
                grace_outputs, _, _, _, _ = _drain_iopub(
                    client, msg_id, timeout=5
                )
                outputs.extend(grace_outputs)
            reg.touch(key)
    except Exception as e:  # noqa: BLE001
        status = "error"
        error_text = f"{type(e).__name__}: {e}"
        logger.exception("lab_execute_cell id=%s crashed", execution_id)

    row.status = status
    row.error = error_text
    row.outputs = outputs
    row.execution_count = execution_count
    row.finished_at = datetime.now(timezone.utc)

    if row.user_id == nb.user_id:
        cell_outputs = dict(nb.cell_outputs or {})
        cell_outputs[row.cell_id] = outputs
        nb.cell_outputs = cell_outputs
        nb.last_executed_at = row.finished_at
    db.commit()


def _find_cell_source(notebook_source: str, cell_id: str) -> Optional[str]:
    for cell in parse_cells(notebook_source):
        if cell.cell_id == cell_id:
            return cell.source
    return None


def _drain_iopub(
    client,
    parent_msg_id: str,
    *,
    timeout: int,
) -> tuple[list[dict[str, Any]], Optional[int], Optional[str], str, bool]:
    """Collect IOPub messages whose parent is ``parent_msg_id`` until idle.

    Returns ``(outputs, execution_count, error_text, status, timed_out)``.
    ``timed_out`` is True when the deadline elapsed before an ``idle`` status
    message was received — the caller is then expected to send an interrupt
    and drain leftover messages.
    """
    outputs: list[dict[str, Any]] = []
    execution_count: Optional[int] = None
    error_text: Optional[str] = None
    status = "success"
    timed_out = False
    deadline = time.monotonic() + timeout

    while True:
        remaining = max(0.05, deadline - time.monotonic())
        try:
            msg = client.get_iopub_msg(timeout=remaining)
        except Exception:  # noqa: BLE001
            status = "interrupted"
            error_text = f"cell exceeded {timeout}s"
            timed_out = True
            break
        parent = msg.get("parent_header") or {}
        if parent.get("msg_id") != parent_msg_id:
            continue
        msg_type = msg.get("msg_type")
        content = msg.get("content") or {}
        if msg_type == "status":
            if content.get("execution_state") == "idle":
                break
            continue
        if msg_type == "stream":
            outputs.append(
                {
                    "output_type": "stream",
                    "name": content.get("name", "stdout"),
                    "text": content.get("text", ""),
                }
            )
        elif msg_type == "display_data":
            outputs.append(
                {
                    "output_type": "display_data",
                    "data": content.get("data", {}),
                    "metadata": content.get("metadata", {}),
                }
            )
        elif msg_type == "execute_result":
            execution_count = content.get("execution_count")
            outputs.append(
                {
                    "output_type": "execute_result",
                    "execution_count": execution_count,
                    "data": content.get("data", {}),
                    "metadata": content.get("metadata", {}),
                }
            )
        elif msg_type == "error":
            status = "error"
            error_text = f"{content.get('ename')}: {content.get('evalue')}"
            outputs.append(
                {
                    "output_type": "error",
                    "ename": content.get("ename", ""),
                    "evalue": content.get("evalue", ""),
                    "traceback": content.get("traceback", []),
                }
            )
        elif msg_type == "execute_input":
            execution_count = content.get("execution_count")

    return outputs, execution_count, error_text, status, timed_out
