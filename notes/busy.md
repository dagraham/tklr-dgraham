# Busy View Tweaks

My way of constructing the busy table for 4 week blocks as bit clunky and slow. I'm thinking of alternative approaches.

Suppose there were a WeeksTable with records for each year-week in a relevant period with these columns

- unique_id
- year_week: YYYY-WW (year-week_number) such as "2025-41"
- busy: 35-digit string of 0 and 1's
  representing 5-bits of busy information for each of the 7 week days in the year week. In each block of 5 digits:
  - digit 0: 1 if an all day event is scheduled
  - digit 1: 1 if the busy period for any event intersects the period from 00:00 until 05:59
  - digit 2: 1 if the busy period for any event intersects the period from 06:00 until 11:59
  - digit 3: 1 if the busy period for any event intersects the period from 12:00 until 17:59
  - digit 4: 1 if the busy period for any event intersects the period from 18:00 until 23:59

When the datetimes table is being populated, a busy string could be calculated for each processed record where the itemtype is "\*" (an event) and

- either the extent is None and the start hour and minute are both zero: an all day event is scheduled for this year_week and week day, so digit 0 for this year-week and week day would be set to 1
- the extent is not None:
  - the appropriate digit 1 ... digit 5 are set to 1 for each of the 4 x 5h59m blocks from start through start plus extent

Thoughts so far?

Question. Starting from a defaults of busy = "00000000000000000000000000000000000" for each year-week in the relvevant period, is there an convenient idiom for updating this default based on the successive use of the corresponding strings for each of the year-weeks generated for each record?

```python
from datetime import datetime, timedelta

# 6-hour windows within a day (local-naive)
WINDOWS = [
    (0, 6),   # bit 1: 00:00 - 06:00
    (6, 12),  # bit 2: 06:00 - 12:00
    (12, 18), # bit 3: 12:00 - 18:00
    (18, 24), # bit 4: 18:00 - 24:00
]
  -
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

def busy_bits_for_event(start: str, end: str | None):
    """
    Return a list of { 'YYYY-WW': '35-bit-string' } for the weeks touched by [start, end).
    Bits per day: [all-day, 00-06, 06-12, 12-18, 18-24].
    """
    start_dt = _parse_local_naive(start)

    # Case 1: all-day marker (end is None and start ends with 0000)
    if end is None and start.endswith("0000"):
        week_key = _iso_year_week(start_dt)
        # 7 days × 5 bits = 35 bits
        bits = ["0"] * 35
        weekday = start_dt.isoweekday() - 1  # Mon=0..Sun=6
        # set all-day bit (index 0 within this day’s 5-bit block)
        bits[weekday * 5 + 0] = "1"
        return [{week_key: "".join(bits)}]

    # Case 2: timed interval: set 6-hour blocks (never set all-day)
    end_dt = _parse_local_naive(end) if end else None
    if not end_dt or end_dt <= start_dt:
        # nothing to mark
        return []

    # Build mapping week_key -> 35-bit list
    weeks: dict[str, list[str]] = {}

    # Iterate days from start.date() to end.date(), inclusive of any overlap
    day = start_dt.replace(hour=0, minute=0)
    # If start has time after midnight, day is that midnight. We’ll loop until
    # the day whose midnight >= end_dt (half-open)
    cursor = day
    while cursor < end_dt:
        week_key = _iso_year_week(cursor)
        if week_key not in weeks:
            weeks[week_key] = ["0"] * 35

        weekday = cursor.isoweekday() - 1  # 0..6
        base = weekday * 5  # start index for this day’s 5 bits

        # For each 6-hour window, set bit if the event overlaps it
        day_start = cursor
        for i, (h0, h1) in enumerate(WINDOWS, start=1):  # bits 1..4
            w_start = day_start.replace(hour=h0, minute=0)
            w_end   = day_start.replace(hour=0, minute=0) + timedelta(hours=h1)
            # overlap > 0 ?
            if max(start_dt, w_start) < min(end_dt, w_end):
                weeks[week_key][base + i] = "1"

        cursor += timedelta(days=1)

    # Convert lists to strings
    return [{wk: "".join(bits)} for wk, bits in weeks.items()]

```

```python

        # One row per event occurrence per week
        self.cursor.execute("""
          CREATE TABLE IF NOT EXISTS BusyWeeksFromDateTimes (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              record_id INTEGER NOT NULL,
              year_week TEXT NOT NULL,
              busybits INTEGER NOT NULL,  -- 35-bit packed integer
              FOREIGN KEY(record_id) REFERENCES DateTimes(record_id)
          );
        """)

        self.cursor.execute("""
          CREATE UNIQUE INDEX IF NOT EXISTS idx_busy_from_record_week
              ON BusyWeeksFromDateTimes(record_id, year_week);
        """)

        # Aggregate layer: one per year-week
        self.cursor.execute("""
          CREATE TABLE IF NOT EXISTS BusyWeeks (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              year_week TEXT UNIQUE NOT NULL,
              busybits INTEGER NOT NULL
          );
        """)

        self.cursor.execute("""
          CREATE TABLE IF NOT EXISTS BusyUpdateQueue (
              record_id INTEGER PRIMARY KEY
          );
        """)

        # -- When a DateTimes row is inserted
        self.cursor.execute("""
          CREATE TRIGGER IF NOT EXISTS trig_busy_insert
          AFTER INSERT ON DateTimes
          BEGIN
              INSERT OR IGNORE INTO BusyUpdateQueue(record_id)
              VALUES (NEW.record_id);
          END;
        """)

        # -- When a DateTimes row is updated
        # -- When a DateTimes row is inserted
        self.cursor.execute("""
          CREATE TRIGGER IF NOT EXISTS trig_busy_update
          AFTER UPDATE ON DateTimes
          BEGIN
              INSERT OR IGNORE INTO BusyUpdateQueue(record_id)
              VALUES (NEW.record_id);
          END;
        """)

        # -- When a DateTimes row is deleted
        # -- When a DateTimes row is inserted
        self.cursor.execute("""
          CREATE TRIGGER IF NOT EXISTS trig_busy_delete
          AFTER DELETE ON DateTimes
          BEGIN
              INSERT OR IGNORE INTO BusyUpdateQueue(record_id)
              VALUES (OLD.record_id);
          END;
        """)

```

```python

    def update_busyweeks_for_record(self, record_id: int):
        """
        Recompute BusyWeeksFromDateTimes rows for the given record,
        then update BusyWeeks aggregates only for affected year-weeks.
        """
        # 1️⃣ Delete old busy records for this record_id
        self.cursor.execute(
            "SELECT DISTINCT year_week FROM BusyWeeksFromDateTimes WHERE record_id=?",
            (record_id,),
        )
        old_weeks = [row[0] for row in self.cursor.fetchall()]

        self.cursor.execute(
            "DELETE FROM BusyWeeksFromDateTimes WHERE record_id=?", (record_id,)
        )

        # 2️⃣ Fetch new start/end datetimes for this record
        self.cursor.execute(
            "SELECT start_datetime, end_datetime FROM DateTimes WHERE record_id=?",
            (record_id,),
        )
        rows = self.cursor.fetchall()

        new_week_entries: list[tuple[str, int]] = []
        for start_dt, end_dt in rows:
            for wk_bits in busy_bits_for_event(start_dt, end_dt):
                for wk, bits in wk_bits.items():
                    new_week_entries.append((wk, bits_to_int(bits)))

        # 3️⃣ Insert fresh BusyWeeksFromDateTimes rows
        for week_key, bits_int in new_week_entries:
            self.cursor.execute(
                """
                INSERT OR REPLACE INTO BusyWeeksFromDateTimes (record_id, year_week, busybits)
                VALUES (?, ?, ?)
                """,
                (record_id, week_key, bits_int),
            )

        # 4️⃣ Aggregate BusyWeeks for affected weeks (old ∪ new)
        affected = sorted(set(old_weeks) | {wk for wk, _ in new_week_entries})
        for week_key in affected:
            self.cursor.execute(
                "SELECT busybits FROM BusyWeeksFromDateTimes WHERE year_week=?",
                (week_key,),
            )
            bits = [row[0] for row in self.cursor.fetchall()]
            agg = or_aggregate(bits)
            self.cursor.execute(
                """
                INSERT INTO BusyWeeks (year_week, busybits)
                VALUES (?, ?)
                ON CONFLICT(year_week)
                DO UPDATE SET busybits=excluded.busybits
                """,
                (week_key, agg),
            )
        self.conn.commit()

    def flush_busy_update_queue(self):
        """Recompute BusyWeeks for any records flagged by triggers."""
        self.cursor.execute("SELECT record_id FROM BusyUpdateQueue")
        record_ids = [r[0] for r in self.cursor.fetchall()]

        if not record_ids:
            return

        for rid in record_ids:
            self.update_busyweeks_for_record(rid)

        self.cursor.execute("DELETE FROM BusyUpdateQueue")
        self.conn.commit()

```

First tables and flow

BusyWeeksFromDateTimes (generated by applying busy_bits_for_event to each record in DateTimes)

- id
- record_id
- year_week
- busybits

BusyWeeks (generated by aggregating records from BusyWeeksFromDateTimes)

- id
- year_week
- busybits

My hope is that a change in a record would only propagate changes in the records in BusyWeeksFromDateTimes for the corresponding record_id and that changes in those records would only propagate changes in the affected year-weeks in BusyWeeks

## to 15 minute resolution

```python
  def setup_busy_tables(self):
      """
      Create fine-grained and aggregated busy/conflict tables
      (15-minute resolution, ternary busy bits stored as BLOBs).
      """

      # One row per event occurrence per week
      self.cursor.execute("""
          CREATE TABLE IF NOT EXISTS BusyWeeksFromDateTimes (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              record_id INTEGER NOT NULL,
              year_week TEXT NOT NULL,
              busybits BLOB NOT NULL,           -- 672 slots (15-min blocks, 0/1)
              FOREIGN KEY(record_id) REFERENCES DateTimes(record_id)
          );
      """)

      self.cursor.execute("""
          CREATE UNIQUE INDEX IF NOT EXISTS idx_busy_from_record_week
              ON BusyWeeksFromDateTimes(record_id, year_week);
      """)

      # Aggregate layer: one per year-week
      self.cursor.execute("""
          CREATE TABLE IF NOT EXISTS BusyWeeks (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              year_week TEXT UNIQUE NOT NULL,
              busybits BLOB NOT NULL             -- 672 slots (0/1/2 = free/busy/conflict)
          );
      """)

      # Update queue table for incremental recomputation
      self.cursor.execute("""
          CREATE TABLE IF NOT EXISTS BusyUpdateQueue (
              record_id INTEGER PRIMARY KEY
          );
      """)

      # Triggers on DateTimes to enqueue changed record_id
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

      self.conn.commit()

```

With **numpy**

```python
import math
from datetime import datetime, timedelta
from typing import Dict
import numpy as np


def fine_busy_bits_for_event(start_str: str, end_str: str | None, resolution: int = 15) -> dict[str, np.ndarray]:
    """
    Map affected year-weeks → busy-bit arrays (uint8, 0/1 per slot).

    Half-open interval semantics:
      - Marks slots where start ≤ t < end.
      - A block that begins exactly at 'end' is not marked.
    """
    # Parse start and end
    start = datetime.strptime(start_str, "%Y%m%dT%H%M")
    if end_str:
        end = datetime.strptime(end_str, "%Y%m%dT%H%M")
    else:
        # handle your special "all-day or zero-extent" rules here
        if start.hour == 0 and start.minute == 0:
            end = None  # all-day marker elsewhere
        else:
            return {}

    # Sanity check
    if end and end <= start:
        raise ValueError("End must be after start")

    slot_minutes = resolution
    slots_per_day = (24 * 60) // slot_minutes  # e.g., 96
    slots_per_week = slots_per_day * 7
    weeks: dict[str, np.ndarray] = {}

    def yw_key(dt: datetime) -> str:
        y, w, _ = dt.isocalendar()
        return f"{y:04d}-{w:02d}"

    cur = start
    while cur.date() <= (end.date() if end else start.date()):
        ywk = yw_key(cur)
        if ywk not in weeks:
            weeks[ywk] = np.zeros(slots_per_week, dtype=np.uint8)

        # day boundaries
        day_start = datetime.combine(cur.date(), datetime.min.time())
        day_end = datetime.combine(cur.date(), datetime.max.time())

        s = max(start, day_start)
        e = min(end, day_end) if end else None

        if e:  # mark half-open interval [s, e)
            s_min = (s.hour * 60 + s.minute) // slot_minutes
            e_min = (e.hour * 60 + e.minute) // slot_minutes  # exclusive upper bound
            s_min = (s.hour * 60 + s.minute) // slot_minutes
            e_min = math.ceil((e.hour * 60 + e.minute) / slot_minutes)
            wd = s.weekday()
            base = wd * slots_per_day
            weeks[ywk][base + s_min : base + e_min] = 1

        cur += timedelta(days=1)

    return weeks

```
