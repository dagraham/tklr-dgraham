#!/usr/bin/env python3
"""
Migrate etm.json records → tklr batch entries.

Usage:
    python migrate.py etm.json [batch.txt]

By default prints to stdout. If batch.txt is given, writes there.
"""

import sys
import json
from datetime import datetime, timezone
from dateutil import tz

# -------------------------------
# Itemtype Conversion
# -------------------------------
ITEMTYPE_MAP = {
    "*": "*",  # event
    "-": "~",  # task (unless jobs → project)
    "%": "%",  # note
    "!": "?",  # inbox
    "~": "+",  # goal
}


# -------------------------------
# Date/Datetime Parsing
# -------------------------------
def parse_etm_date_or_dt(raw: str):
    if raw.startswith("{D}:"):
        return datetime.strptime(raw[4:], "%Y%m%d").date()
    if raw.startswith("{T}:"):
        val = raw[4:]
        kind = val[-1]  # A or N
        val = val[:-1]
        dt = datetime.strptime(val, "%Y%m%dT%H%M")
        if kind == "A":
            return dt.replace(tzinfo=timezone.utc)
        elif kind == "N":
            return dt
    return raw  # fallback


def etm_to_s_token(s_raw: str, z: str | None) -> str:
    if s_raw.startswith("{D}:"):
        d = parse_etm_date_or_dt(s_raw)
        return f"@s {d.isoformat()}"

    dt = parse_etm_date_or_dt(s_raw)
    if isinstance(dt, datetime) and dt.tzinfo:  # aware (UTC)
        if z == "float":
            naive = dt.replace(tzinfo=None)
            return f"@s {naive.strftime('%Y-%m-%d %H:%M')} z none"
        elif z:
            tzinfo = tz.gettz(z)
            local_dt = dt.astimezone(tzinfo)
            return f"@s {local_dt.strftime('%Y-%m-%d %H:%M')} z {z}"
        else:
            return f"@s {dt.strftime('%Y-%m-%d %H:%M')}"  # UTC
    elif isinstance(dt, datetime):
        return f"@s {dt.strftime('%Y-%m-%d %H:%M')} z none"
    return f"@s {s_raw}"


# -------------------------------
# Jobs
# -------------------------------
def job_to_token(job: dict) -> str:
    job_text = job.get("j") or job.get("summary", "").split(":")[0]

    # &r from i and p
    jid = job.get("i")
    prereqs = job.get("p", [])
    r_str = None
    if jid:
        if prereqs:
            r_str = f"&r {jid}: {','.join(prereqs)}"
        else:
            r_str = f"&r {jid}"

    # Preserve other & keys
    extras = []
    for k, v in job.items():
        if k in ("j", "summary", "status", "req", "i", "p"):
            continue
        if k.startswith("&"):
            extras.append(f"{k} {v}")
        elif len(k) == 1:
            extras.append(f"&{k} {v}")

    parts = [f"@~ {job_text}"]
    if r_str:
        parts.append(r_str)
    parts.extend(extras)

    return " ".join(parts)


# -------------------------------
# Token Conversion
# -------------------------------
def etm_to_tokens(rec: dict) -> list[str]:
    tokens = []

    # itemtype
    itemtype = rec.get("itemtype")
    if itemtype == "-":
        if "j" in rec:  # project
            tokens.append("^")
        else:
            tokens.append("~")
    elif itemtype in ITEMTYPE_MAP:
        tokens.append(ITEMTYPE_MAP[itemtype])
    else:
        tokens.append(itemtype or "?")

    # subject
    if "summary" in rec:
        tokens.append(rec["summary"])

    # other keys
    for key, val in rec.items():
        if key in ("itemtype", "summary"):
            continue
        if key == "s":
            tokens.append(etm_to_s_token(val, rec.get("z")))
        elif key == "e" and isinstance(val, str) and val.startswith("{I}:"):
            tokens.append(f"@e {val[3:]}")
        elif key == "r":
            recs = val if isinstance(val, list) else [val]
            for r in recs:
                parts = ["@r " + r.get("r", "")]
                for k, v in r.items():
                    if k == "r":
                        continue
                    parts.append(f"&{k} {v}")
                tokens.append(" ".join(parts))
        elif key == "j":
            jobs = val if isinstance(val, list) else [val]
            for job in jobs:
                tokens.append(job_to_token(job))
        elif key == "d":
            tokens.append(f"@d {val}")
        else:
            tokens.append(f"@{key} {val}")

    return tokens


# -------------------------------
# Writer
# -------------------------------
def write_entry(rec, tokens, out):
    subject = rec.get("summary", "")
    header_type = tokens[0] if tokens else "?"

    inline, block, jobs = [], [], []
    for tok in tokens[1:]:
        if tok.startswith("@d "):
            block.append(tok)
        elif tok.startswith("@s ") or tok.startswith("@r "):
            block.append(tok)
        elif tok.startswith("@~ "):
            jobs.append(tok)
        else:
            inline.append(tok)

    # Header
    line = header_type + " " + subject
    if inline:
        line += " " + " ".join(inline)
    out.write(line + "\n")

    # Block tokens
    for tok in block:
        if tok.startswith("@d "):
            desc = tok[3:]
            lines = desc.splitlines(True)  # keep \n
            if lines:
                out.write("  @d " + lines[0])  # first line
                for line in lines[1:]:
                    out.write(line)  # preserve as-is
                if not desc.endswith("\n"):
                    out.write("\n")
        else:
            out.write("  " + tok + "\n")

    # Jobs
    for job in jobs:
        out.write("  " + job + "\n")

    out.write("\n")  # blank line between entries


# -------------------------------
# Migration
# -------------------------------

#     with open(etm_path) as f:
#         data = json.load(f)
#
#     if batch_path:
#         out = open(batch_path, "w")
#     else:
#         out = sys.stdout
#
#     try:
#         for rec in data.values():
#             tokens = etm_to_tokens(rec)
#             write_entry(rec, tokens, out)
#     finally:
#         if batch_path:
#             out.close()
#
#     if batch_path:
#         print(f"Batch file written: {batch_path}")


def migrate(etm_path: str, batch_path: str | None = None):
    with open(etm_path) as f:
        data = json.load(f)

    # TinyDB dump has two sections: "items" and "archive"
    all_records = {}
    for section in ("items", "archive"):
        if section in data:
            all_records.update(data[section])

    if batch_path:
        out = open(batch_path, "w")
    else:
        out = sys.stdout

    try:
        for rec in all_records.values():
            tokens = etm_to_tokens(rec)
            write_entry(rec, tokens, out)
    finally:
        if batch_path:
            out.close()

    if batch_path:
        print(f"Batch file written: {batch_path}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: migrate.py etm.json [batch.txt]")
        sys.exit(1)

    etm_path = sys.argv[1]
    batch_path = sys.argv[2] if len(sys.argv) > 2 else None
    migrate(etm_path, batch_path)
