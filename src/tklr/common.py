# pyright: reportUndefinedVariable=false
from dateutil.parser import parse as dateutil_parse
from dateutil.parser import parserinfo
from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo
import platform
import sys
import os
import sys
import textwrap
import shutil
import re
from shlex import split as qsplit
import contextlib, io
import subprocess  # for check_output
from rich import print as rprint
from rich.console import Console
from rich.markdown import Markdown

# Initialize a Rich console

from pygments.lexer import RegexLexer
from pygments.token import Keyword
from pygments.token import Literal
from pygments.token import Operator
from pygments.token import Comment

import functools
from time import perf_counter
from typing import List, Callable, Any
import inspect
from typing import Literal
from .versioning import get_version

# import logging
# import logging.config
# logger = logging.getLogger('etm')
# settings = None

from dateutil import __version__ as dateutil_version

from time import perf_counter as timer

# from etm.make_examples import make_examples
import tomllib
from pathlib import Path

ETMDB = DBITEM = DBARCH = dataview = data_changed = None


# def get_version(pyproject_path: Path | None = None) -> str:
#     """
#     Extract the version from pyproject.toml [project] section.
#
#     Args:
#         pyproject_path (Path or None): Optional override path. If None, searches upward.
#
#     Returns:
#         str: version string (e.g., "0.1.0")
#     """
#     if pyproject_path is None:
#         # Search upward from current working dir
#         current = Path.cwd()
#         while current != current.parent:
#             candidate = current / "pyproject.toml"
#             if candidate.exists():
#                 pyproject_path = candidate
#                 break
#             current = current.parent
#         else:
#             return "dev"
#
#     try:
#         with open(pyproject_path, "rb") as f:
#             data = tomllib.load(f)
#         return data.get("project", {}).get("version", "dev")
#     except Exception:
#         return "dev"


def log_msg(msg: str, file_path: str = "log_msg.md"):
    """
    Log a message and save it directly to a specified file.

    Args:
        msg (str): The message to log.
        file_path (str, optional): Path to the log file. Defaults to "log_msg.txt".
    """
    caller_name = inspect.stack()[1].function
    lines = [
        f"- {datetime.now().strftime('%y-%m-%d %H:%M')} " + rf"({caller_name}):  ",
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


def is_aware(dt):
    return dt.tzinfo is not None and dt.tzinfo.utcoffset(dt) is not None


def benchmark(func: Callable[..., Any]) -> Callable[..., Any]:
    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        start = perf_counter()
        result = func(*args, **kwargs)
        end = perf_counter()
        logger.debug(f"⏱ {func.__name__} took {end - start:.4f} seconds")
        return result

    return wrapper


def timeit(message: str = "") -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(func)
        def wrapper(self, *args: Any, **kwargs: Any) -> Any:
            msg = f" ({message.format(self=self)})" if message else ""
            start = perf_counter()
            result = func(self, *args, **kwargs)
            end = perf_counter()
            logger.debug(f"⏱ {func.__name__}{msg} took {end - start:.4f} seconds")
            return result

        return wrapper

    return decorator


def drop_zero_minutes(dt, mode: Literal["24", "12"], end=False):
    """
    >>> drop_zero_minutes(parse('2018-03-07 10am'))
    '10'
    >>> drop_zero_minutes(parse('2018-03-07 2:45pm'))
    '2:45'
    """
    show_minutes = True if mode == "24" else False
    # show_minutes = False
    # logger.debug(f"starting {dt = }; {ampm = }; {show_minutes = }")
    # logger.debug(f"{dt.replace(tzinfo=None) = }")
    dt = dt.replace(tzinfo=None)
    # logger.debug(f"{dt = }")
    # if show_minutes:
    if show_minutes:
        if mode == "12":
            return dt.strftime("%-I:%M").rstrip("M").lower()
        else:
            return dt.strftime("%-H:%M")
    else:
        if dt.minute == 0:
            if mode == "12":
                return dt.strftime("%-I")
            else:
                # return dt.strftime("%-Hh") if end else dt.strftime("%-H")
                return dt.strftime("%-H") if end else dt.strftime("%-H")
        else:
            if mode == "12":
                return dt.strftime("%-I:%M").rstrip("M").lower()
            else:
                return dt.strftime("%-H:%M")


period_regex = re.compile(r"((\d+)([wdhms]))+?")
expanded_period_regex = re.compile(r"((\d+)\s(week|day|hour|minute|second)s?)+?")


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


def parse_period(s: str) -> timedelta:
    """\
    Take a period string and return a corresponding timedelta.
    Examples:
        parse_period('-2w3d4h5m')= -timedelta(weeks=2,days=3,hours=4,minutes=5)
        parse_period('1h30m') = timedelta(hours=1, minutes=30)
        parse_period('-10m') = -timedelta(minutes=10)
    where:
        y: years
        w: weeks
        d: days
        h: hours
        m: minutes
        s: seconds
    """

    knms = {
        "w": "weeks",
        "week": "weeks",
        "weeks": "weeks",
        "d": "days",
        "day": "days",
        "days": "days",
        "h": "hours",
        "hour": "hours",
        "hours": "hours",
        "m": "minutes",
        "minute": "minutes",
        "minutes": "minutes",
        "s": "seconds",
        "second": "second",
        "seconds": "seconds",
    }

    kwds = {
        "weeks": 0,
        "days": 0,
        "hours": 0,
        "minutes": 0,
        "seconds": 0,
    }

    s = str(s).strip()
    sign = None
    if s[0] in ["+", "-"]:
        # record the sign and keep the rest of the string
        sign = s[0]
        s = s[1:]

    m = period_regex.findall(str(s))
    if not m:
        m = expanded_period_regex.findall(str(s))
        if not m:
            return False, f"Invalid period string '{s}'"
    for g in m:
        if g[2] not in knms:
            return False, f"invalid period argument: {g[2]}"

        # num = -int(g[2]) if g[1] == "-" else int(g[2])
        num = int(g[1])
        if num:
            kwds[knms[g[2]]] = num
    td = timedelta(**kwds)

    if sign and sign == "-":
        td = -td

    return True, td


def format_extent(
    beg_dt: datetime, end_dt: datetime, mode: str = Literal["24", "12"]
) -> str:
    """
    Format the beginning to ending times to display for a reminder with an extent (both @s and @e).
    >>> beg_dt = parse('2018-03-07 10am')
    >>> end_dt = parse('2018-03-07 11:30am')
    >>> fmt_extent(beg_dt, end_dt)
    '10-11:30am'
    >>> end_dt = parse('2018-03-07 2pm')
    >>> fmt_extent(beg_dt, end_dt)
    '10am-2pm'
    """
    log_msg(f"{beg_dt = }; {end_dt = }; {mode = }")
    beg_suffix = ""
    end_suffix = end_dt.strftime("%p").lower().rstrip("m") if mode == "12" else ""
    if beg_dt == end_dt:
        if beg_dt.hour == 0 and beg_dt.minute == 0 and beg_dt.second == 0:
            return "~"
        elif beg_dt.hour == 23 and beg_dt.minute == 59 and beg_dt.second == 59:
            return "~"
        else:
            return f"{drop_zero_minutes(end_dt, mode)}{end_suffix}"

    if end_dt.hour == 23 and end_dt.minute == 59 and end_dt.second == 59:
        # end_dt = end_dt.replace(hour=0, minute=0, second=0)
        log_msg(f"end_dt: {end_dt = }")
        # end_dt = end_dt + timedelta(seconds=1)
        log_msg(f"end_dt adjusted: {end_dt = }")
        end_suffix = "a" if mode == "12" else ""
        # end_fmt = "12" if mode == "12" else "24"

    if mode == "12":
        diff = (beg_dt.hour < 12 and end_dt.hour >= 12) or (
            beg_dt.hour >= 12 and end_dt.hour < 12
        )
        beg_suffix = beg_dt.strftime("%p").lower().rstrip("m") if diff else ""

    beg_fmt = drop_zero_minutes(beg_dt, mode)
    end_fmt = drop_zero_minutes(end_dt, mode, end=True)
    log_msg(f"end: {end_dt = }; {end_fmt = }")
    if mode == "12":
        beg_fmt = beg_fmt.lstrip("0")
        end_fmt = end_fmt.lstrip("0")
    # else:
    #     beg_fmt = beg_fmt.lstrip("0")
    #     end_fmt = end_fmt.lstrip("0")

    return f"{beg_fmt}{beg_suffix}-{end_fmt}{end_suffix}"


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
    }
    # Match all integer-unit pairs (e.g., "3h", "15s")
    matches = re.findall(r"(\d+)([wdhm])", time_str)
    if not matches:
        return (
            False,
            "Invalid time string format. Expected integers followed by 'w', 'd', 'h', or 'm'.",
        )
    # Convert each match to seconds and sum them
    total_seconds = sum(int(value) * multipliers[unit] for value, unit in matches)
    return True, total_seconds


def fmt_period(seconds: int, short=True):
    """
    Format seconds as a human readable string
    if short report only biggest 2, else all
    >>> td = timedelta(weeks=1, days=2, hours=3, minutes=27).total_seconds()
    >>> fmt_td(td)
    '1w2d3h27m'
    """
    if type(seconds) is not int:
        return "?"
    if seconds <= 0:
        return ""
    try:
        total_seconds = abs(seconds)
        until = []
        days = hours = minutes = 0
        if total_seconds:
            seconds = total_seconds % 60
            minutes = total_seconds // 60
            if minutes >= 60:
                hours = minutes // 60
                minutes = minutes % 60
            if hours >= 24:
                days = hours // 24
                hours = hours % 24
            if days >= 7:
                weeks = days // 7
                days = days % 7

        if weeks:
            until.append(f"{weeks}w")
        if days:
            until.append(f"{days}d")
        if hours:
            until.append(f"{hours}h")
        if minutes:
            until.append(f"{minutes}m")
        if seconds:
            until.append(f"{seconds}s")
        if not until:
            until.append("0m")
        ret = "".join(until[:2]) if short else "".join(until)
        return ret
    except Exception as e:
        log_msg(f"{seconds}: {e}")
        return ""


def fmt_dt(dt: int, fmt: Literal["date", "time", "datetime"] = "datetime"):
    """
    Format seconds as a human readable string
    >>> fmt_dt(1610386800)
    '2021-01-11 00:00:00'
    """
    # log_msg(f"dt: {dt}")
    fmt = (
        "%y-%m-%d" if fmt == "date" else "%H:%M" if fmt == "time" else "%Y-%m-%d %H:%M"
    )
    if type(dt) is not int:
        return "?"
    if dt <= 0:
        return ""
    return datetime.fromtimestamp(dt).strftime(fmt)


def duration_in_words(seconds: int, short=False):
    """
    Return string representing weeks, days, hours and minutes. Drop any remaining seconds.
    >>> td = timedelta(weeks=1, days=2, hours=3, minutes=27)
    >>> format_duration(td)
    '1 week 2 days 3 hours 27 minutes'
    """
    try:
        until = []
        total_seconds = int(seconds)
        weeks = days = hours = minutes = seconds = 0
        if total_seconds:
            sign = "" if total_seconds > 0 else "- "
            total_seconds = abs(total_seconds)
            seconds = total_seconds % 60
            minutes = total_seconds // 60
            if minutes >= 60:
                hours = minutes // 60
                minutes = minutes % 60
            if hours >= 24:
                days = hours // 24
                hours = hours % 24
            if days >= 7:
                weeks = days // 7
                days = days % 7
        if weeks:
            if weeks > 1:
                until.append(f"{sign}{weeks} weeks")
            else:
                until.append(f"{sign}{weeks} week")
        if days:
            if days > 1:
                until.append(f"{sign}{days} days")
            else:
                until.append(f"{sign}{days} day")
        if hours:
            if hours > 1:
                until.append(f"{sign}{hours} hours")
            else:
                until.append(f"{sign}{hours} hour")
        if minutes:
            if minutes > 1:
                until.append(f"{sign}{minutes} minutes")
            else:
                until.append(f"{sign}{minutes} minute")
        if seconds:
            if seconds > 1:
                until.append(f"{sign}{seconds} seconds")
            else:
                until.append(f"{sign}{seconds} second")
        if not until:
            until.append("zero minutes")
        ret = " ".join(until[:2]) if short else " ".join(until)
        return ret
    except Exception as e:
        log_msg(f"{seconds = } raised exception: {e}")
        return None


class TimeIt(object):
    def __init__(self, label="", loglevel=1):
        self.loglevel = loglevel
        self.label = label
        if self.loglevel == 1:
            self.start = timer()

    def stop(self, *args):
        if self.loglevel == 1:
            self.end = timer()
            msg = f"⏱ {self.label} took {self.end - self.start:.4f} seconds"
            logger.debug(msg)


# from etm.__main__ import ETMHOME
# from etm import options

python_version = platform.python_version()
system_platform = platform.platform(terse=True)
sys_platform = platform.system()
mac = sys.platform == "darwin"
windoz = sys_platform in ("Windows", "Microsoft")

WA = {}
parse_datetime = None
text_pattern = None
etmhome = None
timers_file = None

VERSION_INFO = f"""\
 python:             {python_version}
 dateutil:           {dateutil_version}
 platform:           {system_platform}\
"""


def check_output(cmd):
    if not cmd:
        return
    res = ""
    try:
        res = subprocess.check_output(
            cmd,
            stderr=subprocess.STDOUT,
            shell=True,
            universal_newlines=True,
            encoding="UTF-8",
        )
        return True, res
    except subprocess.CalledProcessError as e:
        logger.warning(f"Error running {cmd}\n'{e.output}'")
        lines = e.output.strip().split("\n")
        msg = lines[-1]
        return False, msg


def db_replace(new):
    """
    Used with update to replace the original doc with new.
    """

    def transform(doc):
        # update doc to include key/values from new
        doc.update(new)
        # remove any key/values from doc that are not in new
        for k in list(doc.keys()):
            if k not in new:
                del doc[k]

    return transform


def import_file(import_file=None):
    import_file = import_file.strip()
    if not import_file:
        return False, ""
    if import_file.lower() == "lorem":
        return True, import_examples()

    if not os.path.isfile(import_file):
        return (
            False,
            f'"{import_file}"\n   either does not exist or is not a regular file',
        )
    filename, extension = os.path.splitext(import_file)
    if extension == ".text":
        return True, import_text(import_file)
    else:
        return (
            False,
            f"Importing a file with the extension '{extension}' is not implemented. Only files with the extension '.text' are recognized",
        )


def import_examples():
    docs = []
    examples = make_examples(last_id=last_id)

    results = []
    good = []
    bad = []
    items = []

    logger.debug(f"starting import from last_id: {last_id}")
    count = 0
    for s in examples:
        ok = True
        count += 1
        if not s:
            continue
        item = Item()  # use ETMDB by default
        item.new_item()
        item.text_changed(s, 1)
        if item.item_hsh.get("itemtype", None) is None:
            ok = False

        if item.item_hsh.get("summary", None) is None:
            ok = False

        if ok:
            # don't check links because the ids won't yet exist
            item.update_item_hsh(check_links=False)
            good.append(f"{item.doc_id}")
        else:
            logger.debug(f"bad entry: {s}")
            bad.append(s)

    logger.debug("ending import")
    res = f"imported {len(good)} items"
    if good:
        res += f"\n  ids: {good[0]} - {good[-1]}"
    if bad:
        res += f"\nrejected {bad} items:\n  "
        res += "\n  ".join(results)
    return res


def import_text(import_file=None):
    docs = []
    with open(import_file, "r") as fo:
        logger.debug(f"opened for reading: '{import_file}'")
        results = []
        good = []
        bad = 0
        reminders = []
        reminder = []
        for line in fo:
            s = line.strip()
            if s and s[0] in ["!", "*", "-", "%"]:
                if reminder:
                    # append it to reminders and reset it
                    reminders.append(reminder)
                    reminder = []
                reminder = [s]
            else:
                # append to the existing reminder
                reminder.append(s)
        if reminder:
            reminders.append(reminder)
    count = 0
    for reminder in reminders:
        count += 1
        logger.debug(f"reminder number {count}: {reminder}")
        ok = True
        s = "\n".join(reminder)
        if not s:
            continue
        logger.debug(f"adding item for {s}")
        item = Item()  # use ETMDB by default
        item.new_item()
        item.text_changed(s, 1)
        if item.item_hsh.get("itemtype", None) is None:
            ok = False

        if item.item_hsh.get("summary", None) is None:
            ok = False

        if ok:
            # don't check links because the ids won't yet exist
            item.update_item_hsh(check_links=False)
            good.append(f"{item.doc_id}")
        else:
            logger.debug(f"bad entry: {s}")
            bad.append(s)

        # if not ok:
        #     bad += 1
        #     results.append(f'   {s}')
        #     continue

        # update_item_hsh stores the item in ETMDB
        # item.update_item_hsh()
        # good.append(f'{item.doc_id}')

    res = f"imported {len(good)} items"
    if good:
        res += f"\n  ids: {good[0]} - {good[-1]}"
    if bad:
        res += f"\nrejected {bad} items:\n  "
        res += "\n  ".join(results)
    logger.debug(f"returning: {res}")
    return res


def import_json(import_file=None):
    import json

    with open(import_file, "r") as fo:
        import_hsh = json.load(fo)
    items = import_hsh["items"]
    docs = []
    dups = 0
    add = 0
    for id in items:
        item_hsh = items[id]
        itemtype = item_hsh.get("itemtype")
        if not itemtype:
            continue
        summary = item_hsh.get("summary")
        if not summary:
            continue
        z = item_hsh.get("z", "Factory")
        bad_keys = [x for x in item_hsh if not item_hsh[x]]
        for key in bad_keys:
            del item_hsh[key]
        if "s" in item_hsh:
            item_hsh["s"] = pen_from_fmt(item_hsh["s"], z)
        if "f" in item_hsh:
            item_hsh["f"] = period_from_fmt(item_hsh["f"], z)
        item_hsh["created"] = datetime.now("UTC")
        if "h" in item_hsh:
            item_hsh["h"] = [period_from_fmt(x, z) for x in item_hsh["h"]]
        if "+" in item_hsh:
            item_hsh["+"] = [pen_from_fmt(x, z) for x in item_hsh["+"]]
        if "-" in item_hsh:
            item_hsh["-"] = [pen_from_fmt(x, z) for x in item_hsh["-"]]
        if "e" in item_hsh:
            item_hsh["e"] = parse_duration(item_hsh["e"])[1]
        if "w" in item_hsh:
            wrps = [parse_duration(x)[1] for x in item_hsh["w"]]
            item_hsh["w"] = wrps
        if "a" in item_hsh:
            alerts = []
            for alert in item_hsh["a"]:
                # drop the True from parse_duration
                tds = [parse_duration(x)[1] for x in alert[0]]
                # put the largest duration first
                tds.sort(reverse=True)
                cmds = alert[1:2]
                args = ""
                if len(alert) > 2 and alert[2]:
                    args = ", ".join(alert[2])
                for cmd in cmds:
                    if args:
                        row = (tds, cmd, args)
                    else:
                        row = (tds, cmd)
                    alerts.append(row)
            item_hsh["a"] = alerts
        if "j" in item_hsh:
            jbs = []
            for jb in item_hsh["j"]:
                if "h" in jb:
                    if "f" not in jb:
                        jb["f"] = jb["h"][-1]
                    del jb["h"]
                jbs.append(jb)
            ok, lofh, last_completed = jobs(jbs, item_hsh)

            if ok:
                item_hsh["j"] = lofh
            else:
                print("using jbs", jbs)
                print(
                    "ok:",
                    ok,
                    " lofh:",
                    lofh,
                    " last_completed:",
                    last_completed,
                )

        if "r" in item_hsh:
            ruls = []
            for rul in item_hsh["r"]:
                if "r" in rul and rul["r"] == "l":
                    continue
                elif "f" in rul:
                    if rul["f"] == "l":
                        continue
                    else:
                        rul["r"] = rul["f"]
                        del rul["f"]
                if "u" in rul:
                    if "t" in rul:
                        del rul["t"]
                    if "c" in rul:
                        del rul["c"]
                elif "t" in rul:
                    rul["c"] = rul["t"]
                    del rul["t"]
                if "u" in rul:
                    if type(rul["u"]) == str:
                        try:
                            rul["u"] = parse(rul["u"], tz=z)
                        except Exception as e:
                            logger.error(f"error parsing rul['u']: {rul['u']}. {e}")
                if "w" in rul:
                    if isinstance(rul["w"], list):
                        rul["w"] = [
                            "{0}:{1}".format("{W}", x.upper()) for x in rul["w"]
                        ]
                    else:
                        rul["w"] = "{0}:{1}".format("{W}", rul["w"].upper())
                bad_keys = []
                for key in rul:
                    if not rul[key]:
                        bad_keys.append(key)
                if bad_keys:
                    for key in bad_keys:
                        del rul[key]
                if rul:
                    ruls.append(rul)
            if ruls:
                item_hsh["r"] = ruls
            else:
                del item_hsh["r"]

        docs.append(item_hsh)
    # now check for duplicates. If an item to be imported has the same type, summary and starting time as an existing item, regard it as a duplicate and do not import it.
    exst = []
    new = []
    dups = 0
    for x in ETMDB:
        exst.append(
            {
                "itemtype": x.get("itemtype"),
                "summary": x.get("summary"),
                "s": x.get("s"),
            }
        )
    i = 0
    for x in docs:
        i += 1
        y = {
            "itemtype": x.get("itemtype"),
            "summary": x.get("summary"),
            "s": x.get("s"),
        }
        if exst and y in exst:
            dups += 1
        else:
            new.append(x)

    ids = []
    if new:
        ids = ETMDB.insert_multiple(new)
        ETMDB.close()
    msg = f"imported {len(new)} items"
    if ids:
        msg += f"\n  ids: {ids[0]}-{ids[-1]}."
    if dups:
        msg += f"\n  rejected {dups} items as duplicates"
    return msg


def update_db(db, doc_id, hsh={}):
    old = db.get(doc_id=doc_id)
    if not old:
        logger.error(f"Could not get document corresponding to doc_id {doc_id}")
        return
    if old == hsh:
        return
    hsh["modified"] = datetime.now()
    logger.debug(f"starting db.update")
    try:
        db.update(db_replace(hsh), doc_ids=[doc_id])
    except Exception as e:
        logger.error(
            f"Error updating document corresponding to doc_id {doc_id}\nhsh {hsh}\nexception: {repr(e)}"
        )


def write_back(db, docs):
    logger.debug(f"starting write_back")
    for doc in docs:
        try:
            doc_id = doc.doc_id
            update_db(db, doc_id, doc)
        except Exception as e:
            logger.error(f"write_back exception: {e}")


def setup_logging(level, etmdir, file=None):
    """
    Setup logging configuration. Override root:level in
    logging.yaml with default_level.
    """

    if not os.path.isdir(etmdir):
        return

    log_levels = {
        1: logging.DEBUG,
        2: logging.INFO,
        3: logging.WARN,
        4: logging.ERROR,
        5: logging.CRITICAL,
    }

    level = int(level)
    loglevel = log_levels.get(level, log_levels[3])

    # if we get here, we have an existing etmdir
    logfile = os.path.normpath(os.path.abspath(os.path.join(etmdir, "etm.log")))

    config = {
        "disable_existing_loggers": False,
        "formatters": {
            "simple": {
                "format": "--- %(asctime)s - %(levelname)s - %(module)s.%(funcName)s\n    %(message)s"
            }
        },
        "handlers": {
            "file": {
                "backupCount": 7,
                "class": "logging.handlers.TimedRotatingFileHandler",
                "encoding": "utf8",
                "filename": logfile,
                "formatter": "simple",
                "level": loglevel,
                "when": "midnight",
                "interval": 1,
            }
        },
        "loggers": {
            "etmmv": {
                "handlers": ["file"],
                "level": loglevel,
                "propagate": False,
            }
        },
        "Redirectoot": {"handlers": ["file"], "level": loglevel},
        "version": 1,
    }
    logging.config.dictConfig(config)
    # logger = logging.getLogger('asyncio').setLevel(logging.WARNING)
    logger = logging.getLogger("etmmv")

    logger.critical("\n######## Initializing logging #########")
    if logfile:
        logger.critical(
            f"logging for file: {file}\n    logging at level: {loglevel}\n    logging to file: {logfile}"
        )
    else:
        logger.critical(f"logging at level: {loglevel}\n    logging to file: {logfile}")
    return logger


def openWithDefault(path):
    if " " in path:
        parts = qsplit(path)
        if parts:
            # wrapper to catch 'Exception Ignored' messages
            output = io.StringIO()
            with contextlib.redirect_stderr(output):
                # the pid business is evidently needed to avoid waiting
                pid = subprocess.Popen(
                    parts,
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                ).pid
                res = output.getvalue()
                if res:
                    logger.error(f"caught by contextlib:\n'{res}'")

    else:
        path = os.path.normpath(os.path.expanduser(path))
        sys_platform = platform.system()
        if platform.system() == "Darwin":  # macOS
            subprocess.run(
                ("open", path),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        elif platform.system() == "Windows":  # Windows
            os.startfile(path)
        else:  # linux
            subprocess.run(
                ("xdg-open", path),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

    return


class TDBLexer(RegexLexer):
    name = "TDB"
    aliases = ["tdb"]
    filenames = "*.*"
    flags = re.MULTILINE | re.DOTALL

    tokens = {
        "root": [
            (
                r"\b(begins|includes|in|equals|more|less|exists|any|all|one)\b",
                Keyword,
            ),
            (
                r"\b(replace|remove|archive|delete|set|provide|attach|detach)\b",
                Keyword,
            ),
            (r"\b(itemtype|summary)\b", Literal),
            (r"\b(and|or|info)\b", Keyword),
        ],
    }


def nowrap(txt, indent=3, width=shutil.get_terminal_size()[0] - 3):
    return txt


def wrap(
    txt_to_wrap: str, indent: int = 3, width: int = shutil.get_terminal_size()[0] - 3
) -> str:
    """
    Split text on newlines into paragraphs. Then preserving the
    indentation of the beginning of each paragraph, wrap each paragraph to the specified width using the initial indentation plus the number of spaces specified by the indent parameter as the subsequent indentation.
    """
    para = [x.rstrip() for x in txt_to_wrap.split("\n")]
    tmp = []
    for p in para:
        p_ = p.lstrip(" ")
        i_ = len(p) - len(p_)
        initial_indent = " " * i_
        subsequent_indent = " " * (indent + i_)
        tmp.append(
            textwrap.fill(
                p_,
                initial_indent=initial_indent,
                subsequent_indent=subsequent_indent,
                width=width - indent - 1,
            )
        )
    return "\n".join(tmp)


def unwrap(wrapped_text: str) -> str:
    # Split the text into paragraphs
    paragraphs = wrapped_text.split("\n")

    # Remove indentations and join lines within each paragraph
    unwrapped_paragraphs = []
    current_paragraph = []

    first = True
    for line in paragraphs:
        if line.strip() == "":
            # Paragraph separator
            if current_paragraph:
                unwrapped_paragraphs.append(" ".join(current_paragraph))
                current_paragraph = []
            unwrapped_paragraphs.append("")
            first = True
        elif first:
            current_paragraph.append(line)
            first = False
        else:
            # Remove leading spaces used for indentation
            current_paragraph.append(line.strip())

    # Add the last paragraph if there is any
    if current_paragraph:
        unwrapped_paragraphs.append(" ".join(current_paragraph))

    # Join the unwrapped paragraphs
    return "\n".join(unwrapped_paragraphs)


def parse(s, **kwd):
    # enable pi when read by main and settings is available
    pi = parserinfo(dayfirst=settings["dayfirst"], yearfirst=settings["yearfirst"])
    # logger.debug(f"parsing {s = } with {kwd = }")
    dt = dateutil_parse(s, parserinfo=pi)
    if "tzinfo" in kwd:
        tzinfo = kwd["tzinfo"]
        # logger.debug(f"using {tzinfo = } with {dt = }")
        if tzinfo == None:
            return dt.replace(tzinfo=None)
        elif tzinfo == "local":
            return dt.astimezone()
        else:
            return dt.replace(tzinfo=ZoneInfo(tzinfo))
    else:
        return dt.astimezone()


class AttrDict(dict):
    def __init__(self, *args, **kwargs):
        super(AttrDict, self).__init__(*args, **kwargs)
        for arg in args:
            if isinstance(arg, dict):
                for k, v in arg.items():
                    self[k] = v

        if kwargs:
            for k, v in kwargs.items():
                self[k] = v

    def __getattr__(self, item):
        try:
            return self[item]
        except KeyError:
            raise AttributeError(f"'AttrDict' object has no attribute '{item}'")

    def __setattr__(self, key, value):
        self[key] = value

    # Initializing AttrDict with a dictionary
    # d = AttrDict({'attr': 'value', 'another': 123})
    # print(d.attr)  # Outputs: value


class EtmChar:
    VSEP = "⏐"  # U+23D0  this will be a de-emphasized color
    FREE = "─"  # U+2500  this will be a de-emphasized color
    HSEP = "┈"  #
    BUSY = "■"  # U+25A0 this will be busy (event) color
    CONF = "▦"  # U+25A6 this will be conflict color
    TASK = "▩"  # U+25A9 this will be busy (task) color
    ADAY = "━"  # U+2501 for all day events ━
    RSKIP = "▶"  # U+25E6 for used time
    LSKIP = "◀"  # U+25E6 for used time
    USED = "◦"  # U+25E6 for used time
    REPS = "↻"  # Flag for repeating items
    FINISHED_CHAR = "✓"
    SKIPPED_CHAR = "✗"
    SLOW_CHAR = "∾"
    LATE_CHAR = "∿"
    INACTIVE_CHAR = "≁"
    # INACTIVE_CHAR='∽'
    ENDED_CHAR = "≀"
    UPDATE_CHAR = "𝕦"
    INBASKET_CHAR = "𝕚"
    KONNECT_CHAR = "k"
    LINK_CHAR = "g"
    PIN_CHAR = "p"
    ELLIPSIS_CHAR = "…"
    LINEDOT = " · "  # ܁ U+00B7 (middle dot),
    ELECTRIC = "⌁"


#  model, data and ical
#  with integer prefixes
WKDAYS_DECODE = {
    "{0}{1}".format(n, d): "{0}({1})".format(d, n) if n else d
    for d in ["MO", "TU", "WE", "TH", "FR", "SA", "SU"]
    for n in ["-4", "-3", "-2", "-1", "", "1", "2", "3", "4"]
}

WKDAYS_ENCODE = {
    "{0}({1})".format(d, n): "{0}{1}".format(n, d) if n else d
    for d in ["MO", "TU", "WE", "TH", "FR", "SA", "SU"]
    for n in ["-4", "-3", "-2", "-1", "+1", "+2", "+3", "+4"]
}

# without integer prefixes
for wkd in ["MO", "TU", "WE", "TH", "FR", "SA", "SU"]:
    WKDAYS_ENCODE[wkd] = wkd

# print(f'WKDAYS_DECODE:\n{WKDAYS_DECODE}')
# print(f'WKDAYS_ENCODE:\n{WKDAYS_ENCODE}')
# WKDAYS_DECODE:
# {'-4MO': 'MO(-4)', '-3MO': 'MO(-3)', '-2MO': 'MO(-2)', '-1MO': 'MO(-1)', 'MO': 'MO', '1MO': 'MO(1)', '2MO': 'MO(2)', '3MO': 'MO(3)', '4MO': 'MO(4)', '-4TU': 'TU(-4)', '-3TU': 'TU(-3)', '-2TU': 'TU(-2)', '-1TU': 'TU(-1)', 'TU': 'TU', '1TU': 'TU(1)', '2TU': 'TU(2)', '3TU': 'TU(3)', '4TU': 'TU(4)', '-4WE': 'WE(-4)', '-3WE': 'WE(-3)', '-2WE': 'WE(-2)', '-1WE': 'WE(-1)', 'WE': 'WE', '1WE': 'WE(1)', '2WE': 'WE(2)', '3WE': 'WE(3)', '4WE': 'WE(4)', '-4TH': 'TH(-4)', '-3TH': 'TH(-3)', '-2TH': 'TH(-2)', '-1TH': 'TH(-1)', 'TH': 'TH', '1TH': 'TH(1)', '2TH': 'TH(2)', '3TH': 'TH(3)', '4TH': 'TH(4)', '-4FR': 'FR(-4)', '-3FR': 'FR(-3)', '-2FR': 'FR(-2)', '-1FR': 'FR(-1)', 'FR': 'FR', '1FR': 'FR(1)', '2FR': 'FR(2)', '3FR': 'FR(3)', '4FR': 'FR(4)', '-4SA': 'SA(-4)', '-3SA': 'SA(-3)', '-2SA': 'SA(-2)', '-1SA': 'SA(-1)', 'SA': 'SA', '1SA': 'SA(1)', '2SA': 'SA(2)', '3SA': 'SA(3)', '4SA': 'SA(4)', '-4SU': 'SU(-4)', '-3SU': 'SU(-3)', '-2SU': 'SU(-2)', '-1SU': 'SU(-1)', 'SU': 'SU', '1SU': 'SU(1)', '2SU': 'SU(2)', '3SU': 'SU(3)', '4SU': 'SU(4)'}
# WKDAYS_ENCODE:
# {'MO(-4)': '-4MO', 'MO(-3)': '-3MO', 'MO(-2)': '-2MO', 'MO(-1)': '-1MO', 'MO(+1)': '+1MO', 'MO(+2)': '+2MO', 'MO(+3)': '+3MO', 'MO(+4)': '+4MO', 'TU(-4)': '-4TU', 'TU(-3)': '-3TU', 'TU(-2)': '-2TU', 'TU(-1)': '-1TU', 'TU(+1)': '+1TU', 'TU(+2)': '+2TU', 'TU(+3)': '+3TU', 'TU(+4)': '+4TU', 'WE(-4)': '-4WE', 'WE(-3)': '-3WE', 'WE(-2)': '-2WE', 'WE(-1)': '-1WE', 'WE(+1)': '+1WE', 'WE(+2)': '+2WE', 'WE(+3)': '+3WE', 'WE(+4)': '+4WE', 'TH(-4)': '-4TH', 'TH(-3)': '-3TH', 'TH(-2)': '-2TH', 'TH(-1)': '-1TH', 'TH(+1)': '+1TH', 'TH(+2)': '+2TH', 'TH(+3)': '+3TH', 'TH(+4)': '+4TH', 'FR(-4)': '-4FR', 'FR(-3)': '-3FR', 'FR(-2)': '-2FR', 'FR(-1)': '-1FR', 'FR(+1)': '+1FR', 'FR(+2)': '+2FR', 'FR(+3)': '+3FR', 'FR(+4)': '+4FR', 'SA(-4)': '-4SA', 'SA(-3)': '-3SA', 'SA(-2)': '-2SA', 'SA(-1)': '-1SA', 'SA(+1)': '+1SA', 'SA(+2)': '+2SA', 'SA(+3)': '+3SA', 'SA(+4)': '+4SA', 'SU(-4)': '-4SU', 'SU(-3)': '-3SU', 'SU(-2)': '-2SU', 'SU(-1)': '-1SU', 'SU(+1)': '+1SU', 'SU(+2)': '+2SU', 'SU(+3)': '+3SU', 'SU(+4)': '+4SU', 'MO': 'MO', 'TU': 'TU', 'WE': 'WE', 'TH': 'TH', 'FR': 'FR', 'SA': 'SA', 'SU': 'SU'}


AWARE_FMT = "%Y%m%dT%H%MA"
NAIVE_FMT = "%Y%m%dT%H%MN"
DATE_FMT = "%Y%m%d"


def normalize_timedelta(delta):
    total_seconds = delta.total_seconds()
    sign = "-" if total_seconds < 0 else ""
    minutes, remainder = divmod(abs(int(total_seconds)), 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)
    weeks, days = divmod(days, 7)

    until = []
    if weeks:
        until.append(f"{weeks}w")
    if days:
        until.append(f"{days}d")
    if hours:
        until.append(f"{hours}h")
    if minutes:
        until.append(f"{minutes}m")
    if not until:
        until.append("0m")

    return sign + "".join(until)


# Test
td = timedelta(days=-1, hours=2, minutes=30)
normalized_td = normalize_timedelta(td)

td = timedelta(days=1, hours=-2, minutes=-30)
normalized_td = normalize_timedelta(td)


def get_anchor(aware: bool) -> datetime:
    dt = datetime(1970, 1, 1, 0, 0, 0)
    if aware:
        return dt.replace(tzinfo=ZoneInfo("UTC"))
    return dt


def encode_datetime(obj):
    if not isinstance(obj, datetime):
        raise ValueError(f"{obj} is not a datetime instance")
    if is_aware(obj):
        return obj.astimezone(ZoneInfo("UTC")).strftime(AWARE_FMT)
    else:
        return obj.strftime(NAIVE_FMT)


def decode_datetime(s):
    if s[-1] not in "AN" or len(s) != 14:
        raise ValueError(f"{s} is not a datetime string")
    if s[-1] == "A":
        return (
            datetime.strptime(s, AWARE_FMT).replace(tzinfo=ZoneInfo("UTC")).astimezone()
        )
    else:
        return datetime.strptime(s, NAIVE_FMT).astimezone(None)


def truncate_string(s: str, max_length: int) -> str:
    log_msg(f"Truncating string '{s}' to {max_length} characters")
    if len(s) > max_length:
        return f"{s[: max_length - 2]} {EtmChar.ELLIPSIS_CHAR}"
    else:
        return s


class Period:
    def __init__(self, datetime1, datetime2):
        # datetime1: done/start; datetime2: due/end. On time => period positive
        # Ensure both inputs are datetime.datetime instances
        if not isinstance(datetime1, datetime) or not isinstance(datetime2, datetime):
            raise ValueError("Both inputs must be datetime instances")

        aware1 = is_aware(datetime1)
        aware2 = is_aware(datetime2)

        if aware1 != aware2:
            raise ValueError(
                f"start: {datetime1.tzinfo}, end: {datetime2.tzinfo}. Both datetimes must either be naive or both must be aware."
            )

        if aware1:
            self.start = datetime1.astimezone(ZoneInfo("UTC"))
            self.end = datetime2.astimezone(ZoneInfo("UTC"))
        else:
            self.start = datetime1.replace(tzinfo=None)
            self.end = datetime2.replace(tzinfo=None)

        self.diff = self.end - self.start

    def __repr__(self):
        return f"Period({encode_datetime(self.start)} -> {encode_datetime(self.end)}, {normalize_timedelta(self.diff)})"

    def __eq__(self, other):
        if isinstance(other, Period):
            return self.start == other.start
        return NotImplemented

    def __lt__(self, other):
        if isinstance(other, Period):
            return self.start < other.start
        return NotImplemented

    def __gt__(self, other):
        if isinstance(other, Period):
            return self.start > other.start
        return NotImplemented

    # Optionally, define __le__ and __ge__
    def __le__(self, other):
        return self < other or self == other

    def __ge__(self, other):
        return self > other or self == other

    def start(self):
        return self.start

    def end(self):
        return self.end

    def diff(self):
        return self.diff
