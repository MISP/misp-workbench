"""Source executed as a kernel's first cell to bind the ``mwlab`` instance.

Interpolated by ``kernel_manager`` with the running user's id and the active
notebook id, so every SDK call carried over IOPub is attributable in the
audit log via ``actor_type=lab_notebook``, ``actor_credential_id=notebook_id``.

The ``sys.path`` injection is necessary because the kernel subprocess runs
with cwd set to a per-notebook tempdir; ``app/`` and ``mwctipy/`` live at
``/code/`` (the container's WORKDIR) and aren't installed as wheels, so
without the path tweak ``import mwctipy`` would fail.
"""

import os

STARTUP_TEMPLATE = """\
import sys as _sys
_code_root = {code_root!r}
if _code_root and _code_root not in _sys.path:
    _sys.path.insert(0, _code_root)
del _sys, _code_root

from mwctipy import MwLab, render
mwlab = MwLab(user_id={user_id}, notebook_id={notebook_id})
"""


def render_startup(user_id: int, notebook_id: int) -> str:
    code_root = os.environ.get("LAB_CODE_ROOT", "/code")
    return STARTUP_TEMPLATE.format(
        code_root=code_root,
        user_id=int(user_id),
        notebook_id=int(notebook_id),
    )
