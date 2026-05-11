"""Process-local registry of live ipykernels, keyed by ``(user_id, notebook_id)``.

The ``lab-worker`` Celery container runs this with ``--pool=threads`` so all
kernels live in one Python process and any thread can drive any kernel — that's
the whole reason for picking a threadpool over prefork. A registry-wide
``RLock`` serialises map mutations; per-key ``Lock`` instances let two
unrelated notebooks execute cells at the same time without contention.

Idle eviction runs lazily on every ``get_or_start`` call: any kernel whose last
activity is older than ``LAB_KERNEL_IDLE_SECONDS`` is shut down. We don't
spawn a background thread for this — the worker process is already a Celery
worker thread and we want the eviction policy to be deterministic for tests.
"""

from __future__ import annotations

import logging
import os
import shutil
import tempfile
import threading
import time
from dataclasses import dataclass, field
from typing import Optional, Tuple


logger = logging.getLogger(__name__)

KernelKey = Tuple[int, int]  # (user_id, notebook_id)

# Tunable via env so ops can stretch / shrink the idle window without redeploy.
LAB_KERNEL_IDLE_SECONDS = int(os.environ.get("LAB_KERNEL_IDLE_SECONDS", "1800"))


@dataclass
class _Entry:
    manager: "object"  # jupyter_client.KernelManager (typed loosely; optional dep)
    client: "object"   # jupyter_client.BlockingKernelClient
    cwd: str
    last_active: float
    lock: threading.Lock = field(default_factory=threading.Lock)
    started: bool = False


class LabKernelRegistry:
    """Singleton holding the (user_id, notebook_id) → kernel map.

    Tests construct their own registry to avoid touching global state; prod
    code uses ``get_default_registry()``.
    """

    def __init__(self, *, idle_seconds: int = LAB_KERNEL_IDLE_SECONDS):
        self._idle_seconds = idle_seconds
        self._lock = threading.RLock()
        self._kernels: dict[KernelKey, _Entry] = {}

    # ── lookup / lifecycle ─────────────────────────────────────────────────

    def get_or_start(self, key: KernelKey) -> _Entry:
        """Return the entry for ``key``, starting a new kernel if missing.

        Caller is expected to hold ``entry.lock`` while sending an
        ``execute_request`` / draining IOPub, so two cell executions on the
        same kernel never interleave.
        """
        self._evict_idle()
        with self._lock:
            entry = self._kernels.get(key)
            if entry is not None:
                entry.last_active = time.monotonic()
                return entry
            entry = self._spawn(key)
            self._kernels[key] = entry
            return entry

    def shutdown(self, key: KernelKey) -> bool:
        with self._lock:
            entry = self._kernels.pop(key, None)
        if entry is None:
            return False
        self._teardown_entry(entry)
        return True

    def interrupt(self, key: KernelKey) -> bool:
        with self._lock:
            entry = self._kernels.get(key)
        if entry is None:
            return False
        try:
            entry.manager.interrupt_kernel()  # type: ignore[attr-defined]
        except Exception:  # noqa: BLE001
            logger.exception("interrupt failed for %s", key)
            return False
        return True

    def shutdown_all(self) -> None:
        with self._lock:
            entries = list(self._kernels.values())
            self._kernels.clear()
        for e in entries:
            self._teardown_entry(e)

    def is_running(self, key: KernelKey) -> bool:
        with self._lock:
            return key in self._kernels

    def touch(self, key: KernelKey) -> None:
        """Mark a kernel as recently used (called by executor after each cell)."""
        with self._lock:
            entry = self._kernels.get(key)
            if entry is not None:
                entry.last_active = time.monotonic()

    # ── internals ──────────────────────────────────────────────────────────

    def _evict_idle(self) -> None:
        now = time.monotonic()
        cutoff = now - self._idle_seconds
        with self._lock:
            stale = [
                (k, v) for k, v in self._kernels.items() if v.last_active < cutoff
            ]
            for k, _ in stale:
                self._kernels.pop(k, None)
        # Tear down outside the lock — manager.shutdown_kernel() can block on subprocess wait.
        for k, entry in stale:
            logger.info("evicting idle lab kernel %s", k)
            self._teardown_entry(entry)

    def _spawn(self, key: KernelKey) -> _Entry:
        # Local import: jupyter_client is only available inside the lab-worker
        # image. Importing at module top would break the api container.
        from jupyter_client import KernelManager  # type: ignore

        cwd = tempfile.mkdtemp(prefix=f"lab-{key[0]}-{key[1]}-")
        km = KernelManager(kernel_name="python3")
        km.start_kernel(cwd=cwd)
        client = km.client()
        client.start_channels()
        client.wait_for_ready(timeout=30)

        entry = _Entry(
            manager=km,
            client=client,
            cwd=cwd,
            last_active=time.monotonic(),
            started=True,
        )

        # Run the startup snippet so `mwlab` is bound before any user cell.
        from app.services.tech_lab.lab.startup import render_startup

        startup_code = render_startup(user_id=key[0], notebook_id=key[1])
        msg_id = client.execute(startup_code, silent=True, store_history=False)
        # Drain shell reply for startup; surface errors loudly so a silent
        # import failure (e.g. mwctipy not on sys.path) doesn't yield a zombie
        # kernel whose user cells then complain about an unbound ``mwlab``.
        try:
            reply = client.get_shell_msg(timeout=30)
        except Exception:  # noqa: BLE001
            self._teardown_entry(entry)
            raise RuntimeError(
                f"lab kernel startup did not reply within 30s (msg={msg_id})"
            )
        content = (reply or {}).get("content") or {}
        if content.get("status") != "ok":
            ename = content.get("ename", "StartupError")
            evalue = content.get("evalue", "(no message)")
            self._teardown_entry(entry)
            raise RuntimeError(f"lab kernel startup failed: {ename}: {evalue}")
        # Drain the small handful of IOPub status messages emitted during the
        # silent startup so the next user cell's poll doesn't pick them up.
        import time as _time

        deadline = _time.monotonic() + 5
        while True:
            try:
                msg = client.get_iopub_msg(
                    timeout=max(0.05, deadline - _time.monotonic())
                )
            except Exception:  # noqa: BLE001
                break
            parent = msg.get("parent_header") or {}
            if parent.get("msg_id") != msg_id:
                continue
            if (
                msg.get("msg_type") == "status"
                and (msg.get("content") or {}).get("execution_state") == "idle"
            ):
                break
        return entry

    def _teardown_entry(self, entry: _Entry) -> None:
        try:
            entry.client.stop_channels()  # type: ignore[attr-defined]
        except Exception:  # noqa: BLE001
            logger.exception("client.stop_channels failed")
        try:
            entry.manager.shutdown_kernel(now=True)  # type: ignore[attr-defined]
        except Exception:  # noqa: BLE001
            logger.exception("manager.shutdown_kernel failed")
        if entry.cwd:
            shutil.rmtree(entry.cwd, ignore_errors=True)


# ── module-level default registry (used by Celery tasks) ──────────────────


_default_registry: Optional[LabKernelRegistry] = None
_default_registry_lock = threading.Lock()


def get_default_registry() -> LabKernelRegistry:
    global _default_registry
    if _default_registry is None:
        with _default_registry_lock:
            if _default_registry is None:
                _default_registry = LabKernelRegistry()
    return _default_registry
