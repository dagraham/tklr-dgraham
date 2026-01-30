import inspect
import textwrap
import shutil
import re
import os
from rich import print as rich_print
from datetime import date, datetime, timedelta, timezone
from typing import Literal, Tuple
from dateutil import tz
from pathlib import Path
from dateutil.parser import parse as dateutil_parse
from dateutil.parser import parserinfo
from zoneinfo import ZoneInfo
from .versioning import get_version

from tklr.tklr_env import TklrEnvironment

env = TklrEnvironment()
AMPM = env.config.ui.ampm
HRS_MINS = "12" if AMPM else "24"

ELLIPSIS_CHAR = "…"

REPEATING = "↻"  # Flag for @r and/or @+ reminders
OFFFSET = "⌁"  # Flag for offset task

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
BIN_COLOR = GOLDENROD
ACTIVE_BIN = GOLD
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
    "b": BIN_COLOR,
    "B": ACTIVE_BIN,
}

_TYPE_COLOR_ALIASES = {
    "event": "*",
    "task": "~",
    "available": "~",
    "finished": "x",
    "project": "^",
    "waiting": "+",
    "note": "%",
    "pastdue": "<",
    "notice": ">",
    "goal": "!",
    "draft": "?",
    "bin": "b",
    "active_bin": "B",
}


def _apply_type_color_overrides() -> None:
    overrides = getattr(env.config.ui, "colors", {}) or {}
    for key, value in overrides.items():
        if not value:
            continue
        normalized = key.strip()
        lookup = _TYPE_COLOR_ALIASES.get(normalized.lower(), normalized)
        if lookup in TYPE_TO_COLOR:
            TYPE_TO_COLOR[lookup] = value.strip()


_apply_type_color_overrides()


def _normalize_ts(value: str | None) -> str:
    if not value:
        return ""
    return value.strip().rstrip("Z")


def has_zero_time_component(value: str | None) -> bool:
    """
    Return True when the timestamp lacks an explicit time component or when its
    time portion resolves to midnight (supports HHMM and HHMMSS encodings).
    """
    text = _normalize_ts(value)
    if not text:
        return False
    if "T" not in text:
        return True
    _, time_part = text.split("T", 1)
    if not time_part:
        return True
    return time_part.strip("0") == ""


def is_all_day_text(start_text: str | None, end_text: str | None) -> bool:
    """
    Return True when a DateTimes start/end pair represents an all-day event.
    Considers date-only strings (YYYYMMDD) and midnight start/end pairs.
    """
    start = _normalize_ts(start_text)
    if not start:
        return False
    if not has_zero_time_component(start):
        return False

    end = _normalize_ts(end_text)
    if not end:
        return True

    return has_zero_time_component(end)

# class datetimeChar:
#     VSEP = "⏐"  # U+23D0  this will be a de-emphasized color
#     FREE = "─"  # U+2500  this will be a de-emphasized color
#     HSEP = "┈"  #
#     BUSY = "■"  # U+25A0 this will be busy (event) color
#     CONF = "▦"  # U+25A6 this will be conflict color
#     TASK = "▩"  # U+25A9 this will be busy (task) color
#     ADAY = "━"  # U+2501 for all day events ━
#     RSKIP = "▶"  # U+25E6 for used time
#     LSKIP = "◀"  # U+25E6 for used time
#     USED = "◦"  # U+25E6 for used time
#     REPS = "↻"  # Flag for repeating items
#     FINISHED_CHAR = "✓"
#     SKIPPED_CHAR = "✗"
#     SLOW_CHAR = "∾"
#     LATE_CHAR = "∿"
#     INACTIVE_CHAR = "≁"
#     # INACTIVE_CHAR='∽'
#     ENDED_CHAR = "≀"
#     UPDATE_CHAR = "𝕦"
#     INBASKET_CHAR = "𝕚"
#     KONNECT_CHAR = "k"
#     LINK_CHAR = "g"
#     PIN_CHAR = "p"
#     ELLIPSIS_CHAR = "…"
#     LINEDOT = " · "  # ܁ U+00B7 (middle dot),
#     ELECTRIC = "⌁"


def get_anchor(aware: bool) -> datetime:
    """
    Return the canonical 1970-01-01 anchor datetime used when normalizing dates.
    If ``aware`` is True the anchor is tagged with UTC tzinfo, otherwise it
    remains naive so callers can safely compare like-with-like values.
    """
    dt = datetime(1970, 1, 1, 0, 0, 0)
    if aware:
        return dt.replace(tzinfo=ZoneInfo("UTC"))
    return dt


def fmt_user(dt_str: str) -> str:
    """
    User friendly formatting for dates and datetimes using env settings
    for ampm, yearfirst, dayfirst and two_digit year.
    """
    if not dt_str:
        return "unscheduled"
    try:
        dt = dateutil_parse(dt_str)
    except Exception as e:
        return f"error parsing {dt_str}: {e}"
    if dt_str.endswith("T0000"):
        return dt.strftime("%Y-%m-%d")
    return dt.strftime("%Y-%m-%d %H:%M")


def parse(s, yearfirst: bool = True, dayfirst: bool = False):
    """
    Parse free-form date/datetime text using the configured ordering rules.
    Dates (no time component) are returned as ``date`` objects; timestamps are
    returned as naive ``datetime`` values with the midnight shortcut collapsed
    back to just the date.  Returns an empty string when parsing fails so
    callers can surface an error without raising.
    """
    pi = parserinfo(
        dayfirst=dayfirst, yearfirst=yearfirst
    )  # FIXME: should come from config
    dt = dateutil_parse(s, parserinfo=pi)
    if isinstance(dt, date) and not isinstance(dt, datetime):
        return dt
    if isinstance(dt, datetime):
        if dt.hour == dt.minute == 0:
            return dt.date()
        return dt
    return ""


def _to_local_naive(dt: datetime) -> datetime:
    """Convert aware dt to local naive; leave naive as is."""
    if not isinstance(dt, date) and isinstance(dt, datetime) and dt.tzinfo:
        local = dt.astimezone(tz.tzlocal()).replace(tzinfo=None)
    else:
        local = dt
    return local


def timedelta_str_to_seconds(time_str: str) -> tuple[bool, int]:
    """
    Converts a time string composed of integers followed by 'w', 'd', 'h', or 'm'
    into the total number of seconds.
    Args:
        time_str (str): The time string (e.g., '3h15s').
    Returns:
        int: The total number of seconds.
    Raises:
        ValueError: If the input string is not in the expected format.
    """
    # Define time multipliers for each unit
    multipliers = {
        "w": 7 * 24 * 60 * 60,  # Weeks to seconds
        "d": 24 * 60 * 60,  # Days to seconds
        "h": 60 * 60,  # Hours to seconds
        "m": 60,  # Minutes to seconds
        "s": 1,  # Seconds to seconds
    }
    # Match all integer-unit pairs (e.g., "3h", "15s")
    matches = re.findall(r"(\d+)([wdhms])", time_str)
    if not matches:
        return (
            False,
            "Invalid time string format. Expected integers followed by 'w', 'd', 'h', or 'm'.",
        )
    # Convert each match to seconds and sum them
    total_seconds = sum(int(value) * multipliers[unit] for value, unit in matches)
    return True, total_seconds


def fmt_utc_z(dt: datetime) -> str:
    """Aware/naive → UTC aware → 'YYYYMMDDTHHMMZ' (no seconds)."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)  # or attach your local tz then convert
    dt = dt.astimezone(timezone.utc)
    return dt.strftime("%Y%m%dT%H%MZ")


def parse_utc_z(s: str) -> datetime:
    """
    'YYYYMMDDTHHMMZ' or 'YYYYMMDDTHHMMSSZ' → aware datetime in UTC.
    Accept seconds if present; normalize to tz-aware UTC object.
    """
    if not s.endswith("Z"):
        dt = dateutil_parse(s)
        if dt.tzinfo is None:
            return dt
    body = s[:-1]
    fmt = "%Y%m%dT%H%M"
    dt = datetime.strptime(body, fmt)
    return dt.replace(tzinfo=timezone.utc)


def truncate_string(s: str, max_length: int) -> str:
    # log_msg(f"Truncating string '{s}' to {max_length} characters")
    if len(s) > max_length:
        return f"{s[: max_length - 2]} {ELLIPSIS_CHAR}"
    else:
        return s


def format_date_range(start_dt: datetime, end_dt: datetime) -> str:
    """
    Format two datetimes as a succinct date range.
    """
    same_year = start_dt.year == end_dt.year
    same_month = start_dt.month == end_dt.month
    if same_year and same_month:
        return f"{start_dt.strftime('%b %-d')} - {end_dt.strftime('%-d, %Y')}"
    if same_year:
        return f"{start_dt.strftime('%b %-d')} - {end_dt.strftime('%b %-d, %Y')}"
    return f"{start_dt.strftime('%b %-d, %Y')} - {end_dt.strftime('%b %-d, %Y')}"


def format_iso_week(monday_date: datetime) -> str:
    """
    Format a label for the ISO week containing `monday_date`.
    """
    start_dt = monday_date.date()
    end_dt = start_dt + timedelta(days=6)
    iso_yr, iso_wk, _ = start_dt.isocalendar()
    yr_wk = f"{iso_yr} #{iso_wk}"
    if start_dt.month == end_dt.month:
        return f"{start_dt.strftime('%b %-d')} - {end_dt.strftime('%-d')}, {yr_wk}"
    return f"{start_dt.strftime('%b %-d')} - {end_dt.strftime('%b %-d')}, {yr_wk}"


def get_previous_yrwk(year: int, week: int) -> tuple[int, int]:
    """Return the ISO year/week preceding the given pair."""
    monday = datetime.strptime(f"{year} {week} 1", "%G %V %u")
    prev = monday - timedelta(weeks=1)
    return prev.isocalendar()[:2]


def get_next_yrwk(year: int, week: int) -> tuple[int, int]:
    """Return the ISO year/week following the given pair."""
    monday = datetime.strptime(f"{year} {week} 1", "%G %V %u")
    nxt = monday + timedelta(weeks=1)
    return nxt.isocalendar()[:2]


def calculate_4_week_start() -> datetime:
    """
    Calculate the Monday starting the current 4-week block.
    """
    today = datetime.now()
    _, iso_week, iso_weekday = today.isocalendar()
    start_of_week = today - timedelta(days=iso_weekday - 1)
    weeks_into_cycle = (iso_week - 1) % 4
    return start_of_week - timedelta(weeks=weeks_into_cycle)


def datetime_from_timestamp(fmt_dt: str | datetime | None) -> datetime | None:
    """
    Parse a compact timestamp ('YYYYMMDD' or 'YYYYMMDDTHHMM') into a datetime.
    """
    if isinstance(fmt_dt, datetime):
        return fmt_dt
    if not fmt_dt:
        return None
    fmt_dt = str(fmt_dt).strip()
    try:
        if "T" in fmt_dt:
            return datetime.strptime(fmt_dt, "%Y%m%dT%H%M")
        return datetime.strptime(fmt_dt, "%Y%m%d")
    except ValueError:
        log_msg(f"could not parse timestamp: {fmt_dt}")
        return None


def format_time_range(start_time: str, end_time: str | None, ampm: bool = False) -> str:
    """Format a time range respecting the AM/PM preference."""
    start_dt = datetime_from_timestamp(start_time)
    end_dt = datetime_from_timestamp(end_time) if end_time else None
    if start_dt is None:
        return ""
    if end_dt is None:
        end_dt = start_dt

    if start_dt == end_dt and start_dt.hour == 0 and start_dt.minute == 0:
        return ""

    extent = start_dt != end_dt
    if ampm:
        start_fmt = "%-I:%M%p" if start_dt.hour < 12 <= end_dt.hour else "%-I:%M"
        start_str = start_dt.strftime(start_fmt).lower().replace(":00", "")
        end_str = end_dt.strftime("%-I:%M%p").lower().replace(":00", "")
        return f"{start_str}-{end_str}" if extent else end_str

    start_str = start_dt.strftime("%H:%M").replace(":00", "")
    if start_str.startswith("0"):
        start_str = start_str[1:]
    end_str = end_dt.strftime("%H:%M")
    if end_str.startswith("0"):
        end_str = end_str[1:]
    return f"{start_str}-{end_str}" if extent else end_str


def speak_time(time_int: int, mode: Literal["24", "12"]) -> str:
    """Convert a POSIX timestamp to a spoken phrase."""
    dt = datetime.fromtimestamp(time_int)
    hour = dt.hour
    minute = dt.minute

    if mode == "24":
        if minute == 0:
            return f"{hour} hours"
        else:
            return f"{hour} {minute} hours"
    else:
        return dt.strftime("%-I:%M %p").lower().replace(":00", "")


def duration_in_words(seconds: int, short: bool = False) -> str:
    """
    Convert a duration (seconds) into a human-readable string.
    """
    try:
        sign = "" if seconds >= 0 else "- "
        total_seconds = abs(int(seconds))
        units = [
            ("week", 604800),
            ("day", 86400),
            ("hour", 3600),
            ("minute", 60),
            ("second", 1),
        ]
        parts: list[str] = []
        for name, unit_seconds in units:
            value, total_seconds = divmod(total_seconds, unit_seconds)
            if value:
                parts.append(f"{sign}{value} {name}{'s' if value > 1 else ''}")
        if not parts:
            return "zero minutes"
        return " ".join(parts[:2]) if short else " ".join(parts)
    except Exception as exc:
        log_msg(f"{seconds = } raised exception: {exc}")
        return ""


def format_timedelta(seconds: int, short: bool = False) -> str:
    """
    Express a timedelta (seconds) using tokens like '+1h30m' or '-2d'.
    When ``short`` is True limit output to the first two non-zero units.
    """
    try:
        sign = "+" if seconds >= 0 else "-"
        total_seconds = abs(int(seconds))
        units = [
            ("w", 604800),
            ("d", 86400),
            ("h", 3600),
            ("m", 60),
            ("s", 1),
        ]
        parts: list[str] = []
        for label, unit_seconds in units:
            value, total_seconds = divmod(total_seconds, unit_seconds)
            if value:
                parts.append(f"{value}{label}")
        if not parts:
            return "now"
        body = "".join(parts[:2]) if short else "".join(parts)
        return sign + body
    except Exception as exc:
        log_msg(f"{seconds = } raised exception: {exc}")
        return ""


def format_datetime(fmt_dt: str, ampm: bool = False) -> str:
    """
    Convert a compact timestamp into a human-readable phrase.
    """
    if "T" in fmt_dt:
        dt = datetime.strptime(fmt_dt, "%Y%m%dT%H%M")
        is_date_only = False
    else:
        dt = datetime.strptime(fmt_dt, "%Y%m%d")
        is_date_only = True

    today = date.today()
    delta_days = (dt.date() - today).days

    if is_date_only:
        if delta_days == 0:
            return "today"
        if -6 <= delta_days <= 6:
            return dt.strftime("%A")
        return dt.strftime("%B %-d, %Y")

    suffix = dt.strftime("%p").lower() if ampm else ""
    hours = dt.strftime("%-I") if ampm else dt.strftime("%H")
    minutes = dt.strftime(":%M") if not ampm or dt.minute else ""
    seconds = dt.strftime(":%S") if dt.second else ""
    time_str = hours + minutes + seconds + suffix

    if delta_days == 0:
        return time_str
    if -6 <= delta_days <= 6:
        return f"{dt.strftime('%A')} at {time_str}"
    return f"{dt.strftime('%B %-d, %Y')} at {time_str}"


def datetime_in_words(fmt_dt: str, ampm: bool = False) -> str:
    """
    Convert a compact datetime string into a conversational description.
    """
    if "T" in fmt_dt:
        dt = datetime.strptime(fmt_dt, "%Y%m%dT%H%M%S")
    else:
        dt = datetime.strptime(fmt_dt, "%Y%m%d")
    today = date.today()
    delta_days = (dt.date() - today).days

    minutes = dt.minute
    minutes_str = (
        "" if minutes == 0 else f" o {minutes}" if minutes < 10 else f" {minutes}"
    )
    hours_str = dt.strftime("%H") if ampm else dt.strftime("%I")
    if hours_str.startswith("0"):
        hours_str = hours_str[1:]
    suffix = " hours" if ampm else " a m" if dt.hour < 12 else " p m"
    time_str = f"{hours_str}{minutes_str}{suffix}"

    if delta_days == 0:
        return time_str
    if -6 <= delta_days <= 6:
        return f"{dt.strftime('%A')} at {time_str}"
    date_str = dt.strftime("%B %-d, %Y")
    return f"{date_str} at {time_str}"


def decimal_to_base26(value: int) -> str:
    """
    Convert a non-negative integer to a base-26 string using lowercase letters.
    """
    if value < 0:
        raise ValueError("value must be non-negative")
    if value == 0:
        return "a"

    digits: list[str] = []
    while value:
        digits.append(chr(ord("a") + (value % 26)))
        value //= 26
    return "".join(reversed(digits))


def indx_to_tag(index: int, fill: int = 1) -> str:
    """
    Map a 0-based index to a tag string (a, b, ..., aa, ab, ...),
    left-padding with 'a' when a wider tag width is required.
    """
    if index < 0:
        raise ValueError("index must be non-negative")
    return decimal_to_base26(index).rjust(fill, "a")


def _get_runtime_home() -> Path:
    override = os.environ.get("TKLR_HOME")
    if override:
        return Path(override).expanduser()
    return env.home


def _resolve_log_file_path(file_path: str | Path) -> Path:
    path = Path(file_path)
    if path.is_absolute():
        return path
    return _get_runtime_home() / path


def _default_log_relative_path(kind: str) -> Path:
    """Return logs/log_<YYMMDD>.md style paths under the runtime home."""
    suffix = datetime.now().strftime("%y%m%d")
    return Path("logs") / f"{kind}_{suffix}.md"


def log_msg(
    msg: str,
    file_path: str | Path | None = None,
    print_output: bool = False,
):
    """
    Log a message and save it directly to a file.

    Args:
        msg (str): The message to log.
        file_path (str | Path | None, optional): Overrides the default path when
            provided. Defaults to ``None`` which writes to ``logs/log_<YYMMDD>.md``.
        print_output (bool, optional): If True, also print to console.
    """
    frame = inspect.stack()[1].frame
    func_name = frame.f_code.co_name

    # Default: just function name
    caller_name = func_name

    # Detect instance/class/static context
    if "self" in frame.f_locals:  # instance method
        cls_name = frame.f_locals["self"].__class__.__name__
        caller_name = f"{cls_name}.{func_name}"
    elif "cls" in frame.f_locals:  # classmethod
        cls_name = frame.f_locals["cls"].__name__
        caller_name = f"{cls_name}.{func_name}"

    # Format the line header
    lines = [
        f"- {datetime.now().strftime('%H:%M:%S')} log_msg ({caller_name}):  ",
    ]
    # Wrap the message text
    lines.extend(
        [
            f"\n{x}"
            for x in textwrap.wrap(
                msg.strip(),
                width=shutil.get_terminal_size()[0] - 6,
                initial_indent="   ",
                subsequent_indent="   ",
            )
        ]
    )
    lines.append("\n\n")

    # Best-effort file logging; fall back to console when the file is unwritable.
    if file_path is None:
        file_path = _default_log_relative_path("log")
    log_path = _resolve_log_file_path(file_path)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        with open(log_path, "a") as f:
            f.writelines(lines)
    except OSError:
        print_output = True

    if print_output:
        print("".join(lines))


def bug_msg(
    msg: str,
    file_path: str | Path | None = None,
    print_output: bool = False,
):
    """
    Companion to log_msg for temporary debugging.

    Args:
        msg (str): The message to log.
        file_path (str | Path | None, optional): Overrides the default path when
            provided. Defaults to ``None`` which writes to ``logs/bug_<YYMMDD>.md``.
        print_output (bool, optional): If True, also print to console.
    """
    frame = inspect.stack()[1].frame
    func_name = frame.f_code.co_name

    # Default: just function name
    caller_name = func_name

    # Detect instance/class/static context
    if "self" in frame.f_locals:  # instance method
        cls_name = frame.f_locals["self"].__class__.__name__
        caller_name = f"{cls_name}.{func_name}"
    elif "cls" in frame.f_locals:  # classmethod
        cls_name = frame.f_locals["cls"].__name__
        caller_name = f"{cls_name}.{func_name}"

    # Format the line header
    lines = [
        f"- {datetime.now().strftime('%H:%M:%S')} bug_msg ({caller_name}):  ",
    ]
    # Wrap the message text
    lines.extend(
        [
            f"\n{x}"
            for x in textwrap.wrap(
                msg.strip(),
                width=shutil.get_terminal_size()[0] - 6,
                initial_indent="   ",
                subsequent_indent="   ",
            )
        ]
    )
    lines.append("\n\n")

    if file_path is None:
        file_path = _default_log_relative_path("bug")
    log_path = _resolve_log_file_path(file_path)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        with open(log_path, "a") as f:
            f.writelines(lines)
    except OSError:
        print_output = True

    if print_output:
        print("".join(lines))


def print_msg(msg: str, file_path: str = "log_msg.md", print_output: bool = False):
    """
    Log a message and save it directly to a specified file.

    Args:
        msg (str): The message to log.
        file_path (str, optional): Path to the log file. Defaults to "log_msg.txt".
    """
    caller_name = inspect.stack()[1].function
    lines = [
        f"{caller_name}",
    ]
    lines.extend(
        [
            f"\n{x}"
            for x in textwrap.wrap(
                msg.strip(),
                width=shutil.get_terminal_size()[0] - 6,
                initial_indent="   ",
                subsequent_indent="   ",
            )
        ]
    )

    # Save the message to the file
    # print("".join(lines))
    for line in lines:
        rich_print(line)
