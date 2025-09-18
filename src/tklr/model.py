import os
import sqlite3
import json
from typing import Optional
from datetime import date, datetime, time, timedelta
from dateutil.rrule import rrulestr
from dateutil.parser import parse
from typing import List, Tuple
from rich import print
from tklr.tklr_env import TklrEnvironment
from dateutil import tz
from dateutil.tz import gettz

from .shared import (
    HRS_MINS,
    ALERT_COMMANDS,
    log_msg,
    format_datetime,
    datetime_from_timestamp,
    duration_in_words,
    datetime_in_words,
    fmt_local_compact,
    parse_local_compact,
    fmt_utc_z,
    parse_utc_z,
)

import re
from tklr.item import Item


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
    # aware in UTC -> 'YYYYMMDDTHHMMSSZ'
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
                jobs.append(
                    {
                        "job_id": j.get("i"),
                        "offset_str": (j.get("s") or "").strip(),
                        "extent_str": (j.get("e") or "").strip(),
                        "status": (j.get("status") or "").strip().lower(),
                        "display_subject": (j.get("display_subject") or "").strip(),
                    }
                )
    return jobs


# You already have this helper elsewhere; re-use it
# from tklr.common import td_str_to_seconds
# def _td_str_to_seconds(s: str) -> int:
#     # minimal fallback if you don’t want to import: supports d/h/m
#     s = (s or "").strip().lower()
#     if not s:
#         return 0
#     total = 0
#     num = ""
#     for ch in s:
#         if ch.isdigit():
#             num += ch
#         else:
#             if not num:
#                 continue
#             n = int(num)
#             if ch == "d":
#                 total += n * 86400
#             elif ch == "h":
#                 total += n * 3600
#             elif ch == "m":
#                 total += n * 60
#             # ignore unknown for brevity
#             num = ""
#     return total
#


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
        self.urgency = self.env.config.urgency

        if reset and os.path.exists(self.db_path):
            os.remove(self.db_path)

        self.conn = sqlite3.connect(self.db_path)
        self.cursor = self.conn.cursor()
        self.conn.create_function("REGEXP", 2, regexp)
        self.conn.create_function("REGEXP", 2, regexp)
        self.setup_database()
        self.compute_urgency = UrgencyComputer(env)

        yr, wk = datetime.now().isocalendar()[:2]
        log_msg(f"Generating weeks for 12 weeks starting from {yr} week number {wk}")
        self.extend_datetimes_for_weeks(yr, wk, 12)

        self.populate_tags()  # NEW: Populate Tags + RecordTags
        self.populate_alerts()  # Populate today's alerts
        log_msg("calling beginby")
        self.populate_beginby()
        self.populate_all_urgency()

        log_msg("back from beginby")

    def format_datetime(self, fmt_dt: str) -> str:
        return format_datetime(fmt_dt, self.ampm)

    def datetime_in_words(self, fmt_dt: str) -> str:
        return datetime_in_words(fmt_dt, self.ampm)

    def setup_database(self):
        """
        Create (if missing) all tables and indexes for tklr.

        Notes:
        - Pinned state is stored ONLY in the `Pinned` table.
        - Urgency has NO `pinned` column; compute it via LEFT JOIN Pinned when reading.
        - Timestamps are stored as UTC epoch seconds (INTEGER) unless noted otherwise.
        """
        # ---------------- Records ----------------
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS Records (
                id                INTEGER PRIMARY KEY AUTOINCREMENT,
                itemtype          TEXT,                         -- '*','~','^','%','?','+', 'x'
                subject           TEXT,
                description       TEXT,
                rruleset          TEXT,
                timezone          TEXT,
                extent            TEXT,
                alerts            TEXT,
                beginby           TEXT,
                context           TEXT,
                jobs              TEXT,
                tags              TEXT,
                priority          INTEGER CHECK (priority IN (1,2,3,4,5)),
                relative_tokens TEXT,                         -- JSON text
                processed         INTEGER,
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
                weights   TEXT                                  -- JSON of component weights, optional
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

        # ---------------- Tags & RecordTags ----------------
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS Tags (
                id   INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE
            );
        """)
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS RecordTags (
                record_id INTEGER NOT NULL,
                tag_id    INTEGER NOT NULL,
                FOREIGN KEY (record_id) REFERENCES Records(id) ON DELETE CASCADE,
                FOREIGN KEY (tag_id)    REFERENCES Tags(id)    ON DELETE CASCADE,
                PRIMARY KEY (record_id, tag_id)
            );
        """)

        # ---------------- Completions ----------------
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS Completions (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                record_id     INTEGER NOT NULL,
                job_id        INTEGER,          -- nullable; link to a specific job if any
                due           INTEGER,          -- epoch seconds (nullable for one-shots)
                completed     TEXT NOT NULL,    -- UTC datetime string, e.g. "20250828T211259Z"
                FOREIGN KEY (record_id) REFERENCES Records(id) ON DELETE CASCADE
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
                record_id     INTEGER NOT NULL,
                job_id        INTEGER,          -- nullable; link to specific job if any
                start_datetime TEXT NOT NULL,   -- 'YYYYMMDD' or 'YYYYMMDDTHHMMSS' (local-naive)
                end_datetime   TEXT,            -- NULL if instantaneous; same formats as start
                FOREIGN KEY (record_id) REFERENCES Records(id) ON DELETE CASCADE
            )
        """)

        # enforce uniqueness across (record_id, job_id, start, end)
        self.cursor.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_datetimes_unique
            ON DateTimes(
                record_id,
                COALESCE(job_id, -1),
                start_datetime,
                COALESCE(end_datetime, '')
            )
        """)

        # range query helper
        self.cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_datetimes_start
            ON DateTimes(start_datetime)
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

        # Alerts table: store local-naive datetimes as TEXT
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
            )
        """)

        # Prevent duplicates: one alert per (record, start, name, trigger)
        self.cursor.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_alerts_unique
            ON Alerts(record_id, start_datetime, alert_name, COALESCE(trigger_datetime,''))
        """)

        # Helpful for “what’s due now”
        self.cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_alerts_trigger
            ON Alerts(trigger_datetime)
        """)

        # ---------------- Beginby (days remaining notices) ----------------
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS Beginby (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                record_id     INTEGER NOT NULL,
                days_remaining INTEGER NOT NULL,
                FOREIGN KEY (record_id) REFERENCES Records(id) ON DELETE CASCADE
            );
        """)

        self.conn.commit()

    def populate_dependent_tables(self):
        """Populate all tables derived from current Records (Tags, DateTimes, Alerts, Beginby)."""
        yr, wk = datetime.now().isocalendar()[:2]
        log_msg(f"Generating weeks for 12 weeks starting from {yr} week number {wk}")
        self.extend_datetimes_for_weeks(yr, wk, 12)
        self.populate_tags()
        self.populate_alerts()
        self.populate_beginby()

    def add_item(self, item: Item):
        print(f"{item.itemtype = }, {item.subject}")
        try:
            timestamp = utc_now_string()
            self.cursor.execute(
                """
                INSERT INTO Records (
                    itemtype, subject, description, rruleset, timezone,
                    extent, alerts, beginby, context, jobs, priority, tags,
                    relative_tokens, processed, created, modified
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
                    item.beginby,
                    item.context,
                    json.dumps(item.jobs),
                    item.priority,
                    json.dumps(item.tags),
                    json.dumps(item.relative_tokens),
                    0,
                    timestamp,  # created
                    timestamp,  # modified (same on insert)
                ),
            )
            self.conn.commit()
        except Exception as e:
            print(f"Error adding {item}: {e}")

    def update_item(self, record_id: int, item: Item):
        """
        Update an existing record with new values from an Item object.
        Only non-None fields in the item will be updated.
        The 'modified' timestamp is always updated.
        """
        try:
            fields = []
            values = []

            # Map of field names to item attributes
            field_map = {
                "itemtype": item.itemtype,
                "subject": item.subject,
                "description": item.description,
                "rruleset": item.rruleset,
                "timezone": item.tz_str,
                "extent": item.extent,
                "alerts": json.dumps(item.alerts) if item.alerts is not None else None,
                "beginby": item.beginby,
                "context": item.context,
                "jobs": json.dumps(item.jobs) if item.jobs is not None else None,
                "tags": json.dumps(item.tags) if item.tags is not None else None,
                "relative_tokens": json.dumps(item.relative_tokens)
                if item.relative_tokens is not None
                else None,
                "processed": 0,  # reset processed
            }

            for field, value in field_map.items():
                if value is not None:
                    fields.append(f"{field} = ?")
                    values.append(value)

            # Always update 'modified' timestamp
            fields.append("modified = ?")
            values.append(utc_now_string())

            values.append(record_id)

            sql = f"UPDATE Records SET {', '.join(fields)} WHERE id = ?"
            self.cursor.execute(sql, values)
            self.conn.commit()
        except Exception as e:
            print(f"Error updating record {record_id}: {e}")

    def save_record(self, item: Item, record_id: int | None = None):
        """Insert or update a record and refresh associated tables."""
        timestamp = utc_now_string()

        if record_id is None:
            # Insert new record
            self.cursor.execute(
                """
                INSERT INTO Records (
                    itemtype, subject, description, rruleset, timezone,
                    extent, alerts, beginby, context, jobs, tags,
                    relative_tokens, processed, created, modified
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    item.itemtype,
                    item.subject,
                    item.description,
                    item.rruleset,
                    item.tz_str,
                    item.extent,
                    json.dumps(item.alerts),
                    item.beginby,
                    item.context,
                    json.dumps(item.jobs),
                    json.dumps(item.tags),
                    json.dumps(item.relative_tokens),
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
                    extent = ?, alerts = ?, beginby = ?, context = ?, jobs = ?, tags = ?,
                    relative_tokens = ?, modified = ?
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
                    item.beginby,
                    item.context,
                    json.dumps(item.jobs),
                    json.dumps(item.tags),
                    json.dumps(item.relative_tokens),
                    timestamp,
                    record_id,
                ),
            )

        self.conn.commit()

        # Refresh auxiliary tables
        self.update_tags_for_record(record_id)
        self.generate_datetimes_for_record(record_id)
        self.populate_alerts_for_record(record_id)
        if item.beginby:
            self.populate_beginby_for_record(record_id)
        if item.itemtype in ["~", "^"]:
            self.populate_urgency_from_record(record_id)

    def add_completion(
        self, record_id: int, job_id: int | None = None, due_ts: int | None = None
    ):
        completed_ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%MZ")
        self.cursor.execute(
            """
            INSERT INTO Completions (record_id, job_id, due, completed)
            VALUES (?, ?, ?, ?)
            """,
            (record_id, job_id, due, completed),
        )
        self.conn.commit()

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
            if job.get("job_id") == job_id:
                return job.get("display_subject") or None

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
        alert_command = ALERT_COMMANDS.get(command_name, "")
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

    def get_beginby_for_today(self):
        self.cursor.execute("""
            SELECT Records.itemtype, Records.subject, Beginby.days_remaining
            FROM Beginby
            JOIN Records ON Beginby.record_id = Records.id
            ORDER BY Beginby.days_remaining ASC
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

    def get_relative_tokens(self, record_id: int):
        """
        Retrieve the relative_tokens field from a record and return it as a list of dictionaries.
        Returns an empty list if the field is null, empty, or if the record is not found.
        """
        self.cursor.execute(
            "SELECT relative_tokens, rruleset, created, modified FROM Records WHERE id = ?",
            (record_id,),
        )
        return [
            (
                # " ".join([t["token"] for t in json.loads(relative_tokens)]),
                json.loads(relative_tokens),
                rruleset,
                created,
                modified,
            )
            for (
                relative_tokens,
                rruleset,
                created,
                modified,
            ) in self.cursor.fetchall()
        ]

    def populate_tags(self):
        """
        Populate Tags and RecordTags tables from the JSON 'tags' field in Records.
        This rebuilds the tag index from scratch.
        """
        self.cursor.execute("DELETE FROM RecordTags;")
        self.cursor.execute("DELETE FROM Tags;")
        self.conn.commit()

        self.cursor.execute(
            "SELECT id, tags FROM Records WHERE tags IS NOT NULL AND tags != ''"
        )
        records = self.cursor.fetchall()

        for record_id, tags_json in records:
            try:
                tags = json.loads(tags_json)
            except Exception as e:
                log_msg(f"⚠️ Failed to parse tags for record {record_id}: {e}")
                continue

            for tag in tags:
                # Insert into Tags table, avoid duplicates
                self.cursor.execute(
                    "INSERT OR IGNORE INTO Tags (name) VALUES (?)", (tag,)
                )
                self.cursor.execute("SELECT id FROM Tags WHERE name = ?", (tag,))
                tag_id = self.cursor.fetchone()[0]

                # Insert into RecordTags mapping table
                self.cursor.execute(
                    "INSERT INTO RecordTags (record_id, tag_id) VALUES (?, ?)",
                    (record_id, tag_id),
                )

        self.conn.commit()
        log_msg("✅ Tags and RecordTags tables populated.")

    def populate_alerts(self):
        """
        Populate the Alerts table for all records that have alerts defined.
        Alerts are only added if they are scheduled to trigger today.
        """
        # ✅ Step 1: Clear existing alerts
        self.cursor.execute("DELETE FROM Alerts;")
        self.conn.commit()

        # ✅ Step 2: Find all records with non-empty alerts
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
        now = round(datetime.now().timestamp())  # Current timestamp
        midnight = round(
            (datetime.now().replace(hour=23, minute=59, second=59)).timestamp()
        )  # Midnight timestamp

        # ✅ Step 3: Process alerts for each record
        for (
            record_id,
            record_name,
            record_description,
            record_location,
            alerts,
            start_datetime,
        ) in records:
            log_msg(f"processing {alerts = }")
            start_dt = datetime_from_timestamp(
                start_datetime
            )  # Convert timestamp to datetime
            today = date.today()

            # Convert alerts from JSON string to list
            alert_list = json.loads(alerts)

            for alert in alert_list:
                if ":" not in alert:
                    continue  # Ignore malformed alerts

                time_part, command_part = alert.split(":")
                timedelta_values = [
                    td_str_to_seconds(t.strip()) for t in time_part.split(",")
                ]
                log_msg(f"{timedelta_values = }")
                commands = [cmd.strip() for cmd in command_part.split(",")]

                for td in timedelta_values:
                    trigger_datetime = (
                        start_datetime - td
                    )  # When the alert should trigger

                    # ✅ Only insert alerts that will trigger before midnight and after now
                    if now <= trigger_datetime < midnight:
                        for alert_name in commands:
                            alert_command = self.create_alert(
                                alert_name,
                                td,
                                start_datetime,
                                record_id,
                                record_name,
                                record_description,
                                record_location,
                            )

                            if alert_command:  # ✅ Ensure it's valid before inserting
                                self.cursor.execute(
                                    "INSERT INTO Alerts (record_id, record_name, trigger_datetime, start_datetime, alert_name, alert_command) VALUES (?, ?, ?, ?, ?, ?)",
                                    (
                                        record_id,
                                        record_name,
                                        trigger_datetime,
                                        start_datetime,
                                        alert_name,
                                        alert_command,
                                    ),
                                )
        self.conn.commit()
        log_msg("✅ Alerts table updated with today's relevant alerts.")

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

        # You *can* clear today's alerts only, but a full clear is OK if you prefer.
        # Safer approach: clear only alerts that trigger today or later and will be re-generated.
        # If you *really* want a full reset, uncomment the next two lines and remove the targeted delete.
        # self.cursor.execute("DELETE FROM Alerts;")
        # self.conn.commit()

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

    def populate_alerts_for_record(self, record_id: int):
        """Regenerate alerts for a specific record, but only if any are scheduled for today."""

        # Clear old alerts for this record
        self.cursor.execute("DELETE FROM Alerts WHERE record_id = ?", (record_id,))

        # Look up the record’s alert data and start datetimes
        self.cursor.execute(
            """
            SELECT R.subject, R.description, R.context, R.alerts, D.start_datetime 
            FROM Records R
            JOIN DateTimes D ON R.id = D.record_id
            WHERE R.id = ? AND R.alerts IS NOT NULL AND R.alerts != ''
            """,
            (record_id,),
        )
        records = self.cursor.fetchall()
        if not records:
            log_msg(f"🔕 No alerts to populate for record {record_id}")
            return

        now = round(datetime.now().timestamp())
        midnight = round(
            datetime.now().replace(hour=23, minute=59, second=59).timestamp()
        )

        for subject, description, context, alerts_json, start_ts in records:
            # start_dt = datetime.fromtimestamp(start_ts)
            alerts = json.loads(alerts_json)
            for alert in alerts:
                if ":" not in alert:
                    continue
                time_part, command_part = alert.split(":")
                timedelta_values = [
                    td_to_seconds(t.strip()) for t in time_part.split(",")
                ]
                commands = [cmd.strip() for cmd in command_part.split(",")]

                for td in timedelta_values:
                    trigger = start_ts - td
                    if now <= trigger < midnight:
                        for name in commands:
                            alert_command = self.create_alert(
                                name,
                                td,
                                start_ts,
                                record_id,
                                subject,
                                description,
                                context,
                            )
                            if alert_command:
                                self.cursor.execute(
                                    "INSERT INTO Alerts (record_id, record_name, trigger_datetime, start_datetime, alert_name, alert_command) VALUES (?, ?, ?, ?, ?, ?)",
                                    (
                                        record_id,
                                        subject,
                                        trigger,
                                        start_ts,
                                        name,
                                        alert_command,
                                    ),
                                )

        self.conn.commit()
        log_msg(f"✅ Alerts updated for record {record_id}")

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
        # beg_year, beg_week = datetime.min.isocalendar()[:2]
        # log_msg(f"Generating weeks {beg_year}-{beg_week} to {end_year}-{end_week}")

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
            # while start_dt.date() != end_dt.date():
            #     day_end = datetime.combine(start_dt.date(), datetime.max.time())
            #     results.append((start_dt, day_end))
            #     start_dt = datetime.combine(
            #         start_dt.date() + timedelta(days=1), datetime.min.time()
            #     )
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
                anchor = datetime.min
                try:
                    cur = rule.after(anchor, inc=True)
                except TypeError:
                    anchor = datetime.min.replace(tzinfo=tz.UTC)
                    cur = rule.after(anchor, inc=True)
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
                parent_local = _to_local_naive(
                    parent_dt
                    if isinstance(parent_dt, datetime)
                    else datetime.combine(parent_dt, datetime.min.time())
                )
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

    def get_events_for_period(self, start_date: datetime, end_date: datetime):
        """
        Retrieve all events that occur or overlap within [start_date, end_date),
        ordered by start time.

        Returns rows as:
        (start_datetime, end_datetime, itemtype, resolved_subject, record_id, job_id)

        If dt.job_id is not NULL and Records.jobs contains a matching job with key "i",
        we use that job's "display_subject" (falling back to "~" or parent subject).
        """
        start_key = _to_key(start_date)
        end_key = _to_key(end_date)

        sql = """
        SELECT
            dt.start_datetime,
            dt.end_datetime,
            r.itemtype,
            r.subject,     -- parent subject
            r.id,
            dt.job_id,
            r.jobs         -- JSON array of job dicts (may be NULL)
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
        rows = self.cursor.fetchall()

        resolved = []
        for (
            start_dt,
            end_dt,
            itemtype,
            parent_subject,
            record_id,
            job_id,
            jobs_json,
        ) in rows:
            subject = parent_subject
            if job_id is not None and jobs_json:
                try:
                    jobs = json.loads(jobs_json)
                    for job in jobs:
                        # match job by its "i" field
                        if job.get("i") == job_id:
                            subject = (
                                job.get("display_subject")
                                or job.get("~")
                                or parent_subject
                            )
                            break
                except Exception:
                    # if JSON is malformed, just fall back to parent subject
                    pass

            resolved.append((start_dt, end_dt, itemtype, subject, record_id, job_id))

        return resolved

    def generate_datetimes_for_period(self, start_date: datetime, end_date: datetime):
        self.cursor.execute("SELECT id FROM Records")
        for (record_id,) in self.cursor.fetchall():
            self.generate_datetimes_for_record(
                record_id,
                window=(start_date, end_date),
                clear_existing=True,
            )

    def get_beginby_for_events(self):
        """
        Retrieve (record_id, days_remaining, subject) from Beginby joined with Records
        for events only (itemtype '*').

        Returns:
            List[Tuple[int, int, str]]: A list of (record_id, days_remaining, subject)
        """
        self.cursor.execute(
            """
            SELECT b.record_id, b.days_remaining, r.subject
            FROM Beginby b
            JOIN Records r ON b.record_id = r.id
            WHERE r.itemtype = '*'
            ORDER BY b.days_remaining
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
            # Process and split events across day boundaries
            # while start_dt.date() <= end_dt.date():
            #     # Compute the end time for the current day
            #     day_end = min(
            #         end_dt,
            #         datetime.combine(
            #             start_dt.date(), datetime.max.time()
            #         ),  # End of the current day
            #     )
            #
            #     # Group by ISO year, week, and weekday
            #     iso_year, iso_week, iso_weekday = start_dt.isocalendar()
            #     # grouped_events[iso_year][iso_week][iso_weekday].append((start_dt, day_end, event_type, name))
            #     grouped_events[iso_year][iso_week][iso_weekday].append(
            #         (start_dt, day_end)
            #     )
            #     # Move to the start of the next day
            #     start_dt = datetime.combine(
            #         start_dt.date() + timedelta(days=1), datetime.min.time()
            #     )

        return grouped_events

    def populate_beginby(self):
        """
        Populate the Beginby table for all records with valid beginby entries.
        This clears existing entries and recomputes them from current record data.
        """
        self.cursor.execute("DELETE FROM Beginby;")
        self.conn.commit()

        # Fetch both record_id and beginby value
        self.cursor.execute(
            "SELECT id, beginby FROM Records WHERE beginby IS NOT NULL AND beginby != ''"
        )
        for record_id, beginby in self.cursor.fetchall():
            self.populate_beginby_for_record(record_id)

        self.conn.commit()

    def populate_beginby_for_record(self, record_id: int):
        self.cursor.execute("SELECT beginby FROM Records WHERE id = ?", (record_id,))
        row = self.cursor.fetchone()
        if not row or not row[0]:
            return  # no beginby for this record
        beginby_str = row[0]

        self.cursor.execute(
            "SELECT start_datetime FROM DateTimes WHERE record_id = ?", (record_id,)
        )
        occurrences = self.cursor.fetchall()

        today = date.today()
        # today_start = datetime.combine(today, datetime.min.time())

        offset = td_str_to_td(beginby_str)

        for (start_ts,) in occurrences:
            scheduled_dt = datetime_from_timestamp(start_ts)
            beginby_dt = scheduled_dt - offset
            if beginby_dt.date() <= today < scheduled_dt.date():
                days_remaining = (scheduled_dt.date() - today).days
                self.cursor.execute(
                    "INSERT INTO Beginby (record_id, days_remaining) VALUES (?, ?)",
                    (record_id, days_remaining),
                )

        self.conn.commit()

    def get_last_instances(self) -> List[Tuple[int, str, str, str, datetime]]:
        """
        Retrieve the last instances of each record falling before today.

        Returns:
            List[Tuple[int, str, str, str, datetime]]: List of tuples containing
                record ID, name, description, type, and the last datetime.
        """
        today = int(datetime.now().timestamp())
        self.cursor.execute(
            """
            SELECT r.id, r.subject, r.description, r.itemtype, MAX(d.start_datetime) AS last_datetime
            FROM Records r
            JOIN DateTimes d ON r.id = d.record_id
            WHERE d.start_datetime < ?
            GROUP BY r.id
            ORDER BY last_datetime DESC
            """,
            (today,),
        )
        return self.cursor.fetchall()

    def get_last_instances(self) -> List[Tuple[int, str, str, str, str]]:
        """
        Retrieve the last instance *before now* for each record.

        Returns:
            List of tuples: (record_id, subject, description, itemtype, last_datetime_key)
            where last_datetime_key is 'YYYYMMDDTHHMMSS'.
        """
        today_key = _today_key()

        sql = """
        WITH norm AS (
        SELECT
            r.id            AS record_id,
            r.subject       AS subject,
            r.description   AS description,
            r.itemtype      AS itemtype,
            CASE
            WHEN LENGTH(d.start_datetime) = 8 THEN d.start_datetime || 'T000000'
            ELSE d.start_datetime
            END             AS start_norm
        FROM Records r
        JOIN DateTimes d ON r.id = d.record_id
        )
        SELECT
        n1.record_id,
        n1.subject,
        n1.description,
        n1.itemtype,
        MAX(n1.start_norm) AS last_datetime
        FROM norm n1
        WHERE n1.start_norm < ?
        GROUP BY n1.record_id
        ORDER BY last_datetime DESC
        """
        self.cursor.execute(sql, (today_key,))
        return self.cursor.fetchall()

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

    # def get_next_instances(self) -> List[Tuple[int, int | None, str, str, str, str]]:
    #     """
    #     Retrieve the next instance *at or after now* for each record.
    #
    #     Returns:
    #         List of tuples:
    #             (record_id, job_id, subject, description, itemtype, next_datetime)
    #     """
    #     today_key = _today_key()
    #
    #     sql = """
    #     WITH norm AS (
    #     SELECT
    #         r.id            AS record_id,
    #         r.subject       AS subject,
    #         r.description   AS description,
    #         r.itemtype      AS itemtype,
    #         CASE
    #         WHEN LENGTH(d.start_datetime) = 8 THEN d.start_datetime || 'T000000'
    #         ELSE d.start_datetime
    #         END             AS start_norm
    #     FROM Records r
    #     JOIN DateTimes d ON r.id = d.record_id
    #     )
    #     SELECT
    #     n1.record_id,
    #     n1.subject,
    #     n1.description,
    #     n1.itemtype,
    #     MIN(n1.start_norm) AS next_datetime
    #     FROM norm n1
    #     WHERE n1.start_norm >= ?
    #     GROUP BY n1.record_id
    #     ORDER BY next_datetime ASC
    #     """
    #     self.cursor.execute(sql, (today_key,))
    #     return self.cursor.fetchall()

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

    def find_records(
        self, regex: str
    ) -> List[Tuple[int, str, str, str, Optional[int], Optional[int]]]:
        """
        Find records whose name or description fields contain a match for the given regex,
        including their last and next instances if they exist.

        Args:
            regex (str): The regex pattern to match.

        Returns:
            List[Tuple[int, str, str, str, Optional[int], Optional[int]]]:
                List of tuples containing:
                    - record ID
                    - subject
                    - description
                    - itemtype
                    - last instance datetime (or None)
                    - next instance datetime (or None)
        """
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
            SELECT
                r.id,
                r.subject,
                r.description,
                r.itemtype,
                li.last_datetime,
                ni.next_datetime
            FROM Records r
            LEFT JOIN LastInstances li ON r.id = li.record_id
            LEFT JOIN NextInstances ni ON r.id = ni.record_id
            WHERE r.subject REGEXP ? OR r.description REGEXP ?
            """,
            (today, today, regex, regex),
        )
        return self.cursor.fetchall()

    # FIXME: should access record_id
    def update_tags_for_record(self, record_data):
        cur = self.conn.cursor()
        tags = record_data.pop("tags", [])
        record_data["relative_tokens"] = json.dumps(
            record_data.get("relative_tokens", [])
        )
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

    def populate_urgency_from_record(self, record: dict):
        record_id = record["id"]
        pinned = self.is_pinned(record_id)
        # log_msg(f"{record_id = }, {pinned = }, {record = }")
        now_seconds = utc_now_to_seconds()
        modified_seconds = dt_str_to_seconds(record["modified"])
        extent_seconds = td_str_to_seconds(record.get("extent", "0m"))
        # beginby_seconds will be 0 in the absence of beginby
        beginby_seconds = td_str_to_seconds(record.get("beginby", "0m"))
        rruleset = record.get("rruleset", "")
        tags = len(json.loads(record.get("tags", "[]")))
        jobs = json.loads(record.get("jobs", "[]"))
        subject = record["subject"]
        # priority_map = self.env.config.urgency.priority.model_dump()
        priority_level = record.get("priority", None)
        # priority = priority_map.get(priority_level, 0)
        description = True if record.get("description", "") else False

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
        if due_seconds and not beginby_seconds:
            # treat due_seconds as the default for a missing @b, i.e.,
            # make the default to hide a task with an @s due entry before due - interval
            beginby_seconds = due_seconds

        self.cursor.execute("DELETE FROM Urgency WHERE record_id = ?", (record_id,))

        # Handle jobs if present
        if jobs:
            for job in jobs:
                status = job.get("status", "")
                if status != "available":
                    continue
                job_id = job.get("i")
                subject = job.get("display_subject", subject)

                job_due = due_seconds
                if job_due:
                    b = td_str_to_seconds(job.get("b", "0m"))
                    s = td_str_to_seconds(job.get("s", "0m"))
                    if b:
                        hide = job_due - b > now_seconds
                        if hide:
                            continue
                    job_due -= s

                job_extent = td_str_to_seconds(job.get("e", "0m"))
                blocking = job.get("blocking")  # assume already computed elsewhere

                urgency, color, weights = self.compute_urgency.from_args_and_weights(
                    now=now_seconds,
                    modified=modified_seconds,
                    due=job_due,
                    extent=job_extent,
                    priority_level=priority_level,
                    blocking=blocking,
                    tags=tags,
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
                and beginby_seconds
                and due_seconds - beginby_seconds > now_seconds
            )
            if not hide:
                urgency, color, weights = self.compute_urgency.from_args_and_weights(
                    now=now_seconds,
                    modified=modified_seconds,
                    due=due_seconds,
                    extent=extent_seconds,
                    priority_level=priority_level,
                    tags=tags,
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
                        record.get("status", "next"),
                        json.dumps(weights),
                    ),
                )

        self.conn.commit()

    def populate_all_urgency(self):
        self.cursor.execute("DELETE FROM Urgency")
        tasks = self.get_all_tasks()
        for task in tasks:
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

    def get_jobs_for_record(self, record_id):
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM Records WHERE record_id = ?", (record_id,))
        return cur.fetchall()

    def get_tagged(self, tag):
        cur = self.conn.cursor()
        cur.execute(
            """
            SELECT Records.* FROM Records
            JOIN RecordTags ON Records.id = RecordTags.record_id
            JOIN Tags ON Tags.id = RecordTags.tag_id
            WHERE Tags.name = ?
        """,
            (tag,),
        )
        return cur.fetchall()

    def delete_record(self, record_id):
        cur = self.conn.cursor()
        cur.execute("DELETE FROM Records WHERE id = ?", (record_id,))
        self.conn.commit()

    def count_records(self):
        cur = self.conn.cursor()
        cur.execute("SELECT COUNT(*) FROM Records")
        return cur.fetchone()[0]
