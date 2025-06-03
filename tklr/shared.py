import inspect
import textwrap
import shutil
from datetime import date, datetime, timedelta
from typing import Literal, Tuple

HRS_MINS = "12"  # 12 or 24 - make this the default
# HRS_MINS = "24"  # 12 or 24 - make this the default

# TODO: these should be in a config file
ALERT_COMMANDS = {
    "d": "/usr/bin/say -v 'Alex' '{name}, {when} at {time}'",
}

ELLIPSIS_CHAR = "…"


def truncate_string(s: str, max_length: int) -> str:
    # log_msg(f"Truncating string '{s}' to {max_length} characters")
    if len(s) > max_length:
        return f"{s[: max_length - 2]} {ELLIPSIS_CHAR}"
    else:
        return s


def log_msg(msg: str, file_path: str = "log_msg.md"):
    """
    Log a message and save it directly to a specified file.

    Args:
        msg (str): The message to log.
        file_path (str, optional): Path to the log file. Defaults to "log_msg.txt".
    """
    caller_name = inspect.stack()[1].function
    # wrapped_lines = textwrap.wrap(
    #     fmt_msg,
    #     initial_indent="",
    #     subsequent_indent="  ",
    #     width=shutil.get_terminal_size()[0] - 3,
    # )
    lines = [
        f"- {datetime.now().strftime('%y-%m-%d %H:%M:%S')} " + rf"({caller_name}):  ",
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
    lines.append("\n\n")

    # Save the message to the file
    with open(file_path, "a") as f:
        f.writelines(lines)


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


def format_time_range(start_time: int, end_time: int, mode: Literal["24", "12"]) -> str:
    """Format time range in 24-hour or 12-hour notation."""
    start_dt = (
        start_time
        if isinstance(start_time, datetime)
        else datetime.fromtimestamp(start_time)
        if isinstance(start_time, int)
        else None
    )
    end_dt = (
        end_time
        if isinstance(end_time, datetime)
        else datetime.fromtimestamp(end_time)
        if isinstance(start_time, int)
        else None
    )
    extent = start_dt != end_dt

    if mode == "24":
        start_hour = start_dt.strftime("%H:%M").replace(":00", "")
        if start_hour.startswith("0"):
            start_hour = start_hour[1:]
        end_hour = end_dt.strftime("%H:%M").replace(":00", "")
        if end_hour.startswith("0"):
            end_hour = end_hour[1:]
        return (
            f"{start_hour}-{end_hour}h" if start_hour != end_hour else f"{start_hour}h"
        )
    else:
        start_fmt = "%-I:%M%p" if start_dt.hour < 12 and end_dt.hour >= 12 else "%-I:%M"
        start_hour = start_dt.strftime(f"{start_fmt}").lower().replace(":00", "")
        end_hour = (
            end_dt.strftime("%-I:%M%p").lower().replace(":00", "")  # .replace("m", "")
        )
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


def format_datetime(
    seconds: int,
    mode: Literal["24", "12"] = HRS_MINS,
) -> str:
    """Return the date and time components of a timestamp using 12 or 24 hour format."""
    date_time = datetime.fromtimestamp(seconds)

    date_part = date_time.strftime("%Y-%m-%d")

    if mode == "24":
        time_part = date_time.strftime("%H:%Mh").lstrip("0").replace(":00", "")
    else:
        time_part = (
            date_time.strftime("%-I:%M%p").lower().replace(":00", "").rstrip("m")
        )
    return date_part, time_part


def format_datetime(seconds: int, mode: Literal["24", "12"] = HRS_MINS) -> str:
    """
    Convert a timestamp into a human-readable phrase based on the current time.

    Args:
        seconds (int): Timestamp in seconds since the epoch.
        mode (str): "24" for 24-hour time (e.g., "15 30 hours"), "12" for 12-hour time (e.g., "3 30 p m").

    Returns:
        str: Formatted datetime phrase.
    """
    dt = datetime.fromtimestamp(seconds)
    today = date.today()
    delta_days = (dt.date() - today).days

    time_str = (
        dt.strftime("%I:%M%p").lower() if mode == "12" else dt.strftime("%H:%Mh")
    ).replace(":00", "")
    if time_str.startswith("0"):
        time_str = "".join(time_str[1:])

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


def datetime_in_words(seconds: int, mode: Literal["24", "12"] = HRS_MINS) -> str:
    """
    Convert a timestamp into a human-readable phrase based on the current time.

    Args:
        seconds (int): Timestamp in seconds since the epoch.
        mode (str): "24" for 24-hour time (e.g., "15 30 hours"), "12" for 12-hour time (e.g., "3 30 p m").

    Returns:
        str: Formatted datetime phrase.
    """
    dt = datetime.fromtimestamp(seconds)
    today = date.today()
    delta_days = (dt.date() - today).days

    # ✅ Format time based on mode
    minutes = dt.minute
    minutes_str = (
        "" if minutes == 0 else f" o {minutes}" if minutes < 10 else f" {minutes}"
    )
    hours_str = dt.strftime("%H") if mode == "24" else dt.strftime("%I")
    if hours_str.startswith("0"):
        hours_str = hours_str[1:]  # Remove leading zero
    suffix = " hours" if mode == "24" else " a m" if dt.hour < 12 else " p m"

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
