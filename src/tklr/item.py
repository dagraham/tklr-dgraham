import re
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

from .shared import log_msg, print_msg
from .common import timedelta_str_to_seconds
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
    return dt.strftime("%Y%m%dT%H%M%S")


def _fmt_utc_Z(dt: datetime) -> str:
    # dt must be UTC-aware
    return dt.strftime("%Y%m%dT%H%M%SZ")


def _local_tzname() -> str:
    # string name is sometimes handy for UI/logging
    try:
        from tzlocal import get_localzone_name

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
    except Exception:
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


def parse(dt_str: str, zone: tzinfo = None) -> Union[date, datetime, str]:
    obj = parse_dt(dt_str)
    if isinstance(obj, date) and not isinstance(obj, datetime):
        return obj
    if (
        isinstance(obj, datetime)
        and obj.hour == 0
        and obj.minute == 0
        and obj.second == 0
    ):
        return obj.date()
    if isinstance(obj, datetime):
        if zone is None:
            return obj
        return obj.replace(tzinfo=zone)
    print(f"Error parsing {dt_str}")
    return f"Error: could not parse '{dt_str}'"


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


def get_local_zoneinfo():
    try:
        from zoneinfo import ZoneInfo
        import os

        tz_path = os.readlink("/etc/localtime")
        if "zoneinfo" in tz_path:
            return ZoneInfo(tz_path.split("zoneinfo/")[-1])
    except Exception:
        return None


def dt_to_dtstr(dt_obj: Union[datetime, date]) -> str:
    """Convert a datetime object to 'YYYYMMDDTHHMMSS' format."""
    if isinstance(dt_obj, date) and not isinstance(dt_obj, datetime):
        return dt_obj.strftime("%Y%m%d")
    return dt_obj.strftime("%Y%m%d%H%M%S")


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
    rule: Iterable[datetime], timezone: ZoneInfo, to_localtime: bool = False
):
    """
    Iterate over datetimes from a rule parsed by rrulestr.

    - If datetime is naive, attach the given timezone.
    - If to_localtime=True, also convert to the system local timezone.
    Yields timezone-aware datetime objects.
    """
    if timezone == "local":
        timezone = get_local_zoneinfo()
    for dt in rule:
        if dt.tzinfo is None:
            dt = dt.replace(
                tzinfo=timezone
            )  # Attach @z timezone without shifting wall clock
        if to_localtime and not is_date(dt):
            dt = as_timezone(dt, timezone)  # Convert to system local timezone
        yield dt


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
        timezone = get_local_zoneinfo()

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
common_methods = list("cdgilmnstuxz")

repeating_methods = list("o") + [
    "r",
    "rr",
    "rc",
    "rm",
    "rE",
    "rH",
    "ri",
    "rM",
    "rn",
    "rs",
    "ru",
    "rW",
    "rw",
]

datetime_methods = list("abe+-")

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
    "~",
    "t",
    # "jj",
    # "ji",
    # "js",
    # "jb",
    # "jp",
    "~a",
    # "jd",
    # "je",
    # "jf",
    # "jl",
    # "jm",
    # "ju",
]

wrap_methods = ["w"]

required = {"*": ["s"], "~": [], "^": ["~"], "%": [], "?": [], "+": []}

all_keys = common_methods + datetime_methods + job_methods + repeating_methods

allowed = {
    "*": common_methods + datetime_methods + repeating_methods + wrap_methods,
    "~": common_methods + datetime_methods + task_methods + repeating_methods,
    "+": common_methods + datetime_methods + task_methods,
    "^": common_methods + datetime_methods + job_methods + repeating_methods,
    "%": common_methods,
    "?": all_keys,
}


requires = {
    "a": ["s"],
    "b": ["s"],
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
    new_structured_tokens: list  # tokens to persist
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
        "o": ["over", "recurrence rule", "do_over"],
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
        "rm": ["months", "list of integers in 1 ... 12", "do_months"],
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
        "~e": ["extent", " timeperiod", "do_duration"],
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
            "timeperiod before task scheduled when job is scheduled",
            "do_duration",
        ],
        "~u": ["used time", "timeperiod: datetime", "do_usedtime"],
        "~?": ["job &-key", "enter &-key", "do_ampj"],
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
        M="BYMONTH",
        m="BYMONTHDAY",
        W="BYWEEKNO",
        w="BYDAY",
        h="BYHOUR",
        n="BYMINUTE",
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

        # --- environment / config ---
        self.env = env

        # --- core parse state ---
        self.entry = ""
        self.previous_entry = ""
        self.itemtype = ""
        self.subject = ""
        self.context = ""
        self.description = ""
        self.item = {}
        self.token_map = {}
        self.parse_ok = False
        self.parse_message = ""
        self.previous_tokens = []
        self.structured_tokens = []
        self.messages = []

        # --- schedule / tokens / jobs ---
        self.extent = ""
        self.rruleset = ""
        self.rrule_tokens = []
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

        # --- other flags / features ---
        self.completions = []

        # --- optional initial parse ---
        self.ampm = False
        self.yearfirst = True
        self.dayfirst = False
        if self.env:
            self.ampm = self.env.config.ui.ampm
            self.dayfirst = self.env.config.ui.dayfirst
            self.yearfirst = self.env.config.ui.yearfirst
        # print(f"{self.ampm = }, {self.yearfirst = }, {self.dayfirst = }")

        if raw:
            self.entry = raw
            self.parse_input(raw)

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
        print(f"{core = }, {zdir = }")

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
        if (zdir or "").lower() == "none":
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

    def parse_input(self, entry: str):
        """
        Parses the input string to extract tokens, then processes and validates the tokens.
        """
        digits = "1234567890" * ceil(len(entry) / 10)
        self._tokenize(entry)

        message = self.validate()
        if message:
            self.parse_ok = False
            self.parse_message = message
            print(f"parse failed: {message = }")
            return

        self.mark_grouped_tokens()
        # print("calling parse_tokens")
        self._parse_tokens(entry)

        self.parse_ok = True
        self.previous_entry = entry
        self.previous_tokens = self.structured_tokens.copy()

        # Build rruleset if @r group exists
        if self.collect_grouped_tokens({"r"}):
            # log_msg(f"building rruleset {self.item = }")
            rruleset = self.build_rruleset()
            log_msg(f"{rruleset = }")
            if rruleset:
                self.item["rruleset"] = rruleset
        elif self.rdstart_str is not None:
            # @s but not @r
            self.item["rruleset"] = f"{self.rdstart_str}"

        # Only build jobs if @~ group exists
        if self.collect_grouped_tokens({"~"}):
            jobset = self.build_jobs()
            success, finalized = self.finalize_jobs(jobset)

        if "s" in self.item and "z" not in self.item:
            self.timezone = local_timezone

        self.itemtype = self.item.get("itemtype", "")
        self.subject = self.item.get("subject", "")
        # priority = self.item.get("priority", None)
        self.rruleset = self.item.get("rruleset", "")

        if self.tags:
            # self.tag_str = "; ".join(self.tags)
            self.item["t"] = self.tags
            print(f"{self.tags = }")
        if self.alerts:
            # self.alert_str = "; ".join(self.alerts)
            self.item["a"] = self.alerts
            print(f"{self.alerts = }")

    def validate(self):
        if len(self.structured_tokens) < 2:
            # nothing to validate without itemtype and subject
            return

        def fmt_error(message: str):
            return [x.strip() for x in message.split(",")]

        errors = []

        itemtype = self.structured_tokens[0]["token"]
        subject = self.structured_tokens[1]["token"]
        allowed_fortype = allowed[itemtype]
        required_fortype = required[itemtype]

        current_atkey = None
        used_atkeys = []
        used_ampkeys = []
        needed = required_fortype
        count = 0
        # print(f"{len(self.structured_tokens) = }")
        for token in self.structured_tokens:
            count += 1
            if token.get("incomplete", False) == True:
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
                this_atkey = token["k"]
                if this_atkey not in all_keys:
                    return fmt_error(f"@{this_atkey}, Unrecognized @-key")
                if this_atkey not in allowed_fortype:
                    return fmt_error(
                        f"@{this_atkey}, The use of this @-key is not supported in type '{itemtype}' reminders"
                    )
                if this_atkey in used_atkeys and this_atkey not in multiple_allowed:
                    return fmt_error(
                        f"@{current_atkey}, Multiple instances of this @-key are not allowed"
                    )
                current_atkey = this_atkey
                used_atkeys.append(current_atkey)
                if this_atkey in ["r", "~"]:
                    # reset for this use
                    used_ampkeys = []
                if current_atkey in needed:
                    needed.remove(current_atkey)
                if current_atkey in requires:
                    for _key in requires[current_atkey]:
                        if _key not in used_atkeys and _key not in needed:
                            needed.append(_key)
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
                        f"&{current_ampkey}, Multiple instances of this &-key are not supported"
                    )
                used_ampkeys.append(this_ampkey)

        if needed:
            needed_keys = ", ".join("@" + k for k in needed)
            needed_msg = f"Required keys not yet provided: {needed_keys}"
        else:
            needed_msg = ""
        return needed_msg

    def collect_grouped_tokens(self, anchor_keys: set[str]) -> list[list[dict]]:
        """
        Collect multiple groups of @-tokens and their immediately trailing &-tokens.

        anchor_keys: e.g. {'r', '~', 's'} — only these @-keys start a group.

        Returns:
            List of token groups: each group is a list of structured tokens:
            [ [anchor_tok, &tok, &tok, ...], ... ]
        """
        groups: list[list[dict]] = []
        current_group: list[dict] = []
        collecting = False

        for token in self.structured_tokens:
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

        # IMPORTANT: include 's' so @s can carry grouped options like '&z'
        anchor_keys = {"r", "~", "s"}

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
        Keys are only present if that @-anchor appears in self.structured_tokens.
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
                except Exception:
                    v = ""
                pairs.append((k, v))
            if pairs:
                tgm.setdefault(akey, []).extend(pairs)

        self.token_group_map = tgm

    def _tokenize(self, entry: str):
        # print(f"_tokenize {entry = }")
        self.entry = entry
        self.errors = []
        self.tokens = []
        self.messages = []

        if not entry:
            self.messages.append((False, "No input provided.", []))
            return

        self.structured_tokens = []

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

        self.structured_tokens.append(
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
            self.structured_tokens.append(
                {"token": subject_token, "s": start, "e": end, "t": "subject"}
            )
            self.subject = subject
        else:
            self.errors.append("Missing subject")

        remainder = rest[len(subject) :]

        # Token pattern that keeps @ and & together
        pattern = r"(@[~\w\+\-]+ [^@&]+)|(&\w+ [^@&]+)"
        for match in re.finditer(pattern, remainder):
            token = match.group(0)
            start_pos = match.start() + offset + len(subject)
            end_pos = match.end() + offset + len(subject)

            token_type = "@" if token.startswith("@") else "&"
            key = token[1:3].strip()
            self.structured_tokens.append(
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
                for tok in reversed(self.structured_tokens):
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
            self.structured_tokens.append(partial_token)

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

        for token in self.structured_tokens:
            # print(f"parsing {token = }")
            start_pos, end_pos = token["s"], token["e"]
            if token.get("k", "") == "+":
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
        for token in self.structured_tokens:
            start_pos, end_pos = token["s"], token["e"]
            if start <= end_pos and end >= start_pos:
                affected_tokens.append(token)
        return affected_tokens

    def _token_has_changed(self, token):
        return token not in self.previous_tokens

    def _dispatch_token(self, token, start_pos, end_pos, token_type):
        if token_type in self.token_keys:
            method_name = self.token_keys[token_type][2]
            method = getattr(self, method_name)
            # log_msg(f"{method_name = } returned {method = }")
            is_valid, result, sub_tokens = method(token)
            if is_valid:
                if token_type == "r":
                    self.rrules.append(result)
                    self._dispatch_sub_tokens(sub_tokens, "r")
                elif token_type == "~":
                    self.jobset.append(result)
                    self._dispatch_sub_tokens(sub_tokens, "~")
                else:
                    self.item[token_type] = result
            else:
                self.parse_ok = False
                log_msg(f"Error processing '{token_type}': {result}")
        else:
            self.parse_ok = False
            log_msg(f"No handler for token: {token}")

    def _dispatch_sub_tokens(self, sub_tokens, prefix):
        for part in sub_tokens:
            if part.startswith("&"):
                token_type = prefix + part[1:2]  # Prepend prefix to token type
                token_value = part[2:].strip()
                if token_type in self.token_keys:
                    method_name = self.token_keys[token_type][2]
                    method = getattr(self, method_name)
                    is_valid, result, *sub_tokens = method(token_value)
                    if is_valid:
                        if prefix == "r":
                            self.rrule_tokens[-1][1][token_type] = result
                        elif prefix == "~":
                            self.job_tokens[-1][1][token_type] = result
                    else:
                        self.parse_ok = False
                        log_msg(f"Error processing sub-token '{token_type}': {result}")
                        return False, result, []
                else:
                    self.parse_ok = False
                    log_msg(f"No handler for sub-token: {token_type}")
                    return False, f"Invalid sub-token: {token_type}", []

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

    def to_dict(self) -> dict:
        return {
            "itemtype": self.itemtype,
            "subject": self.subject,
            "description": self.description,
            "rruleset": self.rruleset,
            "timezone": self.tz_str,
            "extent": self.extent,
            "tags": self.tag_str,
            "alerts": self.alert_str,
            "context": self.context,
            "jobset": self.jobset,
            "priority": self.p,
        }

    @classmethod
    def from_dict(cls, data: dict):
        # Reconstruct the entry string from tokens
        entry_str = " ".join(t["token"] for t in json.loads(data["structured_tokens"]))
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
        extent = re.sub("^@. ", "", token["token"].strip()).lower()
        ok, extent_obj = timedelta_str_to_seconds(extent)
        if ok:
            self.extent = extent
            return True, extent_obj, []
        else:
            return False, extent_obj, []

    def do_over(self, token):
        # Process datetime token
        over = re.sub("^@. ", "", token["token"].strip()).lower()
        ok, over_obj = timedelta_str_to_seconds(over)
        if ok:
            self.over = over
            return True, over_obj, []
        else:
            return False, over_obj, []

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
        if not description:
            return False, "missing description", []
        if description:
            self.description = description
            # print(f"{self.description = }")
            return True, description, []
        else:
            return False, description, []

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
                except Exception:
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
                except Exception:
                    all_ok = False
                    rep_lst.append(f"~{arg}~")
            obj = obj_lst if all_ok else None
            rep = ", ".join(rep_lst)
        return obj, rep

    def do_string(self, token):
        try:
            obj = re.sub("^@. ", "", token.strip())
            rep = obj
        except Exception:
            obj = None
            rep = f"invalid: {token}"
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
            print(f"{self.timezone = } {tz_str = }, {self.timezone.key = }")
            return True, self.timezone, []
        except Exception:
            self.timezone = None
            self.tz_str = ""
            return False, f"Invalid timezone: '{tz_str}'", []

    def do_rrule(self, token):
        """
        Handle an @r ... group. `token` may be a token dict or the raw token string.
        This only validates / records RRULE components; RDATE/EXDATE are added later
        by build_rruleset().
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
            {"token": f"&FREQ {self.freq_map[freq_code]}", "t": "&", "k": "FREQ"}
        )

        # Parse following &-tokens in this @r group (e.g., &i 3, &c 10, &u 20250101, &m..., &w..., &d...)
        for t in group[1:]:
            tstr = t.get("token", "")
            try:
                key, value = tstr[1:].split(maxsplit=1)  # strip leading '&'
                key = key.upper().strip()
                value = value.strip()
            except Exception:
                continue

            self.rrule_tokens.append({"token": tstr, "t": "&", "k": key, "v": value})

        return (True, "", [])

    def do_s(self, token: dict):
        """
        Parse @s, honoring optional trailing 'z <tz>' directive inside the value.
        """
        try:
            raw = token["token"][2:].strip()
            if not raw:
                return False, "Missing @s value", []

            obj, kind, tz_used = self.parse_user_dt_for_s(raw)
            print(f"{raw = }, {obj = }, {kind = }, {tz_used = }")
            if kind == "error":
                # tz_used holds an error message in this case
                return False, tz_used or "Invalid @s value", []

            if kind == "date":
                compact = self._serialize_date(obj)  # 'YYYYMMDD'
                self.token_map["s"] = compact
                self.s_kind = "date"
                self.s_tz = None
                self.dtstart = compact
                self.dtstart_str = f"DTSTART;VALUE=DATE:{compact}"
                self.rdstart_str = f"RDATE:{compact}"
            elif kind == "naive":
                compact = self._serialize_naive_dt(obj)  # 'YYYYMMDDTHHMMSS'
                self.token_map["s"] = compact
                self.s_kind = "naive"
                self.s_tz = None
                self.dtstart = compact
                self.dtstart_str = f"DTSTART:{compact}"
                self.rdstart_str = f"RDATE:{compact}"  # seed for single / no-@r
            else:  # 'aware'
                compact = self._serialize_aware_dt(obj, tz_used)  # 'YYYYMMDDTHHMMSSZ'
                self.token_map["s"] = compact
                self.s_kind = "aware"
                self.s_tz = tz_used  # '' == local
                self.dtstart = compact
                self.dtstart_str = f"DTSTART:{compact}"
                self.rdstart_str = f"RDATE:{compact}"  # seed for single / no-@r

            # reflect serialized form back into the visible token text
            print(
                f"do_s({raw}) returning {compact = }, {self.dtstart_str = }, {self.rdstart_str = }"
            )
            return True, compact, []

        except Exception as e:
            print(f"exception {e}")
            return False, f"Invalid @s value: {e}", []

    def do_job(self, token):
        # Process journal token
        node, summary, tokens_remaining = self._extract_job_node_and_summary(
            token["token"]
        )
        job_params = {"~": summary}
        job_params["node"] = node
        sub_tokens = []
        if tokens_remaining is not None:
            parts = self._sub_tokenize(tokens_remaining)

            for part in parts:
                key, *value = part
                k = key[1]
                v = " ".join(value)
                job_params[k] = v

            # Collect & tokens that follow @~
            sub_tokens = self._extract_sub_tokens(token, "&")
            self.job_tokens.append((token, job_params))
        return True, job_params, sub_tokens

    def _extract_sub_tokens(self, token, delimiter):
        # Use regex to extract sub-tokens
        pattern = rf"({delimiter}\w+ \S+)"
        matches = re.findall(pattern, token)
        return matches

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
            return False, rep

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

    def finish(
        self,
        completed_dt: datetime,
        *,
        history_weight: int = 3,  # for @o ~TD learning
        now: Optional[datetime] = None,
    ) -> FinishResult:
        """
        Finish the 'current' occurrence of this task and advance schedule if needed.
        Returns updated tokens/rruleset + which due_ts was completed + final flag.
        """
        now = now or completed_dt

        # 1) Resolve due_ts (the occurrence we are finishing)
        # Prefer @s if present; otherwise read from rruleset / @+ / RRULE.
        due_ts, second_ts = self._get_first_two_occurrences(now)

        # If no due_ts and no schedule at all, treat as single-shot.
        if due_ts is None:
            # No schedule: record completion with due=None and mark final.
            return FinishResult(
                new_structured_tokens=self.structured_tokens,
                new_rruleset=self.rruleset or "",
                due_ts_used=None,
                finished_final=True,
            )

        # 2) Handle @o first (fixed or learn)
        o_interval = (
            self._get_o_interval()
        )  # returns (td: timedelta, learn: bool) or None
        if o_interval:
            td, learn = o_interval
            # The “due” we finished is the current @s:
            current_s = self._get_start_dt()  # from @s token → datetime
            if not current_s:
                # Safety: if @o exists but @s is missing, treat as single-shot.
                return FinishResult(
                    self.structured_tokens, self.rruleset or "", due_ts, True
                )

            if learn:
                # new_interval = completed - prev_completion_start
                # prev_completion_start is inferred as current_s - old_estimate (your spec)
                prev_start = current_s - td
                new_interval = completed_dt - prev_start
                # Smooth with history_weight
                new_td = self._smooth_interval(
                    old=td, new=new_interval, weight=history_weight
                )
                # Update tokens: replace @o ~TD with @o new_td; move @s to completed_dt + new_td
                self._set_o_interval(new_td, learn=True)
                self._set_start_dt(completed_dt + new_td)
            else:
                # Fixed interval: just bump @s by td
                self._set_start_dt(current_s + td)

            return FinishResult(
                new_structured_tokens=self.structured_tokens,
                new_rruleset=self.rruleset or "",
                due_ts_used=int(due_ts.timestamp()),
                finished_final=False,
            )

        # 3) Handle rruleset flavors
        #    (a) RDATE-only; (b) RDATE list with EXDATE; (c) DTSTART+RRULE[;COUNT|UNTIL]
        if self._is_rdate_only():
            # Drop the first RDATE; if none left → final
            left = self._drop_first_rdate(due_ts)
            return FinishResult(
                new_structured_tokens=self._sync_tokens_from_rruleset(),
                new_rruleset=self.rruleset if left else "",
                due_ts_used=int(due_ts.timestamp()),
                finished_final=(not left),
            )

        if self._has_rrule():
            # Your earlier spec: advance DTSTART to the next occurrence; adjust COUNT if present.
            if second_ts is None:
                # No next → clear rruleset, final
                self._clear_schedule()
                return FinishResult(
                    new_structured_tokens=self.structured_tokens,
                    new_rruleset="",
                    due_ts_used=int(due_ts.timestamp()),
                    finished_final=True,
                )
            else:
                self._advance_dtstart_and_decrement_count(second_ts)
                return FinishResult(
                    new_structured_tokens=self.structured_tokens,
                    new_rruleset=self.rruleset,
                    due_ts_used=int(due_ts.timestamp()),
                    finished_final=False,
                )

        # 4) Fallback: schedule present but not recognized → mark as single-shot
        return FinishResult(
            new_structured_tokens=self.structured_tokens,
            new_rruleset=self.rruleset or "",
            due_ts_used=int(due_ts.timestamp()),
            finished_final=True,
        )

    # ---- helpers you implement with your existing token machinery ----

    def _get_first_two_occurrences(
        self, now: datetime
    ) -> Tuple[datetime | None, datetime | None]:
        """
        Return (first, second) occurrences to drive finish & advance logic.
        Use @s if present; else parse rruleset via rrulestr (respect RDATE/EXDATE/DTSTART/COUNT).
        IMPORTANT per your spec: if the first is past due, *still* return it as first,
        and the second (even if also past) as second.
        """
        # If @s present, first := @s; second := next per @o or rruleset; if neither → None
        s = self._get_start_dt()
        if s:
            # Derive a “second” by checking @o, or from rruleset if it exists, otherwise None
            # This keeps @s-based tasks consistent with your behavior.
            rs = rrulestr(self.rruleset) if (self.rruleset or "").strip() else None
            second = None
            if rs:
                # iterate sorted until you find > s; if exists, that's second
                gen = list(rs)  # your strings are typically small; OK to list
                gen = [d for d in gen if d > s]
                second = gen[0] if gen else None
            return s, second

        if self.rruleset and self.rruleset.strip():
            rs = rrulestr(self.rruleset)
            # We want first & second regardless of 'now' (per your last message)
            # Easiest is to enumerate 2 values from the generator:
            seq = list(rs)
            if not seq:
                return None, None
            if len(seq) == 1:
                return seq[0], None
            return seq[0], seq[1]

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
        from datetime import timedelta

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
                for t in self.structured_tokens
                if t.get("t") == "@" and t.get("k") == "o"
            ),
            None,
        )
        if tok:
            tok["token"] = new_token_text
        else:
            self.structured_tokens.append({"token": new_token_text, "t": "@", "k": "o"})
        # keep original string field too, if you use it elsewhere
        self.over = f"{prefix}{td_str}"

    def _smooth_interval(
        self, old: timedelta, new: timedelta, weight: int
    ) -> timedelta:
        # (w*old + new)/(w+1)
        total = old * weight + new
        secs = total.total_seconds() / (weight + 1)
        return timedelta(seconds=secs)

    def _get_start_dt(self):
        """Parse the @s token to datetime (UTC naive or local—match your parser)."""
        tok = next(
            (
                t
                for t in self.structured_tokens
                if t.get("t") == "@" and t.get("k") == "s"
            ),
            None,
        )
        if not tok:
            return None
        s = tok["token"][2:].strip()  # after '@s'
        from dateutil.parser import parse

        return parse(s)

    def _set_start_dt(self, dt):
        """Replace or add an @s token; keep your formatting with trailing space."""
        ts = dt.strftime("%Y%m%dT%H%M%S")
        tok = next(
            (
                t
                for t in self.structured_tokens
                if t.get("t") == "@" and t.get("k") == "s"
            ),
            None,
        )
        if tok:
            tok["token"] = f"@s {ts} "
        else:
            self.structured_tokens.append({"token": f"@s {ts} ", "t": "@", "k": "s"})

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
            ex_str = first_dt.strftime("%Y%m%dT%H%M%S")  # datetime

        self.structured_tokens.append({"token": f"@- {ex_str} ", "t": "@", "k": "-"})

        # 2) re-parse to regenerate rruleset/derived fields consistently
        self._reparse_from_tokens()

        # 3) decide if anything remains (any RDATE not excluded)
        #    Quick check: do we still have any @+ token with a date/datetime != ex_str?
        remaining = False
        for tok in self.structured_tokens:
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
        for tok in self.structured_tokens:
            if tok.get("t") == "@" and tok.get("k") == "s":
                tok["token"] = f"@s {new_dtstart.strftime('%Y%m%dT%H%M%S')} "
                break
        else:
            self.structured_tokens.append(
                {
                    "token": f"@s {new_dtstart.strftime('%Y%m%dT%H%M%S')} ",
                    "t": "@",
                    "k": "s",
                }
            )

        # decrement &c if present
        for tok in list(self.structured_tokens):
            if tok.get("t") == "&" and tok.get("k") == "c":
                try:
                    parts = tok["token"].split()
                    if len(parts) >= 2 and parts[0] == "&c":
                        cnt = int(parts[1]) - 1
                        if cnt > 0:
                            tok["token"] = f"&c {cnt}"
                        else:
                            self.structured_tokens.remove(tok)  # drop when it hits 0
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

        for tok in self.structured_tokens:
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

        self.structured_tokens = new_tokens
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

                if dt_fmt not in self.rdates:
                    # print(f"added {dt_fmt = } to rdates")
                    rdates.append(dt_fmt)
            self.rdstart_str = f"{self.rdstart_str},{','.join(rdates)}"
            self.rdates = rdates
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

            self.exdates.extend(new_ex)
            # convenience string if you ever need it
            self.exdate_str = ",".join(self.exdates) if self.exdates else ""

            return True, new_ex, []
        except Exception as e:
            return False, f"Invalid @- value: {e}", []

    def finalize_rruleset(self):
        """
        Build self.rruleset from current state, mirroring the old 'master' behavior:

        RRULE present (self.rrule_tokens truthy):
        • prepend self.dtstart_str (if set and well-formed)
        • for each rrule token, emit 'RRULE:...' line
        • append RDATE:self.rdate_str (if any explicit @+)
        • append EXDATE:self.exdate_str (if any explicit @-)
        • clear self.rrule_tokens/self.rdates/self.exdates to avoid duplicates

        No RRULE:
        • start with self.rdstart_str (seeded by do_s)
        • append RDATE:self.rdate_str if present
        """

        components: list[str] = []
        print(f"{self.dtstart_str = }, {self.rdstart_str = }")
        # --- RRULE path ---
        if self.rrule_tokens:
            # put dtstart_str first if possible
            if self.dtstart_str:
                components.append(self.dtstart_str)

            # 2) RRULE lines from rrule_tokens (as in the original master code)
            for token in self.rrule_tokens:
                # token is typically (anchor_token, params_dict)
                _, rrule_params = token
                rule_parts = []

                freq = rrule_params.pop("FREQ", None)
                if freq:
                    rule_parts.append(f"RRULE:FREQ={freq}")

                # remaining params are already like "KEY=VALUE" or "KEY=V1,V2"
                for _, v in rrule_params.items():
                    if v:
                        rule_parts.append(str(v))

                # join with ';' -> RRULE:...
                if rule_parts:
                    components.append(";".join(rule_parts))

            # 3) RDATE / EXDATE from strings managed by do_rdate/do_exdate
            log_msg(f"{self.rdstart_str = }")
            if getattr(self, "rdstart_str", None):
                components.append(f"RDATE:{self.rdstart_str}")
            if getattr(self, "exdate_str", None):
                components.append(f"EXDATE:{self.exdate_str}")

            # Assemble + store
            rruleset_str = "\n".join(ln for ln in components if ln and ln != "None")
            self.item["rruleset"] = rruleset_str
            self.rruleset = rruleset_str

            # Prevent double-append in subsequent calls (matches master)
            self.rrule_tokens = []
            self.rdates = []
            self.exdates = []
            return True, rruleset_str

        # --- RDATE-only path ---

        # Start with the seed created by do_s()
        components.append(self.rdstart_str)

        # Then explicit @+ (if any)
        if getattr(self, "rdate_str", None):
            components.append(f"RDATE:{self.rdate_str}")

        rruleset_str = "\n".join(ln for ln in components if ln and ln != "None")
        self.item["rruleset"] = rruleset_str
        self.rruleset = rruleset_str
        return True, rruleset_str

    def collect_rruleset_tokens(self):
        """Return the list of structured tokens used for building the rruleset."""
        rruleset_tokens = []
        found_rrule = False

        for token in self.structured_tokens:
            if not found_rrule:
                if token["t"] == "@" and token["k"] == "r":
                    found_rrule = True
                    rruleset_tokens.append(token)  # structured token
            else:
                if token["t"] == "&":
                    rruleset_tokens.append(token)  # structured token
                else:
                    break  # stop collecting on first non-& after @r

        return rruleset_tokens

    def build_rruleset(self) -> str:
        """
        Build an rruleset string using self.structured_tokens and self.dtstart_str.
        Emits:
        - DTSTART (if present)
        - RRULE:...
        - RDATE:...   (from your rdstart_str or rdate_str)
        - EXDATE:...  (if you track it)
        """
        rrule_tokens = self.collect_rruleset_tokens()
        if not rrule_tokens or not rrule_tokens[0]["token"].startswith("@r"):
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
                continue
            key = key.upper().strip()
            value = value.strip()
            if key == "M":
                rrule_components["BYMONTH"] = value
            elif key == "W":
                rrule_components["BYDAY"] = value
            elif key == "D":
                rrule_components["BYMONTHDAY"] = value
            elif key == "I":
                rrule_components["INTERVAL"] = value
            elif key == "U":
                rrule_components["UNTIL"] = value.replace("/", "")
            elif key == "C":
                rrule_components["COUNT"] = value

        rrule_line = "RRULE:" + ";".join(
            f"{k}={v}" for k, v in rrule_components.items()
        )

        # Assemble lines safely
        lines: list[str] = []

        dtstart_str = getattr(self, "dtstart_str", "") or ""
        if dtstart_str:
            lines.append(dtstart_str)

        if rrule_line:
            lines.append(rrule_line)

        # If you keep plus-dates inside rdstart_str, append it here.
        # (If you also track self.rdate_str and/or self.exdate_str separately,
        #  prefer to append those explicit lines here instead.)
        rdstart_str = getattr(self, "rdstart_str", "") or ""
        if rdstart_str:
            lines.append(rdstart_str)

        # Optional: include EXDATE if you’re storing it separately
        exdate_str = getattr(self, "exdate_str", "") or ""
        if exdate_str:
            lines.append(f"EXDATE:{exdate_str}")

        return "\n".join(lines)

    def build_jobs(self):
        """
        Build self.jobset from @~ + &... token groups in self.structured_tokens.
        In the new explicit &r format:
        - parse &r for job id and immediate prereqs
        - keep job name
        """
        job_groups = self.collect_grouped_tokens({"~"})
        # print(f"{job_groups = }")
        job_entries = []

        for group in job_groups:
            anchor = group[0]
            token_str = anchor["token"]

            # get job name up to first &
            job_portion = token_str[3:].strip()
            split_index = job_portion.find("&")
            if split_index != -1:
                job_name = job_portion[:split_index].strip()
            else:
                job_name = job_portion

            job = {"~": job_name}

            # process &-keys
            for token in group[1:]:
                try:
                    k, v = token["token"][1:].split(maxsplit=1)
                    k = k.strip()
                    v = v.strip()

                    if k == "r":
                        ok, primary, dependencies = self.do_requires(
                            {"token": f"&r {v}"}
                        )
                        if not ok:
                            self.errors.append(primary)
                            continue
                        job["i"] = primary
                        job["reqs"] = dependencies
                    elif k == "f":  # finished
                        try:
                            dt = parse(v)
                            job["f"] = round(dt.timestamp())
                        except Exception:
                            job["f"] = v
                    else:
                        job[k] = v
                except Exception as e:
                    self.errors.append(
                        f"Failed to parse job metadata token: {token['token']} ({e})"
                    )

            job_entries.append(job)

        self.jobs = job_entries
        print(f"{self.jobs = }")
        return job_entries

    def finalize_jobs(self, jobs):
        """
        With jobs that have explicit ids and prereqs, build:
        - available jobs (no prereqs or prereqs finished)
        - waiting jobs (unmet prereqs)
        - finished jobs
        """
        if not jobs:
            return False, "No jobs to process"
        if not self.parse_ok:
            return False, "Error parsing job tokens"

        # map id -> job
        job_map = {job["i"]: job for job in jobs if "i" in job}

        # determine finished
        finished = {job["i"] for job in jobs if "f" in job}

        # build transitive prereqs
        all_prereqs = {}
        for job in jobs:
            if "i" not in job:
                continue
            i = job["i"]
            # only include unfinished jobs in deps
            deps = set([j for j in job.get("reqs", []) if j not in finished])

            # transitively expand:
            transitive = set(deps)
            to_process = list(deps)
            while to_process:
                d = to_process.pop()
                if d in job_map:
                    subdeps = set(job_map[d].get("reqs", []))
                    for sd in subdeps:
                        if sd not in transitive:
                            transitive.add(sd)
                            to_process.append(sd)
            all_prereqs[i] = transitive

        available = set()
        waiting = set()
        for i, reqs in all_prereqs.items():
            unmet = reqs - finished
            # print(f"{reqs = }, {finished = } => {unmet = }")
            if unmet:
                waiting.add(i)
            elif i in finished:
                continue
            else:
                available.add(i)

        # jobs with no prereqs:
        for job in jobs:
            if "i" in job and job["i"] not in all_prereqs and job["i"] not in finished:
                available.add(job["i"])

        # print(f"{available = }")
        # annotate jobs
        blocking = {}
        for i in available:
            blocking[i] = len(waiting) / len(available)
            # blocking[i] = sum(1 for j in waiting if i in all_prereqs.get(j, set()))

        num_available = len(available)
        num_waiting = len(waiting)
        num_finished = len(finished)

        task_subject = self.item.get("subject", "")
        if len(task_subject) > 12:
            task_subject_display = task_subject[:10] + " …"
        else:
            task_subject_display = task_subject

        # finalize
        final = []
        for job in jobs:
            if "i" not in job:
                continue
            i = job["i"]
            job["prereqs"] = sorted(all_prereqs.get(i, []))
            if i in available:
                job["status"] = "available"
                job["blocking"] = blocking[i]
            elif i in waiting:
                job["status"] = "waiting"
            elif i in finished:
                job["status"] = "finished"

            job["display_subject"] = (
                f"{job['~']} ∊ {task_subject_display} {num_available}/{num_waiting}/{num_finished}"
            )

            final.append(job)
        if all_prereqs:
            self.item["all_prereqs"] = all_prereqs

        self.jobset = json.dumps(final, cls=CustomJSONEncoder)
        self.jobs = final
        self.item["jobs"] = self.jobset

        return True, final

    def do_completion(self, token):
        """
        Handle both:
        - @f <datetime>  (task-level)  -> store in self.completions and normalize token text
        - &f <datetime>  (job-level)   -> return integer timestamp for job metadata
        """
        # --- @f path: dispatcher passes a structured token dict ---
        if isinstance(token, dict):
            # token["token"] looks like "@f 2025-08-14 16:00"
            try:
                body = token["token"][2:].strip()
                dt = parse(body)
                normalized = f"@f {dt.strftime('%Y%m%dT%H%M%S')} "
                token["token"] = normalized
                token["t"] = "@"
                token["k"] = "f"
                # keep a record so finalize_completions() can advance schedules
                if not hasattr(self, "completions"):
                    self.completions = []
                self.completions.append(dt)
                return True, normalized, []
            except Exception as e:
                return False, f"invalid @f datetime: {e}", []

        # --- &f path: dispatcher passes the *string* after "&f " ---
        try:
            dt = parse(str(token).strip())
            # For job metadata we return an int timestamp; your build_jobs/finalize_jobs
            # will carry it through as job["f"] = <epoch-seconds>
            return True, round(dt.timestamp()), []
        except Exception as e:
            return False, f"invalid &f datetime: {e}", []

    def finalize_completions(self):
        """
        Apply the effect of the most recent completion(s) to scheduling tokens:
        - If @o is present: bump @s by interval; (optional) smoothing not shown here.
        - Else if RRULE present:
            - bump @s to next occurrence,
            - decrement &c if present (remove if it hits zero).
        - Else if only RDATE/EXDATE: append an @- for the completed dt.
        Removes processed @f tokens from structured_tokens.
        Leaves &f (job completions) in place (they drive job status).
        Recomputes rruleset afterwards via your existing finalize_rruleset().
        """
        if not self.completions and not self.jobs:  # FIXME: why skip other tasks?
            return  # nothing to do

        # We use the *latest* @f as the completion timestamp to apply.
        completed_dt = max(self.completions) if self.completions else None

        # Figure out what schedule we have
        has_rrule = any(
            tok.get("t") == "@" and tok.get("k") == "r"
            for tok in self.structured_tokens
        )
        has_s = self._find_token("@", "s") is not None
        # Treat "RDATE-only" if no @r, but we either have @+/@- or an rruleset string with only RDATE/EXDATE/DTSTART
        has_rdate_tokens = bool(self._find_all("@", "+") or self._find_all("@", "-"))

        # 1) If @o present, bump @s = completion + interval
        o_seconds = self.item.get(
            "o"
        )  # do_over returned seconds; you also keep self.over text
        if completed_dt and o_seconds is not None:
            self._ensure_start_token(completed_dt + timedelta(seconds=o_seconds))
            # (Optional: learning "~" smoothing could adjust o_seconds here.)
            # Remove @f tokens; completion has been applied
            self._remove_tokens("@", "f")
            # Rebuild strings from tokens
            self.finalize_rruleset()
            if self.collect_grouped_tokens({"~"}):  # project jobs present
                self.finalize_jobs(self.jobs)
            return

        # Build a temporary rruleset object from current tokens/strings to compute due/next.
        # Prefer the authoritative self.item['rruleset'] if already set, else try to build it.
        rule_str = self.item.get("rruleset", "")
        if not rule_str:
            ok, rs = self.finalize_rruleset()
            if ok:
                rule_str = rs

        due_dt = None
        next_dt = None
        if rule_str:
            try:
                rs = rrulestr(rule_str)
                # We want the first TWO occurrences in *sequence order* (even if past-due).
                # Safest: iterate a little; for bounded rules it's cheap.
                it = iter(rs)
                try:
                    due_dt = next(it)
                    next_dt = next(it, None)
                except StopIteration:
                    due_dt = None
                    next_dt = None
            except Exception:
                pass

        # 2) RRULE path
        if has_rrule:
            # No explicit completion time? Nothing to apply
            if not completed_dt:
                return
            # Advance DTSTART to the next occurrence (if any)
            if next_dt is not None:
                self._ensure_start_token(next_dt)
            else:
                # no more repeats: optional to remove @s
                s_tok = self._find_token("@", "s")
                if s_tok:
                    self.structured_tokens.remove(s_tok)

            # Decrement &c (if present)
            c_val = self._get_count_token_value()
            if c_val is not None:
                new_val = max(c_val - 1, 0)
                if new_val > 0:
                    self._set_count_token_value(new_val)
                else:
                    # remove &c when it hits zero
                    self._remove_tokens("&", "c")

            # Remove applied @f tokens
            self._remove_tokens("@", "f")

            # Rebuild
            self.finalize_rruleset()
            if self.collect_grouped_tokens({"~"}):
                self.finalize_jobs(self.jobs)
            return

        # 3) RDATE-only path (or no @r but @+/@- present)
        if completed_dt and (
            has_rdate_tokens
            or (rule_str and "RDATE" in rule_str and "RRULE" not in rule_str)
        ):
            # Append @- <completed> so this instance won’t reappear
            self.structured_tokens.append(
                {"token": f"@- {self._fmt_compact(completed_dt)} ", "t": "@", "k": "-"}
            )
            # Remove @f tokens
            self._remove_tokens("@", "f")
            # Rebuild
            self.finalize_rruleset()
            if self.collect_grouped_tokens({"~"}):
                self.finalize_jobs(self.jobs)
            return

        # 4) No schedule: single-shot — just clear @f (recording to Completions happens in DB layer)
        if completed_dt:
            self._remove_tokens("@", "f")

    def list_rrule(
        self,
        count: Union[None, int] = None,
        after: Union[datetime, None] = None,
        to_localtime: bool = False,
    ) -> List[datetime]:
        """
        Generate a list of localized instances from the rruleset stored in the item.

        Args:
            count: Optional number of instances to limit (e.g., next 10).
            after: Optional datetime to start after.
            to_localtime: Whether to convert instances to system local time.

        Returns:
            A list of localized datetime instances.
        """
        rule_string = self.item.get("rruleset")
        if not rule_string:
            return []
        is_date = "VALUE=DATE" in rule_string
        # fmt_str = "    %a %Y-%m-%d" if is_date else "    %a %Y-%m-%d %H:%M:%S %Z %z"
        print(f"list_rrule: {rule_string = }")
        rule = rrulestr(rule_string)

        timezone = (
            None if is_date else self.timezone
        )  # assuming you store ZoneInfo in self.timezone

        if after is None and count is None:
            # Default: return full localized list
            return localize_rule_instances(
                list(rule),
                timezone,
                to_localtime=to_localtime,
            )

        # Use the preview function for controlled output
        return preview_rule_instances(
            rule,
            timezone,
            count=count or 1000,
            after=after,
            to_localtime=to_localtime,
        )

    def _serialize_date(self, d: date) -> str:
        return d.strftime("%Y%m%d")

    def _serialize_naive_dt(self, dt: datetime) -> str:
        # ensure naive
        if dt.tzinfo is not None:
            dt = dt.replace(tzinfo=None)
        return dt.strftime("%Y%m%dT%H%M%S")

    def _serialize_aware_dt(self, dt: datetime, zone) -> str:
        # Attach or convert to `zone`, then to UTC and append Z
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=zone)
        else:
            dt = dt.astimezone(zone)
        dt_utc = dt.astimezone(tz.UTC)
        return dt_utc.strftime("%Y%m%dT%H%M%SZ")

    # --- these need attention - they don't take advantage of what's already in Item ---

    def _has_o(self) -> bool:
        # @o present?
        # return bool(self.item.get("o", False))
        return any(
            tok.get("t") == "@" and tok.get("k") == "o"
            for tok in self.structured_tokens
        )

    def _has_s(self) -> bool:
        # return bool(self.item.get("s", False))
        return any(
            tok.get("t") == "@" and tok.get("k") == "s"
            for tok in self.structured_tokens
        )

    def _get_start_dt(self) -> datetime | None:
        # return self.dtstart
        tok = next(
            (
                t
                for t in self.structured_tokens
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

    def _set_start_dt(self, dt: datetime) -> None:
        dt_str = dt.strftime("%Y%m%dT%H%M%S")
        tok = next(
            (
                t
                for t in self.structured_tokens
                if t.get("t") == "@" and t.get("k") == "s"
            ),
            None,
        )
        if tok:
            tok["token"] = f"@s {dt_str} "
        else:
            self.structured_tokens.append(
                {"token": f"@s {dt_str} ", "t": "@", "k": "s"}
            )
        self.dtstart = dt_str

    def _has_r(self) -> bool:
        # return bool(self.item.get("r", False))
        return any(
            t.get("t") == "@" and t.get("k") == "r" for t in self.structured_tokens
        )

    def _get_count_token(self):
        # &c N under the @r group
        for t in self.structured_tokens:
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
                    self.structured_tokens.remove(tok)
            except ValueError:
                pass

    def _get_rdate_token(self):
        # @+ token (comma list)
        return next(
            (
                t
                for t in self.structured_tokens
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
                self.structured_tokens.append(
                    {"token": f"@+ {joined}", "t": "@", "k": "+"}
                )
        else:
            if tok:
                self.structured_tokens.remove(tok)

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

        # (Optional) If you also keep textual @~… &f … tokens in structured_tokens,
        # you can append/update them here. Otherwise, finalize_jobs() will rebuild jobs JSON.
        if found:
            self.finalize_jobs(self.jobs)  # keeps statuses consistent
        return found

    def finish_without_exdate(
        self,
        *,
        completed_dt: datetime,
        record_id: int | None = None,
        job_id: int | None = None,
    ) -> FinishResult:
        """
        Finish inside Item, *without* EXDATE, and *disallowing* @o.
        Implements:
        1) If job and >1 unfinished -> add &f to that job, submit (due=None).
        2) If last unfinished job -> treat as whole project task and continue.
        3) If no @s -> itemtype='x', submit (due=None).
        4) If only one instance -> itemtype='x', submit (due=that one).
        5) Else two+ instances:
            - if due comes from @+ -> remove it from @+.
            - set @s = next.
            - if &c exists -> decrement it.
            - finalize_rruleset().
        """
        # --- disallow @o tasks
        # if self._has_o():
        #     raise ValueError("Offset (@o) tasks are handled elsewhere and cannot be finished here.")

        # --- 1) Job case
        # If job_id is provided and more than one job is unfinished, only mark this job finished.
        if job_id is not None and self.jobs:
            unfinished = self._unfinished_jobs()
            if len(unfinished) > 1:
                if self._mark_job_finished(job_id, completed_dt):
                    # No 'due' concept at the project level for job-only finish
                    self.finalize_jobs(self.jobs)
                    self.finalize_rruleset()  # harmless; keeps mirror consistent
                    return FinishResult(
                        new_structured_tokens=self.structured_tokens,
                        new_rruleset=self.rruleset or "",
                        due_ts_used=None,
                        finished_final=False,
                    )
            # else fall through to treat project as a single task

        # --- 3) No @s at all → single-shot
        if not self._has_s():
            self.itemtype = "x"
            # mirror the itemtype token if present
            if (
                self.structured_tokens
                and self.structured_tokens[0].get("t") == "itemtype"
            ):
                self.structured_tokens[0]["token"] = "x"
            # rrset likely empty already; keep consistent
            self.finalize_rruleset()
            return FinishResult(
                new_structured_tokens=self.structured_tokens,
                new_rruleset=self.rruleset or "",
                due_ts_used=None,
                finished_final=True,
            )

        # --- 4) Compute first two instances
        due_dt, next_dt = self._first_two_instances()
        if due_dt is None:
            # Nothing upcoming -> treat as single-shot finished
            self.itemtype = "x"
            if (
                self.structured_tokens
                and self.structured_tokens[0].get("t") == "itemtype"
            ):
                self.structured_tokens[0]["token"] = "x"
            self.finalize_rruleset()
            return FinishResult(
                new_structured_tokens=self.structured_tokens,
                new_rruleset=self.rruleset or "",
                due_ts_used=None,
                finished_final=True,
            )

        if next_dt is None:
            # Exactly one instance -> finishing it ends the task
            self.itemtype = "x"
            if (
                self.structured_tokens
                and self.structured_tokens[0].get("t") == "itemtype"
            ):
                self.structured_tokens[0]["token"] = "x"
            self.finalize_rruleset()
            return FinishResult(
                new_structured_tokens=self.structured_tokens,
                new_rruleset=self.rruleset or "",
                due_ts_used=int(due_dt.timestamp()),
                finished_final=True,
            )

        # --- 5) We have due + next
        # If due was contributed by @+ (RDATE list), remove that specific dt from @+.
        # We detect by comparing compact strings.
        due_compact = due_dt.strftime("%Y%m%dT%H%M%S")
        rdates = set(self._parse_rdate_list())
        if due_compact in rdates:
            self._remove_rdate_exact(due_compact)

        # Move @s to next
        self._set_start_dt(next_dt)

        # If &c exists, decrement it
        self._decrement_count_if_present()

        # Rebuild rruleset to reflect the new @s and any count changes
        self.finalize_rruleset()

        return FinishResult(
            new_structured_tokens=self.structured_tokens,
            new_rruleset=self.rruleset or "",
            due_ts_used=int(due_dt.timestamp()),
            finished_final=False,
        )
