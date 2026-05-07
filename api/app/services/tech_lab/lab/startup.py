"""Source executed as a kernel's first cell to bind the ``mwlab`` instance.

Interpolated by ``kernel_manager`` with the running user's id and the active
notebook id, so every SDK call carried over IOPub is attributable in the
audit log via ``actor_type=lab_notebook``, ``actor_credential_id=notebook_id``.
"""

STARTUP_TEMPLATE = """\
from mwctipy import MwLab, render
mwlab = MwLab(user_id={user_id}, notebook_id={notebook_id})
"""


def render_startup(user_id: int, notebook_id: int) -> str:
    return STARTUP_TEMPLATE.format(user_id=int(user_id), notebook_id=int(notebook_id))
