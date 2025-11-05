from __future__ import annotations
from packaging.version import parse as parse_version
from importlib.metadata import version
from functools import lru_cache

# TODO: Keep the display part - the model part will be in model.py
from datetime import datetime, timedelta, date

# from logging import log
from sre_compile import dis
from rich.console import Console
from rich.table import Table
from rich.box import HEAVY_EDGE
from rich import style
from rich.columns import Columns
from rich.console import Group, group
from rich.panel import Panel
from rich.layout import Layout
from rich import print as rprint
import re
import inspect
from rich.theme import Theme
from rich import box
from rich.text import Text
from typing import List, Tuple, Optional, Dict, Any, Set
from bisect import bisect_left, bisect_right
from typing import Iterator

import string
import shutil
import subprocess
import shlex
import textwrap


import json
from typing import Literal
from .item import Item
from .model import DatabaseManager, UrgencyComputer
from .model import _fmt_naive, _to_local_naive
from .list_colors import css_named_colors

from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from zoneinfo import ZoneInfo

# import sqlite3
from .shared import (
    log_msg,
    HRS_MINS,
    # ALERT_COMMANDS,
    dt_as_utc_timestamp,
    format_time_range,
    format_timedelta,
    datetime_from_timestamp,
    format_datetime,
    datetime_in_words,
    truncate_string,
    parse,
    fmt_local_compact,
    parse_local_compact,
    fmt_utc_z,
    parse_utc_z,
    get_version,
)
from tklr.tklr_env import TklrEnvironment


VERSION = get_version()

ISO_Z = "%Y%m%dT%H%MZ"

type_color = css_named_colors["goldenrod"]
at_color = css_named_colors["goldenrod"]
am_color = css_named_colors["goldenrod"]
# type_color = css_named_colors["burlywood"]
# at_color = css_named_colors["burlywood"]
# am_color = css_named_colors["burlywood"]
label_color = css_named_colors["lightskyblue"]

# The overall background color of the app is #2e2e2e - set in view_textual.css
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
HEADER_COLOR = LIGHT_SKY_BLUE
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
HEADER_STYLE = f"bold {LEMON_CHIFFON}"
FIELD_COLOR = LIGHT_SKY_BLUE

ONEDAY = timedelta(days=1)
ONEWK = 7 * ONEDAY
alpha = [x for x in string.ascii_lowercase]

TYPE_TO_COLOR = {
    "*": EVENT_COLOR,  # event
    "~": AVAILABLE_COLOR,  # available task
    "x": FINISHED_COLOR,  # finished task
    "^": AVAILABLE_COLOR,  # available task
    "+": WAITING_COLOR,  # waiting task
    "%": NOTE_COLOR,  # note
    "<": PASTDUE_COLOR,  # past due task
    ">": NOTICE_COLOR,  # begin
    "!": GOAL_COLOR,  # draft
    "?": DRAFT_COLOR,  # draft
}


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


# Stop at end-of-line or the start of another token-ish thing (@, &, +, %, - ...)
RE_BIN = re.compile(r"@b\s+([^\s].*?)\s*(?=$|[@&+%-])", re.IGNORECASE)


def extract_bin_slashpath(line: str) -> str | None:
    """
    Example:
      "Pick up pastry @b Lille\\France\\places @t 9a" -> "Lille\\France\\places"
    """
    m = RE_BIN.search(line or "")
    return m.group(1) if m else None


def format_tokens(tokens, width, highlight=True):
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
        if ttype == "@" and k == "d":
            if current_line:
                output_lines.append(current_line)
                current_line = ""
            # output_lines.append("")
            for line in token_text.splitlines():
                indent = len(line) - len(line.lstrip(" "))
                wrapped = textwrap.wrap(
                    line, width=width, subsequent_indent=" " * indent
                ) or [""]
                output_lines.extend(wrapped)
            # output_lines.append("")
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
    log_msg(f"{out = }")
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


def format_date_range(start_dt: datetime, end_dt: datetime):
    """
    Format a datetime object as a week string, taking not to repeat the month subject unless the week spans two months.
    """
    same_year = start_dt.year == end_dt.year
    same_month = start_dt.month == end_dt.month
    # same_day = start_dt.day == end_dt.day
    if same_year and same_month:
        return f"{start_dt.strftime('%b %-d')} - {end_dt.strftime('%-d, %Y')}"
    elif same_year and not same_month:
        return f"{start_dt.strftime('%b %-d')} - {end_dt.strftime('%b %-d, %Y')}"
    else:
        return f"{start_dt.strftime('%b %-d, %Y')} - {end_dt.strftime('%b %-d, %Y')}"


def format_iso_week(monday_date: datetime):
    start_dt = monday_date.date()
    end_dt = start_dt + timedelta(days=6)
    iso_yr, iso_wk, _ = start_dt.isocalendar()
    yr_wk = f"{iso_yr} #{iso_wk}"
    same_month = start_dt.month == end_dt.month
    # same_day = start_dt.day == end_dt.day
    if same_month:
        return f"{start_dt.strftime('%b %-d')} - {end_dt.strftime('%-d')}, {yr_wk}"
    else:
        return f"{start_dt.strftime('%b %-d')} - {end_dt.strftime('%b %-d')}, {yr_wk}"


def get_previous_yrwk(year, week):
    """
    Get the previous (year, week) from an ISO calendar (year, week).
    """
    # Convert the ISO year and week to a Monday date
    monday_date = datetime.strptime(f"{year} {week} 1", "%G %V %u")
    # Subtract 1 week
    previous_monday = monday_date - timedelta(weeks=1)
    # Get the ISO year and week of the new date
    return previous_monday.isocalendar()[:2]


def get_next_yrwk(year, week):
    """
    Get the next (year, week) from an ISO calendar (year, week).
    """
    # Convert the ISO year and week to a Monday date
    monday_date = datetime.strptime(f"{year} {week} 1", "%G %V %u")
    # Add 1 week
    next_monday = monday_date + timedelta(weeks=1)
    # Get the ISO year and week of the new date
    return next_monday.isocalendar()[:2]


def calculate_4_week_start():
    """
    Calculate the starting date of the 4-week period, starting on a Monday.
    """
    today = datetime.now()
    iso_year, iso_week, iso_weekday = today.isocalendar()
    start_of_week = today - timedelta(days=iso_weekday - 1)
    weeks_into_cycle = (iso_week - 1) % 4
    return start_of_week - timedelta(weeks=weeks_into_cycle)


def decimal_to_base26(decimal_num):
    """
    Convert a decimal number to its equivalent base-26 string.

    Args:
        decimal_num (int): The decimal number to convert.

    Returns:
        str: The base-26 representation where 'a' = 0, 'b' = 1, ..., 'z' = 25.
    """
    if decimal_num < 0:
        raise ValueError("Decimal number must be non-negative.")

    if decimal_num == 0:
        return "a"  # Special case for zero

    base26 = ""
    while decimal_num > 0:
        digit = decimal_num % 26
        base26 = chr(digit + ord("a")) + base26  # Map digit to 'a'-'z'
        decimal_num //= 26

    return base26


def base26_to_decimal(tag: str) -> int:
    """Decode 'a'..'z' (a=0) for any length."""
    total = 0
    for ch in tag:
        total = total * 26 + (ord(ch) - ord("a"))
    return total


def indx_to_tag(indx: int, fill: int = 1):
    """
    Convert an index to a base-26 tag.
    """
    return decimal_to_base26(indx).rjust(fill, "a")


def event_tuple_to_minutes(start_dt: datetime, end_dt: datetime) -> Tuple[int, int]:
    """
    Convert event start and end datetimes to minutes since midnight.

    Args:
        start_dt (datetime): Event start datetime.
        end_dt (datetime): Event end datetime.

    Returns:
        Tuple(int, int): Tuple of start and end minutes since midnight.
    """
    start_minutes = start_dt.hour * 60 + start_dt.minute
    end_minutes = end_dt.hour * 60 + end_dt.minute if end_dt else start_minutes
    return (start_minutes, end_minutes)


def get_busy_bar(events):
    """
    Determine slot states (0: free, 1: busy, 2: conflict) for a list of events.

    Args:
        L (List[int]): Sorted list of slot boundaries.
        events (List[Tuple[int, int]]): List of event tuples (start, end).

    Returns:
        List[int]: A list where 0 indicates a free slot, 1 indicates a busy slot,
                and 2 indicates a conflicting slot.
    """
    # Initialize slot usage as empty lists
    L = SLOT_MINUTES
    slot_events = [[] for _ in range(len(L) - 1)]
    allday = 0

    for b, e in events:
        # Find the start and end slots for the current event

        if b == 0 and e == 0:
            allday += 1
        if e == b and not allday:
            continue

        start_slot = bisect_left(L, b) - 1
        end_slot = bisect_left(L, e) - 1

        # Track the event in each affected slot
        for i in range(start_slot, min(len(slot_events), end_slot + 1)):
            if L[i + 1] > b and L[i] < e:  # Ensure overlap with the slot
                slot_events[i].append((b, e))

    # Determine the state of each slot
    slots_state = []
    for i, events_in_slot in enumerate(slot_events):
        if not events_in_slot:
            # No events in the slot
            slots_state.append(0)
        elif len(events_in_slot) == 1:
            # Only one event in the slot, so it's busy but not conflicting
            slots_state.append(1)
        else:
            # Check for overlaps to determine if there's a conflict
            events_in_slot.sort()  # Sort events by start time
            conflict = False
            for j in range(len(events_in_slot) - 1):
                _, end1 = events_in_slot[j]
                start2, _ = events_in_slot[j + 1]
                if start2 < end1:  # Overlap detected
                    conflict = True
                    break
            slots_state.append(2 if conflict else 1)

    busy_bar = ["_" for _ in range(len(slots_state))]
    have_busy = False
    for i in range(len(slots_state)):
        if slots_state[i] == 0:
            busy_bar[i] = f"[dim]{FREE}[/dim]"
        elif slots_state[i] == 1:
            have_busy = True
            busy_bar[i] = f"[{BUSY_COLOR}]{BUSY}[/{BUSY_COLOR}]"
        else:
            have_busy = True
            busy_bar[i] = f"[{CONF_COLOR}]{BUSY}[/{CONF_COLOR}]"

    # return slots_state, "".join(busy_bar)
    busy_str = (
        f"\n[{BUSY_FRAME_COLOR}]{''.join(busy_bar)}[/{BUSY_FRAME_COLOR}]"
        if have_busy
        else "\n"
    )

    aday_str = f"[{BUSY_COLOR}]{ADAY}[/{BUSY_COLOR}]" if allday > 0 else ""

    return aday_str, busy_str


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
    log_msg(f"set_anniversary {subject = }, {has_xxx = }")
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
    log_msg(f"{subject = }, {new_subject = }")
    return new_subject


# A page is (rows, tag_map)
# rows: list[str] ready to render (header + content)
# tag_map: { 'a': ('bin', bin_id) | ('reminder', (record_id, job_id)) }
Page = Tuple[List[str], Dict[str, Tuple[str, object]]]


def page_tagger(
    items: List[dict], page_size: int = 26
) -> List[Tuple[List[str], Dict[str, Tuple[int, int | None]]]]:
    """
    Split 'items' into pages. Each item is a dict:
        { "record_id": int | None, "job_id": int | None, "text": str }

    Returns a list of pages. Each page is a tuple:
        (page_rows: list[str], page_tag_map: dict[str -> (record_id, job_id|None)])

    Rules:
      - Only record rows (record_id != None) receive single-letter tags 'a'..'z'.
      - Exactly `page_size` records are tagged per page (except the last page).
      - Headers (record_id is None) are kept in order.
      - If a header's block of records spans pages, the header is duplicated at the
        start of the next page with " (continued)" appended.
    """
    pages: List[Tuple[List[str], Dict[str, Tuple[int, int | None]]]] = []

    page_rows: List[str] = []
    tag_map: Dict[str, Tuple[int, int | None]] = {}
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
        # header row
        if not isinstance(item, dict):
            log_msg(f"error: {item} is not a dict")
            continue
        if item.get("record_id") is None:
            hdr_text = item.get("text", "")
            last_header_text = hdr_text
            page_rows.append(hdr_text)
            # continue; headers do not affect tag_counter
            continue

        # record row (taggable)
        # If current page is already full (page_size tags), start a new page.
        # IMPORTANT: when we create the new page, we want to preseed it with a
        # duplicated header (if one exists) and mark it as "(continued)".
        if tag_counter >= page_size:
            # If we have a last_header_text, duplicate it at top of next page with continued.
            if last_header_text:
                continued_header = f"{last_header_text} (continued)"
                finalize_page(new_page_rows=[continued_header])
            else:
                finalize_page()

        # assign next tag on current page
        tag = chr(ord("a") + tag_counter)
        tag_map[tag] = (item["record_id"], item.get("job_id", None))
        # Use small/dim tag formatting to match your UI style; adapt if needed
        page_rows.append(f" [dim]{tag}[/dim]  {item.get('text', '')}")
        tag_counter += 1

    # At end, still need to push the last page if it has any rows
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
    def __init__(self, database_path: str, env: TklrEnvironment, reset: bool = False):
        # Initialize the database manager
        self.db_manager = DatabaseManager(database_path, env, reset=reset)

        self.tag_to_id = {}  # Maps tag numbers to event IDs
        self.list_tag_to_id: dict[str, dict[str, object]] = {}

        self.yrwk_to_pages = {}  # Maps (iso_year, iso_week) to week description
        self.rownum_to_yrwk = {}  # Maps row numbers to (iso_year, iso_week)
        self.start_date = calculate_4_week_start()
        self.selected_week = tuple(datetime.now().isocalendar()[:2])
        self.env = env
        self.AMPM = env.config.ui.ampm
        self._last_details_meta = None
        self.afill_by_view: dict[str, int] = {}  # e.g. {"events": 1, "tasks": 2}
        self.afill_by_week: dict[Tuple[int, int], int] = {}

        for view in ["next", "last", "find", "events", "tasks", "alerts"]:
            self.list_tag_to_id.setdefault(view, {})
        self.week_tag_to_id: dict[Tuple[int, int], dict[str, object]] = {}
        self.width = shutil.get_terminal_size()[0] - 2
        self.afill = 1
        self._agenda_dirty = False

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

    def make_item(self, entry_str: str, final: bool = False) -> "Item":
        return Item(entry_str, final=final)  # or config=self.env.load_config()

    def add_item(self, item: Item) -> int:
        if item.itemtype in "~^x" and item.has_f:
            log_msg(
                f"{item.itemtype = } {item.has_f = } {item.itemtype in '~^' and item.has_f = }"
            )

        record_id = self.db_manager.add_item(item)

        if item.completion:
            completed_dt, due_dt = item.completion
            # completed_ts = dt_as_utc_timestamp(completed_dt)
            # due_ts = dt_as_utc_timestamp(due_dt) if due_dt else None
            completion = (completed_dt, due_dt)
            self.db_manager.add_completion(record_id, completion)

        return record_id

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

    # def get_tag_iterator(self, view: str, count: int) -> Iterator[str]:
    #     """
    #     Return an iterator over tags (a, b, ..., z, aa, ab, ..., aaa, ...),
    #     consistent with existing set_afill() and add_tag() logic.
    #     """
    #     # determine tag width for this view
    #     self.set_afill([None] * count, view)
    #     fill = self.afill_by_view[view]
    #
    #     for i in range(count):
    #         yield indx_to_tag(i, fill)

    def get_name_to_binpath(self) -> Dict[str, str]:
        # leaf_lower -> "Leaf/Parent/.../Root"
        return self.db_manager.bin_cache.name_to_binpath()

    def get_tag_iterator(self, view: str, count: int) -> Iterator[str]:
        if view not in self.afill_by_view:
            self.set_afill([None] * count, view)
        fill = self.afill_by_view[view]
        for i in range(count):
            yield indx_to_tag(i, fill)

    # --- replace your set_afill with this per-view version ---
    def set_afill(self, details: list, view: str):
        n = len(details)
        fill = 1 if n <= 26 else 2 if n <= 26 * 26 else 3
        log_msg(f"{view = }, {n = }, {fill = }, {details = }")
        self.afill_by_view[view] = fill

    def add_tag(
        self, view: str, indx: int, record_id: int, *, job_id: int | None = None
    ):
        """Produce the next tag (with the pre-chosen width) and register it."""
        fill = self.afill_by_view[view]
        tag = indx_to_tag(indx, fill)  # uses your existing function
        tag_fmt = f" [dim]{tag}[/dim] "
        self.list_tag_to_id.setdefault(view, {})[tag] = {
            "record_id": record_id,
            "job_id": job_id,
        }
        return tag_fmt, indx + 1

    def set_week_afill(self, details: list, yr_wk: Tuple[int, int]):
        n = len(details)
        fill = 1 if n <= 26 else 2 if n <= 26 * 26 else 3
        log_msg(f"{yr_wk = }, {n = }, {fill = }")
        self.afill_by_week[yr_wk] = fill

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
        tag_fmt = f" [dim]{tag}[/dim] "
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

    def get_entry(self, record_id, job_id=None):
        lines = []
        result = self.db_manager.get_tokens(record_id)
        # log_msg(f"{result = }")

        tokens, rruleset, created, modified = result[0]

        entry = format_tokens(tokens, self.width)
        entry = f"[bold {type_color}]{entry[0]}[/bold {type_color}]{entry[1:]}"

        log_msg(f"{rruleset = }")
        # rruleset = f"\n{11 * ' '}".join(rruleset.splitlines())

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
    ):
        """
        Return list: [title, '', ... lines ...] same as process_tag would.
        Use the same internal logic as process_tag but accept ids directly.
        """
        # If you have a general helper that returns fields for a record, reuse it.
        # Here we replicate the important parts used by process_tag()
        core = self.get_record_core(record_id) or {}
        itemtype = core.get("itemtype") or ""
        rruleset = core.get("rruleset") or ""
        all_prereqs = core.get("all_prereqs") or ""

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
        ] + self.get_entry(record_id, job_id)

        _dts = self.db_manager.get_next_start_datetimes_for_record(record_id)
        first, second = (_dts + [None, None])[:2]

        title = f"[bold]{subject:^{self.width}}[/bold]"

        meta = {
            "record_id": record_id,
            "job_id": job_id,
            "itemtype": itemtype,
            "subject": subject,
            "rruleset": rruleset,
            "first": first,
            "second": second,
            "all_prereqs": all_prereqs,
            "pinned": bool(pinned_now),
            "record": self.db_manager.get_record(record_id),
        }
        self._last_details_meta = meta

        # return [title, ""] + fields
        return title, fields, meta

    def get_record(self, record_id):
        return self.db_manager.get_record(record_id)

    def get_all_records(self):
        return self.db_manager.get_all()

    def delete_record(self, record_id):
        self.db_manager.delete_record(record_id)

    def update_tags(self, record_data):
        return self.db_manager.update_record_with_tags(record_data)

    def get_tags(self, record_id):
        return self.db_manager.get_tags_for_record(record_id)

    def get_tagged_records(self, tag):
        return self.db_manager.get_tagged(tag)

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
                record_name,
                trigger_datetime,
                start_datetime,
                alert_command,
            ) = record
            log_msg(f"Executing alert {alert_command = }, {trigger_datetime = }")
            self.execute_alert(alert_command)
            # need command to execute command with arguments
            self.db_manager.mark_alert_executed(alert_id)

    def get_active_alerts(self, width: int = 70):
        # now_fmt = datetime.now().strftime("%A, %B %-d %H:%M:%S")
        alerts = self.db_manager.get_active_alerts()
        header = "Remaining alerts for today"
        results = [header]
        if not alerts:
            results.append(f" [{HEADER_COLOR}]none scheduled[/{HEADER_COLOR}]")
            return results
        now = datetime.now()

        table = Table(title="Remaining alerts for today", expand=True, box=HEAVY_EDGE)
        table.add_column("row", justify="center", width=3, style="dim")
        table.add_column("cmd", justify="center", width=3)
        table.add_column("time", justify="left", width=24)
        table.add_column("subject", width=25, overflow="ellipsis", no_wrap=True)

        # 4*2 + 2*3 + 7 + 14 = 35 => subject width = width - 35
        trigger_width = 7 if self.AMPM else 8
        start_width = 7 if self.AMPM else 6
        alert_width = trigger_width + 3
        name_width = width - 35
        results.append(
            # f"[bold][dim]{'tag':^3}[/dim]  {'  alert         @s ':^{alert_width}}     {'subject':<{name_width}}[/bold]",
            f"[bold][dim]{'tag':^3}[/dim]  {'alert':^{alert_width}}  {'@s':^{start_width}}   {'subject':<{name_width}}[/bold]",
        )

        self.list_tag_to_id.setdefault("alerts", {})
        # self.afill = 1 if len(alerts) <= 26 else 2 if len(alerts) <= 676 else 3
        # self.set_afill(alerts, "get_active_alerts")
        # indx = 0
        # tag = indx_to_tag(indx, self.afill)

        self.set_afill(alerts, "alerts")
        indx = 0
        self.list_tag_to_id.setdefault("alerts", {})

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
                continue
            tag_fmt, indx = self.add_tag("alerts", indx, record_id)
            trtime = self.format_datetime(trigger_datetime)
            sttime = self.format_datetime(start_datetime)
            subject = truncate_string(record_name, name_width)
            row = "  ".join(
                [
                    f"{tag_fmt}",
                    f"[{SALMON}] {alert_name} {trtime:<{trigger_width}}[/{SALMON}][{PALE_GREEN}] → {sttime:<{start_width}}[/{PALE_GREEN}]",
                    f"[{AVAILABLE_COLOR}]{subject:<{name_width}}[/{AVAILABLE_COLOR}]",
                ]
            )
            results.append(row)
        return results

    def process_tag(self, tag: str, view: str, selected_week: tuple[int, int]):
        job_id = None
        if view == "week":
            payload = None
            tags_for_week = self.week_tag_to_id.get(selected_week, None)
            payload = tags_for_week.get(tag, None) if tags_for_week else None
            if payload is None:
                return [f"There is no item corresponding to tag '{tag}'."]
            if isinstance(payload, dict):
                record_id = payload.get("record_id")
                job_id = payload.get("job_id")
            else:
                record_id, job_id = payload, None

        elif view in [
            "next",
            "last",
            "find",
            "events",
            "tasks",
            "agenda-events",
            "agenda-tasks",
            "alerts",
        ]:
            payload = self.list_tag_to_id.get(view, {}).get(tag)
            if payload is None:
                return [f"There is no item corresponding to tag '{tag}'."]
            if isinstance(payload, dict):
                record_id = payload.get("record_id")
                job_id = payload.get("job_id")
            else:
                record_id, job_id = payload, None
        else:
            return ["Invalid view."]

        core = self.get_record_core(record_id) or {}
        itemtype = core.get("itemtype") or ""
        rruleset = core.get("rruleset") or ""
        all_prereqs = core.get("all_prereqs") or ""

        # ----- subject selection -----
        # default to record subject
        subject = core.get("subject") or "(untitled)"
        # if we're in week view and this tag points to a job, prefer the job's display_subject
        # if view == "week" and job_id is not None:
        if job_id is not None:
            log_msg(f"setting subject for {record_id = }, {job_id = }")
            try:
                js = self.db_manager.get_job_display_subject(record_id, job_id)
                if js:  # only override if present/non-empty
                    subject = js
            except Exception as e:
                # fail-safe: keep the record subject
                log_msg(f"Error: {e}. Failed for {record_id = }, {job_id = }")
        # -----------------------------

        try:
            pinned_now = (
                self.db_manager.is_task_pinned(record_id) if itemtype == "~" else False
            )
        except Exception:
            pinned_now = False

        fields = [
            "",
        ] + self.get_entry(record_id, job_id)

        _dts = self.db_manager.get_next_start_datetimes_for_record(record_id, job_id)
        first, second = (_dts + [None, None])[:2]
        log_msg(f"{record_id = }, {job_id = }, {_dts = }, {first = }, {second = }")

        # job_suffix = (
        #     f" [{label_color}]job_id:[/{label_color}] [bold]{job_id}[/bold]"
        #     if job_id is not None
        #     else ""
        # )
        # title = f"[{label_color}]details:[/{label_color}] [bold]{subject}[/bold]"
        title = f"[bold]{subject:^{self.width}}[/bold]"
        # ids = f"[{label_color}]id:[/{label_color}] [bold]{record_id}[/bold]{job_suffix}"

        # side-channel meta for detail actions
        self._last_details_meta = {
            "record_id": record_id,
            "job_id": job_id,
            "itemtype": itemtype,
            "subject": subject,
            "rruleset": rruleset,
            "first": first,
            "second": second,
            "all_prereqs": all_prereqs,
            "pinned": bool(pinned_now),
            "record": self.db_manager.get_record(record_id),
        }

        return [
            title,
            " ",
        ] + fields

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
        except Exception as e:
            log_msg(f"[weeks] ensure_week_generated_with_topup error: {e}")

        year_week = f"{year:04d}-{week:02d}"
        busy_bits = self.db_manager.get_busy_bits_for_week(year_week)
        busy_bar = self._format_busy_bar(busy_bits)

        start_dt = datetime.strptime(f"{year} {week} 1", "%G %V %u")
        # end_dt = start_dt + timedelta(weeks=1)
        details = self.get_week_details(selected_week)

        title = format_iso_week(start_dt)
        return title, busy_bar, details

    # def get_table_and_list(self, start_date: datetime, selected_week: tuple[int, int]):
    #     """
    #     Return the header title, busy bar (as text), and event list details
    #     for the given ISO week.
    #
    #     Returns: (title, busy_bar_str, details_list)
    #     """
    #     year, week = selected_week
    #     year_week = f"{year:04d}-{week:02d}"
    #
    #     # --- 1. Busy bits from BusyWeeks table
    #     busy_bits = self.db_manager.get_busy_bits_for_week(year_week)
    #     busy_bar = self._format_busy_bar(busy_bits)
    #
    #     # --- 2. Week events using your existing method
    #     start_dt = datetime.strptime(f"{year} {week} 1", "%G %V %u")
    #     end_dt = start_dt + timedelta(weeks=1)
    #     details = self.get_week_details(selected_week)
    #
    #     # title = f"{format_date_range(start_dt, end_dt)} #{start_dt.isocalendar().week}"
    #     title = format_iso_week(start_dt)
    #     # --- 3. Title for the week header
    #     # title = f"Week {week} — {start_dt.strftime('%b %d')} to {(end_dt - timedelta(days=1)).strftime('%b %d')}"
    #
    #     return title, busy_bar, details

    def _format_busy_bar(
        self,
        bits: list[int],
        *,
        busy_color: str = "green",
        conflict_color: str = "red",
        allday_color: str = "yellow",
    ) -> str:
        """
        Render 35 busy bits (7×[1 all-day + 4×6h blocks])
        as a compact single-row week bar with color markup.

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

        # --- Header line
        header = "│".join(f" {d:^3} " for d in DAYS)
        lines = [f"│{header}│"]

        # --- Busy row
        day_segments = []
        for day in range(7):
            start = day * 5
            all_day_bit = bits[start]
            block_bits = bits[start + 1 : start + 5]

            # --- all-day symbol
            if all_day_bit:
                all_day_char = f"[{allday_color}]■[/{allday_color}]"
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

        lines.append(f"│{'│'.join(day_segments)}│")
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

        self.set_week_afill(events, yr_wk)

        if not events:
            rows.append(
                {
                    "record_id": None,
                    "job_id": None,
                    "text": f" [{HEADER_COLOR}]Nothing scheduled for this week[/{HEADER_COLOR}]",
                }
            )
            pages = page_tagger(rows)
            return pages

        weekday_to_events = {}
        for i in range(7):
            this_day = (start_datetime + timedelta(days=i)).date()
            weekday_to_events[this_day] = []

        for start_ts, end_ts, itemtype, subject, id, job_id in events:
            log_msg(f"{itemtype = }, {subject = }, {id = }, {job_id = }")
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

            row = {
                "record_id": id,
                "job_id": job_id,
                "text": f"[{type_color}]{itemtype} {escaped_start_end}{subject}[/{type_color}]",
            }
            weekday_to_events.setdefault(start_dt.date(), []).append(row)
            log_msg(f"job row: {row = }")

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
                        "text": f"[bold][{HEADER_COLOR}]{day.strftime('%a, %b %-d')}{flag}[/{HEADER_COLOR}][/bold]",
                    }
                )
                for event in events:
                    rows.append(event)
        pages = page_tagger(rows)
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
        # description = [f"[not bold][{header_color}]{header}[/{header_color}][/not bold]"]

        if not events:
            return [], header

        year_to_events = {}

        for id, job_id, subject, description, itemtype, start_ts in events:
            start_dt = datetime_from_timestamp(start_ts)
            subject = self.apply_anniversary_if_needed(id, subject, start_dt)
            if job_id is not None:
                try:
                    js = self.db_manager.get_job_display_subject(id, job_id)
                    if js:  # only override if present/non-empty
                        subject = js
                    # log_msg(f"{subject = }")
                except Exception as e:
                    # fail-safe: keep the record subject
                    log_msg(f"{e = }")
                    pass
            monthday = start_dt.strftime("%-d")
            start_end = f"{monthday:>2} {format_hours_mins(start_dt, HRS_MINS)}"
            type_color = TYPE_TO_COLOR[itemtype]
            escaped_start_end = f"[not bold]{start_end}[/not bold]"
            item = {
                "record_id": id,
                "job_id": job_id,
                "text": f"[{type_color}]{itemtype} {escaped_start_end} {subject}[/{type_color}]",
            }
            # yr_mnth_to_events.setdefault(start_dt.strftime("%B %Y"), []).append(row)
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
                        "record_id": None,
                        "job_id": None,
                        "text": f"[not bold][{HEADER_COLOR}]{ym}[/{HEADER_COLOR}][/not bold]",
                    }
                )
                for event in events:
                    rows.append(event)

        # build 'rows' as a list of dicts with record_id and text
        pages = page_tagger(rows)
        log_msg(f"{pages = }")
        return pages, header

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

        for id, job_id, subject, description, itemtype, start_ts in events:
            start_dt = datetime_from_timestamp(start_ts)
            subject = self.apply_anniversary_if_needed(id, subject, start_dt)
            # log_msg(f"Week description {subject = }, {start_dt = }, {end_dt = }")
            if job_id is not None:
                try:
                    js = self.db_manager.get_job_display_subject(id, job_id)
                    if js:  # only override if present/non-empty
                        subject = js
                    log_msg(f"{subject = }")
                except Exception as e:
                    # fail-safe: keep the record subject
                    log_msg(f"{e = }")
                    pass
            monthday = start_dt.strftime("%-d")
            start_end = f"{monthday:>2} {format_hours_mins(start_dt, HRS_MINS)}"
            type_color = TYPE_TO_COLOR[itemtype]
            escaped_start_end = f"[not bold]{start_end}[/not bold]"
            item = {
                "record_id": id,
                "job_id": job_id,
                "text": f"[{type_color}]{itemtype} {escaped_start_end} {subject}[/{type_color}]",
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
        pages = page_tagger(rows)
        log_msg(f"{pages = }")
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
        pages = page_tagger(rows)
        log_msg(f"{pages = }")
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

        for start_ts, end_ts, itemtype, subject, record_id, job_id in events:
            # log_msg(f"{start_ts = }, {end_ts = }, {subject = }")
            if itemtype != "*":
                continue  # Only events

            start_dt = datetime_from_timestamp(start_ts)
            grouped[start_dt.date()].append(
                (start_dt.time(), (start_ts, end_ts, subject, record_id, job_id))
            )

        # Sort each day's events by time
        for date in grouped:
            grouped[date].sort(key=lambda x: x[0])

        return dict(grouped)

    def get_completions_view(self):
        """
        Fetch and format description for all completions, grouped by year.
        """
        events = self.db_manager.get_all_completions()
        header = f"Completions ({len(events)})"
        display = [header]

        if not events:
            display.append(f" [{HEADER_COLOR}]Nothing found[/{HEADER_COLOR}]")
            return display

        year_to_events = {}
        for record_id, subject, description, itemtype, due_ts, completed_ts in events:
            completed_dt = datetime_from_timestamp(completed_ts)
            due_dt = datetime_from_timestamp(due_ts) if due_ts else None

            # Format display string
            monthday = completed_dt.strftime("%m-%d")
            completed_str = f"{monthday}{format_hours_mins(completed_dt, HRS_MINS):>8}"
            type_color = TYPE_TO_COLOR[itemtype]
            escaped_completed = f"[not bold]{completed_str}[/not bold]"

            extra = f" (due {due_dt.strftime('%m-%d')})" if due_dt else ""
            row = [
                record_id,
                None,  # no job_id for completions
                f"[{type_color}]{itemtype} {escaped_completed:<12}  {subject}{extra}[/{type_color}]",
            ]

            year_to_events.setdefault(completed_dt.strftime("%Y"), []).append(row)

        self.set_afill(events, "completions")
        self.list_tag_to_id.setdefault("completions", {})

        indx = 0
        for year, events in year_to_events.items():
            if events:
                display.append(
                    f"[not bold][{HEADER_COLOR}]{year}[/{HEADER_COLOR}][/not bold]"
                )
                for event in events:
                    record_id, job_id, event_str = event
                    tag_fmt, indx = self.add_tag(
                        "completions", indx, record_id, job_id=job_id
                    )
                    display.append(f"{tag_fmt}{event_str}")

        return display

    def get_record_completions(self, record_id: int, width: int = 70):
        """
        Fetch and format completion history for a given record.
        """
        completions = self.db_manager.get_completions(record_id)
        header = "Completion history"
        results = [header]

        if not completions:
            results.append(f" [{HEADER_COLOR}]no completions recorded[/{HEADER_COLOR}]")
            return results

        # Column widths similar to alerts
        completed_width = 14  # space for "YYYY-MM-DD HH:MM"
        due_width = 14
        name_width = width - (3 + 3 + completed_width + due_width + 6)

        results.append(
            f"[bold][dim]{'tag':^3}[/dim]  "
            f"{'completed':^{completed_width}}  "
            f"{'due':^{due_width}}   "
            f"{'subject':<{name_width}}[/bold]"
        )

        self.set_afill(completions, "record_completions")
        self.list_tag_to_id.setdefault("record_completions", {})
        indx = 0

        for (
            record_id,
            subject,
            description,
            itemtype,
            due_ts,
            completed_ts,
        ) in completions:
            completed_dt = datetime_from_timestamp(completed_ts)
            completed_str = self.format_datetime(completed_dt, short=True)

            due_str = (
                self.format_datetime(datetime_from_timestamp(due_ts), short=True)
                if due_ts
                else "-"
            )
            subj_fmt = truncate_string(subject, name_width)

            tag_fmt, indx = self.add_tag("record_completions", indx, record_id)

            row = "  ".join(
                [
                    f"{tag_fmt}",
                    f"[{SALMON}]{completed_str:<{completed_width}}[/{SALMON}]",
                    f"[{PALE_GREEN}]{due_str:<{due_width}}[/{PALE_GREEN}]",
                    f"[{AVAILABLE_COLOR}]{subj_fmt:<{name_width}}[/{AVAILABLE_COLOR}]",
                ]
            )
            results.append(row)

        return results

    def get_agenda(self, now: datetime = datetime.now()):
        """ """
        header = "Agenda - Events and Tasks"
        divider = [
            {"record_id": None, "job_id": None, "text": "   "},
        ]
        events_by_date = self.get_agenda_events()
        tasks_by_urgency = self.get_agenda_tasks()
        events_and_tasks = events_by_date + divider + tasks_by_urgency
        pages = page_tagger(events_and_tasks)
        log_msg(f"{pages = }")
        return pages, header

    def get_agenda_events(self, now: datetime = datetime.now()):
        """
        Returns dict: date -> list of (tag, label, subject) for up to three days.
        Rules:
        • Pick the first 3 days that have events.
        • Also include TODAY if it has notice/drafts even with no events.
        • If nothing to display at all, return {}.
        """
        notice_records = (
            self.db_manager.get_notice_for_events()
        )  # (record_id, days_remaining, subject)
        draft_records = self.db_manager.get_drafts()  # (record_id, subject)

        today_dt = now.replace(hour=0, minute=0, second=0, microsecond=0)
        today = today_dt.date()
        now_ts = _fmt_naive(now)

        # Pull events for the next couple of weeks (or whatever window you prefer)
        window_start = today_dt
        window_end = today_dt + timedelta(days=14)
        events = self.db_manager.get_events_for_period(
            _to_local_naive(window_start), _to_local_naive(window_end)
        )
        # events rows: (start_ts, end_ts, itemtype, subject, record_id)

        grouped_by_date = self.group_events_by_date_and_time(
            events
        )  # {date: [(time_key, (start_ts, end_ts, subject, record_id)), ...]}

        # 1) Determine the first three dates with events
        event_dates_sorted = sorted(grouped_by_date.keys())
        allowed_dates: list[date] = []
        for d in event_dates_sorted:
            allowed_dates.append(d)
            if len(allowed_dates) == 3:
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
            allowed_dates = deduped[:3]  # cap to 3

        # 3) If nothing at all to show, bail early
        nothing_to_show = (not allowed_dates) and (not has_today_meta)
        if nothing_to_show:
            return []

        # 4) Build events_by_date only for allowed dates
        events_by_date: dict[date, list[dict]] = {}

        for d in allowed_dates:
            entries = grouped_by_date.get(d, [])
            for _, (start_ts, end_ts, subject, record_id, job_id) in entries:
                end_ts = end_ts or start_ts
                label = format_time_range(start_ts, end_ts, self.AMPM).strip()
                if end_ts.endswith("T000000"):
                    color = ALLDAY_COLOR
                elif end_ts <= now_ts and end_ts != start_ts:
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
                            "text": f"[{NOTICE_COLOR}]+{days_remaining}d {subject} [/{NOTICE_COLOR}]",
                        }
                    )
            if draft_records:
                for record_id, subject in draft_records:
                    events_by_date.setdefault(today, []).append(
                        {
                            "record_id": record_id,
                            "job_id": None,
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
                        "text": f"[not bold][{HEADER_COLOR}]{d.strftime('%a %b %-d')}[/{HEADER_COLOR}][/not bold]",
                    }
                )
                for event in events:
                    rows.append(event)

        return rows

    def get_agenda_tasks(self):
        """
        Returns list of (urgency_str_or_pin, color, tag_fmt, colored_subject)
        Suitable for the Agenda Tasks pane.
        """
        tasks_by_urgency = []

        # Use the JOIN with Pinned so pins persist across restarts
        urgency_records = self.db_manager.get_urgency()
        # rows: (record_id, job_id, subject, urgency, color, status, weights, pinned_int)

        # self.set_afill(urgency_records, "tasks")
        # log_msg(f"urgency_records {self.afill_by_view = }, {len(urgency_records) = }")
        # indx = 0
        # self.list_tag_to_id.setdefault("tasks", {})

        # Agenda tasks (has job_id)
        header = f"Tasks ({len(urgency_records)})"
        rows = [
            {"record_id": None, "job_id": None, "text": header},
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
        ) in urgency_records:
            # log_msg(f"collecting tasks {record_id = }, {job_id = }, {subject = }")
            # tag_fmt, indx = self.add_tag("tasks", indx, record_id, job_id=job_id)
            urgency_str = (
                "📌" if pinned else f"[{color}]{int(round(urgency * 100)):>2}[/{color}]"
            )
            rows.append(
                {
                    "record_id": record_id,
                    "job_id": job_id,
                    "text": f"[{TASK_COLOR}]{urgency_str} {subject}[/{TASK_COLOR}]",
                }
            )

        return rows

    def get_entry_from_record(self, record_id: int) -> str:
        """
        1) Load record -> Item
        2) Call item.finish_without_exdate(...)
        3) Persist Item
        4) Insert Completions row
        5) If fully finished, remove from Urgency/DateTimes
        6) Return summary dict
        """
        result = self.db_manager.get_tokens(record_id)
        tokens, rruleset, created, modified = result[0]
        entry = format_tokens(tokens, self.width, False)

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

    def get_reminders(self, bin_id: int) -> list[dict]:
        return self.db_manager.get_reminders_in_bin(bin_id)

    # def _bin_name(self, bin_id: int) -> str:
    #     self.db_manager.cursor.execute("SELECT name FROM Bins WHERE id=?", (bin_id,))
    #     row = self.db_manager.cursor.fetchone()
    #     return row[0] if row else f"bin:{bin_id}"

    def _is_root(self, bin_id: int) -> bool:
        # adjust if your root id differs
        return bin_id == getattr(self, "root_id", 0)

    @lru_cache(maxsize=2048)
    def _bin_name(self, bin_id: int) -> str:
        if self._is_root(bin_id):
            # choose what you want to display for root
            return "root"  # or "" if you prefer no label
        cur = self.db_manager.cursor
        cur.execute("SELECT name FROM Bins WHERE id=?", (bin_id,))
        row = cur.fetchone()
        return row[0] if row and row[0] else f"bin:{bin_id}"

    def _parent_bin_id(self, bin_id: int) -> Optional[int]:
        # Root has NULL parent
        self.db_manager.cursor.execute(
            "SELECT container_id FROM BinLinks WHERE bin_id=? LIMIT 1", (bin_id,)
        )
        row = self.db_manager.cursor.fetchone()
        return row[0] if row and row[0] is not None else None

    def _bin_path_ids(self, bin_id: int) -> List[int]:
        """Return path of bin ids from root→...→bin_id, but EXCLUDING root."""
        path: List[int] = []
        cur = bin_id
        while cur is not None:
            parent = self._parent_bin_id(cur)
            path.append(cur)
            cur = parent
        path.reverse()
        # Exclude root if it exists and is first
        if path and self._bin_name(path[0]).lower() == "root":
            path = path[1:]
        return path

    # def _format_path_header(
    #     self, path_ids: List[int], continued: bool
    # ) -> Tuple[str, Dict[str, Tuple[str, int]]]:
    #     """
    #     Build a single header line like:  [dim]a[/dim] Activities / [dim]b[/dim] Travel  (continued)
    #     And a tag map a->("bin", path_ids[0]), b->("bin", path_ids[1]), ...
    #     """
    #     tag_map: Dict[str, Tuple[str, int]] = {}
    #     segs: List[str] = []
    #     for i, bid in enumerate(path_ids):
    #         if i >= 26:
    #             break  # safety cap; extremely deep paths won't get more letters
    #         tag = chr(ord("a") + i)
    #         tag_map[tag] = ("bin", bid)
    #         segs.append(f"[dim]{tag}[/dim] {self._bin_name(bid)}")
    #     header = " / ".join(segs) or ".."
    #     if continued:
    #         header += " [i](continued)[/i]"
    #     return header, tag_map

    # def bin_tagger(
    #     self, bin_id: int, page_size: int = 26
    # ) -> list[tuple[list[str], dict[str, tuple[str, object]]]]:
    #     """
    #     Build pages for a single Bin view.
    #     - Header row shows the path (excluding 'root'), taggable (a..)
    #     - Then sub-bins (taggable), then reminders (taggable)
    #     - Page size counts only taggable items (bins/reminders), NOT header
    #     - On every page, header uses the SAME letters; content tags start after len(path).
    #     - When letters for content are exhausted on a page, we START A NEW PAGE.
    #     """
    #     # ---- path (excluding 'root') ----
    #     path_ids = self._bin_path_ids(bin_id)
    #
    #     def _format_path_header(path_ids: list[int], continued: bool):
    #         tag_map: dict[str, tuple[str, int]] = {}
    #         segs: list[str] = []
    #         for i, bid in enumerate(path_ids[:26]):
    #             tag = chr(ord("a") + i)
    #             tag_map[tag] = ("bin", bid)
    #             segs.append(f"[dim]{tag}[/dim] {self._bin_name(bid)}")
    #         header = " / ".join(segs) or ".."
    #         if continued:
    #             header += " [i](continued)[/i]"
    #         return header, tag_map
    #
    #     header_text_first, header_tagmap_first = _format_path_header(
    #         path_ids, continued=False
    #     )
    #
    #     # ---- children ----
    #     subbins = self.db_manager.get_subbins(
    #         bin_id
    #     )  # [{'id','name','subbins','reminders'}]
    #     reminders = self.db_manager.get_reminders_in_bin(
    #         bin_id
    #     )  # [{'id','subject','itemtype'}]
    #
    #     # TYPE_TO_COLOR = getattr(self, "TYPE_TO_COLOR", {}) or {}
    #     bin_rows = [
    #         (
    #             "bin",
    #             b["id"],
    #             # f"[bold yellow]📁 {b['name']}[/bold yellow]  [dim]({b['subbins']}/{b['reminders']})[/dim]",
    #             f"[bold yellow]{b['name']}[/bold yellow]  [dim]({b['subbins']}/{b['reminders']})[/dim]",
    #         )
    #         for b in sorted(subbins, key=lambda x: x["name"].lower())
    #     ]
    #     rec_rows = [
    #         (
    #             "record",
    #             (r["id"], None),
    #             # f"[{TYPE_TO_COLOR.get(r['itemtype'], 'white')}]🗒️ {r['subject']}[/{TYPE_TO_COLOR.get(r['itemtype'], 'white')}]",
    #             f"[{TYPE_TO_COLOR.get(r['itemtype'], 'white')}]{r['itemtype']} {r['subject']}[/{TYPE_TO_COLOR.get(r['itemtype'], 'white')}]",
    #         )
    #         for r in sorted(reminders, key=lambda x: x["subject"].lower())
    #     ]
    #     all_rows = bin_rows + rec_rows
    #
    #     pages: list[tuple[list[str], dict[str, tuple[str, object]]]] = []
    #
    #     # Letters consumed by header each page (for path tags)
    #     header_letters = min(len(path_ids), 26)
    #     # Content letters available per page (after header tags)
    #     # If header is very deep, this may be 0; in normal trees it’s <= 25.
    #     content_capacity = max(0, 26 - header_letters)
    #
    #     i = 0
    #     first_page = True
    #     while i < len(all_rows) or first_page:
    #         # Header for this page
    #         if first_page:
    #             header_text, hdr_tagmap = header_text_first, dict(header_tagmap_first)
    #         else:
    #             header_text, hdr_tagmap = _format_path_header(path_ids, continued=True)
    #
    #         rows: list[str] = [header_text]
    #         tag_map: dict[str, tuple[str, object]] = dict(hdr_tagmap)
    #
    #         # If we literally have 0 content letters (path too deep), we still
    #         # show a header-only page and break to avoid infinite loop.
    #         if content_capacity == 0:
    #             pages.append((rows, tag_map))
    #             break
    #
    #         # Tag content rows up to content_capacity for this page
    #         tagged_this_page = 0
    #         next_letter_idx = header_letters
    #         while i < len(all_rows) and tagged_this_page < content_capacity:
    #             kind, obj, text = all_rows[i]
    #             i += 1
    #             tag = chr(ord("a") + next_letter_idx)
    #             if kind == "bin":
    #                 tag_map[tag] = ("bin", obj)  # obj = child_bin_id
    #             else:
    #                 tag_map[tag] = ("record", obj)  # obj = (record_id, job_id)
    #             rows.append(f" [dim]{tag}[/dim]  {text}")
    #             next_letter_idx += 1
    #             tagged_this_page += 1
    #
    #         pages.append((rows, tag_map))
    #         first_page = False
    #
    #         # next iteration continues with remaining rows (if any)
    #
    #     return pages

    # --- add to Controller ---

    # def _pretty_child_name(self, parent_name: str, child_name: str) -> str:
    #     """
    #     Display-only prettifier:
    #     - If child starts with parent_name, strip that prefix and any leading separators.
    #     - Also handles colon form 'parent:suffix' -> 'suffix' when parent matches.
    #     - Falls back to child_name if stripping would leave empty.
    #     """
    #     pn = (parent_name or "").strip()
    #     cn = (child_name or "").strip()
    #     if not pn or not cn:
    #         return cn
    #
    #     lp = pn.lower()
    #     lc = cn.lower()
    #
    #     # Handle 'parent:suffix' exactly
    #     if ":" in cn:
    #         left, right = cn.split(":", 1)
    #         if left.strip().lower() == lp and right.strip():
    #             return right.strip()
    #
    #     # Handle raw prefix 'parentXYZ' -> 'XYZ' (e.g., '2025' + '202510' -> '10')
    #     if lc.startswith(lp):
    #         suffix = cn[len(pn) :]
    #         suffix = suffix.lstrip(" -_/.:")
    #         return suffix or cn
    #
    #     return cn

    def bin_tagger(
        self, bin_id: int, page_size: int = 26
    ) -> list[tuple[list[str], dict[str, tuple[str, object]]]]:
        """
        Build pages for a single Bin view.
        Header: path without 'root'; ancestors are tagged (a..), current bin is shown untagged.
        Content: sub-bins then reminders; per-page capacity is 26 - len(ancestors).
        """
        # ---- path (excluding 'root') ----
        full_path_ids = self._bin_path_ids(bin_id)  # top→down (no 'root')
        ancestors = full_path_ids[:-1]  # tag these
        current_id = full_path_ids[-1] if full_path_ids else bin_id

        def _format_path_header(
            continued: bool,
        ) -> tuple[str, dict[str, tuple[str, int]]]:
            tag_map: dict[str, tuple[str, int]] = {}
            segs: list[str] = []
            # tag ancestors only
            for i, bid in enumerate(ancestors[:26]):
                tag = chr(ord("a") + i)
                tag_map[tag] = ("bin", bid)
                segs.append(f"[dim]{tag}[/dim] {self._bin_name(bid)}")
            # current bin name (no tag)
            segs.append(f"[bold yellow]{self._bin_name(current_id)}[/bold yellow]")
            header = " / ".join(segs) if segs else ""
            if continued and header:
                header += " [i](continued)[/i]"
            return header, tag_map

        header_text_first, header_tagmap_first = _format_path_header(continued=False)

        # ---- children ----
        subbins = self.db_manager.get_subbins(
            current_id
        )  # [{'id','name','subbins','reminders'}]
        reminders = self.db_manager.get_reminders_in_bin(
            current_id
        )  # [{'id','subject','itemtype'}]

        # bin_rows = [
        #     (
        #         "bin",
        #         b["id"],
        #         f"[bold yellow]{b['name']}[/bold yellow]  [dim]({b['subbins']}/{b['reminders']})[/dim]",
        #     )
        #     for b in sorted(subbins, key=lambda x: x["name"].lower())
        # ]

        bin_rows = []
        for b in sorted(subbins, key=lambda x: x["name"].lower()):
            display_name = self._pretty_child_name(current_name, b["name"])
            text = (
                f"[bold yellow]{display_name}[/bold yellow]  "
                f"[dim]({b['subbins']}/{b['reminders']})[/dim]"
            )
            bin_rows.append(("bin", b["id"], text))

        rec_rows = [
            (
                "record",
                (r["id"], None),
                f"[{TYPE_TO_COLOR.get(r['itemtype'], 'white')}]"
                f"{r['itemtype']} {r['subject']}[/{TYPE_TO_COLOR.get(r['itemtype'], 'white')}]",
            )
            for r in sorted(reminders, key=lambda x: x["subject"].lower())
        ]
        all_rows = bin_rows + rec_rows

        pages: list[tuple[list[str], dict[str, tuple[str, object]]]] = []

        # Letters consumed by ancestors each page (current bin uses no letter)
        reserved = min(len(ancestors), 26)
        content_capacity = max(0, 26 - reserved)

        i = 0
        first_page = True
        while i < len(all_rows) or first_page:
            # Header per page
            if first_page:
                header_text, hdr_tagmap = header_text_first, dict(header_tagmap_first)
            else:
                header_text, hdr_tagmap = _format_path_header(continued=True)

            rows: list[str] = [header_text] if header_text else []
            tag_map: dict[str, tuple[str, object]] = dict(hdr_tagmap)

            if content_capacity == 0:
                pages.append((rows, tag_map))
                break

            # Tag content rows up to capacity
            tagged_this_page = 0
            next_letter_idx = reserved
            while i < len(all_rows) and tagged_this_page < content_capacity:
                kind, obj, text = all_rows[i]
                i += 1
                tag = chr(ord("a") + next_letter_idx)
                if kind == "bin":
                    tag_map[tag] = ("bin", obj)  # obj = child_bin_id
                else:
                    tag_map[tag] = ("record", obj)  # obj = (record_id, job_id)
                rows.append(f" [dim]{tag}[/dim]  {text}")
                next_letter_idx += 1
                tagged_this_page += 1

            pages.append((rows, tag_map))
            first_page = False

        if not pages:
            pages = [
                (
                    [header_text_first] if header_text_first else [],
                    dict(header_tagmap_first),
                )
            ]

        return pages

    def bin_tagger(self, bin_id: int, page_size: int = 26) -> List[Page]:
        """
        Build pages for a single Bin view.

        Path (excluding 'root') is shown as the first row on every page.
        - Path segments are tagged a.., but the LAST segment (the current bin) is NOT tagged.
        - On every page, content letters start after the header letters, so if header used a..c,
        content begins at 'd' on each page.
        - Only taggable rows (bins + reminders) count toward page_size.

        Returns: list[ (rows: list[str], tag_map: dict[str, ('bin'| 'record', target)]) ]
        - target is bin_id for 'bin', or (record_id, job_id|None) for 'record'.
        """

        # ---------- helpers ----------
        def _is_root(bid: int) -> bool:
            # Adjust if you use a different root id
            return bid == getattr(self, "root_id", 0)

        @lru_cache(maxsize=4096)
        def _bin_name(bid: int) -> str:
            if _is_root(bid):
                return "root"
            cur = self.db_manager.cursor
            cur.execute("SELECT name FROM Bins WHERE id=?", (bid,))
            row = cur.fetchone()
            return row[0] if row and row[0] else f"bin:{bid}"

        def _bin_path_ids(bid: int) -> List[int]:
            """Return ancestor path including current bin, excluding root."""
            ids: List[int] = []
            cur = self.db_manager.cursor
            b = bid
            while b is not None and not _is_root(b):
                ids.append(b)
                cur.execute(
                    "SELECT container_id FROM BinLinks WHERE bin_id = ? LIMIT 1", (b,)
                )
                row = cur.fetchone()
                b = row[0] if row else None
            ids.reverse()
            return ids

        # def _pretty_child_name(parent_name: str, child_name: str) -> str:
        #     """Trim parent prefix from child when child starts with parent (e.g., '202510' under '2025' -> '10')."""
        #     if not parent_name:
        #         return child_name
        #     if child_name.startswith(parent_name):
        #         suffix = child_name[len(parent_name) :]
        #         while suffix and suffix[0] in ":/-_ .":
        #             suffix = suffix[1:]
        #         if suffix:
        #             return suffix
        #     return child_name

        def _pretty_child_name(parent_name: str, child_name: str) -> str:
            """
            Trim exactly 'parent:' from the front of a child name.
            This avoids accidental trims when a child merely starts with the same characters.
            Examples:
            parent='2025', child='2025:10'  -> '10'
            parent='people', child='people:S' -> 'S'
            parent='2025', child='202510'   -> '202510'   (unchanged)
            parent='2025', child='2025x'    -> '2025x'    (unchanged)
            """
            if not parent_name:
                return child_name
            prefix = f"{parent_name}:"
            if child_name.startswith(prefix):
                suffix = child_name[len(prefix) :]
                return suffix or child_name  # never return empty string
            return child_name

        def _format_path_header(
            path_ids: List[int], continued: bool
        ) -> Tuple[str, Dict[str, Tuple[str, int]], int]:
            """
            Build the header text and its tag_map.
            Tag all but the last path segment (so the current bin is untagged).
            Returns: (header_text, header_tagmap, header_letters_count)
            """
            tag_map: Dict[str, Tuple[str, int]] = {}
            segs: List[str] = []
            if not path_ids:
                header_text = ".."
                return (
                    (header_text + (" [i](continued)[/i]" if continued else "")),
                    tag_map,
                    0,
                )

            # how many path letters to tag (exclude current bin)
            taggable = max(0, len(path_ids) - 1)
            header_letters = min(taggable, 26)

            for i, bid in enumerate(path_ids):
                name = _bin_name(bid)
                if i < header_letters:  # tagged ancestor
                    tag = chr(ord("a") + i)
                    tag_map[tag] = ("bin", bid)
                    segs.append(f"[dim]{tag}[/dim] {name}")
                elif i == len(path_ids) - 1:  # current bin (untagged)
                    segs.append(f"[bold yellow]{name}[/bold yellow]")
                else:  # very deep path overflow (unlikely)
                    f"[bold yellow]{segs.append(name)}[/bold yellow]"

            header = " / ".join(segs) if segs else ".."
            if continued:
                header += " [i](continued)[/i]"
            return header, tag_map, header_letters

        # ---------- gather data ----------
        path_ids = _bin_path_ids(bin_id)  # excludes root, includes current bin
        current_name = "" if _is_root(bin_id) else _bin_name(bin_id)

        subbins = self.db_manager.get_subbins(bin_id)  # [{id,name,subbins,reminders}]
        reminders = self.db_manager.get_reminders_in_bin(
            bin_id
        )  # [{id,subject,itemtype}]

        # Prepare content rows (bins then reminders), sorted
        bin_rows: List[Tuple[str, Any, str]] = []
        for b in sorted(subbins, key=lambda x: x["name"].lower()):
            disp = _pretty_child_name(current_name, b["name"])
            bin_rows.append(
                (
                    "bin",
                    b["id"],
                    f"[bold yellow]{disp}[/bold yellow]  [dim]({b['subbins']}/{b['reminders']})[/dim]",
                )
            )

        rec_rows: List[Tuple[str, Any, str]] = []
        for r in sorted(reminders, key=lambda x: x["subject"].lower()):
            color = TYPE_TO_COLOR.get(r.get("itemtype", ""), "white")
            rec_rows.append(
                (
                    "record",
                    (r["id"], None),
                    f"[{color}]{r.get('itemtype', '')} {r['subject']}[/{color}]",
                )
            )

        all_rows: List[Tuple[str, Any, str]] = bin_rows + rec_rows

        # ---------- paging ----------
        pages: List[Page] = []
        idx = 0
        first = True

        # header (first page) + how many letters consumed by header
        first_header_text, first_hdr_map, header_letters = _format_path_header(
            path_ids, continued=False
        )
        content_capacity = max(0, page_size - header_letters)

        while first or idx < len(all_rows):
            if first:
                header_text, hdr_map = first_header_text, dict(first_hdr_map)
            else:
                # repeated header with (continued)
                header_text, hdr_map, _ = _format_path_header(path_ids, continued=True)

            rows_out: List[str] = [header_text]
            tag_map: Dict[str, Tuple[str, Any]] = dict(hdr_map)

            if content_capacity == 0:
                # Deep path; show header-only page to avoid infinite loop
                pages.append((rows_out, tag_map))
                break

            tagged = 0
            next_letter_idx = (
                header_letters  # content starts after header letters every page
            )
            while idx < len(all_rows) and tagged < content_capacity:
                kind, payload, text = all_rows[idx]
                idx += 1
                tag = chr(ord("a") + next_letter_idx)
                if kind == "bin":
                    tag_map[tag] = ("bin", payload)
                else:
                    tag_map[tag] = ("record", payload)  # (record_id, job_id)
                rows_out.append(f" [dim]{tag}[/dim]  {text}")
                tagged += 1
                next_letter_idx += 1

            pages.append((rows_out, tag_map))
            first = False

        return pages

    def get_bin_pages(self, bin_id: int):
        """Public API the view will call."""
        pages = self.bin_tagger(bin_id)
        # Title: path text without tags, e.g. "Activities / Travel". If no path => "root".
        path_ids = self._bin_path_ids(bin_id)
        # title = " / ".join(self._bin_name(b) for b in path_ids) or ".."
        title = "Bins"
        return pages, title

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

    # def _sqlite_backup(self, src_db: Path, dest_db: Path) -> None:
    #     """Use SQLite's backup API for a consistent snapshot."""
    #     dest_tmp = dest_db.with_suffix(dest_db.suffix + ".tmp")
    #     dest_db.parent.mkdir(parents=True, exist_ok=True)
    #     with sqlite3.connect(str(src_db)) as src, sqlite3.connect(str(dest_tmp)) as dst:
    #         src.backup(dst, pages=0)  # full backup
    #         # Safety on the destination file only:
    #         dst.execute("PRAGMA wal_checkpoint(TRUNCATE);")
    #         dst.execute("VACUUM;")
    #         dst.commit()
    #     try:
    #         shutil.copystat(src_db, dest_tmp)
    #     except Exception:
    #         pass
    #     dest_tmp.replace(dest_db)

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
        Keep at most 5:
        newest overall, newest >=3d, >=7d, >=14d, >=28d (by calendar day).
        """
        keep: Set[Path] = set()
        if not backups:
            return keep

        newest = max(backups, key=lambda b: (b.day, b.mtime))
        keep.add(newest.path)

        for days in (3, 7, 14, 28):
            cutoff = today_local - timedelta(days=days)
            cands = [b for b in backups if b.day <= cutoff]
            if cands:
                chosen = max(cands, key=lambda b: (b.day, b.mtime))
                keep.add(chosen.path)
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
            if not dry_run:
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
