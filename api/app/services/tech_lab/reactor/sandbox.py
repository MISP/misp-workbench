"""Helpers for executing user-supplied script bodies.

The real isolation boundary is the dedicated worker container (separate user,
read-only FS, resource limits). The whitelist below shapes the in-process
namespace for clarity, not security — never rely on it as a sandbox.
"""

import builtins
import signal
import threading
from contextlib import contextmanager


# Builtins exposed to user scripts. Kept small to nudge users toward the
# `ctx` SDK for anything stateful.
_ALLOWED_BUILTINS = {
    "abs", "all", "any", "bool", "bytes", "chr", "dict", "divmod", "enumerate",
    "filter", "float", "frozenset", "getattr", "hasattr", "hash", "hex", "int",
    "isinstance", "issubclass", "iter", "len", "list", "map", "max", "min",
    "next", "object", "oct", "ord", "pow", "print", "range", "repr", "reversed",
    "round", "set", "slice", "sorted", "str", "sum", "tuple", "type", "zip",
    "True", "False", "None", "Exception", "ValueError", "TypeError", "KeyError",
    "IndexError", "RuntimeError", "StopIteration",
}


def restricted_builtins() -> dict:
    return {name: getattr(builtins, name) for name in _ALLOWED_BUILTINS if hasattr(builtins, name)}


class ScriptTimeout(Exception):
    pass


@contextmanager
def time_limit(seconds: int):
    """SIGALRM-based wall-clock limit. Only works on the main thread of a process.

    The reactor worker runs each task in a process (Celery prefork), so the
    handler executes on the main thread of its own process. Off the main thread
    (e.g. inside FastAPI's TestClient threadpool) we skip the alarm — the timeout
    is best-effort enforcement, not a security boundary.
    """

    if threading.current_thread() is not threading.main_thread():
        yield
        return

    def _handle(_signum, _frame):
        raise ScriptTimeout(f"script exceeded {seconds}s")

    previous = signal.signal(signal.SIGALRM, _handle)
    signal.alarm(max(1, int(seconds)))
    try:
        yield
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, previous)
