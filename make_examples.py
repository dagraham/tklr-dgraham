import random
from datetime import datetime, timedelta
from rich import print
from tklr.model import DatabaseManager
from tklr.shared import log_msg
import lorem
from typing import List, Tuple, Union
from dateutil.tz import gettz
from dateutil import rrule
from dateutil.rrule import rrulestr
import math

ONEDAY = timedelta(days=1)


# in_one_hour = (
#     datetime.now().replace(second=0, microsecond=0) + timedelta(hours=1)
# ).strftime("%Y%m%dT%H%M00")
def in_ten_minutes():
    now = datetime.now().replace(second=0, microsecond=0)
    delta_minutes = 10 + (10 - now.minute % 10)
    next = now + timedelta(minutes=delta_minutes)
    return next.strftime("%Y%m%dT%H%M%S")


def in_one_hour():
    now = datetime.now().replace(second=0, microsecond=0)
    delta_minutes = 60 + (15 - now.minute % 15)
    next = now + timedelta(minutes=delta_minutes)
    return next.strftime("%Y%m%dT%H%M%S")


def in_one_day():
    now = datetime.now().replace(second=0, microsecond=0)
    delta_minutes = 60 + (15 - now.minute % 15)
    next = now + timedelta(days=1, minutes=delta_minutes)
    return next.strftime("%Y%m%dT%H%M%S")


def local_dtstr_to_utc_str(local_dt_str: str) -> str:
    """
    Convert a local datetime string to a UTC datetime string.

    Args:
        local_dt_str (str): Local datetime string.
        local_tz_str (str): Local timezone string.

    Returns:
        str: UTC datetime string.
    """
    from dateutil import parser

    local_dt = parser.parse(local_dt_str).astimezone()
    utc_dt = local_dt.astimezone(tz=gettz("UTC")).replace(tzinfo=None)
    # return utc_dt.isoformat()
    return utc_dt.strftime("%Y%m%dT%H%M%S")


def week(dt: datetime) -> Union[datetime, datetime]:
    y, w, d = dt.isocalendar()
    wk_beg = dt - (d - 1) * ONEDAY if d > 1 else dt
    wk_end = dt + (7 - d) * ONEDAY if d < 7 else dt
    return wk_beg.date(), wk_end.date()


dbm = DatabaseManager("example.db", reset=True)
# Insert the UTC records into the database

num_items = 400
types = ["-", "*"]

locations = ["errands", "home", "office", "shop"]
tags = ["red", "green", "blue"]
dates = [0, 0, 0, 1, 0, 0, 0]  # dates 1/7 of the time
repeat = [0, 0, 0, 0, 1, 0, 0, 0, 0, 0]  # repeat 1/10 of the time
duration = [x for x in range(0, 210, 15)]

now = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
num_konnections = 0
num_items = int(num_items)
wkbeg, wkend = week(now)
months = num_items // 200
start = wkbeg - 12 * 7 * ONEDAY
until = wkend + (40 * 7) * ONEDAY
print(f"Generating {num_items} records from {start} to {until}...")


datetimes = list(
    rrule.rrule(
        rrule.DAILY,
        byweekday=range(7),
        byhour=range(6, 20),
        byminute=range(0, 60, 15),
        dtstart=start,
        until=until,
    )
)

tmp = []
while len(tmp) < 8:
    _ = lorem.sentence().split(" ")[0]
    if _ not in tmp:
        tmp.append(_)

names = []
for i in range(0, 8, 2):
    names.append(f"{tmp[i]}, {tmp[i + 1]}")


def phrase():
    # for the summary
    # drop the ending period
    s = lorem.sentence()[:-1]
    num = random.choice([3, 4, 5])
    words = s.split(" ")[:num]
    return " ".join(words).rstrip()


def word():
    return lorem.sentence()[:-1].split(" ")[0]


freq = [
    "FREQ=WEEKLY;INTERVAL=1",
    "FREQ=WEEKLY;INTERVAL=1;BYDAY=MO,WE,FR",
    "FREQ=WEEKLY;INTERVAL=2",
    "FREQ=DAILY",
    "FREQ=DAILY;INTERVAL=2",
    "FREQ=DAILY;INTERVAL=3",
]

count = [f"COUNT={n}" for n in range(2, 5)]

first_of_month = now.replace(day=1).strftime("%Y-%m-%d")
yesterday_date = (now - ONEDAY).strftime("%Y%m%d")
today_date = now.strftime("%Y%m%d")
tomorrow_date = (now + ONEDAY).strftime("%Y%m%d")
# type, name, details, rrulestr, extent, alerts, location
records = [
    ("*", "first of the month", "all day event", f"RDATE:{first_of_month}", 0, ""),
    ("*", "all day yesterday", "all day event", f"RDATE:{yesterday_date}", 0, ""),
    ("*", "all day today", "all day event", f"RDATE:{today_date}", 0, ""),
    ("*", "all day tomorrow", "all day event", f"RDATE:{tomorrow_date}", 0, ""),
    ("-", "day end yesterday", "all day task", f"RDATE:{yesterday_date}T235959", 0, ""),
    ("-", "day end today", "all day task", f"RDATE:{today_date}T235959", 0, ""),
    ("-", "day end tomorrow", "all day task", f"RDATE:{tomorrow_date}T235959", 0, ""),
    ("*", "zero extent", "zero extent event", f"RDATE:{tomorrow_date}T100000", 0, ""),
    # (
    #     "*",
    #     "ten minutes",
    #     "test alert event",
    #     f"RDATE:{in_ten_minutes()}",
    #     random.choice(duration),
    #     "600, 300, 120, 60, 0, -60: d",
    # ),
    # (
    #     "*",
    #     "today",
    #     "test alert event",
    #     f"RDATE:{in_one_hour()}",
    #     random.choice(duration),
    #     "3600, 1800, 600, 300, 0, -300: d",
    # ),
    # (
    #     "*",
    #     "tomorrow",
    #     "test alert event",
    #     f"RDATE:{in_one_day()}",
    #     random.choice(duration),
    #     "3600, 1800, 600, 300, 0, -300: d",
    # ),
]
while len(records) < num_items:
    t = random.choice(types)
    name = phrase()
    details = lorem.paragraph() + " #lorem"
    start = random.choice(datetimes)
    date = random.choice(dates)
    if date:
        # all day if event else end of day
        dts = (
            start.strftime("%Y%m%dT000000")
            if t == "*"
            else start.strftime("%Y%m%dT235959")
        )
    else:
        dts = start.strftime("%Y%m%dT%H%M00")
    dtstart = local_dtstr_to_utc_str(dts)
    if random.choice(repeat):
        rrulestr = (
            f"DTSTART:{dtstart}\\nRRULE:{random.choice(freq)};{random.choice(count)}"
        )
    else:
        rrulestr = f"RDATE:{dtstart}"
    extent = random.choice(duration)
    # if date:
    #     name = f"{name} {start.strftime('%Y-%m-%d')}"
    #     # extent = 0
    records.append((t, name, details, rrulestr, extent, ""))

id = 0
for record in records:
    id += 1
    dbm.add_record(
        record[0], record[1], record[2], record[3], record[4], record[5], "test"
    )
print(f"Inserted {num_items} records into the database, last_id {id}.")
