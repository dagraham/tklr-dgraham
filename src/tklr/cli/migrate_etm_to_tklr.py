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

AND_KEY_MAP = {
    "n": "M",  # minutes -> &M
    "h": "H",  # hours   -> &H
    "M": "m",  # months  -> &m
    # others unchanged
}

TYPE_MAP = {
    "*": "*",
    "-": "~",  # task
    "%": "%",
    "!": "?",
    "~": "+",  # goal
}

# ------------------------------------------------------------
# Helpers
# ------------------------------------------------------------


def parse_etm_date_or_dt(raw: str):
    """Parse etm-style encoded values into Python objects (date, dt, td, etc)."""
    if raw.startswith("{D}:"):
        dt = datetime.strptime(raw[4:], "%Y%m%d").date()
        return [format_dt(dt)]
    if raw.startswith("{T}:"):
        s = raw[4:]
        kind = s[-1]  # A or N
        s = s[:-1]
        dt = datetime.strptime(s, "%Y%m%dT%H%M")
        if kind == "A":
            dt = dt.replace(tzinfo=timezone.utc)
        return [format_dt(dt)]
    if raw.startswith("{I}:"):
        return [raw[4:]]  # timedelta string
    if raw.startswith("{P}:"):
        return [raw[4:]]  # completion pair, handled specially
    if raw.startswith("{W}:"):
        return [raw[4:]]  # weekday rule
    return [raw]  # fallback passthrough


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


def etm_to_tokens(item: dict, key: str | None, include_etm: bool = True) -> list[str]:
    """Convert an etm JSON entry into a list of tklr tokens."""

    tokens = []
    itemtype = item.get("itemtype", "?")
    if itemtype == "?":
        print(f"missing itemtype: {item = }")
        return []
    mapped_type = TYPE_MAP.get(itemtype, itemtype)  # <-- use TYPE_MAP here
    summary = item.get("summary", "")
    tokens.append(f"{mapped_type} {summary}")

    for k, v in item.items():
        if k in {"itemtype", "summary", "created", "modified", "h", "k", "q", "o"}:
            continue

        # description
        if k == "d":
            tokens.append(f"@d {v}")
            continue

        # start datetime
        if k == "s":
            vals = format_subvalue(v)
            if vals:
                tokens.append(f"@s {vals[0]}")
            continue

        # finish/completion
        if k == "f":
            vals = format_subvalue(v)
            if vals:
                if "->" in vals[0]:
                    left, right = [s.strip() for s in vals[0].split("->", 1)]
                    if left != right:
                        tokens.append(f"@f {left}, {right}")
                    else:
                        tokens.append(f"@f {left}")
                else:
                    tokens.append(f"@f {vals[0]}")
            continue

        # recurrence rules
        if k == "r":
            if isinstance(v, list):
                for rd in v:
                    if isinstance(rd, dict):
                        subparts = []
                        freq = rd.get("r")
                        if freq:
                            subparts.append(freq)
                        for subk, subv in rd.items():
                            if subk == "r":
                                continue
                            mapped = AND_KEY_MAP.get(subk, subk)
                            vals = format_subvalue(subv)
                            if vals:
                                subparts.append(f"&{mapped} {', '.join(vals)}")
                        tokens.append(f"@r {' '.join(subparts)}")
            continue

        # jobs
        if k == "j":
            if isinstance(v, list):
                for jd in v:
                    if isinstance(jd, dict):
                        subparts = []
                        job_summary = jd.get("j", "")
                        if job_summary:
                            subparts.append(job_summary)
                        for subk, subv in jd.items():
                            if subk in {"j", "summary", "status"}:
                                continue
                            mapped = AND_KEY_MAP.get(subk, subk)
                            vals = format_subvalue(subv)
                            if vals:
                                subparts.append(f"&{mapped} {', '.join(vals)}")
                        tokens.append(f"@~ {' '.join(subparts)}")
            continue

        # alerts
        if k == "a":
            if isinstance(v, list):
                for adef in v:
                    if isinstance(adef, list) and len(adef) == 2:
                        times = [x for part in adef[0] for x in format_subvalue(part)]
                        cmds = [x for part in adef[1] for x in format_subvalue(part)]
                        tokens.append(f"@a {','.join(times)}: {','.join(cmds)}")
            continue

        # used time
        if k == "u":
            if isinstance(v, list):
                for used in v:
                    if isinstance(used, list) and len(used) == 2:
                        td = format_subvalue(used[0])[0]
                        d = format_subvalue(used[1])[0]
                        tokens.append(f"@u {td}: {d}")
            continue

        # multi-datetimes (RDATE/EXDATE/etc.)
        if k in {"+", "-", "w"}:
            if isinstance(v, list):
                vals = []
                for sub in v:
                    vals.extend(format_subvalue(sub))
                if vals:
                    tokens.append(f"@{k} {', '.join(vals)}")
            continue

        # everything else
        vals = format_subvalue(v)
        if vals:
            tokens.append(f"@{k} {', '.join(vals)}")

    # only include @ETM if requested
    if include_etm and key is not None:
        tokens.append(f"@# {key}")

    return tokens


def format_subvalue(val) -> list[str]:
    """
    Normalize etm json values into lists of strings for tokens.
    - Always returns a list of strings
    - Handles atomic values and lists
    - Runs through parse_etm_date_or_dt when tagged
    """
    results: list[str] = []
    if isinstance(val, list):
        for v in val:
            results.extend(format_subvalue(v))
    elif isinstance(val, str):
        results.extend(parse_etm_date_or_dt(val))
    elif val is None:
        return []
    else:
        results.append(str(val))
    return results


# def tokens_to_entry(tokens: list[str]) -> str:
#     """Format tokens into entry string with indentation."""
#     entry = [tokens[0]]
#     for tok in tokens[1:]:
#         if tok.startswith("@d "):
#             lines = tok[3:].splitlines()
#             entry.append("  @d " + lines[0])
#             for ln in lines[1:]:
#                 entry.append("     " + ln)
#         else:
#             entry.append("  " + tok)
#     return "\n".join(entry)
#


def tokens_to_entry(tokens: list[str]) -> str:
    """Convert a list of tokens into a formatted entry string."""
    return "\n".join(tokens)


# ------------------------------------------------------------
# Migration driver
# ------------------------------------------------------------
# def migrate(
#     infile: str,
#     outfile: str | None = None,
#     include_etm: bool = True,
#     section: str = "both",
# ) -> None:
#     with open(infile, "r", encoding="utf-8") as f:
#         data = json.load(f)
#
#     sections = []
#     if section in ("both", "items"):
#         sections.append("items")
#     if section in ("both", "archive"):
#         sections.append("archive")
#
#     out_lines = []
#
#     for sec in sections:
#         if sec not in data:
#             continue
#         out_lines.append(f"#### {sec} ####")
#
#         first = True
#         for rid, item in data[sec].items():
#             if not first:
#                 out_lines.append("")  # blank line *before* next entry
#             first = False
#
#             tokens = etm_to_tokens(item, rid, include_etm=include_etm)
#             entry = tokens_to_entry(tokens)
#             out_lines.append(entry)
#
#     out_text = "\n".join(out_lines)
#     if outfile:
#         Path(outfile).write_text(out_text, encoding="utf-8")
#     else:
#         print(out_text)


def migrate(
    infile: str,
    outfile: str | None = None,
    include_etm: bool = True,
    section: str = "both",
) -> None:
    with open(infile, "r", encoding="utf-8") as f:
        data = json.load(f)

    sections = []
    if section in ("both", "items"):
        sections.append("items")
    if section in ("both", "archive"):
        sections.append("archive")

    out_lines = []

    for sec in sections:
        if sec not in data:
            continue
        out_lines.append(f"#### {sec} ####")
        out_lines.append("")  # blank line after header

        for rid, item in data[sec].items():
            tokens = etm_to_tokens(item, rid, include_etm=include_etm)
            entry = tokens_to_entry(tokens)
            out_lines.append(entry)
            out_lines.append("...")  # end-of-record marker
            out_lines.append("")  # blank line before next record

    out_text = "\n".join(out_lines).rstrip() + "\n"
    if outfile:
        Path(outfile).write_text(out_text, encoding="utf-8")
    else:
        print(out_text)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Migrate etm.json (TinyDB) records into tklr batch entry format"
    )
    parser.add_argument("infile", help="Path to etm.json")
    parser.add_argument("outfile", nargs="?", help="Optional output file")
    parser.add_argument("--no-etm", action="store_true", help="Omit @ETM annotations")
    parser.add_argument(
        "--section",
        choices=["items", "archive", "both"],
        default="both",
        help="Which section(s) to migrate (default: both)",
    )
    args = parser.parse_args()

    migrate(
        args.infile, args.outfile, include_etm=not args.no_etm, section=args.section
    )
