"""Execute a reactor script for one queued run.

Container-level isolation does the real work; this module is responsible for:
- pulling source from S3
- compiling and running it with a tame globals dict
- enforcing a wall-clock timeout
- capturing stdout/stderr to S3
- moving the run row through queued -> running -> success/failed/timed_out
"""

import io
import logging
import sys
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime, timezone

from app.models import reactor as reactor_models
from app.services.s3 import get_s3_client
from app.services.tech_lab.reactor.context import ReactorContext
from app.services.tech_lab.reactor.sandbox import (
    ScriptTimeout,
    restricted_builtins,
    time_limit,
)
from app.settings import get_settings
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
    payload = (run.triggered_by or {}).get("payload", run.triggered_by or {})

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
                fn(ctx, payload)
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


def _read_source(source_uri: str) -> str:
    settings = get_settings()
    if settings.Storage.engine == "s3":
        client = get_s3_client()
        obj = client.get_object(Bucket=settings.Storage.s3.bucket, Key=source_uri)
        return obj["Body"].read().decode("utf-8")
    # Local fallback (dev / tests). Stored under /tmp/reactor.
    import os

    base = "/tmp/reactor"
    full = os.path.normpath(os.path.join(base, source_uri))
    if not full.startswith(base):
        raise RuntimeError("invalid source path")
    with open(full, "r", encoding="utf-8") as f:
        return f.read()


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
    settings = get_settings()
    if settings.Storage.engine == "s3":
        client = get_s3_client()
        client.put_object(
            Bucket=settings.Storage.s3.bucket,
            Key=key,
            Body=content.encode("utf-8"),
        )
        return key

    import os

    base = "/tmp/reactor"
    os.makedirs(os.path.join(base, "runs"), exist_ok=True)
    full = os.path.normpath(os.path.join(base, "runs", f"{run_id}.log"))
    if not full.startswith(base):
        raise RuntimeError("invalid log path")
    with open(full, "w", encoding="utf-8") as f:
        f.write(content)
    return key


def read_log(log_uri: str) -> str:
    if not log_uri:
        return ""
    settings = get_settings()
    if settings.Storage.engine == "s3":
        client = get_s3_client()
        obj = client.get_object(Bucket=settings.Storage.s3.bucket, Key=log_uri)
        return obj["Body"].read().decode("utf-8", errors="replace")

    import os

    base = "/tmp/reactor"
    # log_uri is like reactor/runs/<id>.log -> map to /tmp/reactor/runs/<id>.log
    rel = log_uri.removeprefix("reactor/")
    full = os.path.normpath(os.path.join(base, rel))
    if not full.startswith(base):
        return ""
    if not os.path.exists(full):
        return ""
    with open(full, "r", encoding="utf-8") as f:
        return f.read()


# Hook used by tests that need to reset stdout/stderr if Celery's prefork
# worker reparents file descriptors mid-run.
def _reset_streams_for_tests() -> None:  # pragma: no cover
    sys.stdout.flush()
    sys.stderr.flush()
