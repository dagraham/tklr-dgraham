import re, shutil
from dateutil.parser import parse
from dateutil import rrule
from dateutil.rrule import rruleset, rrulestr
from datetime import date, datetime, timedelta
from dateutil.tz import gettz
import pytz
import textwrap

from collections import defaultdict
from math import ceil

from typing import Union, Tuple, Optional
from typing import List, Dict, Any, Callable, Mapping
from common import timedelta_string_to_seconds
import pprint

# JOB_PATTERN = re.compile(r"(^@j) (\d*):\s*(.*)")
# JOB_PATTERN = re.compile(r"^@j ( +)(\S.*)")
JOB_PATTERN = re.compile(r"^@j ( *)([^&]*)(?:(&.*))?")
LETTER_SET = set("abcdefghijklmnopqrstuvwxyz")  # Define once


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
    "rh",
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


def ruleset_to_rulehsh(rrset: rruleset) -> dict[str, str]:
    # FIXME: fixme
    raise NotImplementedError


def ruleset_to_rulestr(rrset: rruleset) -> str:
    # print(f"rrset: {rrset}; {type(rrset) = }; {rrset.__dict__}")
    # print(f"{list(rrset) = }")
    parts = []
    # parts.append("rrules:")
    for rule in rrset._rrule:
        # parts.append(f"{textwrap.fill(str(rule))}")
        parts.append(f"{'\\n'.join(str(rule).split('\n'))}")
    # parts.append("exdates:")
    for exdate in rrset._exdate:
        parts.append(f"EXDATE:{exdate}")
    # parts.append("rdates:")
    for rdate in rrset._rdate:
        parts.append(f"RDATE:{rdate}")
    return "\n".join(parts)


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


class Task:
    token_keys = {
        "subject": [
            "subject",
            "brief task description. Append an '@' to add an option.",
            "do_summary",
        ],
        "s": ["scheduled", "starting date or datetime", "do_datetime"],
        "t": ["tag", "tag name", "do_tag"],
        "r": ["recurrence", "recurrence rule", "do_rrule"],
        "j": ["job", "job entry", "do_job"],
        "+": ["rdate", "recurrence dates", "do_rdate"],
        "-": ["exdate", "exception dates", "do_exdate"],
        # Add more `&` token handlers for @j here as needed
        # "a": ["alerts", "list of alerts", "do_alert"],
        "b": ["beginby", "number of days for beginby notices", "do_beginby"],
        "c": ["context", "calendar", "do_context"],
        "d": ["deleted", "datetime deleted", "do_deleted"],
        "e": ["estimate", "timeperiod", "do_estimate"],
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
            "location",
            "location or context, e.g., home, office, errands",
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
        "jl": ["location", " string", "do_string"],
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
        self.previous_entry = ""
        self.item = {}
        self.previous_tokens = []
        self.rrule_tokens = []
        self.job_tokens = []
        self.token_store = None
        self.rrules = []
        self.jobs = []
        self.tags = []
        self.rdates = []
        self.exdates = []
        self.dtstart = None

    def parse_input(self, entry: str):
        """
        Parses the input string to extract tokens, then processes and validates the tokens.
        """
        digits = "1234567890" * ceil(len(entry) / 10)
        self._tokenize(entry)
        # print(
        #     f"entry to tokens:\n   |{digits[: len(entry)]}|\n   |{entry}|\n   {self.tokens}"
        # )
        self._parse_tokens(entry)
        self.parse_ok = True
        self.previous_entry = entry
        self.previous_tokens = self.tokens.copy()
        if self.rrule_tokens:
            success, rruleset_str = self.finalize_rruleset()
            print(f"\n{success = } for:\n'{self.entry}'\n{rruleset_str}")
        if self.jobs:
            success, jobs = self.finalize_jobs()
            # print(f"\n{success = } for:\n'{self.entry}'")
            # for job in jobs:
            #     print(job)
        # if self.tags:
        #     print(f"\n{success = } for:\n'{self.entry}'")
        #     print(f"tags: {', '.join(self.tags)}")
        #

    def __repr__(self):
        result = []
        result.append(f"Entry:\n{self.entry}")
        if self.rrule_tokens:
            success, rruleset_str = self.finalize_rruleset()
            result.append(f"rruleset:\n{rruleset_str}")
        if self.jobs:
            success, jobs = self.finalize_jobs()
            result.append("jobs:")
            for job in jobs:
                result.append(f"{pprint.pformat(job, sort_dicts=False)}")
        if self.tags:
            result.append("tags:")
            result.append(f"{pprint.pformat(self.tags)}")
        return "\n".join(result)

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
        for i, token_info in enumerate(self.tokens):
            token, start_pos, end_pos = token_info
            if i == 0:
                self._dispatch_token(token, start_pos, end_pos, "itemtype")
            elif i == 1:
                self._dispatch_token(token, start_pos, end_pos, "subject")
            elif token:
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
                print(f"Error processing '{token_type}': {result}")
        else:
            print(f"No handler for token: {token}")

    def _dispatch_sub_tokens(self, sub_tokens, prefix):
        for part in sub_tokens:
            if part.startswith("&"):
                token_type = prefix + part[1:2]  # Prepend prefix to token type
                token_value = part[2:].strip()
                # print(f"token_type = '{token_type}': token_value = '{token_value}'")
                if token_type in self.token_keys:
                    method_name = self.token_keys[token_type][2]
                    method = getattr(self, method_name)
                    is_valid, result = method(token_value)
                    # print(f"{token_value} => {is_valid}, {result}")
                    if is_valid:
                        if prefix == "r":
                            self.rrule_tokens[-1][1][token_type] = result
                        elif prefix == "j":
                            self.job_tokens[-1][1][token_type] = result
                    else:
                        self.parse_ok = False
                        print(f"Error processing sub-token '{token_type}': {result}")
                else:
                    self.parse_ok = False
                    print(f"No handler for sub-token: {token_type}")

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
        # print(f"calling timedelta_string_to_seconds with {arg}")
        ok, res = timedelta_string_to_seconds(arg)
        return ok, res

    @classmethod
    def do_alert(cls, arg):
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
                ok, td_seconds = timedelta_string_to_seconds(td)
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

    def do_estimate(self, token):
        # Process datetime token
        estimate = re.sub("^@. ", "", token.strip())
        # print(f"Processing extent token: '{estimate}'")
        ok, extent_obj = timedelta_string_to_seconds(estimate)
        if ok:
            self.extent = estimate_obj
            return True, estimate_obj, []
        else:
            return False, estimate_obj, []

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

    def do_datetime(self, token):
        # Process datetime token
        # print(f"Processing datetime token: {token}")
        try:
            datetime_str = re.sub("^@. ", "", token)
            datetime_obj = parse(datetime_str)
            self.dtstart = datetime_obj
            return True, datetime_obj, []
        except ValueError as e:
            return False, f"Invalid datetime: {datetime_str}. Error: {e}", []

    def do_rrule(self, token):
        # Process rrule token
        # print(f"Processing rrule token: {token}")
        parts = self._sub_tokenize(token)
        # print(f"do_rrule {parts = }")
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
            rrule_params["DTSTART"] = self.dtstart.strftime("%Y%m%dT%H%M%S")

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
        parts = self._sub_tokenize(tokens_remaining) if tokens_remaining else []
        # print(f"do_job {parts = }")
        # if len(parts) < 1:
        #     return False, f"Missing job subject: {token}", []
        # print(f"job parts = {parts}")

        job_params = {"j": summary}

        for part in parts:
            # print(f"processing part: {part}")
            key, *value = part
            # print(f"processing key: {key}, value: {value}")
            k = key[1]
            v = " ".join(value)
            job_params[k] = v
        if node is not None:
            job_params["node"] = node
        # print(f"appending job_params: {job_params}")
        # self.jobs.append(job_params)

        # Collect & tokens that follow @j
        # sub_tokens = self._extract_sub_tokens(token, '&')
        sub_tokens = []
        # self.job_tokens.append((token, job_params))
        self.job_tokens.append((token, job_params))
        # print(f"returning {job_params = }; {sub_tokens = }")
        return True, job_params, []

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
        print(f"in do_weekdays with wkd_str = |{wkd_str}|")
        matches = re.findall(wkd_regex, wkd_str)
        _ = [f"{x[0]}{x[1]}" for x in matches]
        all = [x.strip() for x in wkd_str.split(",")]
        bad = [x for x in all if x not in _]
        problem_str = ""
        problems = []
        print(f"{all = }, {bad = }")
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

    def do_rdate(self, token):
        # Process rdate token
        print(f"Processing rdate token: {token}")
        parts = re.sub("^@. ", "", token)
        print(f"rdate {parts = }")
        try:
            dates = [parse(dt) for dt in parts.split(",")]
            return True, dates, []
        except ValueError as e:
            return False, f"Invalid rdate: {parts}. Error: {e}", []

    def do_exdate(self, token):
        # Process exdate token
        print(f"Processing exdate token: {token}")
        parts = re.sub("^@. ", "", token)
        print(f"exdate {parts = }")
        try:
            dates = [parse(dt) for dt in parts.split(",")]
            return True, dates, []
        except ValueError as e:
            return False, f"Invalid exdate: {parts[1]}. Error: {e}", []

    def rrule_to_entry(self, rstr: str) -> str:
        """
        Convert an rrule string to an entry string.
        """
        lines = rstr.strip().split("\n")

        dtstart_list = []
        rrule_list = []
        rdate_list = []
        exdate_list = []

        for line in lines:
            if line.startswith("DTSTART:"):
                # TODO: maybe skip DTSTART lines?
                dtstart_str = line.replace("DTSTART:", "")
                dtstart_list.append(dtstart_str)
            elif line.startswith("RRULE:"):
                rrule_str = line.replace("RRULE:", "")
                rrule_list.append(rrule_str)
            elif line.startswith("RDATE:"):
                rdate_str = line.replace("RDATE:", "")
                rdate_list.extend(rdate_str.split(","))  # Split multiple RDATEs
            elif line.startswith("EXDATE:"):
                exdate_str = line.replace("EXDATE:", "")
                exdate_list.extend(exdate_str.split(","))  # Split multiple EXDATEs

        # Process DTSTART
        dtstart_part = ""
        if dtstart_list:
            dtstart_date = datetime.strptime(dtstart_list[0], "%Y%m%dT%H%M%S")
            dtstart_part = f"@s {dtstart_date.strftime('%Y-%m-%d %-I:%M%p').lower()}"

        # Process RRULEs
        rrule_parts = []
        for rrule_str in rrule_list:
            rrule_params = {}
            for param in rrule_str.split(";"):
                key, value = param.split("=")
                rrule_params[key] = value

            freq_entry = list(self.freq_map.keys())[
                list(self.freq_map.values()).index(rrule_params["FREQ"])
            ]
            rrule_part = f"@r {freq_entry}"

            for key, value in rrule_params.items():
                if key == "FREQ":
                    continue
                entry = self.param_to_key[key]
                rrule_part += f" &{entry} {value}"

            rrule_parts.append(rrule_part)

        # Process RDATEs
        rdate_parts = []
        for rdate_str in rdate_list:
            rdate_date = datetime.strptime(rdate_str, "%Y%m%dT%H%M%S")
            rdate_parts.append(f"{rdate_date.strftime('%Y-%m-%d %-I:%M%p').lower()}")
        rdates_str = f"@+ {', '.join(rdate_parts)}" if rdate_parts else ""

        # Process EXDATEs
        exdate_parts = []
        for exdate_str in exdate_list:
            exdate_date = datetime.strptime(exdate_str, "%Y%m%dT%H%M%S")
            exdate_parts.append(f"{exdate_date.strftime('%Y-%m-%d %-I:%M%p').lower()}")
        exdates_str = f"@- {', '.join(exdate_parts)}" if exdate_parts else ""

        # return f"{dtstart_part} {' '.join(rrule_parts)} {' '.join(rdate_parts)} {' '.join(exdate_parts)}"
        return f"{' '.join(rrule_parts)} {rdates_str} {exdates_str}"

    def finalize_rruleset(self):
        # Finalize the rruleset after collecting all related tokens
        if not self.rrule_tokens:
            return False, "No rrule tokens to process"
        if not self.parse_ok:
            return False, "Error parsing tokens"

        components = []
        rruleset_str = ""
        print(
            f"finalizing rruleset using {self.parse_ok = }, {len(self.rrule_tokens) = }; {len(components) = }; {len(rruleset_str) = }"
        )
        for token in self.rrule_tokens:
            rule_parts = []
            _, rrule_params = token
            print(f"finalizing rrule {token = }:  {_ = } with {rrule_params = }")
            dtstart = rrule_params.pop("DTSTART", None)
            if dtstart:
                components.append(f"DTSTART:{dtstart}")
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

        if self.rdates:
            rdates = ",".join([x.strftime("%Y%m%dT%H%M%S") for x in self.rdates])
            print(f"appending {rdates = }")
            components.append(f"RDATE:{rdates}")

        if self.exdates:
            exdates = ",".join([x.strftime("%Y%m%dT%H%M%S") for x in self.exdates])
            print(f"appending {exdates = }")
            components.append(f"EXDATE:{exdates}")

        rruleset_str = "\n".join(components)
        self.item["rruleset"] = rruleset_str
        self.item["r"] = self.rrule_to_entry(rruleset_str.rstrip())

        # must reset these to avoid duplicates
        self.rrule_tokens = []
        self.rdates = []
        self.exdates = []
        return True, rruleset_str

    def finalize_jobs(self):
        """
        Format combined task subject and job subject
        """
        jobs = self.jobs
        if not jobs:
            return False, "No jobs to process"
        if not self.parse_ok:
            return False, "Error parsing tokens"
        # available / waiting / completed
        # completed if 'f' in item

        subject = self.item["subject"]
        job_hsh = {}

        job_hsh = {i: x for i, x in enumerate(jobs)}

        # finished = [i for i, x in enumerate(jobs) if "f" in x]
        finished = set()
        waiting = []
        available = []
        prereqs = {}
        branch = []
        branches = []
        current_node = 0
        job_names = {}
        last_job_number = 0
        last_job = {}
        all = set()
        for i, job in job_hsh.items():
            all.add(i)
            last_job_number = i
            last_job = job
            job_names[i] = job["j"]
            if "f" in job:
                finished.add(i)
            if "node" in job:
                if job["node"] > 0 and len(branch) > job["node"]:
                    branches.append(branch)
                    branch = branch[: job["node"]]
                branch.append(i)

        if "node" in last_job:
            branch = branch[: last_job["node"]]
            # prereqs[i] = branch
            branch.append(last_job_number)
            branches.append(branch)
            branch = []

        if branches:
            # available_names = set()
            # waiting_names = set()
            prereqs = {}
            for branch in branches:
                # print(f"branch = {branch}")
                for _ in branch:
                    all.add(_)
                # leaf = branch[-1]
                for position, i in enumerate(branch):
                    branch_tail = branch[position + 1 :]
                    if branch_tail:
                        prereqs.setdefault(i, set())
                        for j in branch_tail:
                            prereqs[i].add(j)
        # print(f"\n\n{all = }\n\n{prereqs = }\n\n{waiting = }")

        for j, req in prereqs.items():
            prereqs[j] = req - finished

        # print("\n\n{prereqs = }\n\n{available = }\n\n{waiting = }")

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

        status = f"{len(available)}/{len(waiting)}/{len(finished)}"
        jobs = []

        for i, job in job_hsh.items():
            if i in finished:
                job["itemtype"] = "x"
            elif i in waiting:
                job["itemtype"] = "+"
            elif i in available:
                job["itemtype"] = "-"
            else:
                job["itemtype"] = "?"
            loc = job.get("l", "")
            loc = f" ({loc}) " if loc else " "
            job["subject"] = f"{job['j']}{loc}{status}"
            if i in prereqs:
                job["prereqs"] = prereqs[i]
            job["i"] = i
            jobs.append(job)

        # jobs_names = []
        #
        # for i, job in job_hsh.items():
        #     if i in available:
        #         job_names["itemtype"] = "-"
        #     elif i in waiting:
        #         job["itemtype"] = "+"
        #     elif i in finished:
        #         job["itemtype"] = "x"
        #     else:
        #         job["itemtype"] = "?"
        #     job["subject"] = f"{job['j']}: {subject} {status}"
        #     job["i"] = i
        #     jobs.append(job)

        self.item["j"] = jobs
        # print(f"\n\n{prereqs = }\n\n{available = }\n\n{waiting = }")
        return True, jobs
