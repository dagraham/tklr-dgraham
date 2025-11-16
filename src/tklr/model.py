from __future__ import annotations
import os
import sqlite3
import json
from typing import Optional
from datetime import date, datetime, time, timedelta
from dateutil.rrule import rrulestr
from dateutil.parser import parse

from typing import List, Tuple, Optional, Dict, Any, Set, Iterable
from rich import print
from tklr.tklr_env import TklrEnvironment
from dateutil import tz
from dateutil.tz import gettz
import math
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
    format_datetime,
    datetime_from_timestamp,
    duration_in_words,
    datetime_in_words,
    fmt_local_compact,
    parse_local_compact,
    fmt_utc_z,
    parse_utc_z,
    get_anchor,
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
    "seedbed",
    "tags",
    "unlinked",
}

BIN_PATHS = [
    ["books", "library"],
    ["movies", "library"],
    ["series", "library"],
    ["poetry", "library"],
    ["quotations", "library"],
    ["seed", "seedbed"],
    ["germination", "seedbed"],
    ["seedling", "seedbed"],
    ["growing", "seedbed"],
    ["flowering", "seedbed"],
]


def regexp(pattern, value):
    try:
        return re.search(pattern, value) is not None
    except TypeError:
        return False  # Handle None values gracefully


def utc_now_string():
    """Return current UTC time as 'YYYYMMDDTHHMMSS'."""
    return datetime.utcnow().strftime("%Y%m%dT%H%MZ")


def utc_now_to_seconds():
    return round(datetime.utcnow().timestamp())


def is_date(obj):
    return isinstance(obj, date) and not isinstance(obj, datetime)


DATE_FMT = "%Y%m%d"
DT_FMT = "%Y%m%dT%H%M"


def _fmt_date(d: date) -> str:
    return d.strftime(DATE_FMT)


def _fmt_naive(dt: datetime) -> str:
    return dt.strftime(DT_FMT)


def _fmt_utc(dt_aware_utc: datetime) -> str:
    return dt_aware_utc.astimezone(tz.UTC).strftime(DT_FMT) + "Z"


def _to_local_naive(dt: datetime) -> datetime:
    """
    Convert aware -> local-naive; leave naive unchanged.
    Assumes dt is datetime (not date).
    """
    if dt.tzinfo is not None:
        dt = dt.astimezone(tz.tzlocal()).replace(tzinfo=None)
    return dt


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
    Split a local-naive span into same-day segments.
    Inclusive start, inclusive end per segment.
    """
    if end_local <= start_local:
        return [(start_local, end_local)]

    segs: list[tuple[datetime, datetime]] = []
    cur_start = start_local

    while cur_start.date() < end_local.date():
        day_end = datetime.combine(cur_start.date(), time(23, 59, 59))
        segs.append((cur_start, day_end))
        next_day_start = datetime.combine(
            cur_start.date() + timedelta(days=1), time(0, 0, 0)
        )
        cur_start = next_day_start

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
    """Convert a datetime string like '20250601T090000' into a datetime object."""
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
                log_msg(f"json jobs: {j = }")
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

    # --- handle end rules ---
    end = parse(end_str) if end_str else None

    if end is None and (start.hour != 0 or start.minute != 0):
        # zero-extent event: contributes nothing
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
    while True:
        yw = yw_key(cur)
        if yw not in weeks:
            weeks[yw] = np.zeros(slots_per_week, dtype=np.uint8)

        day_index = cur.weekday()  # Mon=0
        base = day_index * (1 + slots_per_day)

        if end is None:
            # all-day flag only
            weeks[yw][base] = 1
        else:
            day_start = datetime.combine(cur.date(), datetime.min.time())
            day_end = datetime.combine(cur.date(), datetime.max.time())
            s = max(start, day_start)
            e = min(end, day_end)

            s_idx = (s.hour * 60 + s.minute) // slot_minutes
            e_idx = (e.hour * 60 + e.minute) // slot_minutes
            log_msg(f"{s_idx = }, {e_idx = }, {e_idx - s_idx = } ")
            weeks[yw][base + 1 + s_idx : base + 1 + e_idx + 1] = 1
            busy_count += np.count_nonzero(weeks[yw])

        if end is None or cur.date() >= end.date():
            break
        cur += timedelta(days=1)
    log_msg(f"{start_str = }, {end_str = }, {busy_count = }")
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
        log_msg(f"{self.name_to_binpath() = }")

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

        urgency = (Wp - Wn) / (2 + Wn + Wp)
        # log_msg(f"{Wp = }, {Wn = }, {Wp - Wn = }, {Wp + Wn = }, {urgency = }")
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
    def __init__(self, db_path: str, env: TklrEnvironment, reset: bool = False):
        self.db_path = db_path
        self.env = env
        self.AMPM = env.config.ui.ampm
        self.ALERTS = env.config.alerts
        self.urgency = self.env.config.urgency

        if reset and os.path.exists(self.db_path):
            os.remove(self.db_path)

        self.conn = sqlite3.connect(self.db_path)
        self.cursor = self.conn.cursor()
        self.conn.create_function("REGEXP", 2, regexp)
        self.conn.create_function("REGEXP", 2, regexp)
        self.setup_database()
        self.compute_urgency = UrgencyComputer(env)
        self.binproc = BinPathProcessor(
            self,
            BinPathConfig(
                allow_reparent=True,  # or False if you want conservative behavior
                standard_roots=BIN_ROOTS,  # <— same set, all lowercase
            ),
        )
        self.bin_cache = BinCache(self.conn)
        log_msg(f"{self.bin_cache.name_to_binpath() = }")
        self.populate_dependent_tables()

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
                itemtype          TEXT,                         -- '*','~','^','%','?','+','x'
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
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS DateTimes (
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

        self.conn.commit()

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

        self.conn.commit()

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
        self.conn.commit()

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

    def populate_dependent_tables(self):
        """Populate all tables derived from current Records (Tags, DateTimes, Alerts, notice)."""
        log_msg("populate dependent tables")
        yr, wk = datetime.now().isocalendar()[:2]
        log_msg(f"Generating weeks for 12 weeks starting from {yr} week number {wk}")
        self.extend_datetimes_for_weeks(yr, wk, 12)
        # self.populate_tags()
        log_msg("calling populate_alerts")
        self.populate_alerts()
        log_msg("calling populate_notice")
        self.populate_notice()
        log_msg("calling populate_busy_from_datetimes")
        self.populate_busy_from_datetimes()  # 👈 new step: source layer
        self.rebuild_busyweeks_from_source()  # 👈 add this line
        self.populate_all_urgency()
        self.ensure_system_bins()

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
            self.conn.commit()

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
            self.conn.commit()
            self.relink_bins_for_record(record_id, item)  # ← add this

        except Exception as e:
            print(f"Error updating record {record_id}: {e}")
            raise

    # def save_record(self, item: Item, record_id: int | None = None):
    #     """Insert or update a record and refresh associated tables."""
    #     timestamp = utc_now_string()
    #
    #     if record_id is None:
    #         # Insert new record
    #         self.cursor.execute(
    #             """
    #             INSERT INTO Records (
    #                 itemtype, subject, description, rruleset, timezone,
    #                 extent, alerts, notice, context, jobs,
    #                 tokens, created, modified
    #             ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    #             """,
    #             (
    #                 item.itemtype,
    #                 item.subject,
    #                 item.description,
    #                 item.rruleset,
    #                 item.tz_str,
    #                 item.extent,
    #                 json.dumps(item.alerts),
    #                 item.notice,
    #                 item.context,
    #                 json.dumps(item.jobs),
    #                 json.dumps(item.tokens),
    #                 timestamp,
    #                 timestamp,
    #             ),
    #         )
    #         record_id = self.cursor.lastrowid
    #     else:
    #         # Update existing record
    #         self.cursor.execute(
    #             """
    #             UPDATE Records
    #             SET itemtype = ?, subject = ?, description = ?, rruleset = ?, timezone = ?,
    #                 extent = ?, alerts = ?, notice = ?, context = ?, jobs = ?,
    #                 tokens = ?, modified = ?
    #             WHERE id = ?
    #             """,
    #             (
    #                 item.itemtype,
    #                 item.subject,
    #                 item.description,
    #                 item.rruleset,
    #                 item.tz_str,
    #                 item.extent,
    #                 json.dumps(item.alerts),
    #                 item.notice,
    #                 item.context,
    #                 json.dumps(item.jobs),
    #                 json.dumps(item.tokens),
    #                 timestamp,
    #                 record_id,
    #             ),
    #         )
    #
    #     self.conn.commit()
    #
    #     # Refresh auxiliary tables
    #     self.generate_datetimes_for_record(record_id)
    #     self.populate_alerts_for_record(record_id)
    #     if item.notice:
    #         self.populate_notice_for_record(record_id)
    #     if item.itemtype in ["~", "^"]:
    #         self.populate_urgency_from_record(record_id)

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

        self.conn.commit()

        # Dependent tables
        self.relink_bins_for_record(record_id, item)
        self.generate_datetimes_for_record(record_id)
        self.populate_alerts_for_record(record_id)
        if item.notice:
            self.populate_notice_for_record(record_id)
        if item.itemtype in ["~", "^"]:
            self.populate_urgency_from_record(record_id)

        # Hashtags: based on subject + description
        self._update_hashtags_for_record(record_id, item.subject, item.description)

        self.conn.commit()
        return record_id

    # def get_record_tags(self, record_id: int) -> list[str]:
    #     self.cursor.execute(
    #         "SELECT COALESCE(tags,'[]') FROM Records WHERE id=?", (record_id,)
    #     )
    #     row = self.cursor.fetchone()
    #     try:
    #         return self._normalize_tags(json.loads(row[0])) if row and row[0] else []
    #     except Exception:
    #         return []
    #
    # def find_records_with_any_tags(self, tags: list[str]) -> list[tuple]:
    #     want = set(self._normalize_tags(tags))
    #     self.cursor.execute("SELECT id, subject, COALESCE(tags,'[]') FROM Records")
    #     out = []
    #     for rid, subj, tags_json in self.cursor.fetchall():
    #         try:
    #             have = (
    #                 set(self._normalize_tags(json.loads(tags_json)))
    #                 if tags_json
    #                 else set()
    #             )
    #         except Exception:
    #             have = set()
    #         if want & have:
    #             out.append((rid, subj))
    #     return out

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
        self.conn.commit()

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
                parse_utc(due) if due else None,
                parse_utc(comp),
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
        self.conn.commit()

    def toggle_pinned(self, record_id: int) -> None:
        self.cursor.execute("SELECT 1 FROM Pinned WHERE record_id=?", (record_id,))
        if self.cursor.fetchone():
            self.cursor.execute("DELETE FROM Pinned WHERE record_id=?", (record_id,))
        else:
            self.cursor.execute(
                "INSERT INTO Pinned(record_id) VALUES (?)", (record_id,)
            )
        self.conn.commit()

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
        log_msg(f"{alerts = }")

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
            log_msg(f"{job = }")
            if job.get("job_id") == job_id:
                return job.get("display_subject") or None

        return None

    def get_job_dict(self, record_id: int, job_id: int | None) -> dict | None:
        """
        Return the full job dictionary for the given record_id + job_id pair.
        Returns None if not found.

        """
        log_msg(f"getting job_dict for {record_id = }, {job_id = }")
        if job_id is None:
            return None

        self.cursor.execute("SELECT jobs FROM Records WHERE id=?", (record_id,))
        row = self.cursor.fetchone()
        if not row or not row[0]:
            return None

        jobs = _parse_jobs_json(row[0])
        log_msg(f"{jobs = }")
        for job in jobs:
            if job.get("job_id") == job_id:
                return job  # Return the full dictionary

        log_msg(f"returning None for {record_id = }, {job_id = }")
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
        self.conn.commit()

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
            alert_command = "{name} {when} at {start}"
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
        log_msg(f"formatted alert {alert_command = }")
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

        log_msg(f"formatted alert: {formatted!r}")
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
        return [
            (
                # " ".join([t["token"] for t in json.loads(tokens)]),
                json.loads(tokens),
                rruleset,
                created,
                modified,
            )
            for (
                tokens,
                rruleset,
                created,
                modified,
            ) in self.cursor.fetchall()
        ]

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
        self.conn.commit()

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

        self.conn.commit()
        print("✅ Alerts table updated with today's relevant alerts.")

    # def populate_alerts_for_record(self, record_id: int):
    #     """Regenerate alerts for a specific record, but only if any are scheduled for today."""
    #
    #     # Clear old alerts for this record
    #     self.cursor.execute("DELETE FROM Alerts WHERE record_id = ?", (record_id,))
    #
    #     # Look up the record’s alert data and start datetimes
    #     self.cursor.execute(
    #         """
    #         SELECT R.subject, R.description, R.context, R.alerts, D.start_datetime
    #         FROM Records R
    #         JOIN DateTimes D ON R.id = D.record_id
    #         WHERE R.id = ? AND R.alerts IS NOT NULL AND R.alerts != ''
    #         """,
    #         (record_id,),
    #     )
    #     records = self.cursor.fetchall()
    #     if not records:
    #         log_msg(f"🔕 No alerts to populate for record {record_id}")
    #         return
    #
    #     now = round(datetime.now().timestamp())
    #     midnight = round(
    #         datetime.now().replace(hour=23, minute=59, second=59).timestamp()
    #     )
    #
    #     for subject, description, context, alerts_json, start_ts in records:
    #         # start_dt = datetime.fromtimestamp(start_ts)
    #         alerts = json.loads(alerts_json)
    #         for alert in alerts:
    #             if ":" not in alert:
    #                 continue
    #             time_part, command_part = alert.split(":")
    #             timedelta_values = [
    #                 td_str_to_seconds(t.strip()) for t in time_part.split(",")
    #             ]
    #             commands = [cmd.strip() for cmd in command_part.split(",")]
    #
    #             for td in timedelta_values:
    #                 trigger = start_ts - td
    #                 if now <= trigger < midnight:
    #                     for name in commands:
    #                         alert_command = self.create_alert(
    #                             name,
    #                             td,
    #                             start_ts,
    #                             record_id,
    #                             subject,
    #                             description,
    #                             context,
    #                         )
    #                         if alert_command:
    #                             self.cursor.execute(
    #                                 "INSERT INTO Alerts (record_id, record_name, trigger_datetime, start_datetime, alert_name, alert_command) VALUES (?, ?, ?, ?, ?, ?)",
    #                                 (
    #                                     record_id,
    #                                     subject,
    #                                     trigger,
    #                                     start_ts,
    #                                     name,
    #                                     alert_command,
    #                                 ),
    #                             )
    #
    #     self.conn.commit()
    #     log_msg(f"✅ Alerts updated for record {record_id}")

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
        self.conn.commit()

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
            log_msg(f"🔕 No alerts to populate for record {record_id}")
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

        self.conn.commit()
        log_msg(f"✅ Alerts updated for record {record_id}")

    def get_generated_weeks_range(self) -> tuple[int, int, int, int] | None:
        row = self.cursor.execute(
            "SELECT start_year, start_week, end_year, end_week FROM GeneratedWeeks"
        ).fetchone()
        return tuple(row) if row else None

    @staticmethod
    def _week_key(year: int, week: int) -> tuple[int, int]:
        return (year, week)

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
        log_msg(f"generating datetimes for {first_day = } {last_day = }")
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

        self.conn.commit()

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

        log_msg(
            f"getting datetimes for {rule_str} between {start_date = } and {end_date = }"
        )
        rule = rrulestr(rule_str, dtstart=start_date)
        occurrences = list(rule.between(start_date, end_date, inc=True))
        print(f"{rule_str = }\n{occurrences = }")
        extent = td_str_to_td(extent) if isinstance(extent, str) else extent
        log_msg(
            f"Generating for {len(occurrences) = } between {start_date = } and {end_date = } with {extent = } for {rule_str = }."
        )

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
        rule_str = (rruleset or "").replace("\\N", "\n").replace("\\n", "\n")

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
        is_aware = "Z" in rule_str

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
                anchor = datetime.min
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
            log_msg(f"{record_id = } has jobs")
            for parent_dt in _iter_parent_occurrences():
                parent_local = _to_local_naive(
                    parent_dt
                    if isinstance(parent_dt, datetime)
                    else datetime.combine(parent_dt, datetime.min.time())
                )
                for j in jobs:
                    log_msg(f"job: {j = }")
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
                                log_msg(
                                    f"inserting job datetimes {s_txt = }, {e_txt = } for {record_id = }, {job_id = }"
                                )
                                self.cursor.execute(
                                    "INSERT OR IGNORE INTO DateTimes (record_id, job_id, start_datetime, end_datetime) VALUES (?, ?, ?, ?)",
                                    (record_id, job_id, s_txt, e_txt),
                                )
                                log_msg("success")
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
                    start_local = _to_local_naive(cur)
                else:
                    start_local = (
                        cur  # date; treated as local-naive midnight by _fmt_naive
                    )

                if extent_sec_record:
                    end_local = (
                        start_local + timedelta(seconds=extent_sec_record)
                        if isinstance(start_local, datetime)
                        else datetime.combine(start_local, datetime.min.time())
                        + timedelta(seconds=extent_sec_record)
                    )
                    try:
                        for seg_start, seg_end in _split_span_local_days(
                            start_local, end_local
                        ):
                            s_txt = _fmt_naive(seg_start)
                            e_txt = (
                                None if seg_end == seg_start else _fmt_naive(seg_end)
                            )
                            self.cursor.execute(
                                "INSERT OR IGNORE INTO DateTimes (record_id, job_id, start_datetime, end_datetime) VALUES (?, NULL, ?, ?)",
                                (record_id, s_txt, e_txt),
                            )
                    except NameError:
                        self.cursor.execute(
                            "INSERT OR IGNORE INTO DateTimes (record_id, job_id, start_datetime, end_datetime) VALUES (?, NULL, ?, ?)",
                            (record_id, _fmt_naive(start_local), _fmt_naive(end_local)),
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
        self.conn.commit()

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
            dt.start_datetime,
            dt.end_datetime,
            r.itemtype,
            r.subject,
            r.id,
            dt.job_id
        FROM DateTimes dt
        JOIN Records r ON dt.record_id = r.id
        WHERE
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
        (record_id, job_id, subject, urgency, color, status, weights, pinned_int)
        """
        self.cursor.execute(
            """
            SELECT
            u.record_id,
            u.job_id,
            u.subject,
            u.urgency,
            u.color,
            u.status,
            u.weights,
            CASE WHEN p.record_id IS NULL THEN 0 ELSE 1 END AS pinned
            FROM Urgency AS u
            LEFT JOIN Pinned AS p ON p.record_id = u.record_id
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
        from collections import defaultdict
        from datetime import datetime, timedelta
        from dateutil.tz import gettz

        # Retrieve all events for the specified period
        events = self.get_events_for_period(start_date, end_date)
        # Group events by ISO year, week, and weekday
        grouped_events = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))

        for start_ts, end_ts, itemtype, subject, id, job_id in events:
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
        self.conn.commit()

        # Fetch both record_id and notice value
        self.cursor.execute(
            "SELECT id, notice FROM Records WHERE notice IS NOT NULL AND notice != ''"
        )
        for record_id, notice in self.cursor.fetchall():
            self.populate_notice_for_record(record_id)

        self.conn.commit()

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

        self.conn.commit()

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

        self.conn.commit()
        print(f"✅ BusyWeeksFromDateTimes populated ({total_inserted} week-records).")

    def get_last_instances(
        self,
    ) -> List[Tuple[int, int | None, str, str, str, str]]:
        """
        Retrieve the last instances of each record/job falling before today.

        Returns:
            List of tuples:
                (record_id, job_id, subject, description, itemtype, last_datetime)
        """
        today = datetime.now().strftime("%Y%m%dT%H%M")
        self.cursor.execute(
            """
            SELECT
                r.id,
                d.job_id,
                r.subject,
                r.description,
                r.itemtype,
                MAX(d.start_datetime) AS last_datetime
            FROM Records r
            JOIN DateTimes d ON r.id = d.record_id
            WHERE d.start_datetime < ?
            GROUP BY r.id, d.job_id
            ORDER BY last_datetime DESC
            """,
            (today,),
        )
        return self.cursor.fetchall()

    def get_next_instances(
        self,
    ) -> List[Tuple[int, int | None, str, str, str, str]]:
        """
        Retrieve the next instances of each record/job falling on or after today.

        Returns:
            List of tuples:
                (record_id, job_id, subject, description, itemtype, last_datetime)
        """
        today = datetime.now().strftime("%Y%m%dT%H%M")
        self.cursor.execute(
            """
            SELECT
                r.id,
                d.job_id,
                r.subject,
                r.description,
                r.itemtype,
                MIN(d.start_datetime) AS next_datetime
            FROM Records r
            JOIN DateTimes d ON r.id = d.record_id
            WHERE d.start_datetime >= ?
            GROUP BY r.id, d.job_id
            ORDER BY next_datetime ASC
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
        self, record_id: int, job_id: int | None = None
    ) -> list[str]:
        """
        Return up to 2 upcoming start datetimes (as compact local-naive strings)
        for the given record (and optional job), sorted ascending.
        """
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

        sql += " ORDER BY start_datetime ASC LIMIT 2"

        self.cursor.execute(sql, params)
        return [row[0] for row in self.cursor.fetchall()]

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
        self.conn.commit()
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
        log_msg(f"{record_id = }, {record = }")

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

        if itemtype not in ["^", "~"]:
            log_msg(f"skipping urgency for {record = }")
            return

        now_seconds = utc_now_to_seconds()
        pinned = self.is_pinned(record_id)

        # Try to parse due from first RDATE in rruleset
        due_seconds = None
        if rruleset.startswith("RDATE:"):
            due_str = rruleset.split(":", 1)[1].split(",")[0]
            try:
                if "T" in due_str:
                    dt = datetime.strptime(due_str.strip(), "%Y%m%dT%H%MZ")
                else:
                    dt = datetime.strptime(due_str.strip(), "%Y%m%d")
                due_seconds = round(dt.timestamp())
            except Exception as e:
                log_msg(f"Invalid RDATE value: {due_str}\n{e}")
        if due_seconds and not notice_seconds:
            # treat due_seconds as the default for a missing @b, i.e.,
            # make the default to hide a task with an @s due entry before due - interval
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

                job_due = due_seconds
                if job_due:
                    b = td_str_to_seconds(job.get("b", "0m"))
                    s = td_str_to_seconds(job.get("s", "0m"))
                    if b:
                        hide = job_due - b > now_seconds
                        if hide:
                            continue
                    job_due += s

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

        self.conn.commit()

    def populate_all_urgency(self):
        self.cursor.execute("DELETE FROM Urgency")
        tasks = self.get_all_tasks()
        for task in tasks:
            # log_msg(f"adding to urgency: {task['itemtype'] = }, {task = }")
            self.populate_urgency_from_record(task)
        self.conn.commit()

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
        self.conn.commit()

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
        log_msg(f"get_record_as_dictionary called with {record = } ({type(record)=})")
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
        self.conn.commit()

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

        print(f"Aggregating {len(weeks)} week(s)...")

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

        self.conn.commit()
        print("✅ BusyWeeks aggregation complete.")

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
        Move a bin under a new parent bin.

        Example:
            move_bin("whatever", "journal")

        Ensures both bins exist, removes any previous parent link,
        and inserts a new (bin_id → new_parent_id) link.
        Prevents cycles and self-parenting.
        """
        try:
            # Ensure the root/unlinked bins exist first
            root_id, unlinked_id = self.ensure_system_bins()

            # Resolve both bin IDs (creating them if needed)
            bin_id = self.ensure_bin_exists(bin_name)
            new_parent_id = self.ensure_bin_exists(new_parent_name)

            # ⚡ Efficiency check: prevent self-parenting before DB recursion
            if bin_id == new_parent_id:
                raise ValueError(f"Cannot move {bin_name!r} under itself.")

            # 🌀 Recursive acyclicity check
            if self.is_descendant(bin_id, new_parent_id):
                raise ValueError(
                    f"Cannot move {bin_name!r} under {new_parent_name!r}: "
                    "would create a cycle."
                )

            # Remove any existing parent link(s)
            self.cursor.execute("DELETE FROM BinLinks WHERE bin_id = ?", (bin_id,))

            # Insert the new parent link
            self.cursor.execute(
                """
                INSERT OR REPLACE INTO BinLinks (bin_id, container_id)
                VALUES (?, ?)
                """,
                (bin_id, new_parent_id),
            )

            self.conn.commit()
            print(f"[move_bin] Moved {bin_name!r} → {new_parent_name!r}")
            return True

        except Exception as e:
            print(f"[move_bin] Error moving {bin_name!r} → {new_parent_name!r}: {e}")
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
        self.conn.commit()
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

        self.conn.commit()
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

        self.conn.commit()
        return parent_id

    def ensure_system_bins(self) -> tuple[int, int]:
        root_id = self.ensure_bin_exists("root")
        unlinked_id = self.ensure_bin_exists("unlinked")

        # link unlinked → root (if not already)
        self.cursor.execute(
            "INSERT OR IGNORE INTO BinLinks (bin_id, container_id) VALUES (?, ?)",
            (unlinked_id, root_id),
        )
        # 👇 cache: reflect current effective parent
        if hasattr(self, "bin_cache"):
            self.bin_cache.on_link(unlinked_id, root_id)

        # Ensure root has no parent (NULL)
        self.cursor.execute(
            "INSERT OR IGNORE INTO BinLinks (bin_id, container_id) VALUES (?, NULL)",
            (root_id,),
        )
        # 👇 cache: reflect root’s parent = None
        if hasattr(self, "bin_cache"):
            self.bin_cache.on_link(root_id, None)

        self.conn.commit()
        return root_id, unlinked_id

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
        self.conn.commit()

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

    # def get_subbins(self, bin_id: int) -> list[dict]:
    #     """Return bins contained in this bin, with counts of subbins/reminders."""
    #     self.cursor.execute(
    #         """
    #         SELECT b.id, b.name,
    #             (SELECT COUNT(*) FROM BinLinks sub WHERE sub.container_id = b.id) AS subbins,
    #             (SELECT COUNT(*) FROM ReminderLinks rl WHERE rl.bin_id = b.id) AS reminders
    #         FROM BinLinks bl
    #         JOIN Bins b ON bl.bin_id = b.id
    #         WHERE bl.container_id = ?
    #         ORDER BY b.name COLLATE NOCASE
    #     """,
    #         (bin_id,),
    #     )
    #     return [
    #         {"id": row[0], "name": row[1], "subbins": row[2], "reminders": row[3]}
    #         for row in self.cursor.fetchall()
    #     ]

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

    # def apply_flags(self, record_id: int, subject: str) -> str:
    #     """
    #     Append any flags from Records.flags (e.g. 𝕒𝕘𝕠𝕣) to the given subject.
    #     """
    #     row = self.get_record_as_dictionary(record_id)
    #     if not row:
    #         return subject
    #
    #     flags = f" {row.get('flags')}" or ""
    #     log_msg(f"{row = }, {flags = }")
    #     if not flags:
    #         return subject
    #
    #     return subject + flags

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
            nm = (name or "").strip().lower()  # ← roots are canonical lowercase
            cid = self.ensure_bin_exists(nm)

            parent = self.get_parent_bin(cid)  # {'id','name'} or None
            if not parent or parent["name"].lower() != "root":
                self.move_bin(nm, "root")  # cycle-safe re-anchor

            self.cursor.execute(
                "INSERT OR IGNORE INTO BinLinks (bin_id, container_id) VALUES (?, ?)",
                (cid, root_id),
            )
            out[nm] = cid

        self.conn.commit()
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
            self.conn.commit()
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
        self.conn.commit()

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
        self.conn.commit()

    # ---- tokens → links glue (single source of truth) ----

    def _tokens_list(self, tokens_obj) -> list[dict]:
        """Accept list or JSON string; normalize to list[dict]."""
        if tokens_obj is None:
            return []
        if isinstance(tokens_obj, str):
            try:
                import json

                return json.loads(tokens_obj) or []
            except Exception:
                return []
        return list(tokens_obj)

    # def _extract_tag_and_bin_names(self, item) -> tuple[list[str], list[str]]:
    #     """
    #     Read '@t <name>' and '@b <name>' from item.tokens.
    #     tokens are dicts; we rely on keys: t='@', k in {'t','b'}, token='@t blue'
    #     """
    #     tokens = self._tokens_list(getattr(item, "tokens", []))
    #     tags: list[str] = []
    #     bins: list[str] = []
    #     for t in tokens:
    #         if t.get("t") != "@":
    #             continue
    #         k = t.get("k")
    #         raw = t.get("token", "")
    #         value = ""
    #         if isinstance(raw, str) and " " in raw:
    #             value = raw.split(" ", 1)[1].strip()
    #         if not value:
    #             continue
    #         if k == "t":
    #             tags.append(value)
    #         elif k == "b":
    #             bins.append(value)
    #     return tags, bins

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
