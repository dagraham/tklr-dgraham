import re
from copy import deepcopy
import shutil
import json

# from dateutil.parser import parse as duparse
from dateutil.rrule import rruleset, rrulestr
from datetime import date, datetime, timedelta
from datetime import tzinfo

# from dateutil.tz import gettz
# import pytz
import textwrap
from dateutil import tz
from dateutil.tz import gettz

# from collections import defaultdict
from math import ceil

from typing import Iterable, List

from typing import Union, Optional, Tuple
from zoneinfo import ZoneInfo

# item.py
from dataclasses import dataclass
from dateutil.parser import parse as parse_dt

# from tklr.model import dt_to_dtstr
from pathlib import Path
from urllib.parse import urlparse


from .shared import (
    log_msg,
    bug_msg,
    _to_local_naive,
    print_msg,
    fmt_utc_z,
    parse_utc_z,
    timedelta_str_to_seconds,
)
from tzlocal import get_localzone_name

from .mask import obfuscate_mask_tokens, reveal_mask_tokens

local_timezone = get_localzone_name()  # e.g., "America/New_York"

JOB_PATTERN = re.compile(r"^@~ ( *)([^&]*)(?:(&.*))?")
LETTER_SET = set("abcdefghijklmnopqrstuvwxyz")  # Define once


def is_date(obj):
    if isinstance(obj, date) and not isinstance(obj, datetime):
        return True
    return False


def is_same_datetime(a: datetime, b: datetime) -> bool:
    """Return True if datetimes a and b refer to the same moment:
    - If both naive: compare directly. Same datetime or date.
    - If both aware: compare after converting to UTC.
    - Else: return False."""
    if a.tzinfo is None and b.tzinfo is None:
        return a == b
    if a.tzinfo is not None and b.tzinfo is not None:
        a_utc = a.astimezone(tz.UTC)
        b_utc = b.astimezone(tz.UTC)
        return a_utc == b_utc
    # One has tzinfo, the other doesn't — treat as non-equal (or raise)
    return False


def is_datetime(obj):
    if isinstance(obj, date) and isinstance(obj, datetime):
        return True
    return False


def is_same_datetime(a: datetime, b: datetime) -> bool:
    """Return True if datetimes a and b refer to the same moment:
    - If both naive: compare directly. Same datetime or date.
    - If both aware: compare after converting to UTC.
    - Else: return False."""
    if a.tzinfo is None and b.tzinfo is None:
        return a == b
    if a.tzinfo is not None and b.tzinfo is not None:
        a_utc = a.astimezone(tz.UTC)
        b_utc = b.astimezone(tz.UTC)
        return a_utc == b_utc
    # One has tzinfo, the other doesn't — treat as non-equal (or raise)
    return False


def _is_date_only(obj) -> bool:
    return isinstance(obj, date) and not isinstance(obj, datetime)


def _is_datetime(obj) -> bool:
    return isinstance(obj, datetime)


# --- serialization you already use elsewhere (kept explicit here) ---
def _fmt_date(d: date) -> str:
    return d.strftime("%Y%m%d")


def _fmt_naive(dt: datetime) -> str:
    # no timezone, naive
    return dt.strftime("%Y%m%dT%H%M")


def _fmt_utc_Z(dt: datetime) -> str:
    # dt must be UTC-aware
    return dt.strftime("%Y%m%dT%H%MZ")


def _local_tzname() -> str:
    # string name is sometimes handy for UI/logging
    try:
        return get_localzone_name()
    except Exception:
        return "local"


def _ensure_utc(dt: datetime) -> datetime:
    # make UTC aware
    return dt.astimezone(tz.UTC)


def _attach_zone(dt: datetime, zone) -> datetime:
    # if dt is naive, attach zone; else convert to zone
    if dt.tzinfo is None:
        return dt.replace(tzinfo=zone)
    return dt.astimezone(zone)


def _parts(s: str) -> List[str]:
    return [p for p in s.split("/") if p]


def _norm(s: str) -> str:
    return "/".join(_parts(s)).lower()


def _ordered_prefix_matches(paths: List[str], frag: str, limit: int = 24) -> List[str]:
    segs = [s.lower() for s in _parts(frag)]
    out: List[str] = []
    for p in paths:
        toks = [t.lower() for t in p.split("/")]
        if len(toks) >= len(segs) and all(
            toks[i].startswith(segs[i]) for i in range(len(segs))
        ):
            out.append(p)
            if len(out) >= limit:
                break
    out.sort(key=lambda s: (s.count("/"), s))
    return out


def _lcp(strings: List[str]) -> str:
    if not strings:
        return ""
    a, b = min(strings), max(strings)
    i = 0
    while i < len(a) and i < len(b) and a[i] == b[i]:
        i += 1
    return a[:i]


def dtstr_to_compact(dt: str) -> str:
    obj = parse_dt(dt)
    if not obj:
        return False, f"Could not parse {obj = }"

    # If the parser returns a datetime at 00:00:00, treat it as a date (your chosen convention)
    # if isinstance(obj, datetime) and obj.hour == obj.minute == obj.second == 0:
    #     return True, obj.strftime("%Y%m%d")

    if isinstance(obj, date) and not isinstance(obj, datetime):
        return True, obj.strftime("%Y%m%d")

    return True, obj.strftime("%Y%m%dT%H%M")


def local_dtstr_to_utc(dt: str) -> str:
    obj = parse_dt(dt)
    if not obj:
        return False, f"Could not parse {obj = }"

    # If the parser returns a datetime at 00:00:00, treat it as a date (your chosen convention)
    # if isinstance(obj, datetime) and obj.hour == obj.minute == obj.second == 0:
    #     return True, obj.strftime("%Y%m%d")

    if isinstance(obj, date) and not isinstance(obj, datetime):
        return True, obj.strftime("%Y%m%d")

    return True, obj.astimezone(tz.UTC).strftime("%Y%m%dT%H%MZ")


# --- parse a possible trailing " z <tzspec>" directive ---
def _split_z_directive(text: str) -> tuple[str, str | None]:
    """
    Accepts things like:
        "2025-08-24 12:00"               -> ("2025-08-24 12:00", None)
        "2025-08-24 12:00 z none"        -> ("2025-08-24 12:00", "none")
        "2025-08-24 12:00 z Europe/Berlin" -> ("2025-08-24 12:00", "Europe/Berlin")
        Only splits on the *last* " z " sequence to avoid false positives in subject text.
    """
    s = text.strip()
    marker = " z "
    idx = s.rfind(marker)
    if idx == -1:
        return s, None
    main = s[:idx].strip()
    tail = s[idx + len(marker) :].strip()
    return (main or s), (tail or None)


# --- helpers used by do_offset / finish ---------------------------------


def td_str_to_td(s: str) -> timedelta:
    """Parse a compact td string like '1w2d3h45m10s' -> timedelta."""
    # If you already have td_str_to_td, use that instead and remove this.

    units = {"w": 7 * 24 * 3600, "d": 24 * 3600, "h": 3600, "m": 60, "s": 1}
    total = 0
    for num, unit in re.findall(r"(\d+)\s*([wdhms])", s.lower()):
        total += int(num) * units[unit]
    return timedelta(seconds=total)


def td_to_td_str(td: timedelta) -> str:
    """Turn a timedelta back into a compact string like '1w2d3h'."""
    if isinstance(td, timedelta):
        secs = int(td.total_seconds())
    else:
        secs = int(td)
    parts = []
    for label, size in (("w", 604800), ("d", 86400), ("h", 3600), ("m", 60), ("s", 1)):
        if secs >= size:
            q, secs = divmod(secs, size)
            parts.append(f"{q}{label}")
    return "".join(parts) or "0s"


def _parse_o_body(body: str) -> tuple[timedelta, bool]:
    """
    Parse the body of @o. Supports:
      '@o 3d'           -> fixed interval 3 days
      '@o ~3d'          -> learning interval starting at 3 days
      '@o learn 3d'     -> same as '~3d'
    Returns (td, learn).
    """
    b = body.strip().lower()
    learn = b.startswith("~")
    if learn:
        b = b[1:]
    td = td_str_to_td(b)
    return td, learn


def parse_f_token(f_token):
    """
    Return (completion_dt, due_dt) from a single @f token.
    The second value may be None if not provided.
    """
    try:
        token_str = f_token["token"].split(maxsplit=1)[1]
        parts = [p.strip() for p in token_str.split(",", 1)]
        completion = parse_dt(parts[0])
        due = parse_dt(parts[1]) if len(parts) > 1 else None
        return completion, due
    except Exception:
        return None, None


def parse(dt_str: str, zone: tzinfo = None):
    """
    User-facing parser with a trailing 'z' directive:

      <datetime>                 -> aware in local tz, normalized to UTC (returns datetime)
      <datetime> z none          -> naive (no tz), as typed (returns datetime)
      <datetime> z <TZNAME>      -> aware in TZNAME, normalized to UTC (returns datetime)
      <date>                     -> returns date (if parsed time is 00:00:00)

    Returns: datetime (UTC or naive) or date; None on failure.
    """
    if not dt_str or not isinstance(dt_str, str):
        return None

    s = dt_str.strip()

    # Look for a trailing "z <arg>" (case-insensitive), e.g. " ... z none" or " ... z Europe/Berlin"
    m = re.search(r"\bz\s+(\S+)\s*$", s, flags=re.IGNORECASE)
    z_arg = None
    if m:
        z_arg = m.group(1)  # e.g. "none" or "Europe/Berlin"
        s = s[: m.start()].rstrip()  # remove the trailing z directive

    try:
        # Parse the main date/time text. (If you have dayfirst/yearfirst config, add it here.)
        obj = parse_dt(s)
    except Exception as e:
        log_msg(f"error: {e}, {s = }")
        return None

    # If the parser returns a datetime at 00:00:00, treat it as a date (your chosen convention)
    if isinstance(obj, datetime) and obj.hour == obj.minute == obj.second == 0:
        return obj.date()

    # If we got a pure date already, return it as-is
    if isinstance(obj, date) and not isinstance(obj, datetime):
        return obj

    # From here on, obj is a datetime
    # Case: explicit naive requested
    if z_arg and z_arg.lower() == "none":
        # Return *naive* datetime exactly as parsed (strip any tzinfo, if present)
        if obj.tzinfo is not None:
            obj = obj.astimezone(tz.UTC).replace(
                tzinfo=None
            )  # normalize then drop tzinfo
        else:
            obj = obj.replace(tzinfo=None)
        return obj

    # Otherwise: aware (local by default, or the provided zone)
    if z_arg:
        zone = tz.gettz(z_arg)
        if zone is None:
            return None  # unknown timezone name
    else:
        # default to the local machine timezone
        zone = tz.gettz(get_localzone_name())

    # Attach/convert to the chosen zone, then normalize to UTC
    if obj.tzinfo is None:
        aware = obj.replace(tzinfo=zone)
    else:
        aware = obj.astimezone(zone)

    return aware.astimezone(tz.UTC)


def parse_completion_value(v: str) -> tuple[datetime | None, datetime | None]:
    """
    Parse '@f' or '&f' value text entered in *user format* (e.g. '2024-3-1 12a, 2024-3-1 10a')
    into (finished_dt, due_dt).
    """
    parts = [p.strip() for p in v.split(",")]
    completed = parse_dt(parts[0]) if parts and parts[0] else None
    due = parse_dt(parts[1]) if len(parts) > 1 and parts[1] else None
    return completed, due


def _parse_compact_dt(s: str) -> datetime:
    """
    Accepts 'YYYYMMDD' or 'YYYYMMDDTHHMMSS' (optionally with trailing 'Z')
    and returns a naive datetime (local) for the 'THHMMSS' case, or
    midnight local for date-only.
    """
    s = (s or "").strip()
    if not s:
        raise ValueError("empty datetime string")

    z = s.endswith("Z")
    if z:
        s = s[:-1]

    if "T" in s:
        # YYYYMMDDTHHMMSS
        return datetime.strptime(s, "%Y%m%dT%H%M")
    else:
        # YYYYMMDD -> midnight (local-naive)
        d = datetime.strptime(s, "%Y%m%d").date()
        return datetime(d.year, d.month, d.day, 0, 0, 0)


class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, timedelta):
            return str(obj)
        if isinstance(obj, set):
            return list(obj)
        if isinstance(obj, ZoneInfo):
            return obj.key
        return super().default(obj)


def dt_to_dtstr(dt_obj: Union[datetime, date]) -> str:
    """Convert a datetime object to 'YYYYMMDDTHHMMSS' format."""
    if isinstance(dt_obj, date) and not isinstance(dt_obj, datetime):
        return dt_obj.strftime("%Y%m%d")
    return dt_obj.strftime("%Y%m%d%H%M")


def as_timezone(dt: datetime, timezone: ZoneInfo) -> datetime:
    if is_date(dt):
        return dt
    return dt.astimezone(timezone)


def enforce_date(dt: datetime) -> datetime:
    """
    Force dt to behave like a date (no meaningful time component).
    """
    if is_datetime(dt):
        return dt.date()
    if is_date:
        return dt
    raise ValueError(f"{dt = } cannot be converted to a date ")


def localize_rule_instances(
    rule: Iterable[Union[datetime, date]],
    timezone: Union[ZoneInfo, None],
    to_localtime: bool = False,
):
    """
    Iterate over instances from a rule parsed by rrulestr.

    - Dates are yielded unchanged.
    - Naive datetimes are assigned the given timezone.
    - Aware datetimes are optionally converted to system localtime.
    """
    if timezone == "local":
        timezone = get_localzone_name()

    for dt in rule:
        if is_date(dt) or not to_localtime:
            yield dt
        else:
            # dt is a datetime
            if dt.tzinfo is None:
                if timezone is not None:
                    dt = dt.replace(tzinfo=timezone)
                else:
                    dt = dt.replace(
                        # tzinfo=tz.UTC
                        tzinfo=tz.tzlocal()
                    )  # fallback to UTC if timezone missing
            if to_localtime:
                dt = dt.astimezone()

            yield dt


def localize_datetime_list(
    dts: List[datetime], timezone: ZoneInfo, to_localtime: bool = False
) -> List[datetime]:
    """
    Localize a list of datetime objects.

    - Attach timezone to naive datetimes
    - Optionally convert to system local time
    - Returns a new list of timezone-aware datetimes
    """
    localized = []
    for dt in dts:
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone)
        if to_localtime:
            dt = dt.astimezone()
        localized.append(dt)
    return localized


def preview_rule_instances(
    rule: rruleset,
    timezone: Union[ZoneInfo, None] = None,
    count: int = 10,
    after: Optional[Union[datetime, date]] = None,
    to_localtime: bool = False,
) -> List[Union[datetime, date]]:
    instances = []
    generator = localize_rule_instances(rule, timezone, to_localtime)

    if after is None:
        after_datetime = datetime.now().astimezone()
        after_date = date.today()

    for dt in list(generator):
        if is_date(dt):
            if dt < after_date:
                continue
        else:
            if dt.astimezone() < after_datetime:
                continue

        instances.append(dt)
        if len(instances) >= count:
            break

    return instances


def preview_upcoming_instances(
    rule: rruleset, timezone: ZoneInfo, count: int = 10, to_localtime: bool = False
) -> List[datetime]:
    """
    Shortcut to preview the next N upcoming localized instances, starting from now.
    """
    now = datetime.now().astimezone()
    return preview_rule_instances(
        rule, timezone, count=count, after=now, to_localtime=to_localtime
    )


def pp_set(s):
    return "{}" if not s else str(s)


def is_lowercase_letter(char):
    return char in LETTER_SET  # O(1) lookup


type_keys = {
    "*": "event",
    "~": "task",
    "^": "project",
    "%": "note",
    "!": "goal",
    "?": "draft",
    "x": "finished",
    # '✓': 'finished',  # more a property of a task than an item type
}
# common_methods = list("cdgblmnstxz") + ["k", "#"]
common_methods = list("cdgblmnstx") + [
    "k",
]

repeating_methods = list("o") + [
    "r",
    "rr",
    "rc",
    "rd",  # monthdays
    "rm",  # months
    "rH",  # hours
    "rM",  # minutes
    "rE",
    "ri",
    "rs",
    "ru",
    "rW",  # week numbers
    "rw",  # week days
]

datetime_methods = list("anew+-")

task_methods = list("ofp")

job_methods = list("efhp") + [
    "~",
    "~r",
    "~j",
    "~a",
    "~b",
    "~c",
    "~d",
    "~e",
    "~f",
    "~i",
    "~l",
    "~m",
    "~p",
    "~s",
]

multiple_allowed = [
    "a",
    "b",
    "r",
    "t",
    "~",
    "~r",
    "~t",
    "~a",
]

wrap_methods = ["w"]

required = {"*": ["s"], "~": [], "^": ["~"], "%": [], "?": [], "!": ["s", "t"], "x": []}

all_keys = common_methods + datetime_methods + job_methods + repeating_methods

allowed = {
    "*": common_methods + datetime_methods + repeating_methods + wrap_methods,
    "x": common_methods + datetime_methods + task_methods + repeating_methods + ["~"],
    "~": common_methods + datetime_methods + task_methods + repeating_methods,
    "!": common_methods + ["s", "t", "f", "k"],
    "^": common_methods + datetime_methods + job_methods + repeating_methods,
    "%": common_methods + datetime_methods,
    "?": all_keys,
}


requires = {
    "a": ["s"],
    "n": ["s"],
    "o": ["s"],
    "+": ["s"],
    "q": ["s"],
    "-": ["rr"],
    "r": ["s"],
    "rr": ["s"],
    "~s": ["s"],
    "~a": ["s"],
    "~b": ["s"],
}


class Paragraph:
    # Placeholder to preserve line breaks
    NON_PRINTING_CHAR = "\u200b"
    # Placeholder for spaces within special tokens
    PLACEHOLDER = "\u00a0"
    # Placeholder for hyphens to prevent word breaks
    NON_BREAKING_HYPHEN = "\u2011"

    def __init__(self, para: str):
        self.para = para

    def preprocess_text(self, text):
        # Regex to find "@\S" patterns and replace spaces within the pattern with PLACEHOLDER
        text = re.sub(
            r"(@\S+\s\S+)",
            lambda m: m.group(0).replace(" ", Paragraph.PLACEHOLDER),
            text,
        )
        # Replace hyphens within words with NON_BREAKING_HYPHEN
        text = re.sub(
            r"(\S)-(\S)",
            lambda m: m.group(1) + Paragraph.NON_BREAKING_HYPHEN + m.group(2),
            text,
        )
        return text

    def postprocess_text(self, text):
        text = text.replace(Paragraph.PLACEHOLDER, " ")
        text = text.replace(Paragraph.NON_BREAKING_HYPHEN, "-")
        return text

    def wrap(
        self, text: str, indent: int = 3, width: int = shutil.get_terminal_size()[0] - 3
    ):
        # Preprocess to replace spaces within specific "@\S" patterns with PLACEHOLDER
        text = self.preprocess_text(text)

        # Split text into paragraphs
        paragraphs = text.split("\n")

        # Wrap each paragraph
        wrapped_paragraphs = []
        for para in paragraphs:
            leading_whitespace = re.match(r"^\s*", para).group()
            initial_indent = leading_whitespace

            # Determine subsequent_indent based on the first non-whitespace character
            stripped_para = para.lstrip()
            if stripped_para.startswith(("^", "~", "*", "%", "?", "+")):
                subsequent_indent = initial_indent + " " * 2
            elif stripped_para.startswith(("@", "&")):
                subsequent_indent = initial_indent + " " * 3
            else:
                subsequent_indent = initial_indent + " " * indent

            wrapped = textwrap.fill(
                para,
                initial_indent="",
                subsequent_indent=subsequent_indent,
                width=width,
            )
            wrapped_paragraphs.append(wrapped)

        # Join paragraphs with newline followed by non-printing character
        wrapped_text = ("\n" + Paragraph.NON_PRINTING_CHAR).join(wrapped_paragraphs)

        # Postprocess to replace PLACEHOLDER and NON_BREAKING_HYPHEN back with spaces and hyphens
        wrapped_text = self.postprocess_text(wrapped_text)
        return wrapped_text

    def unwrap(wrapped_text):
        # Split wrapped text into paragraphs
        paragraphs = wrapped_text.split("\n" + Paragraph.NON_PRINTING_CHAR)

        # Replace newlines followed by spaces in each paragraph with a single space
        unwrapped_paragraphs = []
        for para in paragraphs:
            unwrapped = re.sub(r"\n\s*", " ", para)
            unwrapped_paragraphs.append(unwrapped)

        # Join paragraphs with original newlines
        unwrapped_text = "\n".join(unwrapped_paragraphs)

        return unwrapped_text


# @dataclass
# class FinishResult:
#     new_relative_tokens: list  # tokens to persist
#     new_rruleset: str | None  # possibly None/"" if no more repeats
#     due_ts_used: int | None  # the occurrence this finish applies to
#     finished_final: bool  # True -> no more occurrences


class Item:
    GROUPABLE_ANCHOR_KEYS: frozenset[str] = frozenset({"r", "~"})

    token_keys = {
        "itemtype": [
            "item type",
            "character from * (event), ~ (task), ^ (project), % (note), ! (goal),  x (finished) or ? (draft)",
            "do_itemtype",
        ],
        "subject": [
            "subject",
            "item subject. Append an '@' to add an option.",
            "do_subject",
        ],
        "s": ["scheduled", "starting date or datetime", "do_s"],
        "r": ["recurrence", "recurrence rule", "do_r"],
        "o": ["offset", "offset rule", "do_offset"],
        "t": ["target", "a goal target entry such as '3/w'", "do_target"],
        "~": ["job", "job entry", "do_job"],
        "+": ["rdate", "recurrence dates", "do_plus"],
        "-": ["exdate", "exception dates", "do_minus"],
        "a": ["alerts", "list of alerts", "do_alert"],
        "n": ["notice", "timeperiod", "do_notice"],
        "c": ["context", "context", "do_string"],
        "d": ["details", "expanded notes", "do_d"],
        "e": ["extent", "timeperiod", "do_e"],
        "w": ["wrap", "list of two timeperiods", "do_two_periods"],
        "f": ["finish", "completion done -> due", "do_f"],
        "g": ["goto", "url or filepath", "do_string"],
        "h": [
            "completions",
            "list of completion datetimes",
            "do_fs",
        ],
        "b": ["bin", "forward slash delimited string", "do_b"],
        "l": [
            "label",
            "label for job clone",
            "do_string",
        ],
        "m": ["mask", "string to be masked", "do_mask"],
        "p": [
            "priority",
            "priority from 1 (someday), 2 (low), 3 (medium), 4 (high) to 5 (next)",
            "do_priority",
        ],
        "w": ["wrap", "wrap before, after", "do_wrap"],
        "@": ["@-key", "", "do_at"],
        "rr": [
            "repetition frequency",
            "character from (y)ear, (m)onth, (w)eek,  (d)ay, (h)our, mi(n)ute. Append an '&' to add a repetition option.",
            "do_frequency",
        ],
        "ri": ["interval", "positive integer", "do_interval"],
        "rm": ["months", "list of integers in 1 ... 12", "do_months"],
        "rd": [
            "monthdays",
            "list of integers 1 ... 31, possibly prepended with a minus sign to count backwards from the end of the month",
            "do_monthdays",
        ],
        "rE": [
            "easterdays",
            "number of days before (-), on (0) or after (+) Easter",
            "do_easterdays",
        ],
        "rH": ["hours", "list of integers in 0 ... 23", "do_hours"],
        "rM": ["minutes", "list of integers in 0 ... 59", "do_minutes"],
        "rw": [
            "weekdays",
            "list from SU, MO, ..., SA, possibly prepended with a positive or negative integer",
            "do_weekdays",
        ],
        "rW": [
            "week numbers",
            "list of integers in 1, ... 53",
            "do_weeknumbers",
        ],
        "rc": ["count", "integer number of repetitions", "do_count"],
        "ru": ["until", "datetime", "do_until"],
        "rs": ["set positions", "integer", "do_setpositions"],
        "r?": ["repetition &-key", "enter &-key", "do_ampr"],
        "~~": [
            "subject",
            "do_string",
        ],
        "~a": [
            "alert",
            "list of timeperiods before job is scheduled followed by a colon and a list of commands",
            "do_alert",
        ],
        "~n": ["notice", " notice period", "do_notice"],
        "~c": ["context", " string", "do_string"],
        "~d": ["description", " string", "do_d"],
        "~e": ["extent", " timeperiod", "do_e"],
        "~f": ["finish", " completion done -> due", "do_f"],
        "~i": ["unique id", " integer or string", "do_string"],
        "~l": ["label", " string", "do_string"],
        "~m": ["mask", "string to be masked", "do_mask"],
        "~r": [
            "id and list of requirement ids",
            "list of ids of immediate prereqs",
            "do_requires",
        ],
        "~s": [
            "scheduled",
            "timeperiod after task scheduled when job is scheduled",
            "do_job_s",
        ],
        # "~u": ["used time", "timeperiod: datetime", "do_usedtime"],
        "~?": ["job &-key", "enter &-key", "do_ampj"],
        "k": ["konnection", "not implemented", "do_nothing"],
        # "#": ["etm record number", "not implemented", "do_nothing"],
    }

    wkd_list = ["SU", "MO", "TU", "WE", "TH", "FR", "SA"]
    wkd_str = ", ".join(wkd_list)

    freq_map = dict(
        y="YEARLY", m="MONTHLY", w="WEEKLY", d="DAILY", h="HOURLY", n="MINUTELY"
    )

    key_to_param = dict(
        i="INTERVAL",
        c="COUNT",
        s="BYSETPOS",
        u="UNTIL",
        m="BYMONTH",
        d="BYMONTHDAY",
        W="BYWEEKNO",
        w="BYWEEKDAY",
        H="BYHOUR",
        M="BYMINUTE",
        E="BYEASTER",
    )
    param_to_key = {v: k for k, v in key_to_param.items()}

    def __init__(self, *args, **kwargs):
        """
        Compatible constructor that accepts:
        - Item(entry_str)
        - Item(raw=entry_str)
        - Item(env, entry_str)
        - Item(env=env, raw=entry_str)
        - Item(entry_str, env=env)
        """
        # --- resolve arguments flexibly ---
        self.controller = kwargs.get("controller")

        env = kwargs.get("env")
        raw = kwargs.get("raw")
        self.final: bool = bool(kwargs.get("final", False))  # ← NEW

        # try positional decoding without importing the type
        a = args[0] if len(args) > 0 else None
        b = args[1] if len(args) > 1 else None

        # heuristics: strings are raw; non-strings are likely env
        if raw is None and isinstance(a, str):
            raw = a
            a = None
        if env is None and a is not None and not isinstance(a, str):
            env = a
            a = None

        if raw is None and isinstance(b, str):
            raw = b
            b = None
        if env is None and b is not None and not isinstance(b, str):
            env = b
            b = None

        # iso standard defaults
        self.datefmt = "%Y-%m-%d"
        self.timefmt = "%H:%M"

        # --- environment / config ---
        resolved_env = env or getattr(self.controller, "env", None)
        self.env = resolved_env

        # --- core parse state ---
        self.entry = ""
        self.itemtype = ""
        self.subject = ""
        self.context = ""
        self.description = ""
        self.token_map = {}
        self.parse_ok = False
        self.parse_message = ""
        self.relative_tokens = []
        self.last_result = ()
        self.bin_paths = []
        self.tokens = []
        self.messages = []
        self.validate_messages = []

        # --- schedule / tokens / jobs ---
        self.extent = ""
        self.rruleset = ""
        self.rrule_tokens = []
        self.rrule_components = []
        self.rrule_parts = []
        self.job_tokens = []
        self.token_store = None
        self.rrules = []
        self.jobs = []
        self.bin_paths = []
        self.jobset = []
        self.priority = None
        self.alerts = []
        self.notice = ""

        # --- date/time collections (strings) ---
        self.s_kind = ""
        self.s_tz = None
        self.rdates = []
        self.exdates = []
        self.rdate_str = ""
        self.exdate_str = ""
        self.rruleset_dict = {}

        # --- DTSTART / RDATE (preserve your sentinels) ---
        self.dtstart = None
        self.dtstart_str = None  # important: keep None (not "")
        self.rdstart_str = ""

        # --- timezone defaults (match your previous working code) ---

        self.timezone = get_localzone_name()
        self.tz_str = local_timezone

        # TODO: remove these
        self.skip_token_positions = set()
        self.token_group_anchors = {}

        # --- other flags / features ---
        self.completion = None  # for the completed datetime from @f entry - not a tuple
        self.completions = []  # (completed, due) to update Completions table - a (completed, due) tuple
        self.over = ""
        self.has_f = False  # True if there is an @f to process after parsing tokens
        self.has_s = False  # True if there is an @s to process after parsing tokens

        # --- optional initial parse ---
        self.ampm = False
        self.yearfirst = True
        self.dayfirst = False
        self.history_weight = 3
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

        # print(f"{self.ampm = }, {self.yearfirst = }, {self.dayfirst = }")
        #
        # dayfirst  yearfirst    date     interpretation  standard
        # ========  =========  ========   ==============  ========
        #   True     True      12-10-11    2012-11-10     Y-D-M ??
        #   True     False     12-10-11    2011-10-12     D-M-Y EU
        #   False    True      12-10-11    2012-10-11     Y-M-D ISO 8601
        #   False    False     12-10-11    2011-12-10     M-D-Y US
        #   dayfirst D-M else M-D
        #   yearfirst first else last
        #   DM = %d-%m if dayfirst else "%m-%d"
        #   DMY = f"%Y-{DM}" if yearfirst else f"{DM}-%Y"

        if raw:
            self.entry = raw
            self.parse_input(raw)
            # if self.final:
            #     self.finalize_record()
            #

    def get_name_to_binpath(self) -> dict:
        if self.final or not self.controller:
            return {}
        return self.controller.get_name_to_binpath()

    def to_entry(self) -> str:
        """
        Rebuild a tklr entry string from this Item’s fields.
        """
        # --- map itemtype ---
        itemtype = self.itemtype

        # --- start with type and subject ---
        parts = [f"{itemtype} {self.subject}"]

        # --- description (optional, inline or multi-line) ---
        if self.description:
            parts.append(self.description)

        # --- scheduling tokens ---
        if getattr(self, "dtstart_str", None):
            dt = self._get_start_dt()
            if dt:
                parts.append(f"@s {self.fmt_user(dt)}")

        if getattr(self, "extent", None):
            parts.append(f"@e {self.extent}")

        if getattr(self, "rruleset", None):
            parts.append(f"@r {self.rruleset}")

        if getattr(self, "notice", None):
            parts.append(f"@n {self.notice}")

        # --- context ---
        if getattr(self, "context", None):
            parts.append(f"@c {self.context}")

        # --- jobs ---
        if getattr(self, "jobs", None) and self.jobs not in ("[]", None):
            try:
                jobs = json.loads(self.jobs)
            except Exception:
                jobs = []
            for j in jobs:
                subj = j.get("summary") or j.get("subject")
                if subj:
                    parts.append(f"@~ {subj}")

        return " ".join(parts)

    def parse_input(self, entry: str):
        """
        Parses the input string to extract tokens, then processes and validates the tokens.
        """
        # digits = "1234567890" * ceil(len(entry) / 10)

        self._tokenize(entry)
        # NOTE: _tokenize sets self.itemtype and self.subject

        self.parse_message = self.validate()
        if self.parse_message:
            self.parse_ok = False
            return f"parse failed: {self.parse_message = }"

        self._parse_tokens(entry)

        self.parse_ok = True

        if self.final:
            self.finalize_record()

    def _remove_instance_from_plus_tokens(
        self, tokens: list[dict], tok_str: str
    ) -> bool:
        """
        Remove an entry matching tok_local_str (local format e.g. '20251122T1000')
        from any @+ tokens in the list. If removal empties a @+ list,
        remove that token entirely. Return True if removal happened.
        """
        changed = False
        new_tokens = []
        target_dt = None
        try:
            target_dt = _to_local_naive(parse(tok_str))
        except Exception:
            target_dt = None
            tok_str = tok_str.strip()

        for tok in tokens:
            if tok.get("k") == "+":
                body = tok["token"][2:].strip()
                parts = [p.strip() for p in body.split(",") if p.strip()]
                filtered = []
                for part in parts:
                    match = False
                    if target_dt is not None:
                        try:
                            part_dt = _to_local_naive(parse(part))
                            match = part_dt == target_dt
                        except Exception:
                            match = False
                    if not match:
                        match = part == tok_str
                    if match:
                        changed = True
                    else:
                        filtered.append(part)
                if len(filtered) < len(parts):
                    changed = True
                    if filtered:
                        tok["token"] = "@+ " + ", ".join(filtered)
                        new_tokens.append(tok)
                    # else: drop this token entirely
                else:
                    new_tokens.append(tok)
            else:
                new_tokens.append(tok)
        if changed:
            tokens[:] = new_tokens
        return changed

    def finalize_record(self):
        """
        When the entry and token list is complete:
        1) finalize jobs, processing any &f entries and adding @f when all jobs are finished
        2) finalize_rruleset so that next instances will be available
        3) process @f entries (&f entries will have been done by finalize_jobs)

        """
        if self.has_s:
            self._set_start_dt()

        if self.collect_grouped_tokens({"r"}):
            rruleset = self.finalize_rruleset()
            if rruleset:
                self.rruleset = rruleset
        elif self.rdstart_str is not None:
            # @s but not @r
            self.rruleset = self.rdstart_str

        if self.itemtype == "^":
            jobset = self.build_jobs()
            success, finalized = self.finalize_jobs(jobset)
        # rruleset is needed to get the next two occurrences

        if self.has_f:
            self.finish()
            # self.has_f = False

        stripped_tokens = self._strip_positions(self.relative_tokens)
        self.tokens = self._encode_mask_tokens(stripped_tokens)

    def validate(self):
        self.validate_messages = []

        def fmt_error(message: str):
            # return [x.strip() for x in message.split(",")]
            self.validate_messages.append(message)
            return message

        errors = []

        if len(self.entry.strip()) < 1:
            # nothing to validate without itemtype and subject
            return fmt_error("""\
Reminders begin with a type character from:
    * (event), ~ (task), ^ (project),
    % (note),  ! (goal), ? (draft)
followed by a space and the subject.
""")

        if len(self.relative_tokens) < 1:
            # nothing to validate without itemtype and subject
            return fmt_error(f"""\
Error: an itemtype from:
    * (event), ~ (task), ^ (project),
    % (note),  ! (goal), ? (draft)
must be the first character.
Entry: {self.entry}
""")

        if len(self.relative_tokens) < 2:
            # nothing to validate without itemtype and subject
            return fmt_error("The subject of the reminder follows the itemtype.")

        self.itemtype = self.relative_tokens[0]["token"]
        if not self.itemtype:
            return "no itemtype"

        self.subject = self.relative_tokens[1]["token"].strip()
        if not self.subject or self.subject.startswith("@"):
            return fmt_error("Enter a subject for the reminder.")
        allowed_fortype = allowed[self.itemtype]
        # required_fortype = required[self.itemtype]
        needed = deepcopy(required[self.itemtype])

        current_atkey = None
        used_atkeys = []
        used_ampkeys = []
        count = 0
        # print(f"{len(self.relative_tokens) = }")
        for token in self.relative_tokens:
            count += 1
            if token.get("incomplete", False):
                type = token["t"]
                if token.get("t", "") == "@" and token.get("k", "") == "":
                    need = (
                        f"  required: {', '.join(needed)}\n"
                        if needed and type == "@"
                        else ""
                    )
                    options = []
                    options = (
                        [x for x in allowed_fortype if len(x) == 1]
                        if type == "@"
                        else [x[-1] for x in allowed_fortype if len(x) == 2]
                    )
                    optional = f"  optional: {', '.join(options)}" if options else ""
                    return fmt_error(
                        f"{token['t']} available @-keys:\n{need}{optional}"
                    )

            if token["t"] == "@":
                used_ampkeys = []
                this_atkey = token["k"]

                if this_atkey not in all_keys:
                    return fmt_error(f"@{this_atkey}, Unrecognized @-key")
                if this_atkey not in allowed_fortype:
                    return fmt_error(
                        f"The use of @{this_atkey} is not supported in type '{self.itemtype}' reminders"
                    )
                if this_atkey in used_atkeys and this_atkey not in multiple_allowed:
                    return fmt_error(
                        f"Multiple instances of this @{this_atkey} are not allowed"
                    )

                current_atkey = this_atkey
                used_atkeys.append(current_atkey)

                if this_atkey in ["r", "~"]:
                    used_atkeys.append(f"{current_atkey}{current_atkey}")
                    used_ampkeys = []
                if current_atkey in needed:
                    needed.remove(current_atkey)
                if current_atkey in requires:
                    for _key in requires[current_atkey]:
                        if _key not in used_atkeys and _key not in needed:
                            needed.append(_key)
                if token.get("incomplete", False):
                    # return the info for this key until the beginning of a value is entered
                    return fmt_error(f"{': '.join(self.token_keys[this_atkey][:2])}")

            elif token["t"] == "&":
                this_ampkey = f"{current_atkey}{token['k']}"
                if current_atkey not in ["r", "~"]:
                    return fmt_error(
                        f"&{token['k']}, The use of &-keys is not supported for @{current_atkey}"
                    )

                if this_ampkey not in all_keys:
                    return fmt_error(
                        f"&{token['k']}, This &-key is not supported for @{current_atkey}"
                    )
                if this_ampkey in used_ampkeys and this_ampkey not in multiple_allowed:
                    return fmt_error(
                        f"&{this_ampkey}, Multiple instances of this &-key are not supported"
                    )
                used_ampkeys.append(this_ampkey)

        if needed:
            needed_keys = ", ".join("@" + k for k in needed)
            needed_msg = (
                # f"Required keys not yet provided: {needed_keys} in {self.entry = }"
                f"Required keys not yet provided: {needed_keys = }\n {used_atkeys = }, {used_ampkeys = }"
            )
        else:
            needed_msg = ""
        return needed_msg

    def fmt_user(self, dt: date | datetime) -> str:
        """
        User friendly formatting for dates and datetimes using env settings
        for ampm, yearfirst, dayfirst and two_digit year.
        """
        # Simple user-facing formatter; tweak to match your prefs
        if isinstance(dt, datetime):
            d = dt
            if (
                d.tzinfo == tz.UTC or not self.timezone
            ):  # and not getattr(self, "final", False):
                d = d.astimezone()
            return d.strftime(self.datetimefmt)
        if isinstance(dt, date):
            return dt.strftime(self.datefmt)
        raise ValueError(f"Error: {dt} must either be a date or datetime")

    def fmt_verbose(self, dt: date | datetime) -> str:
        """
        User friendly formatting for dates and datetimes using env settings
        for ampm, yearfirst, dayfirst and two_digit year.
        """
        # Simple user-facing formatter; tweak to match your prefs
        if isinstance(dt, datetime):
            d = dt
            if (
                d.tzinfo == tz.UTC or not self.timezone
            ):  # and not getattr(self, "final", False):
                d = d.astimezone()
            return d.strftime(f"%a, %b %-d %Y {self.timefmt}")
        if isinstance(dt, date):
            return dt.strftime("%a, %b %-d %Y")
        raise ValueError(f"Error: {dt} must either be a date or datetime")

    def fmt_compact(self, dt: datetime) -> str:
        """
        Compact formatting for dates and datetimes using env settings
        for ampm, yearfirst, dayfirst and two_digit year.
        """
        log_msg(f"formatting {dt = }")
        # Simple user-facing formatter; tweak to match your prefs
        if isinstance(dt, datetime):
            return _fmt_naive(dt)
        if isinstance(dt, date):
            return _fmt_date(dt)
        raise ValueError(f"Error: {dt} must either be a date or datetime")

    def parse_user_dt_for_s(
        self, user_text: str
    ) -> tuple[date | datetime | None, str, str | None]:
        """
        Returns (obj, kind, tz_name_used)
        kind ∈ {'date','naive','aware','error'}
        tz_name_used: tz string ('' means local), or None for date/naive/error
        On error: (None, 'error', <message>)
        """
        core, zdir = _split_z_directive(user_text)

        try:
            obj = parse_dt(core, dayfirst=self.dayfirst, yearfirst=self.yearfirst)
        except Exception as e:
            # return None, "error", f"Could not parse '{core}': {e.__class__.__name__}"
            return None, "error", f"Error parsing '{core}'"

        # DATE if midnight or a pure date object
        if _is_date_only(obj) or (
            _is_datetime(obj)
            and obj.hour == obj.minute == obj.second == 0
            and obj.tzinfo is None
        ):
            if _is_datetime(obj):
                obj = obj.date()
            return obj, "date", None

        # DATETIME
        if zdir and zdir.lower() == "none":
            # NAIVE: keep naive (strip tz if present)
            if _is_datetime(obj) and obj.tzinfo is not None:
                obj = obj.replace(tzinfo=None)
            return obj, "naive", None

        # AWARE
        if zdir:
            zone = tz.gettz(zdir)
            if zone is None:
                # >>> HARD FAIL on invalid tz <<<
                return None, "error", f"Unknown timezone: {zdir!r}"
            tz_used = zdir
        else:
            zone = tz.tzlocal()
            tz_used = ""  # '' means "local tz"

        obj_aware = _attach_zone(obj, zone)
        obj_utc = _ensure_utc(obj_aware)
        return obj_utc, "aware", zone

    def collect_grouped_tokens(self, anchor_keys: set[str]) -> list[list[dict]]:
        """
        Collect multiple groups of @-tokens and their immediately trailing &-tokens.

        anchor_keys: e.g. {'r', '~', 's'} — only these @-keys start a group.

        Returns:
            List of token groups: each group is a list of relative tokens:
            [ [anchor_tok, &tok, &tok, ...], ... ]
        """
        groups: list[list[dict]] = []
        for group in self._build_group_metadata():
            if not group:
                continue
            anchor = group[0]
            if anchor.get("t") == "@" and anchor.get("k") in anchor_keys:
                groups.append(list(group))
        return groups

    def mark_grouped_tokens(self):
        """
        Build:
        - skip_token_positions: set of (s,e) spans for &-tokens that belong to an @-group,
            so your dispatcher can skip re-processing them.
        - token_group_anchors: map (s,e) of each grouped &-token -> (s,e) of its @-anchor.
        Also prepares self.token_group_map via build_token_group_map().
        """
        self.skip_token_positions = set()
        self.token_group_anchors = {}

        groups = [
            group
            for group in self._build_group_metadata()
            if group
            and group[0].get("t") == "@"
            and group[0].get("k") in self.GROUPABLE_ANCHOR_KEYS
        ]

        for group in groups:
            anchor = group[0]
            anchor_pos = (anchor["s"], anchor["e"])
            for token in group[1:]:
                pos = (token["s"], token["e"])
                self.skip_token_positions.add(pos)
                self.token_group_anchors[pos] = anchor_pos

        # Build the easy-to-consume map (e.g., token_group_map['s'] -> [("z","CET")])
        self.build_token_group_map(groups)

    def build_token_group_map(self, groups: list[list[dict]]):
        """
        Convert grouped tokens into a simple dict:
        self.token_group_map = {
            'r': [('i','2'), ('c','10'), ...],
            's': [('z','CET'), ...],
            '~': [('f','20250824T120000'), ...],
        }
        Keys are only present if that @-anchor appears in self.relative_tokens.
        """
        tgm: dict[str, list[tuple[str, str]]] = {}
        for group in groups:
            anchor = group[0]
            if anchor.get("t") != "@":
                continue
            akey = anchor.get("k")  # 'r', '~', or 's'
            if not akey:
                continue
            pairs: list[tuple[str, str]] = []
            for tok in group[1:]:
                if tok.get("t") != "&":
                    continue
                k = (tok.get("k") or "").strip()
                # raw value after '&x ':
                try:
                    _, v = tok["token"].split(" ", 1)
                    v = v.strip()
                except Exception as e:
                    log_msg(f"error: {e = }")
                    v = ""
                pairs.append((k, v))
            if pairs:
                tgm.setdefault(akey, []).extend(pairs)

        self.token_group_map = tgm

    def add_token(self, token: dict):
        """
        keys: token (entry str), t (type: itemtype, subject, @, &),
              k (key: a, b, c, d, ... for type @ and &.
              type itemtype and subject have no key)
        add_token takes a token dict and
        1) appends the token as is to self.relative_tokens
        2) extract the token, t and k fields, expands the datetime value(s) for k in list("sf+-")
           and appends the resulting dict to self.stored_tokens
        """

        self.tokens.append(token)

    def _tokenize(self, entry: str):
        self.entry = entry
        self.errors = []
        self.tokens = []
        self.messages = []
        self.relative_tokens = []
        self.stored_tokens = []
        self.subject = ""

        if not entry:
            self.messages.append(
                (False, ": ".join(Item.token_keys["itemtype"][:2]), [])
            )
            return
        if entry[0] not in {"*", "~", "^", "%", "!", "x", "?"}:
            self.messages.append(
                (
                    False,
                    f"Invalid itemtype '{entry[0]}' (expected *, ~, ^, %, !, x or ?)",
                    [],
                )
            )
            return
        # we have an itemtype
        itemtype = entry[0]
        self.itemtype = itemtype
        self.relative_tokens.append(
            {"token": itemtype, "s": 0, "e": 1, "t": "itemtype"}
        )

        # --- subject (everything until the next '@') ---
        cursor = 1
        n_chars = len(entry)
        while cursor < n_chars and entry[cursor].isspace():
            cursor += 1
        subject_start = cursor
        while cursor < n_chars and entry[cursor] != "@":
            cursor += 1
        subject_slice = entry[subject_start:cursor]
        self.subject = subject_slice.strip()
        self.relative_tokens.append(
            {"token": subject_slice, "s": subject_start, "e": cursor, "t": "subject"}
        )

        # --- option tokens (@ / &) ---
        remainder_start = cursor
        remainder = entry[remainder_start:]
        pattern = (
            r"(?:(?<=^)|(?<=\s))(@[\w~+\-]+ [^@&]+)|(?:(?<=^)|(?<=\s))(&\w+ [^@&]+)"
        )
        for match in re.finditer(pattern, remainder):
            token_text = match.group(0)
            start_pos = remainder_start + match.start()
            end_pos = remainder_start + match.end()
            token_type = "@" if token_text.startswith("@") else "&"
            key = token_text[1:3].strip()
            self.relative_tokens.append(
                {
                    "token": token_text,
                    "s": start_pos,
                    "e": end_pos,
                    "t": token_type,
                    "k": key,
                }
            )

        # --- partial token handling (user still typing) ---
        partial_token = None
        at_partial = re.search(r"@([A-Za-z]?)$", entry)
        if at_partial and " " not in at_partial.group(0):
            partial_token = {
                "token": "@" + at_partial.group(1),
                "s": len(entry) - len(at_partial.group(0)),
                "e": len(entry),
                "t": "@",
                "k": at_partial.group(1),
                "incomplete": True,
            }
        else:
            at_space_partial = re.search(r"@([A-Za-z]+)\s*$", entry)
            if at_space_partial:
                partial_token = {
                    "token": entry[len(entry) - len(at_space_partial.group(0)) :],
                    "s": len(entry) - len(at_space_partial.group(0)),
                    "e": len(entry),
                    "t": "@",
                    "k": at_space_partial.group(1),
                    "incomplete": True,
                }
            else:
                amp_partial = re.search(r"&([A-Za-z]*)$", entry)
                if amp_partial and " " not in amp_partial.group(0):
                    parent = None
                    for tok in reversed(self.relative_tokens):
                        if (
                            tok["t"] == "@"
                            and tok.get("k") in self.GROUPABLE_ANCHOR_KEYS
                        ):
                            parent = tok["k"]
                            break
                    partial_token = {
                        "token": "&" + amp_partial.group(1),
                        "s": len(entry) - len(amp_partial.group(0)),
                        "e": len(entry),
                        "t": "&",
                        "k": amp_partial.group(1),
                        "parent": parent,
                        "incomplete": True,
                    }

        if partial_token:
            self.relative_tokens.append(partial_token)

        self._build_group_metadata()

    def _build_group_metadata(self) -> list[list[dict]]:
        """
        Precompute groupings for @-tokens that own &-tokens so downstream code
        can skip rescanning the flat token list.
        """
        token_groups: list[list[dict]] = []
        anchor_token: dict | None = None
        current_group: list[dict] = []

        for token in self.relative_tokens:
            token.pop("_children", None)
            token.pop("parent", None)
            token.pop("anchor_span", None)

            if token.get("t") == "@":
                key = token.get("k")
                if key in self.GROUPABLE_ANCHOR_KEYS:
                    if current_group:
                        token_groups.append(current_group)
                        current_group = []
                    anchor_token = token
                    token["_children"] = []
                    current_group = [token]
                else:
                    if current_group:
                        token_groups.append(current_group)
                        current_group = []
                    anchor_token = None
            elif token.get("t") == "&":
                if anchor_token is not None:
                    token["parent"] = anchor_token.get("k")
                    token["anchor_span"] = (anchor_token["s"], anchor_token["e"])
                    anchor_token.setdefault("_children", []).append(token)
                    current_group.append(token)
                else:
                    token["parent"] = None
            else:
                if current_group:
                    token_groups.append(current_group)
                    current_group = []
                anchor_token = None

        if current_group:
            token_groups.append(current_group)

        return token_groups

    def _parse_tokens(self, entry: str):
        """
        Re-parse the entire entry every time input changes. Entries are short,
        so a full pass is simpler and more reliable than diffing incremental edits.
        """
        self._parse_all_tokens()

    def _parse_all_tokens(self):
        self.mark_grouped_tokens()

        dispatched_anchors = set()
        self.stored_tokens = []

        for token in self.relative_tokens:
            # print(f"parsing {token = }")
            start_pos, end_pos = token["s"], token["e"]
            # if token.get("k", "") in ["+", "-", "s", "f"]:
            if (start_pos, end_pos) in self.skip_token_positions:
                continue  # skip component of a group

            if (start_pos, end_pos) in self.token_group_anchors:
                anchor_pos = self.token_group_anchors[(start_pos, end_pos)]
                if anchor_pos in dispatched_anchors:
                    continue
                anchor_token_info = next(
                    t for t in self.tokens if (t[1], t[2]) == anchor_pos
                )
                token_str, anchor_start, anchor_end = anchor_token_info
                token_type = token["k"]
                self._dispatch_token(token_str, anchor_start, anchor_end, token_type)
                dispatched_anchors.add(anchor_pos)
                continue

            if start_pos == 0:
                self._dispatch_token(token, start_pos, end_pos, "itemtype")
            elif start_pos == 2:
                self._dispatch_token(token, start_pos, end_pos, "subject")
            elif "k" in token:
                token_type = token["k"]
                self._dispatch_token(token, start_pos, end_pos, token_type)

    def _dispatch_token(self, token, start_pos, end_pos, token_type):
        if token_type in self.token_keys:
            method_name = self.token_keys[token_type][2]
            method = getattr(self, method_name)
            is_valid, result, sub_tokens = method(token)
            self.last_result = (is_valid, result, token)
            if is_valid:
                self.parse_ok = is_valid
            else:
                self.parse_ok = False
        else:
            self.parse_ok = False
            log_msg(f"No handler for token: {token}")

    def _extract_job_node_and_summary(self, text):
        match = JOB_PATTERN.match(text)
        if match:
            number = len(match.group(1)) // 2
            summary = match.group(2).rstrip()
            content = match.group(3)
            if content:
                # the leading space is needed for parsing
                content = f" {content}"
            return number, summary, content
        return None, text  # If no match, return None for number and the entire string

    @classmethod
    def from_dict(cls, data: dict):
        # Reconstruct the entry string from tokens
        entry_str = " ".join(t["token"] for t in json.loads(data["tokens"]))
        return cls(entry_str)

    @classmethod
    def from_item(cls, data: dict):
        # Reconstruct the entry string from tokens
        entry_str = " ".join(t["token"] for t in json.loads(data["tokens"]))
        return cls(entry_str)

    @classmethod
    def do_itemtype(cls, token):
        # Process subject token
        if "t" in token and token["t"] == "itemtype":
            return True, token["token"].strip(), []
        else:
            return False, "itemtype cannot be empty", []

    @classmethod
    def do_subject(cls, token):
        # Process subject token
        if "t" in token and token["t"] == "subject":
            return True, token["token"].strip(), []
        else:
            return False, "subject cannot be empty", []

    @classmethod
    def do_job_s(cls, arg: str):
        """ """
        if not arg:
            return False, f"time period {arg}"
        ok, res = timedelta_str_to_seconds(arg)
        return ok, res

    def do_priority(self, token):
        # Process datetime token
        x = re.sub("^@. ", "", token["token"].strip()).lower()
        try:
            y = int(x)
            if 1 <= y <= 5:
                self.priority = y
                # print(f"set {self.priority = }")
                return True, y, []
            else:
                return False, x, []
        except ValueError:
            print(f"failed priority {token = }, {x = }")
            return False, x, []

    def do_notice(self, token):
        # Process datetime token
        notice = re.sub("^[@&]. ", "", token["token"].strip()).lower()
        # notice = re.sub("^@. ", "", token["token"].strip()).lower()

        ok, notice_obj = timedelta_str_to_seconds(notice)
        if ok:
            self.notice = notice
            return True, notice_obj, []
        else:
            log_msg(f"failed to set self.notice: {notice = }, {notice_obj = }")
            return False, notice_obj, []

    def do_e(self, token: dict):
        # Process datetime token
        raw = token["token"][2:].strip()
        if not raw:
            return (
                False,
                f"{self.token_keys['e'][0]} {self.token_keys['e'][1]}",
                [],
            )
            # return False, "Missing @s value", []
        extent = re.sub("^[@&]. ", "", token["token"].strip()).lower()
        ok, extent_obj = timedelta_str_to_seconds(extent)
        if ok:
            self.extent = td_to_td_str(extent_obj)
            return True, f"{self.token_keys['e'][0]} {self.extent}", []
            # return True, extent_obj, []
        else:
            return False, extent_obj, []

    def do_wrap(self, token):
        _w = re.sub("^@. ", "", token["token"].strip()).lower()
        _w_parts = [x.strip() for x in _w.split(",")]
        if len(_w_parts) != 2:
            return False, f"Invalid: {_w_parts}", []
        wrap = []
        msgs = []

        ok, _b_obj = timedelta_str_to_seconds(_w_parts[0])
        if ok:
            wrap.append(_b_obj)
        else:
            msgs.append(f"Error parsing before {_b_obj}")

        ok, _a_obj = timedelta_str_to_seconds(_w_parts[1])
        if ok:
            wrap.append(_a_obj)
        else:
            msgs.append(f"Error parsing after {_a_obj}")
        if msgs:
            return False, ", ".join(msgs), []
        self.wrap = wrap
        return True, wrap, []

    def do_alert(self, token):
        """
        Process an alert string, validate it and return a corresponding string
        """

        alert = token["token"][2:].strip()

        parts = [x.strip() for x in alert.split(":")]
        if len(parts) != 2:
            return False, f"Invalid alert format: {alert}", []
        timedeltas, commands = parts
        secs = []
        tds = []
        cmds = []
        probs = []
        issues = []
        res = ""
        ok = True
        for cmd in [x.strip() for x in commands.split(",")]:
            if is_lowercase_letter(cmd):
                cmds.append(cmd)
            else:
                ok = False
                probs.append(f"  Invalid command: {cmd}")
        for td in [x.strip() for x in timedeltas.split(",")]:
            ok, td_seconds = timedelta_str_to_seconds(td)
            if ok:
                secs.append(str(td_seconds))
                tds.append(td)
            else:
                ok = False
                probs.append(f"  Invalid timedelta: {td}")
        if ok:
            res = f"{', '.join(tds)}: {', '.join(cmds)}"
            self.alerts.append(res)
        else:
            issues.append("; ".join(probs))
        if issues:
            return False, "\n".join(issues), []
        return True, res, []

    def do_requires(self, token):
        """
        Process a requires string for a job.
        Format:
            N
            or
            N:M[,K...]
        where N is the primary id, and M,K,... are dependency ids.

        Returns:
            (True, "", primary, dependencies) on success
            (False, "error message", None, None) on failure
        """
        requires = token["token"][2:].strip()

        try:
            if ":" in requires:
                primary_str, deps_str = requires.split(":", 1)
                primary = int(primary_str.strip())
                dependencies = []
                for part in deps_str.split(","):
                    part = part.strip()
                    if part == "":
                        continue
                    try:
                        dependencies.append(int(part))
                    except ValueError:
                        return (
                            False,
                            f"Invalid dependency value: '{part}' in token '{requires}'",
                            [],
                        )
            else:
                primary = int(requires.strip())
                dependencies = []
        except ValueError as e:
            return (
                False,
                f"Invalid requires token: '{requires}' ({e})",
                [],
            )

        return True, primary, dependencies

    def do_d(self, token):
        raw = token["token"][2:].strip()
        if not raw:
            return (
                False,
                f"{self.token_keys['d'][0]} {self.token_keys['d'][1]}",
                [],
            )
        self.description = raw
        return True, raw, []

    def do_nothing(self, token):
        return True, "passed", []

    @classmethod
    def do_paragraph(cls, arg):
        """
        Remove trailing whitespace.
        """
        obj = None
        rep = arg
        para = [x.rstrip() for x in arg.split("\n")]
        if para:
            all_ok = True
            obj_lst = []
            rep_lst = []
            for p in para:
                try:
                    res = str(p)
                    obj_lst.append(res)
                    rep_lst.append(res)
                except Exception as e:
                    log_msg(f"error: {e}")
                    all_ok = False
                    rep_lst.append(f"~{arg}~")

            obj = "\n".join(obj_lst) if all_ok else False
            rep = "\n".join(rep_lst)
        if obj:
            return True, obj
        else:
            return False, rep

    @classmethod
    def do_stringlist(cls, args: List[str]):
        """
        >>> do_stringlist('')
        (None, '')
        >>> do_stringlist('red')
        (['red'], 'red')
        >>> do_stringlist('red,  green, blue')
        (['red', 'green', 'blue'], 'red, green, blue')
        >>> do_stringlist('Joe Smith <js2@whatever.com>')
        (['Joe Smith <js2@whatever.com>'], 'Joe Smith <js2@whatever.com>')
        """
        obj = None
        rep = args
        if args:
            args = [x.strip() for x in args.split(",")]
            all_ok = True
            obj_lst = []
            rep_lst = []
            for arg in args:
                try:
                    res = str(arg)
                    obj_lst.append(res)
                    rep_lst.append(res)
                except Exception as e:
                    log_msg(f"error: {e}")
                    all_ok = False
                    rep_lst.append(f"~{arg}~")
            obj = obj_lst if all_ok else None
            rep = ", ".join(rep_lst)
        return obj, rep

    def do_string(self, token):
        obj = rep = token["token"][2:].strip()
        return obj, rep, []

    def do_timezone(self, token: dict):
        """Handle @z timezone declaration in user input."""
        tz_str = token["token"][2:].strip()
        # print(f"do_timezone: {tz_str = }")
        if tz_str.lower() in {"none", "naive"}:
            self.timezone = None
            self.tz_str = "none"
            return True, None, []
        try:
            self.timezone = ZoneInfo(tz_str)
            self.tz_str = self.timezone.key
            return True, self.timezone, []
        except Exception as e:
            log_msg(f"error: {e}")
            self.timezone = None
            self.tz_str = ""
            return False, f"Invalid timezone: '{tz_str}'", []

    def do_r(self, token):
        """
        Handle an @r ... group. `token` may be a token dict or the raw token string.
        This only validates / records RRULE components; RDATE/EXDATE are added later
        by finalize_rruleset().
        Returns (ok: bool, message: str, extras: list).
        """

        # Normalize input to raw text
        tok_text = token.get("token") if isinstance(token, dict) else str(token)

        # Find the matching @r group (scan all groups first)
        group = None
        r_groups = list(self.collect_grouped_tokens({"r"}))
        for g in r_groups:
            if g and g[0].get("token") == tok_text:
                group = g
                break

        # Only after scanning all groups decide if it's missing
        if group is None:
            msg = (False, f"No matching @r group found for token: {tok_text}", [])
            self.messages.append(msg)
            return msg

        # Parse frequency from the anchor token "@r d|w|m|y"
        anchor = group[0]
        parts = anchor["token"].split(maxsplit=1)
        if len(parts) < 2:
            msg = (False, f"Missing rrule frequency: {tok_text}", [])
            self.messages.append(msg)
            return msg

        freq_code = parts[1].strip().lower()
        if freq_code not in self.freq_map:
            keys = ", ".join(f"{k} ({v})" for k, v in self.freq_map.items())
            msg = (
                False,
                f"'{freq_code}' is not a supported frequency. Choose from:\n   {keys}",
                [],
            )
            self.messages.append(msg)
            return msg

        # Record a normalized RRULE "component" for your builder
        # (Keep this lightweight. Don't emit RDATE/EXDATE here.)
        self.rrule_tokens.append(
            {"token": f"{self.freq_map[freq_code]}", "t": "&", "k": "FREQ"}
        )

        # Parse following &-tokens in this @r group (e.g., &i 3, &c 10, &u 20250101, &m..., &w..., &d...)
        for t in group[1:]:
            tstr = t.get("token", "")
            try:
                key, value = tstr[1:].split(maxsplit=1)  # strip leading '&'
                key = key.upper().strip()
                value = value.strip()
            except Exception as e:
                log_msg(f"error: {e}")
                continue

            self.rrule_tokens.append({"token": tstr, "t": "&", "k": key, "v": value})

        return (True, "", [])

    def do_s(self, token: dict):
        """
        Parse @s, honoring optional trailing 'z <tz>' directive inside the value.
        Updates self.dtstart_str and self.rdstart_str to seed recurrence.
        """
        try:
            raw = token["token"][2:].strip()
            if not raw:
                return (
                    False,
                    f"{self.token_keys['s'][0]} {self.token_keys['s'][1]}",
                    [],
                )
                # return False, "Missing @s value", []

            obj, kind, tz_used = self.parse_user_dt_for_s(raw)
            if kind == "error":
                return False, tz_used or f"Invalid @s value: {raw}", []

            userfmt = self.fmt_user(obj)
            verbosefmt = self.fmt_verbose(obj)

            if kind == "date":
                compact = self._serialize_date(obj)
                self.s_kind = "date"
                self.s_tz = None
            elif kind == "naive":
                compact = self._serialize_naive_dt(obj)
                self.s_kind = "naive"
                self.s_tz = None
            else:  # aware
                compact = self._serialize_aware_dt(obj, tz_used)
                self.s_kind = "aware"
                self.s_tz = tz_used  # '' == local

            # compact = self._serialize_date_or_datetime(obj)

            self.dtstart = compact
            self.dtstart_str = (
                f"DTSTART:{compact}"
                if kind != "date"
                else f"DTSTART;VALUE=DATE:{compact}"
            )
            self.rdstart_str = f"RDATE:{compact}"
            token["token"] = f"@s {userfmt}"
            retval = userfmt if self.final else verbosefmt
            self.has_s = True

            return True, retval, []

        except Exception as e:
            return False, f"Invalid @s value: {e}", []

    def do_b(self, token: dict) -> Tuple[bool, str, List[str]]:
        """
        Live resolver for '@b Leaf/Parent/.../Root' (leaf→root, '/' only).
        - If matches exist: preview; auto-lock when unique/exact.
        - If no matches: show per-segment status, e.g. 'Churchill (new)/quotations/library'.
        """
        path = token["token"][2:].strip()  # strip '@b'
        rev_dict = self.get_name_to_binpath()  # {leaf_lower: "Leaf/.../Root"}
        path = token["token"][2:].strip()  # after '@b'
        parts = [p.strip() for p in path.split("/") if p.strip()]

        # Batch/final or no controller dict → one-shot resolve
        if self.final or not self.get_name_to_binpath():
            if not parts:
                return False, "Missing bin path after @b", []
            norm = "/".join(parts)  # Leaf/Parent/.../Root
            token["token"] = f"@b {parts[0]}"  # keep prefix; no decoration
            if not token.get("_b_resolved"):  # append ONCE (batch runs once anyway)
                self.bin_paths.append(parts)  # store Leaf→…→Root parts
                token["_b_resolved"] = True
            return True, token["token"], []

        # Fallback for batch/final or if controller not wired
        if not rev_dict:
            if not path:
                return False, "Missing bin path after @b", []
            parts = [p.strip() for p in (path or "").split("/") if p.strip()]
            if not parts:
                return False, "Missing bin path after @b", []
            # keep full token; don't truncate to parts[0]
            token["token"] = f"@b {parts[0]}"
            # don't append to bin_paths here; do it on save
            return True, token["token"], []

        raw = token.get("token", "")
        frag = raw[2:].strip() if raw.startswith("@b") else raw

        if not frag:
            msg = "@b Type bin as Leaf/Parent/…"
            token["token"] = msg
            token.pop("_b_resolved", None)
            token.pop("_b_new", None)
            return True, msg, []

        paths = list(rev_dict.values())  # existing reversed paths
        matches = _ordered_prefix_matches(paths, frag, limit=24)

        if matches:
            nf = _norm(frag)
            exact = next((m for m in matches if _norm(m) == nf), None)
            if exact or len(matches) == 1:
                resolved = exact or matches[0]
                token["token"] = f"@b {resolved}"
                token["_b_new"] = False
                token["_b_resolved"] = True
                return True, token["token"], []
            # ambiguous → preview + suggestions
            lcp = _lcp(matches)
            preview = lcp if lcp and len(lcp) >= len(frag) else matches[0]
            token["token"] = f"@b {preview}"
            token.pop("_b_resolved", None)
            token["_b_new"] = False
            return True, token["token"], matches

        # ---------- No matches → per-segment feedback ----------
        parts = [p.strip() for p in frag.split("/") if p.strip()]
        leaf_to_path = {k.lower(): v for k, v in rev_dict.items()}
        leafnames = set(leaf_to_path.keys())

        # Build a set of existing leaf-first prefixes for quick “does any path start with X?”
        # Example: for 'quotations/library/root' we add 'quotations', 'quotations/library', ...
        prefix_set = set()
        for p in paths:
            toks = p.split("/")
            for i in range(1, len(toks) + 1):
                prefix_set.add("/".join(toks[:i]).lower())

        decorated: list[str] = []
        for i, seg in enumerate(parts):
            seg_l = seg.lower()
            if i == 0:
                # Leaf segment: does *any* existing path start with this leaf?
                starts = f"{seg_l}"
                if starts not in prefix_set and not any(
                    s.startswith(starts + "/") for s in prefix_set
                ):
                    decorated.append(f"{seg} (new)")
                else:
                    decorated.append(seg)
            else:
                # Parent segments: if this segment is an existing leaf name, show its known ancestry
                if seg_l in leafnames:
                    known = leaf_to_path[seg_l].split(
                        "/"
                    )  # e.g., ['quotations','library','root']
                    # drop the leaf itself (known[0]) since we already have 'seg', and (optionally) drop 'root'
                    tail = [x for x in known[1:] if x.lower() != "root"]
                    if tail:
                        decorated.append("/".join([seg] + tail))
                    else:
                        decorated.append(seg)
                else:
                    # Not an exact leaf; if no prefixes suggest it, mark (new)
                    any_prefix = any(k.startswith(seg_l) for k in leafnames)
                    decorated.append(seg if any_prefix else f"{seg} (new)")

        pretty = "@b " + "/".join(decorated)
        # Keep the actual token clean (no "(new)"); only the feedback string is decorated
        token["token"] = f"@b {parts[0]}"
        token.pop("_b_resolved", None)
        token["_b_new"] = True
        return True, pretty, []

    def _looks_like_url(self, s: str) -> bool:
        """Heuristic: valid scheme and netloc."""
        try:
            parsed = urlparse(s)
            return bool(parsed.scheme and parsed.netloc)
        except Exception:
            return False

    def _looks_like_path(self, s: str) -> bool:
        """
        Heuristic for 'valid' path.
        Here we allow non-existent paths (so you can create them later),
        but you could tighten this to Path(...).exists() if you prefer.
        """
        s = (s or "").strip()
        if not s:
            return False
        # Absolute or relative path-ish
        p = Path(s).expanduser()
        # Very loose: must have at least one path component
        return bool(p.parts)

    def do_g(self, token: dict) -> tuple[bool, str, list]:
        """
        @g: goto – must be a URL or file path.

        Returns:
          (True,  "OpenWithDefault", [])
          (False, "<error message>", [])
        """
        raw = (token.get("token") or "").strip()

        # Strip the '@g' prefix if it's there
        # e.g. "@g /path/to/file" or "@ghttps://example.com"
        if raw.startswith("@g"):
            value = raw[2:].strip()
        else:
            # Fallback: take everything after the first space
            parts = raw.split(None, 1)
            value = parts[1].strip() if len(parts) > 1 else ""

        if not value:
            return False, "@g expects a URL or file path, but none was given.", []

        if not (self._looks_like_url(value) or self._looks_like_path(value)):
            return False, f"@g expects a URL or file path, got {value!r}.", []

        # Optional: stash the parsed value for later convenience
        token["goto"] = value

        # On success, your design: return special command name
        return True, "OpenWithDefault", []

    def do_job(self, token):
        # Process journal token
        node, summary, tokens_remaining = self._extract_job_node_and_summary(
            token["token"]
        )
        job_params = {"~": summary}
        job_params["node"] = node

        return True, job_params, []

    @classmethod
    def do_weekdays(cls, wkd_str: str):
        """
        Converts a string representation of weekdays into a list of rrule objects.
        """
        print(" ### do_weekdays ### ")
        wkd_str = wkd_str.upper()
        wkd_regex = r"(?<![\w-])([+-][1-4])?(MO|TU|WE|TH|FR|SA|SU)(?!\w)"
        matches = re.findall(wkd_regex, wkd_str)
        _ = [f"{x[0]}{x[1]}" for x in matches]
        all = [x.strip() for x in wkd_str.split(",")]
        bad = [x for x in all if x not in _]
        problem_str = ""
        problems = []
        for x in bad:
            probs = []
            i, w = cls.split_int_str(x)
            if i is not None:
                abs_i = abs(int(i))
                if abs_i > 4 or abs_i == 0:
                    probs.append(f"{i} must be between -4 and -1 or between +1 and +4")
                elif not (i.startswith("+") or i.startswith("-")):
                    probs.append(f"{i} must begin with '+' or '-'")
            w = w.strip()
            if not w:
                probs.append(f"Missing weekday abbreviation from {cls.wkd_str}")
            elif w not in cls.wkd_list:
                probs.append(f"{w} must be a weekday abbreviation from {cls.wkd_str}")
            if probs:
                problems.append(f"In '{x}': {', '.join(probs)}")
            else:
                # undiagnosed problem
                problems.append(f"{x} is invalid")
        if problems:
            probs = []
            probs.append(", ".join(bad))
            probs.append("\n", join(problems))
            probs_str = "\n".join(probs)
            problem_str = f"Problem entries: {probs_str}"
        good = []
        for x in matches:
            s = f"{x[0]}{x[1]}" if x[0] else f"{x[1]}"
            good.append(s)
        good_str = ",".join(good)
        if problem_str:
            return False, f"{problem_str}\n{good_str}"
        else:
            return True, f"BYDAY={good_str}"

    def do_interval(cls, arg: int):
        """
        Process an integer interval as the rrule frequency.
        """
        try:
            arg = int(arg)
        except Exception:
            return False, "interval must be a postive integer"
        else:
            if arg < 1:
                return False, "interval must be a postive integer"
        return True, f"INTERVAL={arg}"

    @classmethod
    def do_months(cls, arg):
        """
        Process a comma separated list of integer month numbers from 1, 2, ..., 12
        """
        print(" ### do_months ### ")
        monthsstr = (
            "months: a comma separated list of integer month numbers from 1, 2, ..., 12"
        )
        if arg:
            args = arg.split(",")
            ok, res = cls.integer_list(args, 0, 12, False, "")
            if ok:
                obj = res
                rep = f"{arg}"
            else:
                obj = None
                rep = f"invalid months: {res}. Required for {monthsstr}"
        else:
            obj = None
            rep = monthsstr
        if obj is None:
            return False, rep

        return True, f"BYMONTH={rep}"

    @classmethod
    def do_count(cls, arg):
        """
        Process an integer count for rrule
        """
        print(" ### do_count ### ")
        countstr = "count: an integer count for rrule, 1, 2, ... "
        if arg:
            args = arg.strip()
            ok, res = cls.integer(args, 1, None, False, "")
            if ok:
                obj = res
                rep = f"{arg}"
            else:
                obj = None
                rep = f"invalid count: {res}. Required for {countstr}"
        else:
            obj = None
            rep = countstr
        if obj is None:
            return False, rep

        return True, f"COUNT={rep}"

    @classmethod
    def do_monthdays(cls, arg):
        """
        Process a comma separated list of integer month day numbers from 1, 2, ..., 31
        """
        print(" ### do_monthdays ### ")
        monthdaysstr = "monthdays: a comma separated list of integer month day numbers from 1, 2, ..., 31"
        if arg:
            args = arg.split(",")
            ok, res = cls.integer_list(args, 1, 31, False, "")
            if ok:
                obj = res
                rep = f"{arg}"
            else:
                obj = None
                rep = f"invalid monthdays: {res}. Required for {monthdaysstr}"
        else:
            obj = None
            rep = monthdaysstr
        if obj is None:
            return False, rep

        return True, f"BYMONTH={rep}"

    @classmethod
    def do_hours(cls, arg):
        """
        Process a comma separated list of integer hour numbers from 0, 1, ..., 23
        """
        print(" ### do_hours ### ")
        hoursstr = (
            "hours: a comma separated list of integer hour numbers from 0, 1, ..., 23"
        )
        if arg:
            args = arg.split(",")
            ok, res = cls.integer_list(args, 0, 23, False, "")
            if ok:
                obj = res
                rep = f"{arg}"
            else:
                obj = None
                rep = f"invalid hours: {res}. Required for {hoursstr}"
        else:
            obj = None
            rep = hoursstr
        if obj is None:
            return False, rep

        return True, f"BYHOUR={rep}"

    @classmethod
    def do_minutes(cls, arg):
        """
        Process a comma separated list of integer minute numbers from 0, 2, ..., 59
        """
        print(" ### do_minutes ### ")
        minutesstr = "minutes: a comma separated list of integer minute numbers from 0, 2, ..., 59"
        if arg:
            args = arg.split(",")
            ok, res = cls.integer_list(args, 0, 59, False, "")
            if ok:
                obj = res
                rep = f"{arg}"
            else:
                obj = None
                rep = f"invalid minutes: {res}. Required for {minutesstr}"
        else:
            obj = None
            rep = minutesstr
        if obj is None:
            return False, rep

        return True, f"BYMINUTE={rep}"

    @classmethod
    def do_two_periods(cls, arg: List[str]) -> str:
        return True, "not implemented", []

    def do_mask(self, token: dict) -> tuple[bool, str, list]:
        """
        Handle @m / ~m tokens. Validation ensures a value is provided;
        actual encoding happens during finalize_record().
        """
        token_text = token.get("token").strip() or ""
        # parts = token_text.split(maxsplit=1)
        # if len(parts) < 2 or not parts[1].strip():
        if not token_text:
            return False, "@m requires a value", []
        return True, token_text, []

    def integer(cls, arg, min, max, zero, typ=None):
        """
        :param arg: integer
        :param min: minimum allowed or None
        :param max: maximum allowed or None
        :param zero: zero not allowed if False
        :param typ: label for message
        :return: (True, integer) or (False, message)
        >>> integer(-2, -10, 8, False, 'integer_test')
        (True, -2)
        >>> integer(-2, 0, 8, False, 'integer_test')
        (False, 'integer_test: -2 is less than the allowed minimum')
        """
        msg = ""
        try:
            arg = int(arg)
        except Exception:
            if typ:
                return False, "{}: {}".format(typ, arg)
            else:
                return False, arg
        if min is not None and arg < min:
            msg = "{} is less than the allowed minimum".format(arg)
        elif max is not None and arg > max:
            msg = "{} is greater than the allowed maximum".format(arg)
        elif not zero and arg == 0:
            msg = "0 is not allowed"
        if msg:
            if typ:
                return False, "{}: {}".format(typ, msg)
            else:
                return False, msg
        else:
            return True, arg

    @classmethod
    def integer_list(cls, arg, min, max, zero, typ=None):
        """
        :param arg: comma separated list of integers
        :param min: minimum allowed or None
        :param max: maximum allowed or None
        :param zero: zero not allowed if False
        :param typ: label for message
        :return: (True, list of integers) or (False, messages)
        >>> integer_list([-13, -10, 0, "2", 27], -12, +20, True, 'integer_list test')
        (False, 'integer_list test: -13 is less than the allowed minimum; 27 is greater than the allowed maximum')
        >>> integer_list([0, 1, 2, 3, 4], 1, 3, True, "integer_list test")
        (False, 'integer_list test: 0 is less than the allowed minimum; 4 is greater than the allowed maximum')
        >>> integer_list("-1, 1, two, 3", None, None, True, "integer_list test")
        (False, 'integer_list test: -1, 1, two, 3')
        >>> integer_list([1, "2", 3], None, None, True, "integer_list test")
        (True, [1, 2, 3])
        """
        if type(arg) == str:
            try:
                args = [int(x) for x in arg.split(",")]
            except Exception:
                if typ:
                    return False, "{}: {}".format(typ, arg)
                else:
                    return False, arg
        elif type(arg) == list:
            try:
                args = [int(x) for x in arg]
            except Exception:
                if typ:
                    return False, "{}: {}".format(typ, arg)
                else:
                    return False, arg
        elif type(arg) == int:
            args = [arg]
        msg = []
        ret = []
        for arg in args:
            ok, res = cls.integer(arg, min, max, zero, None)
            if ok:
                ret.append(res)
            else:
                msg.append(res)
        if msg:
            if typ:
                return False, "{}: {}".format(typ, "; ".join(msg))
            else:
                return False, "; ".join(msg)
        else:
            return True, ret

    @classmethod
    def split_int_str(cls, s):
        match = re.match(r"^([+-]?\d*)(.{1,})$", s)
        if match:
            integer_part = match.group(1)
            string_part = match.group(2)
            # Convert integer_part to an integer if it's not empty, otherwise None
            integer_part = integer_part if integer_part else None
            string_part = string_part if string_part else None
            return integer_part, string_part
        return None, None  # Default case if no match is found

    # ---- helpers you implement with your existing token machinery ----

    def _get_first_two_occurrences(self) -> tuple[datetime | None, datetime | None]:
        """
        Return (first, second) occurrences from rruleset, which is the
        ultimate source of truth for this item's schedule.
        Always return the first two in sequence, even if they’re already past.
        """
        if not (self.rruleset or "").strip():
            return None, None

        try:
            rs = rrulestr(self.rruleset)
            it = iter(rs)
            first = next(it, None)
            second = next(it, None)
            return first, second
        except Exception as e:
            return None, None

    #
    #     prefix = "~" if learn else ""
    #     new_token_text = f"@o {prefix}{td_str} "
    #
    #     tok = next(
    #         (
    #             t
    #             for t in self.relative_tokens
    #             if t.get("t") == "@" and t.get("k") == "o"
    #         ),
    #         None,
    #     )
    #     if tok:
    #         tok["token"] = new_token_text
    #     else:
    #         self.relative_tokens.append({"token": new_token_text, "t": "@", "k": "o"})
    #     # keep original string field too, if you use it elsewhere
    #     self.over = f"{prefix}{td_str}"

    def _smooth_interval(self, old: timedelta, new: timedelta) -> timedelta:
        """
        (w*old + new)/(w+1), then:
        - if averaged interval > 1 day → round to whole hours (days+hours effectively)
        - else → round to whole minutes
        """
        hour_seconds = 60 * 60
        day_seconds = 24 * hour_seconds
        week_seconds = 7 * day_seconds

        # weighted average as seconds
        total = old * self.history_weight + new
        secs = total.total_seconds() / (self.history_weight + 1)

        if secs > week_seconds:
            # round to integer hours (in seconds)
            rounded = round(secs / day_seconds) * day_seconds
        elif secs > day_seconds:
            # round to integer hours (in seconds)
            rounded = round(secs / hour_seconds) * hour_seconds
        else:
            # round to integer minutes (in seconds)
            rounded = round(secs / 60) * 60

        return timedelta(seconds=rounded)

    def _is_rdate_only(self) -> bool:
        """True if rruleset is only RDATE(+optional EXDATE), i.e. no RRULE."""
        if not self.rruleset:
            return False
        lines = [ln.strip() for ln in self.rruleset.splitlines() if ln.strip()]
        if not lines:
            return False
        # No RRULE anywhere
        if any(ln.upper().startswith("RRULE") for ln in lines):
            return False
        # At least one RDATE (either plain RDATE:... or RDATE;VALUE=DATE:...)
        has_rdate = any(ln.upper().startswith("RDATE") for ln in lines)
        return has_rdate

    def _drop_first_rdate(self, first_dt: datetime) -> bool:
        """
        Mark the first RDATE occurrence as completed by appending an @- EXDATE token,
        then re-parse so rruleset reflects it. Return True if more RDATEs remain.
        """
        # 1) append @- token in the same textual style your parser already understands
        if first_dt.hour == 0 and first_dt.minute == 0 and first_dt.second == 0:
            ex_str = first_dt.strftime("%Y%m%d")  # date-only
        else:
            ex_str = first_dt.strftime("%Y%m%dT%H%M")  # datetime

        self.relative_tokens.append({"token": f"@- {ex_str} ", "t": "@", "k": "-"})

        # 2) re-parse to regenerate rruleset/derived fields consistently
        self._reparse_from_tokens()

        # 3) decide if anything remains (any RDATE not excluded)
        #    Quick check: do we still have any @+ token with a date/datetime != ex_str?
        remaining = False
        for tok in self.relative_tokens:
            if tok.get("t") == "@" and tok.get("k") == "+":
                body = tok["token"][2:].strip()
                for piece in (p.strip() for p in body.split(",") if p.strip()):
                    if piece != ex_str:
                        remaining = True
                        break
            if remaining:
                break

        return remaining

    def _has_rrule(self) -> bool:
        """True if rruleset contains an RRULE line."""
        if not self.rruleset:
            return False
        return any(
            ln.strip().upper().startswith("RRULE") for ln in self.rruleset.splitlines()
        )

    def _advance_dtstart_and_decrement_count(self, new_dtstart: datetime) -> None:
        """Advance @s to `new_dtstart` and decrement any &c COUNT token."""
        formatted_start = self.fmt_user(new_dtstart)
        for tok in self.relative_tokens:
            if tok.get("t") == "@" and tok.get("k") == "s":
                tok["token"] = f"@s {formatted_start} "
                break
        else:
            self.relative_tokens.append(
                {
                    "token": f"@s {formatted_start} ",
                    "t": "@",
                    "k": "s",
                }
            )

        self._decrement_count_token()
        self._reparse_from_tokens()

    def _decrement_count_token(self) -> None:
        """Reduce the first &c token by one (removing it when it reaches zero)."""
        for tok in list(self.relative_tokens):
            if tok.get("t") == "&" and tok.get("k") == "c":
                try:
                    parts = tok["token"].split()
                    if len(parts) >= 2 and parts[0] == "&c":
                        cnt = int(parts[1]) - 1
                        if cnt > 0:
                            tok["token"] = f"&c {cnt}"
                        else:
                            self.relative_tokens.remove(tok)
                except Exception:
                    pass
                break

    def _reparse_from_tokens(self) -> None:
        """Rebuild derived scheduling fields after direct token edits."""
        self.rebuild_from_tokens(resolve_relative=True)

    def _clear_schedule(self) -> None:
        """
        Clear *all* scheduling: @s, @r and its &-params, @+, @- and rruleset.
        Leaves non-scheduling tokens (subject, etc.) intact.
        """
        new_tokens = []
        dropping_group_r = False

        for tok in self.relative_tokens:
            t = tok.get("t")
            k = tok.get("k")

            # drop @s
            if t == "@" and k == "s":
                continue

            # drop @+ / @-
            if t == "@" and k in {"+", "-"}:
                continue

            # drop @r and all following & (r-params) until next non-& token
            if t == "@" and k == "r":
                dropping_group_r = True
                continue

            if dropping_group_r:
                if t == "&":  # r-parameter
                    continue
                else:
                    dropping_group_r = False
                    # fall through to append this non-& token

            new_tokens.append(tok)

        self.relative_tokens = new_tokens
        self.rruleset = ""  # remove compiled schedule string

    def do_plus(self, token: dict):
        """
        Process an RDATE token, e.g., "@+ 2024-07-03 14:00, 2024-08-05 09:00".

        Also accepts relative-like input (e.g. "11a tue") which is parsed
        relative to the current anchor, but when self.final is True we
        rewrite the token to store the *expanded* canonical forms so that
        future parses are stable.
        """
        try:
            # Remove the "@+" prefix and extra whitespace
            token_body = token["token"][2:].strip()

            # Split on commas to get individual date strings
            dt_strs = [s.strip() for s in token_body.split(",") if s.strip()]

            # Process each entry
            rdates: list[str] = []
            udates: list[str] = []

            for dt_str in dt_strs:
                if self.s_kind == "aware":
                    dt = parse(dt_str, self.s_tz)
                    dt_fmt = _fmt_utc_Z(dt)
                elif self.s_kind == "naive":
                    dt = parse(dt_str)
                    dt_fmt = _fmt_naive(dt)
                else:
                    dt = parse(dt_str)
                    dt_fmt = _fmt_date(dt)

                if dt_fmt not in rdates:
                    rdates.append(dt_fmt)
                    udates.append(self.fmt_user(dt))

            # Append to any existing RDATE start string
            if self.rdstart_str:
                self.rdstart_str = f"{self.rdstart_str},{','.join(rdates)}"
                self.rruleset_dict["START_RDATES"] = self.rdstart_str
            else:
                self.rdstart_str = ",".join(rdates)
                self.rruleset_dict["RDATE"] = self.rdstart_str

            self.rdates = rdates
            self.token_map["+"] = ", ".join(udates)

            # 🔸 CRITICAL: when final, freeze the token to the canonical absolute forms
            if getattr(self, "final", False) and rdates:
                token["token"] = f"@+ {', '.join(rdates)}"

            # Prepend RDATE in finalize_rruleset after possible insertion of DTSTART
            return True, rdates, []
        except Exception as e:
            return False, f"Invalid @+ value: {e}", []

    def do_minus(self, token: dict):
        """
        @- … : explicit exclusion dates
        - Maintain a de-duplicated list of compact dates in self.exdates.
        - finalize_rruleset() will emit EXDATE using this list in either path.

        When self.final is True, the token text is rewritten to use the
        expanded canonical forms so that future parses are stable.
        """
        try:
            token_body = token["token"][2:].strip()
            dt_strs = [s.strip() for s in token_body.split(",") if s.strip()]

            if not hasattr(self, "exdates") or self.exdates is None:
                self.exdates = []

            new_ex: list[str] = []
            udates: list[str] = []

            for dt_str in dt_strs:
                if self.s_kind == "aware":
                    dt = parse(dt_str, self.s_tz)
                    dt_fmt = _fmt_utc_Z(dt)
                elif self.s_kind == "naive":
                    dt = parse(dt_str)
                    dt_fmt = _fmt_naive(dt)
                else:
                    dt = parse(dt_str)
                    dt_fmt = _fmt_date(dt)

                if dt_fmt not in self.exdates and dt_fmt not in new_ex:
                    new_ex.append(dt_fmt)
                    udates.append(self.fmt_user(dt))

            self.exdates.extend(new_ex)
            self.token_map["-"] = ", ".join(udates)
            # convenience string if you ever need it
            self.exdate_str = ",".join(self.exdates) if self.exdates else ""

            # 🔸 CRITICAL: when final, freeze the token to the canonical absolute forms
            if getattr(self, "final", False) and new_ex:
                token["token"] = f"@- {', '.join(new_ex)}"

            return True, new_ex, []
        except Exception as e:
            return False, f"Invalid @- value: {e}", []

    def collect_rruleset_tokens(self):
        """Return the list of relative tokens used for building the rruleset."""
        rruleset_tokens = []
        found_rrule = False

        for token in self.relative_tokens:
            if not found_rrule:
                if token["t"] == "@" and token["k"] == "r":
                    found_rrule = True
                    rruleset_tokens.append(token)  # relative token
            else:
                if token["t"] == "&":
                    rruleset_tokens.append(token)  # relative token
                else:
                    break  # stop collecting on first non-& after @r

        return rruleset_tokens

    def finalize_rruleset(self) -> str:
        """
        Build an rruleset string using self.relative_tokens, self.dtstart_str and self.rdstart_str.
        Emits:
        - DTSTART (if rrule is present)
        - RRULE:...
        - RDATE:...   (from your rdstart_str or rdate_str)
        - EXDATE:...  (if you track it)
        """
        rrule_tokens = self.collect_rruleset_tokens()
        if not self.dtstart:
            return ""
        # map @r y/m/w/d → RRULE:FREQ=...
        freq_map = {"y": "YEARLY", "m": "MONTHLY", "w": "WEEKLY", "d": "DAILY"}
        parts = rrule_tokens[0]["token"].split(maxsplit=1)
        freq_abbr = parts[1].strip() if len(parts) > 1 else ""
        freq = freq_map.get(freq_abbr.lower())
        if not freq:
            return ""

        rrule_components = {"FREQ": freq}

        # &-tokens
        for tok in rrule_tokens[1:]:
            token_str = tok["token"]
            try:
                key, value = token_str[1:].split(maxsplit=1)  # strip leading '&'
            except Exception:
                key = tok.get("k", "")
                value = tok.get("v", "")
            # if not (key and value):
            #     continue
            key = key.strip()
            value = value.strip()
            if key == "u":
                ok, res = local_dtstr_to_utc(value)
                value = res if ok else ""
            elif ", " in value:
                value = ",".join(value.split(", "))
            component = self.key_to_param.get(key, None)
            if component:
                rrule_components[component] = value

        rrule_line = "RRULE:" + ";".join(
            f"{k}={v}" for k, v in rrule_components.items()
        )

        # Assemble lines safely
        lines: list[str] = []

        dtstart_str = getattr(self, "dtstart_str", "") or ""
        if dtstart_str:
            lines.append(dtstart_str)
            self.rruleset_dict["DTSTART"] = dtstart_str

        if rrule_line:
            lines.append(rrule_line)
            # only add the rdates from @+, not @s since we have a rrule_line
            self.rruleset_dict["RRULE"] = rrule_line
            if self.rdates:
                lines.append(f"RDATE:{','.join(self.rdates)}")
                self.rruleset_dict["RDATE"] = ",".join(self.rdates)
        else:
            # here we need to include @s since we do not have a rrule_line
            # NOTE Would we be finalizing rruleset with an rrule_line?
            rdstart_str = getattr(self, "rdstart_str", "") or ""
            if rdstart_str:
                lines.append(rdstart_str)
                self.rruleset_dict["RDATESONLY"] = rdstart_str

        exdate_str = getattr(self, "exdate_str", "") or ""
        if exdate_str:
            lines.append(f"EXDATE:{exdate_str}")
            self.rruleset_dict["EXDATE"] = f"EXDATE:{exdate_str}"

        return "\n".join(lines)

    def build_jobs(self):
        """
        Build self.jobs from @~ + &... token groups.
        Handles &r id: prereq1, prereq2, …  and &f completion pairs.
        """
        job_groups = self.collect_grouped_tokens({"~"})
        job_entries = []

        for idx, group in enumerate(job_groups, start=1):
            anchor = group[0]
            token_str = anchor["token"]

            # job name before first &
            job_portion = token_str[3:].strip()
            split_index = job_portion.find("&")
            job_name = (
                job_portion[:split_index].strip() if split_index != -1 else job_portion
            )

            job = {"~": job_name}

            for token in group[1:]:
                try:
                    k, v = token["token"][1:].split(maxsplit=1)
                    k = k.strip()
                    v = v.strip()

                    if k == "r":
                        ok, primary, deps = self.do_requires({"token": f"&r {v}"})
                        if not ok:
                            self.errors.append(primary)
                            continue
                        job["id"] = primary
                        job["reqs"] = deps

                    elif k == "f":  # completion
                        completed, due = parse_completion_value(v)
                        if completed:
                            job["f"] = self.fmt_compact(completed)
                            self.token_map.setdefault("~f", {})
                            self.token_map["~f"][job.get("id", idx)] = self.fmt_user(
                                completed
                            )
                        if due:
                            job["due"] = self.fmt_compact(due)

                    else:
                        job[k] = v

                except Exception as e:
                    self.errors.append(
                        f"Failed to parse job metadata token: {token['token']} ({e})"
                    )

            job_entries.append(job)

        self.jobs = job_entries
        return job_entries

    def finalize_jobs(self, jobs):
        """
        Compute job status (finished / available / waiting)
        using new &r id: prereqs format and propagate @f if all are done.
        Also sets a human-friendly `display_subject` per job.
        """
        if not jobs:
            return False, "No jobs to process"
        if not self.parse_ok:
            return False, "Error parsing job tokens"

        # index by id
        job_map = {j["id"]: j for j in jobs if "id" in j}
        finished = {jid for jid, j in job_map.items() if j.get("f")}

        # --- transitive dependency expansion ---
        all_prereqs = {}
        for jid, job in job_map.items():
            deps = set(job.get("reqs", []))
            trans = set(deps)
            stack = list(deps)
            while stack:
                d = stack.pop()
                if d in job_map:
                    for sd in job_map[d].get("reqs", []):
                        if sd not in trans:
                            trans.add(sd)
                            stack.append(sd)
            all_prereqs[jid] = trans

        # --- classify ---
        available, waiting = set(), set()
        for jid, deps in all_prereqs.items():
            unmet = deps - finished
            if jid in finished:
                continue
            if unmet:
                waiting.add(jid)
            else:
                available.add(jid)

        # annotate job objects with status
        for jid, job in job_map.items():
            if jid in finished:
                job["status"] = "finished"
            elif jid in available:
                job["status"] = "available"
            elif jid in waiting:
                job["status"] = "waiting"
            else:
                job["status"] = "standalone"

        # --- compute counts for display_subject ---
        num_available = sum(
            1 for j in job_map.values() if j.get("status") == "available"
        )
        num_waiting = sum(1 for j in job_map.values() if j.get("status") == "waiting")
        num_finished = sum(1 for j in job_map.values() if j.get("status") == "finished")

        task_subject = getattr(self, "subject", "") or ""
        if len(task_subject) > 12:
            task_subject_display = task_subject[:10] + " …"
        else:
            task_subject_display = task_subject

        # --- set display_subject per job (restoring old behavior) ---
        for jid, job in job_map.items():
            label = job.get("label") or job.get("~") or job.get("name") or f"#{jid}"
            # e.g. "A ∊ ParentTask 3/2/5"
            job["display_subject"] = (
                f"{label} ∊ {task_subject_display} {num_available}/{num_waiting}/{num_finished}"
            )

        # --- propagate @f if all jobs finished ---
        if finished and len(finished) == len(job_map):
            completed_dts = []
            for job in job_map.values():
                if "f" in job:
                    cdt, _ = parse_completion_value(job["f"])
                    if cdt:
                        completed_dts.append(cdt)

            if completed_dts:
                finished_dt = max(completed_dts)
                finished_str = self.fmt_user(finished_dt)
                # tok = {
                #     "token": f"@f {finished_str}",
                #     "t": "@",
                #     "k": "f",
                # }
                # self.add_token(tok)
                self._replace_or_add_token("f", finished_str)
                self._set_itemtype_token("x")
                self.has_f = True
                # self.completion = finished_dt
                first, second = self._get_first_two_occurrences()
                self.completions = (
                    finished_dt,
                    first,
                )

            # strip per-job @f tokens after promoting to record-level @f
            for job in job_map.values():
                job.pop("f", None)
            self._remove_job_finish_tokens()

        # --- finalize ---
        self.jobs = list(job_map.values())
        self.jobset = json.dumps(self.jobs, cls=CustomJSONEncoder)
        return True, self.jobs

    def do_f(self, token: dict | str, *, job_id: str | None = None):
        """
        Handle both:
        @f <datetime>[, <datetime>]  (task-level)
        &f <datetime>[, <datetime>]  (job-level)
        store completion datetime in self.completed
        """

        try:
            if isinstance(token, dict):  # task-level @f
                val = token["token"][2:].strip()
            else:  # job-level &f
                val = str(token).strip()
            due, next = self._get_first_two_occurrences()

            completed = parse(val)
            if not completed:
                return False, f"Invalid completion value: {val}", []
            self.completion = completed

            # ---- update token_map ----
            if job_id is None:
                # top-level task completion
                text = (
                    f"@f {self.fmt_user(completed)}, {self.fmt_user(due)}"
                    if due
                    else f"@f {self.fmt_user(completed)}"
                )
                self.token_map["f"] = text
                self.has_f = True
                token["token"] = text
                token["t"] = "@"
                token["k"] = "f"
                return True, text, []
            else:
                # job-level completion
                self.token_map.setdefault("~f", {})
                self.token_map["~f"][job_id] = self.fmt_user(completed)
                return True, f"&f {self.fmt_user(completed)}", []

        except Exception as e:
            return False, f"Error parsing completion token: {e}", []

    def _serialize_date_or_datetime(self, d: date | datetime, tz_used) -> str:
        if isinstance(d, date):
            return self._serialize_date(d)
        elif isinstance(d, datetime):
            if d.tzinfo is None:
                return self._serialize_naive_dt(d)
            return self._serialize_aware_dt(d, tz.UTC)
        return f"Error: {d} must either be a date or datetime"

    def _serialize_date(self, d: date) -> str:
        return d.strftime("%Y%m%d")

    def _serialize_naive_dt(self, dt: datetime) -> str:
        # ensure naive
        if dt.tzinfo is not None:
            dt = dt.replace(tzinfo=None)
        return dt.strftime("%Y%m%dT%H%M")

    def _serialize_aware_dt(self, dt: datetime, zone) -> str:
        # Attach or convert to `zone`, then to UTC and append Z
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=zone)
        else:
            dt = dt.astimezone(zone)
        dt_utc = dt.astimezone(tz.UTC)
        return dt_utc.strftime("%Y%m%dT%H%MZ")

    # --- these need attention - they don't take advantage of what's already in Item ---

    def _has_s(self) -> bool:
        return any(
            tok.get("t") == "@" and tok.get("k") == "s" for tok in self.relative_tokens
        )

    def _get_start_dt(self) -> datetime | None:
        # start_dt = self.dtstart_str
        # scheduled_datetime = parse(start_dt)  # if self.dtstart_str else None
        # return scheduled_datetime
        tok = next(
            (
                t
                for t in self.relative_tokens
                if t.get("t") == "@" and t.get("k") == "s"
            ),
            None,
        )
        if not tok:
            return None
        val = tok["token"][2:].strip()  # strip "@s "
        dt = parse(val)
        if isinstance(dt, date):
            return dt
        if isinstance(dt, datetime) and dt.tzinfo is None:
            return dt
        return dt.asttimezone(tz.UTC)

    def _set_start_dt(self, dt: datetime | None = None):
        """Replace or add an @s token; keep your formatting with trailing space."""
        # dt = dt | self._get_start_dt()
        if not dt:
            return
        ts = dt.strftime("%Y%m%dT%H%M")
        tok = next(
            (
                t
                for t in self.relative_tokens
                if t.get("t") == "@" and t.get("k") == "s"
            ),
            None,
        )
        if tok:
            tok["token"] = f"@s {ts} "
        else:
            self.relative_tokens.append({"token": f"@s {ts} ", "t": "@", "k": "s"})

    def _has_r(self) -> bool:
        return any(
            t.get("t") == "@" and t.get("k") == "r" for t in self.relative_tokens
        )

    def _get_count_token(self):
        # &c N under the @r group
        for t in self.relative_tokens:
            if t.get("t") == "&" and t.get("k") == "c":
                return t
        return None

    def _decrement_count_if_present(self) -> None:
        tok = self._get_count_token()
        if not tok:
            return
        parts = tok["token"].split()
        if len(parts) == 2 and parts[0] == "&c":
            try:
                n = int(parts[1])
                n2 = max(0, n - 1)
                if n2 > 0:
                    tok["token"] = f"&c {n2}"
                else:
                    # remove &c 0 entirely
                    self.relative_tokens.remove(tok)
            except ValueError:
                pass

    def _get_rdate_token(self):
        # @+ token (comma list)
        return next(
            (
                t
                for t in self.relative_tokens
                if t.get("t") == "@" and t.get("k") == "+"
            ),
            None,
        )

    def _parse_rdate_list(self) -> list[str]:
        """Return list of compact dt strings (e.g. '20250819T110000') from @+."""
        tok = self._get_rdate_token()
        if not tok:
            return []
        body = tok["token"][2:].strip()  # strip '@+ '
        parts = [p.strip() for p in body.split(",") if p.strip()]
        return parts

    def _write_rdate_list(self, items: list[str]) -> None:
        tok = self._get_rdate_token()
        if items:
            joined = ", ".join(items)
            if tok:
                tok["token"] = f"@+ {joined}"
            else:
                self.relative_tokens.append(
                    {"token": f"@+ {joined}", "t": "@", "k": "+"}
                )
        else:
            if tok:
                self.relative_tokens.remove(tok)

    def _remove_rdate_exact(self, dt_compact: str) -> None:
        lst = self._parse_rdate_list()
        lst2 = [x for x in lst if x != dt_compact]
        self._write_rdate_list(lst2)

    # --- for finish trial ---

    def _unfinished_jobs(self) -> list[dict]:
        return [j for j in self.jobs if "f" not in j]

    def _mark_job_finished(self, job_id: int, completed_dt: datetime) -> bool:
        """
        Add &f to the job (in jobs JSON) and also mutate the @~ token group if you keep that as text.
        Returns True if the job was found and marked.
        """
        if not job_id:
            return False
        found = False
        # Annotate JSON jobs
        for j in self.jobs:
            if j.get("i") == job_id and "f" not in j:
                j["f"] = round(completed_dt.timestamp())
                found = True
                break

        # (Optional) If you also keep textual @~… &f … tokens in relative_tokens,
        # you can append/update them here. Otherwise, finalize_jobs() will rebuild jobs JSON.
        if found:
            self.finalize_jobs(self.jobs)  # keeps statuses consistent
        return found

    def _set_itemtype(self, ch: str) -> None:
        """Set itemtype and mirror into the first token if that token stores it."""
        self.itemtype = ch
        if self.relative_tokens and self.relative_tokens[0].get("t") == "itemtype":
            # tokens typically look like {'t':'itemtype', 'token':'~'} or similar
            self.relative_tokens[0]["token"] = ch

    def _is_undated_single_shot(self) -> bool:
        """No @s, no RRULE, no @+ -> nothing to schedule (pure one-shot)."""
        return (
            (not self._has_s())
            and (not self._has_rrule())
            and (not self._find_all("@", "+"))
        )

    def _has_any_future_instances(self, now_dt: datetime | None = None) -> bool:
        """Return True if rruleset/@+ yields at least one occurrence >= now (or at all if now is None)."""
        rule_str = self.rruleset
        if not rule_str and not self._find_all("@", "+"):
            return False
        try:
            rs = rrulestr(rule_str) if rule_str else None
            if rs is None:
                # RDATE-only path (from @+ mirrored into rruleset)
                rdates = self._parse_rdate_list()  # returns compact strings
                return bool(rdates)
            if now_dt is None:
                # if we don’t care about “future”, just “any occurrences”
                return next(iter(rs), None) is not None
            # find first >= now
            try:
                got = rs.after(now_dt, inc=True)
            except TypeError:
                # handle aware/naive mismatch by using UTC-aware fallback

                anchor = now_dt if now_dt.tzinfo else now_dt.replace(tzinfo=tz.UTC)
                got = rs.after(anchor, inc=True)
            return got is not None
        except Exception:
            return False

    def _remove_tokens(
        self,
        selector: str | set[str] | list[str] | tuple[str, ...],
        key: str | None = None,
        *,
        max_count: int | None = None,
        token_types: set[str] | None = None,
    ) -> int:
        """
        Remove tokens based on either (type, key) or a set of keys restricted
        to specific token types.

        Args:
            selector: either the token type (e.g., "@", "&") or a collection of
                token keys (e.g., {"r", "+", "-"}).
            key: optional subtype when `selector` is a token type.
            max_count: only applies to the (type, key) form.
            token_types: when `selector` is a collection of keys, limit removal
                to these token types (defaults to all types).
        """
        if not getattr(self, "relative_tokens", None):
            return 0

        using_key_set = isinstance(selector, (set, list, tuple))
        keys = set(selector) if using_key_set else None
        removed = 0
        removed_f = False
        new_tokens = []

        for tok in self.relative_tokens:
            if using_key_set:
                match = tok.get("k") in keys and (
                    not token_types or tok.get("t") in token_types
                )
                should_skip = match
            else:
                match = tok.get("t") == selector and (
                    key is None or tok.get("k") == key
                )
                should_skip = match and (max_count is None or removed < max_count)

            if should_skip:
                removed += 1
                if (
                    using_key_set
                    and ("f" in keys)
                    and (not token_types or "@" in token_types)
                ) or (
                    not using_key_set
                    and selector == "@"
                    and (key is None or key == "f")
                ):
                    removed_f = True
                continue

            new_tokens.append(tok)

        self.relative_tokens = new_tokens

        if removed_f:
            self._rebuild_completions_from_tokens()

        return removed

    def _rebuild_completions_from_tokens(self) -> None:
        """
        Rebuild self.completions from remaining @f tokens in relative_tokens.
        Normalizes to a list[datetime].
        """

        comps = []
        for tok in getattr(self, "relative_tokens", []):
            if tok.get("t") == "@" and tok.get("k") == "f":
                # token text looks like "@f 20250828T211259 "
                try:
                    body = (tok.get("token") or "")[2:].strip()  # drop "@f"
                    dt = parse(body)
                    comps.append(dt)
                except Exception as e:
                    log_msg(f"error: {e}")

        self.completions = comps

    def _clear_schedule(self) -> None:
        """Clear any schedule fields/tokens and rruleset mirror."""
        # remove @s
        self._remove_tokens("@", "s")
        # remove @+/@- (optional if you mirror in rruleset)
        self._remove_tokens("@", "+")
        self._remove_tokens("@", "-")
        # remove @r group (&-modifiers) – you likely have a grouped removal util
        self._remove_tokens("@", "r")
        self._remove_tokens("&")  # if your &-mods only apply to recurrence
        # clear rruleset string
        self.rruleset = ""

    def _has_any_occurrences_left(self) -> bool:
        """
        Return True if the current schedule (rruleset and/or RDATEs) still yields
        at least one occurrence, irrespective of whether it’s past or future.
        """
        rule_str = self.rruleset
        # If we mirror @+ into RDATE, the rrulestr path below will handle it;
        # but if you keep @+ separate, fall back to parsing @+ directly:
        if not rule_str and self._find_all("@", "+"):
            return bool(self._parse_rdate_list())  # remaining RDATEs?

        if not rule_str:
            return False

        try:
            rs = rrulestr(rule_str)
            return next(iter(rs), None) is not None
        except Exception:
            return False

    def _has_o(self) -> bool:
        return any(
            t.get("t") == "@" and t.get("k") == "o" for t in self.relative_tokens
        )

    def _get_o(self) -> tuple[timedelta, bool] | None:
        """
        Read the first @o token and return (interval, learn) or None.
        """
        tok = next(
            (
                t
                for t in self.relative_tokens
                if t.get("t") == "@" and t.get("k") == "o"
            ),
            None,
        )
        if not tok:
            return None
        body = tok["token"][2:].strip()  # strip '@o'
        td, learn = _parse_o_body(body)
        return td, learn

    def _set_o_interval(self, td: timedelta, learn: bool) -> None:
        """
        Update or create the @o token with a normalized form ('@o 3d', '@o ~3d').
        """
        normalized = f"@o {'~' if learn else ''}{td_to_td_str(td)} "
        o_tok = next(
            (
                t
                for t in self.relative_tokens
                if t.get("t") == "@" and t.get("k") == "o"
            ),
            None,
        )
        if o_tok:
            o_tok["token"] = normalized
        else:
            self.relative_tokens.append({"token": normalized, "t": "@", "k": "o"})

    # --- drop-in replacement for do_over -----------------------------------

    def do_target(self, token):
        """
        Normalize @t (target) token.
        - Accepts '@t 3/1w', etc. taking the format 'num_completions: int' / 'time_period: seconds'.
        Returns (ok, (int, int), messages)
        """
        try:
            # token is a relative token dict, like {"token": "@o 3d", "t":"@", "k":"o"}
            body = token["token"][2:].strip()  # remove '@t'
            num, period = body.split("/")
            num = int(num)
            ok, sec = timedelta_str_to_seconds(period)
            td = timedelta(seconds=sec)
            # Normalize token text
            normalized = f"@t {num}/{td_to_td_str(td)} "
            token["token"] = normalized
            token["t"] = "@"
            token["k"] = "t"
            return True, (num, td), []
        except Exception as e:
            return False, f"invalid {token = }: {e}", []

    def do_offset(self, token):
        """
        Normalize @o (over/offset) token.
        - Accepts '@o 3d', '@o ~3d', '@o learn 3d'
        - Stores a normalized token ('@o 3d ' or '@o ~3d ')
        Returns (ok, seconds, messages) so callers can use the numeric interval if needed.
        """
        try:
            # token is a relative token dict, like {"token": "@o 3d", "t":"@", "k":"o"}
            body = token["token"][2:].strip()  # remove '@o'
            td, learn = _parse_o_body(body)

            # Normalize token text
            normalized = f"{'~' if learn else ''}{td_to_td_str(td)}"
            # token["token"] = normalized
            # token["t"] = "@"
            # token["k"] = "o"
            self._replace_or_add_token("o", normalized)

            # return True, int(td.total_seconds()), []
            return True, normalized, []
        except Exception as e:
            return False, f"invalid @o interval: {e}", []

    def _instance_to_token_format_utc(self, dt: datetime) -> str:
        """Convert a datetime to UTC ‘YYYYMMDDTHHMMZ’ format (for DTSTART in rruleset)."""
        if dt.tzinfo is None:
            local = dt.replace(tzinfo=tz.tzlocal())
        else:
            local = dt
        dt_utc = local.astimezone(tz.UTC)
        return dt_utc.strftime("%Y%m%dT%H%MZ")

    def _instance_to_token_format_local(self, dt: datetime | date) -> str:
        """Format a date or datetime to local token string (no Z)."""
        if isinstance(dt, datetime):
            local = _to_local_naive(dt)
            return local.strftime("%Y%m%dT%H%M")
        else:
            return dt.strftime("%Y%m%d")

    def _is_first_from_rdate(self, first_dt: datetime) -> bool:
        """
        Returns True if the next occurrence (first_dt) matches an explicit @+ list date.
        """
        for tok in self.relative_tokens:
            if tok.get("k") == "+":
                token_body = tok["token"][2:].strip()
                for part in token_body.split(","):
                    part = part.strip()
                    try:
                        dt = parse(part)
                    except Exception:
                        continue
                    if _to_local_naive(dt) == _to_local_naive(first_dt):
                        return True
        return False

    def _get_sorted_plus_dt_str(self) -> str:
        """Find the earliest date in @+ tokens and return it as user-fmt string."""
        plus_dates = []
        for tok in self.relative_tokens:
            if tok.get("k") == "+":
                body = tok["token"][2:].strip()
                parts = [x.strip() for x in body.split(",")]
                parts.sort()
                plus_dates = parts

        if not plus_dates:
            return ""
        return plus_dates

    def next_from_rrule(self):
        rdict = self.rruleset_dict
        if "RRULE" not in rdict:
            return None
        components = [
            rdict.get("DTSTART", ""),
            rdict.get("RRULE", ""),
            rdict.get("EXDATE", ""),
        ]
        rule = rrulestr("\n".join(components))
        first_two = list(rule)[:2]
        if len(first_two) == 2:
            return first_two[1]
        else:
            return None

    def finish(self) -> None:
        """Process finishing of an item."""
        due_dt = None
        if offset_tok := next(
            (t for t in self.relative_tokens if t.get("k") == "o"), None
        ):
            due_dt = self._get_start_dt()
            completed_dt = self.completion
            raw_offset = offset_tok["token"].split(maxsplit=1)[1]
            td = td_str_to_td(raw_offset.lstrip("~"))
            offset_body = raw_offset.strip()
            if offset_body.startswith("~") and due_dt:
                actual = completed_dt - due_dt
                td = self._smooth_interval(td, actual)
                self._replace_or_add_token("o", f"~{td_to_td_str(td)}")
            else:
                self._replace_or_add_token("o", td_to_td_str(td))

            new_due = completed_dt + td
            self._replace_or_add_token("s", self.fmt_user(new_due))
            utc_next = self._instance_to_token_format_utc(new_due)
            self.rruleset = f"RDATE:{utc_next}"
            self.rdstart_str = f"RDATE:{utc_next}"
            self.dtstart = utc_next
            self._remove_tokens({"f"}, token_types={"@"})
            self._remove_job_finish_tokens()

            return

        if target_tok := next(
            (t for t in self.relative_tokens if t.get("k") == "t"), None
        ):
            """
            Remove @f token.
            If @k is missing, then add @k 1.
            If @k is less than the number of num_completions, increment it by 1.
            Else if @k is greater than or equal to the number of num_completions:
                record a success
                increment @s by the allowed period
                reset @k to 0 or remove it.

            PDocstring for finish

            :param self: Description
            """
            due_dt = self._get_start_dt()
            completed_dt = self.completion
            ok, (num_completions, period_td), message = self.do_target(target_tok)
            if not ok:
                return
            done = 0
            if kompleted_tok := next(
                (t for t in self.relative_tokens if t.get("k") == "k"), None
            ):
                done = kompleted_tok["token"][2:].strip()  # remove '@k'
                done = int(done)
            if done + 1 < num_completions:
                # increment @k
                old_done = done
                done += 1
                self._replace_or_add_token("k", done)
            else:
                # mark success, increment @s by period_td, reset @k
                done = 0
                new_start = due_dt + period_td
                self.dtstart = self.fmt_user(new_start)
                self._replace_or_add_token("s", self.dtstart)
                self.rdstart_str = f"RDATE:{self.dtstart}"
                self.rruleset = f"RDATE:{self.dtstart}"
                self.rruleset_dict["START_RDATES"] = self.rdstart_str
            self._replace_or_add_token("k", str(done))
            self._remove_tokens({"f"}, token_types={"@"})
            return

        # if not offset or goal, use rruleset for due
        first, second = self._get_first_two_occurrences()
        due = first
        if due is None:
            # No upcoming instance — mark done
            self._set_itemtype_token("x")
            self.completions = (self.completion, None)
            return

        is_rrule = bool(self.rruleset and "RRULE" in self.rruleset)
        has_plus = any(tok.get("k") == "+" for tok in self.relative_tokens)
        is_rdate_only = (not is_rrule) and has_plus

        if is_rrule:
            if self._is_first_from_rdate(due):
                # First instance came from explicit @+ date despite RRULE
                tok_str = self._instance_to_token_format_local(due)
                removed = self._remove_instance_from_plus_tokens(
                    self.relative_tokens, tok_str
                )
                if not removed:
                    tok_str_alt = fmt_utc_z(due)
                    removed = self._remove_instance_from_plus_tokens(
                        self.relative_tokens, tok_str_alt
                    )
                if removed:
                    self._reparse_from_tokens()

            else:
                # First from RRULE — advance @s to next (and honor COUNT)
                next_due = self.next_from_rrule()
                if next_due:
                    local_next = _to_local_naive(next_due)
                    self._advance_dtstart_and_decrement_count(local_next)
                else:
                    self._decrement_count_token()
                    self._remove_tokens({"r", "+", "-"}, token_types={"@"})
                    self._set_itemtype_token("x")

        elif is_rdate_only:
            # RDATE-only case
            # tok_str = self._instance_to_token_format_local(first)
            # Usual suspects: @s + @+. Combine them as a list of fmt_utc_z strings, sort, remove duplicates
            tok_str = fmt_utc_z(first)
            plus_dates = self._get_sorted_plus_dt_str()
            # the first from @+ will either be the new_start or the instance that was finished
            # either way, it will be removed
            first_from_plus = plus_dates.pop(0) if plus_dates else None
            if plus_dates:
                new_plus = ",".join(plus_dates)
                self._replace_or_add_token("+", new_plus)
            else:
                # there are no more datetimes in @+
                self._remove_tokens({"+"}, token_types={"@"})
            if tok_str == self.dtstart:
                # the first instance is @s
                if first_from_plus:
                    # there is a new_start available in @+ to replace @s
                    new_start = first_from_plus
                    self._replace_or_add_token("s", new_start)
                    self.dtstart = new_start
                else:
                    # @s was the only instance
                    self._set_itemtype_token("x")
            else:
                # the first instance must be from @+, not @s which will remain unchanged
                # since first_from_plus has already been removed from @+, nothing left to do
                pass

            new_plus_dates = self._get_sorted_plus_dt_str()
            new_plus_date_str = (
                f",{','.join([x for x in plus_dates])}" if plus_dates else ""
            )
            self.rdstart_str = f"RDATE:{self.dtstart}{new_plus_date_str}"
            self.rruleset = f"RDATE:{self.dtstart}{new_plus_date_str}"
            self.rruleset_dict["START_RDATES"] = self.rdstart_str

        else:
            # one-shot or no repetition
            self._remove_tokens({"r", "+", "-"}, token_types={"@"})
            self._set_itemtype_token("x")

        self._remove_tokens({"f"}, token_types={"@"})
        if not self.completions:
            self.completions = (self.completion, due)

    def _replace_or_add_token(self, key: str, dt: str) -> None:
        """Replace token with key `key` or add new one for dt."""
        if isinstance(dt, datetime):
            dt = self.fmt_user(dt)
        new_tok = {"token": f"@{key} {dt}", "t": "@", "k": key}
        # replace if exists
        for tok in self.relative_tokens:
            if tok.get("k") == key:
                tok.update(new_tok)
                return
        # else append
        self.relative_tokens.append(new_tok)

    def _remove_job_finish_tokens(self) -> None:
        """Remove &f tokens attached to @~ job groups."""
        job_groups = self.collect_grouped_tokens({"~"})
        for group in job_groups:
            for token in group[1:]:
                if token.get("t") == "&" and token.get("k") == "f":
                    try:
                        self.relative_tokens.remove(token)
                    except ValueError:
                        pass

    def reparse_finish_tokens(self) -> None:
        """
        Re-run only the token handlers that can be affected by finish:
        @s, @r, @+.
        Works directly from self.relative_tokens.
        """
        affected_keys = {"s", "r", "+"}

        for tok in self.relative_tokens:
            k = tok.get("k")
            if k in affected_keys:
                handler = getattr(self, f"do_{k}", None)
                if handler:
                    ok, msg, extras = handler(tok)
                    if not ok:
                        self.parse_ok = False
                        self.parse_message = msg
                        return
                    # process any extra tokens the handler produces
                    for extra in extras:
                        ek = extra.get("k")
                        if ek in affected_keys:
                            getattr(self, f"do_{ek}")(extra)

        # only finalize if parse is still clean
        # if self.parse_ok and self.final:
        #     self.finalize_rcord()

    def mark_final(self) -> None:
        """
        Mark this item as final and normalize to absolute datetimes.
        """
        self.final = True
        self.rebuild_from_tokens(resolve_relative=True)  # force absolute now
        # self.finalize_rruleset()  # RRULE/DTSTART/RDATE/EXDATE strings updated

    def rebuild_from_tokens(self, *, resolve_relative: bool) -> None:
        """Recompute DTSTART/RDATE/RRULE/EXDATE + rruleset + jobs from self.relative_tokens."""
        if resolve_relative is None:
            resolve_relative = self.final
        dtstart_str, rdstart_str, rrule_line = self._derive_rrule_pieces()
        self.dtstart_str = dtstart_str or ""
        self.rdstart_str = rdstart_str or ""
        self.rruleset = self._compose_rruleset(dtstart_str, rrule_line, rdstart_str)
        # If you derive jobs from tokens, keep this; else skip:
        if self.collect_grouped_tokens({"~"}):
            jobs = self.build_jobs()
            self.finalize_jobs(jobs)

    def _normalize_datetime_tokens(self, *, resolve_relative: bool) -> None:
        """Normalize @s/@+/@-/@f to compact absolute strings; optionally resolve human phrases."""

        def to_compact(dt):
            if isinstance(dt, datetime):
                return dt.strftime("%Y%m%dT%H%M")
            # If you ever allow date objects:
            return dt.strftime("%Y%m%d")

        for tok in self.relative_tokens:
            if tok.get("t") != "@":
                continue
            k = tok.get("k")
            text = (tok.get("token") or "").strip()
            if k == "s":
                body = text[2:].strip()
                dt = (
                    parse(body)
                    if resolve_relative
                    else self._parse_compact_or_iso(body)
                )
                tok["token"] = f"@s {to_compact(dt)} "
            elif k in {"+", "-"}:
                body = text[2:].strip()
                parts = [p.strip() for p in body.split(",") if p.strip()]
                dts = [
                    (parse(p) if resolve_relative else self._parse_compact_or_iso(p))
                    for p in parts
                ]
                joined = ",".join(to_compact(dt) for dt in dts)
                tok["token"] = f"@{k} {joined} "
            elif k == "f":
                body = text[2:].strip()
                dt = (
                    parse(body)
                    if resolve_relative
                    else self._parse_compact_or_iso(body)
                )
                tok["token"] = f"@f {to_compact(dt)} "

    def _derive_rrule_pieces(self) -> tuple[str | None, str | None, str | None]:
        """Return (DTSTART line, RDATE line, RRULE line) from tokens."""
        dtstart = None
        rdates, exdates = [], []
        rrule_components = {}

        for tok in self.relative_tokens:
            if tok.get("t") != "@":
                continue
            k = tok.get("k")
            text = (tok.get("token") or "").strip()
            if k == "s":
                dtstart = text[2:].strip()
            elif k == "+":
                rdates += [p.strip() for p in text[2:].split(",") if p.strip()]
            elif k == "-":
                exdates += [p.strip() for p in text[2:].split(",") if p.strip()]
            elif k == "r":
                group = next(
                    (
                        g
                        for g in self.collect_grouped_tokens({"r"})
                        if g and g[0] is tok
                    ),
                    None,
                )
                if group:
                    rrule_components = self._rrule_components_from_group(group)

        dtstart_str = None
        if dtstart:
            dtstart_str = (
                f"DTSTART;VALUE=DATE:{dtstart}"
                if len(dtstart) == 8
                else f"DTSTART:{dtstart}"
            )

        rdstart_str = f"RDATE:{','.join(rdates)}" if rdates else None
        # If you want EXDATE, add it similarly and pass to _compose_rruleset.
        rrule_line = (
            f"RRULE:{';'.join(f'{k}={v}' for k, v in rrule_components.items())}"
            if rrule_components
            else None
        )
        return dtstart_str, rdstart_str, rrule_line

    def _compose_rruleset(
        self, dtstart_str, rrule_line, rdate_line, exdate_line=None
    ) -> str:
        parts = []
        if dtstart_str:
            parts.append(dtstart_str)
        if rrule_line:
            parts.append(rrule_line)
        if rdate_line:
            parts.append(rdate_line)
        if exdate_line:
            parts.append(exdate_line)
        return "\n".join(parts)

    def _parse_compact_or_iso(self, s: str) -> datetime:
        """Accept YYYYMMDD or YYYYMMDDTHHMMSS or any ISO-ish; return datetime."""
        s = s.strip()
        if len(s) == 8 and s.isdigit():
            return datetime.strptime(s, "%Y%m%d")
        if len(s) == 15 and s[8] == "T":
            return datetime.strptime(s, "%Y%m%dT%H%M")
        return parse(s)

    def _rrule_components_from_group(self, group: list[dict]) -> dict:
        """Build RRULE components dict from the @r group & its &-options."""
        freq_map = {"y": "YEARLY", "m": "MONTHLY", "w": "WEEKLY", "d": "DAILY"}
        comps = {}
        anchor = group[0]["token"]  # "@r d" etc.
        parts = anchor.split(maxsplit=1)
        if len(parts) > 1:
            freq_abbr = parts[1].strip()
            freq = freq_map.get(freq_abbr)
            if freq:
                comps["FREQ"] = freq
        for tok in group[1:]:
            if tok.get("t") == "&":
                key, value = (
                    tok.get("k"),
                    (
                        tok.get("v") or tok.get("token", "")[1:].split(maxsplit=1)[-1]
                    ).strip(),
                )
                if key == "m":
                    comps["BYMONTH"] = value
                elif key == "w":
                    comps["BYDAY"] = value
                elif key == "d":
                    comps["BYMONTHDAY"] = value
                elif key == "i":
                    comps["INTERVAL"] = value
                elif key == "u":
                    comps["UNTIL"] = value.replace("/", "")
                elif key == "c":
                    comps["COUNT"] = value
        return comps

    def _strip_positions(self, tokens_with_pos: list[dict]) -> list[dict]:
        """Remove 'start'/'end' from editing tokens and strip whitespace from 'token'."""
        out = []
        for t in tokens_with_pos:
            t2 = dict(t)
            t2.pop("s", None)
            t2.pop("e", None)
            if "token" in t2 and isinstance(t2["token"], str):
                t2["token"] = t2["token"].strip()
            out.append(t2)
        return out

    def _mask_secret(self) -> str:
        if self.env and getattr(self.env, "config", None):
            return getattr(self.env.config, "secret", "") or ""
        return ""

    def _encode_mask_tokens(self, tokens: list[dict]) -> list[dict]:
        secret = self._mask_secret()
        return obfuscate_mask_tokens(tokens, secret)

    def _set_itemtype_token(self, new_itemtype: str) -> None:
        """Update itemtype attribute and the leading token."""
        self.itemtype = new_itemtype
        for tok in self.relative_tokens:
            if tok.get("t") == "itemtype":
                tok["token"] = new_itemtype
                break
