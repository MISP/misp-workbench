"""Execute a reactor script for one queued run.

Container-level isolation does the real work; this module is responsible for:
- pulling source from storage (s3 or local fs)
- compiling and running it with a tame globals dict
- enforcing a wall-clock timeout
- capturing stdout/stderr to storage
- moving the run row through queued -> running -> success/failed/timed_out
"""

import inspect
import io
import logging
import sys
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime, timezone

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


def run_script(db: Session, run_id: int) -> None:
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

    source = _read_source(script.source_uri)
    triggered_by = run.triggered_by or {}
    payload = triggered_by.get("payload", triggered_by)
    trigger = {
        "resource_type": triggered_by.get("resource_type"),
        "action": triggered_by.get("action"),
    }

    stdout = io.StringIO()
    stderr = io.StringIO()
    error: str | None = None
    status = "success"
    ctx: ReactorContext | None = None

    try:
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
                _call_handler(fn, ctx, payload, trigger)
    except ScriptTimeout as e:
        status = "timed_out"
        error = str(e)
    except Exception as e:  # pragma: no cover - exercised by tests
        status = "failed"
        error = f"{type(e).__name__}: {e}"
        logger.exception("reactor run id=%s failed", run_id)

    log_blob = _format_log(stdout.getvalue(), stderr.getvalue(), error)
    log_uri = _write_log(run_id, log_blob)

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


def _call_handler(fn, ctx, payload, trigger) -> None:
    """Invoke the user handler.

    Backward compat: 2-arg ``(ctx, payload)`` handlers are still accepted.
    Newer scripts can declare ``(ctx, payload, trigger)`` to receive the
    ``{"resource_type", "action"}`` info that fired the run.
    """
    try:
        positional = [
            p
            for p in inspect.signature(fn).parameters.values()
            if p.kind
            in (
                inspect.Parameter.POSITIONAL_ONLY,
                inspect.Parameter.POSITIONAL_OR_KEYWORD,
                inspect.Parameter.VAR_POSITIONAL,
            )
        ]
        accepts_trigger = any(
            p.kind == inspect.Parameter.VAR_POSITIONAL for p in positional
        ) or len([p for p in positional if p.kind != inspect.Parameter.VAR_POSITIONAL]) >= 3
    except (TypeError, ValueError):
        accepts_trigger = False

    if accepts_trigger:
        try:
            fn(ctx, payload, trigger)
        except TypeError:
            fn(ctx, payload)
    else:
        fn(ctx, payload)


def _read_source(source_uri: str) -> str:
    return reactor_storage.read_object(source_uri).decode("utf-8")


def _format_log(stdout: str, stderr: str, error: str | None) -> str:
    parts = []
    if stdout:
        parts.append("=== stdout ===\n" + stdout)
    if stderr:
        parts.append("=== stderr ===\n" + stderr)
    if error:
        parts.append("=== error ===\n" + error)
    return "\n".join(parts) if parts else ""


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
