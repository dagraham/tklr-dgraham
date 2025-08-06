from math import log
import os
import sqlite3
import json
from typing import Optional

from datetime import datetime, date, timedelta
from dateutil.rrule import rrulestr
from dateutil.parser import parse
from typing import List, Tuple
from rich import print
from tklr.tklr_env import TklrEnvironment


from .shared import (
    HRS_MINS,
    ALERT_COMMANDS,
    log_msg,
    format_datetime,
    duration_in_words,
    datetime_in_words,
)

import re
from tklr.item import Item

env = TklrEnvironment()
urgency = env.config.urgency


def regexp(pattern, value):
    try:
        return re.search(pattern, value) is not None
    except TypeError:
        return False  # Handle None values gracefully


def utc_now_string():
    """Return current UTC time as 'YYYYMMDDTHHMMSS'."""
    return datetime.utcnow().strftime("%Y%m%dT%H%M%S")


def utc_now_to_seconds():
    return round(datetime.utcnow().timestamp())


def is_date(obj):
    return isinstance(obj, date) and not isinstance(obj, datetime)


def parse_rdates(rule_str):
    """
    Extract RDATE lines and parse them into datetime objects.
    Supports multiple RDATEs separated by commas.
    """
    rdates = []
    for line in rule_str.splitlines():
        if line.startswith("RDATE:"):
            _, value = line.split(":", 1)
            for date_str in value.split(","):
                try:
                    # Try parsing with time first, fall back to date only
                    if "T" in date_str:
                        dt = datetime.strptime(date_str.strip(), "%Y%m%dT%H%M%S")
                    else:
                        dt = datetime.strptime(date_str.strip(), "%Y%m%d")
                    rdates.append(dt)
                except Exception as e:
                    log_msg(f"Invalid RDATE value: {date_str} — {e}")
    log_msg(f"{rdates = }")
    return rdates


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

    log_msg(f"{weeks = }, {days = }, {hours = }, {minutes = }, {seconds = }")

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
        return round(datetime.strptime(datetime_str, "%Y%m%dT%H%M%S").timestamp())

    except ValueError:
        return round(
            datetime.strptime(datetime_str, "%Y%m%dT000000").timestamp()
        )  # Allow date-only


def dt_to_dtstr(dt_obj: datetime) -> str:
    """Convert a datetime object to 'YYYYMMDDTHHMMSS' format."""
    if is_date:
        return dt_obj.strftime("%Y%m%d")
    return dt_obj.strftime("%Y%m%dT%H%M%S")


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


def compute_partitioned_urgency(weights: dict[str, float]) -> float:
    """
    Compute urgency from signed weights:
    - Positive weights push urgency up
    - Negative weights pull urgency down
    - Equal weights → urgency = 0

    Returns:
        urgency ∈ [-1.0, 1.0]
    """
    Wp = 1 + sum(w for w in weights.values() if w > 0)
    Wn = 1 + sum(abs(w) for w in weights.values() if w < 0)

    return (Wp - Wn) / (Wn + Wp)


def urgency_due(due_seconds: int, now_seconds: int) -> float:
    """
    This function calculates the urgency contribution for a task based
    on its due datetime relative to the current datetime and returns
    a float value between 0.0 when (now <= due - interval) and max when
    (now >= due).
    """
    due_max = urgency.due.max
    interval = urgency.due.interval
    if due_seconds and due_max and interval:
        interval_seconds = td_str_to_seconds(interval)
        log_msg(f"{due_max = }, {interval = }, {interval_seconds = }")
        return max(
            0.0,
            min(
                due_max,
                due_max * (1.0 - (now_seconds - due_seconds) / interval_seconds),
            ),
        )
    return 0.0


def urgency_pastdue(due_seconds: int, now_seconds: int) -> float:
    """
    This function calculates the urgency contribution for a task based
    on its due datetime relative to the current datetime and returns
    a float value between 0.0 when (now <= due) and max when
    (now >= due + interval).
    """

    pastdue_max = urgency.pastdue.max
    interval = urgency.pastdue.interval
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


def urgency_recent(modified_seconds: int, now_seconds: int) -> float:
    """
    This function calculates the urgency contribution for a task based
    on the current datetime relative to the (last) modified datetime. It
    represents a combination of a decreasing contribution from recent_max
    based on how recently it was modified and an increasing contribution
    from 0 based on how long ago it was modified. The maximum of the two
    is the age contribution.
    """
    recent_contribution = 0.0
    recent_interval = urgency.recent.interval
    recent_max = urgency.recent.max
    log_msg(f"{recent_interval = }")
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
    log_msg(f"returning {recent_contribution = }")
    return recent_contribution


def urgency_age(modified_seconds: int, now_seconds: int) -> float:
    """
    This function calculates the urgency contribution for a task based
    on the current datetime relative to the (last) modified datetime. It
    represents a combination of a decreasing contribution from recent_max
    based on how recently it was modified and an increasing contribution
    from 0 based on how long ago it was modified. The maximum of the two
    is the age contribution.
    """
    age_contribution = 0
    age_interval = urgency.age.interval
    age_max = urgency.age.max
    log_msg(f"{age_interval = }")
    if age_max and age_interval:
        age_interval_seconds = td_str_to_seconds(age_interval)
        age_contribution = max(
            0.0,
            min(
                age_max,
                age_max * (now_seconds - modified_seconds) / age_interval_seconds,
            ),
        )
    log_msg(f"returning {age_contribution = }")
    return age_contribution


def urgency_priority(priority_level: int) -> float:
    priority = urgency.priority.root.get(str(priority_level), 0.0)
    log_msg(f"returning {priority = }")
    return priority


def urgency_extent(extent_seconds: int) -> float:
    extent_max = 1.0
    extent_interval = td_str_to_seconds(urgency.extent.interval)
    extent = max(0.0, min(extent_max, extent_max * extent_seconds / extent_interval))
    log_msg(f"{extent_seconds = }, {extent = }")
    return extent


def urgency_blocking(num_blocking: int) -> float:
    blocking = 0.0
    if num_blocking:
        blocking_max = urgency.blocking.max
        blocking_count = urgency.blocking.count
        if blocking_max and blocking_count:
            blocking = max(
                0.0, min(blocking_max, blocking_max * num_blocking / blocking_count)
            )
    log_msg(f"returning {blocking = }")
    return blocking


def urgency_tags(num_tags: int) -> float:
    tags = 0.0
    tags_max = urgency.tags.max
    tags_count = urgency.tags.count
    if tags_max and tags_count:
        tags = max(0.0, min(tags_max, tags_max * num_tags / tags_count))
    log_msg(f"returning {tags = }")
    return tags


def urgency_description(has_description: bool) -> float:
    description_max = urgency.description.max
    description = 0.0
    if has_description and description_max:
        description = description_max
    log_msg(f"returning {description = }")
    return description


def urgency_project(has_project: bool) -> float:
    project_max = urgency.project.max
    project = 0.0
    if has_project and project_max:
        project = project_max
    log_msg(f"returning {project = }")
    return project


class DatabaseManager:
    def __init__(self, db_path: str, env: TklrEnvironment, reset: bool = False):
        self.db_path = db_path
        self.env = env
        self.urgency = self.env.config.urgency

        if reset and os.path.exists(self.db_path):
            os.remove(self.db_path)

        self.conn = sqlite3.connect(self.db_path)
        self.cursor = self.conn.cursor()
        self.conn.create_function("REGEXP", 2, regexp)
        self.setup_database()

        yr, wk = datetime.now().isocalendar()[:2]
        log_msg(f"Generating weeks for 12 weeks starting from {yr} week number {wk}")
        self.extend_datetimes_for_weeks(yr, wk, 12)

        self.populate_tags()  # NEW: Populate Tags + RecordTags
        self.populate_alerts()  # Populate today's alerts
        log_msg("calling beginby")
        self.populate_beginby()
        self.populate_all_urgency()

        log_msg("back from beginby")

    def setup_database(self):
        """
        Set up the SQLite database schema.
        # CHECK(itemtype IN ('*', '~', '^', '%', '?')) NOT NULL,
        """
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS Records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                itemtype TEXT,
                subject TEXT,
                description TEXT,
                rruleset TEXT,
                timezone TEXT,
                extent TEXT,
                alerts TEXT,
                beginby TEXT,
                context TEXT,
                jobs TEXT,
                tags TEXT,
                priority INTEGER CHECK (priority IN (1, 2, 3, 4, 5)),
                structured_tokens TEXT,
                processed INTEGER,
                created TEXT,     -- UTC timestamp in 'YYYYMMDDTHHMMSS'
                modified TEXT     -- UTC timestamp in 'YYYYMMDDTHHMMSS'
            );
        """)

        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS Urgency (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                record_id INTEGER NOT NULL,      -- Link to Records
                job_id TEXT,                     -- NULL for standalone tasks
                subject TEXT NOT NULL,           -- Task name or "job name → task"
                urgency FLOAT NOT NULL,          -- Final score
                status TEXT NOT NULL,            -- "next", "waiting", "scheduled", etc.
                weights TEXT,
                FOREIGN KEY (record_id) REFERENCES Records(id) ON DELETE CASCADE
            );
        """)

        self.cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_urgency ON Urgency(urgency)
        """)

        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS Pinned (
                record_id INTEGER PRIMARY KEY,
                FOREIGN KEY (record_id) REFERENCES Records(id) ON DELETE CASCADE
            )
        """)

        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS Tags (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE
            );
        """)

        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS RecordTags (
                record_id INTEGER NOT NULL,
                tag_id INTEGER NOT NULL,
                FOREIGN KEY (record_id) REFERENCES Records(id) ON DELETE CASCADE,
                FOREIGN KEY (tag_id) REFERENCES Tags(id) ON DELETE CASCADE,
                PRIMARY KEY (record_id, tag_id)
            );
        """)

        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS DateTimes (
            record_id INTEGER,
            start_datetime INTEGER,
            end_datetime INTEGER,
            FOREIGN KEY (record_id) REFERENCES Records (id)
        )
        """)

        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS GeneratedWeeks (
            start_year INTEGER,
            start_week INTEGER, 
            end_year INTEGER, 
            end_week INTEGER
        )
        """)

        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS Alerts (
                alert_id INTEGER PRIMARY KEY AUTOINCREMENT,
                record_id INTEGER NOT NULL,
                record_name TEXT NOT NULL,
                trigger_datetime INTEGER NOT NULL,
                start_datetime INTEGER NOT NULL,
                alert_name TEXT NOT NULL,
                alert_command TEXT NOT NULL,
                FOREIGN KEY (record_id) REFERENCES Records(id) ON DELETE CASCADE
            )
        """)
        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS Beginby (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                record_id INTEGER NOT NULL,
                days_remaining INTEGER NOT NULL,
                FOREIGN KEY (record_id) REFERENCES Records(id) ON DELETE CASCADE
            )
            """
        )
        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS Urgency (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                record_id INTEGER NOT NULL,
                job_id INTEGER,                   -- NULL for tasks without jobs
                urgency REAL NOT NULL,
                FOREIGN KEY (record_id) REFERENCES Records(id) ON DELETE CASCADE
            )
            """
        )
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
                    structured_tokens, processed, created, modified
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
                    json.dumps(item.structured_tokens),
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
                "structured_tokens": json.dumps(item.structured_tokens)
                if item.structured_tokens is not None
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
                    structured_tokens, processed, created, modified
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
                    json.dumps(item.structured_tokens),
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
                    structured_tokens = ?, modified = ?
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
                    json.dumps(item.structured_tokens),
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
        self.cursor.execute("SELECT 1 FROM Pinned WHERE record_id = ?", (record_id,))
        if self.cursor.fetchone():
            self.cursor.execute("DELETE FROM Pinned WHERE record_id = ?", (record_id,))
        else:
            self.cursor.execute(
                "INSERT INTO Pinned (record_id) VALUES (?)", (record_id,)
            )
        self.conn.commit()

    def get_pinned_record_ids(self) -> list[int]:
        self.cursor.execute("SELECT record_id FROM Pinned")
        return [row[0] for row in self.cursor.fetchall()]

    def is_pinned(self, record_id: int) -> bool:
        self.cursor.execute("SELECT 1 FROM Pinned WHERE record_id = ?", (record_id,))
        return self.cursor.fetchone() is not None

    def get_due_alerts(self):
        """Retrieve alerts that need execution within the next 6 seconds."""
        now = round(datetime.now().timestamp())

        self.cursor.execute(
            """
            SELECT alert_id, record_id, trigger_datetime, start_datetime, alert_name, alert_command
            FROM Alerts
            WHERE (trigger_datetime) BETWEEN ? AND ?
        """,
            (now - 2, now + 4),
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
            formatted_time = datetime.fromtimestamp(execution_time).strftime(
                "%Y-%m-%d %H:%M:%S"
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

    def get_structured_tokens(self, record_id: int):
        """
        Retrieve the structured_tokens field from a record and return it as a list of dictionaries.
        Returns an empty list if the field is null, empty, or if the record is not found.
        """
        self.cursor.execute(
            "SELECT structured_tokens, rruleset, created, modified FROM Records WHERE id = ?",
            (record_id,),
        )
        return [
            (
                # " ".join([t["token"] for t in json.loads(structured_tokens)]),
                json.loads(structured_tokens),
                rruleset,
                created,
                modified,
            )
            for (
                structured_tokens,
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
            start_dt = datetime.fromtimestamp(
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

    def generate_datetimes_for_period(self, start_date, end_date):
        """
        Populate the DateTimes table with datetimes for all records within the specified range.
        For finite recurrences (e.g., COUNT, UNTIL, or RDATE), generate all datetimes and mark as processed.

        Args:
            start_date (datetime): The start of the period.
            end_date (datetime): The end of the period.
        """
        # Fetch all records with their rrule strings, extents, and processed state
        log_msg(f"generating datetimes for {start_date = } through {end_date = }")
        self.cursor.execute("SELECT id, rruleset, extent, processed FROM Records")
        records = self.cursor.fetchall()

        for record_id, rruleset, extent, processed in records:
            # Replace any escaped newline characters in rruleset
            rule_str = rruleset.replace("\\N", "\n").replace("\\n", "\n")

            # Determine if the recurrence is finite
            is_finite = (
                "RRULE" not in rule_str or "COUNT=" in rule_str or "UNTIL=" in rule_str
            )

            # Skip already-processed finite recurrences
            if processed == 1 and is_finite:
                continue

            try:
                if is_finite:
                    # Handle RDATEs
                    rdate_occurrences = parse_rdates(rule_str)
                    for start_dt in rdate_occurrences:
                        end_dt = start_dt  # or compute duration from extent
                        self.cursor.execute(
                            """
                            INSERT OR IGNORE INTO DateTimes (record_id, start_datetime, end_datetime)
                            VALUES (?, ?, ?)
                            """,
                            (
                                record_id,
                                int(start_dt.timestamp()),
                                int(end_dt.timestamp()),
                            ),
                        )
                    # Handle RRULEs if present
                    if "RRULE" in rule_str:
                        full_occurrences = self.generate_datetimes(
                            rule_str, extent, datetime.min, datetime.max
                        )
                        for start_dt, end_dt in full_occurrences:
                            self.cursor.execute(
                                """
                                INSERT OR IGNORE INTO DateTimes (record_id, start_datetime, end_datetime)
                                VALUES (?, ?, ?)
                                """,
                                (
                                    record_id,
                                    int(start_dt.timestamp()),
                                    int(end_dt.timestamp()),
                                ),
                            )

                    self.cursor.execute(
                        "UPDATE Records SET processed = 1 WHERE id = ?", (record_id,)
                    )
                else:
                    # Generate occurrences for the specified range for infinite rules
                    occurrences = self.generate_datetimes(
                        # rule_str, extent, start_date, end_date
                        rule_str,
                        extent,
                        datetime.min,
                        end_date,
                    )
                    for start_dt, end_dt in occurrences:
                        self.cursor.execute(
                            """
                            INSERT OR IGNORE INTO DateTimes (record_id, start_datetime, end_datetime)
                            VALUES (?, ?, ?)
                            """,
                            (
                                record_id,
                                int(start_dt.timestamp()),
                                int(end_dt.timestamp()),
                            ),
                        )

            except Exception as e:
                log_msg(
                    f"Error processing\n{rruleset = }\n{rule_str = } for {record_id = }:\n  {e}"
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
        extent = td_str_to_td(extent) if isinstance(extent, str) else extent
        log_msg(
            f"Generating for {len(occurrences) = } between {start_date = } and {end_date = } with {extent = } for {rule_str = }."
        )

        # Create (start, end) pairs
        results = []
        for start_dt in occurrences:
            end_dt = start_dt + extent if extent else start_dt
            while start_dt.date() != end_dt.date():
                day_end = datetime.combine(start_dt.date(), datetime.max.time())
                results.append((start_dt, day_end))
                start_dt = datetime.combine(
                    start_dt.date() + timedelta(days=1), datetime.min.time()
                )
            results.append((start_dt, end_dt))

        return results

    def generate_datetimes_for_record(self, record_id: int):
        """
        Regenerate DateTimes entries for a single record.
        This mirrors logic from generate_datetimes_for_period but for one record.
        """

        # Fetch the record's recurrence data
        self.cursor.execute(
            "SELECT rruleset, extent FROM Records WHERE id = ?", (record_id,)
        )
        result = self.cursor.fetchone()
        if not result:
            log_msg(f"⚠️ No record found with id {record_id}")
            return

        rruleset, extent = result

        # Clean and normalize the rruleset string
        rule_str = rruleset.replace("\\N", "\n").replace("\\n", "\n")

        try:
            # Clear existing datetimes for this record
            self.cursor.execute(
                "DELETE FROM DateTimes WHERE record_id = ?", (record_id,)
            )

            # Determine if the recurrence is finite
            is_finite = (
                "RRULE" not in rule_str or "COUNT=" in rule_str or "UNTIL=" in rule_str
            )

            if is_finite:
                occurrences = self.generate_datetimes(
                    rule_str, extent, datetime.min, datetime.max
                )
                self.cursor.execute(
                    "UPDATE Records SET processed = 1 WHERE id = ?", (record_id,)
                )
            else:
                # For infinite recurrences, only generate a 12-week forward window
                start = datetime.now()
                end = start + timedelta(weeks=12)
                occurrences = self.generate_datetimes(rule_str, extent, start, end)

            for start_dt, end_dt in occurrences:
                self.cursor.execute(
                    """
                    INSERT OR IGNORE INTO DateTimes (record_id, start_datetime, end_datetime)
                    VALUES (?, ?, ?)
                    """,
                    (
                        record_id,
                        int(start_dt.timestamp()),
                        int(end_dt.timestamp()),
                    ),
                )

            self.conn.commit()

        except Exception as e:
            log_msg(
                f"⚠️ Error processing rruleset {rule_str} for record_id {record_id}: {e}"
            )

    def get_events_for_period(self, start_date, end_date):
        """
        Retrieve all events that occur or overlap within a specified period,
        including the itemtype, subject, and ID of each event, ordered by start time.

        Args:
            start_date (datetime): The start of the period.
            end_date (datetime): The end of the period.

        Returns:
            List[Tuple[int, int, str, str, int]]: A list of tuples containing
            start and end timestamps, event type, event name, and event ID.
        """
        self.cursor.execute(
            """
        SELECT dt.start_datetime, dt.end_datetime, r.itemtype, r.subject, r.id 
        FROM DateTimes dt
        JOIN Records r ON dt.record_id = r.id
        WHERE dt.start_datetime < ? AND dt.end_datetime >= ?
        ORDER BY dt.start_datetime
        """,
            (end_date.timestamp(), start_date.timestamp()),
        )
        return self.cursor.fetchall()

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
        Retrieve urgency records with record_id, job_id, subject, and urgency,
        ordered by urgency descending.

        Returns:
            List[Tuple[int, int, str, float]]: (record_id, job_id, subject, urgency)
        """
        self.cursor.execute(
            """
            SELECT record_id, job_id, subject, urgency
            FROM Urgency
            ORDER BY urgency DESC
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

        for start_ts, end_ts, itemtype, subject, id in events:
            start_dt = (
                datetime.utcfromtimestamp(start_ts)
                .replace(tzinfo=gettz("UTC"))
                .astimezone()
                .replace(tzinfo=None)
            )
            end_dt = (
                datetime.utcfromtimestamp(end_ts)
                .replace(tzinfo=gettz("UTC"))
                .astimezone()
                .replace(tzinfo=None)
            )

            # Process and split events across day boundaries
            while start_dt.date() <= end_dt.date():
                # Compute the end time for the current day
                # zero_duration = start_dt == end_dt
                # if zero_duration:
                #     log_msg(f"zero_duration item: {name}")
                day_end = min(
                    end_dt,
                    datetime.combine(
                        start_dt.date(), datetime.max.time()
                    ),  # End of the current day
                )

                # Group by ISO year, week, and weekday
                iso_year, iso_week, iso_weekday = start_dt.isocalendar()
                # grouped_events[iso_year][iso_week][iso_weekday].append((start_dt, day_end, event_type, name))
                grouped_events[iso_year][iso_week][iso_weekday].append(
                    (start_dt, day_end)
                )
                # if zero_duration:
                #     log_msg(f"zero_duration appended: {name} {start_dt} {day_end}")

                # Move to the start of the next day
                start_dt = datetime.combine(
                    start_dt.date() + timedelta(days=1), datetime.min.time()
                )

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
            scheduled_dt = datetime.fromtimestamp(start_ts)
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

    def get_next_instances(self) -> List[Tuple[int, str, str, str, datetime]]:
        """
        Retrieve the next instances of each record falling on or after today.

        Returns:
            List[Tuple[int, str, str, str, datetime]]: List of tuples containing
                record ID, name, description, type, and the next datetime.
        """
        today = int(datetime.now().timestamp())
        self.cursor.execute(
            """
            SELECT r.id, r.subject, r.description, r.itemtype, MIN(d.start_datetime) AS next_datetime
            FROM Records r
            JOIN DateTimes d ON r.id = d.record_id
            WHERE d.start_datetime >= ?
            GROUP BY r.id
            ORDER BY next_datetime ASC
            """,
            (today,),
        )
        return self.cursor.fetchall()

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
        record_data["structured_tokens"] = json.dumps(
            record_data.get("structured_tokens", [])
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
        log_msg(f"{record = }")
        record_id = record["id"]
        now_seconds = utc_now_to_seconds()
        modified_seconds = dt_str_to_seconds(record["modified"])
        extent_seconds = td_str_to_seconds(record.get("extent", "0m"))
        # beginby_seconds will be 0 in the absence of beginby
        beginby_seconds = td_str_to_seconds(record.get("beginby", "0m"))
        rruleset = record.get("rruleset", "")
        tags = len(json.loads(record.get("tags", "[]")))
        jobs = json.loads(record.get("jobs", "[]"))
        subject = record["subject"]
        priority_map = self.env.config.urgency.priority.model_dump()
        priority_level = record.get("priority", None)
        priority = priority_map.get(priority_level, 0)
        pinned = self.is_pinned(record_id)

        # Try to parse due from first RDATE in rruleset
        due_seconds = None
        if rruleset.startswith("RDATE:"):
            due_str = rruleset.split(":", 1)[1].split(",")[0]
            try:
                if "T" in due_str:
                    dt = datetime.strptime(due_str.strip(), "%Y%m%dT%H%M%SZ")
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

        # weights and calculator
        # weights = self.env.config.urgency.weights.model_dump()

        # def compute_urgency(**kwargs):
        #     weights = {
        #         "due": urgency_due(kwargs.get("due"), kwargs["now"]),
        #         "pastdue": urgency_pastdue(kwargs.get("due"), kwargs["now"]),
        #         "age": urgency_age(kwargs["modified"], kwargs["now"]),
        #         "recent": urgency_recent(kwargs["modified"], kwargs["now"]),
        #         "priority": urgency_priority(kwargs.get("priority_level")),
        #         "extent": urgency_extent(kwargs["extent"]),
        #         "blocking": urgency_blocking(kwargs.get("blocking", 0.0)),
        #         "tags": urgency_tags(kwargs.get("tags", 0)),
        #         "description": 1.0 if bool("description") else 0.0,
        #         "project": 1.0 if bool(jobs) else 0.0,
        #     }
        #     urgency = compute_partitioned_urgency(weights)
        #     log_msg(f"{subject}:\n  {weights = }\n  returning {urgency = }")
        #     return urgency

        def compute_urgency(**kwargs):
            weights = {
                "due": urgency_due(kwargs.get("due"), kwargs["now"]),
                "pastdue": urgency_pastdue(kwargs.get("due"), kwargs["now"]),
                "age": urgency_age(kwargs["modified"], kwargs["now"]),
                "recent": urgency_recent(kwargs["modified"], kwargs["now"]),
                "priority": urgency_priority(kwargs.get("priority_level")),
                "extent": urgency_extent(kwargs["extent"]),
                "blocking": urgency_blocking(kwargs.get("blocking", 0.0)),
                "tags": urgency_tags(kwargs.get("tags", 0)),
                "description": 1.0 if bool("description") else 0.0,
                "project": 1.0 if bool(jobs) else 0.0,
            }
            urgency = compute_partitioned_urgency(weights)
            log_msg(f"{subject}:\n  {weights = }\n  returning {urgency = }")
            return urgency, weights

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
                    b = td_str_to_seconds(job.get("b"))
                    s = td_str_to_seconds(job.get("s", "0m"))
                    if b:
                        hide = job_due - b > now_seconds
                        if hide:
                            continue
                    job_due -= s

                job_extent = td_str_to_seconds(job.get("e", "0m"))
                blocking = job.get("blocking")  # assume already computed elsewhere

                urgency, weights = (
                    (1.0, {})
                    if pinned
                    else compute_urgency(
                        now=now_seconds,
                        modified=modified_seconds,
                        due=job_due,
                        extent=job_extent,
                        priority_level=priority_level,
                        blocking=blocking,
                        tags=tags,
                    )
                )

                # self.cursor.execute(
                #     """
                #     INSERT INTO Urgency (record_id, job_id, subject, urgency, status)
                #     VALUES (?, ?, ?, ?, ?)
                #     """,
                #     (record_id, job_id, subject, urgency, status),
                # )
                self.cursor.execute(
                    """
                    INSERT INTO Urgency (record_id, job_id, subject, urgency, status, weights)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (record_id, job_id, subject, urgency, status, json.dumps(weights)),
                )

        else:
            hide = (
                due_seconds
                and beginby_seconds
                and due_seconds - beginby_seconds > now_seconds
            )
            if not hide:
                urgency, weights = compute_urgency(
                    now=now_seconds,
                    modified=modified_seconds,
                    due=due_seconds,
                    extent=extent_seconds,
                    priority_level=priority_level,
                    tags=tags,
                )
                # self.cursor.execute(
                #     """
                #     INSERT INTO Urgency (record_id, job_id, subject, urgency, status)
                #     VALUES (?, ?, ?, ?, ?)
                #     """,
                #     (record_id, None, subject, urgency, record.get("status", "next")),
                # )
                self.cursor.execute(
                    """
                    INSERT INTO Urgency (record_id, job_id, subject, urgency, status, weights)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        record_id,
                        None,
                        subject,
                        urgency,
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
        cur.execute("SELECT * FROM Jobs WHERE record_id = ?", (record_id,))
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
