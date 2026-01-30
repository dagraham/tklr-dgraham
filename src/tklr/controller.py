from __future__ import annotations
from packaging.version import parse as parse_version
from importlib.metadata import version
from datetime import datetime, timedelta, date, timezone

import re
import inspect
from typing import List, Tuple, Optional, Dict, Any, Set
import shutil
import calendar
import calendar
import subprocess
import shlex
import textwrap
import sys


import json
from typing import Literal
from .item import Item
from .model import DatabaseManager, UrgencyComputer
from .model import _fmt_naive
from .list_colors import css_named_colors
from .versioning import get_version
from .mask import reveal_mask_tokens
from .query import QueryEngine, QueryError, QueryResponse

from collections import defaultdict, OrderedDict
from dataclasses import dataclass, field
from pathlib import Path
from zoneinfo import ZoneInfo
from dateutil.rrule import rrulestr
from dateutil import tz

# Item prefixes that should be coerced to draft ("?") when importing inbox entries.
INBOX_ITEM_PREFIXES = {"*", "~", "^", "!", "%", "?"}
INBOX_SPLIT_PATTERN = re.compile(r"\n\s*\n")

# import sqlite3
from .shared import (
    TYPE_TO_COLOR,
    log_msg,
    bug_msg,
    _to_local_naive,
    HRS_MINS,
    format_time_range,
    format_timedelta,
    datetime_from_timestamp,
    format_datetime,
    datetime_in_words,
    truncate_string,
    parse,
    fmt_utc_z,
    timedelta_str_to_seconds,
    indx_to_tag,
    format_date_range,
    format_iso_week,
    get_previous_yrwk,
    get_next_yrwk,
    calculate_4_week_start,
    is_all_day_text,
)
from tklr.tklr_env import TklrEnvironment
from tklr.view import ChildBinRow, ReminderRow


VERSION = get_version()

ISO_Z = "%Y%m%dT%H%MZ"

type_color = css_named_colors["goldenrod"]
at_color = css_named_colors["goldenrod"]
am_color = css_named_colors["goldenrod"]
# type_color = css_named_colors["burlywood"]
# at_color = css_named_colors["burlywood"]
# am_color = css_named_colors["burlywood"]
label_color = css_named_colors["lightskyblue"]

# The overall background color of the app is theme-driven (see view_dark.css / view_light.css)
CORNSILK = "#FFF8DC"
DARK_GRAY = "#A9A9A9"
DARK_GREY = "#A9A9A9"  # same as DARK_GRAY
DARK_OLIVEGREEN = "#556B2F"
DARK_ORANGE = "#FF8C00"
DARK_SALMON = "#E9967A"
GOLD = "#FFD700"
GOLDENROD = "#DAA520"
KHAKI = "#F0E68C"
LAWN_GREEN = "#7CFC00"
LEMON_CHIFFON = "#FFFACD"
LIGHT_CORAL = "#F08080"
LIGHT_SKY_BLUE = "#87CEFA"
LIME_GREEN = "#32CD32"
ORANGE_RED = "#FF4500"
PALE_GREEN = "#98FB98"
PEACHPUFF = "#FFDAB9"
SALMON = "#FA8072"
SANDY_BROWN = "#F4A460"
SEA_GREEN = "#2E8B57"
SLATE_GREY = "#708090"
TOMATO = "#FF6347"

# Colors for UI elements
DAY_COLOR = LEMON_CHIFFON
FRAME_COLOR = KHAKI
# HEADER_COLOR = LIGHT_SKY_BLUE
HEADER_COLOR = LEMON_CHIFFON
DIM_COLOR = DARK_GRAY
ALLDAY_COLOR = SANDY_BROWN
EVENT_COLOR = LIME_GREEN
NOTE_COLOR = DARK_SALMON
PASSED_EVENT = DARK_OLIVEGREEN
ACTIVE_EVENT = LAWN_GREEN
TASK_COLOR = LIGHT_SKY_BLUE
AVAILABLE_COLOR = LIGHT_SKY_BLUE
WAITING_COLOR = SLATE_GREY
FINISHED_COLOR = DARK_GREY
GOAL_COLOR = GOLDENROD
CHORE_COLOR = KHAKI
PASTDUE_COLOR = DARK_ORANGE
NOTICE_COLOR = GOLD
DRAFT_COLOR = ORANGE_RED
TODAY_COLOR = TOMATO
SELECTED_BACKGROUND = "#566573"
MATCH_COLOR = TOMATO
TITLE_COLOR = CORNSILK
BUSY_COLOR = "#9acd32"
BUSY_COLOR = "#adff2f"
CONF_COLOR = TOMATO
BUSY_FRAME_COLOR = "#5d5d5d"

# This one appears to be a Rich/Textual style string
SELECTED_COLOR = "bold yellow"
# SLOT_HOURS = [0, 4, 8, 12, 16, 20, 24]
SLOT_HOURS = [0, 6, 12, 18, 24]
SLOT_MINUTES = [x * 60 for x in SLOT_HOURS]
BUSY = "■"  # U+25A0 this will be busy_bar busy and conflict character
FREE = "□"  # U+25A1 this will be busy_bar free character
ADAY = "━"  # U+2501 for all day events ━
NOTICE = "⋙"

SELECTED_COLOR = "yellow"
# SELECTED_COLOR = "bold yellow"

HEADER_COLOR = LEMON_CHIFFON
# HEADER_STYLE = f"bold {LEMON_CHIFFON}"
HEADER_STYLE = f"{LEMON_CHIFFON}"
FIELD_COLOR = LIGHT_SKY_BLUE

ONEDAY = timedelta(days=1)

# TYPE_TO_COLOR = {
#     "*": EVENT_COLOR,  # event
#     "~": AVAILABLE_COLOR,  # available task
#     "x": FINISHED_COLOR,  # finished task
#     "^": AVAILABLE_COLOR,  # available task
#     "+": WAITING_COLOR,  # waiting task
#     "%": NOTE_COLOR,  # note
#     "<": PASTDUE_COLOR,  # past due task
#     ">": NOTICE_COLOR,  # begin
#     "!": GOAL_COLOR,  # draft
#     "?": DRAFT_COLOR,  # draft
# }
#


def _ensure_tokens_list(value):
    """Return a list[dict] for tokens whether DB returned JSON str or already-parsed list."""
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        return list(value)
    if isinstance(value, (bytes, bytearray)):
        value = value.decode("utf-8")
    if isinstance(value, str):
        return json.loads(value)
    # last resort: try to coerce
    return list(value)


def format_tokens(
    tokens,
    width,
    highlight: bool = True,
    *,
    wrap_descriptions: bool = True,
):
    if isinstance(tokens, str):
        try:
            tokens = json.loads(tokens)
        except Exception:
            pass

    output_lines = []
    current_line = ""

    def strip_rich(s: str) -> str:
        return re.sub(r"\[[^\]]+\]", "", s)

    def apply_highlight(line: str) -> str:
        if not highlight:
            return strip_rich(line)
        color = {"@": at_color, "&": am_color}
        return re.sub(
            r"(^|(?<=\s))([@&]\S\s)",
            lambda m: m.group(1)
            + f"[{color[m.group(2)[0]]}]{m.group(2)}[/{color[m.group(2)[0]]}]",
            line,
        )

    for t in tokens:
        token_text = (t.get("token") or "").rstrip("\n")
        ttype = t.get("t")
        k = t.get("k") or t.get("key")

        # ✅ PRESERVE itemtype char as the start of the line
        if ttype == "itemtype":
            if current_line:
                output_lines.append(current_line)
            current_line = token_text  # start new line with '*', '-', '~', '^', etc.
            continue

        # @d blocks: own paragraph, preserve newlines/indent
        # if ttype == "@" and k == "d":
        if ttype == "@" and k in ["d", "m"]:
            if current_line:
                output_lines.append(current_line)
                current_line = ""
            if not wrap_descriptions:
                output_lines.append(token_text)
                continue
            for line in token_text.splitlines():
                indent = len(line) - len(line.lstrip(" "))
                wrapped = textwrap.wrap(
                    line, width=width, subsequent_indent=" " * indent
                ) or [""]
                output_lines.extend(wrapped)
            continue

        # optional special-case for @~
        if ttype == "@" and k == "~":
            # if current_line:
            output_lines.append(current_line)
            current_line = " "
            # if token_text:
            #     output_lines.append(token_text)
            # continu        # normal tokens
        if not token_text:
            continue
        if current_line and len(current_line) + 1 + len(token_text) > width:
            output_lines.append(current_line)
            current_line = token_text
        else:
            current_line = current_line + " " + token_text

    if current_line:
        output_lines.append(current_line)

    return "\n".join(apply_highlight(line) for line in output_lines)


def wrap_preserve_newlines(text, width=70, initial_indent="", subsequent_indent=""):
    lines = text.splitlines()  # preserve \n boundaries
    wrapped_lines = [
        subline
        for line in lines
        for subline in textwrap.wrap(
            line,
            width=width,
            initial_indent=initial_indent,
            subsequent_indent=subsequent_indent,
        )
        or [""]
    ]
    return wrapped_lines


def format_rruleset_for_details(
    rruleset: str, width: int, subsequent_indent: int = 11
) -> str:
    """
    Wrap RDATE/EXDATE value lists on commas to fit `width`.
    Continuation lines are indented by the length of header.
    When a wrap occurs, the comma stays at the end of the line.
    """

    def wrap_value_line(header: str, values_csv: str) -> list[str]:
        # indent = " " * (len(header) + 2)  # for colon and space
        indent = " " * 2
        tokens = [t.strip() for t in values_csv.split(",") if t.strip()]
        out_lines: list[str] = []
        cur = header  # start with e.g. "RDATE:"

        for i, tok in enumerate(tokens):
            sep = "," if i < len(tokens) - 1 else ""  # last token → no comma
            candidate = f"{cur}{tok}{sep}"

            if len(candidate) <= width:
                cur = candidate + " "
            else:
                # flush current line before adding token
                out_lines.append(cur.rstrip())
                cur = f"{indent}{tok}{sep} "
        if cur.strip():
            out_lines.append(cur.rstrip())
        return out_lines

    out: list[str] = []
    for line in (rruleset or "").splitlines():
        if ":" in line:
            prop, value = line.split(":", 1)
            prop_up = prop.upper()
            if prop_up.startswith("RDATE") or prop_up.startswith("EXDATE"):
                out.extend(wrap_value_line(f"{prop_up}:", value.strip()))
                continue
        out.append(line)
    # prepend = " " * (len("rruleset: ")) + "\n"
    return "\n          ".join(out)


def format_hours_mins(dt: datetime, mode: Literal["24", "12"]) -> str:
    """
    Format a datetime object as hours and minutes.
    """
    if dt.minute > 0:
        fmt = {
            "24": "%H:%M",
            "12": "%-I:%M%p",
        }
    else:
        fmt = {
            "24": "%H:%M",
            "12": "%-I%p",
        }

    if mode == "12":
        return dt.strftime(fmt[mode]).lower().rstrip("m")
    return f"{dt.strftime(fmt[mode])}"


def ordinal(n: int) -> str:
    """Return ordinal representation of an integer (1 -> 1st)."""
    if 10 <= n % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def set_anniversary(subject: str, start: date, instance: date, freq: str) -> str:
    """
    Replace {XXX} in subject with ordinal count of periods since start.
    freq ∈ {'y','m','w','d'}.
    """
    has_xxx = "{XXX}" in subject
    if not has_xxx:
        return subject

    if isinstance(start, datetime):
        start = start.date()
    if isinstance(instance, datetime):
        instance = instance.date()

    diff = instance - start
    if freq == "y":
        n = instance.year - start.year
    elif freq == "m":
        n = (instance.year - start.year) * 12 + (instance.month - start.month)
    elif freq == "w":
        n = diff.days // 7
    else:  # 'd'
        n = diff.days

    # n = max(n, 0) + 1  # treat first instance as "1st"
    n = max(n, 0)  # treat first instance as "1st"

    new_subject = subject.replace("{XXX}", ordinal(n))
    # log_msg(f"{subject = }, {new_subject = }")
    return new_subject


# A page is (rows, tag_map)
# rows: list[str] ready to render (header + content)
# tag_map: { 'a': ('bin', bin_id) | ('reminder', (record_id, job_id)) }
Page = Tuple[List[str], Dict[str, Tuple[str, object]]]


def page_tagger(
    items: List[dict],
    page_size: int = 26,
    *,
    dim_style: str = "dim",
) -> List[Tuple[List[str], Dict[str, Tuple[int, int | None, int | None]]]]:
    """
    Split 'items' into pages. Each item is a dict:
        { "record_id": int | None, "job_id": int | None, "text": str, ... }

    Returns a list of pages. Each page is a tuple:
        (
            page_rows: list[str],
            page_tag_map: dict[str -> (record_id, job_id|None, datetime_id|None)]
        )

    Rules:
      - Only record rows (record_id != None) receive single-letter tags 'a'..'z'.
      - Exactly `page_size` records are tagged per page (except the last page).
      - Headers (record_id is None) are kept in order.
      - If a header's block of records spans pages, the header is duplicated at the
        start of the next page with " (continued)" appended.
    """
    pages: List[Tuple[List[str], Dict[str, Tuple[int, int | None, int | None]]]] = []

    page_rows: List[str] = []
    tag_map: Dict[str, Tuple[int, int | None, int | None]] = {}
    tag_counter = 0  # number of record-tags on current page
    last_header_text = None  # text of the most recent header seen (if any)

    def finalize_page(new_page_rows=None):
        """Close out the current page and start a fresh one optionally seeded with
        new_page_rows (e.g., duplicated header)."""
        nonlocal page_rows, tag_map, tag_counter
        pages.append((page_rows, tag_map))
        page_rows = new_page_rows[:] if new_page_rows else []
        tag_map = {}
        tag_counter = 0

    for item in items:
        if not isinstance(item, dict):
            continue

        # header row
        if item.get("record_id") is None:
            hdr_text = item.get("text", "")
            last_header_text = hdr_text
            page_rows.append(hdr_text)
            # headers do not affect tag_counter
            continue

        # record row (taggable)
        if tag_counter >= page_size:
            # If we have a last_header_text, duplicate it at top of next page with continued.
            if last_header_text:
                continued_header = f"{last_header_text} (continued)"
                finalize_page(new_page_rows=[continued_header])
            else:
                finalize_page()

        tag = chr(ord("a") + tag_counter)

        # NEW: include datetime_id (or None) in the tag map
        record_id = item["record_id"]
        job_id = item.get("job_id", None)
        datetime_id = item.get("datetime_id", None)
        instance_ts = item.get("instance_ts", None)

        tag_map[tag] = (record_id, job_id, datetime_id, instance_ts)

        # Display text unchanged
        page_rows.append(f" [{dim_style}]{tag}[/{dim_style}]  {item.get('text', '')}")
        tag_counter += 1

    if page_rows or tag_map:
        pages.append((page_rows, tag_map))

    return pages


@dataclass(frozen=True)
class _BackupInfo:
    path: Path
    day: date
    mtime: float


_BACKUP_RE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})\.db$")


class Controller:
    """
    Coordinates CLI/UI actions: loads reminders from ``DatabaseManager``,
    builds the paginated textual views, and applies edits coming from the
    command handler.  The class intentionally centralizes formatting helpers
    (tag generation, agenda pagination, etc.) so both the CLI and Textual UI
    share the same behavior.
    """

    def __init__(
        self,
        database_path: str,
        env: TklrEnvironment,
        reset: bool = False,
        *,
        auto_populate: bool = True,
    ):
        # Initialize the database manager
        self.db_manager = DatabaseManager(
            database_path,
            env,
            reset=reset,
            auto_populate=auto_populate,
        )

        self.tag_to_id = {}  # Maps tag numbers to event IDs
        self.list_tag_to_id: dict[str, dict[str, object]] = {}

        self.yrwk_to_pages = {}  # Maps (iso_year, iso_week) to week description
        self.rownum_to_yrwk = {}  # Maps row numbers to (iso_year, iso_week)
        self.start_date = calculate_4_week_start()
        self.selected_week = tuple(datetime.now().isocalendar()[:2])
        self.env = env
        self.mask_secret = getattr(self.env.config, "secret", "") if self.env else ""
        self.AMPM = env.config.ui.ampm
        self.agenda_days = 3
        self._last_details_meta = None
        # self.afill_by_view: dict[str, int] = {}  # e.g. {"events": 1, "tasks": 2}
        # self.afill_by_week: dict[Tuple[int, int], int] = {}

        for view in ["next", "last", "find", "events", "tasks", "alerts", "query"]:
            self.list_tag_to_id.setdefault(view, {})
        self.week_tag_to_id: dict[Tuple[int, int], dict[str, object]] = {}
        self.width = shutil.get_terminal_size()[0] - 2
        # self.afill = 1
        self._agenda_dirty = False
        self.ampm = False
        self.timefmt = "%H:%M"
        self.dayfirst = False
        self.yearfirst = True
        self.datefmt = "%Y-%m-%d"
        if self.env:
            self.ampm = self.env.config.ui.ampm
            self.timefmt = "%-I:%M%p" if self.ampm else "%H:%M"
            self.dayfirst = self.env.config.ui.dayfirst
            self.yearfirst = self.env.config.ui.yearfirst
            self.history_weight = self.env.config.ui.history_weight
            self.agenda_days = max(1, self.env.config.ui.agenda_days)
            _yr = "%Y"
            _dm = "%d-%m" if self.dayfirst else "%m-%d"
            self.datefmt = f"{_yr}-{_dm}" if self.yearfirst else f"{_dm}-{_yr}"
            self.current_command = (self.env.config.ui.current_command or "").strip()
        else:
            self.current_command = ""

        self.datetimefmt = f"{self.datefmt} {self.timefmt}"
        self.query_engine = QueryEngine()
        ui = getattr(self.env.config, "ui", None) if self.env else None
        self.ui_theme = getattr(ui, "theme", "dark") if ui else "dark"
        self.dim_style = "dim" if self.ui_theme == "dark" else "#4a4a4a"
        self._apply_theme_colors()

    def fmt_user(self, dt: date | datetime) -> str:
        """
        User friendly formatting for dates and datetimes using env settings
        for ampm, yearfirst, dayfirst and two_digit year.
        """
        # Simple user-facing formatter; tweak to match your prefs
        if isinstance(dt, datetime):
            d = dt
            if d.tzinfo == tz.UTC and not getattr(self, "final", False):
                d = d.astimezone()
            return d.strftime(self.datetimefmt)
        if isinstance(dt, date):
            return dt.strftime(self.datefmt)
        raise ValueError(f"Error: {dt} must either be a date or datetime")

    def _paginate(
        self, rows: List[dict], page_size: int = 26
    ) -> List[Tuple[List[str], Dict[str, Tuple[int, int | None, int | None]]]]:
        return page_tagger(rows, page_size=page_size, dim_style=self.dim_style)

    def _apply_theme_colors(self) -> None:
        global label_color, type_color, HEADER_COLOR, at_color, am_color
        if self.ui_theme == "light":
            # Use a warm accent that's still readable on light backgrounds.
            accent = css_named_colors.get("darkgoldenrod", "#b8860b")
            label_color = accent
            type_color = accent
            HEADER_COLOR = "#1f4b7a"
            at_color = accent
            am_color = accent
        else:
            label_color = css_named_colors["lightskyblue"]
            type_color = css_named_colors["goldenrod"]
            HEADER_COLOR = LEMON_CHIFFON
            at_color = css_named_colors["goldenrod"]
            am_color = css_named_colors["goldenrod"]

    @property
    def root_id(self) -> int:
        """Return the id of the root bin, creating it if necessary."""
        self.db_manager.ensure_system_bins()
        self.db_manager.cursor.execute("SELECT id FROM Bins WHERE name = 'root'")
        row = self.db_manager.cursor.fetchone()
        if not row:
            raise RuntimeError(
                "Root bin not found — database not initialized correctly."
            )
        return row[0]

    def format_datetime(self, fmt_dt: str) -> str:
        return format_datetime(fmt_dt, self.AMPM)

    def datetime_in_words(self, fmt_dt: str) -> str:
        return datetime_in_words(fmt_dt, self.AMPM)

    def _build_current_command_args(self) -> list[str] | None:
        cmd = (self.current_command or "").strip()
        raw = False
        if cmd.startswith("!"):
            raw = True
            cmd = cmd[1:].lstrip()
        if not cmd:
            return None
        home = (
            str(self.env.home)
            if self.env and getattr(self.env, "home", None)
            else str(Path.home() / ".config" / "tklr")
        )
        try:
            parts = shlex.split(cmd)
        except ValueError as exc:
            log_msg(f"Invalid current_command '{cmd}': {exc}")
            return None
        if raw:
            log_msg(f"Built raw current_command args: {parts}")
            return parts
        log_msg(f"Built current_command args: {parts}")
        return [sys.executable, "-m", "tklr.cli.main", "--home", home, *parts]

    def consume_after_save_command(self) -> tuple[list[str], str] | None:
        if not self.current_command:
            return None
        if not getattr(self.db_manager, "after_save_needed", False):
            return None
        args = self._build_current_command_args()
        if not args:
            return None
        self.db_manager.after_save_needed = False
        return args, self.current_command

    def make_item(self, entry_str: str, final: bool = False) -> "Item":
        return Item(self.env, entry_str, final=final)

    def add_item(self, item: Item) -> int:
        record_id = self.db_manager.add_item(item)

        if item.completions:
            self.db_manager.add_completion(record_id, item.completions)

        return record_id

    # ── Inbox processing -------------------------------------------------
    def _inbox_path(self) -> Path:
        path = self.env.home / "inbox.txt"
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass
        if not path.exists():
            try:
                path.touch()
            except Exception:
                pass
        return path

    def _normalize_inbox_entry(self, entry: str) -> str:
        text = entry.strip()
        if not text:
            return ""
        leading = text.lstrip()
        if not leading:
            return ""
        if leading[0] in INBOX_ITEM_PREFIXES:
            body = leading[1:].lstrip()
        else:
            body = leading
        if not body:
            return ""
        return f"? {body}"

    def _ingest_inbox_entry(self, entry: str) -> tuple[bool, str | None]:
        try:
            item = Item(env=self.env, raw=entry, final=True)
        except Exception as exc:
            return False, f"Parse failed: {exc}"
        if not getattr(item, "parse_ok", False) or not getattr(item, "itemtype", ""):
            return False, f"Invalid entry: {entry}"
        try:
            self.db_manager.add_item(item)
        except Exception as exc:
            return False, f"Database error: {exc}"
        return True, None

    def sync_inbox(self) -> tuple[int, list[str]]:
        """
        Import draft reminders from inbox.txt.

        Returns:
            (added_count, error_messages)
        """
        path = self._inbox_path()
        try:
            size = path.stat().st_size
        except FileNotFoundError:
            return 0, []
        except OSError as exc:
            return 0, [f"Unable to read inbox: {exc}"]

        if size == 0:
            return 0, []

        try:
            raw = path.read_text(encoding="utf-8")
        except OSError as exc:
            return 0, [f"Unable to read inbox: {exc}"]

        chunks = [
            chunk.strip()
            for chunk in INBOX_SPLIT_PATTERN.split(raw.strip())
            if chunk.strip()
        ]
        if not chunks:
            try:
                path.write_text("", encoding="utf-8")
            except OSError:
                pass
            return 0, []

        added = 0
        errors: list[str] = []
        leftovers: list[str] = []

        for chunk in chunks:
            normalized = self._normalize_inbox_entry(chunk)
            if not normalized:
                continue
            ok, msg = self._ingest_inbox_entry(normalized)
            if ok:
                added += 1
            else:
                errors.append(msg or "Unknown inbox error.")
                leftovers.append(chunk)

        if added:
            try:
                self.db_manager.populate_dependent_tables()
            except Exception as exc:
                errors.append(f"Failed to refresh derived tables: {exc}")
            self.db_manager.after_save_needed = True

        remaining = "\n\n".join(leftovers).strip() if leftovers else ""
        try:
            path.write_text(
                (remaining + "\n") if remaining else "",
                encoding="utf-8",
            )
        except OSError as exc:
            errors.append(f"Failed to update inbox file: {exc}")

        log_msg(
            f"Inbox sync: added {added} draft{'s' if added != 1 else ''}, "
            f"{len(errors)} warning{'s' if len(errors) != 1 else ''}."
        )
        return added, errors

    def apply_textual_edit(
        self,
        record_id: int,
        edit_fn: Callable[[str], str],
    ) -> bool:
        """
        Load the entry text for record_id, apply edit_fn(text) -> new_text,
        reparse/finalize, and save back to the same record.

        Returns True on success, False if parsing/finalizing fails.
        """
        # 1) Get current entry text for the whole record
        raw = self.get_entry_from_record(record_id)
        if not raw:
            return False

        new_raw = edit_fn(raw)
        if not new_raw or new_raw.strip() == raw.strip():
            # Nothing changed; treat as no-op
            return False

        from tklr.item import Item  # or your actual import

        # 2) Parse the entry (Item.__init__ already parses `new_raw`)
        item = Item(new_raw, controller=self)
        if not getattr(item, "parse_ok", False):
            return False
        item.final = True

        # 3) Finalize (jobs, rrules, etc.)
        item.finalize_record()

        if not getattr(item, "parse_ok", False):
            return False

        # 4) Save back into the same record (and regen DateTimes, Alerts, etc.)
        self.db_manager.save_record(item, record_id=record_id)
        # 🔁 NEW: record completion if one was produced
        # completion = getattr(item, "completions", None)
        # if completion:
        #     self.db_manager.add_completion(record_id, completion)
        if item.completions:
            self.db_manager.add_completion(record_id, item.completions)

        return True

    def new_day(self) -> None:
        """Set after_save_needed flag."""
        self.db_manager.after_save_needed = True

    def _instance_to_rdate_key(self, instance) -> str:
        """
        Convert an instance (string or datetime) into the canonical UTC-Z key
        used in @+ / @- tokens and RDATE/EXDATE, e.g. '20251119T133000Z'.
        """
        # If you already have a datetime, use it; otherwise parse your TEXT form.
        if isinstance(instance, datetime):
            dt = instance
        else:
            # Your existing helper that knows how to parse DateTimes table TEXT
            dt = parse(instance)

        # Make sure it’s timezone-aware; assume local zone if naive.
        if dt.tzinfo is None:
            dt = dt.astimezone()

        # dt_utc = dt.astimezone(tz.UTC)
        # return dt_utc.strftime("%Y%m%dT%H%MZ")
        return fmt_utc_z(dt)

    def apply_token_edit(
        self,
        record_id: int,
        edit_tokens_fn: Callable[[list[dict]], bool],
    ) -> bool:
        """
        Load tokens from Records.tokens for `record_id`, let `edit_tokens_fn`
        mutate them in place, then rebuild the entry string, re-parse/finalize
        via Item, and save back to the same record.

        Returns True if a change was applied and saved, False otherwise.
        """
        rec = self.db_manager.get_record_as_dictionary(record_id)
        if not rec:
            return False

        tokens_json = rec.get("tokens") or "[]"
        try:
            tokens: list[dict] = json.loads(tokens_json)
        except Exception as e:
            log_msg(f"apply_token_edit: bad tokens JSON for {record_id=}: {e}")
            return False
        tokens = reveal_mask_tokens(tokens, self.mask_secret)

        # Let the caller mutate `tokens`; it should return True iff something changed.
        changed = edit_tokens_fn(tokens)
        if not changed:
            return False

        # Rebuild entry text from tokens.
        entry = " ".join(t.get("token", "").strip() for t in tokens if t.get("token"))
        if not entry.strip():
            # Don’t blow away the record with an empty line by accident.
            return False

        # Re-parse + finalize using Item so rruleset / jobs / flags / etc. stay consistent.
        item = Item(entry, controller=self)
        item.final = True
        item.parse_input(entry)
        if not getattr(item, "parse_ok", False):
            log_msg(f"apply_token_edit: parse failed for {record_id=}")
            return False

        item.finalize_record()
        if not getattr(item, "parse_ok", False):
            log_msg(f"apply_token_edit: finalize failed for {record_id=}")
            return False

        # This will also rebuild the tokens column from the new Item state.
        self.db_manager.save_record(item, record_id=record_id)

        # 🔁 NEW: record completion if one was produced
        completion = getattr(item, "completion", None)
        if completion:
            self.db_manager.add_completion(record_id, completion)

        return True

    def _dt_local_naive(self, dt: datetime) -> datetime:
        """Ensure a local-naive datetime for comparison."""
        if dt.tzinfo is None:
            return dt
        return dt.astimezone(tz.tzlocal()).replace(tzinfo=None)

    def _instance_local_from_text(self, text: str) -> datetime:
        """
        Convert a DateTimes TEXT (like 'YYYYMMDD', 'YYYYMMDDTHHMMSS', etc.)
        into a local-naive datetime using your existing parse helper.
        """
        dt = parse(text)  # you already have this
        return self._dt_local_naive(dt)

    def _is_s_plus_no_r(self, tokens: list[dict]) -> bool:
        has_s = any(t.get("t") == "@" and t.get("k") == "s" for t in tokens)
        has_plus = any(t.get("t") == "@" and t.get("k") == "+" for t in tokens)
        has_r = any(t.get("t") == "@" and t.get("k") == "r" for t in tokens)
        return has_s and has_plus and not has_r

    def _adjust_s_plus_from_rruleset(
        self,
        tokens: list[dict],
        rruleset: str,
        instance_text: str,
        mode: str,  # "one" or "this_and_future"
    ) -> bool:
        """
        Special-case handler for the pattern: @s + @+ but no @r.

        - rruleset: the record's rruleset string (RDATE-only in this pattern)
        - instance_text: the DateTimes.start_datetime TEXT of the chosen instance
        - mode:
            "one"             -> delete just this instance
            "this_and_future" -> delete this and all subsequent instances

        Returns True if tokens were modified.
        """
        if not rruleset:
            return False

        try:
            rule = rrulestr(rruleset)
        except Exception:
            return False

        occs = list(rule)
        if not occs:
            return False

        # Canonical local-naive for all instances
        from dateutil import tz

        def to_local_naive(dt: datetime) -> datetime:
            if dt.tzinfo is None:
                return dt
            return dt.astimezone(tz.tzlocal()).replace(tzinfo=None)

        instances_local = [to_local_naive(d) for d in occs]

        inst_local = self._instance_local_from_text(instance_text)

        if mode == "one":
            survivors = [d for d in instances_local if d != inst_local]
        elif mode == "this_and_future":
            survivors = [d for d in instances_local if d < inst_local]
        else:
            return False

        # If nothing left, clear @s/@+ schedule from tokens
        if not survivors:
            tokens[:] = [
                t
                for t in tokens
                if not (t.get("t") == "@" and t.get("k") in {"s", "+"})
            ]
            return True

        survivors.sort()
        new_s = survivors[0]
        plus_list = survivors[1:]

        # Drop existing @s/@+ tokens
        base = [
            t for t in tokens if not (t.get("t") == "@" and t.get("k") in {"s", "+"})
        ]

        # New @s
        base.append(
            {
                "token": f"@s {self.fmt_user(new_s)}",
                "t": "@",
                "k": "s",
            }
        )

        # New @+ if extras exist
        if plus_list:
            plus_str = ", ".join(self.fmt_user(d) for d in plus_list)
            base.append(
                {
                    "token": f"@+ {plus_str}",
                    "t": "@",
                    "k": "+",
                }
            )

        tokens[:] = base
        return True

    def _instance_is_from_rdate(self, rruleset_str: str, instance_dt: datetime) -> bool:
        """
        Check if a given instance datetime comes from an RDATE in the rruleset.

        Args:
            rruleset_str: The rruleset string from the database
            instance_dt: The instance datetime (already parsed, in UTC if aware)

        Returns:
            True if the instance is from an RDATE, False if from RRULE
        """
        if not rruleset_str:
            return False

        # Parse rruleset to extract RDATEs
        rdates = []
        for line in rruleset_str.splitlines():
            line = line.strip()
            if line.startswith("RDATE"):
                # Extract datetime values from RDATE line
                # Format: RDATE:20251106T1900Z or RDATE:20251106T1900Z,20251113T0200Z
                if ":" in line:
                    dates_part = line.split(":", 1)[1]
                    # Split by comma for multiple dates
                    for dt_str in dates_part.split(","):
                        dt_str = dt_str.strip()
                        if dt_str:
                            try:
                                # Parse the UTC datetime
                                if dt_str.endswith("Z"):
                                    # Aware UTC: YYYYMMDDTHHMMZ
                                    dt = datetime.strptime(dt_str[:-1], "%Y%m%dT%H%M")
                                    dt = dt.replace(tzinfo=timezone.utc)
                                elif "T" in dt_str:
                                    # Naive datetime: YYYYMMDDTHHMM
                                    dt = datetime.strptime(dt_str, "%Y%m%dT%H%M")
                                else:
                                    # Date only: YYYYMMDD
                                    dt = datetime.strptime(dt_str, "%Y%m%d")
                                rdates.append(dt)
                            except Exception:
                                continue

        # Ensure we are working with a datetime (dates can surface from all-day entries)
        if isinstance(instance_dt, date) and not isinstance(instance_dt, datetime):
            instance_dt = datetime.combine(instance_dt, datetime.min.time())

        # Convert instance_dt to UTC if aware, or leave naive
        if instance_dt.tzinfo is not None:
            instance_utc = instance_dt.astimezone(timezone.utc).replace(tzinfo=None)
        else:
            instance_utc = instance_dt.replace(tzinfo=None)

        # Check if instance matches any RDATE (compare without timezone for simplicity)
        for rdate in rdates:
            rdate_naive = rdate.replace(tzinfo=None) if rdate.tzinfo else rdate
            # Compare with minute precision (ignore seconds)
            if (
                instance_utc.year == rdate_naive.year
                and instance_utc.month == rdate_naive.month
                and instance_utc.day == rdate_naive.day
                and instance_utc.hour == rdate_naive.hour
                and instance_utc.minute == rdate_naive.minute
            ):
                return True

        return False

    def _advance_s_to_next_rrule_instance(
        self, record_id: int, second_instance_text: str
    ) -> bool:
        """
        Update @s to point to the second instance (advancing past the first RRULE instance).

        Args:
            record_id: The record ID
            second_instance_text: The compact local-naive datetime string of the second instance

        Returns:
            True if successful, False otherwise
        """
        try:
            # Parse the second instance
            second_dt = parse(second_instance_text)

            # Convert to local naive for user display
            from dateutil import tz

            if second_dt.tzinfo is not None:
                second_local = second_dt.astimezone(tz.tzlocal()).replace(tzinfo=None)
            else:
                second_local = second_dt

            # Format for user
            new_s_stamp = self.fmt_user(second_local)

            def edit_tokens(tokens: list[dict]) -> bool:
                # Find and update @s token
                for tok in tokens:
                    if tok.get("t") == "@" and tok.get("k") == "s":
                        tok["token"] = f"@s {new_s_stamp}"
                        return True
                return False

            return self.apply_token_edit(record_id, edit_tokens)

        except Exception as e:
            log_msg(f"Error advancing @s: {e}")
            return False

    def _instance_to_rdate_key(self, instance_text: str) -> str:
        """
        Normalize a DateTimes TEXT value into the key format used in RDATE/EXDATE.

        - Date-only -> 'YYYYMMDD'
        - Datetime  -> 'YYYYMMDDTHHMM'  (local-naive, no 'Z')
        """
        s = (instance_text or "").strip()
        if not s:
            raise ValueError("empty instance_text")

        # Fast path: already compact date-only 'YYYYMMDD'
        if len(s) == 8 and s.isdigit():
            return s

        # Use your custom parse() helper (respects yearfirst/dayfirst)
        dt = parse(s)  # from your helpers module

        if isinstance(dt, date) and not isinstance(dt, datetime):
            # Pure date -> 'YYYYMMDD'
            return dt.strftime("%Y%m%d")

        if isinstance(dt, datetime):
            # Drop seconds if present, match your RDATE minute granularity
            return dt.strftime("%Y%m%dT%H%M")

        # Fallback (shouldn't normally happen)
        raise ValueError(f"Cannot normalize instance_text {instance_text!r}")

    def _remove_instance_from_plus_tokens(
        self, tokens: list[dict], instance_text: str
    ) -> bool:
        """
        Remove the given instance from any @+ tokens by matching the UTC-Z key.
        Returns True if something was removed.
        """
        target = self._instance_to_rdate_key(instance_text)

        removed = False
        new_tokens: list[dict] = []

        for tok in tokens:
            if tok.get("t") == "@" and tok.get("k") == "+":
                raw = tok.get("token", "")
                body = raw[2:].strip() if raw.startswith("@+") else raw.strip()
                parts = [p.strip() for p in body.split(",") if p.strip()]
                if not parts:
                    continue

                filtered = [p for p in parts if p != target]
                if len(filtered) != len(parts):
                    removed = True

                if filtered:
                    new_tok = dict(tok)
                    new_tok["token"] = "@+ " + ", ".join(filtered)
                    new_tokens.append(new_tok)
                else:
                    # @+ now empty → drop the token entirely
                    continue
            else:
                new_tokens.append(tok)

        tokens[:] = new_tokens
        return removed

    def _add_finish_to_job(self, record_id: int, job_id: int, stamp: str) -> bool:
        """
        Insert or update an &f token for the given job_id on a project record.

        - job_id is 1-based index of @~ tokens in the token list.
        - We locate the N-th @~ token, then:
          * if that job already has an &f token in its &-cluster, we replace it
          * otherwise we append a new &f <stamp> at the end of that cluster

        Returns True if any change was made; False if job_id not found.
        """

        def edit_tokens(tokens: List[Dict]) -> bool:
            job_index = 0

            i = 0
            while i < len(tokens):
                tok = tokens[i]

                # Look for @~ job tokens
                if tok.get("t") == "@" and tok.get("k") == "~":
                    job_index += 1

                    if job_index == job_id:
                        # We are at the job_id-th job's @~ token.
                        # Walk forward through its &-cluster.
                        j = i + 1
                        f_index = None

                        while j < len(tokens) and tokens[j].get("t") == "&":
                            if tokens[j].get("k") == "f":
                                f_index = j
                            j += 1

                        if f_index is not None:
                            # Update existing &f
                            tokens[f_index]["token"] = f"&f {stamp}"
                        else:
                            # Insert new &f at the end of the job's &-cluster
                            tokens.insert(
                                j,
                                {
                                    "token": f"&f {stamp}",
                                    "t": "&",
                                    "k": "f",
                                },
                            )

                        return True  # we made a change

                i += 1

            # job_id > number of jobs: nothing changed
            return False

        return self.apply_token_edit(record_id, edit_tokens)

    def _record_completion_event(
        self, record_id: int, completed_dt: datetime, due_dt: datetime | None
    ) -> None:
        """Best-effort persistence of completion history."""
        try:
            self.db_manager.add_completion(record_id, (completed_dt, due_dt))
        except Exception as exc:
            log_msg(f"Unable to record completion for {record_id}: {exc}")

    def finish_task(self, record_id: int, job_id: int | None, when: datetime) -> bool:
        stamp = self.fmt_user(when)

        # ---- Case 1: project job ----
        if job_id is not None:
            return self._add_finish_to_job(record_id, job_id, stamp)

        # ---- Case 2: plain task (no job_id) ----
        upcoming = self.db_manager.get_next_start_datetimes_for_record(record_id) or []
        completion_due: datetime | None = None
        if upcoming:
            try:
                completion_due = self._instance_local_from_text(upcoming[0])
            except Exception:
                completion_due = None

        def _return_with_completion(result: bool) -> bool:
            if result:
                self._record_completion_event(record_id, when, completion_due)
            return result

        # Case 2a: No instances or only 1 instance → append @f
        if len(upcoming) <= 1:
            if upcoming:
                instance_text = upcoming[0]
                self.delete_instance(record_id, instance_text)

            def edit_with_finish(text: str) -> str:
                return text.rstrip() + f" @f {stamp}"

            changed = self.apply_textual_edit(record_id, edit_with_finish)
            return _return_with_completion(changed)

        # Case 2b: 2+ instances → handle based on whether first is RDATE or RRULE
        first_instance_text = upcoming[0]
        second_instance_text = upcoming[1] if len(upcoming) > 1 else None

        # Get the record to access rruleset
        rec = self.db_manager.get_record_as_dictionary(record_id)
        if not rec:
            return False

        rruleset_str = rec.get("rruleset") or ""
        if not rruleset_str:
            # No rruleset, just delete first instance
            res = self.delete_instance(record_id, first_instance_text)
            return _return_with_completion(res)

        # Parse the first instance to get UTC datetime
        try:
            first_dt = parse(first_instance_text)
        except Exception:
            return False

        # Check if first instance comes from RDATE
        is_from_rdate = self._instance_is_from_rdate(rruleset_str, first_dt)

        if is_from_rdate:
            # First instance is from @+ (RDATE) → remove it from @+
            res = self.delete_instance(record_id, first_instance_text)
            return _return_with_completion(res)
        else:
            # First instance is from @r (RRULE) → update @s to second instance
            if not second_instance_text:
                # Safety: shouldn't happen, but handle gracefully
                res = self.delete_instance(record_id, first_instance_text)
                return _return_with_completion(res)

            res = self._advance_s_to_next_rrule_instance(
                record_id, second_instance_text
            )
            return _return_with_completion(res)

    def touch_item(self, record_id: int) -> None:
        """Refresh the modified timestamp for a record."""
        self.db_manager.touch_record(record_id)
        try:
            self.db_manager.populate_dependent_tables()
        except Exception:
            pass

    def schedule_new(self, record_id: int, job_id: int | None, when: datetime) -> bool:
        stamp = self.fmt_user(when)

        def edit(text: str) -> str:
            return text.rstrip() + f" @+ {stamp}"

        return self.apply_textual_edit(record_id, edit)

    def reschedule_instance(
        self,
        record_id: int,
        old_instance_text: str,
        new_when: datetime,
    ) -> bool:
        new_stamp = self.fmt_user(new_when)

        def edit(text: str) -> str:
            # Add @- old_instance and @+ new_instance
            return text.rstrip() + f" @- {old_instance_text} @+ {new_stamp}"

        return self.apply_textual_edit(record_id, edit)

    #
    #     rruleset = rec.get("rruleset") or ""
    #
    #     inst_dt = parse(instance_text)
    #     cutoff = inst_dt - timedelta(seconds=1)
    #     cutoff_stamp = self.fmt_user(cutoff)
    #
    #     def edit_tokens(tokens: list[dict]) -> bool:
    #         # 1) Special case: @s + @+ but no @r
    #         if self._is_s_plus_no_r(tokens) and rruleset:
    #             changed = self._adjust_s_plus_from_rruleset(
    #                 tokens,
    #                 rruleset=rruleset,
    #                 instance_text=instance_text,
    #                 mode="this_and_future",
    #             )
    #             if changed:
    #                 return True
    #             # fall through to general path if nothing changed
    #
    #         changed = False
    #
    #         # 2) General path: clean explicit @+ for this instance (UTC-Z)
    #         removed = self._remove_instance_from_plus_tokens(tokens, instance_text)
    #         changed = changed or removed
    #
    #         # 3) Always append &u cutoff for this-and-future semantics
    #         tokens.append(
    #             {
    #                 "token": f"&u {cutoff_stamp}",
    #                 "t": "&",
    #                 "k": "u",
    #             }
    #         )
    #         changed = True
    #
    #         return changed
    #
    #     return self.apply_token_edit(record_id, edit_tokens)

    def _is_in_plus_list(self, tokens: list[dict], dt: datetime) -> bool:
        """
        Return True if dt (local-naive) matches one of the entries in any @+ token.
        """
        local_dt = _to_local_naive(dt)
        fmt_str = local_dt.strftime("%Y%m%dT%H%M")
        for tok in tokens:
            if tok.get("k") == "+":
                body = tok["token"][2:].strip()
                for part in body.split(","):
                    part = part.strip()
                    try:
                        part_dt = parse(part)
                    except Exception:
                        continue
                    if _to_local_naive(part_dt).strftime("%Y%m%dT%H%M") == fmt_str:
                        return True
        return False

    def delete_instance(self, record_id: int, instance_text: str) -> bool:
        """
        Delete a specific instance:
        - If instance comes from @+ list, remove it from that list.
        - Otherwise append @- for that instance.
        """

        def edit_tokens(tokens: list[dict]) -> bool:
            try:
                inst_dt = parse(instance_text)
            except Exception:
                return False
            inst_local = _to_local_naive(inst_dt)

            if self._is_in_plus_list(tokens, inst_dt):
                # remove from @+
                tok_local_str = inst_local.strftime("%Y%m%dT%H%M")
                return self._remove_instance_from_plus_tokens(tokens, tok_local_str)
            else:
                # append exclusion
                tok_local_str = inst_local.strftime("%Y%m%dT%H%M")
                tokens.append({"token": f"@- {tok_local_str}", "t": "@", "k": "-"})
                return True

        return self.apply_token_edit(record_id, edit_tokens)

    def delete_this_and_future(self, record_id: int, instance_text: str) -> bool:
        """
        Delete this instance and all subsequent ones:
        - If the instance is in @+ list, remove it.
        - Always append &u cutoff (instance minus 1 second).
        """
        try:
            dt = parse(instance_text)
        except Exception:
            return False
        inst_local = _to_local_naive(dt)
        cutoff = inst_local - timedelta(seconds=1)
        cutoff_stamp = cutoff.strftime("%Y%m%dT%H%M")

        def edit_tokens(tokens: list[dict]) -> bool:
            changed = False
            if self._is_in_plus_list(tokens, dt):
                tok_local_str = inst_local.strftime("%Y%m%dT%H%M")
                removed = self._remove_instance_from_plus_tokens(tokens, tok_local_str)
                changed = changed or removed
            tokens.append({"token": f"&u {cutoff_stamp}", "t": "&", "k": "u"})
            return True

        return self.apply_token_edit(record_id, edit_tokens)

    def delete_record(self, record_id: int) -> None:
        # For jobs you may eventually allow “delete just this job”
        # but right now delete whole reminder:
        self.db_manager.delete_item(record_id)

    def apply_anniversary_if_needed(
        self, record_id: int, subject: str, instance: datetime
    ) -> str:
        """
        If this record is a recurring event with a {XXX} placeholder,
        replace it with the ordinal number of this instance.
        """
        if "{XXX}" not in subject:
            return subject

        row = self.db_manager.get_record(record_id)
        if not row:
            return subject

        # The rruleset text is column 4 (based on your tuple)
        rruleset = row[4]
        if not rruleset:
            return subject

        # --- Extract DTSTART and FREQ ---
        start_dt = None
        freq = None

        for line in rruleset.splitlines():
            if line.startswith("DTSTART"):
                # Handles both VALUE=DATE and VALUE=DATETIME
                if ":" in line:
                    val = line.split(":")[1].strip()
                    try:
                        if "T" in val:
                            start_dt = datetime.strptime(val, "%Y%m%dT%H%M%S")
                        else:
                            start_dt = datetime.strptime(val, "%Y%m%d")
                    except Exception:
                        pass
            elif line.startswith("RRULE"):
                # look for FREQ=YEARLY etc.
                parts = line.split(":")[-1].split(";")
                for p in parts:
                    if p.startswith("FREQ="):
                        freq_val = p.split("=")[1].strip().lower()
                        freq = {
                            "daily": "d",
                            "weekly": "w",
                            "monthly": "m",
                            "yearly": "y",
                        }.get(freq_val)
                        break

        if not start_dt or not freq:
            return subject

        # --- Compute ordinal replacement ---
        return set_anniversary(subject, start_dt, instance, freq)

    def apply_flags(self, record_id: int, subject: str) -> str:
        """
        Append any flags from Records.flags (e.g. 𝕒𝕘𝕠𝕣) to the given subject.
        """
        row = self.db_manager.get_record_as_dictionary(record_id)
        if not row:
            return subject

        flags = f" {row.get('flags')}" or ""
        # log_msg(f"{row = }, {flags = }")
        if not flags:
            return subject

        return subject + flags

    def get_name_to_binpath(self) -> Dict[str, str]:
        # leaf_lower -> "Leaf/Parent/.../Root"
        return self.db_manager.bin_cache.name_to_binpath()

    def add_tag(
        self, view: str, indx: int, record_id: int, *, job_id: int | None = None
    ):
        """Produce the next tag (with the pre-chosen width) and register it."""
        fill = self.afill_by_view[view]
        tag = indx_to_tag(indx, fill)  # uses your existing function
        dim = self.dim_style
        tag_fmt = f" [{dim}]{tag}[/{dim}] "
        self.list_tag_to_id.setdefault(view, {})[tag] = {
            "record_id": record_id,
            "job_id": job_id,
        }
        return tag_fmt, indx + 1

    def add_week_tag(
        self,
        yr_wk: Tuple[int, int],
        indx: int,
        record_id: int,
        job_id: int | None = None,
    ):
        """Produce the next tag (with the pre-chosen width) and register it."""
        fill = self.afill_by_week[yr_wk]
        tag = indx_to_tag(indx, fill)  # uses your existing function
        dim = self.dim_style
        tag_fmt = f" [{dim}]{tag}[/{dim}] "
        self.week_tag_to_id.setdefault(yr_wk, {})[tag] = {
            "record_id": record_id,
            "job_id": job_id,
        }
        return tag_fmt, indx + 1

    def mark_agenda_dirty(self) -> None:
        self._agenda_dirty = True

    def consume_agenda_dirty(self) -> bool:
        was_dirty = self._agenda_dirty
        self._agenda_dirty = False
        return was_dirty

    def toggle_pin(self, record_id: int) -> bool:
        self.db_manager.toggle_pinned(record_id)
        self.mark_agenda_dirty()  # ← mark dirty every time
        return self.db_manager.is_pinned(record_id)

    def get_last_details_meta(self):
        return self._last_details_meta

    def toggle_pinned(self, record_id: int):
        self.db_manager.toggle_pinned(record_id)
        log_msg(f"{record_id = }, {self.db_manager.is_pinned(record_id) = }")
        return self.db_manager.is_pinned(record_id)

    def get_entry(self, record_id, job_id=None, instance=None):
        """
        Build the Rich-rendered detail view for a reminder.

        Returns a list of strings representing:
        1) the colored header line (item type + subject);
        2) a blank spacer;
        3) the optional ``instance`` line if supplied;
        4) the optional formatted rruleset block (wrapped, indented);
        5) the id/created/modified footer with optional job id.

        Callers can feed the returned list directly into ListWithDetails.
        """
        lines = []
        result = self.db_manager.get_tokens(record_id)
        # log_msg(f"{result = }")

        tokens, rruleset, created, modified = result[0]

        # Preserve helpful highlighting even in the light theme; colors are adjusted earlier
        # in _apply_theme_colors() so contrast remains readable.
        highlight_tokens = True
        entry = format_tokens(tokens, self.width, highlight=highlight_tokens)
        entry = f"[bold {type_color}]{entry[0]}[/bold {type_color}]{entry[1:]}"

        log_msg(f"{rruleset = }")
        # rruleset = f"\n{11 * ' '}".join(rruleset.splitlines())

        instance_line = (
            f"[{label_color}]instance:[/{label_color}] {instance}" if instance else ""
        )
        rr_line = ""
        if rruleset:
            formatted_rr = format_rruleset_for_details(
                rruleset, width=self.width - 10, subsequent_indent=9
            )
            rr_line = f"[{label_color}]rruleset:[/{label_color}] {formatted_rr}"

        job = (
            f" [{label_color}]job_id:[/{label_color}] [bold]{job_id}[/bold]"
            if job_id
            else ""
        )
        lines.extend(
            [
                entry,
                " ",
                instance_line,
                rr_line,
                f"[{label_color}]id/cr/md:[/{label_color}] {record_id}{job} / {created} / {modified}",
            ]
        )

        return lines

    def update_record_from_item(self, item) -> None:
        self.cursor.execute(
            """
            UPDATE Records
            SET itemtype=?, subject=?, description=?, rruleset=?, timezone=?,
                extent=?, alerts=?, notice=?, context=?, jobs=?, tags=?,
                priority=?, tokens=?, modified=?
            WHERE id=?
            """,
            (
                item.itemtype,
                item.subject,
                item.description,
                item.rruleset,
                item.timezone or "",
                item.extent or "",
                json.dumps(item.alerts or []),
                item.notice or "",
                item.context or "",
                json.dumps(item.jobs or None),
                ";".join(item.tags or []),
                item.p or "",
                json.dumps(item.tokens),
                datetime.utcnow().timestamp(),
                item.id,
            ),
        )
        self.conn.commit()

    def get_record_core(self, record_id: int) -> dict:
        row = self.db_manager.get_record(record_id)
        if not row:
            return {
                "id": record_id,
                "itemtype": "",
                "subject": "",
                "rruleset": None,
                "record": None,
            }
        # tuple layout per your schema
        return {
            "id": record_id,
            "itemtype": row[1],
            "subject": row[2],
            "rruleset": row[4],
            "record": row,
        }

    def get_details_for_record(
        self,
        record_id: int,
        job_id: int | None = None,
        datetime_id: int | None = None,
        instance_ts: str | None = None,
    ):
        """
        Return list: [title, '', ... lines ...] same as process_tag would.
        Use the same internal logic as process_tag but accept ids directly.
        """
        # If you have a general helper that returns fields for a record, reuse it.
        # Here we replicate the important parts used by process_tag()
        core = self.get_record_core(record_id) or {}
        record_dict = self.db_manager.get_record_as_dictionary(record_id) or {}

        tokens_json = record_dict.get("tokens") or "[]"
        entry_text = ""
        try:
            tokens_list = json.loads(tokens_json)
            tokens_list = reveal_mask_tokens(tokens_list, self.mask_secret)
            entry_text = " ".join(
                tok.get("token", "").strip()
                for tok in tokens_list
                if isinstance(tok, dict) and tok.get("token")
            ).strip()
        except (json.JSONDecodeError, TypeError):
            entry_text = ""
        itemtype = core.get("itemtype") or ""
        rruleset = core.get("rruleset") or ""
        all_prereqs = core.get("all_prereqs") or ""

        instance_line = (
            f"\n[{label_color}]instance:[/{label_color}] {instance_ts}"
            if instance_ts
            else ""
        )

        subject = core.get("subject") or "(untitled)"
        if job_id is not None:
            try:
                js = self.db_manager.get_job_display_subject(record_id, job_id)
                if js:
                    subject = js
            except Exception:
                pass

        try:
            pinned_now = (
                self.db_manager.is_task_pinned(record_id) if itemtype == "~" else False
            )
        except Exception:
            pinned_now = False

        fields = [
            "",
        ] + self.get_entry(record_id, job_id, instance_ts)

        _dts = self.db_manager.get_next_start_datetimes_for_record(record_id)
        first, second = (_dts + [None, None])[:2]
        log_msg(f"setting meta {first = }, {second = }")

        # title = f"[bold]{subject:^{self.width}}[/bold]"
        title = f"[green]{subject:^{self.width}}[/green]"

        meta = {
            "record_id": record_id,
            "job_id": job_id,
            "itemtype": itemtype,
            "subject": subject,
            "rruleset": rruleset,
            "first": first,
            "second": second,
            "datetime_id": datetime_id,
            "instance_ts": instance_ts,
            "all_prereqs": all_prereqs,
            "pinned": bool(pinned_now),
            "record": record_dict,
            "entry_text": entry_text,
        }
        self._last_details_meta = meta

        # return [title, ""] + fields
        return title, fields, meta

    def get_record(self, record_id):
        return self.db_manager.get_record(record_id)

    def run_query(self, query_text: str) -> QueryResponse:
        """
        Execute a query string and return the resulting QueryResponse.
        """
        records = self.db_manager.iter_records_for_query()
        return self.query_engine.run(query_text, records)

    def get_all_records(self):
        return self.db_manager.get_all()

    def delete_record(self, record_id):
        self.db_manager.delete_record(record_id)

    def sync_jobs(self, record_id, jobs_list):
        self.db_manager.sync_jobs_from_record(record_id, jobs_list)

    def get_jobs(self, record_id):
        return self.db_manager.get_jobs_for_record(record_id)

    def get_job(self, record_id):
        return self.db_manager.get_jobs_for_record(record_id)

    def record_count(self):
        return self.db_manager.count_records()

    def populate_alerts(self):
        self.db_manager.populate_alerts()

    def populate_notice(self):
        self.db_manager.populate_notice()

    def refresh_alerts(self):
        self.db_manager.populate_alerts()

    def refresh_tags(self):
        self.db_manager.populate_tags()

    def execute_alert(self, command: str):
        """
        Execute the given alert command using subprocess.

        Args:
            command (str): The command string to execute.
        """
        if not command:
            print("❌ Error: No command provided to execute.")
            return

        try:
            # ✅ Use shlex.split() to safely parse the command
            subprocess.run(shlex.split(command), check=True)
            print(f"✅ Successfully executed: {command}")
        except subprocess.CalledProcessError as e:
            print(f"❌ Error executing command: {command}\n{e}")
        except FileNotFoundError:
            print(f"❌ Command not found: {command}")
        except Exception as e:
            print(f"❌ Unexpected error: {e}")

    def execute_due_alerts(self):
        records = self.db_manager.get_due_alerts()
        # log_msg(f"{records = }")
        # SELECT alert_id, record_id, record_name, trigger_datetime, start_timedelta, command
        for record in records:
            (
                alert_id,
                record_id,
                trigger_datetime,
                start_datetime,
                alert_name,
                alert_command,
            ) = record
            log_msg(
                f"Executing alert {alert_name = }, {alert_command = }, {trigger_datetime = }"
            )
            self.execute_alert(alert_command)
            # need command to execute command with arguments
            self.db_manager.mark_alert_executed(alert_id)

    def get_due_alerts(self, now: datetime) -> List[str]:
        due = []
        records = self.db_manager.get_due_alerts()
        for record in records:
            (
                alert_id,
                record_id,
                trigger_datetime,
                start_datetime,
                alert_name,
                alert_command,
            ) = record
            due.append([alert_id, alert_name, alert_command])
            log_msg(f"{due[-1] = }")
        return due

    def get_active_alerts(self, width: int = 70):
        # now_fmt = datetime.now().strftime("%A, %B %-d %H:%M:%S")
        alerts = self.db_manager.get_active_alerts()
        log_msg(f"{alerts = }")
        title = "Remaining alerts for today"
        if not alerts:
            header = f"[{HEADER_COLOR}] none remaining [/{HEADER_COLOR}]"
            return [], header

        now = datetime.now()

        trigger_width = 7 if self.AMPM else 8
        start_width = 7 if self.AMPM else 6
        alert_width = trigger_width + 3
        name_width = width - 35
        dim = self.dim_style
        header = f"[bold][{dim}]{'tag':^3}[/{dim}] {'alert':^{alert_width}}   {'for':^{start_width}}    {'subject':<{name_width}}[/bold]"

        rows = []
        log_msg(f"processing {len(alerts)} alerts")

        for alert in alerts:
            log_msg(f"Alert: {alert = }")
            # alert_id, record_id, record_name, start_dt, td, command
            (
                alert_id,
                record_id,
                record_name,
                trigger_datetime,
                start_datetime,
                alert_name,
                alert_command,
            ) = alert
            if now > datetime_from_timestamp(trigger_datetime):
                log_msg("skipping - already passed")
                continue
            # tag_fmt, indx = self.add_tag("alerts", indx, record_id)
            trtime = self.format_datetime(trigger_datetime)
            sttime = self.format_datetime(start_datetime)
            subject = truncate_string(record_name, name_width)
            text = (
                f"[{SALMON}] {alert_name} {trtime:<{trigger_width}}[/{SALMON}][{PALE_GREEN}] → {sttime:<{start_width}}[/{PALE_GREEN}] "
                + f" [{AVAILABLE_COLOR}]{subject:<{name_width}}[/{AVAILABLE_COLOR}]"
            )
            rows.append({"record_id": record_id, "job_id": None, "text": text})
        pages = self._paginate(rows)
        log_msg(f"{header = }\n{rows = }\n{pages = }")
        return pages, header

    def get_table_and_list(self, start_date: datetime, selected_week: tuple[int, int]):
        year, week = selected_week

        try:
            extended = self.db_manager.ensure_week_generated_with_topup(
                year, week, cushion=6, topup_threshold=2
            )
            if extended:
                log_msg(
                    f"[weeks] extended/generated around {year}-W{week:02d} (+cushion)"
                )
                try:
                    self.db_manager.populate_dependent_tables()
                except Exception as refresh_exc:
                    log_msg(
                        f"[weeks] populate_dependent_tables failed after extension: {refresh_exc}"
                    )
        except Exception as e:
            log_msg(f"[weeks] ensure_week_generated_with_topup error: {e}")

        year_week = f"{year:04d}-{week:02d}"
        busy_bits = self.db_manager.get_busy_bits_for_week(year_week)
        busy_bar = self._format_busy_bar(busy_bits)

        start_dt = datetime.strptime(f"{year} {week} 1", "%G %V %u")
        details = self.get_week_details(selected_week)

        title = format_iso_week(start_dt)
        return title, busy_bar, details

    def _format_busy_bar(
        self,
        bits: list[int],
        *,
        busy_color: str | None = None,
        conflict_color: str | None = None,
        allday_color: str | None = None,
        header_color: str | None = None,
    ) -> str:
        """
        Render 35 busy bits (7×[1 all-day + 4×6h blocks]) as a compact single-row
        week bar with color markup.

        Layout:
            | Mon | Tue | Wed | Thu | Fri | Sat | Sun |
            |■██▓▓|     |▓███ | ... |

        Encoding:
            0 = free       → " "
            1 = busy       → colored block
            2 = conflict   → colored block
            (first of 5 per day is the all-day bit → colored "■" if set)
        """
        DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        assert len(bits) == 35, "expected 35 bits (7×5)"

        theme = getattr(self, "ui_theme", "dark")
        if busy_color is None:
            busy_color = "green" if theme == "dark" else "#1f7a1f"
        if conflict_color is None:
            conflict_color = "red" if theme == "dark" else "#c62828"
        if allday_color is None:
            allday_color = "#ffbf00" if theme == "dark" else "#ff9100"
        if header_color is None:
            # header_color = "cyan" if theme == "dark" else "#1f395a"
            header_color = LEMON_CHIFFON if theme == "dark" else "#1f395a"

        # --- Header line
        header = "│".join(f" {d:^3} " for d in DAYS)
        lines = [f"[{header_color}]│{header}│[/{header_color}]"]

        # --- Busy row
        day_segments = []
        vertical_bar = f"[{header_color}]│[/{header_color}]"
        for day in range(7):
            start = day * 5
            all_day_bit = bits[start]
            block_bits = bits[start + 1 : start + 5]

            # --- all-day symbol
            if all_day_bit:
                all_day_char = f"[{allday_color}]█[/{allday_color}]"
            else:
                all_day_char = " "

            # --- 4×6h blocks
            blocks = ""
            for b in block_bits:
                if b == 1:
                    blocks += f"[{busy_color}]█[/{busy_color}]"
                elif b == 2:
                    blocks += f"[{conflict_color}]▓[/{conflict_color}]"
                else:
                    blocks += " "

            day_segments.append(all_day_char + blocks)

        lines.append(f"{vertical_bar}{'│'.join(day_segments)}{vertical_bar}")
        return "\n".join(lines)

    def get_week_details(self, yr_wk):
        """
        Fetch and format rows for a specific week.
        """
        # log_msg(f"Getting rows for week {yr_wk}")
        today = datetime.now()
        tomorrow = today + ONEDAY
        today_year, today_week, today_weekday = today.isocalendar()
        tomorrow_year, tomorrow_week, tomorrow_day = tomorrow.isocalendar()

        self.selected_week = yr_wk

        start_datetime = datetime.strptime(f"{yr_wk[0]} {yr_wk[1]} 1", "%G %V %u")
        end_datetime = start_datetime + timedelta(weeks=1)
        events = self.db_manager.get_events_for_period(start_datetime, end_datetime)

        # log_msg(f"from get_events_for_period:\n{events = }")
        this_week = format_date_range(start_datetime, end_datetime - ONEDAY)
        # terminal_width = shutil.get_terminal_size().columns

        header = f"{this_week} #{yr_wk[1]} ({len(events)})"
        rows = []

        # self.set_week_afill(events, yr_wk)

        if not events:
            rows.append(
                {
                    "record_id": None,
                    "job_id": None,
                    "datetime_id": None,
                    "instance_ts": yr_wk[0],
                    "text": f" [{HEADER_COLOR}]Nothing scheduled for this week[/{HEADER_COLOR}]",
                }
            )
            pages = self._paginate(rows)
            return pages

        weekday_to_events = {}
        for i in range(7):
            this_day = (start_datetime + timedelta(days=i)).date()
            weekday_to_events[this_day] = []

        # for start_ts, end_ts, itemtype, subject, id, job_id in events:
        for dt_id, start_ts, end_ts, itemtype, subject, id, job_id in events:
            start_dt = datetime_from_timestamp(start_ts)
            end_dt = datetime_from_timestamp(end_ts)
            if itemtype == "*":  # event
                # 🪄 new line: replace {XXX} with ordinal instance
                subject = self.apply_anniversary_if_needed(id, subject, start_dt)
                # log_msg(
                #     f"Week rows {itemtype = }, {subject = }, {start_dt = }, {end_dt = }"
                # )
            status = "available"

            if start_dt == end_dt:
                # if start_dt.hour == 0 and start_dt.minute == 0 and start_dt.second == 0:
                if start_dt.hour == 0 and start_dt.minute == 0:
                    # start_end = f"{str('~'):^11}"
                    start_end = ""
                elif start_dt.hour == 23 and start_dt.minute == 59:
                    start_end = ""
                else:
                    start_end = f"{format_time_range(start_dt, end_dt, self.AMPM)}"
            else:
                start_end = f"{format_time_range(start_dt, end_dt, self.AMPM)}"

            type_color = TYPE_TO_COLOR[itemtype]
            escaped_start_end = (
                f"[not bold]{start_end} [/not bold]" if start_end else ""
            )

            if job_id:
                job = self.db_manager.get_job_dict(id, job_id)
                status = job.get("status", "available")
                subject = job.get("display_subject", subject)
                itemtype = "~"
            if status != "available":
                type_color = WAITING_COLOR

            # 👉 NEW: append flags from Records.flags
            old_subject = subject
            subject = self.apply_flags(id, subject)

            row = {
                "record_id": id,
                "job_id": job_id,
                "datetime_id": dt_id,
                "instance_ts": start_ts,
                "text": f"[{type_color}]{itemtype} {escaped_start_end}{subject}[/{type_color}]",
            }
            weekday_to_events.setdefault(start_dt.date(), []).append(row)

        for day, events in weekday_to_events.items():
            # TODO: today, tomorrow here
            iso_year, iso_week, weekday = day.isocalendar()
            today = (
                iso_year == today_year
                and iso_week == today_week
                and weekday == today_weekday
            )
            tomorrow = (
                iso_year == tomorrow_year
                and iso_week == tomorrow_week
                and weekday == tomorrow_day
            )
            flag = " (today)" if today else " (tomorrow)" if tomorrow else ""
            if events:
                rows.append(
                    {
                        "record_id": None,
                        "job_id": None,
                        "datetime_id": dt_id,
                        "instance_ts": start_ts,
                        # "text": f"[bold][{HEADER_COLOR}]{day.strftime('%a, %b %-d')}{flag}[/{HEADER_COLOR}][/bold]",
                        "text": f"[{HEADER_COLOR}]{day.strftime('%a, %b %-d')}{flag}[/{HEADER_COLOR}]",
                    }
                )
                for event in events:
                    rows.append(event)
        pages = self._paginate(rows)
        self.yrwk_to_pages[yr_wk] = pages
        # log_msg(f"{len(pages) = }, {pages[0] = }, {pages[-1] = }")
        return pages

    def get_busy_bits_for_week(self, selected_week: tuple[int, int]) -> list[int]:
        """Convert (year, week) tuple to 'YYYY-WW' and delegate to model."""
        year, week = selected_week
        year_week = f"{year:04d}-{week:02d}"
        return self.db_manager.get_busy_bits_for_week(year_week)

    def get_next(self):
        """
        Fetch and format description for the next instances.
        """
        events = self.db_manager.get_next_instances()
        header = f"Next Instances ({len(events)})"

        if not events:
            return [], header

        year_to_events = {}

        for dt_id, id, job_id, subject, description, itemtype, start_ts in events:
            start_dt = datetime_from_timestamp(start_ts)
            subject = self.apply_anniversary_if_needed(id, subject, start_dt)
            if job_id is not None:
                try:
                    js = self.db_manager.get_job_display_subject(id, job_id)
                    if js:
                        subject = js
                except Exception as e:
                    log_msg(f"{e = }")

            subject = self.apply_flags(id, subject)
            day_display = start_dt.strftime("%m-%d")
            timestamp_markup = f"[not bold]{day_display}[/not bold]"
            type_color = TYPE_TO_COLOR[itemtype]
            item = {
                "record_id": id,
                "job_id": job_id,
                "datetime_id": dt_id,
                "instance_ts": start_ts,
                "text": f"{timestamp_markup}   [{type_color}]{itemtype} {subject}[/{type_color}]",
            }
            year_to_events.setdefault(start_dt.strftime("%b %Y"), []).append(item)

        # self.list_tag_to_id.setdefault("next", {})
        # indx = 0
        """
        rows: a list of dicts each with either
           - { 'record_id': int, 'text': str }  (a taggable record row)
           - { 'record_id': None, 'text': str }  (a non-taggable header row)
        page_size: number of taggable rows per page
        """

        rows = []
        for ym, events in year_to_events.items():
            if events:
                rows.append(
                    {
                        "dt_id": None,
                        "record_id": None,
                        "job_id": None,
                        "datetime_id": None,
                        "instance_ts": None,
                        "text": f"[not bold][{HEADER_COLOR}]{ym}[/{HEADER_COLOR}][/not bold]",
                    }
                )
                for event in events:
                    rows.append(event)

        # build 'rows' as a list of dicts with record_id and text
        pages = self._paginate(rows)
        return pages, header

    def get_modified(self, yield_rows: bool = False):
        """
        List reminders ordered by their modified timestamp (newest first).
        """
        records = self.db_manager.get_records_by_modified()
        header = f"Modified ({len(records)})"

        rows: list[dict] = []
        if not records:
            return rows if yield_rows else ([], header)

        current_bucket: str | None = None
        for record_id, subject, itemtype, modified_ts, _desc in records:
            normalized_ts = (
                modified_ts[:-1]
                if modified_ts and modified_ts.endswith("Z")
                else modified_ts
            )
            bucket_dt = datetime_from_timestamp(normalized_ts)
            bucket_label = bucket_dt.strftime("%b %Y") if bucket_dt else "Unknown"
            day_display = bucket_dt.strftime("%m-%d") if bucket_dt else "--"
            if bucket_label != current_bucket:
                current_bucket = bucket_label
                rows.append(
                    {
                        "record_id": None,
                        "job_id": None,
                        "datetime_id": None,
                        "instance_ts": None,
                        "text": f"[not bold][{HEADER_COLOR}]{bucket_label}[/{HEADER_COLOR}][/not bold]",
                    }
                )

            subject_text = subject or "(untitled)"
            subject_text = self.apply_flags(record_id, subject_text)
            timestamp_markup = f"[not bold]{day_display}[/not bold]"
            type_color = TYPE_TO_COLOR.get(itemtype, "white")

            rows.append(
                {
                    "record_id": record_id,
                    "job_id": None,
                    "datetime_id": None,
                    "instance_ts": modified_ts,
                    "text": f"{timestamp_markup}   [{type_color}]{itemtype} {subject_text}[/{type_color}]",
                }
            )

        if yield_rows:
            return rows

        pages = self._paginate(rows)
        return pages, header

    def get_goals(self, yield_rows: bool = False, *, include_future: bool = False):
        """
        Build the data needed for Goals View: priority-sorted goals with progress.

        When `include_future` is True, also include inactive goals whose next @s
        start time is in the future and sort the result by that datetime.
        """

        def _get_at_value(tokens: list[dict], key: str) -> str:
            for tok in tokens:
                if tok.get("t") == "@" and tok.get("k") == key:
                    token_text = tok.get("token") or ""
                    parts = token_text.split(maxsplit=1)
                    if len(parts) == 2:
                        return parts[1].strip()
            return ""

        def _update_at_token(
            tokens: list[dict],
            key: str,
            new_value: str | None,
            *,
            allow_create: bool = False,
        ) -> bool:
            """
            Update the first token matching @<key>. Returns True when a change occurs.
            """
            for idx, tok in enumerate(tokens):
                if tok.get("t") == "@" and tok.get("k") == key:
                    if new_value is None:
                        tokens.pop(idx)
                        return True
                    new_text = f"@{key} {new_value}".strip()
                    if tok.get("token") != new_text:
                        tokens[idx] = {**tok, "token": new_text}
                        return True
                    return False
            if new_value is None or not allow_create:
                return False
            tokens.append({"token": f"@{key} {new_value}".strip(), "t": "@", "k": key})
            return True

        records = self.db_manager.get_goal_records()
        # header = (
        #     f"[bold {HEADER_COLOR}]tag        done    left      subject"
        #     f"[/bold {HEADER_COLOR}]"
        # )
        header = ""

        if not records:
            if yield_rows:
                return [], 0, header
            rows = [
                {
                    "record_id": None,
                    "job_id": None,
                    "datetime_id": None,
                    "instance_ts": None,
                    "text": f"[{HEADER_COLOR}]No goals available[/{HEADER_COLOR}]",
                }
            ]
            return self._paginate(rows), "Goals (0)", header

        now = datetime.now()
        goals: list[dict[str, object]] = []

        for record_id, subject, tokens_json in records:
            raw_tokens = _ensure_tokens_list(tokens_json)
            tokens = reveal_mask_tokens(raw_tokens, self.mask_secret)
            if not tokens:
                continue

            start_raw = _get_at_value(tokens, "s")
            k_raw = _get_at_value(tokens, "k")
            target_raw = _get_at_value(tokens, "t")
            if not start_raw or not target_raw or "/" not in target_raw:
                continue

            try:
                parsed_start = parse(
                    start_raw,
                    yearfirst=self.yearfirst,
                    dayfirst=self.dayfirst,
                )
            except Exception:
                continue

            start_is_date_only = isinstance(parsed_start, date) and not isinstance(
                parsed_start, datetime
            )
            if start_is_date_only:
                start_dt = datetime.combine(parsed_start, datetime.min.time())
            else:
                start_dt = parsed_start if isinstance(parsed_start, datetime) else None
                if start_dt is None:
                    continue
            if start_dt.tzinfo is not None:
                start_dt = _to_local_naive(start_dt)

            num_part, period_part = target_raw.split("/", 1)
            try:
                num_required = int(num_part.strip())
            except Exception:
                continue
            if num_required <= 0:
                continue

            ok, seconds = timedelta_str_to_seconds(period_part.strip())
            if not ok or not isinstance(seconds, int) or seconds <= 0:
                continue
            period_td = timedelta(seconds=seconds)

            completed_raw = _get_at_value(tokens, "k")
            try:
                num_completed = int(completed_raw.strip())
            except Exception:
                num_completed = 0
            num_completed = max(0, min(num_completed, num_required))

            tokens_dirty = False
            has_k_token = any(
                tok.get("t") == "@" and tok.get("k") == "k" for tok in raw_tokens
            )

            completed_periods = num_completed // num_required if num_required else 0
            if completed_periods:
                start_dt = start_dt + period_td * completed_periods
                num_completed -= completed_periods * num_required
                formatted_start = self.fmt_user(
                    start_dt.date() if start_is_date_only else start_dt
                )
                if _update_at_token(raw_tokens, "s", formatted_start):
                    tokens_dirty = True
                if has_k_token and _update_at_token(
                    raw_tokens, "k", str(num_completed)
                ):
                    tokens_dirty = True

            end_dt = start_dt + period_td

            if now >= end_dt:
                delta = now - start_dt
                periods_passed = max(1, int(delta // period_td))
                start_dt = start_dt + period_td * periods_passed
                end_dt = start_dt + period_td
                formatted_start = self.fmt_user(
                    start_dt.date() if start_is_date_only else start_dt
                )
                if _update_at_token(raw_tokens, "s", formatted_start):
                    tokens_dirty = True
                if has_k_token and _update_at_token(raw_tokens, "k", "0"):
                    tokens_dirty = True
                num_completed = 0

            if tokens_dirty:
                self.db_manager.update_record_tokens(record_id, raw_tokens)

            if (not include_future) and now < start_dt:
                continue

            remaining_seconds_raw = int((end_dt - now).total_seconds())
            remaining_display = "now"
            if remaining_seconds_raw != 0:
                pretty = (
                    format_timedelta(abs(remaining_seconds_raw), short=True) or "now"
                )
                if remaining_seconds_raw < 0:
                    remaining_display = f"-{pretty.lstrip('+').lstrip('-')}"
                else:
                    remaining_display = pretty.lstrip("+")

            remaining_instances = max(num_required - num_completed, 0)
            period_seconds = max(int(period_td.total_seconds()), 1)
            time_for_priority = (
                remaining_seconds_raw if remaining_seconds_raw > 0 else 1
            )
            if remaining_instances == 0:
                priority = 0
            else:
                priority = (remaining_instances * period_seconds) / (
                    num_required * time_for_priority
                )

            goals.append(
                {
                    "record_id": record_id,
                    "priority": priority,
                    "remaining_seconds": max(remaining_seconds_raw, 0),
                    "remaining_instances": remaining_instances,
                    "num_required": num_required,
                    "num_completed": num_completed,
                    "subject": self.apply_flags(record_id, subject or "(no subject)"),
                    "time_display": remaining_display,
                    "start_dt": start_dt,
                    "start_display": self.fmt_user(
                        start_dt.date() if start_is_date_only else start_dt
                    ),
                }
            )

        if not goals:
            if yield_rows:
                return [], 0, header
            rows = [
                {
                    "record_id": None,
                    "job_id": None,
                    "datetime_id": None,
                    "instance_ts": None,
                    "text": f"[{HEADER_COLOR}]No goals available[/{HEADER_COLOR}]",
                }
            ]
            return self._paginate(rows), "Goals (0)", header

        def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
            hex_color = hex_color.lstrip("#")
            return tuple(int(hex_color[i : i + 2], 16) for i in (0, 2, 4))

        def _rgb_to_hex(rgb: tuple[int, int, int]) -> str:
            return "#{:02x}{:02x}{:02x}".format(*rgb)

        min_priority = 0.0
        max_priority = 2.0
        low_rgb = _hex_to_rgb(PALE_GREEN)
        high_rgb = _hex_to_rgb(ORANGE_RED)

        def _priority_color(value: float) -> str:
            clamped = max(min_priority, min(max_priority, value))
            span = max_priority - min_priority or 1.0
            t = (clamped - min_priority) / span
            rgb = tuple(
                round(low + t * (high - low)) for low, high in zip(low_rgb, high_rgb)
            )
            return _rgb_to_hex(rgb)

        if include_future:
            goals.sort(
                key=lambda g: (
                    g["start_dt"],
                    g["subject"].lower(),
                )
            )
        else:
            goals.sort(
                key=lambda g: (
                    -g["priority"],
                    g["remaining_seconds"],
                    g["subject"].lower(),
                )
            )

        rows = []
        goal_count = len(goals)
        for goal in goals:
            # priority_display = f"{goal['priority']:.2f}"
            priority_display = f"{round(100 * goal['priority'])}"
            progress_display = f"{goal['remaining_instances']}/{goal['num_required']}"
            time_display = goal["time_display"]
            row_color = _priority_color(goal["priority"])
            if include_future:
                start_display = goal["start_display"]
                text = (
                    f"[{row_color}]{start_display:>16} "
                    f"{progress_display:>4} {time_display:^6} "
                    f"{goal['subject']}[/{row_color}]"
                )
            else:
                text = (
                    f"[{row_color}]{priority_display:>3} "
                    f"{progress_display:>4} {time_display:^6} "
                    f"{goal['subject']}[/{row_color}]"
                )
            rows.append(
                {
                    "record_id": goal["record_id"],
                    "job_id": None,
                    "datetime_id": None,
                    "instance_ts": None,
                    "text": text,
                }
            )

        if yield_rows:
            return rows, goal_count, header

        pages = self._paginate(rows)
        title = f"Goals ({goal_count})"
        return pages, title, header

    def get_year_calendar(
        self, year_offset: int = 0, available_width: int | None = None
    ) -> tuple[list[str], str]:
        width = available_width or shutil.get_terminal_size((80, 20)).columns
        columns = 2 if width < 70 else 3
        target_year = datetime.now().year + year_offset

        gap = 3
        # width per column leaves a gap between blocks; keep at least 17 chars
        available_for_columns = max(width - (columns - 1) * gap, 34)
        col_width = max(17, available_for_columns // columns)

        text_cal = calendar.TextCalendar()
        months = [
            text_cal.formatmonth(target_year, m, w=2).splitlines() for m in range(1, 13)
        ]

        lines: list[str] = [""]
        for start in range(0, 12, columns):
            group = months[start : start + columns]
            max_height = max(len(m) for m in group)
            for m in group:
                while len(m) < max_height:
                    m.append("")
            for row in range(max_height):
                segments = [m[row].ljust(col_width) for m in group]
                line = (" " * gap).join(segments)
                lines.append(line.rstrip())
            lines.append("")

        while lines and not lines[-1].strip():
            lines.pop()

        max_len = max((len(line) for line in lines), default=0)
        indent = " " * max(((width - max_len) // 2), 0)
        indented = [indent + line for line in lines]
        title = f"Year {target_year}"
        return indented, title

    def get_last(self):
        """
        Fetch and format description for the next instances.
        """
        events = self.db_manager.get_last_instances()
        header = f"Last instances ({len(events)})"
        # description = [f"[not bold][{HEADER_COLOR}]{header}[/{HEADER_COLOR}][/not bold]"]

        if not events:
            return [], header

        # use a, ..., z if len(events) <= 26 else use aa, ..., zz
        year_to_events = {}

        for dt_id, id, job_id, subject, description, itemtype, start_ts in events:
            start_dt = datetime_from_timestamp(start_ts)
            subject = self.apply_anniversary_if_needed(id, subject, start_dt)
            if job_id is not None:
                try:
                    js = self.db_manager.get_job_display_subject(id, job_id)
                    if js:
                        subject = js
                except Exception:
                    pass

            subject = self.apply_flags(id, subject)
            day_display = start_dt.strftime("%m-%d")
            timestamp_markup = f"[not bold]{day_display}[/not bold]"
            type_color = TYPE_TO_COLOR[itemtype]
            item = {
                "dt_id": dt_id,
                "record_id": id,
                "job_id": job_id,
                "instance_ts": start_ts,
                "text": f"{timestamp_markup}   [{type_color}]{itemtype} {subject}[/{type_color}]",
            }
            year_to_events.setdefault(start_dt.strftime("%b %Y"), []).append(item)

        rows = []
        for ym, events in year_to_events.items():
            if events:
                rows.append(
                    {
                        "record_id": None,
                        "job_id": None,
                        "text": f"[not bold][{HEADER_COLOR}]{ym}[/{HEADER_COLOR}][/not bold]",
                    }
                )
                for event in events:
                    rows.append(event)
        pages = self._paginate(rows)
        return pages, header

    def find_records(self, search_str: str):
        """
        Fetch and format description for the next instances.
        """
        search_str = search_str.strip()
        events = self.db_manager.find_records(search_str)

        matching = (
            f'containing a match for "[{SELECTED_COLOR}]{search_str}[/{SELECTED_COLOR}]" '
            if search_str
            else "matching anything"
        )

        header = f"Items ({len(events)})\n {matching}"

        if not events:
            return [], header

        rows = []

        for record_id, subject, _, itemtype, last_ts, next_ts in events:
            subject = f"{truncate_string(subject, 32):<34}"
            # 👉 NEW: append flags from Records.flags
            subject = self.apply_flags(record_id, subject)
            last_dt = (
                datetime_from_timestamp(last_ts).strftime("%y-%m-%d %H:%M")
                if last_ts
                else "~"
            )
            last_fmt = f"{last_dt:^14}"
            next_dt = (
                datetime_from_timestamp(next_ts).strftime("%y-%m-%d %H:%M")
                if next_ts
                else "~"
            )
            next_fmt = f"{next_dt:^14}"
            type_color = TYPE_TO_COLOR[itemtype]
            escaped_last = f"[not bold]{last_fmt}[/not bold]"
            escaped_next = f"[not bold]{next_fmt}[/not bold]"
            rows.append(
                {
                    "record_id": record_id,
                    "job_id": None,
                    "text": f"[{type_color}]{itemtype} {subject} {escaped_next}[/{type_color}]",
                }
            )
        pages = self._paginate(rows)
        return pages, header

    def group_events_by_date_and_time(self, events):
        """
        Groups only scheduled '*' events by date and time.

        Args:
            events (List[Tuple[int, int, str, str, int]]):
                List of (start_ts, end_ts, itemtype, subject, id)

        Returns:
            Dict[date, List[Tuple[time, Tuple]]]:
                Dict mapping date to list of (start_time, event) tuples
        """
        grouped = defaultdict(list)

        for dt_id, start_ts, end_ts, itemtype, subject, record_id, job_id in events:
            # log_msg(f"{start_ts = }, {end_ts = }, {subject = }")
            if itemtype != "*":
                continue  # Only events

            start_dt = datetime_from_timestamp(start_ts)
            grouped[start_dt.date()].append(
                (start_dt.time(), (dt_id, start_ts, end_ts, subject, record_id, job_id))
            )

        # Sort each day's events by time
        for date in grouped:
            grouped[date].sort(key=lambda x: x[0])

        return dict(grouped)

    def get_completions(self):
        """
        Fetch and format recent completions for a Completions view.

        Returns:
            pages, header

        pages has the same shape as get_next:
            [ (page_rows: list[str], page_tag_map: dict[str, (record_id, job_id)]) ]
        """
        records = self.db_manager.get_all_completions()
        header = f"Completions ({len(records)})"
        items = self._build_completion_items(records)
        pages = self._paginate(items)
        return pages, header

    def _build_completion_items(
        self,
        records: list[tuple[int, str, str, str, datetime | None, datetime]],
        *,
        empty_message: str | None = None,
    ) -> list[dict]:
        """
        Shared formatter that converts completion rows into renderable dicts.
        """
        if not records:
            if not empty_message:
                return []
            return [
                {
                    "dt_id": None,
                    "record_id": None,
                    "job_id": None,
                    "datetime_id": None,
                    "instance_ts": None,
                    "text": f"[{HEADER_COLOR}]{empty_message}[/{HEADER_COLOR}]",
                }
            ]

        year_to_events: OrderedDict[str, list[dict]] = OrderedDict()

        for (
            record_id,
            subject,
            description,
            itemtype,
            due_dt,
            completed_dt,
        ) in records:
            subject = self.apply_flags(record_id, subject or "(untitled)")
            completed_dt = completed_dt.astimezone()
            due_dt = due_dt.astimezone() if due_dt else None

            monthday = completed_dt.strftime("%-m-%d")
            time_part = format_hours_mins(completed_dt, HRS_MINS)
            when_str = f"{monthday:>2} {time_part}"

            type_color = TYPE_TO_COLOR.get(itemtype, "white")
            when_frag = f"[not bold]{when_str}[/not bold]"

            item = {
                "record_id": record_id,
                "job_id": None,
                "datetime_id": None,
                "instance_ts": due_dt.strftime("%Y%m%dT%H%M") if due_dt else "none",
                "text": f"[{type_color}]{itemtype} {when_frag} {subject}[/{type_color}]",
            }

            ym = completed_dt.strftime("%b %Y")
            year_to_events.setdefault(ym, []).append(item)

        rows: list[dict] = []
        for ym, events in year_to_events.items():
            if not events:
                continue
            rows.append(
                {
                    "dt_id": None,
                    "record_id": None,
                    "job_id": None,
                    "datetime_id": None,
                    "instance_ts": None,
                    "text": f"[not bold][{HEADER_COLOR}]{ym}[/{HEADER_COLOR}][/not bold]",
                }
            )
            rows.extend(events)

        return rows

    def get_record_completion_pages(self, record_id: int):
        """
        Build a Completions-style view limited to a single record.
        """
        records = self.db_manager.get_completions(record_id)
        rec_dict = self.db_manager.get_record_as_dictionary(record_id) or {}
        subject = rec_dict.get("subject") or "(untitled)"
        header = f"Completions for {subject} ({len(records)})"
        items = self._build_completion_items(
            records,
            empty_message=f"No completions recorded for {subject}",
        )
        pages = self._paginate(items)
        return pages, header

    def get_record_completions(self, record_id: int):
        """
        Return (title, lines) describing completions for a specific record,
        formatted like the global Completions view.
        """
        records = self.db_manager.get_completions(record_id)
        rec_dict = self.db_manager.get_record_as_dictionary(record_id) or {}
        subject = rec_dict.get("subject") or "(untitled)"
        title = f"Completions for {subject}"
        items = self._build_completion_items(
            records,
            empty_message=f"No completions recorded for {subject}",
        )

        lines: list[str] = []
        for item in items:
            text = item.get("text", "")
            if item.get("record_id") is None:
                lines.append(text)
            else:
                lines.append(f"  {text}")

        return title, lines

    def get_record_repetitions(self, record_id: int, *, limit: int = 20):
        """
        Return (title, lines) describing the next few repetitions for a record.
        """
        record_dict = self.db_manager.get_record_as_dictionary(record_id) or {}
        subject = record_dict.get("subject") or "(untitled)"
        rruleset = (record_dict.get("rruleset") or "").strip()
        tokens_raw = record_dict.get("tokens")
        tokens_list: list[dict] = []
        if isinstance(tokens_raw, str):
            try:
                tokens_list = json.loads(tokens_raw)
            except Exception:
                tokens_list = []
        elif isinstance(tokens_raw, list):
            tokens_list = tokens_raw

        has_rrule = bool(rruleset) or any(
            isinstance(tok, dict) and tok.get("t") == "@" and tok.get("k") == "r"
            for tok in tokens_list
        )

        title = f"Repetitions for {subject}"
        if not has_rrule:
            return title, ["This reminder has no @r schedule."]

        lines: list[str] = []
        upcoming_rows = self.db_manager.get_upcoming_instances_for_record(
            record_id, limit=limit
        )

        def _parse_dt(text: str | None) -> datetime | None:
            if not text:
                return None
            try:
                return self._instance_local_from_text(text)
            except Exception:
                return None

        occurrences: list[tuple[datetime | None, datetime | None]] = [
            (_parse_dt(start), _parse_dt(end)) for start, end in upcoming_rows
        ]

        if not occurrences and rruleset:
            try:
                rule = rrulestr(rruleset)
                cursor = datetime.now()
                for _ in range(limit):
                    nxt = rule.after(cursor, inc=True)
                    if not nxt:
                        break
                    occurrences.append((self._dt_local_naive(nxt), None))
                    cursor = nxt + timedelta(seconds=1)
            except Exception as exc:
                return title, [f"Unable to parse rruleset: {exc}"]

        if not occurrences:
            return title, ["No upcoming repetitions were found."]

        lines.append(f"Next {len(occurrences)} occurrence(s):")
        for start_dt, end_dt in occurrences:
            start_display = self.fmt_user(start_dt) if start_dt else "—"
            if end_dt:
                end_display = self.fmt_user(end_dt)
                lines.append(f"  • {start_display} → {end_display}")
            else:
                lines.append(f"  • {start_display}")

        if rruleset:
            lines.extend(
                ["", "rruleset:", *(f"  {line}" for line in rruleset.splitlines())]
            )

        return title, lines

    def get_agenda(self, now: datetime | None = None, yield_rows: bool = False):
        """Return agenda rows/pages combining events, goals, and tasks."""
        if now is None:
            now = datetime.now()
        header = "Agenda"
        divider = [
            {
                "record_id": None,
                "job_id": None,
                "datetime_id": None,
                "instance_ts": None,
                "text": "   ",
            },
        ]
        events_by_date = self.get_agenda_events(now=now)
        goals_rows, goal_count, goals_header = self.get_goals(
            yield_rows=True, include_future=False
        )
        tasks_by_urgency = self.get_agenda_tasks()

        goals_section: list[dict] = []
        if goal_count:
            goals_section.append(
                {
                    "record_id": None,
                    "job_id": None,
                    "datetime_id": None,
                    "instance_ts": None,
                    "text": f"Goals ({goal_count})",
                }
            )
            if goals_header:
                goals_section.append(
                    {
                        "record_id": None,
                        "job_id": None,
                        "datetime_id": None,
                        "instance_ts": None,
                        "text": goals_header,
                    }
                )
            goals_section.extend(goals_rows)

        events_goals_tasks = list(events_by_date)
        if goals_section:
            if events_goals_tasks:
                events_goals_tasks += divider
            events_goals_tasks.extend(goals_section)
        if events_goals_tasks:
            events_goals_tasks += divider
        events_goals_tasks.extend(tasks_by_urgency)

        if yield_rows:
            return events_goals_tasks

        pages = self._paginate(events_goals_tasks)
        return pages, header

    def get_agenda_events(self, now: datetime | None = None):
        """
        Build agenda event rows for the configured number of days.
        Rules:
        • Pick the first N days with events where N = agenda_days.
        • Also include TODAY if it has notice/drafts even with no events.
        • If nothing to display at all, return [].
        """
        if now is None:
            now = datetime.now()

        notice_records = (
            self.db_manager.get_notice_for_events()
        )  # (record_id, days_remaining, subject)
        draft_records = self.db_manager.get_drafts()  # (record_id, subject)

        today_dt = now.replace(hour=0, minute=0, second=0, microsecond=0)
        today = today_dt.date()
        now_ts = _fmt_naive(now)
        days_limit = max(1, getattr(self, "agenda_days", 3))

        # Pull events for the next couple of weeks (or whatever window you prefer)
        window_start = today_dt
        window_span = max(14, days_limit * 3)
        window_end = today_dt + timedelta(days=window_span)
        events = self.db_manager.get_events_for_period(
            _to_local_naive(window_start), _to_local_naive(window_end)
        )
        # events rows: (start_ts, end_ts, itemtype, subject, record_id)

        grouped_by_date = self.group_events_by_date_and_time(
            events
        )  # {date: [(time_key, (start_ts, end_ts, subject, record_id)), ...]}

        # 1) Determine the first N dates with events
        event_dates_sorted = sorted(grouped_by_date.keys())
        allowed_dates: list[date] = []
        for d in event_dates_sorted:
            allowed_dates.append(d)
            if len(allowed_dates) == days_limit:
                break

        # 2) If today has notice/draft items, include it even if it has no events
        has_today_meta = bool(notice_records or draft_records)
        if has_today_meta and today not in allowed_dates:
            # Prepend today; keep max three days
            allowed_dates = [today] + allowed_dates
            # De-dupe while preserving order
            seen = set()
            deduped = []
            for d in allowed_dates:
                if d not in seen:
                    seen.add(d)
                    deduped.append(d)
            allowed_dates = deduped[:days_limit]  # cap to configured limit

        # 3) If nothing at all to show, bail early
        nothing_to_show = (not allowed_dates) and (not has_today_meta)
        if nothing_to_show:
            return []

        # 4) Build events_by_date only for allowed dates
        events_by_date: dict[date, list[dict]] = {}

        for d in allowed_dates:
            entries = grouped_by_date.get(d, [])
            for _, (dt_id, start_ts, end_ts, subject, record_id, job_id) in entries:
                start_dt = datetime_from_timestamp(start_ts)
                if start_dt is not None:
                    subject = self.apply_anniversary_if_needed(
                        record_id, subject, start_dt
                    )
                subject = self.apply_flags(record_id, subject)
                raw_end_ts = end_ts
                effective_end_ts = raw_end_ts or start_ts
                is_all_day = is_all_day_text(start_ts, raw_end_ts)
                label = (
                    format_time_range(start_ts, effective_end_ts, self.AMPM).strip()
                    if not is_all_day
                    else ""
                )
                if is_all_day:
                    color = ALLDAY_COLOR
                elif effective_end_ts <= now_ts:
                    color = PASSED_EVENT
                elif start_ts <= now_ts:
                    color = ACTIVE_EVENT
                else:
                    color = EVENT_COLOR
                label_fmt = f"{label} " if label else ""
                events_by_date.setdefault(d, []).append(
                    {
                        "record_id": record_id,
                        "job_id": None,
                        "datetime_id": dt_id,
                        "instance_ts": start_ts,
                        "text": f"[{color}]{label_fmt}{subject}[/{color}]",
                    }
                )

        # 5) If TODAY is in allowed_dates (either because it had events or we added it)
        #    attach notice + draft markers even if it had no events
        if today in allowed_dates:
            if notice_records:
                for record_id, days_remaining, subject in notice_records:
                    events_by_date.setdefault(today, []).append(
                        {
                            "record_id": record_id,
                            "job_id": None,
                            "datetime_id": dt_id,
                            "instance_ts": start_ts,
                            "text": f"[{NOTICE_COLOR}]+{days_remaining}d {subject} [/{NOTICE_COLOR}]",
                        }
                    )
            if draft_records:
                for record_id, subject in draft_records:
                    events_by_date.setdefault(today, []).append(
                        {
                            "record_id": record_id,
                            "job_id": None,
                            "datetime_id": None,
                            "instance_ts": None,
                            "text": f"[{DRAFT_COLOR}] ? {subject}[/{DRAFT_COLOR}]",
                        }
                    )

        # 6) Tagging and indexing
        total_items = sum(len(v) for v in events_by_date.values())
        if total_items == 0:
            # Edge case: allowed_dates may exist but nothing actually added (shouldn’t happen, but safe-guard)
            return {}

        # self.set_afill(range(total_items), "events")
        # self.afill_by_view["events"] = self.afill
        # self.list_tag_to_id.setdefault("events", {})

        rows = []
        for d, events in sorted(events_by_date.items()):
            if events:
                rows.append(
                    {
                        "record_id": None,
                        "job_id": None,
                        "datetime_id": None,
                        "instance_ts": None,
                        "text": f"[not bold][{HEADER_COLOR}]{d.strftime('%a %b %-d')}[/{HEADER_COLOR}][/not bold]",
                    }
                )
                for event in events:
                    rows.append(event)

        return rows

    def get_agenda_tasks(self):
        """
        Returns rows suitable for the Agenda Tasks pane.

        Each row is a dict:
        {
            "record_id": int | None,
            "job_id": int | None,
            "datetime_id": int | None,
            "instance_ts": str | None,
            "text": str,
        }
        """
        tasks_by_urgency = []

        # Use the JOIN with Pinned so pins persist across restarts
        urgency_records = self.db_manager.get_urgency()
        # rows now:
        # (record_id, job_id, subject, urgency, color, status, weights,
        #  pinned_int, datetime_id, instance_ts)

        header = f"Tasks ({len(urgency_records)})"
        rows = [
            {
                "record_id": None,
                "job_id": None,
                "datetime_id": None,
                "instance_ts": None,
                "text": header,
            },
        ]

        for (
            record_id,
            job_id,
            subject,
            urgency,
            color,
            status,
            weights,
            pinned,
            datetime_id,
            instance_ts,
        ) in urgency_records:
            # urgency_str = (
            #     "📌" if pinned else f"[{color}]{int(round(urgency * 100)):>3}[/{color}]"
            # )
            urgency_str = "📌" if pinned else f"{round(100 * urgency):>3}"

            rows.append(
                {
                    "record_id": record_id,
                    "job_id": job_id,
                    "datetime_id": datetime_id,  # 👈 earliest DateTimes.id, or None
                    "instance_ts": instance_ts,  # 👈 earliest start_datetime TEXT, or None
                    "text": f"[{color}]{urgency_str}  {self.apply_flags(record_id, subject)}[/{color}]",
                }
            )

        return rows

    def get_entry_from_record(self, record_id: int) -> str:
        """
        Convenience wrapper that returns the formatted token summary for a record.

        Unlike ``get_entry`` this method does not touch jobs or completions—it
        simply loads ``tokens`` + formatting metadata from the database and
        feeds them through ``format_tokens`` for CLI display.
        """
        result = self.db_manager.get_tokens(record_id)
        tokens, rruleset, created, modified = result[0]
        entry = format_tokens(
            tokens,
            self.width,
            False,
            wrap_descriptions=False,
        )

        return entry

        if isinstance(tokens_value, str):
            try:
                tokens = json.loads(tokens_value)
            except Exception:
                # already a list or malformed — best effort
                pass
        if not isinstance(tokens, list):
            raise ValueError("Structured tokens not available/invalid for this record.")

        entry_str = "\n".join(tok.get("token", "") for tok in tokens)
        return entry_str

    def finish_from_details(
        self, record_id: int, job_id: int | None, completed_dt: datetime
    ) -> dict:
        """
        1) Load record -> Item
        2) Call item.finish_without_exdate(...)
        3) Persist Item
        4) Insert Completions row
        5) If fully finished, remove from Urgency/DateTimes
        6) Return summary dict
        """
        row = self.db_manager.get_record(record_id)
        if not row:
            raise ValueError(f"No record found for id {record_id}")

        # 0..16 schema like you described; 13 = tokens
        tokens_value = row[13]
        tokens = tokens_value
        if isinstance(tokens_value, str):
            try:
                tokens = json.loads(tokens_value)
            except Exception:
                # already a list or malformed — best effort
                pass
        if not isinstance(tokens, list):
            raise ValueError("Structured tokens not available/invalid for this record.")
        tokens = reveal_mask_tokens(tokens, self.mask_secret)

        entry_str = "".join(tok.get("token", "") for tok in tokens).strip()

        # Build/parse the Item
        # item = Item(entry_str)
        item = self.make_item(entry_str)
        if not getattr(item, "parse_ok", True):
            # Some Item versions set parse_ok/parse_message; if not, skip this guard.
            raise ValueError(getattr(item, "parse_message", "Item.parse failed"))

        # Remember subject fallback so we never null it on update
        existing_subject = row[2]
        if not item.subject:
            item.subject = existing_subject

        # 2) Let Item do all the schedule math (no EXDATE path as requested)
        fin = item.finish_without_exdate(
            completed_dt=completed_dt,
            record_id=record_id,
            job_id=job_id,
        )
        due_ts_used = getattr(fin, "due_ts_used", None)
        finished_final = getattr(fin, "finished_final", False)

        # 3) Persist the mutated Item
        self.db_manager.update_item(record_id, item)

        # 4) Insert completion (NULL due is allowed for one-shots)
        self.db_manager.insert_completion(
            record_id=record_id,
            due_ts=due_ts_used,
            completed_ts=int(completed_dt.timestamp()),
        )

        # 5) If final, purge from derived tables so it vanishes from lists
        if finished_final:
            try:
                self.db_manager.cursor.execute(
                    "DELETE FROM Urgency   WHERE record_id=?", (record_id,)
                )
                self.db_manager.cursor.execute(
                    "DELETE FROM DateTimes WHERE record_id=?", (record_id,)
                )
                self.db_manager.conn.commit()
            except Exception:
                pass

        # Optional: recompute derivations; DetailsScreen also calls refresh, but safe here
        try:
            self.db_manager.populate_dependent_tables()
        except Exception:
            pass

        return {
            "record_id": record_id,
            "final": finished_final,
            "due_ts": due_ts_used,
            "completed_ts": int(completed_dt.timestamp()),
            "new_rruleset": item.rruleset or "",
        }

    def get_bin_name(self, bin_id: int) -> str:
        return self.db_manager.get_bin_name(bin_id)

    def get_parent_bin(self, bin_id: int) -> dict | None:
        return self.db_manager.get_parent_bin(bin_id)

    def get_subbins(self, bin_id: int) -> list[dict]:
        return self.db_manager.get_subbins(bin_id)

        def get_record_details(self, record_id: int) -> str:
            """Fetch record details formatted for the details pane."""
            record = self.db_manager.get_record(record_id)
            if not record:
                return "[red]No details found[/red]"

            subject = record[2]
            desc = record[3] or ""
            itemtype = record[1]
            return f"[bold]{itemtype}[/bold]  {subject}\n\n{desc}"

    # controller.py (inside class Controller)

    # --- Backup helpers ---------------------------------------------------------
    def _db_path_from_self(self) -> Path:
        """
        Resolve the path of the live DB from Controller/DatabaseManager.
        Adjust the attribute names if yours differ.
        """
        # Common patterns; pick whichever exists in your DB manager:
        for attr in ("db_path", "database_path", "path"):
            p = getattr(self.db_manager, attr, None)
            if p:
                return Path(p)
        # Fallback if you also store it on the controller:
        if hasattr(self, "db_path"):
            return Path(self.db_path)
        raise RuntimeError(
            "Couldn't resolve database path from Controller / db_manager."
        )

    def _parse_backup_name(self, p: Path) -> Optional[date]:
        m = _BACKUP_RE.match(p.name)
        if not m:
            return None
        y, mth, d = map(int, m.groups())
        return date(y, mth, d)

    def _find_backups(self, dir_path: Path) -> List[_BackupInfo]:
        out: List[_BackupInfo] = []
        if not dir_path.exists():
            return out
        for p in dir_path.iterdir():
            if not p.is_file():
                continue
            d = self._parse_backup_name(p)
            if d is None:
                continue
            try:
                st = p.stat()
            except FileNotFoundError:
                continue
            out.append(_BackupInfo(path=p, day=d, mtime=st.st_mtime))
        out.sort(key=lambda bi: (bi.day, bi.mtime), reverse=True)
        return out

    def _should_snapshot(self, db_path: Path, backups: List[_BackupInfo]) -> bool:
        try:
            db_mtime = db_path.stat().st_mtime
        except FileNotFoundError:
            return False
        latest_backup_mtime = max((b.mtime for b in backups), default=0.0)
        return db_mtime > latest_backup_mtime

    def _select_retention(
        self, backups: List[_BackupInfo], today_local: date
    ) -> Set[Path]:
        """
        Bucket-based retention:
            - If there are 6 or fewer backups, keep them all.
            - Otherwise keep the oldest entry from each age bucket:
              0–3, 4–7, 8–14, 15–21, 22–42, 43–84 days old.
        """
        if not backups:
            return set()
        if len(backups) <= 6:
            return {b.path for b in backups}

        buckets: list[tuple[int, int]] = [
            (0, 3),
            (4, 7),
            (8, 14),
            (15, 21),
            (22, 42),
            (43, 84),
        ]
        keep: Set[Path] = set()
        bucket_assigned: dict[int, Path] = {}

        # Oldest first so we capture the oldest file in each bucket.
        oldest_first = sorted(backups, key=lambda b: (b.day, b.mtime))

        for backup in oldest_first:
            age_days = max(0, (today_local - backup.day).days)
            for idx, (low, high) in enumerate(buckets):
                if low <= age_days <= high:
                    if idx not in bucket_assigned:
                        bucket_assigned[idx] = backup.path
                        keep.add(backup.path)
                    break

        # Fallback: if every backup fell outside the defined buckets, keep the oldest overall.
        if not keep:
            keep.add(oldest_first[0].path)

        return keep

    # --- Public API --------------------------------------------------------------
    def rotate_daily_backups(self) -> None:
        # Where is the live DB?
        db_path: Path = Path(
            self.db_manager.db_path
        ).resolve()  # ensure DatabaseManager exposes .db_path
        backup_dir: Path = db_path.parent / "backups"
        backup_dir.mkdir(parents=True, exist_ok=True)

        # Example: name yesterday’s snapshot
        snap_date = date.today() - timedelta(days=1)
        target = backup_dir / f"{snap_date.isoformat()}.db"

        # Make the snapshot
        self.db_manager.backup_to(target)

        # …then your retention/pruning logic …
        tz = getattr(getattr(self, "env", None), "timezone", "America/New_York")
        tzinfo = ZoneInfo(tz)

        now = datetime.now(tzinfo)
        today = now.date()
        yesterday = today - timedelta(days=1)

        bdir = Path(backup_dir) if backup_dir else db_path.parent
        bdir.mkdir(parents=True, exist_ok=True)

        backups = self._find_backups(bdir)

        created: Optional[Path] = None
        if self._should_snapshot(db_path, backups):
            target = bdir / f"{yesterday.isoformat()}.db"
            self.db_manager.backup_to(target)
            created = target
            backups = self._find_backups(bdir)  # refresh

        keep = self._select_retention(backups, today_local=today)
        kept = sorted(keep)
        removed: List[Path] = []
        for b in backups:
            if b.path not in keep:
                removed.append(b.path)
                try:
                    b.path.unlink()
                except FileNotFoundError:
                    pass

        return created, kept, removed

    ###VVV new for tagged bin tree

    def get_root_bin_id(self) -> int:
        # Reuse your existing, tested anchor
        return self.db_manager.ensure_root_exists()

    def _make_crumb(self, bin_id: int | None):
        """Return [(id, name), ...] from root to current."""
        if bin_id is None:
            rid = self.db_manager.ensure_root_exists()
            return [(rid, "root")]
        # climb using your get_parent_bin
        chain = []
        cur = bin_id
        while cur is not None:
            name = self.db_manager.get_bin_name(cur)
            chain.append((cur, name))
            parent = self.db_manager.get_parent_bin(cur)  # {'id','name'} or None
            cur = parent["id"] if parent else None
        return list(reversed(chain)) or [(self.db_manager.ensure_root_exists(), "root")]

    def get_bin_summary(self, bin_id: int | None, *, filter_text: str | None = None):
        """
        Returns:
        children  -> [ChildBinRow]
        reminders -> [ReminderRow]
        crumb     -> [(id, name), ...]
        Uses ONLY DatabaseManager public methods.
        """
        # 1) children (uses your counts + sort)
        raw_children = self.db_manager.get_subbins(
            bin_id if bin_id is not None else self.get_root_bin_id()
        )
        # shape: {"id","name","subbins","reminders"}
        children = [
            ChildBinRow(
                bin_id=c["id"],
                name=c["name"],
                child_ct=c["subbins"],
                rem_ct=c["reminders"],
            )
            for c in raw_children
        ]

        # — Custom ordering of children based on config.bin_orders —
        root_name = self.get_bin_name(
            bin_id if bin_id is not None else self.get_root_bin_id()
        )
        order_list = self.env.config.bin_orders.get(root_name, [])
        if order_list:

            def _child_sort_key(c: ChildBinRow):
                try:
                    return (0, order_list.index(c.name))
                except ValueError:
                    return (1, c.name.lower())

            children.sort(key=_child_sort_key)
        else:
            children.sort(key=lambda c: c.name.lower())

        # 2) reminders (linked via ReminderLinks)
        raw_reminders = self.db_manager.get_reminders_in_bin(
            bin_id if bin_id is not None else self.get_root_bin_id()
        )

        reminders = [
            ReminderRow(
                record_id=r["id"],
                subject=self.apply_flags(r["id"], r["subject"]),
                # subject=r["subject"],
                itemtype=r["itemtype"],
            )
            for r in raw_reminders
        ]

        # 3) apply filter (controller-level; no new SQL)
        if filter_text:
            f = filter_text.casefold()
            children = [c for c in children if f in c.name.casefold()]
            reminders = [r for r in reminders if f in r.subject.casefold()]

        # 4) crumb
        crumb = self._make_crumb(
            bin_id if bin_id is not None else self.get_root_bin_id()
        )
        return children, reminders, crumb

    def get_descendant_tree(self, bin_id: int) -> list[tuple[int, str, int]]:
        """
        Return a pre-order flattened list of (bin_id, name, depth)
        for the bins-only subtree rooted at `bin_id`.
        Uses DatabaseManager.get_subbins(), but applies custom sorting.
        """
        out: list[tuple[int, str, int]] = []
        bin_orders = self.env.config.bin_orders  # Adjust this to how you access config

        def walk(current_id: int, depth: int) -> None:
            root_name = self.db_manager.get_bin_name(current_id)
            order_list = self.env.config.bin_orders.get(root_name)
            sorted_children = self.db_manager.get_subbins(
                current_id, custom_order=order_list
            )

            for ch in sorted_children:
                out.append((ch["id"], ch["name"], depth + 1))
                walk(ch["id"], depth + 1)

        root_name = self.db_manager.get_bin_name(bin_id)
        out.append((bin_id, root_name, 0))
        walk(bin_id, 0)
        return out

    # ----- Bin mutations -----
    def find_bin_id_by_name(self, name: str) -> int | None:
        return self.db_manager.get_bin_id_by_name(name)

    def create_bin(self, name: str, parent_id: int | None) -> int:
        return self.db_manager.create_bin(name, parent_id)

    def rename_bin(self, bin_id: int, new_name: str) -> None:
        self.db_manager.rename_bin(bin_id, new_name)

    def move_bin_under(self, bin_id: int, new_parent_id: int) -> None:
        self.db_manager.move_bin_to_parent(bin_id, new_parent_id)

    def delete_bin(self, bin_id: int) -> str:
        """
        Delete a bin: purge it when empty, otherwise move it under 'unlinked'.

        Returns:
            'purged'   -> bin removed permanently (no children/reminders)
            'archived' -> bin moved under the 'unlinked' container
        """
        removed = self.db_manager.delete_bin_if_empty(bin_id)
        if removed:
            return "purged"
        self.db_manager.mark_bin_deleted(bin_id)
        return "archived"

    def is_protected_bin(self, bin_id: int) -> bool:
        return self.db_manager.is_system_bin(bin_id)

    def get_tag_groups(self) -> dict[str, list[dict]]:
        """
        Return a mapping: tag -> list of Records rows for that tag.
        """
        cur = self.db_manager.conn.cursor()
        cur.execute(
            """
            SELECT H.tag, R.*
            FROM Hashtags H
            JOIN Records R ON H.record_id = R.id
            ORDER BY H.tag, R.id
            """
        )

        columns = [col[0] for col in cur.description]
        tag_index = columns.index("tag")

        tag_groups: dict[str, list[dict]] = {}

        for row in cur.fetchall():
            row_dict = dict(zip(columns, row))
            tag = row_dict.pop("tag")
            tag_groups.setdefault(tag, []).append(row_dict)

        return tag_groups

    def get_tag_view(self):
        """
        Build paged rows for the Tag view.

        Returns:
            pages: list[list[dict]]  # from page_tagger
            header: str              # e.g. "Tags (N)"
        """
        tag_groups = self.get_tag_groups()

        rows: list[dict] = []

        # Sort tags alphabetically (you can tweak this later)
        for tag in sorted(tag_groups.keys(), key=str.lower):
            records = tag_groups[tag]
            if not records:
                continue

            # Header row for the tag
            rows.append(
                {
                    "record_id": None,
                    "job_id": None,
                    "text": f"[bold][{HEADER_COLOR}]#{tag}[/{HEADER_COLOR}][/bold]",
                }
            )

            # One row per record under this tag
            for rec in records:
                rid = rec["id"]
                subj = rec.get("subject") or ""
                itemtype = rec.get("itemtype", "")
                flags = rec.get("flags") or ""
                # subject + flags
                display = subj + flags
                type_color = TYPE_TO_COLOR.get(itemtype, "white")

                rows.append(
                    {
                        "record_id": rid,
                        "job_id": None,
                        "text": f"[{type_color}]{itemtype} {display}[/{type_color}]",
                    }
                )

        if not rows:
            header = "Hash Tags (0)"
            return (
                self._paginate(
                    [
                        {
                            "record_id": None,
                            "job_id": None,
                            "text": f"[{HEADER_COLOR}]No tags found[/{HEADER_COLOR}]",
                        }
                    ]
                ),
                header,
            )

        pages = self._paginate(rows)
        title = f"Hash Tags ({len(tag_groups)})"
        return pages, title
