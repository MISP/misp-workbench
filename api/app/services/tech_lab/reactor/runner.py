"""Execute a reactor script for one queued run.

Container-level isolation does the real work; this module is responsible for:
- pulling source from storage (s3 or local fs)
- compiling and running it with a tame globals dict
- enforcing a wall-clock timeout
- capturing stdout/stderr to storage
- moving the run row through queued -> running -> success/failed/timed_out
"""

import functools
import io
import json
import logging
import sys
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime, timezone

import pyinstrument
from app.models import reactor as reactor_models
from app.services.tech_lab.reactor import storage as reactor_storage
from app.services.tech_lab.reactor.context import ReactorContext
from app.services.tech_lab.reactor.sandbox import (
    ScriptTimeout,
    restricted_builtins,
    time_limit,
)
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


def run_script(db: Session, run_id: int, *, profile: bool = False) -> None:
    """Execute a queued reactor run.

    ``profile=True`` samples the user handler with pyinstrument. The text
    summary is appended to the run log under ``=== profile ===`` and the
    full call tree is persisted as JSON at ``reactor/runs/<id>.profile.json``
    so the UI can render an interactive flame chart. Intended for the
    synchronous ``/test`` endpoint — too heavy for prod queue workers.
    """
    run = (
        db.query(reactor_models.ReactorRun)
        .filter(reactor_models.ReactorRun.id == run_id)
        .first()
    )
    if run is None:
        logger.warning("reactor run id=%s not found", run_id)
        return

    script = (
        db.query(reactor_models.ReactorScript)
        .filter(reactor_models.ReactorScript.id == run.script_id)
        .first()
    )
    if script is None:
        run.status = "failed"
        run.error = "script not found"
        run.finished_at = datetime.now(timezone.utc)
        db.commit()
        return

    run.status = "running"
    run.started_at = datetime.now(timezone.utc)
    db.commit()

    triggered_by = run.triggered_by or {}
    payload = triggered_by.get("payload", {})
    trigger = {
        "resource_type": triggered_by.get("resource_type"),
        "action": triggered_by.get("action"),
    }

    stdout = io.StringIO()
    stderr = io.StringIO()
    error: str | None = None
    status = "success"
    ctx: ReactorContext | None = None
    profiler = pyinstrument.Profiler() if profile else None

    try:
        # Source read lives inside the try so storage errors (for example a
        # missing S3 object) become a failed run row instead of an escaped
        # Celery exception that leaves the row stuck in "running".
        source = _read_source(script.source_uri)
        ctx = ReactorContext(db, script, run)
        compiled = compile(source, f"<reactor:{script.id}>", "exec")
        script_globals: dict = {"__builtins__": restricted_builtins(), "__name__": "__reactor__"}

        with redirect_stdout(stdout), redirect_stderr(stderr):
            with time_limit(script.timeout_seconds):
                exec(compiled, script_globals)
                fn = script_globals.get(script.entrypoint)
                if not callable(fn):
                    raise RuntimeError(
                        f"entrypoint {script.entrypoint!r} not defined or not callable"
                    )
                if profiler is not None:
                    profiler.start()
                    try:
                        fn(ctx, payload, trigger)
                    finally:
                        profiler.stop()
                else:
                    fn(ctx, payload, trigger)
    except ScriptTimeout as e:
        status = "timed_out"
        error = str(e)
    except Exception as e:  # pragma: no cover - exercised by tests
        status = "failed"
        error = f"{type(e).__name__}: {e}"
        logger.exception("reactor run id=%s failed", run_id)

    profile_text = _format_profile(profiler) if profiler is not None else None
    log_blob = _format_log(
        stdout.getvalue(), stderr.getvalue(), error, profile=profile_text
    )
    log_uri = _write_log(run_id, log_blob)
    if profiler is not None:
        _write_profile(run_id, profiler)

    run.status = status
    run.error = error
    run.finished_at = datetime.now(timezone.utc)
    run.log_uri = log_uri
    if ctx is not None:
        run.writes_count = ctx._writes_count

    script.last_run_at = run.finished_at
    script.last_run_status = status
    script.last_run_id = run.id
    script.updated_at = run.finished_at

    db.commit()


@functools.lru_cache(maxsize=128)
def _read_source(source_uri: str) -> str:
    """Fetch and decode script source. Cached because URIs are immutable —
    every script update writes a new ``reactor/scripts/<uuid>.py`` and the
    old key is deleted, so a hit is always still-fresh source.
    """
    return reactor_storage.read_object(source_uri).decode("utf-8")


def _format_log(
    stdout: str, stderr: str, error: str | None, profile: str | None = None
) -> str:
    parts = []
    if stdout:
        parts.append("=== stdout ===\n" + stdout)
    if stderr:
        parts.append("=== stderr ===\n" + stderr)
    if error:
        parts.append("=== error ===\n" + error)
    if profile:
        parts.append("=== profile ===\n" + profile)
    return "\n".join(parts) if parts else ""


def _format_profile(profiler: pyinstrument.Profiler) -> str:
    """Render pyinstrument's text summary for the run log."""
    return profiler.output_text(unicode=True, color=False, show_all=False)


def _write_profile(run_id: int, profiler: pyinstrument.Profiler) -> str:
    """Persist a d3-flame-graph-shaped tree to storage. Returns the key."""
    tree = _profile_to_flame_tree(profiler)
    key = f"reactor/runs/{run_id}.profile.json"
    reactor_storage.write_object(key, json.dumps(tree).encode("utf-8"))
    return key


def _profile_to_flame_tree(profiler: pyinstrument.Profiler) -> dict:
    """Convert pyinstrument's call tree to ``{name, value, children}``.

    d3-flame-graph wants ``value`` in arbitrary units; pyinstrument frames
    expose ``time`` (seconds) which is what we want. ``time`` is already
    inclusive (frame + descendants), matching flame-graph semantics.
    """
    root_frame = profiler.last_session.root_frame() if profiler.last_session else None
    if root_frame is None:
        return {"name": "(empty)", "value": 0, "children": []}
    return _frame_to_flame_node(root_frame)


def _frame_to_flame_node(frame) -> dict:
    name = getattr(frame, "function", None) or "<unknown>"
    file_short = getattr(frame, "file_path_short", None)
    if file_short:
        line = getattr(frame, "line_no", None)
        name = f"{name} ({file_short}:{line})" if line else f"{name} ({file_short})"
    return {
        "name": name,
        "value": float(getattr(frame, "time", 0.0)),
        "children": [_frame_to_flame_node(c) for c in (frame.children or [])],
    }


def read_profile(run_id: int) -> dict | None:
    key = f"reactor/runs/{run_id}.profile.json"
    if not reactor_storage.object_exists(key):
        return None
    try:
        return json.loads(reactor_storage.read_object(key).decode("utf-8"))
    except (FileNotFoundError, ValueError):
        return None


def _write_log(run_id: int, content: str) -> str:
    key = f"reactor/runs/{run_id}.log"
    reactor_storage.write_object(key, content.encode("utf-8"))
    return key


def read_log(log_uri: str) -> str:
    if not log_uri or not reactor_storage.object_exists(log_uri):
        return ""
    try:
        return reactor_storage.read_object(log_uri).decode("utf-8", errors="replace")
    except FileNotFoundError:
        return ""


# Hook used by tests that need to reset stdout/stderr if Celery's prefork
# worker reparents file descriptors mid-run.
def _reset_streams_for_tests() -> None:  # pragma: no cover
    sys.stdout.flush()
    sys.stderr.flush()
