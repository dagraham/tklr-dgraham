"""Self-contained HTML version of the agenda, for viewing on a phone."""

from __future__ import annotations

import html
import io
import json
import re
from datetime import datetime

from rich.console import Console
from rich.text import Text

# Details lines that are internal bookkeeping rather than reminder content.
_INTERNAL_PREFIXES = ("rruleset:", "id/cr/md:", "instance:")
# An @m value runs to the end of its line; keep the key, hide the value.
_MASK_RE = re.compile(r"(@m\s*(?:\[/[^\]]*\]\s*)?)[^\n]*")

_STYLE = """
body { background:#1e1e1e; color:#ddd; margin:0; padding:12px;
       font:15px/1.4 ui-monospace, Menlo, monospace; }
h1 { font-size:17px; margin:0 0 10px; }
.h { margin:14px 0 4px; }
details { margin:2px 0; }
summary { list-style:none; cursor:pointer; white-space:pre-wrap; }
summary::-webkit-details-marker { display:none; }
.d { white-space:pre-wrap; margin:4px 0 10px 1.5em; padding-left:8px;
     border-left:2px solid #555; }
a { color:#87cefa; }
footer { margin-top:18px; color:#888; font-size:12px; }
"""


def _markup_to_html(markup: str) -> str:
    """Render rich markup to inline-styled HTML spans."""
    console = Console(
        file=io.StringIO(), record=True, width=10_000, color_system="truecolor"
    )
    console.print(Text.from_markup(markup), end="", soft_wrap=True)
    return console.export_html(inline_styles=True, code_format="{code}").strip()


def _record_links(controller, record_id: int) -> list[str]:
    rec = controller.db_manager.get_record_as_dictionary(record_id) or {}
    try:
        tokens = json.loads(rec.get("tokens") or "[]")
    except ValueError:
        return []
    links = []
    for tok in tokens:
        if tok.get("t") == "@" and tok.get("k") == "g":
            target = (tok.get("token") or "")[2:].strip()
            if target:
                links.append(target)
    return links


def _details_html(controller, row: dict) -> str:
    _title, lines, _meta = controller.get_details_for_record(
        row["record_id"],
        row.get("job_id"),
        row.get("datetime_id"),
        row.get("instance_ts"),
    )
    parts = []
    for line in lines:
        if Text.from_markup(line).plain.strip().startswith(_INTERNAL_PREFIXES):
            continue
        line = _MASK_RE.sub(lambda m: m.group(1) + "••••", line)
        parts.append(_markup_to_html(line))
    body = "\n".join(p for p in parts if p.strip()).strip("\n")
    for target in _record_links(controller, row["record_id"]):
        safe = html.escape(target, quote=True)
        body += f'\n<a href="{safe}">{safe}</a>'
    return body


def build_agenda_html(controller, *, now: datetime | None = None) -> str:
    rows = controller.get_agenda(yield_rows=True)
    out = []
    for row in rows:
        text = row.get("text", "")
        if not Text.from_markup(text).plain.strip():
            continue
        line_html = _markup_to_html(text)
        if row.get("record_id") is None:
            out.append(f'<div class="h">{line_html}</div>')
            continue
        try:
            details = _details_html(controller, row)
        except Exception:
            details = ""
        out.append(
            f"<details><summary>{line_html}</summary>"
            f'<div class="d">{details}</div></details>'
        )

    stamp = (now or datetime.now()).strftime("%a %b %-d %Y %H:%M")
    return (
        "<!DOCTYPE html>\n<html><head><meta charset=\"utf-8\">\n"
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        f"<title>Agenda</title><style>{_STYLE}</style></head><body>\n"
        "<h1>Agenda</h1>\n" + "\n".join(out) + f"\n<footer>Updated {stamp}</footer>\n"
        "</body></html>\n"
    )
