from __future__ import annotations

import base64
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

__all__ = ["MIGRATION_ITEM_TYPES", "migrate_etm_directory"]

# Supported ETM item types for filtering.
MIGRATION_ITEM_TYPES = ("*", "-", "%", "~", "!")

TAG_PATTERNS = {
    "D": re.compile(r"^\{D\}:(\d{8})$"),
    "T": re.compile(r"^\{T\}:(\d{8}T\d{4})([AN])$"),
    "I": re.compile(r"^\{I\}:(.+)$"),
    "P": re.compile(r"^\{P\}:(.+)$"),
    "W": re.compile(r"^\{W\}:(.+)$"),
}

BARE_DT = re.compile(r"^(\d{8})T(\d{4})([ANZ]?)$")

AND_KEY_MAP = {
    "n": "M",
    "h": "H",
    "M": "m",
}

TYPE_MAP = {
    "*": "*",
    "-": "~",
    "%": "%",
    "!": "?",
    "~": "+",
}

MASK_PREFIX = "{M}:"


def decode_mask(secret: str, encoded: str) -> str:
    try:
        data = base64.urlsafe_b64decode(encoded).decode()
    except Exception:
        return encoded
    decrypted: list[str] = []
    for i, ch in enumerate(data):
        key_c = secret[i % len(secret)]
        decrypted.append(chr((256 + ord(ch) - ord(key_c)) % 256))
    return "".join(decrypted)


def format_dt(dt: Any) -> str:
    if isinstance(dt, datetime):
        if dt.tzinfo is not None:
            return dt.astimezone().strftime("%Y-%m-%d %H:%M")
        return dt.strftime("%Y-%m-%d %H:%M")
    if hasattr(dt, "strftime"):
        return dt.strftime("%Y-%m-%d")
    return str(dt)


def parse_etm_date_or_dt(val: Any) -> list[str]:
    if isinstance(val, list):
        out: list[str] = []
        for v in val:
            out.extend(parse_etm_date_or_dt(v))
        return out
    if not isinstance(val, str):
        return [str(val)]
    if m := TAG_PATTERNS["D"].match(val):
        d = datetime.strptime(m.group(1), "%Y%m%d").date()
        return [format_dt(d)]
    if m := TAG_PATTERNS["T"].match(val):
        ts, kind = m.groups()
        dt = datetime.strptime(ts, "%Y%m%dT%H%M")
        if kind in ("A", "Z"):
            dt = dt.replace(tzinfo=timezone.utc)
        return [format_dt(dt)]
    if m := TAG_PATTERNS["P"].match(val):
        pair = m.group(1)
        left_raw, right_raw = [s.strip() for s in pair.split("->", 1)]
        left_fmt = parse_etm_date_or_dt(left_raw)[0]
        right_fmt = parse_etm_date_or_dt(right_raw)[0]
        return [f"{left_fmt} -> {right_fmt}"]
    if m := TAG_PATTERNS["I"].match(val):
        return [m.group(1)]
    if m := TAG_PATTERNS["W"].match(val):
        return [m.group(1)]
    if m := BARE_DT.match(val):
        ymd, hm, suf = m.groups()
        dt = datetime.strptime(f"{ymd}T{hm}", "%Y%m%dT%H%M")
        if suf in ("A", "Z"):
            dt = dt.replace(tzinfo=timezone.utc)
        return [format_dt(dt)]
    return [val]


def format_subvalue(val: Any) -> list[str]:
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


def reorder_tokens(tokens: list[str]) -> list[str]:
    if not tokens:
        return tokens
    header = [tokens[0]]
    rest = tokens[1:]
    start_tokens = [t for t in rest if t.startswith("@s ")]
    recur_tokens = [t for t in rest if t.startswith("@r ")]
    plus_tokens = [t for t in rest if t.startswith("@+ ")]
    minus_tokens = [t for t in rest if t.startswith("@- ")]
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
    ordered += header
    ordered += start_tokens
    ordered += recur_tokens
    ordered += plus_tokens
    ordered += minus_tokens
    ordered += others
    return ordered


def _append_description_token(
    tokens: list[str],
    content: str,
    insert_at: int | None,
) -> None:
    index = insert_at if insert_at is not None else len(tokens)
    tokens.insert(index, f"@d {content}")


def etm_to_tokens(
    item: dict,
    key: str | None,
    *,
    include_record_id: bool,
    secret: str | None,
) -> list[str]:
    raw_type = item.get("itemtype", "?")
    has_jobs = bool(item.get("j"))
    itemtype = TYPE_MAP.get(raw_type, raw_type)
    if itemtype == "~" and has_jobs:
        itemtype = "^"
    summary = item.get("summary", "")
    tokens = [f"{itemtype} {summary}"]

    o_val = item.get("o")
    convert_o_from_r = False
    new_o_value = None
    skip_o_key = False
    if o_val == "s":
        itemtype = "*"
        tokens[0] = f"{itemtype} {summary}"
        skip_o_key = True
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
                skip_o_key = True

    description_value: str | None = None
    description_insert_index: int | None = None
    hashtag_suffix: list[str] = []

    for k, v in item.items():
        if k in {"itemtype", "summary", "created", "modified", "h", "k", "q"}:
            continue
        if k == "d":
            description_value = str(v)
            if description_insert_index is None:
                description_insert_index = len(tokens)
            continue
        if k == "t":
            vals = format_subvalue(v)
            if vals:
                hashtags: list[str] = []
                for entry in vals:
                    parts = [p.strip() for p in entry.split() if p.strip()]
                    if parts:
                        hashtags.append("#" + "_".join(parts))
                if hashtags:
                    hashtag_suffix.extend(hashtags)
                    if description_insert_index is None:
                        description_insert_index = len(tokens)
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
        if k == "r":
            if convert_o_from_r and new_o_value:
                tokens.append(f"@o {new_o_value}")
                continue
            if isinstance(v, list):
                for rd in v:
                    if isinstance(rd, dict):
                        subparts: list[str] = []
                        freq = rd.get("r")
                        if freq:
                            subparts.append(freq)
                        for subk, subv in rd.items():
                            if subk == "r":
                                continue
                            legacy_rrule_map = {
                                "M": "m",
                                "m": "d",
                                "h": "H",
                                "n": "M",
                            }
                            mapped_subk = legacy_rrule_map.get(subk, subk)
                            mapped = AND_KEY_MAP.get(mapped_subk, mapped_subk)
                            vals = format_subvalue(subv)
                            if vals:
                                subparts.append(f"&{mapped} {', '.join(vals)}")
                        tokens.append(f"@r {' '.join(subparts)}")
            continue
        if k == "j":
            if isinstance(v, list):
                for jd in v:
                    if isinstance(jd, dict):
                        parts: list[str] = []
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
                        fstr = jd.get("f")
                        if isinstance(fstr, str) and fstr.startswith("{P}:"):
                            fvalue = format_subvalue(fstr)
                            if fvalue:
                                parts.append(f"&f {', '.join(fvalue)}")
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
            # skip 'u' key entirely
            continue
            # if isinstance(v, list):
            #     for used in v:
            #         if isinstance(used, list) and len(used) == 2:
            #             td = format_subvalue(used[0])[0]
            #             d = format_subvalue(used[1])[0]
            #             print(f"{used = }, {td = }, {d = }")
            #             tokens.append(f"@u {td}: {d}")
            # continue
        if k in {"+", "-", "w"}:
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
            if skip_o_key:
                continue
            vals = format_subvalue(v)
            if vals:
                tokens.append(f"@o {', '.join(vals)}")
            continue
        if k == "m":
            vals = format_subvalue(v)
            if vals:
                cleaned: list[str] = []
                for value in vals:
                    masked = value
                    if masked.startswith(MASK_PREFIX):
                        masked = masked.split(":", 1)[1]
                    if secret:
                        masked = decode_mask(secret, masked)
                    cleaned.append(masked)
                tokens.append(f"@m {' '.join(cleaned)}")
            continue
        vals = format_subvalue(v)
        if vals:
            tokens.append(f"@{k} {', '.join(vals)}")

    if description_value is not None or hashtag_suffix:
        content = description_value or ""
        if hashtag_suffix:
            suffix = " ".join(hashtag_suffix)
            content = f"{content} {suffix}" if content else suffix
        _append_description_token(tokens, content, description_insert_index)

    tokens = reorder_tokens(tokens)
    if include_record_id and key is not None:
        tokens.append(f"@# {key}")
    return tokens


def tokens_to_entry(tokens: Iterable[str]) -> str:
    return "\n".join(tokens)


def migrate_etm_directory(
    etm_dir: Path,
    outfile: Path,
    *,
    secret: str | None = None,
    include_archive: bool = False,
    include_record_ids: bool = False,
    allowed_item_types: set[str] | None = None,
) -> int:
    json_path = etm_dir / "etm.json"
    if not json_path.exists():
        raise FileNotFoundError(f"No etm.json found in {etm_dir}")

    data = json.loads(json_path.read_text(encoding="utf-8"))
    sections = ["items"]
    if include_archive:
        sections.append("archive")

    out_lines: list[str] = []
    count = 0
    for section in sections:
        records = data.get(section, {})
        if not records:
            continue
        out_lines.append(f"#### {section} ####")
        out_lines.append("")
        for record_id, item in records.items():
            raw_type = item.get("itemtype", "?")
            if allowed_item_types and raw_type not in allowed_item_types:
                continue
            tokens = etm_to_tokens(
                item,
                record_id if include_record_ids else None,
                include_record_id=include_record_ids,
                secret=secret,
            )
            out_lines.append(tokens_to_entry(tokens))
            out_lines.append("...")
            out_lines.append("")
            count += 1

    text = "\n".join(out_lines).rstrip() + ("\n" if out_lines else "")
    outfile.parent.mkdir(parents=True, exist_ok=True)
    outfile.write_text(text, encoding="utf-8")
    return count
