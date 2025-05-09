import re, shutil
import json
from dateutil.parser import parse
from dateutil import rrule
from dateutil.rrule import rruleset, rrulestr
from datetime import time, date, datetime, timedelta

# from dateutil.tz import gettz
import pytz
import textwrap
from dateutil import tz
from dateutil.tz import gettz

from collections import defaultdict
from math import ceil
from copy import deepcopy

from typing import Iterable, List

from typing import Union, Tuple, Optional
from typing import List, Dict, Any, Callable, Mapping
from common import timedelta_str_to_seconds, log_msg, fmt_dt
from zoneinfo import ZoneInfo, available_timezones

JOB_PATTERN = re.compile(r"^@j ( *)([^&]*)(?:(&.*))?")
LETTER_SET = set("abcdefghijklmnopqrstuvwxyz")  # Define once


def get_local_zoneinfo():
    try:
        from zoneinfo import ZoneInfo
        import os

        tz_path = os.readlink("/etc/localtime")
        if "zoneinfo" in tz_path:
            return ZoneInfo(tz_path.split("zoneinfo/")[-1])
    except Exception:
        return None


def is_date(obj):
    return isinstance(obj, date) and not isinstance(obj, datetime)


def as_timezone(dt: datetime, timezone: ZoneInfo) -> datetime:
    if is_date(dt):
        return dt
    return dt.astimezone(timezone)


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
        if is_date(dt):
            # print(f"Yielding date: {dt}")
            yield dt
        else:
            # dt is a datetime
            # print(f"Yielding datetime: {dt}")
            if dt.tzinfo is None:
                if timezone is not None:
                    # print(f"Attaching timezone: {timezone} to naive datetime {dt}")
                    dt = dt.replace(tzinfo=timezone)
                else:
                    # print(f"Attaching timezone: {timezone} to naive datetime {dt}")
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
    after: Optional[datetime] = None,
    to_localtime: bool = False,
) -> List[datetime]:
    """
    Generate a list of upcoming localized instances from a rule.

    Args:
        rule: Parsed rule from rrulestr().
        timezone: ZoneInfo timezone to attach to naive datetimes.
        count: Maximum number of instances to return.
        after: Optional datetime to start on (default: now).
        to_localtime: Whether to convert to system local time for display.

    Returns:
        A list of timezone-aware datetime objects.
    """
    instances = []
    generator = localize_rule_instances(rule, timezone, to_localtime)

    if after is not None:
        if after.tzinfo is None:
            after = after.replace(tzinfo=timezone)

    for dt in generator:
        if after and dt < after:
            continue
        instances.append(dt)
        if len(instances) >= count:
            break
    return instances


def preview_rule_instances(
    rule: rruleset,
    timezone: Union[ZoneInfo, None] = None,
    count: int = 10,
    after: Optional[Union[datetime, date]] = None,
    to_localtime: bool = False,
) -> List[Union[datetime, date]]:
    instances = []
    generator = localize_rule_instances(rule, timezone, to_localtime)
    # print(f"{list(generator) = }")

    if after is None:
        after = datetime.now().astimezone()

    for dt in list(generator):
        if is_date(dt):
            # dt is a date
            # print(f"{dt = }")
            # if isinstance(after, datetime):
            #     after_date = after.date()
            # else:
            after_date = after

            if dt < after_date:
                # print(f"Skipping {dt} as it is before {after_date}")
                continue
        else:
            # dt is a datetime
            # print(f"{dt = }")
            # if isinstance(after, date) and not isinstance(after, datetime):
            #     # Promote date to datetime with same tzinfo
            #     after_dt = datetime(
            #         after.year, after.month, after.day, tzinfo=dt.tzinfo
            #     )
            # else:
            after_dt = after

            # print(f"{dt = }, {after_dt = }")
            if dt < after_dt:
                # print(f"Skipping {dt} as it is before {after_dt}")
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


def extract_labeled_subtrees(jobs):
    labels = {}
    i = 0
    while i < len(jobs):
        job = jobs[i]
        if "l" in job:
            label = job["l"]
            if label in labels:
                raise ValueError(f"Duplicate label: {label}")
            base_node = job["node"]
            subtree = [deepcopy(job)]
            i += 1
            while i < len(jobs) and jobs[i]["node"] > base_node:
                subtree.append(deepcopy(jobs[i]))
                i += 1
            # Remove the 'l' key from the root of the labeled subtree
            del subtree[0]["l"]
            labels[label] = subtree
        else:
            i += 1
    return labels


def inject_subtree(label_name, target_node, labels):
    if label_name not in labels:
        raise ValueError(f"Unknown label: {label_name}")
    subtree = deepcopy(labels[label_name])
    base_node = subtree[0]["node"]
    for job in subtree:
        job["node"] = target_node + (job["node"] - base_node)
    return subtree


def is_lowercase_letter(char):
    return char in LETTER_SET  # O(1) lookup


type_keys = {
    "*": "event",
    "-": "task",
    "%": "journal",
    "!": "inbox",
    "~": "goal",
    "+": "track",
    # '✓': 'finished',  # more a property of a task than an item type
}
common_methods = list("cdgilmnstuxz")

repeating_methods = list("+-o") + [
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

datetime_methods = list("abe")

job_methods = list("efhp") + [
    "jj",
    "ja",
    "jb",
    "jd",
    "je",
    "jf",
    "ji",
    "jl",
    "jm",
    "jp",
    "js",
    "ju",
]

multiple_allowed = [
    "a",
    "u",
    "t",
    "jj",
    "ji",
    "js",
    "jb",
    "jp",
    "ja",
    "jd",
    "je",
    "jf",
    "jl",
    "jm",
    "ju",
]

wrap_methods = ["w"]

required = {"*": ["s"], "-": [], "%": [], "~": ["s"], "+": ["s"]}

allowed = {
    "*": common_methods + datetime_methods + repeating_methods + wrap_methods,
    "-": common_methods + datetime_methods + job_methods + repeating_methods,
    "%": common_methods + ["+"],
    "~": common_methods + ["q", "h"],
    "+": common_methods + ["h"],
}

# inbox
required["!"] = []
allowed["!"] = common_methods + datetime_methods + job_methods + repeating_methods

requires = {
    "a": ["s"],
    "b": ["s"],
    "+": ["s"],
    "q": ["s"],
    "-": ["rr"],
    "rr": ["s"],
    "js": ["s"],
    "ja": ["s"],
    "jb": ["s"],
}


# NOTE: experiment for replacing jinja2
def itemhsh_to_details(item: dict[str, str]) -> str:
    format_dict = {
        "itemtype": "",
        "subject": " ",
        "s": f"\n@s ",
        "e": f" @e ",
        "r": f"\n@r ",
    }

    formatted_string = ""
    for key in format_dict.keys():
        if key in item:
            formatted_string += f"{format_dict[key]}{item[key]}"
    return formatted_string


# def ruleset_to_rulestr(rrset: rruleset) -> str:
#     print(f"rrset: {rrset}; {type(rrset) = }; {rrset.__dict__}")
#     print(f"{list(rrset) = }")
#     parts = []
#     # parts.append("rrules:")
#     for rule in rrset._rrule:
#         # parts.append(f"{textwrap.fill(str(rule))}")
#         parts.append(f"{'\\n'.join(str(rule).split('\n'))}")
#     # parts.append("exdates:")
#     for exdate in rrset._exdate:
#         parts.append(f"EXDATE:{exdate}")
#     # parts.append("rdates:")
#     for rdate in rrset._rdate:
#         parts.append(f"RDATE:{rdate}")
#     return "\n".join(parts)


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
            if stripped_para.startswith(("+", "-", "*", "%", "!", "~")):
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


class Item:
    token_keys = {
        "itemtype": [
            "item type",
            "character from * (event), - (task), % (journal), ~ (goal), + (track) or ! (inbox)",
            "do_itemtype",
        ],
        "subject": [
            "subject",
            "brief item description. Append an '@' to add an option.",
            "do_summary",
        ],
        "s": ["scheduled", "starting date or datetime", "do_datetime"],
        "t": ["tag", "tag name", "do_tag"],
        "r": ["recurrence", "recurrence rule", "do_rrule"],
        "j": ["job", "job entry", "do_job"],
        "+": ["rdate", "recurrence dates", "do_rdate"],
        "-": ["exdate", "exception dates", "do_exdate"],
        # Add more `&` token handlers for @j here as needed
        "a": ["alerts", "list of alerts", "do_alert"],
        "b": ["beginby", "number of days for beginby notices", "do_beginby"],
        "c": ["context", "context", "do_string"],
        "d": ["description", "description", "do_description"],
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
        "o": [
            "overdue",
            "character from (r)estart, (s)kip or (k)eep",
            "do_overdue",
        ],
        "p": [
            "priority",
            "priority from 0 (none) to 4 (urgent)",
            "do_priority",
        ],
        "z": [
            "timezone",
            "a timezone entry such as 'US/Eastern' or 'Europe/Paris' or 'float' to specify a naive/floating datetime",
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
        "jj": [
            "subject",
            "job subject. Append an '&' to add a job option.",
            "do_string",
        ],
        "ja": [
            "alert",
            "list of timeperiods before job is scheduled followed by a colon and a list of commands",
            "do_alert",
        ],
        "jb": ["beginby", " integer number of days", "do_beginby"],
        "jd": ["description", " string", "do_description"],
        "je": ["extent", " timeperiod", "do_duration"],
        "jf": ["finish", " completion done -> due", "do_completion"],
        "ji": ["unique id", " integer or string", "do_string"],
        "jl": ["label", " string", "do_string"],
        "jm": ["mask", "string to be masked", "do_mask"],
        "jp": [
            "prerequisite ids",
            "list of ids of immediate prereqs",
            "do_stringlist",
        ],
        "js": [
            "scheduled",
            "timeperiod before task scheduled when job is scheduled",
            "do_duration",
        ],
        "ju": ["used time", "timeperiod: datetime", "do_usedtime"],
        "j?": ["job &-key", "enter &-key", "do_ampj"],
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

    def __init__(self):
        self.entry = ""
        self.tokens = []
        self.itemtype = ""
        self.previous_entry = ""
        self.item = {}
        self.previous_tokens = []
        self.rrule_tokens = []
        self.job_tokens = []
        self.token_store = None
        self.rrules = []
        self.jobs = []
        self.tags = []
        self.alerts = []
        self.rdates = []
        self.exdates = []
        self.dtstart = None
        self.dtstart_str = None
        self.rdate_str = None
        self.rdstart_str = None
        self.exdate_str = None
        self.timezone = gettz("local")
        self.enforce_dates = False

    def parse_input(self, entry: str):
        """
        Parses the input string to extract tokens, then processes and validates the tokens.
        """
        digits = "1234567890" * ceil(len(entry) / 10)
        self._tokenize(entry)
        self._parse_tokens(entry)
        self.parse_ok = True
        self.previous_entry = entry
        self.previous_tokens = self.tokens.copy()

        success, rruleset_str = self.finalize_rruleset()

        for i in ["r", "s"]:
            if i in self.item:
                del self.item[i]
        if self.jobs:
            success, jobs = self.finalize_jobs()
        if self.tags:
            self.item["t"] = self.tags
            print(f"tags: {self.tags}")
        if self.alerts:
            self.item["a"] = self.alerts
            print(f"alerts: {self.alerts}")

    def _tokenize(self, entry: str):
        self.entry = entry
        pattern = r"(@\w+ [^@]+)|(^\S+)|(\S[^@]*)"
        matches = re.finditer(pattern, self.entry)
        tokens_with_positions = []
        for match in matches:
            # Get the matched token
            token = match.group(0)
            # Get the start and end positions
            start_pos = match.start()
            end_pos = match.end()
            # Append the token and its positions as a tuple
            tokens_with_positions.append((token, start_pos, end_pos))
        self.tokens = tokens_with_positions

    def _sub_tokenize(self, entry):
        pattern = r"(@\w+ [^&]+)|(^\S+)|(\S[^&]*)"
        matches = re.finditer(pattern, entry)
        if matches is None:
            return []
        tokens_with_positions = []
        for match in matches:
            # print(f"{match = }")
            # Get the matched token
            token = match.group(0)
            # Get the start and end positions
            start_pos = match.start()
            end_pos = match.end()
            # Append the token and its positions as a tuple
            # tokens_with_positions.append((token, start_pos, end_pos))
            tokens_with_positions.append(tuple(token.split()))
        return tokens_with_positions

    def _parse_tokens(self, entry: str):
        if not self.previous_entry:
            # If there is no previous entry, parse all tokens
            self._parse_all_tokens()
            return

        # Identify the affected tokens based on the change
        changes = self._find_changes(self.previous_entry, entry)
        affected_tokens = self._identify_affected_tokens(changes)

        # Parse only the affected tokens
        for token_info in affected_tokens:
            token, start_pos, end_pos = token_info
            # Check if the token has actually changed
            if self._token_has_changed(token_info):
                # print(f"processing changed token: {token_info}")
                if start_pos == 0:
                    self._dispatch_token(token, start_pos, end_pos, "itemtype")
                elif start_pos == 2:
                    self._dispatch_token(token, start_pos, end_pos, "subject")
                else:
                    self._dispatch_token(token, start_pos, end_pos)

    def _parse_all_tokens(self):
        # print(f"{self.tokens = }")
        # second_pass = []

        # first pass
        for i, token_info in enumerate(self.tokens):
            token, start_pos, end_pos = token_info
            if i == 0:
                self._dispatch_token(token, start_pos, end_pos, "itemtype")
            elif i == 1:
                self._dispatch_token(token, start_pos, end_pos, "subject")
            else:
                token_type = token.split()[0][
                    1:
                ]  # Extract token type (e.g., 's' from '@s')
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
        for token_info in self.tokens:
            token, start_pos, end_pos = token_info
            if start <= end_pos and end >= start_pos:
                affected_tokens.append(token_info)
        return affected_tokens

    def _token_has_changed(self, token_info):
        return token_info not in self.previous_tokens

    def _dispatch_token(self, token, start_pos, end_pos, token_type=None):
        # print(
        #     f"dispatching token: {token = }, {start_pos = }, {end_pos = }, {token_type = }"
        # )
        if token_type is None:
            if token == "@":
                self.do_at()
                return
            elif token.startswith("@"):
                token_type = token.split()[0][
                    1:
                ]  # Extract token type (e.g., 's' from '@s')
            else:
                token_type = token
        if token_type in self.token_keys:
            # print(f"Dispatching token: {token} as {token_type}")
            # print(f"Dispatching token: {token.rstrip()}")
            method_name = self.token_keys[token_type][2]
            # print(f"method_name = {method_name}")
            method = getattr(self, method_name)
            is_valid, result, sub_tokens = method(token)
            if is_valid:
                if token_type == "r":
                    # print(f"appending {result} to self.rrules")
                    self.rrules.append(result)
                    self._dispatch_sub_tokens(sub_tokens, "r")
                elif token_type == "j":
                    # print(f"appending {result} to self.jobs")
                    self.jobs.append(result)
                    self._dispatch_sub_tokens(sub_tokens, "j")
                elif token_type == "+":
                    self.rdates.extend(result)
                elif token_type == "-":
                    self.exdates.extend(result)
                else:
                    self.item[token_type] = result
            else:
                self.parse_ok = False
                log_msg(f"Error processing '{token_type}': {result}")
        else:
            log_msg(f"No handler for token: {token}")

    def _dispatch_sub_tokens(self, sub_tokens, prefix):
        for part in sub_tokens:
            if part.startswith("&"):
                token_type = prefix + part[1:2]  # Prepend prefix to token type
                token_value = part[2:].strip()
                # print(f"token_type = '{token_type}': token_value = '{token_value}'")
                if token_type in self.token_keys:
                    method_name = self.token_keys[token_type][2]
                    method = getattr(self, method_name)
                    is_valid, result, *sub_tokens = method(token_value)
                    # print(f"{token_value} => {is_valid}, {result}")
                    if is_valid:
                        if prefix == "r":
                            self.rrule_tokens[-1][1][token_type] = result
                        elif prefix == "j":
                            self.job_tokens[-1][1][token_type] = result
                    else:
                        self.parse_ok = False
                        log_msg(f"Error processing sub-token '{token_type}': {result}")
                        return False, result, []
                else:
                    self.parse_ok = False
                    log_msg(f"No handler for sub-token: {token_type}")
                    return False, f"Invalid sub-token: {token_type}", []

    def _validate(self):
        # Overall validation logic if needed
        pass

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

    def do_itemtype(self, token):
        # Process item type token
        # print(f"Processing item type token: {token}")
        valid_itemtypes = {"*", "-", "%", "~", "+", "!"}
        itemtype = token[0]
        if itemtype in valid_itemtypes:
            self.itemtype = itemtype
            return True, itemtype, []
        else:
            return False, f"Invalid item type: {itemtype}", []

    @classmethod
    def do_summary(cls, token):
        # Process subject token
        # print(f"Processing subject token: {token}")
        if len(token) >= 1:
            return True, token.strip(), []
        else:
            return False, "subject cannot be empty", []

    @classmethod
    def do_duration(cls, arg: str):
        """ """
        # print(f"processing duration: {arg}")
        if not arg:
            return False, f"time period {arg}"
        print(f"calling timedelta_str_to_seconds with {arg}")
        ok, res = timedelta_str_to_seconds(arg)
        return ok, res

    def do_alert(self, arg):
        """
        Process an alert string, validate it and return a corresponding string
        with the timedelta components replaced by integer seconds.
        """
        alerts = [x.strip() for x in arg.split(";")]
        if not alerts:
            return False, "missing alerts", []
        res = []
        issues = []
        for alert in alerts:
            parts = [x.strip() for x in alert.split(":")]
            if len(parts) != 2:
                issues.append(f"Invalid alert format: {alert}")
                continue
            timedeltas, commands = parts
            secs = []
            cmds = []
            probs = [f"For alert: {alert}"]
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
                else:
                    ok = False
                    probs.append(f"  Invalid timedelta: {td}")
            if ok:
                res.append(f"{', '.join(secs)}: {', '.join(cmds)}")
            else:
                issues.append("; ".join(probs))
        if issues:
            return False, "\n".join(issues), []
        self.alerts.extend(res)
        return True, "; ".join(res), []

    def do_description(self, token):
        # print(f"Processing description: {token}")
        description = re.sub("^@. ", "", token)
        if not description:
            return False, "missing description", []
        ok, rep = Item.do_paragraph(description)
        if ok:
            self.description = rep
            return True, rep, []
        else:
            return False, rep, []

    def do_extent(self, token):
        # Process datetime token
        extent = re.sub("^@. ", "", token.strip())
        ok, extent_obj = timedelta_str_to_seconds(extent)
        if ok:
            self.extent = extent_obj
            return True, extent_obj, []
        else:
            return False, extent_obj, []

    def do_tag(self, token):
        # Process datetime token

        obj, rep, parts = self.do_string(token)
        if obj:
            self.tags.append(obj)
            return True, obj, []
        else:
            return False, rep, []

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
                except:
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
                except:
                    all_ok = False
                    rep_lst.append(f"~{arg}~")
            obj = obj_lst if all_ok else None
            rep = ", ".join(rep_lst)
        return obj, rep

    def do_string(self, token):
        try:
            obj = re.sub("^@. ", "", token.strip())
            rep = obj
        except:
            obj = None
            rep = f"invalid: {token}"
        return obj, rep, []

    def do_timezone(self, token: str):
        """Handle @z timezone declaration in user input."""
        tz_str = token.strip()[2:].strip()
        # print(f"{tz_str = }")
        if tz_str.lower() in {"float", "naive"}:
            self.timezone = None
            return True, None, []
        try:
            self.timezone = ZoneInfo(tz_str)
            return True, self.timezone, []
        except Exception:
            self.timezone = None
            return False, f"Invalid timezone: '{tz_str}'", []

    def promote_date_to_datetime(self, dt: datetime) -> datetime | date:
        """
        If dt is exactly midnight (00:00:00), adjust:
        - For events (*): move to 00:00:01
        - For tasks (-): move to 23:59:59
        """
        if dt.hour == 0 and dt.minute == 0 and dt.second == 0:
            return dt.date()
            # if self.itemtype == "-":
            #     return dt.replace(hour=23, minute=59, second=59)
            # else:
            #     return dt.replace(second=1)
        return dt

    def enforce_date(self, dt: datetime) -> datetime:
        """
        Force dt to behave like a date (no meaningful time component).
        Always promote time to:
        - 00:00:01 for events (*)
        - 23:59:59 for tasks (-)
        """
        return dt.date()
        # if self.itemtype == "-":
        #     return dt.replace(hour=23, minute=59, second=59, microsecond=0)
        # else:
        #     return dt.replace(hour=0, minute=0, second=1, microsecond=0)

    def do_datetime(self, token):
        """
        Process a datetime token such as "@s 3p fri" or "@s 2025-04-24".
        Sets both self.dtstart and self.dtstart_str.
        """
        try:
            datetime_str = token.strip()
            # Remove prefix like '@s '
            datetime_str = re.sub(r"^@.\s+", "", datetime_str)
            # Parse the datetime
            odt = parse(datetime_str)
            dt = self.promote_date_to_datetime(odt)
            is_date = dt != odt
            self.enforce_dates = dt != odt
            # self.rdstart will be used if there is no recurrence rule
            if is_date:
                self.dtstart_str = f"DTSTART;VALUE=DATE:{dt.strftime('%Y%m%d')}"
                self.rdstart_str = f"RDATE;VALUE=DATE:{dt.strftime('%Y%m%d')}"
            else:
                self.dtstart_str = f"DTSTART:{dt.strftime('%Y%m%dT%H%M%S')}"
                self.rdstart_str = f"RDATE:{dt.strftime('%Y%m%dT%H%M%S')}"

            self.dtstart = dt
            return True, dt, []

        except ValueError as e:
            return False, f"Invalid datetime: {token}. Error: {e}", []

    def do_rrule(self, token):
        # Process rrule token
        # print(f"Processing rrule token: {token}")
        parts = self._sub_tokenize(token)
        if len(parts) < 1:
            return False, f"Missing rrule frequency: {token}", []
        elif parts[0][1] not in self.freq_map:
            keys = ", ".join([f"{k}: {v}" for k, v in self.freq_map.items()])
            return (
                False,
                f"'{parts[1]}', is not one of the supported frequencies from: \n   {keys}",
                [],
            )
        freq = self.freq_map[parts[0][1]]
        rrule_params = {"FREQ": freq}
        if self.dtstart:
            rrule_params["DTSTART"] = self.dtstart.strftime("%Y%m%dT%H%M%S%z")

        # Collect & tokens that follow @r
        sub_tokens = self._extract_sub_tokens(token, "&")

        self.rrule_tokens.append((token, rrule_params))
        # print(f"{self.rrule_tokens = }")
        return True, rrule_params, sub_tokens

    def do_job(self, token):
        # Process journal token
        # print(f"Processing job token: {token}")
        node, summary, tokens_remaining = self._extract_job_node_and_summary(token)
        # print(f"{node = }; {summary = }; {tokens_remaining = }")
        job_params = {"j": summary}
        job_params["node"] = node
        sub_tokens = []
        if tokens_remaining is not None:
            parts = self._sub_tokenize(tokens_remaining)
            # print(f"{parts = }")

            for part in parts:
                # print(f"processing part: {part}")
                key, *value = part
                # print(f"processing key: {key}, value: {value}")
                k = key[1]
                v = " ".join(value)
                job_params[k] = v
            # if node is not None:
            #     job_params["node"] = node

            # Collect & tokens that follow @j
            sub_tokens = self._extract_sub_tokens(token, "&")
            # self.job_tokens.append((token, job_params))
            self.job_tokens.append((token, job_params))
            # print(f"returning {job_params = }; {sub_tokens = }")
        return True, job_params, sub_tokens

    def _extract_sub_tokens(self, token, delimiter):
        # Use regex to extract sub-tokens
        pattern = rf"({delimiter}\w+ \S+)"
        matches = re.findall(pattern, token)
        return matches

    def do_at(self):
        print(f"TODO: do_at() -> show available @ tokens")

    def do_amp(self):
        print(f"TODO: do_amp() -> show available & tokens")

    @classmethod
    def do_weekdays(cls, wkd_str: str):
        """
        Converts a string representation of weekdays into a list of rrule objects.
        """
        wkd_str = wkd_str.upper()
        wkd_regex = r"(?<![\w-])([+-][1-4])?(MO|TU|WE|TH|FR|SA|SU)(?!\w)"
        # print(f"in do_weekdays with wkd_str = |{wkd_str}|")
        matches = re.findall(wkd_regex, wkd_str)
        _ = [f"{x[0]}{x[1]}" for x in matches]
        all = [x.strip() for x in wkd_str.split(",")]
        bad = [x for x in all if x not in _]
        problem_str = ""
        problems = []
        # print(f"{all = }, {bad = }")
        for x in bad:
            probs = []
            print(f"splitting {x}")
            i, w = cls.split_int_str(x)
            print(f"{x = }, i = |{i}|, w = |{w}|")
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
            problem_str = f"Problem entries: {', '.join(bad)}\n{'\n'.join(problems)}"
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
        except:
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
        except:
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
            except:
                if typ:
                    return False, "{}: {}".format(typ, arg)
                else:
                    return False, arg
        elif type(arg) == list:
            try:
                args = [int(x) for x in arg]
            except:
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

    def do_rdate(self, token: str):
        """
        Process an RDATE token, e.g., "@+ 2024-07-03 14:00, 2024-08-05 09:00".
        Uses the global timezone (set via @z) for all entries, and serializes
        them using TZID (even for UTC).
        """
        try:
            # Remove the "@+" prefix and extra whitespace
            token_body = token.strip()[2:].strip()
            # Split on commas to get individual date strings
            print(f"{token_body = }")
            dt_strs = [s.strip() for s in token_body.split(",") if s.strip()]
            print(f"{dt_strs = }")

            # Process each entry
            rdates = []
            for dt_str in dt_strs:
                dt = parse(dt_str.strip())
                if self.enforce_dates:
                    dt = self.enforce_date(dt)
                print(f"{dt = }")
                # If dt is naive and a global timezone is available, use it
                if dt.tzinfo is None and self.timezone and not self.enforce_dates:
                    print(f"replacing tzinfo with {self.timezone} in {dt = }")
                    dt.replace(tzinfo=self.timezone)
                    print(f"replaced {dt = }")
                # Promote a date to a datetime if necessary (using your helper)
                # dt = self.promote_date_to_datetime(dt)
                print(f"adding {dt = } to rdates")
                if dt not in self.rdates:
                    print(f"added {dt = } to rdates")
                    rdates.append(dt)
            print(f"{rdates = }")
            self.rdates = rdates
            # Prepend RDATE in finalize_rruleset after possible insertion of DTSTART
            fmt_str = ";VALUE=DATE:%Y%m%d" if self.enforce_dates else "%Y%m%dT%H%M%S"
            self.rdate_str = ",".join([dt.strftime(f"{fmt_str}") for dt in rdates])
            return True, self.rdate_str, []
        except Exception as e:
            return False, f"Invalid @+ value: {e}", []

    def do_exdate(self, token):
        """
        Process @- (EXDATE) token and append properly formatted EXDATE line(s) to self.rruleset.
        Always uses TZID, including for UTC.
        """
        try:
            # Remove the "@+" prefix and extra whitespace
            token_body = token.strip()[2:].strip()
            # Split on commas to get individual date strings
            print(f"{token_body = }")
            dt_strs = [s.strip() for s in token_body.split(",") if s.strip()]
            exdates = []
            for dt_str in dt_strs:
                dt = parse(dt_str.strip())
                if self.enforce_dates:
                    dt = self.enforce_date(dt)
                # remove dt from rdates if possible, if not, add to exdates
                removed_it = False
                self.rdates = [rd for rd in self.rdates if rd != dt]
                while dt in self.rdates:
                    self.rdates.remove(dt)
                    removed_it = True
                if not removed_it and dt not in self.exdates:
                    exdates.append(dt)
            self.exdates = exdates
            fmt_str = ";VALUE=DATE:%Y%m%d" if self.enforce_dates else "%Y%m%dT%H%M%S"
            self.exdate_str = ",".join([dt.strftime(f"{fmt_str}") for dt in exdates])
            return True, self.exdate_str, []

        except Exception as e:
            return False, f"Invalid @- token: {token}. Error: {e}", []

    def finalize_rruleset(self):
        if self.rrule_tokens:
            # print("finalizing rruleset with tokens")
            components = []
            rruleset_str = ""
            # print(
            #     f"finalizing rruleset using {self.parse_ok = }, {len(self.rrule_tokens) = }; {len(components) = }; {len(rruleset_str) = }"
            # )
            for token in self.rrule_tokens:
                print(f"{self.rrule_tokens = }")
                rule_parts = []
                _, rrule_params = token
                # print(
                #     f"finalizing rrule {token = }:  {_ = } with {rrule_params = }; {self.dtstart_str = }"
                # )
                dtstart = rrule_params.pop("DTSTART", None)
                # if dtstart:
                #     components.append(f"DTSTART:{dtstart}")
                if self.dtstart_str:
                    components.append(self.dtstart_str)
                freq = rrule_params.pop("FREQ", None)
                if freq:
                    rule_parts = [
                        f"RRULE:FREQ={freq}",
                    ]
                for k, v in rrule_params.items():
                    if v:
                        rule_parts.append(f"{v}")
                rrule_params = {}

                rule = ";".join(rule_parts)

                components.append(rule)

            if self.rdate_str:
                # rdates = ",".join([x.strftime("%Y%m%dT%H%M%S") for x in self.rdates])
                # print(f"appending {rdates = }")

                components.append(f"RDATE:{self.rdate_str}")

            if self.exdate_str:
                components.append(f"EXDATE:{self.exdate_str}")

            rruleset_str = "\n".join(components)
            self.item["rruleset"] = rruleset_str

            # must reset these to avoid duplicates
            self.rrule_tokens = []
            self.rdates = []
            self.exdates = []
            return True, rruleset_str

        elif self.rdstart_str:
            # print("finalizing rruleset with rdate only")
            components = [self.rdstart_str]
            if self.rdate_str:
                components.append(f"RDATE:{self.rdate_str}")
            rruleset_str = "\n".join(components)
            self.item["rruleset"] = rruleset_str
            # must reset these to avoid duplicates
            # self.rrule_tokens = []
            # self.rdates = []
            # self.exdates = []
            return True, rruleset_str
        return False, "No rrule tokens or rdate to finalize"

    def finalize_jobs(self):
        """
        From the list of jobs, assign ids taking account of jobs shared
        through labels and then from the place of the job in the sequence, its
        node (level of indention) and its finished status, determine the
        relevant prequisites, and the lists of available, waiting and finished
        jobs.
        """
        jobs = self.jobs
        if not jobs:
            return False, "No jobs to process"
        if not self.parse_ok:
            return False, "Error parsing tokens"

        # subject = self.item["subject"]
        job_hsh = {}

        branch = []
        branches = []
        job_names = {}
        labels = {}
        idx = 0
        finalized_jobs = []
        last_job = {}
        last_node = 0
        for _, job in enumerate(jobs):
            bump_idx = False
            job_name = job["j"]
            if job_name in labels:
                # this is an instance of labeled job and should use the idx of the label
                # take the node level from the job
                this_node = job.get("node", 0)
                # use the labeled job for the rest
                this_job = deepcopy(labels[job_name])
                this_i = this_job.get("i", 0)
                this_job["node"] = this_node
                this_job["i"] = this_i
                job_names[idx] = this_job["j"]
                # print(f"{this_job = }")
            else:
                # a job needing an idx, perhaps with a lobel
                bump_idx = True
                this_job = deepcopy(job)
                this_job["i"] = idx
                job_names[idx] = this_job["j"]

                if "l" in this_job:
                    label = this_job["l"]
                    if label in labels:
                        raise ValueError(f"Duplicate label: {label}")
                    job_copy = deepcopy(this_job)
                    del job_copy["l"]
                    if "jl" in job_copy:
                        del job_copy["jl"]
                    labels[label] = job_copy
                    this_job = job_copy

            if "node" in this_job:
                if this_job["node"] >= 0 and len(branch) >= this_job["node"]:
                    branches.append(branch)
                    branch = branch[: this_job["node"]]
                branch.append(this_job["i"])
            else:
                log_msg(f"node missing from {this_job = }")

            job_hsh[idx] = this_job
            finalized_jobs.append(this_job)
            last_job = this_job
            if bump_idx:
                idx += 1

        if "node" in last_job:
            branches.append(branch)
            branch = []

        all = set()
        prereqs = {}
        if branches:
            for branch in branches:
                # print(f"branch = {branch}")
                for _ in branch:
                    all.add(_)
                for position, i in enumerate(branch):
                    branch_tail = branch[position + 1 :]
                    if branch_tail:
                        prereqs.setdefault(i, set())
                        for j in branch_tail:
                            prereqs[i].add(j)

        finished = set(job["i"] for job in finalized_jobs if "f" in job)
        empty = []
        for j, req in prereqs.items():
            prereqs[j] = req - finished
            if not prereqs[j]:
                empty.append(j)

        for j in empty:
            del prereqs[j]

        available = set()
        waiting = set()
        for j in all:
            if j in prereqs:
                if prereqs[j]:
                    waiting.add(j)
                else:
                    available.add(j)
            elif j not in finished:
                available.add(j)

        jobs = []
        print("jobs: ")
        for job in finalized_jobs:
            i = job["i"]
            req = prereqs.get(i, [])
            if req:
                job["prereqs"] = req
            print(f"  {job})")
            jobs.append(job)

        self.item["j"] = jobs

        print("prereqs")
        for i, reqs in prereqs.items():
            print(f"  {i}: {reqs}")
        for name, value in {
            "available": available,
            "waiting": waiting,
            "finished": finished,
        }.items():
            print(f"{name} = {pp_set(value)}")

        return True, jobs

    def do_completion(self, token):
        """ "process completion command"""
        print("TODO: do_completion() -> implement")
        return False, token, []

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
        # print(f"list_rrule: {rule_string = }")
        is_date = "VALUE=DATE" in rule_string
        # print(f"{is_date = }")
        fmt_str = "    %a %Y-%m-%d" if is_date else "    %a %Y-%m-%d %H:%M:%S %Z %z"
        # rule = rrulestr(rule_string, ignoretz=True), ignoretz=True
        print(f"list_rrule: {rule_string = }")
        rule = rrulestr(rule_string)
        # try:
        #     res = list(rule)
        #     # Print the occurrences
        #     print("=>")
        #     print("Instances[:10]:")
        #     print("  Try As stored:")
        #     for dt in res[:count]:
        #         _ = dt
        #         print(_.strftime(f"{fmt_str}"))
        #     print("  Try As localtime:")
        #     for dt in res[:count]:
        #         _ = dt.astimezone(tz.tzlocal())
        #         print(_.strftime(f"{fmt_str}"))
        # except Exception as e:
        #     print(f"Error parsing rrulestr: {e}")
        #     return False

        timezone = (
            None if is_date else self.timezone
        )  # assuming you store ZoneInfo in self.timezone
        # to_localtime = to_localtime and not self.enforce_dates
        # print(
        #     f"Using localize_rule_instances with {to_localtime = }, {timezone = }, {count = }, {after = }"
        # )
        # timezone = None

        if after is None and count is None:
            # Default: return full localized list
            # print("after and count are None, returning full list")
            return localize_rule_instances(
                list(rule),
                timezone,
                to_localtime=to_localtime,
            )

        # Use the preview function for controlled output
        # print(
        #     f"Using preview_rule_instances with {count = }, {after = }, {timezone = }, {rule = }"
        # )
        return preview_rule_instances(
            rule,
            timezone,
            count=count or 1000,
            after=after,
            to_localtime=to_localtime,
        )


# class ItemManager:
#     def __init__(self):
#         self.doc_view_data = {}  # Primary structure: dict[doc_id, dict[view, list[row]]]
#         self.view_doc_data = defaultdict(
#             lambda: defaultdict(list)
#         )  # Secondary index: dict[view, dict[doc_id, list[row]])
#         self.view_cache = {}  # Cache for views
#         self.doc_view_contribution = defaultdict(
#             set
#         )  # Tracks views each doc_id contributes to
#
#     def add_or_update_item(self, item):
#         doc_id = item.doc_id
#         new_views_and_rows = item.get_weekly_rows()
#
#         # Invalidate cache for views that will be affected by this doc_id
#         self.invalidate_cache_for_doc(doc_id)
#
#         # Update the primary structure
#         self.doc_view_data[doc_id] = new_views_and_rows
#
#         # Update the secondary index
#         for view, rows in new_views_and_rows.items():
#             self.view_doc_data[view][doc_id] = rows
#             self.doc_view_contribution[doc_id].add(view)
#
#     def get_view_data(self, view):
#         # Check if the view is in the cache
#         if view in self.view_cache:
#             return self.view_cache[view]
#
#         # Retrieve data for a specific view
#         view_data = dict(self.view_doc_data[view])
#
#         # Cache the view data
#         self.view_cache[view] = view_data
#         return view_data
#
#     def get_reminder_data(self, doc_id):
#         # Retrieve data for a specific reminder
#         return self.doc_view_data.get(doc_id, {})
#
#     def remove_item(self, doc_id):
#         # Invalidate cache for views that will be affected by this doc_id
#         self.invalidate_cache_for_doc(doc_id)
#
#         # Remove reminder from primary structure
#         if doc_id in self.doc_view_data:
#             views_and_rows = self.doc_view_data.pop(doc_id)
#             # Remove from secondary index
#             for view in views_and_rows:
#                 if doc_id in self.view_doc_data[view]:
#                     del self.view_doc_data[view][doc_id]
#
#             # Remove doc_id from contribution tracking
#             if doc_id in self.doc_view_contribution:
#                 del self.doc_view_contribution[doc_id]
#
#     def invalidate_cache_for_doc(self, doc_id):
#         # Invalidate cache entries for views affected by this doc_id
#         if doc_id in self.doc_view_contribution:
#             for view in self.doc_view_contribution[doc_id]:
#                 if view in self.view_cache:
#                     del self.view_cache[view]
