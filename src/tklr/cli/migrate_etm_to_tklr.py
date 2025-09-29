#!/usr/bin/env python3
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ------------------------------------------------------------
# Regex patterns for ETM tags
# ------------------------------------------------------------
TAG_PATTERNS = {
    "D": re.compile(r"^\{D\}:(\d{8})$"),
    "T": re.compile(r"^\{T\}:(\d{8}T\d{4})([AN])$"),
    "I": re.compile(r"^\{I\}:(.+)$"),
    "P": re.compile(r"^\{P\}:(.+)$"),
    "W": re.compile(r"^\{W\}:(.+)$"),
}


# ------------------------------------------------------------
# Helpers
# ------------------------------------------------------------
def format_dt(dt: Any) -> str:
    """Format datetime or date in user-friendly format."""
    if isinstance(dt, datetime):
        if dt.tzinfo is not None:
            # Show local time if aware
            return dt.astimezone().strftime("%Y-%m-%d %H:%M")
        return dt.strftime("%Y-%m-%d %H:%M")
    elif hasattr(dt, "strftime"):  # date
        return dt.strftime("%Y-%m-%d")
    return str(dt)


def decode_etm_value(val: Any) -> list[str]:
    """Decode any etm-encoded value(s) into user-facing strings."""
    if isinstance(val, list):
        results = []
        for v in val:
            results.extend(decode_etm_value(v))
        return results

    if not isinstance(val, str):
        return [str(val)]

    if m := TAG_PATTERNS["D"].match(val):
        dt = datetime.strptime(m.group(1), "%Y%m%d").date()
        return [format_dt(dt)]

    if m := TAG_PATTERNS["T"].match(val):
        ts, kind = m.groups()
        dt = datetime.strptime(ts, "%Y%m%dT%H%M")
        if kind == "A":
            dt = dt.replace(tzinfo=timezone.utc)
        return [format_dt(dt)]

    if m := TAG_PATTERNS["I"].match(val):
        return [m.group(1)]

    if m := TAG_PATTERNS["P"].match(val):
        return [m.group(1)]  # handled specially in @f/&f

    if m := TAG_PATTERNS["W"].match(val):
        return [m.group(1)]

    return [val]


# ------------------------------------------------------------
# Conversion logic
# ------------------------------------------------------------
TYPE_MAP = {
    "*": "*",
    "-": "~",  # task
    "%": "%",
    "!": "?",
    "~": "+",  # goal
}


def etm_completion_to_token(val: str) -> str:
    """Convert {P}: completion pair into @f token."""
    if isinstance(val, str) and val.startswith("{P}:"):
        pair = val[4:]
        comp, due = pair.split("->")
        comp_val = decode_etm_value(comp.strip())[0]
        due_val = decode_etm_value(due.strip())[0]
        if comp_val == due_val:
            return f"@f {comp_val}"
        else:
            return f"@f {comp_val}, {due_val}"
    return f"@f {val}"


def etm_rrule_to_tokens(rules: list[dict]) -> list[str]:
    tokens = []
    for r in rules:
        freq = r.get("r")
        if not freq:
            continue
        parts = [f"@r {freq}"]
        for k, v in r.items():
            if k == "r":
                continue
            vals = decode_etm_value(v)
            parts.append(f"&{k} {','.join(vals)}")
        tokens.append(" ".join(parts))
    return tokens


def etm_jobs_to_tokens(jobs: list[dict]) -> list[str]:
    tokens = []
    for j in jobs:
        subj = j.get("j", "").strip()
        parts = [f"@~ {subj}"]

        # job id + prereqs
        if "i" in j:
            reqs = ",".join(j.get("p", [])) if j.get("p") else ""
            if reqs:
                parts.append(f"&r {j['i']}: {reqs}")
            else:
                parts.append(f"&r {j['i']}")

        # completion
        if "f" in j and isinstance(j["f"], str) and j["f"].startswith("{P}:"):
            pair = j["f"][4:]
            comp, due = pair.split("->")
            comp_val = decode_etm_value(comp.strip())[0]
            due_val = decode_etm_value(due.strip())[0]
            if comp_val == due_val:
                parts.append(f"&f {comp_val}")
            else:
                parts.append(f"&f {comp_val}, {due_val}")

        # other keys
        for k2, v2 in j.items():
            if k2 in ("j", "i", "p", "summary", "status", "req", "f"):
                continue
            parts.append(f"&{k2} {','.join(decode_etm_value(v2))}")

        tokens.append(" ".join(parts))
    return tokens


def encode_for_token(key: str, val: Any) -> str:
    vals = decode_etm_value(val)
    return f"@{key} {','.join(vals)}"


def etm_to_tokens(item: dict, rid: str | None = None) -> list[str]:
    tokens = []
    itemtype = TYPE_MAP.get(item.get("itemtype"), item.get("itemtype", "?"))
    subject = item.get("summary", "").strip()
    tokens.append(f"{itemtype} {subject}")

    for key, val in item.items():
        if key in ("itemtype", "summary", "created", "modified", "h"):
            continue

        if key in ("+", "-", "w"):
            vals = decode_etm_value(val)
            tokens.append(f"@{key} {', '.join(vals)}")

        elif key == "a":
            # multiple alerts allowed
            for alert in val:  # each is [times, commands]
                times, cmds = alert
                timestr = ", ".join(decode_etm_value(times))
                cmdstr = ", ".join(decode_etm_value(cmds))
                tokens.append(f"@a {timestr}: {cmdstr}")

        elif key == "u":
            # used-time entries: list of [timedelta, date]
            for pair in val:
                if isinstance(pair, list) and len(pair) == 2:
                    td = decode_etm_value(pair[0])[0]
                    day = decode_etm_value(pair[1])[0]
                    tokens.append(f"@u {td}: {day}")

        elif key == "r":
            tokens.extend(etm_rrule_to_tokens(val))

        elif key == "j":
            tokens.extend(etm_jobs_to_tokens(val))

        elif key == "f":
            tokens.append(etm_completion_to_token(val))

        else:
            tokens.append(encode_for_token(key, val))

    if rid:
        tokens.append(f"@ETM {rid}")

    return tokens


def tokens_to_entry(tokens: list[str]) -> str:
    """Format tokens into entry string with indentation."""
    entry = [tokens[0]]
    for tok in tokens[1:]:
        if tok.startswith("@d "):
            lines = tok[3:].splitlines()
            entry.append("  @d " + lines[0])
            for ln in lines[1:]:
                entry.append("     " + ln)
        else:
            entry.append("  " + tok)
    return "\n".join(entry)


# ------------------------------------------------------------
# Migration driver
# ------------------------------------------------------------
def migrate(infile: str, outfile: str | None = None) -> None:
    with open(infile, "r", encoding="utf-8") as f:
        data = json.load(f)

    sections = ["items", "archive"]
    out_lines = []

    for section in sections:
        if section not in data:
            continue
        out_lines.append(f"#### {section} ####")
        for rid, item in data[section].items():
            tokens = etm_to_tokens(item, rid)
            entry = tokens_to_entry(tokens)
            out_lines.append(entry)
            out_lines.append("")  # blank line between items

    out_text = "\n".join(out_lines)
    if outfile:
        Path(outfile).write_text(out_text, encoding="utf-8")
    else:
        print(out_text)


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: migrate_etm_to_tklr.py infile.json [outfile.txt]")
    else:
        infile = sys.argv[1]
        outfile = sys.argv[2] if len(sys.argv) > 2 else None
        migrate(infile, outfile)
