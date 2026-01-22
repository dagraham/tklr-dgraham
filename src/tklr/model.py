from __future__ import annotations
import os
import sqlite3
import json
from typing import Optional
from datetime import date, datetime, time, timedelta
from dateutil.rrule import rrulestr
from dateutil import parser as dateutil_parser

from typing import List, Tuple, Optional, Dict, Any, Set, Iterable
from rich import print
from tklr.tklr_env import TklrEnvironment
from tklr.mask import reveal_mask_tokens
from dateutil import tz

# from dateutil.tz import gettz
# import math
import numpy as np
from pathlib import Path
from dataclasses import dataclass, field

import shutil

# from textwrap import indent
from rich.console import Console
from rich.text import Text


from .shared import (
    HRS_MINS,
    log_msg,
    bug_msg,
    parse,
    format_datetime,
    _to_local_naive,
    datetime_from_timestamp,
    duration_in_words,
    datetime_in_words,
    fmt_utc_z,
    parse_utc_z,
    fmt_user,
    get_anchor,
    has_zero_time_component,
    is_all_day_text,
)

import re
from .item import Item
from collections import defaultdict, deque

TAG_RE = re.compile(r"(?<!\w)#([A-Za-z0-9]+)")


anniversary_regex = re.compile(r"!(\d{4})!")

BIN_ROOTS = {
    "activities",
    "journal",
    "library",
    "people",
    "places",
    "projects",
    "unlinked",
}

BIN_PATHS = [
    ["books", "library"],
    ["ideas", "library"],
    ["poetry", "library"],
    ["quotations", "library"],
    ["series", "library"],
    ["video", "library"],
]


def regexp(pattern, value):
    try:
        return re.search(pattern, value) is not None
    except TypeError:
        return False  # Handle None values gracefully


def utc_now_string():
    """Return current UTC time as 'YYYYMMDDTHHMMSS'."""
    return datetime.now(tz.UTC).strftime("%Y%m%dT%H%MZ")


def utc_now_to_seconds():
    return round(datetime.now(tz.UTC).timestamp())


def is_date(obj):
    return isinstance(obj, date) and not isinstance(obj, datetime)


DATE_FMT = "%Y%m%d"
DT_FMT = "%Y%m%dT%H%M"


def _fmt_date(d: date) -> str:
    """Return date keys in YYYYMMDD form."""
    return d.strftime(DATE_FMT)


def _fmt_naive(dt: datetime) -> str:
    """Format a datetime as local-naive minute precision (YYYYMMDDTHHMM)."""
    if dt.tzinfo is not None:
        dt = dt.astimezone(tz.tzlocal()).replace(tzinfo=None)
    return dt.strftime(DT_FMT)


def _fmt_utc(dt_aware_utc: datetime) -> str:
    """
    Format any datetime into the storage key space, preferring UTC when tz-aware.
    """
    if isinstance(dt_aware_utc, date):
        return _fmt_date(dt_aware_utc)
    if isinstance(dt_aware_utc, datetime) and dt_aware_utc.tzinfo is None:
        return _fmt_naive(dt_aware_utc)
    return dt_aware_utc.astimezone(tz.UTC).strftime(DT_FMT) + "Z"


def _to_key(dt: datetime) -> str:
    """Naive-local datetime -> 'YYYYMMDDTHHMMSS' string key."""
    return dt.strftime("%Y%m%dT%H%M")


def _today_key() -> str:
    """'YYYYMMDDTHHMMSS' for now in local time, used for lexicographic comparisons."""
    return datetime.now().strftime("%Y%m%dT%H%M")


def _split_span_local_days(
    start_local: datetime, end_local: datetime
) -> list[tuple[datetime, datetime]]:
    """
    Split a local-naive span into day segments so multi-day busy windows
    can be processed per calendar day. Returns (start, end) pairs for each day.
    """
    if isinstance(start_local, date) and not isinstance(start_local, datetime):
        start_local = datetime.combine(start_local, time.min)
    if isinstance(end_local, date) and not isinstance(end_local, datetime):
        end_local = datetime.combine(end_local, time.min)

    start_local = _to_local_naive(start_local)
    end_local = _to_local_naive(end_local)

    if end_local <= start_local:
        return [(start_local, end_local)]
    if start_local.date() == end_local.date():
        return [(start_local, end_local)]

    segs: list[tuple[datetime, datetime]] = []
    cur_start = start_local

    while cur_start.date() < end_local.date():
        day_boundary = datetime.combine(cur_start.date(), time(23, 59, 59))
        segs.append((cur_start, day_boundary))
        cur_start = datetime.combine(
            cur_start.date() + timedelta(days=1), time(0, 0, 0)
        )

    segs.append((cur_start, end_local))
    return segs


def td_str_to_td(duration_str: str) -> timedelta:
    """Convert a duration string like '1h30m20s' into a timedelta."""
    duration_str = duration_str.strip()
    sign = "+"
    if duration_str[0] in ["+", "-"]:
        sign = duration_str[0]
        duration_str = duration_str[1:]

    pattern = r"(?:(\d+)w)?(?:(\d+)d)?(?:(\d+)h)?(?:(\d+)m)?(?:(\d+)s)?"
    match = re.fullmatch(pattern, duration_str.strip())
    if not match:
        raise ValueError(f"Invalid duration format: '{duration_str}'")
    weeks, days, hours, minutes, seconds = [int(x) if x else 0 for x in match.groups()]
    if sign == "-":
        return -timedelta(
            weeks=weeks, days=days, hours=hours, minutes=minutes, seconds=seconds
        )
    else:
        return timedelta(
            weeks=weeks, days=days, hours=hours, minutes=minutes, seconds=seconds
        )


def td_str_to_seconds(duration_str: str) -> int:
    """Convert a duration string like '1h30m20s' into a timedelta."""
    duration_str = duration_str.strip()
    if not duration_str:
        return 0
    sign = "+"
    if duration_str[0] in ["+", "-"]:
        sign = duration_str[0]
        duration_str = duration_str[1:]

    pattern = r"(?:(\d+)w)?(?:(\d+)d)?(?:(\d+)h)?(?:(\d+)m)?(?:(\d+)s)?"
    match = re.fullmatch(pattern, duration_str.strip())
    if not match:
        raise ValueError(f"Invalid duration format: '{duration_str}'")
    weeks, days, hours, minutes, seconds = [int(x) if x else 0 for x in match.groups()]

    # log_msg(f"{weeks = }, {days = }, {hours = }, {minutes = }, {seconds = }")

    if sign == "-":
        return -(weeks * 604800 + days * 86400 + hours * 3600 + minutes * 60 + seconds)
    else:
        return weeks * 604800 + days * 86400 + hours * 3600 + minutes * 60 + seconds


def dt_str_to_seconds(datetime_str: str) -> int:
    """Convert timestamps like '20250601T0900' into epoch seconds."""
    if not datetime_str:
        return None
    if "T" not in datetime_str:
        datetime_str += "T000000"
    try:
        return round(datetime.strptime(datetime_str[:13], "%Y%m%dT%H%M").timestamp())

    except ValueError:
        return round(
            datetime.strptime(datetime_str.rstrip("Z"), "%Y%m%dT0000").timestamp()
        )  # Allow date-only


def dt_to_dtstr(dt_obj: datetime) -> str:
    """Convert a datetime object to 'YYYYMMDDTHHMM' format."""
    if is_date:
        return dt_obj.strftime("%Y%m%d")
    return dt_obj.strftime("%Y%m%dT%H%M")


def td_to_tdstr(td_obj: timedelta) -> str:
    """Convert a timedelta object to a compact string like '1h30m20s'."""
    total = int(td_obj.total_seconds())
    if total == 0:
        return "0s"

    w, remainder = divmod(total, 604800)

    d, remainder = divmod(total, 86400)

    h, remainder = divmod(remainder, 3600)

    m, s = divmod(remainder, 60)

    parts = []
    if w:
        parts.append(f"{d}w")
    if d:
        parts.append(f"{d}d")
    if h:
        parts.append(f"{h}h")
    if m:
        parts.append(f"{m}m")
    if s:
        parts.append(f"{s}s")

    return "".join(parts)


# If you already have these helpers elsewhere, import and reuse them.
def _fmt_compact_local_naive(dt: datetime) -> str:
    """Return local-naive 'YYYYMMDD' or 'YYYYMMDDTHHMMSS'."""
    if dt.tzinfo is not None:
        dt = dt.astimezone(tz.tzlocal()).replace(tzinfo=None)
    if dt.hour == 0 and dt.minute == 0 and dt.second == 0:
        return dt.strftime("%Y%m%d")
    return dt.strftime("%Y%m%dT%H%M")


def _shift_from_parent(parent_dt: datetime, seconds: int) -> datetime:
    """
    Positive seconds = '&s 5d' means 5 days BEFORE parent => subtract.
    Negative seconds => AFTER parent => add.
    """
    return parent_dt - timedelta(seconds=seconds)


def _parse_jobs_json(jobs_json: str | None) -> list[dict]:
    """
    Parse your jobs list. Expects a list of dicts like:
      {"~": "create plan", "s": "1w", "e": "1h", "i": 1, "status": "...", ...}
    Returns a normalized list with keys: job_id, offset_str, extent_str, status.
    """
    if not jobs_json:
        return []
    try:
        data = json.loads(jobs_json)
    except Exception:
        return []

    jobs = []
    if isinstance(data, list):
        for j in data:
            if isinstance(j, dict):
                # log_msg(f"json jobs: {j = }")
                jobs.append(
                    {
                        "job_id": j.get("id"),
                        "offset_str": (j.get("s") or "").strip(),
                        "extent_str": (j.get("e") or "").strip(),
                        "status": (j.get("status") or "").strip().lower(),
                        "display_subject": (j.get("display_subject") or "").strip(),
                    }
                )
    return jobs


# 6-hour windows within a day (local-naive)
WINDOWS = [
    (0, 6),  # bit 1: 00:00 - 06:00
    (6, 12),  # bit 2: 06:00 - 12:00
    (12, 18),  # bit 3: 12:00 - 18:00
    (18, 24),  # bit 4: 18:00 - 24:00
]


def bits_to_int(bitstring: str) -> int:
    """'0000101...' → integer."""
    return int(bitstring, 2)


def int_to_bits(value: int) -> str:
    """Integer → 35-bit '010...'."""
    return format(value, "035b")


def or_aggregate(values: list[int]) -> int:
    """Bitwise OR aggregate."""
    acc = 0
    for v in values:
        acc |= v
    return acc


def _parse_local_naive(ts: str) -> datetime:
    # "YYYYmmddTHHMM" → naive local datetime
    return datetime.strptime(ts, "%Y%m%dT%H%M")


def _iso_year_week(d: datetime) -> str:
    y, w, _ = d.isocalendar()
    return f"{y:04d}-{w:02d}"


def fine_busy_bits_for_event(
    start_str: str, end_str: str | None
) -> dict[str, np.ndarray]:
    """
    Return dict of {year_week: 679-slot uint8 array}
    (7 days × (1 all-day + 96 fifteen-minute blocks))
    """
    start = parse(start_str)
    end = parse(end_str) if end_str else None

    is_all_day = is_all_day_text(start_str, end_str)

    if isinstance(start, date) and not isinstance(start, datetime):
        start = datetime.combine(start, datetime.min.time())
    if isinstance(end, date) and not isinstance(end, datetime):
        end = datetime.combine(end, datetime.min.time()) if end else None

    if end is None and not is_all_day:
        return {}

    slot_minutes = 15
    slots_per_day = 96
    slots_per_week = 7 * (1 + slots_per_day)  # 679
    weeks: dict[str, np.ndarray] = {}

    def yw_key(dt: datetime) -> str:
        y, w, _ = dt.isocalendar()
        return f"{y:04d}-{w:02d}"

    cur = start
    busy_count = 0
    all_day_last_date: date | None = None
    if is_all_day:
        start_day = start.date()
        all_day_last_date = start_day
        if end:
            end_day = end.date()
            candidate = end_day
            if has_zero_time_component(end_str) and end_day > start_day:
                candidate = end_day - timedelta(days=1)
            all_day_last_date = max(start_day, candidate)

    while True:
        yw = yw_key(cur)
        if yw not in weeks:
            weeks[yw] = np.zeros(slots_per_week, dtype=np.uint8)

        day_index = cur.weekday()  # Mon=0
        base = day_index * (1 + slots_per_day)

        if is_all_day:
            weeks[yw][base] = 1
        else:
            day_start = datetime.combine(cur.date(), datetime.min.time())
            day_end = datetime.combine(cur.date(), datetime.max.time())
            s = max(start, day_start)
            e = min(end, day_end)

            s_idx = (s.hour * 60 + s.minute) // slot_minutes
            e_idx = (e.hour * 60 + e.minute) // slot_minutes
            weeks[yw][base + 1 + s_idx : base + 1 + e_idx + 1] = 1
            busy_count += np.count_nonzero(weeks[yw])

        if is_all_day:
            if cur.date() >= all_day_last_date:
                break
        else:
            if end is None or cur.date() >= end.date():
                break
        cur += timedelta(days=1)
    # log_msg(f"{start_str = }, {end_str = }, {busy_count = }")
    return weeks


def _reduce_to_35_slots(arr: np.ndarray) -> np.ndarray:
    """
    Convert 679 fine bits (7 × (1 + 96)) into 35 coarse slots
    (7 × [1 all-day + 4 × 6-hour blocks]).
    """
    days = 7
    allday_bits = arr.reshape(days, 97)[:, 0]
    quarters = arr.reshape(days, 97)[:, 1:]  # 7×96

    coarse = np.zeros((days, 5), dtype=np.uint8)

    for d in range(days):
        # all-day stays as-is
        coarse[d, 0] = allday_bits[d]

        # 4 six-hour ranges
        for i in range(4):
            start = i * 24  # 6h = 24 × 15min
            end = start + 24
            chunk = quarters[d, start:end]
            if np.any(chunk == 2):
                coarse[d, i + 1] = 2
            elif np.any(chunk == 1):
                coarse[d, i + 1] = 1
            else:
                coarse[d, i + 1] = 0

    return coarse.flatten()


class SafeDict(dict):
    def __missing__(self, key):
        # Return a placeholder or empty string
        return f"{{{key}}}"


@dataclass
class BinPathConfig:
    allow_reparent: bool = True
    standard_roots: Set[str] = field(
        default_factory=lambda: BIN_ROOTS
    )  # anchored at root
    standard_paths: List[List[str]] = field(default_factory=lambda: BIN_PATHS)


class BinPathProcessor:
    def __init__(self, model, cfg: Optional[BinPathConfig] = None):
        """
        model: your Model instance (ensure_system_bins, ensure_root_children, move_bin, etc.)
        """
        self.m = model
        self.cfg = cfg or BinPathConfig()
        # Ensure system bins + standard roots exist at startup
        self.m.ensure_system_bins()
        if self.cfg.standard_roots:
            self.m.ensure_root_children(sorted(self.cfg.standard_roots))  # idempotent
        # NEW: ensure standard child paths exist + are correctly anchored
        for parts in self.cfg.standard_paths or []:
            try:
                # parts: ["leaf", "parent", "grandparent", ...]
                # apply_parts ensures/repairs hierarchy without touching records
                _norm, _log, _leaf_id = self.apply_parts(parts)
                # You could log _log somewhere if desired
            except Exception as e:
                # Fail soft: don’t break startup if one path is weird
                print(f"[binpaths] error applying standard path {parts!r}: {e}")

    @staticmethod
    def canon(name: str) -> str:
        return (name or "").strip()

    def _is_unlinked(self, bin_id: int) -> bool:
        """
        Unlinked if no parent row in BinLinks OR parent is the explicit 'unlinked' bin.
        """
        parent = self.m.get_parent_bin(bin_id)  # {'id','name'} or None
        if parent is None:
            return True
        return self.canon(parent["name"]) == "unlinked"

    def _ensure_standard_root_anchor(self, name: str) -> None:
        """
        Ensure standard roots exist directly under root.
        """
        self.m.ensure_root_children([name])  # puts child under root if missing

    # --- New: operate on already-split parts instead of parsing a string ---

    def apply_parts(self, parts: List[str]) -> Tuple[str, List[str], int]:
        """
        Process a bin path given as parts, e.g. ["lille","france","places"].
        Interpretation: parts[0] is the leaf, following are ancestors (nearest first).
        Returns: (normalized_token '@b <leaf>', log, leaf_bin_id)
        """
        log: List[str] = []

        parts = [p for p in (parts or []) if (p or "").strip()]
        if not parts:
            raise ValueError("Empty @b parts")

        leaf_name = self.canon(parts[0])
        ancestors = [self.canon(p) for p in parts[1:]]  # nearest first
        log.append(f"Parsed leaf='{leaf_name}', ancestors={ancestors!r}")

        # Ensure system bins present
        root_id, unlinked_id = self.m.ensure_system_bins()

        # Ensure leaf exists
        leaf_id = self.m.ensure_bin_exists(leaf_name)
        normalized = f"@b {leaf_name}"

        # No ancestors case
        if not ancestors:
            if not self._is_unlinked(leaf_id):
                log.append("Leaf already linked (not under 'unlinked'); no changes.")
                return normalized, log, leaf_id
            self._attach_if_missing(leaf_name, "unlinked", log)
            log.append("Leaf had no parent; placed under 'unlinked'.")
            return normalized, log, leaf_id

        # Walk up the chain: leaf -> parent -> grandparent...
        child_name = leaf_name
        for anc in ancestors:
            if anc in self.cfg.standard_roots:
                self._ensure_standard_root_anchor(anc)
            self._attach_if_missing(child_name, anc, log)
            child_name = anc

        top = ancestors[-1]
        if top in self.cfg.standard_roots:
            log.append(f"Ensured standard root '{top}' is anchored under root.")
        return normalized, log, leaf_id

    def _attach_if_missing(
        self, child_name: str, parent_name: str, log: List[str]
    ) -> None:
        """
        Attach child under parent if not already so; reparenting via move_bin (cycle-safe).
        """
        try:
            child_id = self.m.ensure_bin_exists(child_name)
            parent_id = self.m.ensure_bin_exists(parent_name)

            parent = self.m.get_parent_bin(child_id)
            if parent and self.canon(parent["name"]) == self.canon(parent_name):
                log.append(f"'{child_name}' already under '{parent_name}'.")
                return

            if (
                (not self.cfg.allow_reparent)
                and parent
                and self.canon(parent["name"]) != self.canon(parent_name)
            ):
                log.append(
                    f"Skipped reparenting '{child_name}' (existing parent='{parent['name']}') "
                    f"-> requested '{parent_name}' (allow_reparent=False)"
                )
                return

            ok = self.m.move_bin(child_name, parent_name)
            log.append(
                f"{'Attached' if ok else 'Failed to attach'} '{child_name}' under '{parent_name}'."
            )
        except Exception as e:
            log.append(f"Error attaching '{child_name}' -> '{parent_name}': {e}")

    # Convenience wrappers for your controller:

    def assign_record_via_parts(
        self, record_id: int, parts: List[str]
    ) -> Tuple[str, List[str], int]:
        """
        Ensure/repair hierarchy for {parts} and link the record to the leaf.
        """
        normalized, log, leaf_id = self.apply_parts(parts)
        self.m.link_record_to_bin(record_id, leaf_id)  # idempotent
        log.append(
            f"Linked record {record_id} → bin {leaf_id} ('{self.m.get_bin_name(leaf_id)}')."
        )
        return normalized, log, leaf_id

    def assign_record_many(
        self, record_id: int, list_of_parts: List[List[str]]
    ) -> Tuple[List[str], List[str], List[int]]:
        """
        Process multiple bin paths for a single record.
        Returns: (normalized_tokens, combined_log, leaf_ids)
        """
        norm_tokens: List[str] = []
        combined_log: List[str] = []
        leaf_ids: List[int] = []

        # De-duplicate exact paths to avoid redundant work
        seen = set()
        for parts in list_of_parts or []:
            key = tuple(self.canon(p) for p in parts if (p or "").strip())
            if not key or key in seen:
                continue
            seen.add(key)

            norm, log, leaf_id = self.assign_record_via_parts(record_id, list(key))
            norm_tokens.append(norm)
            combined_log.extend(log)
            leaf_ids.append(leaf_id)

        return norm_tokens, combined_log, leaf_ids


# bin_cache.py
def _rev_path_for(
    bid: int, name: Dict[int, str], parent: Dict[int, Optional[int]]
) -> str:
    parts: List[str] = []
    cur = bid
    while cur is not None:
        parts.append(name[cur])
        cur = parent.get(cur)
    return "/".join(parts)  # leaf → ... → root


class BinCache:
    """
    Incremental cache for bins/links with a simple public API:

      - name_to_binpath(): Dict[str, str]   # { leaf_lower: "Leaf/Parent/.../Root" }

    Update methods you call from your existing model helpers:

      - on_create(bid, name, parent_id)
      - on_rename(bid, new_name)
      - on_link(bid, parent_id)             # (re)parent; also used by move
      - on_unlink(bid)                      # set parent to None
      - on_delete(bid)                      # delete a bin and its subtree
    """

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn
        self.name: Dict[int, str] = {}
        self.parent: Dict[int, Optional[int]] = {}
        self.children: Dict[Optional[int], Set[int]] = defaultdict(set)
        self.rev_path: Dict[int, str] = {}
        self._name_to_binpath: Dict[str, str] = {}
        self._load_all()

    # ---------- initial build ----------

    def _load_all(self) -> None:
        rows = self.conn.execute("""
            SELECT b.id, b.name, bl.container_id
            FROM Bins b
            LEFT JOIN BinLinks bl ON bl.bin_id = b.id
        """).fetchall()

        self.name.clear()
        self.parent.clear()
        self.children.clear()
        for bid, nm, par in rows:
            self.name[bid] = nm
            self.parent[bid] = par
            self.children[par].add(bid)

        # compute reversed (leaf→root) paths
        self.rev_path = {
            bid: _rev_path_for(bid, self.name, self.parent) for bid in self.name
        }
        self._rebuild_name_dict()
        # log_msg(f"{self.name_to_binpath() = }")

    def _rebuild_name_dict(self) -> None:
        self._name_to_binpath = {
            nm.lower(): self.rev_path[bid] for bid, nm in self.name.items()
        }

    # ---------- subtree utilities ----------

    def _iter_subtree(self, root_id: int) -> Iterable[int]:
        q = deque([root_id])
        while q:
            x = q.popleft()
            yield x
            for c in self.children.get(x, ()):
                q.append(c)

    def _refresh_paths_for_subtree(self, root_id: int) -> None:
        # recompute rev_path for root and descendants; update name_to_binpath values
        for bid in self._iter_subtree(root_id):
            self.rev_path[bid] = _rev_path_for(bid, self.name, self.parent)
        for bid in self._iter_subtree(root_id):
            self._name_to_binpath[self.name[bid].lower()] = self.rev_path[bid]

    # ---------- mutations you call ----------

    def on_create(self, bid: int, nm: str, parent_id: Optional[int]) -> None:
        self.name[bid] = nm
        self.parent[bid] = parent_id
        self.children[parent_id].add(bid)
        self.rev_path[bid] = _rev_path_for(bid, self.name, self.parent)
        self._name_to_binpath[nm.lower()] = self.rev_path[bid]

    def on_rename(self, bid: int, new_name: str) -> None:
        old = self.name[bid]
        if old.lower() != new_name.lower():
            self._name_to_binpath.pop(old.lower(), None)
        self.name[bid] = new_name
        self._refresh_paths_for_subtree(bid)

    def on_link(self, bid: int, new_parent_id: Optional[int]) -> None:
        old_parent = self.parent.get(bid)
        if old_parent == new_parent_id:
            # nothing changed
            return
        if old_parent in self.children:
            self.children[old_parent].discard(bid)
        self.children[new_parent_id].add(bid)
        self.parent[bid] = new_parent_id
        self._refresh_paths_for_subtree(bid)

    def on_unlink(self, bid: int) -> None:
        old_parent = self.parent.get(bid)
        if old_parent in self.children:
            self.children[old_parent].discard(bid)
        self.parent[bid] = None
        self._refresh_paths_for_subtree(bid)

    def on_delete(self, bid: int) -> None:
        # remove whole subtree
        to_rm = list(self._iter_subtree(bid))
        par = self.parent.get(bid)
        if par in self.children:
            self.children[par].discard(bid)
        for x in to_rm:
            self._name_to_binpath.pop(self.name[x].lower(), None)
            # detach from parent/children maps
            p = self.parent.get(x)
            if p in self.children:
                self.children[p].discard(x)
            self.children.pop(x, None)
            self.parent.pop(x, None)
            self.rev_path.pop(x, None)
            self.name.pop(x, None)

    # ---------- query ----------

    def name_to_binpath(self) -> Dict[str, str]:
        return self._name_to_binpath


class UrgencyComputer:
    def __init__(self, env: TklrEnvironment):
        self.env = env
        self.urgency = env.config.urgency

        self.MIN_URGENCY = self.urgency.colors.min_urgency
        self.MIN_HEX_COLOR = self.urgency.colors.min_hex_color
        self.MAX_HEX_COLOR = self.urgency.colors.max_hex_color
        self.STEPS = self.urgency.colors.steps

        self.MAX_POSSIBLE_URGENCY = sum(
            comp.max
            for comp in vars(self.urgency).values()
            if hasattr(comp, "max") and isinstance(comp.max, (int, float))
        )
        self.BUCKETS = self.get_urgency_color_buckets()

    def hex_to_rgb(self, hex_color: str) -> Tuple[int, int, int]:
        hex_color = hex_color.lstrip("#")
        return tuple(int(hex_color[i : i + 2], 16) for i in (0, 2, 4))

    def rgb_to_hex(self, rgb: Tuple[int, int, int]) -> str:
        return "#{:02x}{:02x}{:02x}".format(*rgb)

    def get_urgency_color_buckets(self) -> List[str]:
        neg_rgb = self.hex_to_rgb(self.MIN_HEX_COLOR)
        max_rgb = self.hex_to_rgb(self.MAX_HEX_COLOR)

        buckets = []
        for i in range(self.STEPS):
            t = i / (self.STEPS - 1)
            rgb = tuple(
                round(neg + t * (maxc - neg)) for neg, maxc in zip(neg_rgb, max_rgb)
            )
            buckets.append(self.rgb_to_hex(rgb))
        return buckets

    def urgency_to_bucket_color(self, urgency: float) -> str:
        if urgency <= self.MIN_URGENCY:
            return self.MIN_HEX_COLOR
        if urgency >= 1.0:
            return self.MAX_HEX_COLOR

        i = min(
            int((urgency - self.MIN_URGENCY) * len(self.BUCKETS)), len(self.BUCKETS) - 1
        )
        return self.BUCKETS[i]

    def compute_partitioned_urgency(self, weights: dict[str, float]) -> float:
        """
        Compute urgency from signed weights:
        - Positive weights push urgency up
        - Negative weights pull urgency down
        - Equal weights → urgency = 0

        Returns:
            urgency ∈ [-1.0, 1.0]
        """
        Wp = 0.0 + sum(w for w in weights.values() if w > 0)

        Wn = 0.0 + sum(abs(w) for w in weights.values() if w < 0)

        urgency = (Wp - Wn) / self.MAX_POSSIBLE_URGENCY
        return urgency

    def urgency_due(self, due_seconds: int, now_seconds: int) -> float:
        """
        This function calculates the urgency contribution for a task based
        on its due datetime relative to the current datetime and returns
        a float value between 0.0 when (now <= due - interval) and max when
        (now >= due).
        """
        due_max = self.urgency.due.max
        interval = self.urgency.due.interval
        if due_seconds and due_max and interval:
            interval_seconds = td_str_to_seconds(interval)
            # log_msg(f"{due_max = }, {interval = }, {interval_seconds = }")
            return max(
                0.0,
                min(
                    due_max,
                    due_max * (1.0 - (now_seconds - due_seconds) / interval_seconds),
                ),
            )
        return 0.0

    def urgency_pastdue(self, due_seconds: int, now_seconds: int) -> float:
        """
        This function calculates the urgency contribution for a task based
        on its due datetime relative to the current datetime and returns
        a float value between 0.0 when (now <= due) and max when
        (now >= due + interval).
        """

        pastdue_max = self.urgency.pastdue.max
        interval = self.urgency.pastdue.interval
        if due_seconds and pastdue_max and interval:
            interval_seconds = td_str_to_seconds(interval)
            return max(
                0.0,
                min(
                    pastdue_max,
                    pastdue_max * (now_seconds - due_seconds) / interval_seconds,
                ),
            )
        return 0.0

    def urgency_recent(self, modified_seconds: int, now_seconds: int) -> float:
        """
        This function calculates the urgency contribution for a task based
        on the current datetime relative to the (last) modified datetime. It
        represents a combination of a decreasing contribution from recent_max
        based on how recently it was modified and an increasing contribution
        from 0 based on how long ago it was modified. The maximum of the two
        is the age contribution.
        """
        recent_contribution = 0.0
        recent_interval = self.urgency.recent.interval
        recent_max = self.urgency.recent.max
        # log_msg(f"{recent_interval = }")
        if recent_max and recent_interval:
            recent_interval_seconds = td_str_to_seconds(recent_interval)
            recent_contribution = max(
                0.0,
                min(
                    recent_max,
                    recent_max
                    * (1 - (now_seconds - modified_seconds) / recent_interval_seconds),
                ),
            )
        # log_msg(f"computed {recent_contribution = }")
        return recent_contribution

    def urgency_age(self, modified_seconds: int, now_seconds: int) -> float:
        """
        This function calculates the urgency contribution for a task based
        on the current datetime relative to the (last) modified datetime. It
        represents a combination of a decreasing contribution from recent_max
        based on how recently it was modified and an increasing contribution
        from 0 based on how long ago it was modified. The maximum of the two
        is the age contribution.
        """
        age_contribution = 0
        age_interval = self.urgency.age.interval
        age_max = self.urgency.age.max
        # log_msg(f"{age_interval = }")
        if age_max and age_interval:
            age_interval_seconds = td_str_to_seconds(age_interval)
            age_contribution = max(
                0.0,
                min(
                    age_max,
                    age_max * (now_seconds - modified_seconds) / age_interval_seconds,
                ),
            )
        # log_msg(f"computed {age_contribution = }")
        return age_contribution

    def urgency_priority(self, priority_level: int) -> float:
        priority = self.urgency.priority.root.get(str(priority_level), 0.0)
        # log_msg(f"computed {priority = }")
        return priority

    def urgency_extent(self, extent_seconds: int) -> float:
        extent_max = 1.0
        extent_interval = td_str_to_seconds(self.urgency.extent.interval)
        extent = max(
            0.0, min(extent_max, extent_max * extent_seconds / extent_interval)
        )
        # log_msg(f"{extent_seconds = }, {extent = }")
        return extent

    def urgency_blocking(self, num_blocking: int) -> float:
        blocking = 0.0
        if num_blocking:
            blocking_max = self.urgency.blocking.max
            blocking_count = self.urgency.blocking.count
            if blocking_max and blocking_count:
                blocking = max(
                    0.0, min(blocking_max, blocking_max * num_blocking / blocking_count)
                )
        # log_msg(f"computed {blocking = }")
        return blocking

    def urgency_tags(self, num_tags: int) -> float:
        tags = 0.0
        tags_max = self.urgency.tags.max
        tags_count = self.urgency.tags.count
        if tags_max and tags_count:
            tags = max(0.0, min(tags_max, tags_max * num_tags / tags_count))
        # log_msg(f"computed {tags = }")
        return tags

    def urgency_description(self, has_description: bool) -> float:
        description_max = self.urgency.description.max
        description = 0.0
        if has_description and description_max:
            description = description_max
        # log_msg(f"computed {description = }")
        return description

    def urgency_project(self, has_project: bool) -> float:
        project_max = self.urgency.project.max
        project = 0.0
        if has_project and project_max:
            project = project_max
        # log_msg(f"computed {project = }")
        return project

    def from_args_and_weights(self, **kwargs):
        if bool(kwargs.get("pinned", False)):
            return 1.0, self.urgency_to_bucket_color(1.0), {}
        weights = {
            "due": self.urgency_due(kwargs.get("due"), kwargs["now"]),
            "pastdue": self.urgency_pastdue(kwargs.get("due"), kwargs["now"]),
            "age": self.urgency_age(kwargs["modified"], kwargs["now"]),
            "recent": self.urgency_recent(kwargs["modified"], kwargs["now"]),
            "priority": self.urgency_priority(kwargs.get("priority_level")),
            "extent": self.urgency_extent(kwargs["extent"]),
            "blocking": self.urgency_blocking(kwargs.get("blocking", 0.0)),
            "tags": self.urgency_tags(kwargs.get("tags", 0)),
            "description": self.urgency_description(kwargs.get("description", False)),
            "project": 1.0 if bool(kwargs.get("jobs", False)) else 0.0,
        }
        if bool(kwargs.get("pinned", False)):
            urgency = 1.0
            # log_msg("pinned, ignoring weights, returning urgency 1.0")
        else:
            urgency = self.compute_partitioned_urgency(weights)
            # log_msg(f"{weights = }\n  returning {urgency = }")
        return urgency, self.urgency_to_bucket_color(urgency), weights


class DatabaseManager:
    def __init__(
        self,
        db_path: str,
        env: TklrEnvironment,
        reset: bool = False,
        *,
        auto_populate: bool = True,
    ):
        self.db_path = db_path
        self.env = env
        self.AMPM = env.config.ui.ampm
        self.ALERTS = env.config.alerts
        self.urgency = self.env.config.urgency

        if reset and os.path.exists(self.db_path):
            os.remove(self.db_path)

        self.conn = sqlite3.connect(self.db_path)
        try:
            self.conn.execute("PRAGMA busy_timeout = 5000")
        except sqlite3.OperationalError:
            pass
        self.cursor = self.conn.cursor()
        self.conn.create_function("REGEXP", 2, regexp)
        self.conn.create_function("REGEXP", 2, regexp)
        self.setup_database()
        self.compute_urgency = UrgencyComputer(env)
        self._state_cache: dict[str, Any] = {}
        self._bin_root_overrides: dict[str, str] = self._load_bin_root_overrides()
        std_roots = self._build_standard_roots()
        std_paths = self._build_standard_paths()
        self.binproc = BinPathProcessor(
            self,
            BinPathConfig(
                allow_reparent=True,  # or False if you want conservative behavior
                standard_roots=std_roots,
                standard_paths=std_paths,
            ),
        )
        self.bin_cache = BinCache(self.conn)
        self.root_bin_id = None
        self.unlinked_bin_id = None
        self._system_bins_initialized = False
        self.root_bin_id, self.unlinked_bin_id = self.ensure_system_bins()
        self.after_save_needed: bool = True

        if auto_populate:
            self.populate_dependent_tables()

    def commit(self):
        self.conn.commit()
        self.after_save_needed = True

    def _get_state_value(self, key: str, default=None):
        if key in self._state_cache:
            return self._state_cache[key]
        row = self.cursor.execute(
            "SELECT value FROM DerivedState WHERE key = ?", (key,)
        ).fetchone()
        if not row:
            self._state_cache[key] = default
            return default
        try:
            value = json.loads(row[0])
        except Exception:
            value = row[0]
        self._state_cache[key] = value
        return value

    def _set_state_value(self, key: str, value) -> None:
        payload = json.dumps(value)
        self.cursor.execute(
            """
            INSERT INTO DerivedState(key, value)
            VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """,
            (key, payload),
        )
        self._state_cache[key] = value

    # ----- Standard root overrides -----

    def _load_bin_root_overrides(self) -> dict[str, str]:
        """
        Return canonical-root overrides stored in DerivedState.
        Keys are canonical names from BIN_ROOTS; values are the user-visible names.
        """
        raw = self._get_state_value("bin_root_overrides", {}) or {}
        overrides: dict[str, str] = {}
        if isinstance(raw, dict):
            for canonical in BIN_ROOTS:
                val = raw.get(canonical)
                if isinstance(val, str):
                    fixed = val.strip()
                    if fixed and fixed.lower() != canonical.lower():
                        overrides[canonical] = fixed
        return overrides

    def _persist_bin_root_overrides(self) -> None:
        if not hasattr(self, "_bin_root_overrides"):
            return
        payload = {
            canon: name
            for canon, name in self._bin_root_overrides.items()
            if name and name.strip() and name.strip().lower() != canon.lower()
        }
        self._set_state_value("bin_root_overrides", payload)

    def _current_root_name(self, canonical: str) -> str:
        overrides = getattr(self, "_bin_root_overrides", {}) or {}
        return overrides.get(canonical, canonical)

    def _build_standard_roots(self) -> set[str]:
        return {self._current_root_name(name) for name in BIN_ROOTS}

    def _build_standard_paths(self) -> list[list[str]]:
        paths: list[list[str]] = []
        overrides = getattr(self, "_bin_root_overrides", {}) or {}
        for original in BIN_PATHS:
            if not original:
                continue
            parts = list(original)
            # Skip the leaf (index 0); ancestors should honor overrides.
            for idx in range(1, len(parts)):
                canonical = parts[idx]
                if canonical in BIN_ROOTS and canonical in overrides:
                    parts[idx] = overrides[canonical]
            paths.append(parts)
        return paths

    def _canonical_root_for_name(self, actual_name: str) -> str | None:
        name = (actual_name or "").strip().lower()
        if not name:
            return None
        for canonical in BIN_ROOTS:
            if self._current_root_name(canonical).lower() == name:
                return canonical
        return None

    def _refresh_standard_root_runtime(self) -> None:
        if not hasattr(self, "binproc"):
            return
        cfg = getattr(self.binproc, "cfg", None)
        if not cfg:
            return
        cfg.standard_roots = self._build_standard_roots()
        cfg.standard_paths = self._build_standard_paths()

    def _handle_standard_root_rename(
        self, canonical: str | None, old_name: str, new_name: str
    ) -> None:
        if not canonical:
            return
        actual = (new_name or "").strip()
        if not actual:
            return
        if not hasattr(self, "_bin_root_overrides"):
            self._bin_root_overrides = {}
        if actual.lower() == canonical.lower():
            self._bin_root_overrides.pop(canonical, None)
        else:
            self._bin_root_overrides[canonical] = actual
        self._persist_bin_root_overrides()
        self._refresh_standard_root_runtime()

    def _records_version(self) -> str:
        row = self.cursor.execute("SELECT MAX(modified) FROM Records").fetchone()
        if not row:
            return "0"
        return row[0] or "0"

    def format_datetime(self, fmt_dt: str) -> str:
        return format_datetime(fmt_dt, self.ampm)

    def datetime_in_words(self, fmt_dt: str) -> str:
        return datetime_in_words(fmt_dt, self.ampm)

    def setup_database(self):
        """
        Create (if missing) all tables and indexes for tklr.

        Simplified tags model:
        - Tags live ONLY in Records.tags (JSON text).
        - No separate Tags / RecordTags tables.

        Other notes:
        - Timestamps are stored as TEXT in UTC (e.g., 'YYYYMMDDTHHMMSS') unless otherwise noted.
        - DateTimes.start/end are local-naive TEXT ('YYYYMMDD' or 'YYYYMMDDTHHMMSS').
        """
        # FK safety
        self.cursor.execute("PRAGMA foreign_keys = ON")

        # --- Optional cleanup of old tag tables (safe if they don't exist) ---
        self.cursor.execute("DROP TABLE IF EXISTS RecordTags;")
        self.cursor.execute("DROP TABLE IF EXISTS Tags;")

        # ---------------- Records ----------------
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS Records (
                id                INTEGER PRIMARY KEY AUTOINCREMENT,
                itemtype          TEXT,                         -- '*','~','^','%','?','!','x'
                subject           TEXT,
                description       TEXT,
                rruleset          TEXT,                         -- serialized ruleset
                timezone          TEXT,                         -- TZ name or 'float'
                extent            TEXT,                         -- optional JSON or text
                alerts            TEXT,                         -- JSON
                notice            TEXT,
                context           TEXT,
                jobs              TEXT,                         -- JSON
                flags             TEXT,                         -- compact flags (e.g. 𝕒𝕘𝕠𝕣)
                priority          INTEGER CHECK (priority IN (1,2,3,4,5)),
                tokens            TEXT,                         -- JSON text (parsed tokens)
                processed         INTEGER,                      -- 0/1
                created           TEXT,                         -- 'YYYYMMDDTHHMMSS' UTC
                modified          TEXT                          -- 'YYYYMMDDTHHMMSS' UTC
            );
        """)

        # ---------------- Pinned ----------------
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS Pinned (
                record_id INTEGER PRIMARY KEY,
                FOREIGN KEY (record_id) REFERENCES Records(id) ON DELETE CASCADE
            );
        """)
        self.cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_pinned_record
            ON Pinned(record_id);
        """)

        # ---------------- Urgency (NO pinned column) ----------------
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS Urgency (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                record_id INTEGER NOT NULL,                     -- References Records.id
                job_id    INTEGER,                              -- NULL if not part of a project
                subject   TEXT    NOT NULL,
                urgency   REAL    NOT NULL,
                color     TEXT,                                 -- optional precomputed color
                status    TEXT    NOT NULL,                     -- "next","waiting","scheduled",…
                weights   TEXT,                                 -- JSON of component weights (optional)
                FOREIGN KEY (record_id) REFERENCES Records(id) ON DELETE CASCADE
            );
        """)
        self.cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_urgency_record
            ON Urgency(record_id);
        """)
        self.cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_urgency_urgency
            ON Urgency(urgency DESC);
        """)

        # ---------------- Completions ----------------
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS Completions (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                record_id  INTEGER NOT NULL,
                completed  TEXT NOT NULL,  -- UTC-aware: "YYYYMMDDTHHMMZ"
                due        TEXT,           -- optional UTC-aware: "YYYYMMDDTHHMMZ"
                FOREIGN KEY(record_id) REFERENCES Records(id) ON DELETE CASCADE
            );
        """)
        self.cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_completions_record_id
            ON Completions(record_id);
        """)
        self.cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_completions_completed
            ON Completions(completed);
        """)
        self.cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_completions_record_due
            ON Completions(record_id, due);
        """)

        # ---------------- DateTimes ----------------
        # self.cursor.execute("""
        #     CREATE TABLE IF NOT EXISTS DateTimes (
        #         record_id      INTEGER NOT NULL,
        #         job_id         INTEGER,          -- nullable; link to specific job if any
        #         start_datetime TEXT NOT NULL,    -- 'YYYYMMDD' or 'YYYYMMDDTHHMMSS' (local-naive)
        #         end_datetime   TEXT,             -- NULL if instantaneous; same formats as start
        #         FOREIGN KEY (record_id) REFERENCES Records(id) ON DELETE CASCADE
        #     );
        # """)

        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS DateTimes (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                record_id      INTEGER NOT NULL,
                job_id         INTEGER,          -- nullable; link to specific job if any
                start_datetime TEXT NOT NULL,    -- 'YYYYMMDD' or 'YYYYMMDDTHHMMSS' (local-naive)
                end_datetime   TEXT,             -- NULL if instantaneous; same formats as start
                FOREIGN KEY (record_id) REFERENCES Records(id) ON DELETE CASCADE
            );
        """)

        # enforce uniqueness across (record_id, job_id, start, end)
        self.cursor.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_datetimes_unique
            ON DateTimes(
                record_id,
                COALESCE(job_id, -1),
                start_datetime,
                COALESCE(end_datetime, '')
            );
        """)
        # range query helper
        self.cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_datetimes_start
            ON DateTimes(start_datetime);
        """)

        # ---------------- GeneratedWeeks (cache of week ranges) ----------------
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS GeneratedWeeks (
                start_year INTEGER,
                start_week INTEGER,
                end_year   INTEGER,
                end_week   INTEGER
            );
        """)

        # ---------------- Alerts ----------------
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS Alerts (
                alert_id         INTEGER PRIMARY KEY AUTOINCREMENT,
                record_id        INTEGER NOT NULL,
                record_name      TEXT    NOT NULL,
                trigger_datetime TEXT    NOT NULL,  -- 'YYYYMMDDTHHMMSS' (local-naive)
                start_datetime   TEXT    NOT NULL,  -- 'YYYYMMDD' or 'YYYYMMDDTHHMMSS' (local-naive)
                alert_name       TEXT    NOT NULL,
                alert_command    TEXT    NOT NULL,
                FOREIGN KEY (record_id) REFERENCES Records(id) ON DELETE CASCADE
            );
        """)
        # Prevent duplicates: one alert per (record, start, name, trigger)
        self.cursor.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_alerts_unique
            ON Alerts(record_id, start_datetime, alert_name, COALESCE(trigger_datetime,''));
        """)
        # Helpful for “what’s due now”
        self.cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_alerts_trigger
            ON Alerts(trigger_datetime);
        """)

        # ---------------- Notice (days remaining notices) ----------------
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS Notice (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                record_id      INTEGER NOT NULL,
                days_remaining INTEGER NOT NULL,
                FOREIGN KEY (record_id) REFERENCES Records(id) ON DELETE CASCADE
            );
        """)

        # ---------------- Derived state cache ----------------
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS DerivedState (
                key   TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
        """)

        # ---------------- Bins & Links ----------------
        self.cursor.execute("PRAGMA foreign_keys = ON;")

        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS Bins (
                id   INTEGER PRIMARY KEY,
                name TEXT NOT NULL CHECK (length(trim(name)) > 0)
            );
        """)

        self.cursor.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS uq_bins_name_nocase
            ON Bins(name COLLATE NOCASE);
        """)

        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS BinLinks (
                bin_id       INTEGER NOT NULL,
                container_id INTEGER,
                FOREIGN KEY (bin_id)       REFERENCES Bins(id) ON DELETE CASCADE,
                FOREIGN KEY (container_id) REFERENCES Bins(id) ON DELETE SET NULL,
                UNIQUE(bin_id)
            );
        """)

        self.cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_binlinks_container
            ON BinLinks(container_id);
        """)

        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS ReminderLinks (
                reminder_id INTEGER NOT NULL,
                bin_id      INTEGER NOT NULL,
                FOREIGN KEY (reminder_id) REFERENCES Records(id) ON DELETE CASCADE,
                FOREIGN KEY (bin_id)      REFERENCES Bins(id)    ON DELETE CASCADE,
                UNIQUE(reminder_id, bin_id)
            );
        """)

        self.cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_reminderlinks_bin
            ON ReminderLinks(bin_id);
        """)

        self.cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_reminderlinks_reminder
            ON ReminderLinks(reminder_id);
        """)

        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS Hashtags (
                tag       TEXT NOT NULL,
                record_id INTEGER NOT NULL,
                FOREIGN KEY (record_id) REFERENCES Records(id) ON DELETE CASCADE
            );
        """)

        self.cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_hashtags_tag ON Hashtags(tag);
        """)

        self.cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_hashtags_record ON Hashtags(record_id);
        """)

        # ---------------- Busy tables (unchanged) ----------------
        self.setup_busy_tables()
        # Seed default top-level bins (idempotent)

        self.ensure_root_children(sorted(BIN_ROOTS))

        self.commit()
        self.cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row[0] for row in self.cursor.fetchall()]
        tables.sort()

    def setup_busy_tables(self):
        """
        Create / reset busy cache tables and triggers.

        Design:
        - BusyWeeksFromDateTimes: per (record_id, year_week) cache of fine-grained busybits (BLOB, 672 slots).
            FK references Records(id) — not DateTimes — since we aggregate per record/week.
        - BusyWeeks: per year_week aggregated ternary bits (TEXT, 35 chars).
        - BusyUpdateQueue: queue of record_ids to recompute.

        Triggers enqueue record_id on any insert/update/delete in DateTimes.
        """

        # Make schema idempotent and remove any old incompatible objects.
        self.cursor.execute("PRAGMA foreign_keys=ON")

        # Drop old triggers (names must match what you used previously)
        self.cursor.execute("DROP TRIGGER IF EXISTS trig_busy_insert")
        self.cursor.execute("DROP TRIGGER IF EXISTS trig_busy_update")
        self.cursor.execute("DROP TRIGGER IF EXISTS trig_busy_delete")
        self.cursor.execute("DROP TRIGGER IF EXISTS trig_busy_records_delete")

        # Drop old tables if they exist (to get rid of the bad FK)
        self.cursor.execute("DROP TABLE IF EXISTS BusyWeeksFromDateTimes")
        self.cursor.execute("DROP TABLE IF EXISTS BusyWeeks")
        self.cursor.execute("DROP TABLE IF EXISTS BusyUpdateQueue")

        # Reset DerivedState entry so busy caches get rebuilt after the drop.
        # Otherwise `_maybe_refresh_busy_tables` would skip the regeneration
        # because it still sees the prior "seeded" flag.
        try:
            self.cursor.execute(
                """
                INSERT INTO DerivedState(key, value)
                VALUES ('busy', ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
                """,
                (json.dumps({"seeded": False}),),
            )
        except sqlite3.OperationalError:
            # Table will be created moments later; nothing to do.
            pass

        # Recreate BusyWeeks (aggregate per week)
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS BusyWeeks (
                year_week TEXT PRIMARY KEY,
                busybits  TEXT NOT NULL  -- 35-char string of '0','1','2'
            );
        """)

        # Recreate BusyWeeksFromDateTimes (per record/week)
        # PRIMARY KEY enforces one row per (record, week)
        # FK to Records(id) so deletes of records cascade cleanly
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS BusyWeeksFromDateTimes (
                record_id  INTEGER NOT NULL,
                year_week  TEXT    NOT NULL,
                busybits   BLOB    NOT NULL,  -- 672 slots (15-min blocks)
                PRIMARY KEY (record_id, year_week),
                FOREIGN KEY(record_id) REFERENCES Records(id) ON DELETE CASCADE
            );
        """)

        # Update queue for incremental recomputation
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS BusyUpdateQueue (
                record_id INTEGER PRIMARY KEY
            );
        """)

        # Triggers on DateTimes to enqueue affected record
        self.cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS trig_busy_insert
            AFTER INSERT ON DateTimes
            BEGIN
                INSERT OR IGNORE INTO BusyUpdateQueue(record_id)
                VALUES (NEW.record_id);
            END;
        """)

        self.cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS trig_busy_update
            AFTER UPDATE ON DateTimes
            BEGIN
                INSERT OR IGNORE INTO BusyUpdateQueue(record_id)
                VALUES (NEW.record_id);
            END;
        """)

        self.cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS trig_busy_delete
            AFTER DELETE ON DateTimes
            BEGIN
                INSERT OR IGNORE INTO BusyUpdateQueue(record_id)
                VALUES (OLD.record_id);
            END;
        """)

        # If a record is deleted, clean any cache rows (cascades remove BusyWeeksFromDateTimes).
        # Also clear from the queue if present.
        self.cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS trig_busy_records_delete
            AFTER DELETE ON Records
            BEGIN
                DELETE FROM BusyUpdateQueue WHERE record_id = OLD.id;
                -- BusyWeeksFromDateTimes rows are removed by FK ON DELETE CASCADE.
            END;
        """)

        self.commit()

    def backup_to(self, dest_db: Path) -> Path:
        """
        Create a consistent SQLite snapshot of the current database at dest_db.
        Uses the live connection (self.conn) to copy committed state.
        Returns the final backup path.
        """
        dest_db = Path(dest_db)
        tmp = dest_db.with_suffix(dest_db.suffix + ".tmp")
        dest_db.parent.mkdir(parents=True, exist_ok=True)

        # Ensure we copy a committed state
        self.commit()

        # Copy using SQLite's backup API
        with sqlite3.connect(str(tmp)) as dst:
            self.conn.backup(dst)  # full backup
            # Tidy destination file only
            dst.execute("PRAGMA wal_checkpoint(TRUNCATE);")
            dst.execute("VACUUM;")
            dst.commit()

        # Preserve timestamps/permissions from the source file if available
        try:
            # Adjust attribute name if your manager stores the DB path differently
            src_path = Path(
                getattr(
                    self,
                    "db_path",
                    self.conn.execute("PRAGMA database_list").fetchone()[2],
                )
            )
            shutil.copystat(src_path, tmp)
        except Exception:
            pass

        tmp.replace(dest_db)
        return dest_db

    def populate_dependent_tables(self, *, force: bool = False):
        """
        Populate derived tables (DateTimes cache, alerts, notice, busy weeks, urgency)
        only when inputs have changed.
        """
        yr, wk = datetime.now().isocalendar()[:2]
        today_key = date.today().isoformat()
        records_version = self._records_version()

        work_done = False
        work_done |= self._maybe_extend_datetimes(yr, wk, 12, records_version, force)
        work_done |= self._maybe_populate_alerts(today_key, records_version, force)
        work_done |= self._maybe_populate_notice(today_key, records_version, force)
        work_done |= self._maybe_refresh_busy_tables(force)
        work_done |= self._maybe_populate_urgency(records_version, force)

        self.after_save_needed = False

    def _maybe_extend_datetimes(
        self,
        year: int,
        week: int,
        weeks_ahead: int,
        records_version: str,
        force: bool,
    ) -> bool:
        need_span = self._advance_week(year, week, weeks_ahead)
        rng = self.get_generated_weeks_range()
        state = self._get_state_value("datetimes", {})
        version_match = state.get("version") == records_version
        range_ok = bool(
            rng
            and self._range_includes(rng, (year, week))
            and self._range_includes(rng, need_span)
        )

        if not force and version_match and range_ok:
            return False

        self.extend_datetimes_for_weeks(year, week, weeks_ahead)
        new_rng = self.get_generated_weeks_range()
        self._set_state_value(
            "datetimes",
            {
                "version": records_version,
                "range": list(new_rng) if new_rng else None,
            },
        )
        return True

    def _maybe_populate_alerts(
        self, today_key: str, records_version: str, force: bool
    ) -> bool:
        state = self._get_state_value("alerts", {})
        if (
            not force
            and state.get("day") == today_key
            and state.get("version") == records_version
        ):
            return False

        self.populate_alerts()
        self._set_state_value(
            "alerts",
            {
                "day": today_key,
                "version": records_version,
            },
        )
        return True

    def _maybe_populate_notice(
        self, today_key: str, records_version: str, force: bool
    ) -> bool:
        state = self._get_state_value("notice", {})
        if (
            not force
            and state.get("day") == today_key
            and state.get("version") == records_version
        ):
            return False

        self.populate_notice()
        self._set_state_value(
            "notice",
            {
                "day": today_key,
                "version": records_version,
            },
        )
        return True

    def _maybe_refresh_busy_tables(self, force: bool) -> bool:
        state = self._get_state_value("busy", {})
        if force:
            self.populate_busy_from_datetimes()
            self.rebuild_busyweeks_from_source()
            self.cursor.execute("DELETE FROM BusyUpdateQueue")
            self._set_state_value("busy", {"seeded": True})
            self.commit()
            return True

        self.cursor.execute("SELECT record_id FROM BusyUpdateQueue")
        queued = [row[0] for row in self.cursor.fetchall()]
        if not queued:
            if state.get("seeded"):
                return False
            self.populate_busy_from_datetimes()
            self.rebuild_busyweeks_from_source()
            self._set_state_value("busy", {"seeded": True})
            return True

        for record_id in queued:
            self.update_busy_weeks_for_record(record_id)

        self.cursor.execute("DELETE FROM BusyUpdateQueue")
        self.commit()
        self._set_state_value("busy", {"seeded": True})
        return True

    def _maybe_populate_urgency(
        self, records_version: str, force: bool, state_key: str = "urgency"
    ) -> bool:
        state = self._get_state_value(state_key, {})
        if not force and state.get("version") == records_version:
            return False

        self.populate_all_urgency()
        self._set_state_value(state_key, {"version": records_version})
        return True

    def _normalize_tags(self, tags) -> list[str]:
        """Return a sorted, de-duplicated, lowercased list of tag strings."""
        if tags is None:
            return []
        if isinstance(tags, str):
            parts = [p for p in re.split(r"[,\s]+", tags) if p]
        else:
            parts = list(tags)
        return sorted({p.strip().lower() for p in parts if p and p.strip()})

    def _compute_flags(self, item) -> str:
        """
        Derive flags string from an Item:
        𝕒 -> has alerts
        𝕘 -> has goto (@g)
        𝕠 -> has offset (@o)
        𝕣 -> has repeat (@r or @+)
        """
        flags: list[str] = []
        tokens = getattr(item, "tokens", []) or []

        # alerts: explicit @a or non-empty item.alerts
        has_alert = bool(item.alerts) or any(
            t.get("t") == "@" and t.get("k") == "a" for t in tokens
        )
        if has_alert:
            flags.append("𝕒")

        # goto: @g
        if any(t.get("t") == "@" and t.get("k") == "g" for t in tokens):
            flags.append("𝕘")

        # offset: @o
        if any(t.get("t") == "@" and t.get("k") == "o" for t in tokens):
            flags.append("𝕠")

        # repeat: @r or @+
        if any(t.get("t") == "@" and t.get("k") in ("r", "+") for t in tokens):
            flags.append("𝕣")

        return "".join(flags)

    def _update_hashtags_for_record(
        self,
        record_id: int,
        subject: str | None,
        description: str | None,
    ) -> None:
        text = (subject or "") + "\n" + (description or "")
        tags = set(TAG_RE.findall(text))

        self.cursor.execute("DELETE FROM Hashtags WHERE record_id = ?", (record_id,))
        for tag in tags:
            self.cursor.execute(
                "INSERT INTO Hashtags (tag, record_id) VALUES (?, ?)",
                (tag, record_id),
            )

    def add_item(self, item: Item) -> int:
        flags = self._compute_flags(item)
        try:
            timestamp = utc_now_string()
            self.cursor.execute(
                """
                INSERT INTO Records (
                    itemtype, subject, description, rruleset, timezone,
                    extent, alerts, notice, context, jobs, flags, priority,
                    tokens, processed, created, modified
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    item.itemtype,
                    item.subject,
                    item.description,
                    item.rruleset,
                    item.tz_str,
                    item.extent,
                    json.dumps(item.alerts),
                    item.notice,
                    item.context,
                    json.dumps(item.jobs),
                    flags,
                    item.priority,
                    json.dumps(item.tokens),
                    0,
                    timestamp,
                    timestamp,
                ),
            )
            self.commit()

            record_id = self.cursor.lastrowid
            self.relink_bins_for_record(record_id, item)  # ← add this
            self._update_hashtags_for_record(record_id, item.subject, item.description)
            return record_id

        except Exception as e:
            print(f"Error adding {item}: {e}")
            raise

    def update_item(self, record_id: int, item: Item):
        try:
            fields, values = [], []

            def set_field(name, value):
                if value is not None:
                    fields.append(f"{name} = ?")
                    values.append(value)

            set_field("itemtype", item.itemtype)
            set_field("subject", item.subject)
            set_field("description", item.description)
            set_field("rruleset", item.rruleset)
            set_field("timezone", item.tz_str)
            set_field("extent", item.extent)
            set_field(
                "alerts", json.dumps(item.alerts) if item.alerts is not None else None
            )
            set_field("notice", item.notice)
            set_field("context", item.context)
            set_field("jobs", json.dumps(item.jobs) if item.jobs is not None else None)
            set_field("priority", item.priority)
            set_field(
                "tokens", json.dumps(item.tokens) if item.tokens is not None else None
            )
            set_field("processed", 0)

            fields.append("modified = ?")
            values.append(utc_now_string())
            values.append(record_id)

            sql = f"UPDATE Records SET {', '.join(fields)} WHERE id = ?"

            self.cursor.execute(sql, values)
            self.commit()
            self.relink_bins_for_record(record_id, item)  # ← add this

        except Exception as e:
            print(f"Error updating record {record_id}: {e}")
            raise

    def save_record(self, item: Item, record_id: int | None = None) -> int:
        """Insert or update a record and refresh associated tables."""
        timestamp = utc_now_string()
        flags = self._compute_flags(item)

        if record_id is None:
            # Insert new record
            self.cursor.execute(
                """
                INSERT INTO Records (
                    itemtype, subject, description, rruleset, timezone,
                    extent, alerts, notice, context, jobs,
                    flags, priority, tokens, processed, created, modified
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    item.itemtype,
                    item.subject,
                    item.description,
                    item.rruleset,
                    item.tz_str,
                    item.extent,
                    json.dumps(item.alerts),
                    item.notice,
                    item.context,
                    json.dumps(item.jobs),
                    flags,
                    item.priority,
                    json.dumps(item.tokens),
                    0,
                    timestamp,
                    timestamp,
                ),
            )
            record_id = self.cursor.lastrowid
        else:
            # Update existing record
            self.cursor.execute(
                """
                UPDATE Records
                SET itemtype = ?, subject = ?, description = ?, rruleset = ?, timezone = ?,
                    extent = ?, alerts = ?, notice = ?, context = ?, jobs = ?,
                    flags = ?, priority = ?, tokens = ?, processed = 0, modified = ?
                WHERE id = ?
                """,
                (
                    item.itemtype,
                    item.subject,
                    item.description,
                    item.rruleset,
                    item.tz_str,
                    item.extent,
                    json.dumps(item.alerts),
                    item.notice,
                    item.context,
                    json.dumps(item.jobs),
                    flags,
                    item.priority,
                    json.dumps(item.tokens),
                    timestamp,
                    record_id,
                ),
            )

        self.commit()

        # Dependent tables
        self.relink_bins_for_record(record_id, item)
        self.generate_datetimes_for_record(record_id)
        self.populate_alerts_for_record(record_id)
        if item.notice:
            self.populate_notice_for_record(record_id)
        if item.itemtype in ["~", "^"]:
            self.populate_urgency_from_record(record_id)
        self.update_busy_weeks_for_record(record_id)

        # Hashtags: based on subject + description
        self._update_hashtags_for_record(record_id, item.subject, item.description)

        self.commit()
        return record_id

    def add_completion(
        self,
        record_id: int,
        completion: tuple[datetime, datetime | None],
    ) -> None:
        """Store a completion record as UTC-aware compact strings."""
        if completion is None:
            return

        completed_dt, due_dt = completion
        self.cursor.execute(
            """
            INSERT INTO Completions (record_id, completed, due)
            VALUES (?, ?, ?)
            """,
            (
                record_id,
                _fmt_utc(completed_dt),
                _fmt_utc(due_dt) if due_dt else None,
            ),
        )
        self.commit()

    def get_completions(self, record_id: int):
        """
        Return all completions for a given record, sorted newest first.

        Returns:
            [(record_id, subject, description, itemtype, due_dt, completed_dt)]
        """
        self.cursor.execute(
            """
            SELECT
                r.id,
                r.subject,
                r.description,
                r.itemtype,
                c.due,
                c.completed
            FROM Completions c
            JOIN Records r ON c.record_id = r.id
            WHERE r.id = ?
            ORDER BY c.completed DESC
            """,
            (record_id,),
        )
        rows = self.cursor.fetchall()
        return [
            (
                rid,
                subj,
                desc,
                itype,
                parse_utc_z(due) if due else None,
                parse_utc_z(comp),
            )
            for (rid, subj, desc, itype, due, comp) in rows
        ]

    def get_all_completions(self):
        """
        Return all completions across all records, newest first.

        Rows:
            [(record_id, subject, description, itemtype, due_dt, completed_dt)]
        """
        self.cursor.execute(
            """
            SELECT
                r.id,
                r.subject,
                r.description,
                r.itemtype,
                c.due,
                c.completed
            FROM Completions c
            JOIN Records r ON c.record_id = r.id
            ORDER BY c.completed DESC
            """
        )
        rows = self.cursor.fetchall()
        return [
            (
                rid,
                subj,
                desc,
                itype,
                parse_utc_z(due) if due else None,
                parse_utc_z(comp),
            )
            for (rid, subj, desc, itype, due, comp) in rows
        ]

    def touch_record(self, record_id: int):
        """
        Update the 'modified' timestamp for the given record to the current UTC time.
        """
        now = utc_now_string()
        self.cursor.execute(
            """
            UPDATE Records SET modified = ? WHERE id = ?
            """,
            (now, record_id),
        )
        self.commit()

    def toggle_pinned(self, record_id: int) -> None:
        self.cursor.execute("SELECT 1 FROM Pinned WHERE record_id=?", (record_id,))
        if self.cursor.fetchone():
            self.cursor.execute("DELETE FROM Pinned WHERE record_id=?", (record_id,))
        else:
            self.cursor.execute(
                "INSERT INTO Pinned(record_id) VALUES (?)", (record_id,)
            )
        self.commit()

    def is_pinned(self, record_id: int) -> bool:
        self.cursor.execute(
            "SELECT 1 FROM Pinned WHERE record_id=? LIMIT 1", (record_id,)
        )
        return self.cursor.fetchone() is not None

    def get_due_alerts(self):
        """Retrieve alerts that need execution within the next 6 seconds."""
        # now = round(datetime.now().timestamp())
        now = datetime.now()
        now_minus = _fmt_naive(now - timedelta(seconds=2))
        now_plus = _fmt_naive(now + timedelta(seconds=5))
        # log_msg(f"{now_minus = }, {now_plus = }")

        self.cursor.execute(
            """
            SELECT alert_id, record_id, trigger_datetime, start_datetime, alert_name, alert_command
            FROM Alerts
            WHERE (trigger_datetime) BETWEEN ? AND ?
        """,
            (now_minus, now_plus),
        )

        return self.cursor.fetchall()

    def get_active_alerts(self):
        """Retrieve alerts that will trigger on or after the current moment and before midnight."""

        self.cursor.execute(
            """
            SELECT alert_id, record_id, record_name, trigger_datetime, start_datetime, alert_name, alert_command
            FROM Alerts
            ORDER BY trigger_datetime ASC
            """,
        )

        alerts = self.cursor.fetchall()

        if not alerts:
            return []

        results = []
        for alert in alerts:
            (
                alert_id,
                record_id,
                record_name,
                trigger_datetime,
                start_datetime,
                alert_name,
                alert_command,
            ) = alert
            results.append(
                [
                    alert_id,
                    record_id,
                    record_name,
                    trigger_datetime,
                    start_datetime,
                    alert_name,
                    alert_command,
                ]
            )

        return results

    def get_all_tasks(self) -> list[dict]:
        """
        Retrieve all task and project records from the database.

        Returns:
            A list of dictionaries representing task and project records.
        """
        self.cursor.execute(
            """
            SELECT * FROM Records
            WHERE itemtype IN ('~', '^')
            ORDER BY id
            """
        )
        columns = [column[0] for column in self.cursor.description]
        return [dict(zip(columns, row)) for row in self.cursor.fetchall()]

    def get_job_display_subject(self, record_id: int, job_id: int | None) -> str | None:
        """
        Return the display_subject for a given record_id + job_id pair.
        Falls back to None if not found or no display_subject is present.
        """
        if job_id is None:
            return None

        self.cursor.execute("SELECT jobs FROM Records WHERE id=?", (record_id,))
        row = self.cursor.fetchone()
        if not row or not row[0]:
            return None

        jobs = _parse_jobs_json(row[0])
        for job in jobs:
            if job.get("job_id") == job_id:
                return job.get("display_subject") or None

        return None

    def get_job_dict(self, record_id: int, job_id: int | None) -> dict | None:
        """
        Return the full job dictionary for the given record_id + job_id pair.
        Returns None if not found.

        """
        if job_id is None:
            return None

        self.cursor.execute("SELECT jobs FROM Records WHERE id=?", (record_id,))
        row = self.cursor.fetchone()
        if not row or not row[0]:
            return None

        jobs = _parse_jobs_json(row[0])
        for job in jobs:
            if job.get("job_id") == job_id:
                return job  # Return the full dictionary

        return None

    def get_all_alerts(self):
        """Retrieve all stored alerts for debugging."""
        self.cursor.execute("""
            SELECT alert_id, record_id, record_name, start_datetime, timedelta, command
            FROM Alerts
            ORDER BY start_datetime ASC
        """)
        alerts = self.cursor.fetchall()

        if not alerts:
            return [
                "🔔 No alerts found.",
            ]

        results = [
            "🔔 Current Alerts:",
        ]
        for alert in alerts:
            alert_id, record_id, record_name, start_dt, td, command = alert
            execution_time = start_dt - td  # When the alert is scheduled to run
            formatted_time = datetime_from_timestamp(execution_time).strftime(
                "%Y-%m-%d %H:%M"
            )

            results.append([alert_id, record_id, record_name, formatted_time, command])

        return results

    def mark_alert_executed(self, alert_id):
        """Optional: Mark alert as executed to prevent duplicate execution."""
        self.cursor.execute(
            """
            DELETE FROM Alerts WHERE alert_id = ?
        """,
            (alert_id,),
        )
        self.commit()

    def create_alert(
        self,
        command_name,
        timedelta,
        start_datetime,
        record_id,
        record_name,
        record_description,
        record_location,
    ):
        if command_name == "n":
            alert_command = "{name} {when} ({start})"
        else:
            alert_command = self.ALERTS.get(command_name, "")
        if not alert_command:
            log_msg(f"❌ Alert command not found for '{command_name}'")
            return None  # Explicitly return None if command is missing

        name = record_name
        description = record_description
        location = record_location

        if timedelta > 0:
            when = f"in {duration_in_words(timedelta)}"
        elif timedelta == 0:
            when = "now"
        else:
            when = f"{duration_in_words(-timedelta)} ago"

        start = format_datetime(start_datetime, HRS_MINS)
        time_fmt = datetime_in_words(start_datetime)

        alert_command = alert_command.format(
            name=name,
            when=when,
            time=time_fmt,
            description=description,
            location=location,
            start=start,
        )
        return alert_command

    def create_alert(
        self,
        command_name,
        timedelta,
        start_datetime,
        record_id,
        record_name,
        record_description,
        record_location,
    ):
        if command_name == "n":
            alert_command_template = "{name} {when} at {start}"
        else:
            alert_command_template = self.ALERTS.get(command_name, "")
        if not alert_command_template:
            log_msg(f"❌ Alert command not found for '{command_name}'")
            return None

        name = record_name
        description = record_description
        location = record_location

        if timedelta > 0:
            when = f"in {duration_in_words(timedelta)}"
        elif timedelta == 0:
            when = "now"
        else:
            when = f"{duration_in_words(-timedelta)} ago"

        start = format_datetime(start_datetime, HRS_MINS)
        start_words = datetime_in_words(start_datetime)

        # Prepare dict of available fields
        field_values = {
            "name": name,
            "when": when,
            "start": start,
            "time": start_words,
            "description": description,
            "location": location,
        }

        # Use SafeDict to avoid KeyError for missing placeholders
        formatted = None
        try:
            formatted = alert_command_template.format_map(SafeDict(field_values))
        except Exception as e:
            log_msg(f"❌ Alert formatting error for command '{command_name}': {e}")
            # Fallback: use a minimal template or use the raw template
            formatted = alert_command_template.format_map(SafeDict(field_values))

        return formatted

    def get_notice_for_today(self):
        self.cursor.execute("""
            SELECT Records.itemtype, Records.subject, notice.days_remaining
            FROM notice
            JOIN Records ON notice.record_id = Records.id
            ORDER BY notice.days_remaining ASC
        """)
        return [
            (
                record_id,
                itemtype,
                subject,
                int(round(days_remaining)),
            )
            for (
                record_id,
                itemtype,
                subject,
                days_remaining,
            ) in self.cursor.fetchall()
        ]

    def get_tokens(self, record_id: int):
        """
        Retrieve the tokens field from a record and return it as a list of dictionaries.
        Returns an empty list if the field is null, empty, or if the record is not found.
        """
        self.cursor.execute(
            "SELECT tokens, rruleset, created, modified FROM Records WHERE id = ?",
            (record_id,),
        )
        results = []
        secret = getattr(self.env.config, "secret", "")
        for tokens, rruleset, created, modified in self.cursor.fetchall():
            try:
                token_list = json.loads(tokens) if tokens else []
            except Exception:
                token_list = []
            token_list = reveal_mask_tokens(token_list, secret)
            results.append((token_list, rruleset, created, modified))
        return results

    def get_goal_records(self) -> list[tuple[int, str, str]]:
        """Return (record_id, subject, tokens_json) for goal reminders."""
        self.cursor.execute(
            """
            SELECT id, subject, tokens
            FROM Records
            WHERE itemtype = '!'
            ORDER BY id
            """
        )
        return self.cursor.fetchall()

    def update_record_tokens(self, record_id: int, tokens: list[dict]) -> None:
        """Persist an updated tokens list for a record."""
        serialized = json.dumps(tokens or [])
        self.cursor.execute(
            "UPDATE Records SET tokens = ?, modified = ? WHERE id = ?",
            (serialized, utc_now_string(), record_id),
        )
        self.commit()

    def iter_records_for_query(self):
        """
        Yield dictionaries containing id, itemtype, subject, and decoded tokens for queries.
        """
        self.cursor.execute(
            "SELECT id, itemtype, subject, tokens FROM Records ORDER BY id ASC"
        )
        for record_id, itemtype, subject, token_blob in self.cursor.fetchall():
            yield {
                "id": record_id,
                "itemtype": itemtype or "",
                "subject": subject or "",
                "tokens": self._tokens_list(token_blob),
            }

    def populate_alerts(self):
        """
        Populate the Alerts table for all records that have alerts defined.
        Inserts alerts that will trigger between now and local end-of-day.
        Uses TEXT datetimes ('YYYYMMDD' or 'YYYYMMDDTHHMMSS', local-naive).
        """

        # --- small helpers for TEXT <-> datetime (local-naive) ---
        from datetime import datetime, timedelta

        def _parse_local_text_dt(s: str) -> datetime:
            """Parse 'YYYYMMDD' or 'YYYYMMDDTHHMMSS' (local-naive) into datetime."""
            s = (s or "").strip()
            if not s:
                raise ValueError("empty datetime text")
            if "T" in s:
                # datetime
                return datetime.strptime(s, "%Y%m%dT%H%M")
            else:
                # date-only -> treat as midnight local
                return datetime.strptime(s, "%Y%m%d")

        def _to_text_dt(dt: datetime, is_date_only: bool = False) -> str:
            """
            Render datetime back to TEXT storage.
            If is_date_only=True, keep 'YYYYMMDD'; else use 'YYYYMMDDTHHMMSS'.
            """
            if is_date_only:
                return dt.strftime("%Y%m%d")
            return dt.strftime("%Y%m%dT%H%M")

        def _is_date_only_text(s: str) -> bool:
            return "T" not in (s or "")

        # --- time window (local-naive) ---
        now = datetime.now()
        end_of_day = now.replace(hour=23, minute=59, second=59, microsecond=0)

        # Targeted delete: remove alerts in [now, end_of_day] so we can repopulate without duplicates.
        self.cursor.execute(
            """
            DELETE FROM Alerts
            WHERE trigger_datetime >= ?
            AND trigger_datetime <= ?
            """,
            (now.strftime("%Y%m%dT%H%M"), end_of_day.strftime("%Y%m%dT%H%M")),
        )
        self.commit()

        # Find records that have alerts and at least one DateTimes row
        self.cursor.execute(
            """
            SELECT R.id, R.subject, R.description, R.context, R.alerts, D.start_datetime
            FROM Records R
            JOIN DateTimes D ON R.id = D.record_id
            WHERE R.alerts IS NOT NULL AND R.alerts != ''
            """
        )
        records = self.cursor.fetchall()
        if not records:
            print("🔔 No records with alerts found.")
            return

        for (
            record_id,
            record_name,
            record_description,
            record_location,
            alerts_json,
            start_text,
        ) in records:
            # start_text is local-naive TEXT ('YYYYMMDD' or 'YYYYMMDDTHHMMSS')
            try:
                start_dt = _parse_local_text_dt(start_text)
            except Exception as e:
                # bad/malformed DateTimes row; skip gracefully
                print(
                    f"⚠️ Skipping record {record_id}: invalid start_datetime {start_text!r}: {e}"
                )
                continue

            is_date_only = _is_date_only_text(start_text)

            try:
                alert_list = json.loads(alerts_json)
                if not isinstance(alert_list, list):
                    continue
            except Exception:
                continue

            for alert in alert_list:
                if ":" not in alert:
                    continue  # ignore malformed alerts like "10m" with no command
                time_part, command_part = alert.split(":", 1)

                # support multiple lead times and multiple commands per line
                try:
                    lead_secs_list = [
                        td_str_to_seconds(t.strip()) for t in time_part.split(",")
                    ]
                except Exception:
                    continue
                commands = [
                    cmd.strip() for cmd in command_part.split(",") if cmd.strip()
                ]
                if not commands:
                    continue

                # For date-only starts, we alert relative to midnight (00:00:00) of that day
                if is_date_only:
                    effective_start_dt = start_dt.replace(
                        hour=0, minute=0, second=0, microsecond=0
                    )
                else:
                    effective_start_dt = start_dt

                for lead_secs in lead_secs_list:
                    trigger_dt = effective_start_dt - timedelta(seconds=lead_secs)

                    # only alerts that trigger today between now and end_of_day
                    if not (now <= trigger_dt <= end_of_day):
                        continue

                    trigger_text = _to_text_dt(trigger_dt)  # always 'YYYYMMDDTHHMMSS'
                    start_store_text = _to_text_dt(
                        effective_start_dt, is_date_only=is_date_only
                    )

                    for alert_name in commands:
                        # If you have a helper that *builds* the command string, call it;
                        # otherwise keep your existing create_alert signature but pass TEXTs.
                        alert_command = self.create_alert(
                            alert_name,
                            lead_secs,
                            start_store_text,  # now TEXT, not epoch
                            record_id,
                            record_name,
                            record_description,
                            record_location,
                        )

                        if not alert_command:
                            continue

                        # Unique index will prevent duplicates; OR IGNORE keeps this idempotent.
                        self.cursor.execute(
                            """
                            INSERT OR IGNORE INTO Alerts
                                (record_id, record_name, trigger_datetime, start_datetime, alert_name, alert_command)
                            VALUES (?, ?, ?, ?, ?, ?)
                            """,
                            (
                                record_id,
                                record_name,
                                trigger_text,
                                start_store_text,
                                alert_name,
                                alert_command,
                            ),
                        )

        self.commit()
        log_msg("✅ Alerts table updated with today's relevant alerts.")

    def populate_alerts_for_record(self, record_id: int):
        """
        Regenerate alerts for a specific record, for alerts that trigger today
        (local time), using the same TEXT-based semantics as populate_alerts().
        """

        # --- small helpers (you can factor these out to avoid duplication) ---
        def _parse_local_text_dt(s: str) -> datetime:
            """Parse 'YYYYMMDD' or 'YYYYMMDDTHHMM' (local-naive) into datetime."""
            s = (s or "").strip()
            if not s:
                raise ValueError("empty datetime text")
            if "T" in s:
                return datetime.strptime(s, "%Y%m%dT%H%M")
            else:
                return datetime.strptime(s, "%Y%m%d")

        def _to_text_dt(dt: datetime, is_date_only: bool = False) -> str:
            """Render datetime back to TEXT storage."""
            if is_date_only:
                return dt.strftime("%Y%m%d")
            return dt.strftime("%Y%m%dT%H%M")

        def _is_date_only_text(s: str) -> bool:
            return "T" not in (s or "")

        # --- time window (local-naive) ---
        now = datetime.now()
        end_of_day = now.replace(hour=23, minute=59, second=59, microsecond=0)

        now_text = now.strftime("%Y%m%dT%H%M")
        eod_text = end_of_day.strftime("%Y%m%dT%H%M")

        # Clear old alerts for this record in today's window
        self.cursor.execute(
            """
            DELETE FROM Alerts
            WHERE record_id = ?
            AND trigger_datetime >= ?
            AND trigger_datetime <= ?
            """,
            (record_id, now_text, eod_text),
        )
        self.commit()

        # Look up the record’s alert data and start datetimes
        self.cursor.execute(
            """
            SELECT R.id, R.subject, R.description, R.context, R.alerts, D.start_datetime
            FROM Records R
            JOIN DateTimes D ON R.id = D.record_id
            WHERE R.id = ?
            AND R.alerts IS NOT NULL
            AND R.alerts != ''
            """,
            (record_id,),
        )
        records = self.cursor.fetchall()
        if not records:
            return

        for (
            rec_id,
            record_name,
            record_description,
            record_location,
            alerts_json,
            start_text,
        ) in records:
            try:
                start_dt = _parse_local_text_dt(start_text)
            except Exception as e:
                log_msg(
                    f"⚠️ Skipping record {rec_id}: invalid start_datetime {start_text!r}: {e}"
                )
                continue

            is_date_only = _is_date_only_text(start_text)

            try:
                alert_list = json.loads(alerts_json)
                if not isinstance(alert_list, list):
                    continue
            except Exception:
                continue

            for alert in alert_list:
                if ":" not in alert:
                    continue  # malformed, e.g. "10m"
                time_part, command_part = alert.split(":", 1)

                try:
                    lead_secs_list = [
                        td_str_to_seconds(t.strip()) for t in time_part.split(",")
                    ]
                except Exception:
                    continue

                commands = [
                    cmd.strip() for cmd in command_part.split(",") if cmd.strip()
                ]
                if not commands:
                    continue

                # For date-only starts, schedule relative to midnight of that day
                if is_date_only:
                    effective_start_dt = start_dt.replace(
                        hour=0, minute=0, second=0, microsecond=0
                    )
                else:
                    effective_start_dt = start_dt

                for lead_secs in lead_secs_list:
                    trigger_dt = effective_start_dt - timedelta(seconds=lead_secs)

                    # only alerts that trigger today between now and end_of_day
                    if not (now <= trigger_dt <= end_of_day):
                        continue

                    trigger_text = _to_text_dt(trigger_dt)
                    start_store_text = _to_text_dt(
                        effective_start_dt, is_date_only=is_date_only
                    )

                    for alert_name in commands:
                        alert_command = self.create_alert(
                            alert_name,
                            lead_secs,
                            start_store_text,  # TEXT, same as in populate_alerts()
                            rec_id,
                            record_name,
                            record_description,
                            record_location,
                        )
                        if not alert_command:
                            continue

                        self.cursor.execute(
                            """
                            INSERT OR IGNORE INTO Alerts
                                (record_id, record_name, trigger_datetime, start_datetime, alert_name, alert_command)
                            VALUES (?, ?, ?, ?, ?, ?)
                            """,
                            (
                                rec_id,
                                record_name,
                                trigger_text,
                                start_store_text,
                                alert_name,
                                alert_command,
                            ),
                        )

        self.commit()

    def get_generated_weeks_range(self) -> tuple[int, int, int, int] | None:
        row = self.cursor.execute(
            "SELECT start_year, start_week, end_year, end_week FROM GeneratedWeeks"
        ).fetchone()
        return tuple(row) if row else None

    def _format_rrule_datetime(self, value: str) -> str:
        text = (value or "").strip()
        if not text:
            return text
        try:
            dt = dateutil_parser.parse(text)
        except Exception:
            return text

        if isinstance(dt, datetime):
            has_z = text.upper().endswith("Z")
            if has_z:
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=tz.UTC)
                else:
                    dt = dt.astimezone(tz.UTC)
                fmt = "%Y%m%dT%H%M%S" if dt.second else "%Y%m%dT%H%M"
                return dt.strftime(fmt) + "Z"
            fmt = "%Y%m%dT%H%M%S" if dt.second else "%Y%m%dT%H%M"
            return dt.strftime(fmt)
        if isinstance(dt, date):
            return dt.strftime("%Y%m%d")
        return text

    def _normalize_rruleset(self, rule_str: str) -> str:
        if not rule_str:
            return ""

        cleaned = re.sub(
            r"\s+(RRULE:|RDATE:|EXDATE:|DTSTART:)",
            r"\n\1",
            rule_str,
            flags=re.IGNORECASE,
        )

        normalized: list[str] = []
        for raw_line in cleaned.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            upper = line.upper()
            if upper.startswith("DTSTART:"):
                _, body = line.split(":", 1)
                normalized.append(f"DTSTART:{self._format_rrule_datetime(body)}")
            elif upper.startswith("RDATE:"):
                _, body = line.split(":", 1)
                parts = [
                    self._format_rrule_datetime(part)
                    for part in body.split(",")
                    if part
                ]
                normalized.append(f"RDATE:{','.join(parts)}")
            else:
                normalized.append(line)
        return "\n".join(normalized)

    @staticmethod
    def _week_key(year: int, week: int) -> tuple[int, int]:
        return (year, week)

    @staticmethod
    def _advance_week(year: int, week: int, weeks: int) -> tuple[int, int]:
        base = datetime.strptime(f"{year} {week} 1", "%G %V %u") + timedelta(
            weeks=weeks
        )
        return base.isocalendar()[:2]

    @staticmethod
    def _range_includes(
        range_tuple: tuple[int, int, int, int], week: tuple[int, int]
    ) -> bool:
        sy, sw, ey, ew = range_tuple
        start_key = (sy, sw)
        end_key = (ey, ew)
        return start_key <= week <= end_key

    def _parse_rdate_to_seconds(self, value: str) -> int | None:
        text = (value or "").strip()
        if not text:
            return None
        try:
            dt = parse_utc_z(text)
        except Exception:
            try:
                dt = dateutil_parser.parse(text)
            except Exception:
                return None

        if isinstance(dt, date) and not isinstance(dt, datetime):
            dt = datetime.combine(dt, datetime.min.time())

        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=tz.tzlocal())

        return round(dt.timestamp())

    def is_week_in_generated(self, year: int, week: int) -> bool:
        rng = self.get_generated_weeks_range()
        if not rng:
            return False
        sy, sw, ey, ew = rng
        return (
            self._week_key(sy, sw)
            <= self._week_key(year, week)
            <= self._week_key(ey, ew)
        )

    @staticmethod
    def _iso_date(year: int, week: int, weekday: int = 1) -> datetime:
        # ISO: %G (ISO year), %V (ISO week), %u (1..7, Monday=1)
        return datetime.strptime(f"{year} {week} {weekday}", "%G %V %u")

    def _weeks_between(self, a: tuple[int, int], b: tuple[int, int]) -> int:
        da = self._iso_date(*a)
        db = self._iso_date(*b)
        return (db - da).days // 7

    def ensure_week_generated_with_topup(
        self,
        year: int,
        week: int,
        cushion: int = 6,
        topup_threshold: int = 2,
    ) -> bool:
        """
        Ensure (year, week) exists in DateTimes.
        - If it's outside the cached range (earlier or later): extend to include it (+ cushion).
        - If it's inside but within `topup_threshold` weeks of either edge, extend a bit past that edge.
        Returns True if any extension was performed.
        """
        rng = self.get_generated_weeks_range()

        # No range yet: seed it from requested week
        if not rng:
            self.extend_datetimes_for_weeks(year, week, cushion + 1)
            return True

        sy, sw, ey, ew = rng
        wk_key = self._week_key(year, week)

        # Outside range -> extend starting at requested week
        if wk_key < self._week_key(sy, sw) or wk_key > self._week_key(ey, ew):
            self.extend_datetimes_for_weeks(year, week, cushion + 1)
            return True

        # Inside range: check “near left” edge
        if self._weeks_between((sy, sw), (year, week)) <= topup_threshold:
            earlier_start = self._iso_date(sy, sw) - timedelta(weeks=cushion)
            e_y, e_w = earlier_start.isocalendar()[:2]
            self.extend_datetimes_for_weeks(e_y, e_w, cushion + 1)
            return True

        # Inside range: check “near right” edge
        if self._weeks_between((year, week), (ey, ew)) <= topup_threshold:
            start_after = self._iso_date(ey, ew) + timedelta(weeks=1)
            n_y, n_w = start_after.isocalendar()[:2]
            self.extend_datetimes_for_weeks(n_y, n_w, cushion)
            return True

        return False

    def extend_datetimes_for_weeks(self, start_year, start_week, weeks):
        """
        Extend the DateTimes table by generating data for the specified number of weeks
        starting from a given year and week.

        Args:
            start_year (int): The starting year.
            start_week (int): The starting ISO week.
            weeks (int): Number of weeks to generate.
        """
        start = datetime.strptime(f"{start_year} {start_week} 1", "%G %V %u")
        end = start + timedelta(weeks=weeks)

        start_year, start_week = start.isocalendar()[:2]
        end_year, end_week = end.isocalendar()[:2]

        self.cursor.execute(
            "SELECT start_year, start_week, end_year, end_week FROM GeneratedWeeks"
        )
        cached_ranges = self.cursor.fetchall()

        # Determine the full range that needs to be generated
        min_year = (
            min(cached_ranges, key=lambda x: x[0])[0] if cached_ranges else start_year
        )
        min_week = (
            min(cached_ranges, key=lambda x: x[1])[1] if cached_ranges else start_week
        )
        max_year = (
            max(cached_ranges, key=lambda x: x[2])[2] if cached_ranges else end_year
        )
        max_week = (
            max(cached_ranges, key=lambda x: x[3])[3] if cached_ranges else end_week
        )

        # Expand the range to include gaps and requested period
        if start_year < min_year or (start_year == min_year and start_week < min_week):
            min_year, min_week = start_year, start_week
        if end_year > max_year or (end_year == max_year and end_week > max_week):
            max_year, max_week = end_year, end_week

        first_day = datetime.strptime(f"{min_year} {min_week} 1", "%G %V %u")
        last_day = datetime.strptime(
            f"{max_year} {max_week} 1", "%G %V %u"
        ) + timedelta(days=6)

        # Generate new datetimes for the extended range
        self.generate_datetimes_for_period(first_day, last_day)

        # Update the GeneratedWeeks table
        self.cursor.execute("DELETE FROM GeneratedWeeks")  # Clear old entries
        self.cursor.execute(
            """
        INSERT INTO GeneratedWeeks (start_year, start_week, end_year, end_week)
        VALUES (?, ?, ?, ?)
        """,
            (min_year, min_week, max_year, max_week),
        )

        self.commit()

    def generate_datetimes(self, rule_str, extent, start_date, end_date):
        """
        Generate occurrences for a given rruleset within the specified date range.

        Args:
            rule_str (str): The rrule string defining the recurrence rule.
            extent (int): The duration of each occurrence in minutes.
            start_date (datetime): The start of the range.
            end_date (datetime): The end of the range.

        Returns:
            List[Tuple[datetime, datetime]]: A list of (start_dt, end_dt) tuples.
        """

        rule = rrulestr(rule_str, dtstart=start_date)
        occurrences = list(rule.between(start_date, end_date, inc=True))
        extent = td_str_to_td(extent) if isinstance(extent, str) else extent

        # Create (start, end) pairs
        results = []
        for start_dt in occurrences:
            end_dt = start_dt + extent if extent else start_dt
            results.append((start_dt, end_dt))

        return results

    def generate_datetimes_for_record(
        self,
        record_id: int,
        *,
        window: tuple[datetime, datetime] | None = None,
        clear_existing: bool = True,
    ) -> None:
        """
        Regenerate DateTimes rows for a single record.

        Behavior:
        • If the record has jobs (project): generate rows for jobs ONLY (job_id set).
        • If the record has no jobs (event or single task): generate rows for the parent
            itself (job_id NULL).
        • Notes / unscheduled: nothing.

        Infinite rules: constrained to `window` when provided.
        Finite rules: generated fully (window ignored).
        """
        # Fetch core fields including itemtype and jobs JSON
        self.cursor.execute(
            "SELECT itemtype, rruleset, extent, jobs, processed FROM Records WHERE id=?",
            (record_id,),
        )
        row = self.cursor.fetchone()
        if not row:
            log_msg(f"⚠️ No record found id={record_id}")
            return

        itemtype, rruleset, record_extent, jobs_json, processed = row
        raw_rule = (rruleset or "").replace("\\N", "\n").replace("\\n", "\n")
        is_aware = "Z" in raw_rule
        rule_str = self._normalize_rruleset(raw_rule)

        # Nothing to do without any schedule
        if not rule_str:
            return

        # Optional: clear existing rows for this record
        if clear_existing:
            self.cursor.execute(
                "DELETE FROM DateTimes WHERE record_id = ?", (record_id,)
            )

        # Parse jobs (if any)
        jobs = _parse_jobs_json(jobs_json)
        has_jobs = bool(jobs)
        # log_msg(f"{has_jobs = }, {jobs = }")

        has_rrule = "RRULE" in rule_str
        is_finite = (not has_rrule) or ("COUNT=" in rule_str) or ("UNTIL=" in rule_str)

        # Build parent recurrence iterator
        try:
            rule = rrulestr(rule_str)
        except Exception as e:
            log_msg(
                f"rrulestr failed for record {record_id}: {e}\n---\n{rule_str}\n---"
            )
            return

        def _iter_parent_occurrences():
            if is_finite:
                anchor = get_anchor(is_aware)

                try:
                    cur = rule.after(anchor, inc=True)
                except TypeError:
                    log_msg(
                        f"exception processing {anchor = } with {is_aware = } in {record_id = }"
                    )
                    cur = None

                while cur is not None:
                    yield cur
                    cur = rule.after(cur, inc=False)
            else:
                if window:
                    lo, hi = window
                    try:
                        occs = rule.between(lo, hi, inc=True)
                    except TypeError:
                        if lo.tzinfo is None:
                            lo = lo.replace(tzinfo=tz.UTC)
                        if hi.tzinfo is None:
                            hi = hi.replace(tzinfo=tz.UTC)
                        occs = rule.between(lo, hi, inc=True)
                    for cur in occs:
                        yield cur
                else:
                    # default horizon for infinite rules
                    start = datetime.now()
                    end = start + timedelta(weeks=12)
                    try:
                        occs = rule.between(start, end, inc=True)
                    except TypeError:
                        occs = rule.between(
                            start.replace(tzinfo=tz.UTC),
                            end.replace(tzinfo=tz.UTC),
                            inc=True,
                        )
                    for cur in occs:
                        yield cur

        extent_sec_record = td_str_to_seconds(record_extent or "")

        # ---- PATH A: Projects with jobs -> generate job rows only ----
        if has_jobs:
            for parent_dt in _iter_parent_occurrences():
                if isinstance(parent_dt, datetime):
                    base_parent = parent_dt
                    if base_parent.tzinfo is None and is_aware:
                        base_parent = base_parent.replace(tzinfo=tz.UTC)
                    parent_local = _to_local_naive(base_parent)
                else:
                    parent_local = datetime.combine(parent_dt, datetime.min.time())
                for j in jobs:
                    if j.get("status") == "finished":
                        continue
                    job_id = j.get("job_id")
                    off_sec = td_str_to_seconds(j.get("offset_str") or "")
                    job_start = _shift_from_parent(parent_local, off_sec)
                    job_extent_sec = (
                        td_str_to_seconds(j.get("extent_str") or "")
                        or extent_sec_record
                    )

                    if job_extent_sec:
                        job_end = job_start + timedelta(seconds=job_extent_sec)
                        try:
                            # preferred: split across days if you have this helper
                            for seg_start, seg_end in _split_span_local_days(
                                job_start, job_end
                            ):
                                s_txt = _fmt_naive(seg_start)
                                e_txt = (
                                    None
                                    if seg_end == seg_start
                                    else _fmt_naive(seg_end)
                                )
                                self.cursor.execute(
                                    "INSERT OR IGNORE INTO DateTimes (record_id, job_id, start_datetime, end_datetime) VALUES (?, ?, ?, ?)",
                                    (record_id, job_id, s_txt, e_txt),
                                )
                        except NameError:
                            # fallback: single row
                            self.cursor.execute(
                                "INSERT OR IGNORE INTO DateTimes (record_id, job_id, start_datetime, end_datetime) VALUES (?, ?, ?, ?)",
                                (
                                    record_id,
                                    job_id,
                                    _fmt_naive(job_start),
                                    _fmt_naive(job_end),
                                ),
                            )
                        except Exception as e:
                            log_msg(f"error: {e}")
                    else:
                        self.cursor.execute(
                            "INSERT OR IGNORE INTO DateTimes (record_id, job_id, start_datetime, end_datetime) VALUES (?, ?, ?, NULL)",
                            (record_id, job_id, _fmt_naive(job_start)),
                        )

        # ---- PATH B: Events / single tasks (no jobs) -> generate parent rows ----
        else:
            for cur in _iter_parent_occurrences():
                # cur can be aware/naive datetime (or, rarely, date)
                if isinstance(cur, datetime):
                    base_dt = cur
                    if base_dt.tzinfo is None and is_aware:
                        base_dt = base_dt.replace(tzinfo=tz.UTC)
                    start_local = _to_local_naive(base_dt)
                else:
                    start_local = datetime.combine(cur, datetime.min.time())
                start_local = datetime_from_timestamp(_fmt_naive(start_local))

                if extent_sec_record:
                    end_local = (
                        start_local + timedelta(seconds=extent_sec_record)
                        if isinstance(start_local, datetime)
                        else datetime.combine(start_local, datetime.min.time())
                        + timedelta(seconds=extent_sec_record)
                    )
                    end_local = datetime_from_timestamp(_fmt_naive(end_local))
                    segments = _split_span_local_days(start_local, end_local)
                    for seg_start, seg_end in segments:
                        s_txt = _fmt_naive(seg_start)
                        e_txt = None if seg_end == seg_start else _fmt_naive(seg_end)
                        self.cursor.execute(
                            "INSERT OR IGNORE INTO DateTimes (record_id, job_id, start_datetime, end_datetime) VALUES (?, NULL, ?, ?)",
                            (record_id, s_txt, e_txt),
                        )
                else:
                    self.cursor.execute(
                        "INSERT OR IGNORE INTO DateTimes (record_id, job_id, start_datetime, end_datetime) VALUES (?, NULL, ?, NULL)",
                        (record_id, _fmt_naive(start_local)),
                    )

        # Mark finite as processed only when we generated full set (no window)
        if is_finite and not window:
            self.cursor.execute(
                "UPDATE Records SET processed = 1 WHERE id = ?", (record_id,)
            )
        self.commit()

    def get_events_for_period(self, start_date: datetime, end_date: datetime):
        """
        Retrieve all events that occur or overlap within [start_date, end_date),
        ordered by start time.

        Returns rows as:
            (start_datetime, end_datetime, itemtype, subject, record_id, job_id)

        DateTimes table stores TEXT:
        - date-only: 'YYYYMMDD'
        - datetime:  'YYYYMMDDTHHMMSS'
        - end_datetime may be NULL (instantaneous)

        Overlap rule:
        normalized_end   >= period_start_key
        normalized_start <  period_end_key
        """
        start_key = _to_key(start_date)
        end_key = _to_key(end_date)

        sql = """
        SELECT
            dt.id,
            dt.start_datetime,
            dt.end_datetime,
            r.itemtype,
            r.subject,
            r.id,
            dt.job_id
        FROM DateTimes dt
        JOIN Records r ON dt.record_id = r.id
        WHERE
            r.itemtype != '!' AND
            -- normalized end >= period start
            (
                CASE
                    WHEN dt.end_datetime IS NULL THEN
                        CASE
                            WHEN LENGTH(dt.start_datetime) = 8 THEN dt.start_datetime || 'T000000'
                            ELSE dt.start_datetime
                        END
                    WHEN LENGTH(dt.end_datetime) = 8 THEN dt.end_datetime || 'T235959'
                    ELSE dt.end_datetime
                END
            ) >= ?
            AND
            -- normalized start < period end
            (
                CASE
                    WHEN LENGTH(dt.start_datetime) = 8 THEN dt.start_datetime || 'T000000'
                    ELSE dt.start_datetime
                END
            ) < ?
        ORDER BY
            CASE
                WHEN LENGTH(dt.start_datetime) = 8 THEN dt.start_datetime || 'T000000'
                ELSE dt.start_datetime
            END
        """
        self.cursor.execute(sql, (start_key, end_key))
        return self.cursor.fetchall()

    def generate_datetimes_for_period(self, start_date: datetime, end_date: datetime):
        self.cursor.execute("SELECT id FROM Records")
        for (record_id,) in self.cursor.fetchall():
            self.generate_datetimes_for_record(
                record_id,
                window=(start_date, end_date),
                clear_existing=True,
            )

    def get_notice_for_events(self):
        """
        Retrieve (record_id, days_remaining, subject) from notice joined with Records
        for events only (itemtype '*').

        Returns:
            List[Tuple[int, int, str]]: A list of (record_id, days_remaining, subject)
        """
        self.cursor.execute(
            """
            SELECT n.record_id, n.days_remaining, r.subject
            FROM notice n
            JOIN Records r ON n.record_id = r.id
            WHERE r.itemtype = '*'
            ORDER BY n.days_remaining
            """
        )
        return self.cursor.fetchall()

    def get_drafts(self):
        """
        Retrieve all draft records (itemtype '?') with their ID and subject.

        Returns:
            List[Tuple[int, str]]: A list of (id, subject)
        """
        self.cursor.execute(
            """
            SELECT id, subject
            FROM Records
            WHERE itemtype = '?'
            ORDER BY id
            """
        )
        return self.cursor.fetchall()

    def get_urgency(self):
        """
        Return tasks for the Agenda view, with pinned-first ordering.

        Rows:
        (
            record_id,
            job_id,
            subject,
            urgency,
            color,
            status,
            weights,
            pinned_int,
            datetime_id,   -- may be NULL
            instance_ts    -- TEXT start_datetime or NULL
        )
        """
        self.cursor.execute(
            """
            WITH first_per_job AS (
                SELECT
                    record_id,
                    job_id,
                    -- normalized start for correct ordering of date-only vs datetime
                    MIN(
                        CASE
                            WHEN LENGTH(start_datetime) = 8
                                THEN start_datetime || 'T000000'
                            ELSE start_datetime
                        END
                    ) AS first_norm_start
                FROM DateTimes
                GROUP BY record_id, job_id
            ),
            first_dt AS (
                SELECT
                    d.id,
                    d.record_id,
                    d.job_id,
                    d.start_datetime
                FROM DateTimes d
                JOIN first_per_job fp
                ON d.record_id = fp.record_id
                AND COALESCE(d.job_id, -1) = COALESCE(fp.job_id, -1)
                AND CASE
                        WHEN LENGTH(d.start_datetime) = 8
                            THEN d.start_datetime || 'T000000'
                        ELSE d.start_datetime
                    END = fp.first_norm_start
            )
            SELECT
                u.record_id,
                u.job_id,
                u.subject,
                u.urgency,
                u.color,
                u.status,
                u.weights,
                CASE WHEN p.record_id IS NULL THEN 0 ELSE 1 END AS pinned,
                fd.id           AS datetime_id,
                fd.start_datetime AS instance_ts
            FROM Urgency AS u
            JOIN Records AS r
            ON r.id = u.record_id
            LEFT JOIN Pinned AS p
            ON p.record_id = u.record_id
            LEFT JOIN first_dt AS fd
            ON fd.record_id = u.record_id
            AND COALESCE(fd.job_id, -1) = COALESCE(u.job_id, -1)
            WHERE r.itemtype != 'x'
            ORDER BY pinned DESC, u.urgency DESC, u.id ASC
            """
        )
        return self.cursor.fetchall()

    def process_events(self, start_date, end_date):
        """
        Process events and split across days for display.

        Args:
            start_date (datetime): The start of the period.
            end_date (datetime): The end of the period.

        Returns:
            Dict[int, Dict[int, Dict[int, List[Tuple]]]]: Nested dictionary grouped by year, week, and weekday.
        """

        # Retrieve all events for the specified period
        events = self.get_events_for_period(start_date, end_date)
        # Group events by ISO year, week, and weekday
        grouped_events = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))

        # for start_ts, end_ts, itemtype, subject, id, job_id in events:
        for dt_id, start_ts, end_ts, itemtype, subject, id, job_id in events:
            start_dt = (
                datetime_from_timestamp(start_ts)
                # .replace(tzinfo=gettz("UTC"))
                # .astimezone()
                # .replace(tzinfo=None)
            )
            end_dt = (
                datetime_from_timestamp(end_ts)
                # .replace(tzinfo=gettz("UTC"))
                # .astimezone()
                # .replace(tzinfo=None)
            )

            iso_year, iso_week, iso_weekday = start_dt.isocalendar()
            grouped_events[iso_year][iso_week][iso_weekday].append((start_dt, end_dt))

        return grouped_events

    def populate_notice(self):
        """
        Populate the notice table for all records with valid notice entries.
        This clears existing entries and recomputes them from current record data.
        """
        self.cursor.execute("DELETE FROM Notice;")
        self.commit()

        # Fetch both record_id and notice value
        self.cursor.execute(
            "SELECT id, notice FROM Records WHERE notice IS NOT NULL AND notice != ''"
        )
        for record_id, notice in self.cursor.fetchall():
            self.populate_notice_for_record(record_id)

        self.commit()

    def populate_notice_for_record(self, record_id: int):
        self.cursor.execute("SELECT notice FROM Records WHERE id = ?", (record_id,))
        row = self.cursor.fetchone()
        if not row or not row[0]:
            return  # no notice for this record
        notice_str = row[0]

        self.cursor.execute(
            "SELECT start_datetime FROM DateTimes WHERE record_id = ? ORDER BY start_datetime ASC",
            (record_id,),
        )
        occurrences = self.cursor.fetchall()

        today = date.today()
        offset = td_str_to_td(notice_str)

        for (start_ts,) in occurrences:
            scheduled_dt = datetime_from_timestamp(start_ts)
            notice_dt = scheduled_dt - offset
            if notice_dt.date() <= today < scheduled_dt.date():
                days_remaining = (scheduled_dt.date() - today).days
                self.cursor.execute(
                    "INSERT INTO notice (record_id, days_remaining) VALUES (?, ?)",
                    (record_id, days_remaining),
                )
                break  # Only insert for the earliest qualifying instance

        self.commit()

    def _next_start_seconds(
        self, record_id: int, job_id: int | None = None
    ) -> int | None:
        """
        Return the epoch seconds for the next scheduled start in DateTimes.
        If there is no future start, fall back to the earliest historical start.
        """

        sql = "SELECT start_datetime FROM DateTimes WHERE record_id = ?"
        params: list[object] = [record_id]
        if job_id is None:
            sql += " AND job_id IS NULL"
        else:
            sql += " AND job_id = ?"
            params.append(job_id)
        sql += " ORDER BY start_datetime ASC"

        self.cursor.execute(sql, tuple(params))
        rows = self.cursor.fetchall()
        if not rows:
            return None

        now = datetime.now()
        fallback: int | None = None
        for (start_text,) in rows:
            start_dt = datetime_from_timestamp(start_text)
            if not start_dt:
                continue
            start_seconds = round(start_dt.timestamp())
            if start_dt >= now:
                return start_seconds
            if fallback is None:
                fallback = start_seconds
        return fallback

    def _offset_seconds_from_record(self, record: dict) -> int | None:
        """Extract the first @o interval (in seconds) from stored tokens."""
        tokens_json = record.get("tokens")
        if not tokens_json:
            return None
        try:
            tokens = json.loads(tokens_json)
        except Exception:
            return None
        if not isinstance(tokens, list):
            return None
        for tok in tokens:
            if not isinstance(tok, dict):
                continue
            if tok.get("t") != "@" or tok.get("k") != "o":
                continue
            body = (tok.get("token") or "").strip()
            if body.startswith("@o"):
                body = body[2:].strip()
            body = body.lstrip("~").strip()
            if not body:
                continue
            try:
                return td_str_to_seconds(body)
            except ValueError:
                continue
        return None

    def populate_busy_from_datetimes(self):
        """
        Build BusyWeeksFromDateTimes from DateTimes.
        For each (record_id, year_week) pair, accumulate busybits
        across all event segments — merging with np.maximum().
        """
        import numpy as np

        log_msg("🧩 Rebuilding BusyWeeksFromDateTimes…")
        self.cursor.execute("DELETE FROM BusyWeeksFromDateTimes")

        # Only include Records that are events (itemtype='*')
        self.cursor.execute("""
            SELECT dt.record_id, dt.start_datetime, dt.end_datetime
            FROM DateTimes AS dt
            JOIN Records AS r ON r.id = dt.record_id
            WHERE r.itemtype = '*'
        """)
        rows = self.cursor.fetchall()
        if not rows:
            print("⚠️ No event DateTimes entries found.")
            return

        total_inserted = 0
        for record_id, start_str, end_str in rows:
            weeks = fine_busy_bits_for_event(start_str, end_str)
            for yw, arr in weeks.items():
                # ensure numpy array
                arr = np.asarray(arr, dtype=np.uint8)

                # check if a row already exists for (record_id, week)
                self.cursor.execute(
                    "SELECT busybits FROM BusyWeeksFromDateTimes WHERE record_id=? AND year_week=?",
                    (record_id, yw),
                )
                row = self.cursor.fetchone()
                if row:
                    existing = np.frombuffer(row[0], dtype=np.uint8)
                    merged = np.maximum(existing, arr)
                else:
                    merged = arr

                # upsert
                self.cursor.execute(
                    """
                    INSERT INTO BusyWeeksFromDateTimes (record_id, year_week, busybits)
                    VALUES (?, ?, ?)
                    ON CONFLICT(record_id, year_week)
                    DO UPDATE SET busybits = excluded.busybits
                    """,
                    (record_id, yw, merged.tobytes()),
                )
                total_inserted += 1

        self.commit()
        log_msg(f"✅ BusyWeeksFromDateTimes populated ({total_inserted} week-records).")

    def get_last_instances(
        self,
    ) -> List[Tuple[int, int, int | None, str, str, str, str]]:
        """
        Retrieve the last instances of each record/job falling before today.

        Returns:
            List of tuples:
                (
                    datetime_id,    # DateTimes.id
                    record_id,
                    job_id,         # may be None
                    subject,
                    description,
                    itemtype,
                    instance_ts     # TEXT 'YYYYMMDD' or 'YYYYMMDDTHHMMSS'
                )
        """
        today = datetime.now().strftime("%Y%m%dT%H%M")

        self.cursor.execute(
            """
            WITH last_per_job AS (
                SELECT
                    record_id,
                    job_id,
                    MAX(start_datetime) AS last_datetime
                FROM DateTimes
                WHERE start_datetime < ?
                GROUP BY record_id, job_id
            )
            SELECT
                d.id          AS datetime_id,
                r.id          AS record_id,
                d.job_id      AS job_id,
                r.subject,
                r.description,
                r.itemtype,
                d.start_datetime AS instance_ts
            FROM last_per_job lp
            JOIN DateTimes d
            ON d.record_id = lp.record_id
            AND d.start_datetime = lp.last_datetime
            AND COALESCE(d.job_id, -1) = COALESCE(lp.job_id, -1)
            JOIN Records r
            ON r.id = d.record_id
            ORDER BY d.start_datetime DESC
            """,
            (today,),
        )
        return self.cursor.fetchall()

    def get_records_by_modified(
        self,
    ) -> List[Tuple[int, str | None, str, str | None, str | None]]:
        """
        Return every record ordered by its modified timestamp, newest first.
        """
        self.cursor.execute(
            """
            SELECT id, subject, itemtype, modified, description
            FROM Records
            WHERE modified IS NOT NULL
            ORDER BY modified DESC
            """
        )
        return self.cursor.fetchall()

    #         SELECT
    #             r.id,
    #             d.job_id,
    #             r.subject,
    #             r.description,
    #             r.itemtype,
    #             MIN(d.start_datetime) AS next_datetime
    #         FROM Records r
    #         JOIN DateTimes d ON r.id = d.record_id
    #         WHERE d.start_datetime >= ?
    #         GROUP BY r.id, d.job_id
    #         ORDER BY next_datetime ASC
    #         """,
    #         (today,),
    def get_next_instances(
        self,
    ) -> List[Tuple[int, int, int | None, str, str, str, str]]:
        """
        Retrieve the next instances of each record/job falling on or after today.

        Returns:
            List of tuples:
                (
                    datetime_id,    # DateTimes.id
                    record_id,
                    job_id,         # may be None
                    subject,
                    description,
                    itemtype,
                    instance_ts     # TEXT 'YYYYMMDD' or 'YYYYMMDDTHHMMSS'
                )
        """
        today = datetime.now().strftime("%Y%m%dT%H%M")

        self.cursor.execute(
            """
            WITH next_per_job AS (
                SELECT
                    record_id,
                    job_id,
                    MIN(start_datetime) AS next_datetime
                FROM DateTimes
                WHERE start_datetime >= ?
                GROUP BY record_id, job_id
            )
            SELECT
                d.id          AS datetime_id,
                r.id          AS record_id,
                d.job_id      AS job_id,
                r.subject,
                r.description,
                r.itemtype,
                d.start_datetime AS instance_ts
            FROM next_per_job np
            JOIN DateTimes d
            ON d.record_id = np.record_id
            AND d.start_datetime = np.next_datetime
            AND COALESCE(d.job_id, -1) = COALESCE(np.job_id, -1)
            JOIN Records r
            ON r.id = d.record_id
            ORDER BY d.start_datetime ASC
            """,
            (today,),
        )
        return self.cursor.fetchall()

    def get_next_instance_for_record(
        self, record_id: int
    ) -> tuple[str, str | None] | None:
        """
        Return (start_datetime, end_datetime|NULL) as compact local-naive strings
        for the next instance of a single record, or None if none.
        """
        # start_datetime sorted ascending; end_datetime can be NULL
        self.cursor.execute(
            """
            SELECT start_datetime, end_datetime
            FROM DateTimes
            WHERE record_id = ?
            AND start_datetime >= ?
            ORDER BY start_datetime ASC
            LIMIT 1
            """,
            # now in compact local-naive format
            (_fmt_naive(datetime.now()),),
        )
        row = self.cursor.fetchone()
        if row:
            return row[0], row[1]
        return None

    def get_next_start_datetimes_for_record(
        self,
        record_id: int,
        job_id: int | None = None,
        *,
        limit: int = 2,
    ) -> list[str]:
        """
        Return up to 2 upcoming start datetimes (as compact local-naive strings)
        for the given record (and optional job), sorted ascending.
        """
        limit = max(1, int(limit)) if limit else 1
        sql = """
            SELECT start_datetime
            FROM DateTimes
            WHERE record_id = ?
        """
        # params = [record_id, _fmt_naive(datetime.now())]
        params = [
            record_id,
        ]

        if job_id is not None:
            sql += " AND job_id = ?"
            params.append(job_id)

        sql += " ORDER BY start_datetime ASC LIMIT ?"
        params.append(limit)

        self.cursor.execute(sql, params)
        return [row[0] for row in self.cursor.fetchall()]

    def get_upcoming_instances_for_record(
        self, record_id: int, *, limit: int = 20
    ) -> list[tuple[str, str | None]]:
        """
        Return up to `limit` upcoming instances (start/end) for a record.
        """
        limit = max(1, int(limit)) if limit else 1
        now_key = _fmt_naive(datetime.now())
        self.cursor.execute(
            """
            SELECT start_datetime, end_datetime
            FROM DateTimes
            WHERE record_id = ?
              AND start_datetime >= ?
            ORDER BY start_datetime ASC
            LIMIT ?
            """,
            (record_id, now_key, limit),
        )
        return [(row[0], row[1]) for row in self.cursor.fetchall()]

    def find_records(self, regex: str):
        regex_ci = f"(?i){regex}"  # force case-insensitive
        today = int(datetime.now().timestamp())
        self.cursor.execute(
            """
            WITH
            LastInstances AS (
                SELECT record_id, MAX(start_datetime) AS last_datetime
                FROM DateTimes
                WHERE start_datetime < ?
                GROUP BY record_id
            ),
            NextInstances AS (
                SELECT record_id, MIN(start_datetime) AS next_datetime
                FROM DateTimes
                WHERE start_datetime >= ?
                GROUP BY record_id
            )
            SELECT r.id, r.subject, r.description, r.itemtype, li.last_datetime, ni.next_datetime
            FROM Records r
            LEFT JOIN LastInstances li ON r.id = li.record_id
            LEFT JOIN NextInstances ni ON r.id = ni.record_id
            WHERE r.subject REGEXP ? OR r.description REGEXP ?
            """,
            (today, today, regex_ci, regex_ci),
        )
        return self.cursor.fetchall()

    # FIXME: should access record_id
    def update_tags_for_record(self, record_data):
        cur = self.conn.cursor()
        tags = record_data.pop("tags", [])
        record_data["tokens"] = json.dumps(record_data.get("tokens", []))
        record_data["jobs"] = json.dumps(record_data.get("jobs", []))
        if "id" in record_data:
            record_id = record_data["id"]
            columns = [k for k in record_data if k != "id"]
            assignments = ", ".join([f"{col} = ?" for col in columns])
            values = [record_data[col] for col in columns]
            values.append(record_id)
            cur.execute(f"UPDATE Records SET {assignments} WHERE id = ?", values)
            cur.execute("DELETE FROM RecordTags WHERE record_id = ?", (record_id,))
        else:
            columns = list(record_data.keys())
            values = [record_data[col] for col in columns]
            placeholders = ", ".join(["?"] * len(columns))
            cur.execute(
                f"INSERT INTO Records ({', '.join(columns)}) VALUES ({placeholders})",
                values,
            )
            record_id = cur.lastrowid
        for tag in tags:
            cur.execute("INSERT OR IGNORE INTO Tags (name) VALUES (?)", (tag,))
            cur.execute("SELECT id FROM Tags WHERE name = ?", (tag,))
            tag_id = cur.fetchone()[0]
            cur.execute(
                "INSERT INTO RecordTags (record_id, tag_id) VALUES (?, ?)",
                (record_id, tag_id),
            )
        self.commit()
        return record_id

    def get_tags_for_record(self, record_id):
        cur = self.conn.cursor()
        cur.execute(
            """
            SELECT Tags.name FROM Tags
            JOIN RecordTags ON Tags.id = RecordTags.tag_id
            WHERE RecordTags.record_id = ?
        """,
            (record_id,),
        )
        return [row[0] for row in cur.fetchall()]

    def populate_urgency_from_record(self, record_id: int):
        record = self.get_record_as_dictionary(record_id)

        record_id = record["id"]
        itemtype = record["itemtype"]
        # log_msg(f"{record_id = }, {pinned = }, {record = }")
        modified_seconds = dt_str_to_seconds(record["modified"])
        extent_seconds = td_str_to_seconds(record.get("extent", "0m"))
        # notice_seconds will be 0 in the absence of notice
        notice_seconds = td_str_to_seconds(record.get("notice", "0m"))
        rruleset = record.get("rruleset", "")
        jobs = json.loads(record.get("jobs", "[]"))
        subject = record["subject"]
        # priority_map = self.env.config.urgency.priority.model_dump()
        priority_level = record.get("priority", None)
        # priority = priority_map.get(priority_level, 0)
        description = True if record.get("description", "") else False
        flags = record.get("flags") or ""
        has_offset = "𝕠" in flags

        if itemtype not in ["^", "~"]:
            return

        now_seconds = utc_now_to_seconds()
        pinned = self.is_pinned(record_id)

        # Try to parse due from first RDATE in rruleset
        due_seconds = None
        offset_seconds = None
        if has_offset:
            due_seconds = self._next_start_seconds(record_id, None)
            offset_seconds = self._offset_seconds_from_record(record)
        if due_seconds is None and rruleset.startswith("RDATE:"):
            due_str = rruleset.split(":", 1)[1].split(",")[0]
            parsed_due = self._parse_rdate_to_seconds(due_str)
            if parsed_due is not None:
                due_seconds = parsed_due
            else:
                log_msg(f"Invalid RDATE value: {due_str}")
        if due_seconds is None:
            due_seconds = self._next_start_seconds(record_id, None)
        if due_seconds and not notice_seconds:
            # treat due_seconds as the default for a missing @b, i.e.,
            # make the default to hide a task with an @s due entry before due - interval
            if offset_seconds:
                notice_seconds = offset_seconds
            else:
                notice_seconds = due_seconds

        self.cursor.execute("DELETE FROM Urgency WHERE record_id = ?", (record_id,))

        # Handle jobs if present
        if jobs:
            for job in jobs:
                status = job.get("status", "")
                if status != "available":
                    continue
                job_id = job.get("id")
                subject = job.get("display_subject", subject)

                job_due = self._next_start_seconds(record_id, job_id)
                s_seconds = td_str_to_seconds(job.get("s", "0m"))
                if job_due is None and due_seconds:
                    job_due = due_seconds + s_seconds
                elif job_due is None and s_seconds:
                    job_due = now_seconds + s_seconds

                job_notice = td_str_to_seconds(job.get("b", "0m")) or notice_seconds
                if job_due and job_notice:
                    hide = job_due - job_notice > now_seconds
                    if hide:
                        continue

                job_extent = td_str_to_seconds(job.get("e", "0m"))
                blocking = job.get("blocking")  # assume already computed elsewhere

                urgency, color, weights = self.compute_urgency.from_args_and_weights(
                    now=now_seconds,
                    modified=modified_seconds,
                    due=job_due,
                    extent=job_extent,
                    priority_level=priority_level,
                    blocking=blocking,
                    description=description,
                    jobs=True,
                    pinned=pinned,
                )

                self.cursor.execute(
                    """
                    INSERT INTO Urgency (record_id, job_id, subject, urgency, color, status, weights)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        record_id,
                        job_id,
                        subject,
                        urgency,
                        color,
                        status,
                        json.dumps(weights),
                    ),
                )

        else:
            hide = (
                due_seconds
                and notice_seconds
                and due_seconds - notice_seconds > now_seconds
            )
            if not hide:
                urgency, color, weights = self.compute_urgency.from_args_and_weights(
                    now=now_seconds,
                    modified=modified_seconds,
                    due=due_seconds,
                    extent=extent_seconds,
                    priority_level=priority_level,
                    description=description,
                    jobs=False,
                    pinned=pinned,
                )

                self.cursor.execute(
                    """
                    INSERT INTO Urgency (record_id, job_id, subject, urgency, color, status, weights)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        record_id,
                        None,
                        subject,
                        urgency,
                        color,
                        # record.get("status", "next"),
                        "next",
                        json.dumps(weights),
                    ),
                )

        self.commit()

    def populate_all_urgency(self):
        self.cursor.execute("DELETE FROM Urgency")
        tasks = self.get_all_tasks()
        for task in tasks:
            # log_msg(f"adding to urgency: {task['itemtype'] = }, {task = }")
            self.populate_urgency_from_record(task)
        self.commit()

    def update_urgency(self, urgency_id: int):
        """
        Recalculate urgency score for a given entry using only fields in the Urgency table.
        """
        self.cursor.execute("SELECT urgency_id FROM ActiveUrgency WHERE id = 1")
        row = self.cursor.fetchone()
        active_id = row[0] if row else None

        self.cursor.execute(
            """
            SELECT id, touched, status FROM Urgency WHERE id = ?
        """,
            (urgency_id,),
        )
        row = self.cursor.fetchone()
        if not row:
            return  # skip nonexistent

        urgency_id, touched_ts, status = row
        now_ts = int(time.time())

        # Example scoring
        age_days = (now_ts - touched_ts) / 86400 if touched_ts else 0
        active_bonus = 10.0 if urgency_id == active_id else 0.0
        status_weight = {
            "next": 5.0,
            "scheduled": 2.0,
            "waiting": -1.0,
            "someday": -5.0,
        }.get(status, 0.0)

        score = age_days + active_bonus + status_weight

        self.cursor.execute(
            """
            UPDATE Urgency SET urgency = ? WHERE id = ?
        """,
            (score, urgency_id),
        )
        self.commit()

    def update_all_urgencies(self):
        self.cursor.execute("SELECT id FROM Urgency")
        for (urgency_id,) in self.cursor.fetchall():
            self.update_urgency(urgency_id)

    def get_all(self):
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM Records")
        return cur.fetchall()

    def get_record(self, record_id):
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM Records WHERE id = ?", (record_id,))
        return cur.fetchone()

    def get_record_as_dictionary(self, record: int) -> dict | None:
        if isinstance(record, dict):
            return record
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM Records WHERE id = ?", (record,))
        row = cur.fetchone()
        if row is None:
            return None

        columns = [column[0] for column in cur.description]
        return dict(zip(columns, row))

    def get_jobs_for_record(self, record_id):
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM Records WHERE record_id = ?", (record_id,))
        return cur.fetchall()

    def delete_record(self, record_id):
        cur = self.conn.cursor()
        cur.execute("DELETE FROM Records WHERE id = ?", (record_id,))
        self.commit()
        self.update_busy_weeks_for_record(record_id)

    def count_records(self):
        cur = self.conn.cursor()
        cur.execute("SELECT COUNT(*) FROM Records")
        return cur.fetchone()[0]

    def rebuild_busyweeks_from_source(self):
        """
        Aggregate all BusyWeeksFromDateTimes → BusyWeeks,
        collapsing to 35-slot weekly maps:
        (7 days × [1 all-day + 4 × 6-hour blocks]).

        Ternary encoding:
        0 = free
        1 = busy
        2 = conflict
        """

        self.cursor.execute("SELECT DISTINCT year_week FROM BusyWeeksFromDateTimes")
        weeks = [row[0] for row in self.cursor.fetchall()]
        if not weeks:
            print("⚠️ No data to aggregate.")
            return

        for yw in weeks:
            # --- Gather all event arrays for this week
            self.cursor.execute(
                "SELECT busybits FROM BusyWeeksFromDateTimes WHERE year_week = ?",
                (yw,),
            )
            blobs = [
                np.frombuffer(row[0], dtype=np.uint8) for row in self.cursor.fetchall()
            ]
            if not blobs:
                continue

            n = len(blobs[0])
            if any(arr.size != n for arr in blobs):
                print(f"⚠️ Skipping {yw}: inconsistent array sizes")
                continue

            # Stack vertically -> shape (num_events, 679)
            stack = np.vstack(blobs)

            # Count per slot
            counts = stack.sum(axis=0)

            # Collapse fine bits into ternary (0 free / 1 busy / 2 conflict)
            merged = np.where(counts >= 2, 2, np.where(counts >= 1, 1, 0)).astype(
                np.uint8
            )

            # Reduce 679 fine bits → 35 coarse blocks (7 × [1+4])
            merged = _reduce_to_35_slots(merged)

            # Serialize
            blob = merged.tobytes()

            bits_str = "".join(str(int(x)) for x in merged)
            self.cursor.execute(
                """
                INSERT INTO BusyWeeks (year_week, busybits)
                VALUES (?, ?)
                ON CONFLICT(year_week)
                DO UPDATE SET busybits = excluded.busybits
            """,
                (yw, bits_str),
            )

        self.commit()

    def _aggregate_busy_week(self, year_week: str) -> None:
        import numpy as np

        self.cursor.execute(
            "SELECT busybits FROM BusyWeeksFromDateTimes WHERE year_week = ?",
            (year_week,),
        )
        blobs = [
            np.frombuffer(row[0], dtype=np.uint8) for row in self.cursor.fetchall()
        ]
        if not blobs:
            self.cursor.execute(
                "DELETE FROM BusyWeeks WHERE year_week = ?", (year_week,)
            )
            self.commit()
            return

        stack = np.vstack(blobs)
        counts = stack.sum(axis=0)
        merged = np.where(counts >= 2, 2, np.where(counts >= 1, 1, 0)).astype(np.uint8)
        merged = _reduce_to_35_slots(merged)
        bits_str = "".join(str(int(x)) for x in merged)
        self.cursor.execute(
            """
            INSERT INTO BusyWeeks (year_week, busybits)
            VALUES (?, ?)
            ON CONFLICT(year_week)
            DO UPDATE SET busybits = excluded.busybits
            """,
            (year_week, bits_str),
        )
        self.commit()

    def update_busy_weeks_for_record(self, record_id: int) -> None:
        """
        Recompute busy caches impacted by a single record.
        """
        import numpy as np

        self.cursor.execute(
            "SELECT year_week FROM BusyWeeksFromDateTimes WHERE record_id = ?",
            (record_id,),
        )
        affected = {row[0] for row in self.cursor.fetchall()}
        self.cursor.execute(
            "DELETE FROM BusyWeeksFromDateTimes WHERE record_id = ?", (record_id,)
        )
        self.commit()

        self.cursor.execute("SELECT itemtype FROM Records WHERE id = ?", (record_id,))
        row = self.cursor.fetchone()
        itemtype = row[0] if row else None

        if itemtype == "*":
            self.cursor.execute(
                """
                SELECT start_datetime, end_datetime
                FROM DateTimes
                WHERE record_id = ?
                """,
                (record_id,),
            )
            rows = self.cursor.fetchall()
            week_map: dict[str, np.ndarray] = {}
            for start_str, end_str in rows:
                for year_week, arr in fine_busy_bits_for_event(
                    start_str, end_str
                ).items():
                    affected.add(year_week)
                    arr = np.asarray(arr, dtype=np.uint8)
                    if year_week in week_map:
                        week_map[year_week] = np.maximum(week_map[year_week], arr)
                    else:
                        week_map[year_week] = arr
            for year_week, arr in week_map.items():
                self.cursor.execute(
                    """
                    INSERT INTO BusyWeeksFromDateTimes (record_id, year_week, busybits)
                    VALUES (?, ?, ?)
                    ON CONFLICT(record_id, year_week)
                    DO UPDATE SET busybits = excluded.busybits
                    """,
                    (record_id, year_week, arr.tobytes()),
                )
            self.commit()

        for year_week in affected:
            self._aggregate_busy_week(year_week)

    def show_busy_week(self, year_week: str):
        """
        Display the 7×96 busy/conflict map for a given ISO year-week.

        Reads from BusyWeeks, decodes the blob, and prints 7 lines:
            - one per weekday (Mon → Sun)
            - each line shows 96 characters (15-min slots)
            0 = free, 1 = busy, 2 = conflict

        Example:
            Mon  000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000
            Tue  000000000000111100000000...
            ...
        """
        self.cursor.execute(
            "SELECT busybits FROM BusyWeeks WHERE year_week = ?",
            (year_week,),
        )
        row = self.cursor.fetchone()
        if not row:
            print(f"No BusyWeeks entry for {year_week}")
            return

        # Decode the 672-slot array
        arr = np.frombuffer(row[0], dtype=np.uint8)
        if arr.size != 672:
            print(f"Unexpected busybits length: {arr.size}")
            return

        # Split into 7 days × 96 slots
        days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        slots_per_day = 96

        print(f"🗓  Busy/conflict map for {year_week}\n")
        for i, day in enumerate(days):
            start = i * slots_per_day
            end = start + slots_per_day
            line = "".join(str(x) for x in arr[start:end])
            print(f"{day:<4}{line}")

    def show_busy_week_pretty(self, year_week: str):
        """
        Display a 7×96 busy/conflict map for a given ISO year-week with color and hour markers.
        0 = free, 1 = busy, 2 = conflict (colored red).

        Uses 15-min resolution; 96 slots per day.
        """
        console = Console()

        self.cursor.execute(
            "SELECT busybits FROM BusyWeeks WHERE year_week = ?",
            (year_week,),
        )
        row = self.cursor.fetchone()
        if not row:
            console.print(f"[red]No BusyWeeks entry for {year_week}[/red]")
            return

        arr = np.frombuffer(row[0], dtype=np.uint8)
        if arr.size != 672:
            console.print(f"[red]Unexpected busybits length: {arr.size}[/red]")
            return

        days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        slots_per_day = 96  # 96 x 15min = 24h
        hours = [f"{h:02d}" for h in range(24)]

        # Header row: hour markers
        header = "    "  # spacing before first hour
        for h in hours:
            header += h + " " * 3  # one char per 15 min slot
        console.print(f"[bold cyan]🗓 Busy/conflict map for {year_week}[/bold cyan]\n")
        console.print(header)

        for i, day in enumerate(days):
            start = i * slots_per_day
            end = start + slots_per_day
            line_bits = arr[start:end]

            text_line = Text()
            for bit in line_bits:
                if bit == 0:
                    text_line.append("·", style="dim")  # free
                elif bit == 1:
                    text_line.append("█", style="yellow")  # busy
                elif bit == 2:
                    text_line.append("█", style="bold red")  # conflict

            console.print(f"{day:<4}{text_line}")

    def get_busy_bits_for_week(self, year_week: str) -> list[int]:
        """
        Return a list of 35 ternary busy bits (0=free, 1=busy, 2=conflict)
        for the given ISO year-week string (e.g. '2025-41').
        """
        self.cursor.execute(
            "SELECT busybits FROM BusyWeeks WHERE year_week = ?", (year_week,)
        )
        row = self.cursor.fetchone()
        if not row:
            return [0] * 35

        bits_str = row[0]
        if isinstance(bits_str, bytes):
            bits_str = bits_str.decode("utf-8")

        bits = [int(ch) for ch in bits_str if ch in "012"]
        if len(bits) != 35:
            bits = (bits + [0] * 35)[:35]
        return bits

    def move_bin(self, bin_name: str, new_parent_name: str) -> bool:
        """
        Convenience wrapper that moves bins by name (creating them if missing).
        """
        try:
            self.ensure_system_bins()
            bin_id = self.ensure_bin_exists(bin_name)
            new_parent_id = self.ensure_bin_exists(new_parent_name)
            self.move_bin_to_parent(bin_id, new_parent_id)
            return True
        except Exception as exc:
            print(f"[move_bin] Error moving {bin_name!r} → {new_parent_name!r}: {exc}")
            return False

    def is_descendant(self, ancestor_id: int, candidate_id: int) -> bool:
        """
        Return True if candidate_id is a descendant of ancestor_id.
        """
        self.cursor.execute(
            """
            WITH RECURSIVE descendants(id) AS (
                SELECT bin_id FROM BinLinks WHERE container_id = ?
                UNION
                SELECT BinLinks.bin_id
                FROM BinLinks JOIN descendants ON BinLinks.container_id = descendants.id
            )
            SELECT 1 FROM descendants WHERE id = ? LIMIT 1
        """,
            (ancestor_id, candidate_id),
        )
        return self.cursor.fetchone() is not None

    def ensure_bin_exists(self, name: str) -> int:
        disp = (name or "").strip()
        if not disp:
            raise ValueError("Bin name must be non-empty")

        self.cursor.execute(
            "SELECT id FROM Bins WHERE name = ? COLLATE NOCASE", (disp,)
        )
        row = self.cursor.fetchone()
        if row:
            return row[0]

        self.cursor.execute("INSERT INTO Bins (name) VALUES (?)", (disp,))
        self.commit()
        bid = self.cursor.lastrowid

        # 👇 cache: record the creation with unknown parent (None) for now
        if hasattr(self, "bin_cache"):
            self.bin_cache.on_create(bid, disp, None)

        return bid

    def ensure_bin_path(self, path: str) -> int:
        """
        Ensure the given bin path exists.
        Example:
            "personal/quotations" will create:
                - personal → root
                - quotations → personal
        If single-level, link under 'unlinked'.
        Returns the final (leaf) bin_id.
        """
        root_id, unlinked_id = self.ensure_system_bins()
        parts = [p.strip() for p in path.split("/") if p.strip()]
        if not parts:
            return root_id

        parent_id = root_id  # start at root
        if len(parts) == 1:
            parent_id = unlinked_id  # single bin goes under 'unlinked'

        for name in parts:
            bin_id = self.ensure_bin_exists(name)
            self.cursor.execute(
                """
                INSERT OR IGNORE INTO BinLinks (bin_id, container_id)
                VALUES (?, ?)
            """,
                (bin_id, parent_id),
            )
            parent_id = bin_id

        self.commit()
        return parent_id

    def ensure_bin_path(self, path: str) -> int:
        root_id, unlinked_id = self.ensure_system_bins()
        parts = [p.strip() for p in path.split("/") if p.strip()]
        if not parts:
            return root_id

        parent_id = root_id
        if len(parts) == 1:
            parent_id = unlinked_id  # single bin goes under 'unlinked'

        for name in parts:
            bin_id = self.ensure_bin_exists(name)
            self.cursor.execute(
                "INSERT OR IGNORE INTO BinLinks (bin_id, container_id) VALUES (?, ?)",
                (bin_id, parent_id),
            )

            # 👇 cache: reflect the *actual* parent from DB after the insert/ignore
            if hasattr(self, "bin_cache"):
                self.cursor.execute(
                    "SELECT container_id FROM BinLinks WHERE bin_id=?", (bin_id,)
                )
                row = self.cursor.fetchone()
                eff_parent = row[0] if row else None
                self.bin_cache.on_link(bin_id, eff_parent)

            parent_id = bin_id

        self.commit()
        return parent_id

    def ensure_system_bins(self) -> tuple[int, int]:
        if getattr(self, "_system_bins_initialized", False):
            return self.root_bin_id, self.unlinked_bin_id

        root_id = self.ensure_bin_exists("root")
        unlinked_id = self.ensure_bin_exists("unlinked")

        # Ensure root has no parent (NULL)
        self.cursor.execute(
            "INSERT OR IGNORE INTO BinLinks (bin_id, container_id) VALUES (?, NULL)",
            (root_id,),
        )
        if hasattr(self, "bin_cache"):
            self.bin_cache.on_link(root_id, None)

        # Link unlinked → root
        self.cursor.execute(
            "INSERT OR IGNORE INTO BinLinks (bin_id, container_id) VALUES (?, ?)",
            (unlinked_id, root_id),
        )

        if hasattr(self, "bin_cache"):
            self.bin_cache.on_link(unlinked_id, root_id)

        self.commit()

        self.root_bin_id = root_id
        self.unlinked_bin_id = unlinked_id
        self._system_bins_initialized = True
        self._retire_deleted_bin(unlinked_id)
        return root_id, unlinked_id

    def _retire_deleted_bin(self, unlinked_id: int) -> None:
        """
        Move any legacy 'deleted' bin contents under 'unlinked' and remove the bin.
        """
        deleted_id = self.get_bin_id_by_name("deleted")
        if not deleted_id:
            return

        # Re-parent children of 'deleted' to 'unlinked'
        children = self.cursor.execute(
            "SELECT bin_id FROM BinLinks WHERE container_id = ?", (deleted_id,)
        ).fetchall()
        for (child_id,) in children:
            try:
                self.move_bin_to_parent(child_id, unlinked_id)
            except ValueError:
                # Ignore errors for bins that were already re-parented.
                continue

        # Re-link reminders that pointed directly to 'deleted'
        reminder_rows = self.cursor.execute(
            "SELECT reminder_id FROM ReminderLinks WHERE bin_id = ?", (deleted_id,)
        ).fetchall()
        self.cursor.execute("DELETE FROM ReminderLinks WHERE bin_id = ?", (deleted_id,))
        self.commit()
        for (rid,) in reminder_rows:
            try:
                self.link_record_to_bin(rid, unlinked_id)
            except Exception:
                continue

        # Remove the 'deleted' bin entry itself.
        self.cursor.execute("DELETE FROM BinLinks WHERE bin_id = ?", (deleted_id,))
        self.cursor.execute("DELETE FROM Bins WHERE id = ?", (deleted_id,))
        self.commit()
        if hasattr(self, "bin_cache"):
            self.bin_cache.on_delete(deleted_id)

    def get_bin_id_by_name(self, name: str) -> int | None:
        """Return the id for `name` (case-insensitive) or None if missing."""
        nm = (name or "").strip()
        if not nm:
            return None
        self.cursor.execute(
            "SELECT id FROM Bins WHERE name = ? COLLATE NOCASE",
            (nm,),
        )
        row = self.cursor.fetchone()
        return int(row[0]) if row else None

    def is_system_bin(self, bin_id: int) -> bool:
        """True if bin_id refers to root or unlinked."""
        self.ensure_system_bins()
        protected = {
            self.root_bin_id,
            self.unlinked_bin_id,
        }
        return bin_id in protected

    def create_bin(self, name: str, parent_id: int | None) -> int:
        """
        Create a new bin under parent_id (or root if None). Raises on duplicates.
        """
        nm = (name or "").strip()
        if not nm:
            raise ValueError("Bin name must be non-empty.")

        if self.get_bin_id_by_name(nm) is not None:
            raise ValueError(f"A bin named {nm!r} already exists.")

        if parent_id is None:
            parent_id = self.ensure_root_exists()

        # Validate parent exists
        self.cursor.execute("SELECT 1 FROM Bins WHERE id = ?", (parent_id,))
        if self.cursor.fetchone() is None:
            raise ValueError(f"Parent bin #{parent_id} does not exist.")

        self.cursor.execute("INSERT INTO Bins (name) VALUES (?)", (nm,))
        new_id = int(self.cursor.lastrowid)
        self.cursor.execute(
            "INSERT OR REPLACE INTO BinLinks (bin_id, container_id) VALUES (?, ?)",
            (new_id, parent_id),
        )
        self.commit()

        if hasattr(self, "bin_cache"):
            self.bin_cache.on_create(new_id, nm, parent_id)

        return new_id

    def rename_bin(self, bin_id: int, new_name: str) -> None:
        """Rename a bin unless it is one of the protected system bins."""
        nm = (new_name or "").strip()
        if not nm:
            raise ValueError("Bin name must be non-empty.")

        self.cursor.execute("SELECT name FROM Bins WHERE id = ?", (bin_id,))
        row = self.cursor.fetchone()
        if not row:
            raise ValueError(f"Bin #{bin_id} does not exist.")

        if self.is_system_bin(bin_id):
            raise ValueError("System bins cannot be renamed.")

        current = row[0]
        canonical = self._canonical_root_for_name(current)
        if current.lower() == nm.lower():
            return  # no change

        self.cursor.execute(
            "SELECT 1 FROM Bins WHERE id != ? AND name = ? COLLATE NOCASE",
            (bin_id, nm),
        )
        if self.cursor.fetchone():
            raise ValueError(f"A bin named {nm!r} already exists.")

        self.cursor.execute("UPDATE Bins SET name = ? WHERE id = ?", (nm, bin_id))
        self.commit()

        if hasattr(self, "bin_cache"):
            self.bin_cache.on_rename(bin_id, nm)

        self._handle_standard_root_rename(canonical, current, nm)

    def move_bin_to_parent(self, bin_id: int, new_parent_id: int) -> None:
        """Re-parent a bin (by id) under a new parent id."""
        if bin_id == new_parent_id:
            raise ValueError("Cannot move a bin under itself.")

        self.cursor.execute("SELECT 1 FROM Bins WHERE id = ?", (bin_id,))
        if self.cursor.fetchone() is None:
            raise ValueError(f"Bin #{bin_id} does not exist.")

        self.cursor.execute("SELECT 1 FROM Bins WHERE id = ?", (new_parent_id,))
        if self.cursor.fetchone() is None:
            raise ValueError(f"Parent bin #{new_parent_id} does not exist.")

        if self.is_system_bin(bin_id):
            raise ValueError("System bins cannot be moved.")

        if self.is_descendant(bin_id, new_parent_id):
            raise ValueError("Cannot move a bin under its own descendant.")

        self.cursor.execute(
            "SELECT container_id FROM BinLinks WHERE bin_id = ?",
            (bin_id,),
        )
        row = self.cursor.fetchone()
        current_parent = row[0] if row else None
        if current_parent == new_parent_id:
            return

        self.cursor.execute("DELETE FROM BinLinks WHERE bin_id = ?", (bin_id,))
        self.cursor.execute(
            "INSERT OR REPLACE INTO BinLinks (bin_id, container_id) VALUES (?, ?)",
            (bin_id, new_parent_id),
        )
        self.commit()

        if hasattr(self, "bin_cache"):
            self.bin_cache.on_link(bin_id, new_parent_id)

    def mark_bin_deleted(self, bin_id: int) -> None:
        """Move a bin into the 'unlinked' container when it cannot be removed."""
        self.ensure_system_bins()
        if self.is_system_bin(bin_id):
            raise ValueError("System bins cannot be deleted.")
        unlinked_id = self.unlinked_bin_id
        if unlinked_id is None:
            raise ValueError("Unlinked bin is unavailable.")
        self.move_bin_to_parent(bin_id, unlinked_id)

    def _bin_is_empty(self, bin_id: int) -> bool:
        """True when the bin has no child bins and no reminders."""
        child = self.cursor.execute(
            "SELECT 1 FROM BinLinks WHERE container_id = ? LIMIT 1", (bin_id,)
        ).fetchone()
        if child:
            return False
        reminder = self.cursor.execute(
            "SELECT 1 FROM ReminderLinks WHERE bin_id = ? LIMIT 1", (bin_id,)
        ).fetchone()
        return reminder is None

    def delete_bin_if_empty(self, bin_id: int) -> bool:
        """
        Permanently delete `bin_id` if it has no children or reminders.

        Returns True when the bin was removed, False if it still has dependents
        and should instead be moved under the 'unlinked' container.
        """
        self.ensure_system_bins()
        row = self.cursor.execute(
            "SELECT 1 FROM Bins WHERE id = ?", (bin_id,)
        ).fetchone()
        if not row:
            raise ValueError(f"Bin #{bin_id} does not exist.")
        if self.is_system_bin(bin_id):
            raise ValueError("System bins cannot be deleted.")
        if not self._bin_is_empty(bin_id):
            return False

        self.cursor.execute("DELETE FROM BinLinks WHERE bin_id = ?", (bin_id,))
        self.cursor.execute("DELETE FROM Bins WHERE id = ?", (bin_id,))
        self.commit()

        if hasattr(self, "bin_cache"):
            self.bin_cache.on_delete(bin_id)
        return True

    def link_record_to_bin_path(self, record_id: int, path: str) -> None:
        """
        Ensure the bin path exists and link the record to its leaf bin.
        Example:
            record_id = 42, path = "personal/quotations"
            → ensures bins, links 42 → quotations
        """
        leaf_bin_id = self.ensure_bin_path(path)

        self.cursor.execute(
            """
            INSERT OR IGNORE INTO ReminderLinks (reminder_id, bin_id)
            VALUES (?, ?)
            """,
            (record_id, leaf_bin_id),
        )
        self.commit()

    # === Bin access helpers ===
    def get_bin_name(self, bin_id: int) -> str:
        """Return bin name by id."""
        self.cursor.execute("SELECT name FROM Bins WHERE id=?", (bin_id,))
        row = self.cursor.fetchone()
        return row[0] if row else f"[unknown #{bin_id}]"

    def get_parent_bin(self, bin_id: int) -> dict | None:
        """Return parent bin as {'id': ..., 'name': ...} or None if root."""
        self.cursor.execute(
            """
            SELECT b2.id, b2.name
            FROM BinLinks bl
            JOIN Bins b2 ON bl.container_id = b2.id
            WHERE bl.bin_id = ?
        """,
            (bin_id,),
        )
        row = self.cursor.fetchone()
        return {"id": row[0], "name": row[1]} if row else None

    def get_subbins(
        self, bin_id: int, custom_order: list[str] | None = None
    ) -> list[dict]:
        """
        Return bins contained in this bin, with counts of subbins/reminders.
        If custom_order is provided (list of child names in order), place those
        first in that sequence, then any others alphabetically by name.
        """
        self.cursor.execute(
            """
            SELECT b.id, b.name,
                (SELECT COUNT(*) FROM BinLinks sub WHERE sub.container_id = b.id) AS subbins,
                (SELECT COUNT(*) FROM ReminderLinks rl WHERE rl.bin_id = b.id) AS reminders
            FROM BinLinks bl
            JOIN Bins b ON bl.bin_id = b.id
            WHERE bl.container_id = ?
        """,
            (bin_id,),
        )
        results = [
            {"id": row[0], "name": row[1], "subbins": row[2], "reminders": row[3]}
            for row in self.cursor.fetchall()
        ]

        if custom_order:

            def sort_key(ch):
                try:
                    idx = custom_order.index(ch["name"])
                    return (0, idx)
                except ValueError:
                    return (1, ch["name"].lower())

            return sorted(results, key=sort_key)
        else:
            return sorted(results, key=lambda ch: ch["name"].lower())

    def get_reminders_in_bin(self, bin_id: int) -> list[dict]:
        """Return reminders linked to this bin."""
        self.cursor.execute(
            """
            SELECT r.id, r.subject, r.itemtype
            FROM ReminderLinks rl
            JOIN Records r ON rl.reminder_id = r.id
            WHERE rl.bin_id = ?
            ORDER BY r.subject COLLATE NOCASE
        """,
            (bin_id,),
        )
        return [
            {
                "id": row[0],
                # "subject": self.apply_flags(row[0], row[1]),
                "subject": row[1],
                "itemtype": row[2],
            }
            for row in self.cursor.fetchall()
        ]

    # ---------- New, non-colliding helpers ----------

    def ensure_root_exists(self) -> int:
        """Return id for 'root' (creating/anchoring it if needed)."""
        root_id, _ = self.ensure_system_bins()
        return root_id

    def ensure_root_children(self, names: list[str]) -> dict[str, int]:
        """
        Ensure lowercased children live directly under root; returns {name: id}.
        Idempotent and corrects mis-parented roots.
        """
        root_id = self.ensure_root_exists()
        out: dict[str, int] = {}
        for name in names:
            nm = (name or "").strip()
            if not nm:
                continue
            cid = self.ensure_bin_exists(nm)

            parent = self.get_parent_bin(cid)  # {'id','name'} or None
            if not parent or parent["name"].lower() != "root":
                self.move_bin(nm, "root")  # cycle-safe re-anchor

            self.cursor.execute(
                "INSERT OR IGNORE INTO BinLinks (bin_id, container_id) VALUES (?, ?)",
                (cid, root_id),
            )
            out[nm.lower()] = cid

        self.commit()
        return out

    def ensure_bin(
        self, name: str, parent_id: int | None = None, *, allow_reparent: bool = False
    ) -> int:
        nm = (name or "").strip()
        if not nm:
            raise ValueError("Bin name must be non-empty")
        bin_id = self.ensure_bin_exists(nm)
        if parent_id is None:
            parent_id = self.ensure_root_exists()

        parent = self.get_parent_bin(bin_id)
        if parent is None:
            # no parent yet — just insert
            self.cursor.execute(
                "INSERT OR IGNORE INTO BinLinks (bin_id, container_id) VALUES (?, ?)",
                (bin_id, parent_id),
            )
            self.commit()
        else:
            # already has a parent
            if allow_reparent and parent["id"] != parent_id:
                # figure out parent's name for move_bin(); cheapest is to query it
                desired_parent_name = self.get_bin_name(parent_id)
                self.move_bin(nm, desired_parent_name)

        return bin_id

    def link_record_to_bin(self, record_id: int, bin_id: int) -> None:
        self.cursor.execute(
            "INSERT OR IGNORE INTO ReminderLinks(reminder_id, bin_id) VALUES (?, ?)",
            (record_id, bin_id),
        )
        self.commit()

    def unlink_record_from_bins(
        self, record_id: int, *, only_tag_bins: bool | None = None
    ) -> None:
        """
        only_tag_bins=None -> unlink ALL links for record_id
        only_tag_bins=True -> unlink only tags:*
        only_tag_bins=False -> unlink only non-tags
        """
        if only_tag_bins is None:
            self.cursor.execute(
                "DELETE FROM ReminderLinks WHERE reminder_id=?", (record_id,)
            )
        elif only_tag_bins is True:
            self.cursor.execute(
                """
                DELETE FROM ReminderLinks
                WHERE reminder_id=?
                AND bin_id IN (SELECT id FROM Bins WHERE name LIKE 'tags:%')
                """,
                (record_id,),
            )
        else:
            self.cursor.execute(
                """
                DELETE FROM ReminderLinks
                WHERE reminder_id=?
                AND bin_id NOT IN (SELECT id FROM Bins WHERE name LIKE 'tags:%')
                """,
                (record_id,),
            )
        self.commit()

    # ---- tokens → links glue (single source of truth) ----

    def _tokens_list(self, tokens_obj) -> list[dict]:
        """Accept list or JSON string; normalize to list[dict]."""
        secret = getattr(self.env.config, "secret", "")
        if tokens_obj is None:
            return []
        if isinstance(tokens_obj, str):
            try:
                import json

                tokens = json.loads(tokens_obj) or []
            except Exception:
                tokens = []
        else:
            tokens = list(tokens_obj)
        return reveal_mask_tokens(tokens, secret)

    def relink_bins_for_record(
        self, record_id: int, item, *, default_parent_name: str = "unlinked"
    ) -> None:
        """
        Rebuild ReminderLinks for bins only.

        Behavior:
        - Always unlinks all existing bin links for this record.
        - Preferred input: item.bin_paths (list[list[str]]).
        - Fallback: simple '@b <leaf>' tokens via item.simple_bins (list[str]).
        - No tag handling — hashtags are now stored in Hashtags table separately.
        """

        # Ensure required default parent exists (usually "unlinked").
        defaults = self.ensure_root_children([default_parent_name])
        default_parent_id = defaults[default_parent_name]

        # -------- 1) Clear all existing bin links --------
        self.unlink_record_from_bins(record_id)

        # -------- 2) Preferred: hierarchical bin paths --------
        bin_paths: list[list[str]] = getattr(item, "bin_paths", []) or []
        if bin_paths:
            # BinPathProcessor handles creation, normalization, parent fixes, linking.
            _norm_tokens, _log, _leaf_ids = self.binproc.assign_record_many(
                record_id, bin_paths
            )
            return  # fully handled

        # -------- 3) Fallback: simple '@b <leaf>' tokens --------
        simple_bins: list[str] = getattr(item, "simple_bins", []) or []
        for name in simple_bins:
            nm = name.strip()
            if not nm:
                continue
            bid = self.ensure_bin(nm, parent_id=default_parent_id)
            self.link_record_to_bin(record_id, bid)

    ###VVV new for tagged bin treated
    def get_root_bin_id(self) -> int:
        # Reuse your existing, tested anchor
        return self.ensure_root_exists()

    def _make_crumb(self, bin_id: int | None):
        """Return [(id, name), ...] from root to current."""
        if bin_id is None:
            rid = self.ensure_root_exists()
            return [(rid, "root")]
        # climb using your get_parent_bin
        chain = []
        cur = bin_id
        while cur is not None:
            name = self.get_bin_name(cur)
            chain.append((cur, name))
            parent = self.get_parent_bin(cur)  # {'id','name'} or None
            cur = parent["id"] if parent else None
        return list(reversed(chain)) or [(self.ensure_root_exists(), "root")]

    def get_bin_summary(self, bin_id: int | None, *, filter_text: str | None = None):
        """
        Returns:
          children  -> [ChildBinRow]
          reminders -> [ReminderRow]
          crumb     -> [(id, name), ...]
        Uses ONLY DatabaseManager public methods you showed.
        """
        # 1) children (uses your counts + sort)
        raw_children = self.get_subbins(
            bin_id if bin_id is not None else self.get_root_bin_id()
        )
        # shape: {"id","name","subbins","reminders"}
        children = [
            ChildBinRow(
                bin_id=c["id"],
                name=c["name"],
                child_ct=c["subbins"],
                rem_ct=c["reminders"],
            )
            for c in raw_children
        ]

        # 2) reminders (linked via ReminderLinks)
        raw_reminders = self.get_reminders_in_bin(
            bin_id if bin_id is not None else self.get_root_bin_id()
        )
        # shape: {"id","subject","itemtype"}
        reminders = [
            ReminderRow(
                record_id=r["id"],
                subject=r["subject"],
                # keep optional fields absent; view handles it
            )
            for r in raw_reminders
        ]

        # 3) apply filter (controller-level; no new SQL)
        if filter_text:
            f = filter_text.casefold()
            children = [c for c in children if f in c.name.casefold()]
            reminders = [r for r in reminders if f in r.subject.casefold()]

        # 4) crumb
        crumb = self._make_crumb(
            bin_id if bin_id is not None else self.get_root_bin_id()
        )
        return children, reminders, crumb

    def get_reminder_details(self, record_id: int) -> str:
        # Minimal, safe detail using your existing schema
        row = self.cursor.execute(
            "SELECT subject, itemtype FROM Records WHERE id=?",
            (record_id,),
        ).fetchone()
        if not row:
            return "[b]Unknown reminder[/b]"
        subject, itemtype = row
        return f"[b]{subject}[/b]\n[dim]type:[/dim] {itemtype or '—'}"
