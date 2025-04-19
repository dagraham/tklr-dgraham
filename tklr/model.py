import os
import sqlite3
from typing import Optional

# from bisect import bisect_left, bisect_right
# from collections import defaultdict
from datetime import datetime, date, timedelta
from dateutil.rrule import rrulestr
from typing import List, Tuple
from prompt_toolkit.styles.named_colors import NAMED_COLORS

from .shared import (
    HRS_MINS,
    ALERT_COMMANDS,
    log_msg,
    format_datetime,
    duration_in_words,
    datetime_in_words,
)

import re


def regexp(pattern, value):
    try:
        return re.search(pattern, value) is not None
    except TypeError:
        return False  # Handle None values gracefully


# Constants for busy bar rendering
# BUSY_COLOR = NAMED_COLORS["YellowGreen"]
# CONF_COLOR = NAMED_COLORS["Tomato"]
# FRAME_COLOR = NAMED_COLORS["DimGrey"]
# SLOT_HOURS = [0, 4, 8, 12, 16, 20, 24]
# SLOT_MINUTES = [x * 60 for x in SLOT_HOURS]
# BUSY = "■"  # U+25A0 this will be busy_bar busy and conflict character
# FREE = "□"  # U+25A1 this will be busy_bar free character
# ADAY = "━"  # U+2501 for all day events ━

DEFAULT_LOG_FILE = "log_msg.md"


class DatabaseManager:
    def __init__(self, db_path, reset=False):
        """
        Initialize the database manager and optionally replace the database.

        Args:
            db_path (str): Path to the SQLite database file.
            replace (bool): Whether to replace the existing database.
        """
        self.db_path = db_path
        if reset and os.path.exists(db_path):
            os.remove(db_path)
        self.conn = sqlite3.connect(self.db_path)
        self.cursor = self.conn.cursor()
        self.conn.create_function("REGEXP", 2, regexp)
        self.setup_database()
        yr, wk = datetime.now().isocalendar()[:2]
        log_msg(f"Generating weeks for 12 weeks starting from {yr} week number {wk}")
        self.extend_datetimes_for_weeks(yr, wk, 12)
        self.populate_alerts()

    def setup_database(self):
        """
        Set up the SQLite database schema.
        """
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS Records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT CHECK(type IN ('*', '-', '~', '^')) NOT NULL,
            name TEXT NOT NULL,
            details TEXT,
            rrulestr TEXT,
            extent INTEGER,
            alerts TEXT,
            location TEXT,
            processed INTEGER DEFAULT 0
        )
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
        self.conn.commit()

    def add_record(self, record_type, name, details, rrstr, extent, alerts, location):
        """
        Add a new record to the database.
        """
        # log_msg(
        #     f"Adding record: {record_type = } {name = } {details = } {rrstr = } {extent = } {alerts = } {location = }"
        # )
        self.cursor.execute(
            "INSERT INTO Records (type, name, details, rrulestr, extent, alerts, location) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (record_type, name, details, rrstr, extent, alerts, location),
        )
        new_record_id = self.cursor.lastrowid  # Retrieve the new record ID
        self.conn.commit()
        log_msg(f"Added record {name} with ID {new_record_id}.")
        return new_record_id  # Return the ID to the caller

        # For future reference, this is how you can add a new column to an existing table:
        # # ✅ Check if 'alerts' column exists, and add it if missing
        # self.cursor.execute("PRAGMA table_info(Records);")
        # existing_columns = {row[1] for row in self.cursor.fetchall()}  # Column names
        #
        # if "alerts" not in existing_columns:
        #     self.cursor.execute(
        #         "ALTER TABLE Records ADD COLUMN alerts TEXT DEFAULT '';"
        #     )
        #     self.conn.commit()

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
        record_details,
        record_location,
    ):
        alert_command = ALERT_COMMANDS.get(command_name, "")
        if not alert_command:
            log_msg(f"❌ Alert command not found for '{command_name}'")
            return None  # Explicitly return None if command is missing

        # today = date.today()
        # today_fmt = today.strftime("%Y-%m-%d")
        name = record_name
        details = record_details
        location = record_location

        if timedelta > 0:
            when = f"in {duration_in_words(timedelta)}"
        elif timedelta == 0:
            when = "now"
        else:
            when = f"{duration_in_words(-timedelta)} ago"

        start = format_datetime(start_datetime, HRS_MINS)
        # time_fmt = start_time if start_date == today_fmt else start_date
        time_fmt = datetime_in_words(start_datetime)

        alert_command = alert_command.format(
            name=name,
            when=when,
            time=time_fmt,
            details=details,
            location=location,
            start=start,
        )
        log_msg(f"formatted alert {alert_command = }")
        return alert_command

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
            SELECT R.id, R.name, R.details, R.location, R.alerts, D.start_datetime 
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
            record_details,
            record_location,
            alerts_str,
            start_datetime,
        ) in records:
            start_dt = datetime.fromtimestamp(
                start_datetime
            )  # Convert timestamp to datetime
            today = date.today()

            for alert in alerts_str.split(";"):
                if ":" not in alert:
                    continue  # Ignore malformed alerts

                time_part, command_part = alert.split(":")
                timedelta_values = [int(t.strip()) for t in time_part.split(",")]
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
                                record_details,
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
        beg_year, beg_week = datetime.min.isocalendar()[:2]
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
        self.cursor.execute("SELECT id, rrulestr, extent, processed FROM Records")
        records = self.cursor.fetchall()

        for record_id, rule_str, extent, processed in records:
            # Replace any escaped newline characters in rrulestr
            rule_str = rule_str.replace("\\N", "\n").replace("\\n", "\n")

            # Determine if the recurrence is finite
            is_finite = (
                "RRULE" not in rule_str or "COUNT=" in rule_str or "UNTIL=" in rule_str
            )

            # Skip already-processed finite recurrences
            if processed == 1 and is_finite:
                continue

            try:
                if is_finite:
                    # Generate all occurrences for the entire recurrence period
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
                    # Mark finite rules (RRULE or RDATE) as processed after all occurrences are inserted
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
                    f"Error processing rrulestr for record_id {record_id}: {rule_str}\n{e}"
                )

        self.conn.commit()

    def generate_datetimes(self, rule_str, extent, start_date, end_date):
        """
        Generate occurrences for a given rrulestr within the specified date range.

        Args:
            rule_str (str): The rrule string defining the recurrence rule.
            extent (int): The duration of each occurrence in minutes.
            start_date (datetime): The start of the range.
            end_date (datetime): The end of the range.

        Returns:
            List[Tuple[datetime, datetime]]: A list of (start_dt, end_dt) tuples.
        """
        from dateutil.rrule import rrulestr

        rule = rrulestr(rule_str, dtstart=start_date)
        occurrences = list(rule.between(start_date, end_date, inc=True))

        # Create (start, end) pairs
        results = []
        for start_dt in occurrences:
            end_dt = start_dt + timedelta(minutes=extent) if extent else start_dt
            while start_dt.date() != end_dt.date():
                day_end = datetime.combine(start_dt.date(), datetime.max.time())
                results.append((start_dt, day_end))
                start_dt = datetime.combine(
                    start_dt.date() + timedelta(days=1), datetime.min.time()
                )
            results.append((start_dt, end_dt))

        return results

    def get_events_for_period(self, start_date, end_date):
        """
        Retrieve all events that occur or overlap within a specified period,
        including the type, name, and ID of each event, ordered by start time.

        Args:
            start_date (datetime): The start of the period.
            end_date (datetime): The end of the period.

        Returns:
            List[Tuple[int, int, str, str, int]]: A list of tuples containing
            start and end timestamps, event type, event name, and event ID.
        """
        self.cursor.execute(
            """
        SELECT dt.start_datetime, dt.end_datetime, r.type, r.name, r.id 
        FROM DateTimes dt
        JOIN Records r ON dt.record_id = r.id
        WHERE dt.start_datetime < ? AND dt.end_datetime >= ?
        ORDER BY dt.start_datetime
        """,
            (end_date.timestamp(), start_date.timestamp()),
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

        for start_ts, end_ts, event_type, name, id in events:
            # Convert timestamps to localized datetime objects
            # if start_ts == end_ts:
            #     log_msg(f"Event {name} has zero duration")
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
                zero_duration = start_dt == end_dt
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

    def get_last_instances(self) -> List[Tuple[int, str, str, str, datetime]]:
        """
        Retrieve the last instances of each record falling before today.

        Returns:
            List[Tuple[int, str, str, str, datetime]]: List of tuples containing
                record ID, name, details, type, and the last datetime.
        """
        today = int(datetime.now().timestamp())
        self.cursor.execute(
            """
            SELECT r.id, r.name, r.details, r.type, MAX(d.start_datetime) AS last_datetime
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
                record ID, name, details, type, and the next datetime.
        """
        today = int(datetime.now().timestamp())
        self.cursor.execute(
            """
            SELECT r.id, r.name, r.details, r.type, MIN(d.start_datetime) AS next_datetime
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
        Find records whose name or details fields contain a match for the given regex,
        including their last and next instances if they exist.

        Args:
            regex (str): The regex pattern to match.

        Returns:
            List[Tuple[int, str, str, str, Optional[int], Optional[int]]]:
                List of tuples containing:
                    - record ID
                    - name
                    - details
                    - type
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
                r.name,
                r.details,
                r.type,
                li.last_datetime,
                ni.next_datetime
            FROM Records r
            LEFT JOIN LastInstances li ON r.id = li.record_id
            LEFT JOIN NextInstances ni ON r.id = ni.record_id
            WHERE r.name REGEXP ? OR r.details REGEXP ?
            """,
            (today, today, regex, regex),
        )
        return self.cursor.fetchall()
