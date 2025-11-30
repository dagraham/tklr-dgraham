from __future__ import annotations
from packaging.version import parse as parse_version
from importlib.metadata import version
from functools import lru_cache

# TODO: Keep the display part - the model part will be in model.py
from datetime import datetime, timedelta, date, timezone

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
from typing import Iterator, Callable

import string
import shutil
import subprocess
import shlex
import textwrap


import json
from typing import Literal
from .item import Item
from .model import DatabaseManager, UrgencyComputer
from .model import _fmt_naive
from .list_colors import css_named_colors
from .versioning import get_version

from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from zoneinfo import ZoneInfo
from dateutil.rrule import rrulestr
from dateutil import tz

# import sqlite3
from .shared import (
    TYPE_TO_COLOR,
    REPEATING,
    log_msg,
    bug_msg,
    _to_local_naive,
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
    # fmt_user,
    parse_utc_z,
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
    bug_msg(f"{out = }")
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


def format_iso_week(monday_date: datetime )->str:
    """
    Format an ISO week string, taking not to repeat the month subject unless the week spans two months.

    Args:
        monday_date (datetime): The date of the Monday of the week.

    Returns:
        str: Formatted string like 'Monday 17 - Sunday 23, 2023 #1'.
    """
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
    # bug_msg(f"set_anniversary {subject = }, {has_xxx = }")
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


# def page_tagger(
#     items: List[dict], page_size: int = 26
# ) -> List[Tuple[List[str], Dict[str, Tuple[int, int | None]]]]:
#     """
#     Split 'items' into pages. Each item is a dict:
#         { "record_id": int | None, "job_id": int | None, "text": str }
#
#     Returns a list of pages. Each page is a tuple:
#         (page_rows: list[str], page_tag_map: dict[str -> (record_id, job_id|None)])
#
#     Rules:
#       - Only record rows (record_id != None) receive single-letter tags 'a'..'z'.
#       - Exactly `page_size` records are tagged per page (except the last page).
#       - Headers (record_id is None) are kept in order.
#       - If a header's block of records spans pages, the header is duplicated at the
#         start of the next page with " (continued)" appended.
#     """
#     pages: List[Tuple[List[str], Dict[str, Tuple[int, int | None]]]] = []
#
#     page_rows: List[str] = []
#     tag_map: Dict[str, Tuple[int, int | None]] = {}
#     tag_counter = 0  # number of record-tags on current page
#     last_header_text = None  # text of the most recent header seen (if any)
#
#     def finalize_page(new_page_rows=None):
#         """Close out the current page and start a fresh one optionally seeded with
#         new_page_rows (e.g., duplicated header)."""
#         nonlocal page_rows, tag_map, tag_counter
#         pages.append((page_rows, tag_map))
#         page_rows = new_page_rows[:] if new_page_rows else []
#         tag_map = {}
#         tag_counter = 0
#
#     for item in items:
#         # header row
#         if not isinstance(item, dict):
#             log_msg(f"error: {item} is not a dict")
#             continue
#         if item.get("record_id") is None:
#             hdr_text = item.get("text", "")
#             last_header_text = hdr_text
#             page_rows.append(hdr_text)
#             # continue; headers do not affect tag_counter
#             continue
#
#         # record row (taggable)
#         # If current page is already full (page_size tags), start a new page.
#         # IMPORTANT: when we create the new page, we want to preseed it with a
#         # duplicated header (if one exists) and mark it as "(continued)".
#         if tag_counter >= page_size:
#             # If we have a last_header_text, duplicate it at top of next page with continued.
#             if last_header_text:
#                 continued_header = f"{last_header_text} (continued)"
#                 finalize_page(new_page_rows=[continued_header])
#             else:
#                 finalize_page()
#
#         # assign next tag on current page
#         tag = chr(ord("a") + tag_counter)
#         tag_map[tag] = (item["record_id"], item.get("job_id", None))
#         # Use small/dim tag formatting to match your UI style; adapt if needed
#         page_rows.append(f" [dim]{tag}[/dim]  {item.get('text', '')}")
#         tag_counter += 1
#
#     # At end, still need to push the last page if it has any rows
#     if page_rows or tag_map:
#         pages.append((page_rows, tag_map))
#
#     return pages


def page_tagger(
    items: List[dict], page_size: int = 26
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
            # bug_msg(f"error: {item} is not a dict")
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
        # bug_msg(f"{tag_map = }")

        # Display text unchanged
        page_rows.append(f" [dim]{tag}[/dim]  {item.get('text', '')}")
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
        # self.afill_by_view: dict[str, int] = {}  # e.g. {"events": 1, "tasks": 2}
        # self.afill_by_week: dict[Tuple[int, int], int] = {}

        for view in ["next", "last", "find", "events", "tasks", "alerts"]:
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
            _yr = "%Y"
            _dm = "%d-%m" if self.dayfirst else "%m-%d"
            self.datefmt = f"{_yr}-{_dm}" if self.yearfirst else f"{_dm}-{_yr}"
        self.datetimefmt = f"{self.datefmt} {self.timefmt}"

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
            bug_msg(
                f"{item.itemtype = } {item.has_f = } {item.itemtype in '~^x' and item.has_f = }"
            )

        record_id = self.db_manager.add_item(item)

        if item.completions:
            bug_msg(f"{item.completions = }")
            self.db_manager.add_completion(record_id, item.completions)

        return record_id

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

        # 2) Parse as a final Item
        item = Item(new_raw, controller=self)
        item.final = True
        item.parse_input(new_raw)

        if not getattr(item, "parse_ok", False):
            # You might want a log_msg here
            return False

        # 3) Finalize (jobs, rrules, etc.)
        item.finalize_record()

        if not getattr(item, "parse_ok", False):
            return False

        # 4) Save back into the same record (and regen DateTimes, Alerts, etc.)
        self.db_manager.save_record(item, record_id=record_id)
        # 🔁 NEW: record completion if one was produced
        completion = getattr(item, "completions", None)
        if completion:
            self.db_manager.add_completion(record_id, completion)

        return True

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

        # bug_msg(
        #     f"{inst_local = }, {instances_local = }, {inst_local in instances_local = }"
        # )
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
        
        # Convert instance_dt to UTC if aware, or leave naive
        if instance_dt.tzinfo is not None:
            instance_utc = instance_dt.astimezone(timezone.utc).replace(tzinfo=None)
        else:
            instance_utc = instance_dt.replace(tzinfo=None)
        
        # Check if instance matches any RDATE (compare without timezone for simplicity)
        for rdate in rdates:
            rdate_naive = rdate.replace(tzinfo=None) if rdate.tzinfo else rdate
            # Compare with minute precision (ignore seconds)
            if (instance_utc.year == rdate_naive.year and
                instance_utc.month == rdate_naive.month and
                instance_utc.day == rdate_naive.day and
                instance_utc.hour == rdate_naive.hour and
                instance_utc.minute == rdate_naive.minute):
                return True
        
        return False

    def _advance_s_to_next_rrule_instance(self, record_id: int, second_instance_text: str) -> bool:
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
            bug_msg(f"Error advancing @s: {e}")
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

    # def finish_task(self, record_id: int, job_id: int | None, when: datetime) -> bool:
    #     """
    #     Mark a task (or job) as finished at `when`.
    #
    #     Semantics:
    #     - Job (job_id not None):
    #         add &f <stamp> to that job spec (unchanged from before).
    #     - Plain task (no job_id):
    #         look at upcoming instances from DateTimes:
    #
    #         * 0 upcoming:
    #             - no schedule → just append @f <stamp>.
    #         * 1 upcoming:
    #             - consume that last instance (like delete_instance),
    #               then append @f <stamp> to mark the reminder finished.
    #         * 2+ upcoming:
    #             - consume only the *next* instance (like delete_instance),
    #               and DO NOT add @f yet (reminder still has future instances).
    #     """
    #     stamp = self.fmt_user(when)
    #
    #     # ---- Case 1: project job ----
    #     if job_id is not None:
    #
    #         def edit_job(text: str) -> str:
    #             # your existing helper that injects &f into the given job
    #             return self._add_finish_to_job(text, job_id, stamp)
    #
    #         return self.apply_textual_edit(record_id, edit_job)
    #
    #     # ---- Case 2: plain task (no job_id) ----
    #     upcoming = self.db_manager.get_next_start_datetimes_for_record(record_id) or []
    #
    #     # 0 upcoming instances: no schedule -> simple one-shot finish
    #     if not upcoming:
    #
    #         def edit_no_schedule(text: str) -> str:
    #             return text.rstrip() + f" @f {stamp}"
    #
    #         return self.apply_textual_edit(record_id, edit_no_schedule)
    #
    #     # 1 upcoming instance: finishing this consumes the last instance AND the reminder
    #     if len(upcoming) == 1:
    #         instance_text = upcoming[0]
    #
    #         # consume that final instance (RDATE/@s/@+ housekeeping)
    #         self.delete_instance(record_id, instance_text)
    #
    #         # now mark the reminder as finished with @f
    #         def edit_last(text: str) -> str:
    #             return text.rstrip() + f" @f {stamp}"
    #
    #         return self.apply_textual_edit(record_id, edit_last)
    #
    #     # 2+ upcoming instances: repeating → consume ONLY the next instance
    #     instance_text = upcoming[0]
    #     return self.delete_instance(record_id, instance_text)

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

    def finish_task(self, record_id: int, job_id: int | None, when: datetime) -> bool:
        stamp = self.fmt_user(when)

        # ---- Case 1: project job ----
        if job_id is not None:
            return self._add_finish_to_job(record_id, job_id, stamp)

        # ---- Case 2: plain task (no job_id) ----
        upcoming = self.db_manager.get_next_start_datetimes_for_record(record_id) or []
        bug_msg(f"{upcoming = }")

        # Case 2a: No instances or only 1 instance → append @f
        if len(upcoming) <= 1:
            if upcoming:
                instance_text = upcoming[0]
                self.delete_instance(record_id, instance_text)

            def edit_with_finish(text: str) -> str:
                return text.rstrip() + f" @f {stamp}"

            return self.apply_textual_edit(record_id, edit_with_finish)

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
            return self.delete_instance(record_id, first_instance_text)
        
        # Parse the first instance to get UTC datetime
        try:
            first_dt = parse(first_instance_text)
        except Exception:
            return False
        
        # Check if first instance comes from RDATE
        is_from_rdate = self._instance_is_from_rdate(rruleset_str, first_dt)
        
        if is_from_rdate:
            # First instance is from @+ (RDATE) → remove it from @+
            return self.delete_instance(record_id, first_instance_text)
        else:
            # First instance is from @r (RRULE) → update @s to second instance
            if not second_instance_text:
                # Safety: shouldn't happen, but handle gracefully
                return self.delete_instance(record_id, first_instance_text)
            
            return self._advance_s_to_next_rrule_instance(record_id, second_instance_text)

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

    # def delete_instance(
    #     self,
    #     record_id: int,
    #     instance_text: str,
    # ) -> bool:
    #     """
    #     For a single instance:
    #
    #     Special case:
    #     - If the record uses @s + @+ with no @r, we:
    #         * Compute the full instance list from rruleset.
    #         * Drop just this instance.
    #         * Rebuild @s and @+ from the survivors.
    #
    #     General case:
    #     - If the instance appears in an @+ list, remove it from that list.
    #     - Otherwise, append an @- <instance_text> exclusion token (in entry format).
    #     """
    #
    #     rec = self.db_manager.get_record_as_dictionary(record_id)
    #     if not rec:
    #         return False
    #
    #     rruleset = rec.get("rruleset") or ""
    #
    #     def edit_tokens(tokens: list[dict]) -> bool:
    #         # 1) Special case: @s + @+ but no @r
    #         if self._is_s_plus_no_r(tokens) and rruleset:
    #             changed = self._adjust_s_plus_from_rruleset(
    #                 tokens,
    #                 rruleset=rruleset,
    #                 instance_text=instance_text,
    #                 mode="one",
    #             )
    #             if changed:
    #                 return True
    #             # fall through to general path if nothing changed for some reason
    #
    #         changed = False
    #
    #         # 2) General path: try to remove from @+ using UTC-Z
    #         removed = self._remove_instance_from_plus_tokens(tokens, instance_text)
    #         changed = changed or removed
    #
    #         # 3) If not present in @+, fall back to @- <entry-style-datetime>
    #         if not removed:
    #             inst_dt = parse(instance_text)
    #             entry_style = self.fmt_user(inst_dt)
    #             tokens.append(
    #                 {
    #                     "token": f"@- {entry_style}",
    #                     "t": "@",
    #                     "k": "-",
    #                 }
    #             )
    #             changed = True
    #
    #         return changed
    #
    #     return self.apply_token_edit(record_id, edit_tokens)
    #
    # def delete_this_and_future(
    #     self,
    #     record_id: int,
    #     instance_text: str,
    # ) -> bool:
    #     """
    #     instance_text is the TEXT of the selected instance's start_datetime.
    #
    #     Special case (@s + @+ with no @r):
    #     - Use rruleset to get the full instance list.
    #     - Remove this instance and all subsequent ones.
    #     - Rebuild @s and @+ from survivors (or clear schedule if none).
    #
    #     General case:
    #     - Remove this instance from @+ if present.
    #     - Append &u <cutoff_stamp> where cutoff_stamp is (instance_dt - 1s)
    #         in entry format.
    #     """
    #
    #     rec = self.db_manager.get_record_as_dictionary(record_id)
    #     if not rec:
    #         return False
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

    # def get_tag_iterator(self, view: str, count: int) -> Iterator[str]:
    #     if view not in self.afill_by_view:
    #         self.set_afill([None] * count, view)
    #     fill = self.afill_by_view[view]
    #     for i in range(count):
    #         yield indx_to_tag(i, fill)

    # --- replace your set_afill with this per-view version ---
    # def set_afill(self, details: list, view: str):
    #     n = len(details)
    #     fill = 1 if n <= 26 else 2 if n <= 26 * 26 else 3
    #     log_msg(f"{view = }, {n = }, {fill = }, {details = }")
    #     self.afill_by_view[view] = fill

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

    # def set_week_afill(self, details: list, yr_wk: Tuple[int, int]):
    #     n = len(details)
    #     fill = 1 if n <= 26 else 2 if n <= 26 * 26 else 3
    #     log_msg(f"{yr_wk = }, {n = }, {fill = }")
    #     # self.afill_by_week[yr_wk] = fill

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

    def get_entry(self, record_id, job_id=None, instance=None):
        lines = []
        result = self.db_manager.get_tokens(record_id)
        # log_msg(f"{result = }")

        tokens, rruleset, created, modified = result[0]

        entry = format_tokens(tokens, self.width)
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

        title = f"[bold]{subject:^{self.width}}[/bold]"

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
            "record": self.db_manager.get_record(record_id),
        }
        self._last_details_meta = meta
        bug_msg(f"{meta['first'] = }, {meta['second'] = }, {meta['instance_ts'] = }")

        # return [title, ""] + fields
        return title, fields, meta

    def get_record(self, record_id):
        return self.db_manager.get_record(record_id)

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
        header = f"[bold][dim]{'tag':^3}[/dim] {'alert':^{alert_width}}   {'for':^{start_width}}    {'subject':<{name_width}}[/bold]"

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
        pages = page_tagger(rows)
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
            pages = page_tagger(rows)
            return pages

        weekday_to_events = {}
        for i in range(7):
            this_day = (start_datetime + timedelta(days=i)).date()
            weekday_to_events[this_day] = []

        # for start_ts, end_ts, itemtype, subject, id, job_id in events:
        for dt_id, start_ts, end_ts, itemtype, subject, id, job_id in events:
            # bug_msg(f"{itemtype = }, {subject = }, {dt_id = }, {id = }, {job_id = }")
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
            # bug_msg(f"{old_subject = }, {subject = }")

            row = {
                "record_id": id,
                "job_id": job_id,
                "datetime_id": dt_id,
                "instance_ts": start_ts,
                "text": f"[{type_color}]{itemtype} {escaped_start_end}{subject}[/{type_color}]",
            }
            weekday_to_events.setdefault(start_dt.date(), []).append(row)
            # bug_msg(f"job row: {row = }")

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

        if not events:
            return [], header

        year_to_events = {}

        for dt_id, id, job_id, subject, description, itemtype, start_ts in events:
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

            # 👉 NEW: append flags from Records.flags
            subject = self.apply_flags(id, subject)

            monthday = start_dt.strftime("%-m-%d")
            start_end = f"{monthday:>2} {format_hours_mins(start_dt, HRS_MINS)}"
            type_color = TYPE_TO_COLOR[itemtype]
            escaped_start_end = f"[not bold]{start_end}[/not bold]"
            item = {
                "record_id": id,
                "job_id": job_id,
                "datetime_id": dt_id,
                "instance_ts": start_ts,
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
        pages = page_tagger(rows)
        # bug_msg(f"{pages = }")
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

        for dt_id, id, job_id, subject, description, itemtype, start_ts in events:
            start_dt = datetime_from_timestamp(start_ts)
            subject = self.apply_anniversary_if_needed(id, subject, start_dt)
            # log_msg(f"Week description {subject = }, {start_dt = }, {end_dt = }")
            if job_id is not None:
                try:
                    js = self.db_manager.get_job_display_subject(id, job_id)
                    if js:  # only override if present/non-empty
                        subject = js
                    # bug_msg(f"{subject = }")
                except Exception as e:
                    # fail-safe: keep the record subject
                    # bug_msg(f"{e = }")
                    pass

            # 👉 NEW: append flags from Records.flags
            subject = self.apply_flags(id, subject)

            monthday = start_dt.strftime("%-m-%d")
            start_end = f"{monthday:>2} {format_hours_mins(start_dt, HRS_MINS)}"
            type_color = TYPE_TO_COLOR[itemtype]
            escaped_start_end = f"[not bold]{start_end}[/not bold]"
            item = {
                "dt_id": dt_id,
                "record_id": id,
                "job_id": job_id,
                "instance_ts": start_ts,
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
        # bug_msg(f"{pages = }")
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
        pages = page_tagger(rows)
        # bug_msg(f"{pages = }")
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

        if not records:
            return [], header

        # Group by month-year of completion (e.g. "Nov 2025")
        year_to_events: dict[str, list[dict]] = defaultdict(list)

        for (
            record_id,
            subject,
            description,
            itemtype,
            due_dt,  # may be None
            completed_dt,  # datetime
        ) in records:
            # apply flags 𝕣/𝕠/𝕒/𝕘 (from Records.flags)
            subject = self.apply_flags(record_id, subject or "(untitled)")
            completed_dt = completed_dt.astimezone()
            due_dt = due_dt.astimezone() if due_dt else None

            # display: " 5 14:30" style like get_next
            monthday = completed_dt.strftime("%-m-%d")
            time_part = format_hours_mins(completed_dt, HRS_MINS)
            when_str = f"{monthday:>2} {time_part}"

            type_color = TYPE_TO_COLOR.get(itemtype, "white")
            when_frag = f"[not bold]{when_str}[/not bold]"

            item = {
                "record_id": record_id,
                "job_id": None,  # no per-job completions yet
                "datetime_id": None,  # keeping keys parallel with other views
                "instance_ts": due_dt.strftime("%Y%m%dT%H%M") if due_dt else "none",
                "text": f"[{type_color}]{itemtype} {when_frag} {subject}[/{type_color}]",
            }

            ym = completed_dt.strftime("%b %Y")
            year_to_events[ym].append(item)

        # Flatten to rows (month headers + items), then page-tagger
        rows: list[dict] = []
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
                rows.extend(events)

        pages = page_tagger(rows)
        return pages, header

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

        # self.set_afill(completions, "record_completions")
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
        # bug_msg(f"{pages = }")
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
            for _, (dt_id, start_ts, end_ts, subject, record_id, job_id) in entries:
                subject = self.apply_flags(record_id, subject)
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

    # def get_agenda_tasks(self):
    #     """
    #     Returns list of (urgency_str_or_pin, color, tag_fmt, colored_subject)
    #     Suitable for the Agenda Tasks pane.
    #     """
    #     tasks_by_urgency = []
    #
    #     # Use the JOIN with Pinned so pins persist across restarts
    #     urgency_records = self.db_manager.get_urgency()
    #     # rows: (record_id, job_id, subject, urgency, color, status, weights, pinned_int)
    #
    #     # self.set_afill(urgency_records, "tasks")
    #     # log_msg(f"urgency_records {self.afill_by_view = }, {len(urgency_records) = }")
    #     # indx = 0
    #     # self.list_tag_to_id.setdefault("tasks", {})
    #
    #     # Agenda tasks (has job_id)
    #     header = f"Tasks ({len(urgency_records)})"
    #     rows = [
    #         {"record_id": None, "job_id": None, "text": header},
    #     ]
    #     for (
    #         record_id,
    #         job_id,
    #         subject,
    #         urgency,
    #         color,
    #         status,
    #         weights,
    #         pinned,
    #     ) in urgency_records:
    #         # log_msg(f"collecting tasks {record_id = }, {job_id = }, {subject = }")
    #         # tag_fmt, indx = self.add_tag("tasks", indx, record_id, job_id=job_id)
    #         urgency_str = (
    #             "📌" if pinned else f"[{color}]{int(round(urgency * 100)):>2}[/{color}]"
    #         )
    #         rows.append(
    #             {
    #                 "record_id": record_id,
    #                 "job_id": job_id,
    #                 "text": f"[{TASK_COLOR}]{urgency_str} {self.apply_flags(record_id, subject)}[/{TASK_COLOR}]",
    #             }
    #         )
    #
    #     return rows

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
            urgency_str = (
                "📌" if pinned else f"[{color}]{int(round(urgency * 100)):>2}[/{color}]"
            )

            rows.append(
                {
                    "record_id": record_id,
                    "job_id": job_id,
                    "datetime_id": datetime_id,  # 👈 earliest DateTimes.id, or None
                    "instance_ts": instance_ts,  # 👈 earliest start_datetime TEXT, or None
                    "text": f"[{TASK_COLOR}]{urgency_str} {self.apply_flags(record_id, subject)}[/{TASK_COLOR}]",
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

        # def get_reminders(self, bin_id: int) -> list[dict]:
        #     return self.db_manager.get_reminders_in_bin(bin_id)

        # def _bin_name(self, bin_id: int) -> str:
        #     self.db_manager.cursor.execute("SELECT name FROM Bins WHERE id=?", (bin_id,))
        #     row = self.db_manager.cursor.fetchone()
        #     return row[0] if row else f"bin:{bin_id}"

        # def _is_root(self, bin_id: int) -> bool:
        #     # adjust if your root id differs
        #     return bin_id == getattr(self, "root_id", 0)

        # @lru_cache(maxsize=2048)
        # def _bin_name(self, bin_id: int) -> str:
        #     if self._is_root(bin_id):
        #         # choose what you want to display for root
        #         return "root"  # or "" if you prefer no label
        #     cur = self.db_manager.cursor
        #     cur.execute("SELECT name FROM Bins WHERE id=?", (bin_id,))
        #     row = cur.fetchone()
        #     return row[0] if row and row[0] else f"bin:{bin_id}"
        #
        # def _parent_bin_id(self, bin_id: int) -> Optional[int]:
        #     # Root has NULL parent
        #     self.db_manager.cursor.execute(
        #         "SELECT container_id FROM BinLinks WHERE bin_id=? LIMIT 1", (bin_id,)
        #     )
        #     row = self.db_manager.cursor.fetchone()
        #     return row[0] if row and row[0] is not None else None
        #
        # def _bin_path_ids(self, bin_id: int) -> List[int]:
        #     """Return path of bin ids from root→...→bin_id, but EXCLUDING root."""
        #     path: List[int] = []
        #     cur = bin_id
        #     while cur is not None:
        #         parent = self._parent_bin_id(cur)
        #         path.append(cur)
        #         cur = parent
        #     path.reverse()
        #     # Exclude root if it exists and is first
        #     if path and self._bin_name(path[0]).lower() == "root":
        #         path = path[1:]
        #     return path

        # def bin_tagger(self, bin_id: int, page_size: int = 26) -> List[Page]:
        #     """
        #     Build pages for a single Bin view.
        #
        #     Path (excluding 'root') is shown as the first row on every page.
        #     - Path segments are tagged a.., but the LAST segment (the current bin) is NOT tagged.
        #     - On every page, content letters start after the header letters, so if header used a..c,
        #     content begins at 'd' on each page.
        #     - Only taggable rows (bins + reminders) count toward page_size.
        #
        #     Returns: list[ (rows: list[str], tag_map: dict[str, ('bin'| 'record', target)]) ]
        #     - target is bin_id for 'bin', or (record_id, job_id|None) for 'record'.
        #     """
        #
        #     # ---------- helpers ----------
        #     def _is_root(bid: int) -> bool:
        #         # Adjust if you use a different root id
        #         return bid == getattr(self, "root_id", 0)
        #
        #     @lru_cache(maxsize=4096)
        #     def _bin_name(bid: int) -> str:
        #         if _is_root(bid):
        #             return "root"
        #         cur = self.db_manager.cursor
        #         cur.execute("SELECT name FROM Bins WHERE id=?", (bid,))
        #         row = cur.fetchone()
        #         return row[0] if row and row[0] else f"bin:{bid}"
        #
        #     def _bin_path_ids(bid: int) -> List[int]:
        #         """Return ancestor path including current bin, excluding root."""
        #         ids: List[int] = []
        #         cur = self.db_manager.cursor
        #         b = bid
        #         while b is not None and not _is_root(b):
        #             ids.append(b)
        #             cur.execute(
        #                 "SELECT container_id FROM BinLinks WHERE bin_id = ? LIMIT 1", (b,)
        #             )
        #             row = cur.fetchone()
        #             b = row[0] if row else None
        #         ids.reverse()
        #         return ids
        #
        #     def _pretty_child_name(parent_name: str, child_name: str) -> str:
        #         """
        #         Trim exactly 'parent:' from the front of a child name.
        #         This avoids accidental trims when a child merely starts with the same characters.
        #         Examples:
        #         parent='2025', child='2025:10'  -> '10'
        #         parent='people', child='people:S' -> 'S'
        #         parent='2025', child='202510'   -> '202510'   (unchanged)
        #         parent='2025', child='2025x'    -> '2025x'    (unchanged)
        #         """
        #         if not parent_name:
        #             return child_name
        #         prefix = f"{parent_name}:"
        #         if child_name.startswith(prefix):
        #             suffix = child_name[len(prefix) :]
        #             return suffix or child_name  # never return empty string
        #         return child_name
        #
        #     def _format_path_header(
        #         path_ids: List[int], continued: bool
        #     ) -> Tuple[str, Dict[str, Tuple[str, int]], int]:
        #         """
        #         Build the header text and its tag_map.
        #         Tag all but the last path segment (so the current bin is untagged).
        #         Returns: (header_text, header_tagmap, header_letters_count)
        #         """
        #         tag_map: Dict[str, Tuple[str, int]] = {}
        #         segs: List[str] = []
        #         if not path_ids:
        #             header_text = ".."
        #             return (
        #                 (header_text + (" [i](continued)[/i]" if continued else "")),
        #                 tag_map,
        #                 0,
        #             )
        #
        #         # how many path letters to tag (exclude current bin)
        #         taggable = max(0, len(path_ids) - 1)
        #         header_letters = min(taggable, 26)
        #
        #         for i, bid in enumerate(path_ids):
        #             name = _bin_name(bid)
        #             if i < header_letters:  # tagged ancestor
        #                 tag = chr(ord("a") + i)
        #                 tag_map[tag] = ("bin", bid)
        #                 segs.append(f"[dim]{tag}[/dim] {name}")
        #             elif i == len(path_ids) - 1:  # current bin (untagged)
        #                 segs.append(f"[bold red]{name}[/bold red]")
        #             else:  # very deep path overflow (unlikely)
        #                 f"[bold yellow]{segs.append(name)}[/bold yellow]"
        #
        #         header = " / ".join(segs) if segs else ".."
        #         if continued:
        #             header += " [i](continued)[/i]"
        #         return header, tag_map, header_letters
        #
        #     # ---------- gather data ----------
        #     path_ids = _bin_path_ids(bin_id)  # excludes root, includes current bin
        #     current_name = "" if _is_root(bin_id) else _bin_name(bin_id)
        #
        #     subbins = self.db_manager.get_subbins(bin_id)  # [{id,name,subbins,reminders}]
        #     reminders = self.db_manager.get_reminders_in_bin(
        #         bin_id
        #     )  # [{id,subject,itemtype}]
        #
        #     # Prepare content rows (bins then reminders), sorted
        #     bin_rows: List[Tuple[str, Any, str]] = []
        #     for b in sorted(subbins, key=lambda x: x["name"].lower()):
        #         disp = _pretty_child_name(current_name, b["name"])
        #         bin_rows.append(
        #             (
        #                 "bin",
        #                 b["id"],
        #                 f"[bold yellow]{disp}[/bold yellow]  [dim]({b['subbins']}/{b['reminders']})[/dim]",
        #             )
        #         )
        #
        #     rec_rows: List[Tuple[str, Any, str]] = []
        #
        #     for r in sorted(reminders, key=lambda x: x["subject"].lower()):
        #         log_msg(f"bins {r = }")
        #         color = TYPE_TO_COLOR.get(r.get("itemtype", ""), "white")
        #         old_subject = r["subject"]
        #         subject = self.apply_flags(r["id"], r["subject"])
        #         log_msg(f"bins {old_subject = }, {subject = }")
        #         rec_rows.append(
        #             (
        #                 "record",
        #                 (r["id"], None),
        #                 f"[{color}]{r.get('itemtype', '')} {subject}[/{color}]",
        #             )
        #         )
        #
        #     all_rows: List[Tuple[str, Any, str]] = bin_rows + rec_rows
        #
        #     # ---------- paging ----------
        #     pages: List[Page] = []
        #     idx = 0
        #     first = True
        #
        #     # header (first page) + how many letters consumed by header
        #     first_header_text, first_hdr_map, header_letters = _format_path_header(
        #         path_ids, continued=False
        #     )
        #     content_capacity = max(0, page_size - header_letters)
        #
        #     while first or idx < len(all_rows):
        #         if first:
        #             header_text, hdr_map = first_header_text, dict(first_hdr_map)
        #         else:
        #             # repeated header with (continued)
        #             header_text, hdr_map, _ = _format_path_header(path_ids, continued=True)
        #
        #         rows_out: List[str] = [header_text]
        #         tag_map: Dict[str, Tuple[str, Any]] = dict(hdr_map)
        #
        #         if content_capacity == 0:
        #             # Deep path; show header-only page to avoid infinite loop
        #             pages.append((rows_out, tag_map))
        #             break
        #
        #         tagged = 0
        #         next_letter_idx = (
        #             header_letters  # content starts after header letters every page
        #         )
        #         while idx < len(all_rows) and tagged < content_capacity:
        #             kind, payload, text = all_rows[idx]
        #             idx += 1
        #             tag = chr(ord("a") + next_letter_idx)
        #             if kind == "bin":
        #                 tag_map[tag] = ("bin", payload)
        #             else:
        #                 tag_map[tag] = ("record", payload)  # (record_id, job_id)
        #             rows_out.append(f" [dim]{tag}[/dim]  {text}")
        #             tagged += 1
        #             next_letter_idx += 1
        #
        #         pages.append((rows_out, tag_map))
        #         first = False
        #
        #     return pages

        # def get_bin_pages(self, bin_id: int):
        #     """Public API the view will call."""
        #     pages = self.bin_tagger(bin_id)
        #     # Title: path text without tags, e.g. "Activities / Travel". If no path => "root".
        #     path_ids = self._bin_path_ids(bin_id)
        #     # title = " / ".join(self._bin_name(b) for b in path_ids) or ".."
        #     title = "Bins"
        #     return pages, title

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

    # def get_reminder_details(self, record_id: int) -> str:
    #     # Minimal, safe detail using your existing schema
    #     row = self.db_manager.cursor.execute(
    #         "SELECT subject, itemtype FROM Records WHERE id=?",
    #         (record_id,),
    #     ).fetchone()
    #     if not row:
    #         return "[b]Unknown reminder[/b]"
    #     old_subject, itemtype = row
    #     subject = self.apply_flags(record_id, old_subject)
    #     log_msg(f"bins new {old_subject = }, {subject = }")
    #     return f"[b]{subject}[/b]\n[dim]type:[/dim] {itemtype or '—'}"

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
                    "text": f"[bold][{HEADER_COLOR}]{tag}[/{HEADER_COLOR}][/bold]",
                }
            )

            # One row per record under this tag
            for rec in records:
                rid = rec["id"]
                subj = rec.get("subject") or ""
                flags = rec.get("flags") or ""
                # subject + flags
                display = subj + flags

                rows.append(
                    {
                        "record_id": rid,
                        "job_id": None,
                        "text": f"{display}",
                    }
                )

        if not rows:
            header = "Tags (0)"
            return page_tagger(
                [
                    {
                        "record_id": None,
                        "job_id": None,
                        "text": f"[{HEADER_COLOR}]No tags found[/{HEADER_COLOR}]",
                    }
                ]
            ), header

        pages = page_tagger(rows)
        title = f"Tags ({len(tag_groups)})"
        return pages, title
