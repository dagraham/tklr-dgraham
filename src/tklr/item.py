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

from .shared import (
    log_msg,
    print_msg,
    fmt_local_compact,
    parse_local_compact,
    fmt_utc_z,
    parse_utc_z,
    timedelta_str_to_seconds,
)
from tzlocal import get_localzone_name

local_timezone = get_localzone_name()  # e.g., "America/New_York"

JOB_PATTERN = re.compile(r"^@~ ( *)([^&]*)(?:(&.*))?")
LETTER_SET = set("abcdefghijklmnopqrstuvwxyz")  # Define once


def is_date(obj):
    if isinstance(obj, date) and not isinstance(obj, datetime):
        return True
    return False


def is_datetime(obj):
    if isinstance(obj, date) and isinstance(obj, datetime):
        return True
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
    secs = int(td.total_seconds())
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
    learn = False
    if b.startswith("~"):
        learn = True
        b = b[1:].strip()
    elif b.startswith("learn"):
        learn = True
        b = b[5:].strip()

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


# def parse_pair(dt_pair_str: str) -> str:
#     """ """
#     dt_strs = [x.strip() for x in dt_pair_str.split(",")]
#     return [parse(x) for x in dt_strs]


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
    "+": "goal",
    "?": "draft",
    "x": "finished",
    # '✓': 'finished',  # more a property of a task than an item type
}
common_methods = list("cdgilmnstuxz") + ["k", "#"]

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

datetime_methods = list("abew+-")

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
    "~u",
]

multiple_allowed = [
    "a",
    "u",
    "r",
    "t",
    "~",
    "~r",
    "~t",
    "~a",
]

wrap_methods = ["w"]

required = {"*": ["s"], "~": [], "^": ["~"], "%": [], "?": [], "+": []}

all_keys = common_methods + datetime_methods + job_methods + repeating_methods

allowed = {
    "*": common_methods + datetime_methods + repeating_methods + wrap_methods,
    "~": common_methods + datetime_methods + task_methods + repeating_methods,
    "+": common_methods + datetime_methods + task_methods,
    "^": common_methods + datetime_methods + job_methods + repeating_methods,
    "%": common_methods + datetime_methods,
    "?": all_keys,
}


requires = {
    "a": ["s"],
    "b": ["s"],
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


@dataclass
class FinishResult:
    new_relative_tokens: list  # tokens to persist
    new_rruleset: str | None  # possibly None/"" if no more repeats
    due_ts_used: int | None  # the occurrence this finish applies to
    finished_final: bool  # True -> no more occurrences


class Item:
    token_keys = {
        "itemtype": [
            "item type",
            "character from * (event), ~ (task), ^ (project), % (note),  ! (goal) or ? (draft)",
            "do_itemtype",
        ],
        "subject": [
            "subject",
            "item subject. Append an '@' to add an option.",
            "do_summary",
        ],
        "s": ["scheduled", "starting date or datetime", "do_s"],
        "t": ["tag", "tag name", "do_tag"],
        "r": ["recurrence", "recurrence rule", "do_rrule"],
        "o": ["offset", "offset rule", "do_offset"],
        "~": ["job", "job entry", "do_job"],
        "+": ["rdate", "recurrence dates", "do_rdate"],
        "-": ["exdate", "exception dates", "do_exdate"],
        "a": ["alerts", "list of alerts", "do_alert"],
        "b": ["beginby", "period for beginby notices", "do_beginby"],
        "c": ["context", "context", "do_string"],
        "d": ["description", "item description", "do_description"],
        "e": ["extent", "timeperiod", "do_extent"],
        "w": ["wrap", "list of two timeperiods", "do_two_periods"],
        "f": ["finish", "completion done -> due", "do_completion"],
        "g": ["goto", "url or filepath", "do_string"],
        "h": [
            "completions",
            "list of completion datetimes",
            "do_completions",
        ],
        "i": ["index", "forward slash delimited string", "do_string"],
        "l": [
            "label",
            "label for job clone",
            "do_string",
        ],
        "m": ["mask", "string to be masked", "do_mask"],
        "n": ["attendee", "name <email address>", "do_string"],
        "p": [
            "priority",
            "priority from 1 (someday), 2 (low), 3 (medium), 4 (high) to 5 (next)",
            "do_priority",
        ],
        "w": ["wrap", "wrap before, after", "do_wrap"],
        "z": [
            "timezone",
            "a timezone entry such as 'US/Eastern' or 'Europe/Paris' or 'none' to specify a naive datetime, i.e., one without timezone information",
            "do_timezone",
        ],
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
            "job subject. Append an '&' to add a job option.",
            "do_string",
        ],
        "~a": [
            "alert",
            "list of timeperiods before job is scheduled followed by a colon and a list of commands",
            "do_alert",
        ],
        # "~b": ["beginby", " beginby period", "do_beginby"],
        "~c": ["context", " string", "do_string"],
        "~d": ["description", " string", "do_description"],
        "~e": ["extent", " timeperiod", "do_extent"],
        "~f": ["finish", " completion done -> due", "do_completion"],
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
            "do_duration",
        ],
        "~u": ["used time", "timeperiod: datetime", "do_usedtime"],
        "~?": ["job &-key", "enter &-key", "do_ampj"],
        "k": ["konnection", "not implemented", "do_nothing"],
        "#": ["etm record number", "not implemented", "do_nothing"],
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
        self.env = env

        # --- core parse state ---
        self.entry = ""
        self.previous_entry = ""
        self.itemtype = ""
        self.subject = ""
        self.context = ""
        self.description = ""
        self.token_map = {}
        self.parse_ok = False
        self.parse_message = ""
        self.previous_tokens = []
        self.relative_tokens = []
        self.tokens = []
        self.messages = []

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
        self.jobset = []
        self.priority = None
        self.tags = []
        self.alerts = []
        self.beginby = ""

        # --- date/time collections (strings) ---
        self.s_kind = ""
        self.s_tz = None
        self.rdates = []
        self.exdates = []
        self.rdate_str = ""
        self.exdate_str = ""

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
        self.completion: tuple[datetime, datetime | None] | None = None
        self.over = ""
        self.has_f = False  # True if there is an @f to process after parsing tokens

        # --- optional initial parse ---
        self.ampm = False
        self.yearfirst = True
        self.dayfirst = False
        self.two_digit_year = True
        if self.env:
            self.ampm = self.env.config.ui.ampm
            self.timefmt = "%-I:%M%p" if self.ampm else "%H:%M"
            self.dayfirst = self.env.config.ui.dayfirst
            self.yearfirst = self.env.config.ui.yearfirst
            self.history_weight = self.env.config.ui.history_weight
            _yr = "%y" if self.two_digit_year else "%Y"
            _dm = "%d-%m" if self.dayfirst else "%m-%d"
            self.datefmt = f"{_yr}-{_dm}" if self.yearfirst else f"{_dm}-{_yr}"
            self.two_digit_year = self.env.config.ui.two_digit_year
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

    def to_entry(self) -> str:
        """
        Rebuild a tklr entry string from this Item’s fields.
        """
        # --- map itemtype ---
        itemtype = self.itemtype
        # if itemtype == "-":  # special case: etm task/project split
        #     if self.jobs and self.jobs != "[]":
        #         itemtype = "^"  # project
        #     else:
        #         itemtype = "~"  # task
        # else:
        #     itemtype = TYPE_MAP.get(itemtype, itemtype)

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

        if getattr(self, "beginby", None):
            parts.append(f"@b {self.beginby}")

        # --- tags ---
        if getattr(self, "tags", None):
            tags = " ".join(f"@t {t}" for t in self.tags)
            parts.append(tags)

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

        message = self.validate()
        if message:
            self.parse_ok = False
            self.parse_message = message
            print(f"parse failed: {message = }")
            return
        self.mark_grouped_tokens()
        self._parse_tokens(entry)

        self.parse_ok = True
        self.previous_entry = entry
        self.previous_tokens = self.relative_tokens.copy()

        if self.final:
            self.finalize_record()

    def finalize_record(self):
        """
        When the entry and token list is complete:
        1) finalize jobs, processing any &f entries and adding @f when all jobs are finished
        2) finalize_rruleset so that next instances will be available
        3) process @f entries (&f entries will have been done by finalize_jobs)

        """
        if self.itemtype == "^":
            jobset = self.build_jobs()
            success, finalized = self.finalize_jobs(jobset)
        # rruleset is needed to get the next two occurrences
        if self.collect_grouped_tokens({"r"}):
            rruleset = self.finalize_rruleset()
            log_msg(f"got rruleset {rruleset = }")
            if rruleset:
                self.rruleset = rruleset
        elif self.rdstart_str is not None:
            # @s but not @r
            self.rruleset = self.rdstart_str

        if self.has_f:
            self.itemtype = "x"
            self.finish()

        self.tokens = self._strip_positions(self.relative_tokens)
        log_msg(f"{self.relative_tokens = }; {self.tokens = }")

    def validate(self):
        if len(self.relative_tokens) < 2:
            # nothing to validate without itemtype and subject
            return

        def fmt_error(message: str):
            return [x.strip() for x in message.split(",")]

        errors = []

        self.itemtype = self.relative_tokens[0]["token"]
        if not self.itemtype:
            return "no itemtype"

        subject = self.relative_tokens[1]["token"]
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
                need = (
                    f"required: {', '.join(needed)}\n" if needed and type == "@" else ""
                )
                options = []
                options = (
                    [x for x in allowed_fortype if len(x) == 1]
                    if type == "@"
                    else [x[-1] for x in allowed_fortype if len(x) == 2]
                )
                optional = f"options: {', '.join(options)}" if options else ""
                return fmt_error(f"{token['t']} incomplete, {need}{optional}")
            if token["t"] == "@":
                # print(f"{token['token']}; {used_atkeys = }")
                used_ampkeys = []
                this_atkey = token["k"]
                log_msg(f"{this_atkey = }")
                if this_atkey not in all_keys:
                    return fmt_error(f"@{this_atkey}, Unrecognized @-key")
                if this_atkey not in allowed_fortype:
                    return fmt_error(
                        f"@{this_atkey}, The use of this @-key is not supported in type '{self.itemtype}' reminders"
                    )
                if this_atkey in used_atkeys and this_atkey not in multiple_allowed:
                    return fmt_error(
                        f"@{current_atkey}, Multiple instances of this @-key are not allowed"
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
            elif token["t"] == "&":
                this_ampkey = f"{current_atkey}{token['k']}"
                log_msg(f"{current_atkey = }, {this_ampkey = }")
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

    def fmt_user(self, dt: datetime) -> str:
        """
        User friendly formatting for dates and datetimes using env settings
        for ampm, yearfirst, dayfirst and two_digit year.
        """
        # Simple user-facing formatter; tweak to match your prefs
        if isinstance(dt, datetime):
            return dt.strftime(self.datetimefmt)
        if isinstance(dt, date):
            return dt.strftime(self.datefmt)
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
            return None, "error", f"Could not parse '{core}': {e.__class__.__name__}"

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
        current_group: list[dict] = []
        collecting = False

        for token in self.relative_tokens:
            if token.get("t") == "@" and token.get("k") in anchor_keys:
                if current_group:
                    groups.append(current_group)
                current_group = [token]
                collecting = True
            elif collecting and token.get("t") == "&":
                current_group.append(token)
            elif collecting:
                # hit a non-& token, close the current group
                groups.append(current_group)
                current_group = []
                collecting = False

        if current_group:
            groups.append(current_group)

        log_msg(f"{groups = }")
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

        anchor_keys = {"r", "~"}

        groups = self.collect_grouped_tokens(anchor_keys)

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

        log_msg(f"token_group_map {tgm = }")

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
        log_msg(f"_tokenize {entry = }")

        self.entry = entry
        self.errors = []
        self.tokens = []
        self.messages = []

        if not entry:
            self.messages.append((False, "No input provided.", []))
            return

        self.relative_tokens = []
        self.stored_tokens = []

        # First: itemtype
        itemtype = entry[0]
        if itemtype not in {"*", "~", "^", "%", "+", "?"}:
            self.messages.append(
                (
                    False,
                    f"Invalid itemtype '{itemtype}' (expected *, ~, ^, %, + or ?)",
                    [],
                )
            )
            return

        self.relative_tokens.append(
            {"token": itemtype, "s": 0, "e": 1, "t": "itemtype"}
        )
        self.itemtype = itemtype

        rest = entry[1:].lstrip()
        offset = 1 + len(entry[1:]) - len(rest)

        # Find start of first @-key to get subject
        at_pos = rest.find("@")
        subject = rest[:at_pos].strip() if at_pos != -1 else rest
        if subject:
            start = offset
            end = offset + len(subject) + 1  # trailing space
            subject_token = subject + " "
            self.relative_tokens.append(
                {"token": subject_token, "s": start, "e": end, "t": "subject"}
            )
            self.subject = subject
        else:
            self.errors.append("Missing subject")

        remainder = rest[len(subject) :]

        # Token pattern that keeps @ and & together - this one courtesy of
        # ChatGPT and nothing short of magic
        # pattern = (
        #     r"(?:(?<=^)|(?<=\s))(@[\w~+\-]+ [^@&\n]+)|(?:(?<=^)|(?<=\s))(&\w+ [^@&\n]+)"
        # )
        pattern = (
            r"(?:(?<=^)|(?<=\s))(@[\w~+\-]+ [^@&]+)|(?:(?<=^)|(?<=\s))(&\w+ [^@&]+)"
        )
        # pattern = r"@[^@]+(?:\s&[^@]+)*(?=(?:\s@|$))"
        for match in re.finditer(pattern, remainder):
            token = match.group(0)
            start_pos = match.start() + offset + len(subject)
            end_pos = match.end() + offset + len(subject)

            token_type = "@" if token.startswith("@") else "&"
            key = token[1:3].strip()
            self.relative_tokens.append(
                {
                    "token": token,
                    "s": start_pos,
                    "e": end_pos,
                    "t": token_type,
                    "k": key,
                }
            )

        # Detect and append a potential partial token at the end
        partial_token = None
        if entry.endswith("@") or re.search(r"@([a-zA-Z])$", entry):
            match = re.search(r"@([a-zA-Z]?)$", entry)
            if match:
                partial_token = {
                    "token": "@" + match.group(1),
                    "s": len(entry) - len(match.group(0)),
                    "e": len(entry),
                    "t": "@",
                    "k": match.group(1),
                    "incomplete": True,
                }

        elif entry.endswith("&") or re.search(r"&([a-zA-Z]+)$", entry):
            match = re.search(r"&([a-zA-Z]*)$", entry)
            if match:
                # Optionally find parent group (r or j)
                parent = None
                for tok in reversed(self.relative_tokens):
                    if tok["t"] == "@" and tok["k"] in ["r", "~"]:
                        parent = tok["k"]
                        break
                partial_token = {
                    "token": "&" + match.group(1),
                    "s": len(entry) - len(match.group(0)),
                    "e": len(entry),
                    "t": "&",
                    "k": match.group(1),
                    "parent": parent,
                    "incomplete": True,
                }

        if partial_token:
            self.relative_tokens.append(partial_token)

    def _parse_tokens(self, entry: str):
        if not self.previous_entry:
            self._parse_all_tokens()
            return

        self.mark_grouped_tokens()

        changes = self._find_changes(self.previous_entry, entry)
        affected_tokens = self._identify_affected_tokens(changes)

        dispatched_anchors = set()

        for token in affected_tokens:
            start_pos, end_pos = token["s"], token["e"]
            if not self._token_has_changed(token):
                continue

            if (start_pos, end_pos) in self.skip_token_positions:
                continue  # don't dispatch grouped & tokens alone

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
            else:
                token_type = token["k"]
                self._dispatch_token(token, start_pos, end_pos, token_type)

    def _parse_all_tokens(self):
        self.mark_grouped_tokens()

        dispatched_anchors = set()
        self.stored_tokens = []

        for token in self.relative_tokens:
            # print(f"parsing {token = }")
            start_pos, end_pos = token["s"], token["e"]
            if token.get("k", "") in ["+", "-", "s", "f"]:
                log_msg(f"identified @+ {token = }")
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

    def _find_changes(self, previous: str, current: str):
        # Find the range of changes between the previous and current strings
        start = 0
        while (
            start < len(previous)
            and start < len(current)
            and previous[start] == current[start]
        ):
            start += 1

        end_prev = len(previous)
        end_curr = len(current)

        while (
            end_prev > start
            and end_curr > start
            and previous[end_prev - 1] == current[end_curr - 1]
        ):
            end_prev -= 1
            end_curr -= 1

        return start, end_curr

    def _identify_affected_tokens(self, changes):
        start, end = changes
        affected_tokens = []
        for token in self.relative_tokens:
            start_pos, end_pos = token["s"], token["e"]
            if start <= end_pos and end >= start_pos:
                affected_tokens.append(token)
        return affected_tokens

    def _token_has_changed(self, token):
        return token not in self.previous_tokens

    def _dispatch_token(self, token, start_pos, end_pos, token_type):
        log_msg(f"dispatch_token {token = }")
        if token_type in self.token_keys:
            method_name = self.token_keys[token_type][2]
            method = getattr(self, method_name)
            # log_msg(f"{method_name = } returned {method = }")
            is_valid, result, sub_tokens = method(token)
            log_msg(f"{is_valid = }, {result = }, {sub_tokens = }")
            if is_valid:
                self.parse_ok = is_valid
                # if token_type == "r":
                #     log_msg(
                #         f"appending {result = } to self.rrules, dispatching {sub_tokens = } in {self.entry = }"
                #     )
                #     self.rrules.append(result)
                #     self._dispatch_sub_tokens(sub_tokens, "r")
                # elif token_type == "~":
                #     log_msg(
                #         f"appending {result = } to self.jobset, dispatching {sub_tokens = } in {self.entry = }"
                #     )
                #     self.jobset.append(result)
                #     log_msg(f"dispatching {sub_tokens = } in {self.entry = }")
                #     ok, res, toks = self._dispatch_sub_tokens(sub_tokens, "~")
            else:
                self.parse_ok = False
                log_msg(f"Error processing '{token_type}': {result}")
        else:
            self.parse_ok = False
            log_msg(f"No handler for token: {token}")

    # def _dispatch_sub_tokens(self, sub_tokens, prefix):
    #     log_msg(f"dispatch_sub_tokens {sub_tokens = }, {prefix = }")
    #     return True, "", []
    #     if not sub_tokens:
    #         return True, "", []
    #     for part in sub_tokens:
    #         if part.startswith("&"):
    #             token_type = prefix + part[1:2]  # Prepend prefix to token type
    #             token_value = part[2:].strip()
    #             if token_type in self.token_keys:
    #                 method_name = self.token_keys[token_type][2]
    #                 method = getattr(self, method_name)
    #                 is_valid, result, *sub_tokens = method(token_value)
    #                 if is_valid:
    #                     if prefix == "r":
    #                         self.rrule_tokens[-1][1][token_type] = result
    #                         self.rrule_parts.append(result)
    #                         log_msg(f"{self.rrule_parts = }")
    #                     elif prefix == "~":
    #                         self.job_tokens[-1][1][token_type] = result
    #                         log_msg(f"self.job_tokens = ")
    #                 else:
    #                     self.parse_ok = False
    #                     log_msg(f"Error processing sub-token '{token_type}': {result}")
    #                     return False, result, []
    #             else:
    #                 self.parse_ok = False
    #                 log_msg(f"No handler for sub-token: {token_type}")
    #                 return False, f"Invalid sub-token: {token_type}", []

    def _extract_job_node_and_summary(self, text):
        log_msg(f"{text = }")
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

    # def to_dict(self) -> dict:
    #     return {
    #         "itemtype": self.itemtype,
    #         "subject": self.subject,
    #         "description": self.description,
    #         "rruleset": self.rruleset,
    #         "timezone": self.tz_str,
    #         "extent": self.extent,
    #         "tags": self.tag_str,
    #         "alerts": self.alert_str,
    #         "context": self.context,
    #         "jobset": self.jobset,
    #         "priority": self.p,
    #     }

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
    def do_summary(cls, token):
        # Process subject token
        if "t" in token and token["t"] == "subject":
            return True, token["token"].strip(), []
        else:
            return False, "subject cannot be empty", []

    @classmethod
    def do_duration(cls, arg: str):
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

    def do_beginby(self, token):
        # Process datetime token
        beginby = re.sub("^@. ", "", token["token"].strip()).lower()

        ok, beginby_obj = timedelta_str_to_seconds(beginby)
        if ok:
            self.beginby = beginby
            return True, beginby_obj, []
        else:
            return False, beginby_obj, []

    def do_extent(self, token):
        # Process datetime token
        extent = re.sub("^[@&]. ", "", token["token"].strip()).lower()
        ok, extent_obj = timedelta_str_to_seconds(extent)
        log_msg(f"{token = }, {ok = }, {extent_obj = }")
        if ok:
            self.extent = extent
            return True, extent_obj, []
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

    def do_description(self, token):
        description = re.sub("^@. ", "", token["token"])
        log_msg(f"{token = }, {description = }")
        if not description:
            return False, "missing description", []
        if description:
            self.description = description
            # print(f"{self.description = }")
            return True, description, []
        else:
            return False, description, []

    def do_nothing(self, token):
        return True, "passed", []

    def do_tag(self, token):
        # Process datetime token
        tag = re.sub("^@. ", "", token["token"].strip())

        if tag:
            self.tags.append(tag)
            # print(f"{self.tags = }")
            return True, tag, []
        else:
            return False, tag, []

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
        # try:
        #     obj = tok_str
        #     rep = tok_str
        # except Exception:
        #     obj = None
        #     rep = f"invalid: {token}"
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

    def do_rrule(self, token):
        """
        Handle an @r ... group. `token` may be a token dict or the raw token string.
        This only validates / records RRULE components; RDATE/EXDATE are added later
        by finalize_rruleset().
        Returns (ok: bool, message: str, extras: list).
        """
        log_msg(f"in do_rrule: {token = }")

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

        log_msg(f"{self.rrule_tokens = } processing remaining tokens")
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

        log_msg(f"got {self.rrule_tokens = }")
        return (True, "", [])

    def do_s(self, token: dict):
        """
        Parse @s, honoring optional trailing 'z <tz>' directive inside the value.
        Updates self.dtstart_str and self.rdstart_str to seed recurrence.
        """
        try:
            raw = token["token"][2:].strip()
            if not raw:
                return False, "Missing @s value", []

            obj, kind, tz_used = self.parse_user_dt_for_s(raw)
            if kind == "error":
                return False, tz_used or f"Invalid @s value: {raw}", []

            userfmt = self.fmt_user(obj)

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

            self.dtstart = compact
            self.dtstart_str = (
                f"DTSTART:{compact}"
                if kind != "date"
                else f"DTSTART;VALUE=DATE:{compact}"
            )
            self.rdstart_str = f"RDATE:{compact}"

            return True, userfmt, []

        except Exception as e:
            return False, f"Invalid @s value: {e}", []

    def do_job(self, token):
        # Process journal token
        node, summary, tokens_remaining = self._extract_job_node_and_summary(
            token["token"]
        )
        log_msg(f"{token = }, {node = }, {summary = }, {tokens_remaining = }")
        job_params = {"~": summary}
        job_params["node"] = node
        log_msg(f"{self.job_tokens = }")

        return True, job_params, []

    def do_at(self):
        print("TODO: do_at() -> show available @ tokens")

    def do_amp(self):
        print("TODO: do_amp() -> show available & tokens")

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
            log_msg(f"returning False, {arg = }, {rep = }")
            return False, rep

        log_msg(f"returning True, {arg = }, {rep = },")
        return True, f"BYMINUTE={rep}"

    @classmethod
    def do_two_periods(cls, arg: List[str]) -> str:
        return True, "not implemented", []

    @classmethod
    def do_mask(cls, arg: str) -> str:
        return True, "not implemented", []

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
        except Exception:
            return None, None

    def _get_o_interval(self):
        """
        Return (timedelta, learn_bool) if @o present, else None.
        Expects self.over to hold the *original* @o string (e.g. '4d' or '~4d').
        """
        s = (self.over or "").strip()
        if not s:
            return None
        # FIXME: what about projects?
        learn = s.startswith("~")
        base = s[1:].strip() if learn else s
        ok, seconds = timedelta_str_to_seconds(base)
        if not ok:
            return None

        return (timedelta(seconds=seconds), learn)

    def _set_o_interval(self, td, learn: bool):
        """Write @o token back (e.g., '@o 4d3h ' or '@o ~4d3h ')."""
        # convert timedelta -> your TD string; use your existing helper if you have it
        seconds = int(td.total_seconds())
        # simple example: only days/hours; replace with your own formatter
        days, rem = divmod(seconds, 86400)
        hours, rem = divmod(rem, 3600)
        minutes = rem // 60
        parts = []
        if days:
            parts.append(f"{days}d")
        if hours:
            parts.append(f"{hours}h")
        if minutes:
            parts.append(f"{minutes}m")
        td_str = "".join(parts) or "0m"

        prefix = "~" if learn else ""
        new_token_text = f"@o {prefix}{td_str} "

        tok = next(
            (
                t
                for t in self.relative_tokens
                if t.get("t") == "@" and t.get("k") == "o"
            ),
            None,
        )
        if tok:
            tok["token"] = new_token_text
        else:
            self.relative_tokens.append({"token": new_token_text, "t": "@", "k": "o"})
        # keep original string field too, if you use it elsewhere
        self.over = f"{prefix}{td_str}"

    def _smooth_interval(
        self, old: timedelta, new: timedelta, weight: int
    ) -> timedelta:
        # (w*old + new)/(w+1)
        total = old * weight + new
        secs = total.total_seconds() / (weight + 1)
        return timedelta(seconds=secs)

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
        # bump @s (or create)
        for tok in self.relative_tokens:
            if tok.get("t") == "@" and tok.get("k") == "s":
                tok["token"] = f"@s {new_dtstart.strftime('%Y%m%dT%H%M')} "
                break
        else:
            self.relative_tokens.append(
                {
                    "token": f"@s {new_dtstart.strftime('%Y%m%dT%H%M')} ",
                    "t": "@",
                    "k": "s",
                }
            )

        # decrement &c if present
        for tok in list(self.relative_tokens):
            if tok.get("t") == "&" and tok.get("k") == "c":
                try:
                    parts = tok["token"].split()
                    if len(parts) >= 2 and parts[0] == "&c":
                        cnt = int(parts[1]) - 1
                        if cnt > 0:
                            tok["token"] = f"&c {cnt}"
                        else:
                            self.relative_tokens.remove(tok)  # drop when it hits 0
                except Exception:
                    pass
                break

        # rebuild rruleset / derived fields from tokens
        self._reparse_from_tokens()

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

    def do_rdate(self, token: str):
        """
        Process an RDATE token, e.g., "@+ 2024-07-03 14:00, 2024-08-05 09:00".
        Uses the global timezone (set via @z) for all entries, and serializes
        them using TZID (even for UTC).
        """
        log_msg(f"processing rdate {token = }")
        try:
            # Remove the "@+" prefix and extra whitespace
            # token_body = token.strip()[2:].strip()
            token_body = token["token"][2:].strip()

            # Split on commas to get individual date strings
            dt_strs = [s.strip() for s in token_body.split(",") if s.strip()]

            # Process each entry
            rdates = []
            udates = []
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
                    # print(f"added {dt_fmt = } to rdates")
                    rdates.append(dt_fmt)
                    udates.append(self.fmt_user(dt))

            self.rdstart_str = f"{self.rdstart_str},{','.join(rdates)}"
            self.rdates = rdates
            self.token_map["+"] = ", ".join(udates)
            # Prepend RDATE in finalize_rruleset after possible insertion of DTSTART
            log_msg(f"{rdates = }, {self.rdstart_str = }")
            return True, rdates, []
        except Exception as e:
            return False, f"Invalid @+ value: {e}", []

    def do_exdate(self, token: dict):
        """
        @- … : explicit exclusion dates
        - Maintain a de-duplicated list of compact dates in self.exdates.
        - finalize_rruleset() will emit EXDATE using this list in either path.
        """
        try:
            token_body = token["token"][2:].strip()
            dt_strs = [s.strip() for s in token_body.split(",") if s.strip()]

            if not hasattr(self, "exdates") or self.exdates is None:
                self.exdates = []

            new_ex = []
            udates = []
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
        # rrule_tokens = self.rrule_tokens
        log_msg(f"in finalize_rruleset {self.rrule_tokens = }")
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
                ok, res = dtstr_to_compact(value)
                value = res if ok else ""
            elif ", " in value:
                value = ",".join(value.split(", "))
            component = self.key_to_param.get(key, None)
            log_msg(f"components {key = }, {value = }, {component = }")
            if component:
                rrule_components[component] = value

        rrule_line = "RRULE:" + ";".join(
            f"{k}={v}" for k, v in rrule_components.items()
        )

        log_msg(f"{self.rrule_components = }")

        log_msg(f"{rrule_line = }")
        # Assemble lines safely
        lines: list[str] = []

        dtstart_str = getattr(self, "dtstart_str", "") or ""
        if dtstart_str:
            lines.append(dtstart_str)
            log_msg(f"appended dtstart_str: {lines = }")

        if rrule_line:
            lines.append(rrule_line)
            log_msg(f"appended rrule_line: {lines = }")
            # only add the rdates from @+, not @s since we have a rrule_line
            if self.rdates:
                lines.append(f"RDATE:{','.join(self.rdates)}")
                log_msg(f"appended RDATE + rdates: {lines = }")
        else:
            # here we need to include @s since we do not have a rrule_line
            rdstart_str = getattr(self, "rdstart_str", "") or ""
            if rdstart_str:
                lines.append(rdstart_str)
                log_msg(f"appended rdstart_str: {lines = }")

        exdate_str = getattr(self, "exdate_str", "") or ""
        if exdate_str:
            lines.append(f"EXDATE:{exdate_str}")
            log_msg(f"appended exdate_str: {lines = }")

        log_msg(f"RETURNING {lines = }")

        return "\n".join(lines)

    # def build_jobs(self):
    #     """
    #     Build self.jobset from @~ + &... token groups in self.relative_tokens.
    #     In the new explicit &r format:
    #     - parse &r for job id and immediate prereqs
    #     - keep job name
    #     """
    #     job_groups = self.collect_grouped_tokens({"~"})
    #     # print(f"{job_groups = }")
    #     job_entries = []
    #
    #     count = 0
    #     for group in job_groups:
    #         anchor = group[0]
    #         token_str = anchor["token"]
    #
    #         # get job name up to first &
    #         job_portion = token_str[3:].strip()
    #         split_index = job_portion.find("&")
    #         if split_index != -1:
    #             job_name = job_portion[:split_index].strip()
    #         else:
    #             job_name = job_portion
    #
    #         job = {"~": job_name}
    #         count += 1
    #
    #         # process &-keys
    #         for token in group[1:]:
    #             try:
    #                 k, v = token["token"][1:].split(maxsplit=1)
    #                 k = k.strip()
    #                 v = v.strip()
    #
    #                 if k == "r":
    #                     ok, primary, dependencies = self.do_requires(
    #                         {"token": f"&r {v}"}
    #                     )
    #                     if not ok:
    #                         self.errors.append(primary)
    #                         continue
    #                     job["i"] = primary
    #                     job["reqs"] = dependencies
    #                 elif k == "f":  # finished
    #                     log_msg(f"processing job finished for {v = }")
    #                     try:
    #                         dts = parse_pair(v)
    #                         log_msg(f"got {dts = } for {count = }")
    #                         job["f"] = ",".join([self.fmt_compact(dt) for dt in dts])
    #                         log_msg(f"{job['f'] = }")
    #                         log_msg(f"adding to {self.token_map = }")
    #                         self.token_map.setdefault("~f", {})
    #                         self.token_map["~f"][count] = ", ".join(
    #                             [self.fmt_user(dt) for dt in dts]
    #                         )
    #                         log_msg(f"added to {self.token_map = }")
    #                     except Exception as e:
    #                         log_msg(f"Error: {e = }")
    #                         job["f"] = v
    #                 else:
    #                     job[k] = v
    #             except Exception as e:
    #                 self.errors.append(
    #                     f"Failed to parse job metadata token: {token['token']} ({e})"
    #                 )
    #
    #         job_entries.append(job)
    #
    #     self.jobs = job_entries
    #     return job_entries

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

    # def finalize_jobs(self, jobs):
    #     """
    #     With jobs that have explicit ids and prereqs, build:
    #     - available jobs (no prereqs or prereqs finished)
    #     - waiting jobs (unmet prereqs)
    #     - finished jobs
    #     """
    #
    #     if not jobs:
    #         return False, "No jobs to process"
    #     if not self.parse_ok:
    #         return False, "Error parsing job tokens"
    #
    #     # map id -> job
    #     job_map = {job["i"]: job for job in jobs if "i" in job}
    #
    #     # determine finished
    #     finished = {job["i"] for job in jobs if "f" in job}
    #
    #     # build transitive prereqs
    #     all_prereqs = {}
    #     for job in jobs:
    #         if "i" not in job:
    #             continue
    #         i = job["i"]
    #         deps = set([j for j in job.get("reqs", []) if j not in finished])
    #
    #         transitive = set(deps)
    #         to_process = list(deps)
    #         while to_process:
    #             d = to_process.pop()
    #             if d in job_map:
    #                 subdeps = set(job_map[d].get("reqs", []))
    #                 for sd in subdeps:
    #                     if sd not in transitive:
    #                         transitive.add(sd)
    #                         to_process.append(sd)
    #         all_prereqs[i] = transitive
    #
    #     available = set()
    #     waiting = set()
    #     for i, reqs in all_prereqs.items():
    #         unmet = reqs - finished
    #         if unmet:
    #             waiting.add(i)
    #         elif i in finished:
    #             continue
    #         else:
    #             available.add(i)
    #
    #     for job in jobs:
    #         if "i" in job and job["i"] not in all_prereqs and job["i"] not in finished:
    #             available.add(job["i"])
    #
    #     blocking = {}
    #     for i in available:
    #         blocking[i] = len(waiting) / len(available) if available else 0.0
    #
    #     num_available = len(available)
    #     num_waiting = len(waiting)
    #     num_finished = len(finished)
    #
    #     task_subject = self.subject
    #     if len(task_subject) > 12:
    #         task_subject_display = task_subject[:10] + " …"
    #     else:
    #         task_subject_display = task_subject
    #
    #     final = []
    #     for job in jobs:
    #         if "i" not in job:
    #             continue
    #         i = job["i"]
    #         job["prereqs"] = sorted(all_prereqs.get(i, []))
    #         if i in available:
    #             job["status"] = "available"
    #             job["blocking"] = blocking[i]
    #         elif i in waiting:
    #             job["status"] = "waiting"
    #         elif i in finished:
    #             job["status"] = "finished"
    #             self.token_map.setdefault("~f", {})
    #             self.token_map["~f"][i] = self.fmt_user(parse_dt(job["f"]))
    #
    #         job["display_subject"] = (
    #             f"{job['~']} ∊ {task_subject_display} {num_available}/{num_waiting}/{num_finished}"
    #         )
    #         final.append(job)
    #
    #     self.jobset = json.dumps(final, cls=CustomJSONEncoder)
    #     self.jobs = final
    #
    #     # 🔑 unified injection of @f
    #     if len(finished) == len(job_map) and finished:
    #         finish_dts = [parse_dt(job["f"]) for job in jobs if "f" in job]
    #         if finish_dts:
    #             finished_dt = max(finish_dts)
    #             finished_tok = {
    #                 "token": f"@f {self.fmt_user(finished_dt)}",
    #                 "t": "@",
    #                 "k": "f",
    #             }
    #             self.add_token(finished_tok)
    #             self.has_f = True
    #         for job in jobs:
    #             job.pop("f", None)
    #
    #     return True, final

    def finalize_jobs(self, jobs):
        """
        Compute job status (finished / available / waiting)
        using new &r id: prereqs format and propagate @f if all are done.
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

        # annotate job objects
        for jid, job in job_map.items():
            if jid in finished:
                job["status"] = "finished"
            elif jid in available:
                job["status"] = "available"
            elif jid in waiting:
                job["status"] = "waiting"
            else:
                job["status"] = "standalone"

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
                tok = {
                    "token": f"@f {self.fmt_user(finished_dt)}",
                    "t": "@",
                    "k": "f",
                }
                self.add_token(tok)
                self.has_f = True

            for job in job_map.values():
                job.pop("f", None)

        # --- finalize ---
        self.jobs = list(job_map.values())
        self.jobset = json.dumps(self.jobs, cls=CustomJSONEncoder)
        return True, self.jobs

    # def do_completion(self, token, *, job_id: int | None = None):
    #     """
    #     Handle both:
    #     - @f <datetime>  (task-wide)  -> add (dt, None) to self.completions
    #     - &f <datetime>  (job-level)  -> add (dt, job_id) to self.completions
    #     """
    #     # Ensure store exists
    #     if not hasattr(self, "completions"):
    #         self.completions = []  # list[(datetime, job_id|None)]
    #
    #     # Dispatcher passes relative dict for @f and a raw string for &f
    #     if isinstance(token, dict):  # @f path
    #         body = token["token"][2:].strip()  # strip "@f"
    #         # dt = _parse_compact_dt(body) if body[:4].isdigit() else parse(body)
    #         parts = body.split(",")
    #         dts = []
    #         dt_objs = []
    #         msgs = []
    #         for part in parts:  # NOTE: there should be at most 2 parts
    #             try:
    #                 dt = parse(part)
    #                 dt_objs.append(dt)
    #                 dts.append(self.fmt_user(dt))
    #             except Exception as e:
    #                 msgs.append(f"Error parsing {part}: {e}")
    #         if msgs:
    #             log_msg(f"completion error {msgs = }")
    #             return False, ", ".join(msgs), []
    #         token["token"] = f"@f {', '.join(dts)}"
    #         token["t"] = "@"
    #         token["k"] = "f"
    #
    #         # dt = parse(body)
    #         # # normalize token text to compact
    #         # token["token"] = f"@f {dt.strftime('%Y%m%dT%H%M')} "
    #         # token["t"] = "@"
    #         # token["k"] = "f"
    #         # task-level completion
    #         self.completions.append(dt_objs)
    #         log_msg(f"adding {dts = } to token_map")
    #         # self.token_map["f"] = self.fmt_user(dt)
    #         self.has_f = True
    #         return True, token["token"], []
    #
    #     # &f path: token is the string after "&f "
    #     try:
    #         log_msg(f"processing completion for {job_id = }")
    #         body = str(token).strip()
    #         # dt = _parse_compact_dt(body) if body[:4].isdigit() else parse(body)
    #         dt = parse(body)
    #         self.completions.append((dt, job_id))
    #         log_msg(f"adding {dt = } to token_map for {job_id = }")
    #         log_msg(f"got here {self.token_map = }")
    #         self.token_map.setdefault("~f", {})
    #         log_msg(f"got here {self.token_map = }")
    #         self.token_map["~f"][job_id] = self.fmt_user(dt)
    #         log_msg(f"got here {self.token_map = }")
    #         # If you also mirror &f into tokens, you can return normalized text here,
    #         # but typically &f lives in jobs JSON, not the top-level tokens.
    #         return True, int(dt.timestamp()), []
    #     except Exception as e:
    #         log_msg(f"error: {e = }")
    #         return False, f"invalid &f datetime: {e}, {body = }", []

    def do_completion(self, token: dict | str, *, job_id: str | None = None):
        """
        Handle both:
        @f <datetime>[, <datetime>]  (task-level)
        &f <datetime>[, <datetime>]  (job-level)
        """
        if not hasattr(self, "completions"):
            self.completions = []  # list[(completed_dt, due_dt, job_id|None)]

        try:
            if isinstance(token, dict):  # task-level @f
                val = token["token"][2:].strip()
            else:  # job-level &f
                val = str(token).strip()

            completed, due = parse_completion_value(val)
            if not completed:
                return False, f"Invalid completion value: {val}", []

            self.completions.append((completed, due, job_id))

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

    # def _get_start_dt(self):
    #     """Parse the @s token to datetime (UTC naive or local—match your parser)."""
    #     tok = next(
    #         (
    #             t
    #             for t in self.relative_tokens
    #             if t.get("t") == "@" and t.get("k") == "s"
    #         ),
    #         None,
    #     )
    #     if not tok:
    #         return None
    #     s = tok["token"][2:].strip()  # after '@s'
    #
    #     return parse(s)

    def _get_start_dt(self) -> datetime | None:
        # return self.dtstart
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
        try:
            return parse(val)
        except Exception:
            return None

    def _set_start_dt(self, dt):
        """Replace or add an @s token; keep your formatting with trailing space."""
        ts = dt.strftime("%Y%m%dT%H%M")
        log_msg(f"starting {self.relative_tokens = }")
        tok = next(
            (
                t
                for t in self.relative_tokens  # TODO: self.tokens instead?
                if t.get("t") == "@" and t.get("k") == "s"
            ),
            None,
        )
        if tok:
            tok["token"] = f"@s {ts} "
            log_msg(f'{tok["token"] = }')
        else:
            self.relative_tokens.append({"token": f"@s {ts} ", "t": "@", "k": "s"})
        log_msg(f"ending {self.relative_tokens = }")

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
        self, t: str, k: str | None = None, *, max_count: int | None = None
    ) -> int:
        """
        Remove tokens from self.relative_tokens that match:
        token["t"] == t and (k is None or token["k"] == k)

        Args:
            t: primary token type (e.g., "@", "&", "itemtype")
            k: optional subtype (e.g., "f", "s", "r"). If None, match all with type t.
            max_count: remove at most this many; None = remove all matches.

        Returns:
            int: number of tokens removed.
        """
        if not hasattr(self, "relative_tokens") or not self.relative_tokens:
            return 0

        removed = 0
        new_tokens = []
        for tok in self.relative_tokens:
            match = (tok.get("t") == t) and (k is None or tok.get("k") == k)
            if match and (max_count is None or removed < max_count):
                removed += 1
                continue
            new_tokens.append(tok)

        self.relative_tokens = new_tokens

        # Keep self.completions consistent if we removed @f tokens
        if t == "@" and (k is None or k == "f"):
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

    def _get_o_interval(self) -> tuple[timedelta, bool] | None:
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
            normalized = f"@o {'~' if learn else ''}{td_to_td_str(td)} "
            token["token"] = normalized
            token["t"] = "@"
            token["k"] = "o"

            return True, int(td.total_seconds()), []
        except Exception as e:
            return False, f"invalid @o interval: {e}", []

    def finish(self) -> None:
        f_tokens = [t for t in self.relative_tokens if t.get("k") == "f"]
        if not f_tokens:
            return
        log_msg(f"{f_tokens = }")

        # completed_dt = max(parse_dt(t["token"].split(maxsplit=1)[1]) for t in f_tokens)
        completed_dt, was_due_dt = parse_f_token(f_tokens[0])

        due_dt = None  # default

        if offset_tok := next(
            (t for t in self.relative_tokens if t.get("k") == "o"), None
        ):
            due_dt = self._get_start_dt()
            td = td_str_to_td(offset_tok["token"].split(maxsplit=1)[1])
            self._replace_or_add_token("s", completed_dt + td)
            if offset_tok["token"].startswith("~") and due_dt:
                actual = completed_dt - due_dt
                td = self._smooth_interval(td, actual)
                offset_tok["token"] = f"@o {td_to_td_str(td)}"
                self._replace_or_add_token("s", completed_dt + td)

        elif self.rruleset:
            first, second = self._get_first_two_occurrences()
            due_dt = first
            if second:
                self._replace_or_add_token("s", second)
            else:
                self._remove_tokens({"s", "r", "+", "-"})
                self.itemtype = "x"

        else:
            # one-off
            due_dt = None
            self.itemtype = "x"

        # ⬇️ single assignment here
        self.completion = (completed_dt, due_dt)

        self._remove_tokens({"f"})
        self.reparse_finish_tokens()

    def _replace_or_add_token(self, key: str, dt: datetime) -> None:
        """Replace token with key `key` or add new one for dt."""
        new_tok = {"token": f"@{key} {self.fmt_user(dt)}", "t": "@", "k": key}
        # replace if exists
        for tok in self.relative_tokens:
            if tok.get("k") == key:
                log_msg(f"original {key =}; {tok = }; {new_tok = }")
                tok.update(new_tok)
                return
        # else append
        self.relative_tokens.append(new_tok)

    def _remove_tokens(self, keys: set[str]) -> None:
        """Remove tokens with matching keys from self.tokens."""
        self.relative_tokens = [
            t for t in self.relative_tokens if t.get("k") not in keys
        ]

    def reparse_finish_tokens(self) -> None:
        """
        Re-run only the token handlers that can be affected by finish():
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
        if self.parse_ok and self.final:
            self.finalize_record()

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
        log_msg(f"{resolve_relative = }")
        # self._normalize_datetime_tokens(resolve_relative=resolve_relative)
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
            log_msg(f"{tok = }")
            if tok.get("t") != "@":
                continue
            k = tok.get("k")
            text = (tok.get("token") or "").strip()
            if k == "s":
                body = text[2:].strip()
                log_msg(f"{body = }")
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

    # def _strip_positions(self, tokens_with_pos: list[dict]) -> list[dict]:
    #     """Remove 'start'/'end' from editing tokens to store as record tokens."""
    #     out = []
    #     for t in tokens_with_pos:
    #         t2 = dict(t)
    #         t2.pop("s", None)
    #         t2.pop("e", None)
    #         out.append(t2)
    #     return out

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
