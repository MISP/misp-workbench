"""Unit tests for ``app/services/tech_lab/reactor/runner.py``."""

from contextlib import contextmanager
from unittest.mock import MagicMock, patch

from app.models import reactor as reactor_models

# Import via the worker path first to fully resolve the runner ↔ context cycle
# before the direct runner import below.
from app.repositories import reactor as _reactor_repository  # noqa: F401
from app.services.tech_lab.reactor import runner
from app.services.tech_lab.reactor.sandbox import ScriptTimeout


# ──────────────────────────────────────────────────────────────────────────
# _format_log
# ──────────────────────────────────────────────────────────────────────────


class TestFormatLog:
    def test_empty_when_all_empty(self):
        assert runner._format_log("", "", None) == ""

    def test_stdout_only(self):
        assert runner._format_log("hi\n", "", None) == "=== stdout ===\nhi\n"

    def test_stderr_only(self):
        assert runner._format_log("", "warn\n", None) == "=== stderr ===\nwarn\n"

    def test_error_only(self):
        assert runner._format_log("", "", "boom") == "=== error ===\nboom"

    def test_all_sections_joined(self):
        out = runner._format_log("a\n", "b\n", "c")
        assert out == "=== stdout ===\na\n\n=== stderr ===\nb\n\n=== error ===\nc"

    def test_omits_empty_sections(self):
        # stdout + error, no stderr
        out = runner._format_log("a\n", "", "c")
        assert "stderr" not in out
        assert "stdout" in out and "error" in out


# ──────────────────────────────────────────────────────────────────────────
# _call_handler — backwards-compat dispatch
# ──────────────────────────────────────────────────────────────────────────


class TestCallHandler:
    def test_two_arg_handler_called_without_trigger(self):
        seen = []

        def handle(ctx, payload):
            seen.append((ctx, payload))

        runner._call_handler(handle, "ctx", {"k": "v"}, {"resource_type": "event"})
        assert seen == [("ctx", {"k": "v"})]

    def test_three_arg_handler_receives_trigger(self):
        seen = []

        def handle(ctx, payload, trigger):
            seen.append((ctx, payload, trigger))

        runner._call_handler(handle, "ctx", {"k": "v"}, {"resource_type": "event"})
        assert seen == [("ctx", {"k": "v"}, {"resource_type": "event"})]

    def test_var_positional_handler_receives_trigger(self):
        seen = []

        def handle(*args):
            seen.append(args)

        runner._call_handler(handle, "ctx", {"k": "v"}, {"resource_type": "event"})
        # *args path always passes the trigger.
        assert seen == [("ctx", {"k": "v"}, {"resource_type": "event"})]

    def test_unintrospectable_callable_falls_back_to_three_args(self):
        # Some C-implemented callables raise from inspect.signature; the
        # fallback assumes the new (ctx, payload, trigger) shape.
        seen = []

        def handle(ctx, payload, trigger):
            seen.append((ctx, payload, trigger))

        with patch.object(
            runner.inspect, "signature", side_effect=ValueError("no signature")
        ):
            runner._call_handler(handle, "ctx", "p", "t")
        assert seen == [("ctx", "p", "t")]


# ──────────────────────────────────────────────────────────────────────────
# Source / log helpers
# ──────────────────────────────────────────────────────────────────────────


class TestReadSource:
    def test_decodes_storage_bytes(self):
        with patch.object(
            runner.reactor_storage, "read_object", return_value=b"print('x')\n"
        ) as ro:
            assert runner._read_source("reactor/scripts/x.py") == "print('x')\n"
        ro.assert_called_once_with("reactor/scripts/x.py")


class TestWriteLog:
    def test_writes_canonical_key_and_returns_it(self):
        with patch.object(runner.reactor_storage, "write_object") as wo:
            uri = runner._write_log(123, "hello\n")
        assert uri == "reactor/runs/123.log"
        wo.assert_called_once_with("reactor/runs/123.log", b"hello\n")


class TestReadLog:
    def test_returns_empty_for_empty_uri(self):
        # Must short-circuit without consulting storage.
        with patch.object(runner.reactor_storage, "object_exists") as oe:
            assert runner.read_log("") == ""
            assert runner.read_log(None) == ""
        oe.assert_not_called()

    def test_returns_empty_when_object_missing(self):
        with patch.object(
            runner.reactor_storage, "object_exists", return_value=False
        ), patch.object(runner.reactor_storage, "read_object") as ro:
            assert runner.read_log("reactor/runs/9.log") == ""
        ro.assert_not_called()

    def test_returns_decoded_text_when_present(self):
        with patch.object(
            runner.reactor_storage, "object_exists", return_value=True
        ), patch.object(
            runner.reactor_storage, "read_object", return_value=b"line1\nline2\n"
        ):
            assert runner.read_log("reactor/runs/9.log") == "line1\nline2\n"

    def test_returns_empty_when_storage_raises_filenotfound(self):
        with patch.object(
            runner.reactor_storage, "object_exists", return_value=True
        ), patch.object(
            runner.reactor_storage, "read_object", side_effect=FileNotFoundError()
        ):
            assert runner.read_log("reactor/runs/9.log") == ""

    def test_replaces_invalid_utf8_bytes(self):
        with patch.object(
            runner.reactor_storage, "object_exists", return_value=True
        ), patch.object(
            runner.reactor_storage, "read_object", return_value=b"ok\xff"
        ):
            out = runner.read_log("reactor/runs/9.log")
        assert out.startswith("ok")
        # \xff is not valid UTF-8 — must not raise; replacement char appears.
        assert "�" in out


# ──────────────────────────────────────────────────────────────────────────
# run_script — full lifecycle
# ──────────────────────────────────────────────────────────────────────────


def _make_script(**overrides):
    """Build a stand-in ReactorScript with sensible defaults."""
    s = MagicMock(spec=reactor_models.ReactorScript)
    s.id = 1
    s.user_id = 99
    s.name = "demo"
    s.entrypoint = "handle"
    s.timeout_seconds = 5
    s.max_writes = 10
    s.source_uri = "reactor/scripts/demo.py"
    s.last_run_at = None
    s.last_run_status = None
    s.last_run_id = None
    s.updated_at = None
    for k, v in overrides.items():
        setattr(s, k, v)
    return s


def _make_run(**overrides):
    r = MagicMock(spec=reactor_models.ReactorRun)
    r.id = 7
    r.script_id = 1
    r.status = "queued"
    r.started_at = None
    r.finished_at = None
    r.error = None
    r.log_uri = None
    r.writes_count = 0
    r.triggered_by = {}
    for k, v in overrides.items():
        setattr(r, k, v)
    return r


def _fake_db(*, run, script):
    """Build a MagicMock ``db`` whose ``query(model)`` returns the right row."""
    db = MagicMock()

    def query(model):
        q = MagicMock()
        if model is reactor_models.ReactorRun:
            q.filter.return_value.first.return_value = run
        elif model is reactor_models.ReactorScript:
            q.filter.return_value.first.return_value = script
        else:
            q.filter.return_value.first.return_value = None
        return q

    db.query.side_effect = query
    return db


@contextmanager
def _patched_storage(source: str, captured_writes: dict | None = None):
    """Patch reactor_storage so reads return ``source`` and writes are captured."""
    captured = captured_writes if captured_writes is not None else {}

    def _write(key, body):
        captured[key] = body

    with patch.object(
        runner.reactor_storage, "read_object", return_value=source.encode()
    ), patch.object(
        runner.reactor_storage, "write_object", side_effect=_write
    ):
        yield captured


class TestRunScriptLifecycle:
    def test_returns_silently_when_run_not_found(self):
        db = _fake_db(run=None, script=None)
        with patch.object(runner.reactor_storage, "read_object") as ro:
            runner.run_script(db, 12345)
        ro.assert_not_called()
        db.commit.assert_not_called()

    def test_marks_failed_when_script_missing(self):
        run = _make_run()
        db = _fake_db(run=run, script=None)
        with patch.object(runner.reactor_storage, "read_object") as ro:
            runner.run_script(db, run.id)
        ro.assert_not_called()
        assert run.status == "failed"
        assert run.error == "script not found"
        assert run.finished_at is not None
        db.commit.assert_called_once()

    def test_happy_path_runs_handler_and_records_success(self):
        run = _make_run(triggered_by={"payload": {"hello": "world"}})
        script = _make_script()
        db = _fake_db(run=run, script=script)

        source = (
            "def handle(ctx, payload):\n"
            "    print('payload was', payload)\n"
        )
        with _patched_storage(source) as written:
            runner.run_script(db, run.id)

        assert run.status == "success"
        assert run.error is None
        assert run.started_at is not None
        assert run.finished_at is not None
        assert run.log_uri == f"reactor/runs/{run.id}.log"
        assert run.writes_count == 0  # handler made no writes via ctx

        # Log captured stdout from the handler.
        log_blob = written[run.log_uri].decode()
        assert "=== stdout ===" in log_blob
        assert "payload was {'hello': 'world'}" in log_blob

        # Script bookkeeping mirrors the run.
        assert script.last_run_at == run.finished_at
        assert script.last_run_status == "success"
        assert script.last_run_id == run.id
        assert script.updated_at == run.finished_at

    def test_three_arg_handler_receives_trigger_info(self):
        run = _make_run(
            triggered_by={
                "resource_type": "event",
                "action": "created",
                "payload": {"info": "phish"},
            }
        )
        script = _make_script()
        db = _fake_db(run=run, script=script)

        source = (
            "def handle(ctx, payload, trigger):\n"
            "    print('trigger', trigger)\n"
            "    print('payload', payload)\n"
        )
        with _patched_storage(source) as written:
            runner.run_script(db, run.id)

        assert run.status == "success"
        log_blob = written[run.log_uri].decode()
        assert "trigger {'resource_type': 'event', 'action': 'created'}" in log_blob
        assert "payload {'info': 'phish'}" in log_blob

    def test_legacy_triggered_by_without_payload_key_passes_whole_dict(self):
        # Older runs stored the trigger payload at the top level rather than
        # nested under "payload"; the runner falls back to the whole dict.
        run = _make_run(triggered_by={"info": "phish"})
        script = _make_script()
        db = _fake_db(run=run, script=script)

        source = (
            "def handle(ctx, payload):\n"
            "    print('payload', payload)\n"
        )
        with _patched_storage(source) as written:
            runner.run_script(db, run.id)

        log_blob = written[run.log_uri].decode()
        assert "payload {'info': 'phish'}" in log_blob

    def test_handler_exception_marks_failed_with_type_and_message(self):
        run = _make_run()
        script = _make_script()
        db = _fake_db(run=run, script=script)

        source = (
            "def handle(ctx, payload):\n"
            "    raise ValueError('boom')\n"
        )
        with _patched_storage(source) as written:
            runner.run_script(db, run.id)

        assert run.status == "failed"
        assert run.error == "ValueError: boom"
        log_blob = written[run.log_uri].decode()
        assert "=== error ===" in log_blob
        assert "ValueError: boom" in log_blob
        assert script.last_run_status == "failed"

    def test_missing_entrypoint_marks_failed(self):
        run = _make_run()
        script = _make_script(entrypoint="handle")
        db = _fake_db(run=run, script=script)

        # Source defines no `handle` callable.
        source = "x = 1\n"
        with _patched_storage(source):
            runner.run_script(db, run.id)

        assert run.status == "failed"
        assert "handle" in (run.error or "")
        assert script.last_run_status == "failed"

    def test_timeout_marks_status_timed_out(self):
        run = _make_run()
        script = _make_script(timeout_seconds=1)
        db = _fake_db(run=run, script=script)

        @contextmanager
        def _instant_timeout(seconds):
            raise ScriptTimeout(f"script exceeded {seconds}s")
            yield  # noqa: unreachable, satisfies generator protocol

        source = (
            "def handle(ctx, payload):\n"
            "    pass\n"
        )
        with _patched_storage(source) as written, patch.object(
            runner, "time_limit", _instant_timeout
        ):
            runner.run_script(db, run.id)

        assert run.status == "timed_out"
        assert run.error == "script exceeded 1s"
        log_blob = written[run.log_uri].decode()
        assert "=== error ===" in log_blob
        assert "script exceeded 1s" in log_blob
        assert script.last_run_status == "timed_out"

    def test_writes_count_propagates_from_context(self):
        run = _make_run()
        script = _make_script()
        db = _fake_db(run=run, script=script)

        # Patch ReactorContext so handler.write quota tracking is observable
        # without going through the real repositories.
        fake_ctx = MagicMock()
        fake_ctx._writes_count = 4

        source = (
            "def handle(ctx, payload):\n"
            "    pass\n"
        )
        with _patched_storage(source), patch.object(
            runner, "ReactorContext", return_value=fake_ctx
        ):
            runner.run_script(db, run.id)

        assert run.writes_count == 4

    def test_run_marked_running_before_user_code_executes(self):
        run = _make_run()
        script = _make_script()
        db = _fake_db(run=run, script=script)

        observed_status = []

        source = (
            "def handle(ctx, payload):\n"
            "    pass\n"
        )

        # Inspect the run state right before the handler is dispatched.
        original_call = runner._call_handler

        def _spy(*args, **kwargs):
            observed_status.append(run.status)
            return original_call(*args, **kwargs)

        with _patched_storage(source), patch.object(
            runner, "_call_handler", side_effect=_spy
        ):
            runner.run_script(db, run.id)

        assert observed_status == ["running"]
        assert run.status == "success"  # transitions to terminal at the end
