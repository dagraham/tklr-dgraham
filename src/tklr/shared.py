import inspect
import textwrap
import shutil
import re
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
    # enable pi when read by main and settings is available
    pi = parserinfo(
        dayfirst=dayfirst, yearfirst=yearfirst
    )  # FIXME: should come from config
    # logger.debug(f"parsing {s = } with {kwd = }")
    dt = dateutil_parse(s, parserinfo=pi)
    if isinstance(dt, date) and not isinstance(dt, datetime):
        return dt
    if isinstance(dt, datetime):
        if dt.hour == dt.minute == 0:
            return dt.date()
        return dt
    return ""


def dt_as_utc_timestamp(dt: datetime) -> int:
    if not isinstance(dt, datetime):
        return 0
    return round(dt.astimezone(tz.UTC).timestamp())


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


# ---------- DateTimes (local-naive, minute precision) ----------
def fmt_local_compact(dt: datetime) -> str:
    """Local-naive → 'YYYYMMDD' or 'YYYYMMDDTHHMM' (no seconds)."""
    if dt.hour == dt.minute == dt.second == 0:
        return dt.strftime("%Y%m%d")
    return dt.strftime("%Y%m%dT%H%M")


def parse_local_compact(s: str) -> datetime:
    """'YYYYMMDD' or 'YYYYMMDDTHHMM' → local-naive datetime."""
    if len(s) == 8:
        return datetime.strptime(s, "%Y%m%d")
    if len(s) == 13 and s[8] == "T":
        return datetime.strptime(s, "%Y%m%dT%H%M")
    raise ValueError(f"Bad local-compact datetime: {s!r}")


# FIXME: not needed without seconds
# ---------- Alerts (local-naive, second precision) ----------
# def fmt_local_seconds(dt: datetime) -> str:
#     """Local-naive → 'YYYYMMDDTHHMMSS'."""
#     return dt.strftime("%Y%m%dT%H%M%S")
#
#
# def parse_local_seconds(s: str) -> datetime:
#     """'YYYYMMDDTHHMMSS' → local-naive datetime."""
#     return datetime.strptime(s, "%Y%m%dT%H%M%S")
#


# ---------- Aware UTC (with trailing 'Z', minute precision) ----------
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
        raise ValueError(f"UTC-Z string must end with 'Z': {s!r}")
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


def log_msg(msg: str, file_path: str = "log_msg.md", print_output: bool = False):
    """
    Log a message and save it directly to a specified file.

    Args:
        msg (str): The message to log.
        file_path (str, optional): Path to the log file. Defaults to "log_msg.md".
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
        f"- {datetime.now().strftime('%y-%m-%d %H:%M:%S')} ({caller_name}):  ",
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

    # Save the message to the file
    with open(file_path, "a") as f:
        f.writelines(lines)

    # Optional console print
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


def display_messages(file_path: str = "log_msg.md"):
    """
    Display all logged messages from the specified file.

    Args:
        file_path (str, optional): Path to the log file. Defaults to "log_msg.txt".
    """
    try:
        # Read messages from the file
        with open(file_path, "r") as f:
            markdown_content = f.read()
        markdown = Markdown(markdown_content)
        console = Console()
        console.print(markdown)
    except FileNotFoundError:
        print(f"Error: Log file '{file_path}' not found.")


def format_time_range(start_time: str, end_time: str, ampm: bool = False) -> str:
    """Format time range respecting ampm setting."""
    start_dt = datetime_from_timestamp(start_time)
    end_dt = datetime_from_timestamp(end_time) if end_time else None
    # log_msg(f"{start_dt = }, {end_dt = }")

    if not end_dt:
        end_dt = start_dt

    extent = start_dt != end_dt

    if start_dt == end_dt and start_dt.hour == 0 and start_dt.minute == 0:
        return ""

    if ampm:
        start_fmt = "%-I:%M%p" if start_dt.hour < 12 and end_dt.hour >= 12 else "%-I:%M"
        start_hour = start_dt.strftime(f"{start_fmt}").lower().replace(":00", "")
        end_hour = (
            end_dt.strftime("%-I:%M%p").lower().replace(":00", "")  # .replace("m", "")
        )
        # log_msg(f"{start_hour = }, {end_hour = }")
        return f"{start_hour}-{end_hour}" if extent else f"{end_hour}"
    else:
        start_hour = start_dt.strftime("%H:%M").replace(":00", "")
        if start_hour.startswith("0"):
            start_hour = start_hour[1:]
        end_hour = end_dt.strftime("%H:%M")  # .replace(":00", "")
        if end_hour.startswith("0"):
            end_hour = end_hour[1:]
        # log_msg(f"{start_hour = }, {end_hour = }")
        return f"{start_hour}-{end_hour}" if extent else f"{end_hour}"


def speak_time(time_int: int, mode: Literal["24", "12"]) -> str:
    """Convert time into a spoken phrase for 24-hour or 12-hour format."""
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


def duration_in_words(seconds: int, short=False):
    """
    Convert a duration in seconds into a human-readable string (weeks, days, hours, minutes).

    Args:
        seconds (int): Duration in seconds.
        short (bool): If True, return a shortened version (max 2 components).

    Returns:
        str: Human-readable duration (e.g., "1 week 2 days", "3 hours 27 minutes").
    """
    try:
        # Handle sign for negative durations
        sign = "" if seconds >= 0 else "- "
        total_seconds = abs(int(seconds))

        # Define time units in seconds
        units = [
            ("week", 604800),  # 7 * 24 * 60 * 60
            ("day", 86400),  # 24 * 60 * 60
            ("hour", 3600),  # 60 * 60
            ("minute", 60),  # 60
            ("second", 1),  # 1
        ]

        # Compute time components
        result = []
        for name, unit_seconds in units:
            value, total_seconds = divmod(total_seconds, unit_seconds)
            if value:
                result.append(f"{sign}{value} {name}{'s' if value > 1 else ''}")

        # Handle case where duration is zero
        if not result:
            return "zero minutes"

        # Return formatted duration
        return " ".join(result[:2]) if short else " ".join(result)

    except Exception as e:
        log_msg(f"{seconds = } raised exception: {e}")
        return None


def format_timedelta(seconds: int, short=False):
    """
    Convert a duration in seconds into a human-readable string (weeks, days, hours, minutes).

    Args:
        seconds (int): Duration in seconds.
        short (bool): If True, return a shortened version (max 2 components).

    Returns:
        str: Human-readable duration (e.g., "1 week 2 days", "3 hours 27 minutes").
    """
    try:
        # Handle sign for negative durations
        sign = "+" if seconds >= 0 else "-"
        total_seconds = abs(int(seconds))

        # Define time units in seconds
        units = [
            ("w", 604800),  # 7 * 24 * 60 * 60
            ("d", 86400),  # 24 * 60 * 60
            ("h", 3600),  # 60 * 60
            ("m", 60),  # 60
            ("s", 1),  # 1
        ]

        # Compute time components
        result = []
        for name, unit_seconds in units:
            value, total_seconds = divmod(total_seconds, unit_seconds)
            if value:
                result.append(f"{value}{name}")

        # Handle case where duration is zero
        if not result:
            return "now"

        # Return formatted duration
        return sign + ("".join(result[:2]) if short else "".join(result))

    except Exception as e:
        log_msg(f"{seconds = } raised exception: {e}")
        return None


# def format_datetime(
#     seconds: int,
#     mode: Literal["24", "12"] = HRS_MINS,
# ) -> str:
#     """Return the date and time components of a timestamp using 12 or 24 hour format."""
#     date_time = datetime.fromtimestamp(seconds)
#
#     date_part = date_time.strftime("%Y-%m-%d")
#
#     if mode == "24":
#         time_part = date_time.strftime("%H:%Mh").lstrip("0").replace(":00", "")
#     else:
#         time_part = (
#             date_time.strftime("%-I:%M%p").lower().replace(":00", "").rstrip("m")
#         )
#     return date_part, time_part


# def format_datetime(fmt_dt: str, ampm: bool = False) -> str:
#     """
#     Convert a timestamp into a human-readable phrase based on the current time.
#
#     Args:
#         seconds (int): Timestamp in seconds since the epoch.
#         mode (str): "24" for 24-hour time (e.g., "15 30 hours"), "12" for 12-hour time (e.g., "3 30 p m").
#
#     Returns:
#         str: Formatted datetime phrase.
#     """
#     dt = datetime.fromtimestamp(seconds)
#     today = date.today()
#     delta_days = (dt.date() - today).days
#
#     time_str = (
#         dt.strftime("%I:%M%p").lower() if ampm else dt.strftime("%H:%Mh")
#     ).replace(":00", "")
#     if time_str.startswith("0"):
#         time_str = "".join(time_str[1:])
#
#     # ✅ Case 1: Today → "3 30 p m" or "15 30 hours"
#     if delta_days == 0:
#         return time_str
#
#     # ✅ Case 2: Within the past/future 6 days → "Monday at 3 30 p m"
#     elif -6 <= delta_days <= 6:
#         day_of_week = dt.strftime("%A")
#         return f"{day_of_week} at {time_str}"
#
#     # ✅ Case 3: Beyond 6 days → "January 1, 2022 at 3 30 p m"
#     else:
#         date_str = dt.strftime("%B %-d, %Y")  # "January 1, 2022"
#         return f"{date_str} at {time_str}"
#

# def datetime_in_words(seconds: int, mode: Literal["24", "12"]) -> str:
#     """Convert a timestamp into a human-readable phrase.
#     If the datetime is today, return the time only, e.g. "3 30 p m" or "15 30 hours".
#     Else if the datetime is within 6 days, return the day of the week and time. e.g. "Monday at 3 30 p m".
#     Else return the full date and time, e.g. "January 1, 2022 at 3 30 p m".
#     """
#
#     date_time = datetime.fromtimestamp(seconds)
#     date_part = date_time.strftime("%A, %B %d, %Y")
#     time_part = date_time.strftime("%-I:%M %p").lower().replace(":00", "")
#     return f"{date_part} at {time_part}"
#


def datetime_from_timestamp(fmt_dt: str) -> str:
    if isinstance(fmt_dt, datetime):
        return fmt_dt
    if fmt_dt is None:
        return None
    try:
        if "T" in fmt_dt:
            dt = datetime.strptime(fmt_dt, "%Y%m%dT%H%M")
            # is_date_only = False
        else:
            dt = datetime.strptime(fmt_dt, "%Y%m%d")
            # is_date_only = True
    except ValueError:
        print(f"could not parse {fmt_dt}")
        return None
    return dt


def format_datetime(fmt_dt: str, ampm: bool = False) -> str:
    """
    Convert a compact naive-local datetime string into a human-readable phrase.

    Args:
        fmt_dt: 'YYYYMMDD' (date) or 'YYYYMMDDTHHMMSS' (naive datetime, local).
        ampm:   True -> '3:30pm' / False -> '15h30'.

    Returns:
        str: Human-readable phrase like 'today', 'Monday at 3pm', or
             'January 5, 2026 at 15h'.
    """
    # Parse
    if "T" in fmt_dt:
        dt = datetime.strptime(fmt_dt, "%Y%m%dT%H%M")
        is_date_only = False
    else:
        dt = datetime.strptime(fmt_dt, "%Y%m%d")
        is_date_only = True

    today = date.today()
    delta_days = (dt.date() - today).days

    # Date-only cases
    if is_date_only:
        if delta_days == 0:
            return "today"
        elif -6 <= delta_days <= 6:
            return dt.strftime("%A")
        else:
            # Note: %-d is POSIX; if you need Windows support, use an alternate path.
            return dt.strftime("%B %-d, %Y")

    suffix = dt.strftime("%p").lower() if ampm else ""
    hours = dt.strftime("%-I") if ampm else dt.strftime("%H")
    minutes = dt.strftime(":%M") if not ampm or dt.minute else ""
    seconds = dt.strftime(":%S") if dt.second else ""
    time_str = hours + minutes + seconds + suffix

    # Time string
    # time_str = dt.strftime("%I:%M%p").lower() if ampm else dt.strftime("%H:%M")
    # Drop :00 minutes
    # if time_str.endswith(":00pm") or time_str.endswith(":00am"):
    # if ampm:
    #     time_str = time_str.replace(":00", "")
    # # else:
    # #     time_str = time_str.replace(":00", "h")
    # # Drop leading zero for 12-hour format
    # if ampm and time_str.startswith("0"):
    #     time_str = time_str[1:]

    # Phrasing
    if delta_days == 0:
        return time_str
    elif -6 <= delta_days <= 6:
        return f"{dt.strftime('%A')} at {time_str}"
    else:
        return f"{dt.strftime('%B %-d, %Y')} at {time_str}"


def datetime_in_words(fmt_dt: str, ampm: bool = False) -> str:
    """
    Convert a compact datetime string into a human-readable phrase based on the current time.

    Args:
        fmt_dt: 'YYYYMMDD' (date) or 'YYYYMMDDTHHMMSS' (naive datetime, local).
        ampm:   True -> '3:30pm' / False -> '15h30'.

    Returns:
        str: Human-readable phrase like 'today', 'Monday at 3pm', or
             'January 5, 2026 at 15h'.
    """
    if "T" in fmt_dt:
        dt = datetime.strptime(fmt_dt, "%Y%m%dT%H%M%S")
        is_date_only = False
    else:
        dt = datetime.strptime(fmt_dt, "%Y%m%d")
        is_date_only = True
    today = date.today()
    delta_days = (dt.date() - today).days

    # ✅ Format time based on mode
    minutes = dt.minute
    minutes_str = (
        "" if minutes == 0 else f" o {minutes}" if minutes < 10 else f" {minutes}"
    )
    hours_str = dt.strftime("%H") if ampm else dt.strftime("%I")
    if hours_str.startswith("0"):
        hours_str = hours_str[1:]  # Remove leading zero
    suffix = " hours" if ampm else " a m" if dt.hour < 12 else " p m"

    time_str = f"{hours_str}{minutes_str}{suffix}"

    # ✅ Case 1: Today → "3 30 p m" or "15 30 hours"
    if delta_days == 0:
        return time_str

    # ✅ Case 2: Within the past/future 6 days → "Monday at 3 30 p m"
    elif -6 <= delta_days <= 6:
        day_of_week = dt.strftime("%A")
        return f"{day_of_week} at {time_str}"

    # ✅ Case 3: Beyond 6 days → "January 1, 2022 at 3 30 p m"
    else:
        date_str = dt.strftime("%B %-d, %Y")  # "January 1, 2022"
        return f"{date_str} at {time_str}"
