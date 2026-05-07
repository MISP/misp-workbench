"""mwctipy — analyst SDK for misp-workbench notebooks.

Imported into every Tech Lab notebook kernel at startup. The bound instance
``mwlab = MwLab(user_id=..., notebook_id=...)`` carries the running user's
identity for audit purposes.
"""

from mwctipy.client import MwLab  # noqa: F401
from mwctipy import render  # noqa: F401

__all__ = ["MwLab", "render"]
