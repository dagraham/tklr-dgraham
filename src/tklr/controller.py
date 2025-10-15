from __future__ import annotations
from packaging.version import parse as parse_version
from importlib.metadata import version

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
from typing import List, Tuple, Optional, Dict, Any
from bisect import bisect_left, bisect_right

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
BEGIN_COLOR = GOLD
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
BEGINBY = "⋙"

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
    ">": BEGIN_COLOR,  # begin
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


def format_tokens(tokens, width):
    # tokens = json.loads(tokens)
    output_lines = []
    current_line = ""

    for i, t in enumerate(tokens):
        token = t["token"].rstrip()
        key = t.get("key", "")
        # log_msg(f"processing {key = } in {token = }, {token.startswith('@~')}")

        if t["t"] == "itemtype":
            current_line = ""

        if key == "@d":
            # Handle @d and @~ blocks: always on their own, preserve and wrap content
            if current_line:
                output_lines.append(current_line)
                current_line = ""
            output_lines.append("")  # extra newline before @d
            wrapped_lines = []
            for line in token.splitlines():
                indent = len(line) - len(line.lstrip(" "))
                wrap = textwrap.wrap(line, width=width, subsequent_indent=" " * indent)
                wrapped_lines.extend(wrap or [""])
            output_lines.extend(wrapped_lines)
            output_lines.append("")  # extra newline after @d
            continue

        if token.startswith("@~"):
            # Begin component tasks on a new line
            output_lines.append(current_line)
            current_line = " "

        # Calculate length if this token is added to current_line
        if len(current_line) + len(token) + 1 > width:
            output_lines.append(current_line)
            current_line = ""

        if current_line:
            current_line += " "

        # current_line += f"{token} "
        current_line += token

    if current_line:
        output_lines.append(current_line)

    def highlight(line):
        # Highlight @x and &x preceded by space or line start, followed by space
        color = {
            "@": f"{at_color}",
            "&": f"{am_color}",
        }
        return re.sub(
            r"(^|(?<=\s))([@&]\S\s)",
            # lambda m: m.group(1) + f"[yellow]{m.group(2)}[/yellow]",
            lambda m: m.group(1)
            + f"[{color[m.group(2)[0]]}]{m.group(2)}[/{color[m.group(2)[0]]}]",
            line,
        )

    if (
        len(output_lines) >= 1
        and output_lines[0]
        and output_lines[0].startswith("entry: ")
    ):
        line = output_lines.pop(0)
        line = f"[{label_color}]entry:[/label_color] [bold yellow]{line[8]}[/bold yellow]{line[9:]}"
        # line = f"[bold yellow]{line[4]}[/bold yellow]{line[5:]}"
        output_lines.insert(0, line)
    # log_msg(f"{output_lines = }")

    return "\n ".join(highlight(line) for line in output_lines)


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
    return "\n           ".join(out)


def format_hours_mins(dt: datetime, mode: Literal["24", "12"]) -> str:
    """
    Format a datetime object as hours and minutes.
    """
    fmt = {
        "24": "%H:%M",
        "12": "%I:%M%p",
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


class Controller:
    def __init__(self, database_path: str, env: TklrEnvironment, reset: bool = False):
        # Initialize the database manager
        self.db_manager = DatabaseManager(database_path, env, reset=reset)

        self.tag_to_id = {}  # Maps tag numbers to event IDs
        self.list_tag_to_id: dict[str, dict[str, object]] = {}

        self.yrwk_to_details = {}  # Maps (iso_year, iso_week) to week description
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
                rruleset, width=self.width - 11, subsequent_indent=11
            )
            rr_line = f"[{label_color}]rruleset:[/{label_color}]  {formatted_rr}"

        job = (
            f" [{label_color}]job_id:[/{label_color}] [bold]{job_id}[/bold]"
            if job_id
            else ""
        )
        lines.extend(
            [
                # f"[{label_color}]entry:[/{label_color}] {entry}",
                entry,
                " ",
                f"[{label_color}]record_id:[/{label_color}] {record_id}{job}",
                rr_line,
                f"[{label_color}]created:[/{label_color}]   {created}",
                f"[{label_color}]modified:[/{label_color}]  {modified}",
            ]
        )

        return lines

    def update_record_from_item(self, item) -> None:
        self.cursor.execute(
            """
            UPDATE Records
            SET itemtype=?, subject=?, description=?, rruleset=?, timezone=?,
                extent=?, alerts=?, beginby=?, context=?, jobs=?, tags=?,
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
                item.beginby or "",
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

    def populate_beginby(self):
        self.db_manager.populate_beginby()

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

    # def process_tag(self, tag: str, view: str, selected_week: tuple[int, int]):
    #     if view == "week":
    #         log_msg(
    #             f"{selected_week = }, {tag = }, {self.week_tag_to_id[selected_week] = }"
    #         )
    #         payload = self.week_tag_to_id[selected_week].get(tag)
    #         if payload is None:
    #             return [f"There is no item corresponding to tag '{tag}'."]
    #         if isinstance(payload, dict):
    #             log_msg(f"{payload = }")
    #             record_id = payload.get("record_id")
    #             job_id = payload.get("job_id")
    #         else:
    #             # backward compatibility (old mapping was tag -> record_id)
    #             log_msg(f"{payload = }")
    #             record_id, job_id = payload, None
    #
    #     elif view in [
    #         "next",
    #         "last",
    #         "find",
    #         "events",
    #         "tasks",
    #         "agenda-events",
    #         "agenda-tasks",
    #         "alerts",
    #     ]:
    #         payload = self.list_tag_to_id.get(view, {}).get(tag)
    #         log_msg(f"{payload = }")
    #         if payload is None:
    #             return [f"There is no item corresponding to tag '{tag}'."]
    #         if isinstance(payload, dict):
    #             record_id = payload.get("record_id")
    #             job_id = payload.get("job_id")
    #         else:
    #             # backward compatibility (old mapping was tag -> record_id)
    #             record_id, job_id = payload, None
    #     else:
    #         return ["Invalid view."]
    #
    #     # log_msg(f"got {record_id = } for {tag = }")
    #     core = self.get_record_core(record_id) or {}
    #     log_msg(f"{core = }")
    #     subject = core.get("subject") or "(untitled)"
    #     itemtype = core.get("itemtype") or ""
    #     rruleset = core.get("rrulestr") or ""
    #     all_prereqs = core.get("all_prereqs") or ""
    #
    #     try:
    #         pinned_now = (
    #             self.db_manager.is_task_pinned(record_id) if itemtype == "~" else False
    #         )
    #     except Exception:
    #         pinned_now = False
    #
    #     fields = self.get_entry(record_id, job_id)
    #     # if job_id is not None:
    #     #     fields = [f"[{label_color}]job_id:[/{label_color}] {job_id}"] + fields
    #     job = (
    #         f" [{label_color}]job_id:[/{label_color}] [bold]{job_id}[/bold]"
    #         if job_id
    #         else ""
    #     )
    #     title = f"[{label_color}]details for:[/{label_color}] [bold]{subject}[/bold]"
    #     ids = f"[{label_color}]id:[/{label_color}] [bold]{record_id}[/bold]{job}"
    #
    #     # <-- this is your existing single source of truth for DetailsScreen
    #     self._last_details_meta = {
    #         "record_id": record_id,
    #         "job_id": job_id,
    #         "itemtype": itemtype,  # "~" task, "*" event, etc.
    #         "rruleset": rruleset,
    #         "all_prereqs": all_prereqs,
    #         "pinned": bool(pinned_now),
    #         "record": self.db_manager.get_record(record_id),
    #     }
    #
    #     return [title, ids] + fields

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

    # def generate_table(self, start_date, selected_week, grouped_events):
    #     """
    #     Generate a Rich table displaying events for the specified 4-week period.
    #     """
    #     selected_week = self.selected_week
    #     end_date = start_date + timedelta(weeks=4) - ONEDAY  # End on a Sunday
    #     start_date = start_date
    #     today_year, today_week, today_weekday = datetime.now().isocalendar()
    #     tomorrow_year, tomorrow_week, tomorrow_day = (
    #         datetime.now() + ONEDAY
    #     ).isocalendar()
    #     title = f"Schedule for {format_iso_week(start_date)}"
    #
    #     table = Table(
    #         show_header=True,
    #         header_style=HEADER_STYLE,
    #         show_lines=True,
    #         style=FRAME_COLOR,
    #         expand=True,
    #         box=box.SQUARE,
    #         # title=title,
    #         # title_style="bold",
    #     )
    #
    #     weekdays = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    #     for day in weekdays:
    #         table.add_column(
    #             day,
    #             justify="center",
    #             style=DAY_COLOR,
    #             width=8,
    #             ratio=1,
    #         )
    #
    #     self.rownum_to_details = {}  # Reset for this period
    #     current_date = start_date
    #     weeks = []
    #     row_num = 0
    #     while current_date <= end_date:
    #         yr_wk = current_date.isocalendar()[:2]
    #         iso_year, iso_week = yr_wk
    #         if yr_wk not in weeks:
    #             weeks.append(yr_wk)
    #         # row_num += 1
    #         row_num = f"{yr_wk[1]:>2}"
    #         self.rownum_to_yrwk[row_num] = yr_wk
    #         # row = [f"[{DIM_COLOR}]{row_num}[{DIM_COLOR}]\n"]
    #         SELECTED = yr_wk == selected_week
    #         row = []
    #
    #         for weekday in range(1, 8):  # ISO weekdays: 1 = Monday, 7 = Sunday
    #             date = datetime.strptime(f"{iso_year} {iso_week} {weekday}", "%G %V %u")
    #             monthday_str = date.strftime(
    #                 "%-d"
    #             )  # Month day as string without leading zero
    #             events = (
    #                 grouped_events.get(iso_year, {}).get(iso_week, {}).get(weekday, [])
    #             )
    #             today = (
    #                 iso_year == today_year
    #                 and iso_week == today_week
    #                 and weekday == today_weekday
    #             )
    #             # tomorrow = (
    #             #     iso_year == tomorrow_year
    #             #     and iso_week == tomorrow_week
    #             #     and weekday == tomorrow_day
    #             # )
    #
    #             # mday = monthday_str
    #             mday = f"{monthday_str:>2}"
    #             if today:
    #                 mday = (
    #                     f"[bold][{TODAY_COLOR}]{monthday_str:>2}[/{TODAY_COLOR}][/bold]"
    #                 )
    #
    #             if events:
    #                 tups = [event_tuple_to_minutes(ev[0], ev[1]) for ev in events]
    #                 aday_str, busy_str = get_busy_bar(tups)
    #                 # log_msg(f"{date = }, {tups = }, {busy_str = }")
    #                 if aday_str:
    #                     row.append(f"{aday_str + mday + aday_str:>4}{busy_str}")
    #                 else:
    #                     row.append(f"{mday:>2}{busy_str}")
    #             else:
    #                 row.append(f"{mday}\n")
    #
    #             if SELECTED:
    #                 row = [
    #                     f"[{SELECTED_COLOR}]{cell}[/{SELECTED_COLOR}]" for cell in row
    #                 ]
    #         if SELECTED:
    #             table.add_row(*row, style=f"on {SELECTED_BACKGROUND}")
    #
    #         else:
    #             table.add_row(*row)
    #         self.yrwk_to_details[yr_wk] = self.get_week_details((iso_year, iso_week))
    #         current_date += timedelta(weeks=1)
    #
    #     return title, table
    #
    # def get_table_and_list(self, start_date: datetime, selected_week: Tuple[int, int]):
    #     """
    #     - rich_display(start_datetime, selected_week)
    #         - sets:
    #             self.tag_to_id = {}  # Maps tag numbers to event IDs
    #             self.yrwk_to_details = {}  # Maps (iso_year, iso_week), to the description for that week
    #             self.rownum_to_yrwk = {}  # Maps row numbers to (iso_year, iso_week) for the current period
    #         - return title
    #         - return table
    #         - return description for selected_week
    #     """
    #     log_msg(f"Getting table for {start_date = }, {selected_week = }")
    #     self.selected_week = selected_week
    #     current_start_year, current_start_week, _ = start_date.isocalendar()
    #     self.db_manager.extend_datetimes_for_weeks(
    #         current_start_year, current_start_week, 4
    #     )
    #     grouped_events = self.db_manager.process_events(
    #         start_date, start_date + timedelta(weeks=4)
    #     )
    #
    #     # Generate the table
    #     title, table = self.generate_table(start_date, selected_week, grouped_events)
    #     log_msg(
    #         f"Generated table for {title}, {selected_week = }, {self.afill_by_week.get(selected_week) = }"
    #     )
    #
    #     if selected_week in self.yrwk_to_details:
    #         description = self.yrwk_to_details[selected_week]
    #     else:
    #         description = "No week selected."
    #     return title, table, description

    def get_table_and_list(self, start_date: datetime, selected_week: tuple[int, int]):
        """
        Return the header title, busy bar (as text), and event list details
        for the given ISO week.

        Returns: (title, busy_bar_str, details_list)
        """
        year, week = selected_week
        year_week = f"{year:04d}-{week:02d}"

        # --- 1. Busy bits from BusyWeeks table
        busy_bits = self.db_manager.get_busy_bits_for_week(year_week)
        busy_bar = self._format_busy_bar(busy_bits)

        # --- 2. Week events using your existing method
        start_dt = datetime.strptime(f"{year} {week} 1", "%G %V %u")
        end_dt = start_dt + timedelta(weeks=1)
        details = self.get_week_details(selected_week)

        # title = f"{format_date_range(start_dt, end_dt)} #{start_dt.isocalendar().week}"
        title = format_iso_week(start_dt)
        # --- 3. Title for the week header
        # title = f"Week {week} — {start_dt.strftime('%b %d')} to {(end_dt - timedelta(days=1)).strftime('%b %d')}"

        return title, busy_bar, details

    # def _format_busy_bar(self, bits: list[int]) -> str:
    #     """
    #     Render 35 busy bits (7×[1 all-day + 4×6h blocks]) as a two-row week bar.
    #     """
    #     DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    #     assert len(bits) == 35, "expected 35 bits (7×5)"
    #     chars = {0: " ", 1: "█", 2: "▓"}  # free, busy, conflict
    #     rows = []
    #     # top: day headers, centered in 5 columns
    #     # headers = " ".join(f" {d:^5} " for d in DAYS)
    #     headers = "|".join(f" {d:^3} " for d in DAYS)
    #     log_msg(f"{headers = }")
    #     rows.append(f"|{headers}|")
    #
    #     # bottom: 5-slot cells under each header
    #     for block in range(5):  # all-day + 4×6h blocks
    #         row = ""
    #         for day in range(7):
    #             idx = day * 5 + block
    #             row += f"{chars[bits[idx]] * 5}"
    #         rows.append(row)
    #
    #     return "\n".join(rows)
    #
    # def _format_busy_bar(self, bits: list[int]) -> str:
    #     """
    #     Render 35 busy bits (7×[1 all-day + 4×6h blocks])
    #     as a compact one-row week bar under the weekday headers.
    #     """
    #     DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    #     assert len(bits) == 35, "expected 35 bits (7×5)"
    #     chars = {0: " ", 1: "█", 2: "▓"}  # free, busy, conflict
    #     rows = []
    #
    #     # header line
    #     headers = "|".join(f" {d:^3} " for d in DAYS)
    #     rows.append(f"|{headers}|")
    #
    #     # single busy row
    #     day_blocks = []
    #     for day in range(7):
    #         start = day * 5
    #         segment = "".join(chars[bits[start + i]] for i in range(5))
    #         day_blocks.append(segment)
    #
    #     busy_line = "|".join(day_blocks)
    #     rows.append(f"|{busy_line}|")
    #
    #     return "\n".join(rows)

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
        Fetch and format description for a specific week.
        """
        # log_msg(f"Getting description for week {yr_wk}")
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
        description = [header]

        self.set_week_afill(events, yr_wk)

        if not events:
            description.append(
                f" [{HEADER_COLOR}]Nothing scheduled for this week[/{HEADER_COLOR}]"
            )
            # return "\n".join(description)
            return description

        weekday_to_events = {}
        for i in range(7):
            this_day = (start_datetime + timedelta(days=i)).date()
            weekday_to_events[this_day] = []

        for start_ts, end_ts, itemtype, subject, id, job_id in events:
            start_dt = datetime_from_timestamp(start_ts)
            end_dt = datetime_from_timestamp(end_ts)
            if itemtype == "*":  # event
                # 🪄 new line: replace {XXX} with ordinal instance
                subject = self.apply_anniversary_if_needed(id, subject, start_dt)
                log_msg(
                    f"Week description {itemtype = }, {subject = }, {start_dt = }, {end_dt = }"
                )
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

            row = [
                id,
                job_id,
                f"[{type_color}]{itemtype} {escaped_start_end}{subject}[/{type_color}]",
            ]
            weekday_to_events.setdefault(start_dt.date(), []).append(row)

        indx = 0

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
                description.append(
                    # f" [bold][yellow]{day.strftime('%A, %B %-d')}[/yellow][/bold]"
                    # f"[not bold][{HEADER_COLOR}]{day.strftime('%a, %b %-d')}{flag}[/{HEADER_COLOR}][/not bold]"
                    f"[bold][{HEADER_COLOR}]{day.strftime('%a, %b %-d')}{flag}[/{HEADER_COLOR}][/bold]"
                )
                for event in events:
                    event_id, job_id, event_str = event
                    # log_msg(f"{event_str = }")
                    # tag_fmt, indx = self.add_tag(yr_wk, indx, event_id)
                    # tag = indx_to_tag(indx, self.afill)
                    # self.tag_to_id[yr_wk][tag] = event_id
                    # description.append(f" [dim]{tag}[/dim]   {event_str}")
                    tag_fmt, indx = self.add_week_tag(yr_wk, indx, event_id, job_id)
                    description.append(f"{tag_fmt} {event_str}")
                    # indx += 1
        # NOTE: maybe return list for scrollable view?
        # details_str = "\n".join(description)
        self.yrwk_to_details[yr_wk] = description
        log_msg(f"{description = }")
        return description

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
        header = f"next instances ({len(events)})"
        # description = [f"[not bold][{header_color}]{header}[/{header_color}][/not bold]"]
        display = [header]

        if not events:
            display.append(f" [{HEADER_COLOR}]nothing found[/{HEADER_COLOR}]")
            return display

        # use a, ..., z if len(events) <= 26 else use aa, ..., zz
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
            monthday = start_dt.strftime("%m-%d")
            start_end = f"{monthday}{format_hours_mins(start_dt, HRS_MINS):>8}"
            type_color = TYPE_TO_COLOR[itemtype]
            escaped_start_end = f"[not bold]{start_end}[/not bold]"
            row = [
                id,
                job_id,
                f"[{type_color}]{itemtype} {escaped_start_end:<12}  {subject}[/{type_color}]",
            ]
            # yr_mnth_to_events.setdefault(start_dt.strftime("%B %Y"), []).append(row)
            year_to_events.setdefault(start_dt.strftime("%Y"), []).append(row)

        self.set_afill(events, "next")

        self.list_tag_to_id.setdefault("next", {})
        indx = 0

        for ym, events in year_to_events.items():
            if events:
                display.append(
                    f"[not bold][{HEADER_COLOR}]{ym}[/{HEADER_COLOR}][/not bold]"
                )
                for event in events:
                    event_id, job_id, event_str = event
                    tag_fmt, indx = self.add_tag("next", indx, event_id, job_id=job_id)
                    display.append(f"{tag_fmt}{event_str}")
        return display

    def get_last(self):
        """
        Fetch and format description for the next instances.
        """
        events = self.db_manager.get_last_instances()
        header = f"Last instances ({len(events)})"
        # description = [f"[not bold][{HEADER_COLOR}]{header}[/{HEADER_COLOR}][/not bold]"]
        display = [header]

        if not events:
            display.append(f" [{HEADER_COLOR}]Nothing found[/{HEADER_COLOR}]")
            # return "\n".join(display)
            return display

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
            monthday = start_dt.strftime("%m-%d")
            start_end = f"{monthday}{format_hours_mins(start_dt, HRS_MINS):>8}"
            type_color = TYPE_TO_COLOR[itemtype]
            escaped_start_end = f"[not bold]{start_end}[/not bold]"
            row = [
                id,
                job_id,
                f"[{type_color}]{itemtype} {escaped_start_end:<12}  {subject}[/{type_color}]",
            ]
            year_to_events.setdefault(start_dt.strftime("%Y"), []).append(row)

        self.set_afill(events, "last")
        self.list_tag_to_id.setdefault("last", {})

        indx = 0

        for ym, events in year_to_events.items():
            if events:
                display.append(
                    # f" [bold][yellow]{day.strftime('%A, %B %-d')}[/yellow][/bold]"
                    f"[not bold][{HEADER_COLOR}]{ym}[/{HEADER_COLOR}][/not bold]"
                )
                for event in events:
                    event_id, job_id, event_str = event
                    # log_msg(f"{event_str = }")
                    # tag = indx_to_tag(indx, self.afill)
                    # tag_fmt, indx = self.add_tag("last", indx, event_id)
                    tag_fmt, indx = self.add_tag("last", indx, event_id, job_id=job_id)
                    # self.list_tag_to_id["last"][tag] = event_id
                    display.append(f"{tag_fmt}{event_str}")
        return display

    def find_records(self, search_str: str):
        """
        Fetch and format description for the next instances.
        """
        events = self.db_manager.find_records(search_str)
        header = f"Items ({len(events)})\n containing a match for [{SELECTED_COLOR}]{search_str}[/{SELECTED_COLOR}] "
        description = header.split("\n")

        if not events:
            description.append(f" [{HEADER_COLOR}]Nothing found[/{HEADER_COLOR}]")
            # return "\n".join(description)
            return description

        # use a, ..., z if len(events) <= 26 else use aa, ..., zz
        self.set_afill(events, "find")

        self.list_tag_to_id.setdefault("find", {})

        indx = 0

        for record_id, subject, _, itemtype, last_ts, next_ts in events:
            subject = f"{truncate_string(subject, 30):<30}"
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
            row = f"[{type_color}]{itemtype} {subject} {escaped_last} {escaped_next}[/{type_color}]"
            tag_fmt, indx = self.add_tag("find", indx, record_id)
            description.append(f"{tag_fmt} {row}")
        return description

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
            log_msg(f"{start_ts = }, {end_ts = }, {subject = }")
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

    def get_agenda_events(self, now: datetime = datetime.now()):
        """
        Returns dict: date -> list of (tag, label, subject) for up to three days.
        Rules:
        • Pick the first 3 days that have events.
        • Also include TODAY if it has beginby/drafts even with no events.
        • If nothing to display at all, return {}.
        """
        begin_records = (
            self.db_manager.get_beginby_for_events()
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

        # 2) If today has begin/draft items, include it even if it has no events
        has_today_meta = bool(begin_records or draft_records)
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
            return {}

        # 4) Build events_by_date only for allowed dates
        events_by_date: dict[date, list[tuple[int, str, str]]] = {}

        for d in allowed_dates:
            entries = grouped_by_date.get(d, [])
            for _, (start_ts, end_ts, subject, record_id, job_id) in entries:
                end_ts = end_ts or start_ts
                label = format_time_range(start_ts, end_ts, self.AMPM)
                if end_ts.endswith("T000000"):
                    color = ALLDAY_COLOR
                elif end_ts <= now_ts and end_ts != start_ts:
                    color = PASSED_EVENT
                elif start_ts <= now_ts:
                    color = ACTIVE_EVENT
                else:
                    color = EVENT_COLOR
                events_by_date.setdefault(d, []).append(
                    (
                        record_id,
                        f"[{color}]{label}[/{color}]" if label.strip() else "",
                        f"[{color}]{subject}[/{color}]",
                    )
                )

        # 5) If TODAY is in allowed_dates (either because it had events or we added it)
        #    attach beginby + draft markers even if it had no events
        if today in allowed_dates:
            if begin_records:
                for record_id, days_remaining, subject in begin_records:
                    events_by_date.setdefault(today, []).append(
                        (
                            record_id,
                            f"[{BEGIN_COLOR}]+{days_remaining}d{BEGINBY}[/{BEGIN_COLOR}]",
                            f"[{BEGIN_COLOR}]{subject}[/{BEGIN_COLOR}]",
                        )
                    )
            if draft_records:
                for record_id, subject in draft_records:
                    events_by_date.setdefault(today, []).append(
                        (
                            record_id,
                            f"[{DRAFT_COLOR}] ? [/{DRAFT_COLOR}]",
                            f"[{DRAFT_COLOR}]{subject}[/{DRAFT_COLOR}]",
                        )
                    )

        # 6) Tagging and indexing
        total_items = sum(len(v) for v in events_by_date.values())
        if total_items == 0:
            # Edge case: allowed_dates may exist but nothing actually added (shouldn’t happen, but safe-guard)
            return {}

        self.set_afill(range(total_items), "events")
        # self.afill_by_view["events"] = self.afill
        self.list_tag_to_id.setdefault("events", {})

        indexed_events_by_date: dict[date, list[tuple[str, str, str]]] = {}
        tag_index = 0
        for d in sorted(events_by_date.keys()):
            for record_id, label, subject in events_by_date[d]:
                tag_fmt, tag_index = self.add_tag("events", tag_index, record_id)
                indexed_events_by_date.setdefault(d, []).append(
                    (tag_fmt, label, subject)
                )

        return indexed_events_by_date

    def get_agenda_tasks(self):
        """
        Returns list of (urgency_str_or_pin, color, tag_fmt, colored_subject)
        Suitable for the Agenda Tasks pane.
        """
        tasks_by_urgency = []

        # Use the JOIN with Pinned so pins persist across restarts
        urgency_records = self.db_manager.get_urgency()
        # rows: (record_id, job_id, subject, urgency, color, status, weights, pinned_int)

        self.set_afill(urgency_records, "tasks")
        log_msg(f"urgency_records {self.afill_by_view = }, {len(urgency_records) = }")
        indx = 0
        self.list_tag_to_id.setdefault("tasks", {})

        # Agenda tasks (has job_id)
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
            log_msg(f"collecting tasks {record_id = }, {job_id = }, {subject = }")
            tag_fmt, indx = self.add_tag("tasks", indx, record_id, job_id=job_id)
            urgency_str = (
                "📌" if pinned else f"[{color}]{int(round(urgency * 100)):>2}[/{color}]"
            )
            tasks_by_urgency.append(
                (
                    urgency_str,
                    color,
                    tag_fmt,
                    f"[{TASK_COLOR}]{subject}[/{TASK_COLOR}]",
                )
            )

        return tasks_by_urgency

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

    def get_record_details(self, record_id: int) -> str:
        """Fetch record details formatted for the details pane."""
        record = self.db_manager.get_record(record_id)
        if not record:
            return "[red]No details found[/red]"

        subject = record[2]
        desc = record[3] or ""
        itemtype = record[1]
        return f"[bold]{itemtype}[/bold]  {subject}\n\n{desc}"
