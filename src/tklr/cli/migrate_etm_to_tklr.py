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

BARE_DT = re.compile(r"^(\d{8})T(\d{4})([ANZ]?)$")

AND_KEY_MAP = {
    "n": "M",  # minutes -> &M
    "h": "H",  # hours   -> &H
    "M": "m",  # months  -> &m
    # others unchanged
}

TYPE_MAP = {
    "*": "*",  # event
    "-": "~",  # task
    "%": "%",  # note
    "!": "?",  # inbox
    "~": "+",  # goal
}


# ------------------------------------------------------------
# Helpers
# ------------------------------------------------------------


def parse_etm_date_or_dt(val) -> list[str]:
    """
    Decode ETM-encoded values (dates, datetimes, intervals, completions, weekdays).
    Always returns a list[str]. Handles:
      - lists (recursively)
      - {D}:YYYYMMDD
      - {T}:YYYYMMDDTHHMM[A|N|Z]
      - {P}:<dt_str> -> <dt_str>   (returns one string: 'left -> right' with both sides formatted)
      - {I}:<interval> (timedelta string passthrough)
      - {W}:<weekday spec> (passthrough)
      - bare datetimes: YYYYMMDDTHHMM[A|N|Z]? (formatted)
      - everything else: passthrough
    """
    # lists: flatten
    if isinstance(val, list):
        out: list[str] = []
        for v in val:
            out.extend(parse_etm_date_or_dt(v))
        return out

    # non-strings: stringify
    if not isinstance(val, str):
        return [str(val)]

    # {D}
    if m := TAG_PATTERNS["D"].match(val):
        d = datetime.strptime(m.group(1), "%Y%m%d").date()
        return [format_dt(d)]

    # {T}
    if m := TAG_PATTERNS["T"].match(val):
        ts, kind = m.groups()
        dt = datetime.strptime(ts, "%Y%m%dT%H%M")
        if kind in ("A", "Z"):
            dt = dt.replace(tzinfo=timezone.utc)
        return [format_dt(dt)]

    # {P}: <dt_str> -> <dt_str>  → return a single "left -> right" string with both sides formatted
    if m := TAG_PATTERNS["P"].match(val):
        pair = m.group(1)
        left_raw, right_raw = [s.strip() for s in pair.split("->", 1)]

        # reuse this function to format each side; take first result from the returned list
        left_fmt = parse_etm_date_or_dt(left_raw)[0]
        right_fmt = parse_etm_date_or_dt(right_raw)[0]
        return [f"{left_fmt} -> {right_fmt}"]

    # {I} interval and {W} weekday: passthrough content
    if m := TAG_PATTERNS["I"].match(val):
        return [m.group(1)]
    if m := TAG_PATTERNS["W"].match(val):
        return [m.group(1)]

    # bare datetime like 20250807T2300A / 20250807T2300 / 20250807T2300N
    if m := BARE_DT.match(val):
        ymd, hm, suf = m.groups()
        dt = datetime.strptime(f"{ymd}T{hm}", "%Y%m%dT%H%M")
        if suf in ("A", "Z"):
            dt = dt.replace(tzinfo=timezone.utc)
        return [format_dt(dt)]

    # fallback
    return [val]


def format_dt(dt: Any) -> str:
    """Format datetime or date in user-friendly format."""
    if isinstance(dt, datetime):
        if dt.tzinfo is not None:
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
        pair = m.groups(1)[0].split("->")
        print(f"{m.groups(1)[0] = }, {pair = }")
        res = []
        for dt_str in pair:
            dt_str = dt_str.strip()
            dt = None
            _l = len(dt_str)
            if _l == 8:
                dt = datetime.strptime(dt_str, "%Y%m%d")
            elif _l == 13:
                dt = datetime.strptime(dt_str, "%Y%m%dT%H%M")
            elif _l == 14:
                dt = datetime.strptime(dt_str[:-1], "%Y%m%dT%H%M")
                if dt_str[-1] == "A":
                    dt.replace(tzinfo=timezone.utc)
            else:
                print("{_l = }, {dt_str = }")

            if dt:
                res.append(format_dt(dt))
        return ", ".join(res)

    if m := TAG_PATTERNS["W"].match(val):
        return [m.group(1)]

    return [val]


def format_subvalue(val) -> list[str]:
    """Normalize etm json values into lists of strings for tokens."""
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


# ------------------------------------------------------------
# Conversion logic
# ------------------------------------------------------------
# def etm_to_tokens(item: dict, key: str | None, include_etm: bool = True) -> list[str]:
#     """Convert an etm JSON entry into a list of tklr tokens."""
#
#     raw_type = item.get("itemtype", "?")
#     has_jobs = bool(item.get("j"))  # detect jobs
#     itemtype = TYPE_MAP.get(raw_type, raw_type)
#
#     # Promote tasks-with-jobs to projects
#     if itemtype == "~" and has_jobs:
#         itemtype = "^"
#
#     summary = item.get("summary", "")
#     tokens = [f"{itemtype} {summary}"]
#
#     for k, v in item.items():
#         if k in {"itemtype", "summary", "created", "modified", "h", "k", "q"}:
#             continue
#
#         if k == "d":  # description
#             tokens.append(f"@d {v}")
#             continue
#
#         if k == "b":  # beginby
#             tokens.append(f"@b {v}d")
#             continue
#
#         if k == "z" and v == "float":
#             tokens.append("@z none")
#             continue
#
#         if k == "s":  # start datetime
#             vals = format_subvalue(v)
#             if vals:
#                 tokens.append(f"@s {vals[0]}")
#             continue
#
#         # finish/completion
#         if k == "f":
#             vals = format_subvalue(v)  # uses parse_etm_date_or_dt under the hood
#             if vals:
#                 s = vals[0]  # for @f we only expect one normalized value back
#                 if "->" in s:
#                     left, right = [t.strip() for t in s.split("->", 1)]
#                     if left == right:
#                         tokens.append(f"@f {left}")
#                     else:
#                         tokens.append(f"@f {left}, {right}")
#                 else:
#                     tokens.append(f"@f {s}")
#             continue
#
#         # if k == "r":  # recurrence rules
#         #     if isinstance(v, list):
#         #         for rd in v:
#         #             if isinstance(rd, dict):
#         #                 subparts = []
#         #                 freq = rd.get("r")
#         #                 if freq:
#         #                     subparts.append(freq)
#         #                 for subk, subv in rd.items():
#         #                     if subk == "r":
#         #                         continue
#         #                     mapped = AND_KEY_MAP.get(subk, subk)
#         #                     vals = format_subvalue(subv)
#         #                     if vals:
#         #                         subparts.append(f"&{mapped} {', '.join(vals)}")
#         #                 tokens.append(f"@r {' '.join(subparts)}")
#         #     continue
#
#         replaced_o = False  # track if @o already handled or suppressed
#
#         if k == "r":  # recurrence rules
#             # Handle legacy "@o r" (offset-repeat) form
#             if item.get("o") == "r" and itemtype in {"~", "^"}:
#                 rlist = v if isinstance(v, list) else []
#                 if rlist and isinstance(rlist[0], dict):
#                     rd = rlist[0]
#                     freq = rd.get("r")
#                     interval = rd.get("i", 1)
#                     if freq in {"y", "m", "w", "d"}:
#                         new_o_value = f"{interval}{freq}"
#                         tokens.append(f"@o {new_o_value}")
#                         replaced_o = True  # prevent later duplicate
#                 # skip normal @r generation
#                 continue
#
#             # --- Normal recurring events ---
#             if isinstance(v, list):
#                 for rd in v:
#                     if isinstance(rd, dict):
#                         subparts = []
#                         freq = rd.get("r")
#                         if freq:
#                             subparts.append(freq)
#                         for subk, subv in rd.items():
#                             if subk == "r":
#                                 continue
#                             mapped = AND_KEY_MAP.get(subk, subk)
#                             vals = format_subvalue(subv)
#                             if vals:
#                                 subparts.append(f"&{mapped} {', '.join(vals)}")
#                         tokens.append(f"@r {' '.join(subparts)}")
#             continue
#
#         # --- Handle legacy or special "@o" forms ---
#         if k == "o":
#             # Skip entirely if already handled by @o r
#             if replaced_o:
#                 continue
#
#             # Handle legacy "@o s" (shift → convert itemtype)
#             if v == "s":
#                 itemtype = "*"  # promote to event
#                 continue  # omit entirely, no @o token
#
#             # Normal @o
#             vals = format_subvalue(v)
#             if vals:
#                 tokens.append(f"@o {', '.join(vals)}")
#             continue
#
#         # jobs
#         if k == "j":
#             if isinstance(v, list):
#                 for jd in v:
#                     if isinstance(jd, dict):
#                         parts = []
#
#                         # job subject
#                         job_summary = jd.get("j", "").strip()
#                         if job_summary:
#                             parts.append(job_summary)
#
#                         # build &r from id + prereqs
#                         jid = jd.get("i")
#                         prereqs = jd.get("p", [])
#                         if jid:
#                             if prereqs:
#                                 parts.append(f"&r {jid}: {', '.join(prereqs)}")
#                             else:
#                                 parts.append(f"&r {jid}")
#
#                         # completion (&f same as @f)
#                         if (
#                             "f" in jd
#                             and isinstance(jd["f"], str)
#                             and jd["f"].startswith("{P}:")
#                         ):
#                             pair = jd["f"][4:]
#                             comp, due = pair.split("->")
#                             comp_val = decode_etm_value(comp.strip())[0]
#                             due_val = decode_etm_value(due.strip())[0]
#                             if comp_val == due_val:
#                                 parts.append(f"&f {comp_val}")
#                             else:
#                                 parts.append(f"&f {comp_val}, {due_val}")
#
#                         # other keys (skip ones we already handled)
#                         for subk, subv in jd.items():
#                             if subk in {"j", "i", "p", "summary", "status", "req", "f"}:
#                                 continue
#                             vals = format_subvalue(subv)
#                             if vals:
#                                 parts.append(f"&{subk} {', '.join(vals)}")
#
#                         tokens.append(f"@~ {' '.join(parts)}")
#             continue
#
#         if k == "a":  # alerts
#             if isinstance(v, list):
#                 for adef in v:
#                     if isinstance(adef, list) and len(adef) == 2:
#                         times = [x for part in adef[0] for x in format_subvalue(part)]
#                         cmds = [x for part in adef[1] for x in format_subvalue(part)]
#                         tokens.append(f"@a {','.join(times)}: {','.join(cmds)}")
#             continue
#
#         if k == "u":  # used time
#             if isinstance(v, list):
#                 for used in v:
#                     if isinstance(used, list) and len(used) == 2:
#                         td = format_subvalue(used[0])[0]
#                         d = format_subvalue(used[1])[0]
#                         tokens.append(f"@u {td}: {d}")
#             continue
#
#         if k in {"+", "-", "w"}:  # multi-datetimes (RDATE/EXDATE/etc.)
#             if isinstance(v, list):
#                 vals = []
#                 for sub in v:
#                     vals.extend(format_subvalue(sub))
#                 if vals:
#                     tokens.append(f"@{k} {', '.join(vals)}")
#             continue
#
#         # everything else
#         vals = format_subvalue(v)
#         if vals:
#             tokens.append(f"@{k} {', '.join(vals)}")
#
#     if include_etm and key is not None:
#         tokens.append(f"@# {key}")
#
#     return tokens


def reorder_tokens(tokens: list[str]) -> list[str]:
    """
    Ensure logical ordering of tokens for valid parsing:
      1. itemtype/subject first
      2. @s before @r or @+
      3. @r before @-
      4. everything else after
    """
    if not tokens:
        return tokens

    # First token should always be itemtype + subject
    header = [tokens[0]]
    rest = tokens[1:]

    start_tokens = [t for t in rest if t.startswith("@s ")]
    recur_tokens = [t for t in rest if t.startswith("@r ")]
    plus_tokens = [t for t in rest if t.startswith("@+ ")]
    minus_tokens = [t for t in rest if t.startswith("@- ")]

    # Everything else stays in natural order
    others = [
        t
        for t in rest
        if not (
            t.startswith("@s ")
            or t.startswith("@r ")
            or t.startswith("@+ ")
            or t.startswith("@- ")
        )
    ]

    ordered = []
    ordered += header  # itemtype + subject
    ordered += start_tokens  # @s before @r
    ordered += recur_tokens  # @r before @+
    ordered += plus_tokens  # @+ before @-
    ordered += minus_tokens  # @-
    ordered += others  # everything else

    return ordered


def etm_to_tokens(item: dict, key: str | None, include_etm: bool = True) -> list[str]:
    raw_type = item.get("itemtype", "?")
    has_jobs = bool(item.get("j"))
    itemtype = TYPE_MAP.get(raw_type, raw_type)

    # promote tasks-with-jobs to projects
    if itemtype == "~" and has_jobs:
        itemtype = "^"

    summary = item.get("summary", "")
    tokens = [f"{itemtype} {summary}"]

    # ---------- PREPASS: decide @o behavior ----------
    o_val = item.get("o")
    convert_o_from_r = False  # True → emit @o <interval><freq> and suppress @r
    new_o_value = None  # the computed "<interval><freq>" string
    skip_o_key = False  # True → do not emit original @o key at all

    # case: "@o s" → delete @o and convert item to event
    if o_val == "s":
        itemtype = "*"  # promote to event
        tokens[0] = f"{itemtype} {summary}"
        skip_o_key = True

    # case: "@o r" on task/project with an r-rule → convert to "@o <interval><freq>"
    elif o_val == "r" and itemtype in {"~", "^"}:
        rlist = item.get("r") if isinstance(item.get("r"), list) else []
        if rlist and isinstance(rlist[0], dict):
            rd = rlist[0]
            freq = rd.get("r")
            interval = rd.get("i", 1)
            if (
                freq in {"y", "m", "w", "d", "h"}
                and isinstance(interval, int)
                and interval > 0
            ):
                new_o_value = f"{interval}{freq}"
                convert_o_from_r = True
                skip_o_key = True  # do not emit literal "@o r"

    # ---------- MAIN LOOP ----------
    for k, v in item.items():
        if k in {"itemtype", "summary", "created", "modified", "h", "k", "q"}:
            continue

        if k == "d":
            tokens.append(f"@d {v}")
            continue

        if k == "b":
            tokens.append(f"@n {v}d")
            continue

        if k == "i":
            tokens.append(f"@b {v}")
            continue

        if k == "z" and v == "float":
            tokens.append("@z none")
            continue

        if k == "s":
            vals = format_subvalue(v)
            if vals:
                tokens.append(f"@s {vals[0]}")
            continue

        if k == "f":
            vals = format_subvalue(v)
            if vals:
                s = vals[0]
                if "->" in s:
                    left, right = [t.strip() for t in s.split("->", 1)]
                    tokens.append(
                        f"@f {left}" if left == right else f"@f {left}, {right}"
                    )
                else:
                    tokens.append(f"@f {s}")
            continue

        # if k == "r":
        #     # If converting "@o r", emit the computed @o once and suppress @r entirely
        #     if convert_o_from_r and new_o_value:
        #         tokens.append(f"@o {new_o_value}")
        #         continue
        #
        #     # otherwise, normal @r parsing
        #     if isinstance(v, list):
        #         for rd in v:
        #             if isinstance(rd, dict):
        #                 subparts = []
        #                 freq = rd.get("r")
        #                 if freq:
        #                     subparts.append(freq)
        #                 for subk, subv in rd.items():
        #                     if subk == "r":
        #                         continue
        #                     mapped = AND_KEY_MAP.get(subk, subk)
        #                     vals = format_subvalue(subv)
        #                     if vals:
        #                         subparts.append(f"&{mapped} {', '.join(vals)}")
        #                 tokens.append(f"@r {' '.join(subparts)}")
        #     continue

        if k == "r":
            # If converting "@o r", emit the computed @o once and suppress @r entirely
            if convert_o_from_r and new_o_value:
                tokens.append(f"@o {new_o_value}")
                continue

            # otherwise, normal @r parsing
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

                            # --- fix legacy rrule subkeys ---
                            legacy_rrule_map = {
                                "M": "m",  # BYMONTH → &m
                                "m": "d",  # BYMONTHDAY → &d
                                "h": "H",  # BYHOUR → &H
                                "n": "M",  # BYMINUTE → &M
                            }
                            mapped_subk = legacy_rrule_map.get(subk, subk)

                            mapped = AND_KEY_MAP.get(mapped_subk, mapped_subk)
                            vals = format_subvalue(subv)
                            if vals:
                                subparts.append(f"&{mapped} {', '.join(vals)}")

                        print(f"@r {' '.join(subparts)}")

                        tokens.append(f"@r {' '.join(subparts)}")
            continue

        if k == "j":
            if isinstance(v, list):
                for jd in v:
                    if isinstance(jd, dict):
                        parts = []
                        job_summary = jd.get("j", "").strip()
                        if job_summary:
                            parts.append(job_summary)

                        jid = jd.get("i")
                        prereqs = jd.get("p", [])
                        if jid:
                            parts.append(
                                f"&r {jid}: {', '.join(prereqs)}"
                                if prereqs
                                else f"&r {jid}"
                            )

                        if (
                            "f" in jd
                            and isinstance(jd["f"], str)
                            and jd["f"].startswith("{P}:")
                        ):
                            fstr = jd["f"]
                            if not fstr:
                                return
                            fvalue = decode_etm_value(fstr)

                            print(f"{fstr = }, {fvalue = }")
                            # comp, due = pair.split("->")
                            # comp_val = decode_etm_value(comp.strip())[0]
                            # due_val = decode_etm_value(due.strip())[0]
                            parts.append(f"&f {fvalue}")

                        for subk, subv in jd.items():
                            if subk in {"j", "i", "p", "summary", "status", "req", "f"}:
                                continue
                            vals = format_subvalue(subv)
                            if vals:
                                parts.append(f"&{subk} {', '.join(vals)}")

                        tokens.append(f"@~ {' '.join(parts)}")
            continue

        if k == "a":
            if isinstance(v, list):
                for adef in v:
                    if isinstance(adef, list) and len(adef) == 2:
                        times = [x for part in adef[0] for x in format_subvalue(part)]
                        cmds = [x for part in adef[1] for x in format_subvalue(part)]
                        tokens.append(f"@a {','.join(times)}: {','.join(cmds)}")
            continue

        if k == "u":
            if isinstance(v, list):
                for used in v:
                    if isinstance(used, list) and len(used) == 2:
                        td = format_subvalue(used[0])[0]
                        d = format_subvalue(used[1])[0]
                        tokens.append(f"@u {td}: {d}")
            continue

        # if k in {"+", "-", "w"}:
        #     if isinstance(v, list):
        #         vals = []
        #         for sub in v:
        #             vals.extend(format_subvalue(sub))
        #         if vals:
        #             tokens.append(f"@{k} {', '.join(vals)}")
        #     continue

        if k in {"+", "-", "w"}:
            # drop @- if @r was converted to @o
            if k == "-" and convert_o_from_r:
                continue

            if isinstance(v, list):
                vals = []
                for sub in v:
                    vals.extend(format_subvalue(sub))
                if vals:
                    tokens.append(f"@{k} {', '.join(vals)}")
            continue

        if k == "o":
            # Skip original o if we already handled it (either "@o r" conversion or "@o s" suppression)
            if skip_o_key:
                continue
            vals = format_subvalue(v)
            if vals:
                tokens.append(f"@o {', '.join(vals)}")
            continue

        # everything else
        vals = format_subvalue(v)
        if vals:
            tokens.append(f"@{k} {', '.join(vals)}")

    tokens = reorder_tokens(tokens)

    if include_etm and key is not None:
        tokens.append(f"@# {key}")

    return tokens


# ------------------------------------------------------------
# Entry formatting
# ------------------------------------------------------------


def tokens_to_entry(tokens: list[str]) -> str:
    """Convert a list of tokens into a formatted entry string."""
    return "\n".join(tokens)


# ------------------------------------------------------------
# Migration driver
# ------------------------------------------------------------
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

    count = 0
    for sec in sections:
        if sec not in data:
            continue
        out_lines.append(f"#### {sec} ####")
        out_lines.append("")

        for rid, item in data[sec].items():
            count += 1
            tokens = etm_to_tokens(item, rid, include_etm=include_etm)
            entry = tokens_to_entry(tokens)
            out_lines.append(entry)
            out_lines.append("...")
            out_lines.append("")

    out_text = "\n".join(out_lines).rstrip() + "\n"
    if outfile:
        Path(outfile).write_text(out_text, encoding="utf-8")
    else:
        print(out_text)
    print(f"processed {count} records")


# ------------------------------------------------------------
# CLI
# ------------------------------------------------------------
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Migrate etm.json (TinyDB) records into tklr batch entry format"
    )
    parser.add_argument("infile", help="Path to etm.json")
    parser.add_argument("outfile", nargs="?", help="Optional output file")
    parser.add_argument(
        "--no-etm", action="store_true", help="Omit @# (etm unique_id) annotations"
    )
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
