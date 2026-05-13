"""Tiny HTML renderers for analyst-style summaries.

Returned as raw HTML strings; analysts wrap them in ``IPython.display.HTML``
when they want them rendered, or feed them straight into Markdown cells.
Real visualisation belongs in matplotlib / altair, which analysts can
``import`` themselves.
"""

from __future__ import annotations

import html
from typing import Iterable


def timeline(events: Iterable[dict]) -> str:
    """One-line-per-event ordered list (most recent first by ``date`` if present)."""
    rows = list(events)
    rows.sort(key=lambda e: e.get("date") or "", reverse=True)
    items = []
    for ev in rows:
        info = html.escape(str(ev.get("info", "(no info)")))
        date = html.escape(str(ev.get("date", "")))
        items.append(f"<li><b>{date}</b> — {info}</li>")
    return f"<ul class='mwctipy-timeline'>{''.join(items)}</ul>"


def tag_cloud(items: Iterable[dict]) -> str:
    """Sum tag counts across rows; render as a ``<span>`` cloud sized by frequency."""
    counts: dict[str, int] = {}
    for row in items:
        for t in row.get("tags") or []:
            name = t.get("name") if isinstance(t, dict) else t
            if name:
                counts[name] = counts.get(name, 0) + 1
    if not counts:
        return "<span class='mwctipy-empty'>(no tags)</span>"
    max_n = max(counts.values())
    spans = []
    for name, n in sorted(counts.items(), key=lambda kv: -kv[1]):
        size = 0.8 + 1.2 * (n / max_n)
        safe = html.escape(name)
        spans.append(
            f"<span style='font-size:{size:.2f}em;margin:0 6px'>{safe} ({n})</span>"
        )
    return f"<div class='mwctipy-tag-cloud'>{''.join(spans)}</div>"
