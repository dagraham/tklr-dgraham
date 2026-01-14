#! /usr/bin/env python3
# To illustrate tklr
import random

from datetime import datetime, timedelta
from rich import print
from tklr.item import Item
from tklr.controller import Controller
from tklr.model import DatabaseManager
from tklr.tklr_env import TklrEnvironment

# from tklr.shared import log_msg
import lorem
from typing import Union
from dateutil.tz import gettz
from dateutil import rrule
from dateutil.rrule import rruleset, rrulestr
from dateutil.parser import parse


ONEDAY = timedelta(days=1)
ONEWEEK = timedelta(days=7)


BINS = [
    "activities/root",
    "2025:11/2025/journal/root",
    "2025:12/2025/journal/root",
    "2026:01/2026/journal/root",
    "library/root",
    "books/library/root",
    "movies/library/root",
    "series/library/root",
    "poetry/library/root",
    "quotations/library/root",
    "people:A/people/root",
    "people:B/people/root",
    "people:C/people/root",
    "places/root",
    "projects/root",
    "1_seed/idea garden/root",
    "2_germinating/idea garden/root",
    "3_sprouting/idea garden/root",
    "4_growing/idea garden/root",
    "5_flowering/idea garden/root",
    "tags/root",
]


# in_one_hour = (
#     datetime.now().replace(second=0, microsecond=0) + timedelta(hours=1)
# ).strftime("%Y-%m-%d %H:%M00")
def monday():
    return (parse("monday") - ONEWEEK).strftime("%Y-%m-%d")


def in_two_minutes():
    now = datetime.now().replace(second=0, microsecond=0)
    delta_minutes = 2 + (2 - now.minute % 10)
    next = now + timedelta(minutes=delta_minutes)
    return next.strftime("%Y-%m-%d %H:%M")


def in_five_minutes():
    now = datetime.now().replace(second=0, microsecond=0)
    delta_minutes = 5 + (5 - now.minute % 10)
    next = now + timedelta(minutes=delta_minutes)
    return next.strftime("%Y-%m-%d %H:%M")


def in_ten_minutes():
    now = datetime.now().replace(second=0, microsecond=0)
    delta_minutes = 10 + (10 - now.minute % 10)
    next = now + timedelta(minutes=delta_minutes)
    return next.strftime("%Y-%m-%d %H:%M")


def one_hour_ago():
    now = datetime.now().replace(second=0, microsecond=0)
    delta_minutes = 60 + (15 - now.minute % 15)
    next = now - timedelta(minutes=delta_minutes)
    return next.strftime("%Y-%m-%d %H:%M")


def in_one_hour():
    now = datetime.now().replace(second=0, microsecond=0)
    delta_minutes = 60 + (15 - now.minute % 15)
    next = now + timedelta(minutes=delta_minutes)
    return next.strftime("%Y-%m-%d %H:%M")


def in_one_day():
    now = datetime.now().replace(second=0, microsecond=0)
    delta_minutes = 60 + (15 - now.minute % 15)
    next = now + timedelta(days=1, minutes=delta_minutes)
    return next.strftime("%Y-%m-%d %H:%M")


def in_two_days():
    now = datetime.now().replace(second=0, microsecond=0)
    delta_minutes = 60 + (15 - now.minute % 15)
    next = now + timedelta(days=2, minutes=delta_minutes)
    return next.strftime("%Y-%m-%d %H:%M")


def in_five_days():
    now = datetime.now().replace(second=0, microsecond=0)
    delta_minutes = 60 + (15 - now.minute % 15)
    next = now + timedelta(days=5, minutes=delta_minutes)
    return next.strftime("%Y-%m-%d %H:%M")


def five_days_ago():
    now = datetime.now().replace(second=0, microsecond=0)
    delta_minutes = 60 + (15 - now.minute % 15)
    next = now - timedelta(days=5, minutes=delta_minutes)
    return next.strftime("%Y-%m-%d %H:%M")


def in_two_weeks():
    now = datetime.now().replace(second=0, microsecond=0)
    delta_minutes = 60 + (15 - now.minute % 15)
    next = now + timedelta(days=2 * 7, minutes=delta_minutes)
    return next.strftime("%Y-%m-%d %H:%M")


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

    try:
        local_dt = parser.parse(local_dt_str).astimezone()
        utc_dt = local_dt.astimezone(tz=gettz("UTC")).replace(tzinfo=None)
        # return utc_dt.isoformat()
        return utc_dt.strftime("%Y-%m-%d %H:%M")
    except:
        print(f"error parsing {local_dt_str = }")
        return ""


def to_tdstr(seconds: int) -> str:
    """Convert a timedelta object to a compact string like '1h30m20s'."""
    total = int(seconds)
    if total == 0:
        return "0s"

    h, remainder = divmod(total, 3600)
    m, s = divmod(remainder, 60)

    parts = []
    if h:
        parts.append(f"{h}h")
    if m:
        parts.append(f"{m}m")
    if s:
        parts.append(f"{s}s")

    return "".join(parts)


def week(dt: datetime) -> Union[datetime, datetime]:
    y, w, d = dt.isocalendar()
    wk_beg = dt - (d - 1) * ONEDAY if d > 1 else dt
    wk_end = dt + (7 - d) * ONEDAY if d < 7 else dt
    return wk_beg.date(), wk_end.date()


env = TklrEnvironment()
ctrl = Controller("./examples/tklr.db", env, reset=True)
# Insert the UTC records into the database

num_items = 0
types = ["*", "*", "*", "*", "*", "%"]

contexts = ["errands", "home", "office", "shop"]
tags = ["red", "green", "blue"]
dates = [0, 0, 0, 1, 0, 0, 0]  # dates 1/7 of the time
repeat = [0, 0, 0, 0, 1, 0, 0, 0, 0, 0]  # repeat 1/10 of the time
# duration = [to_tdstr(x) for x in range(6, 2 * 60 * 60, 6)]
duration = [to_tdstr(x) for x in range(0, 2 * 60 * 60, 900)]

now = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
num_konnections = 0
num_items = int(num_items)
wkbeg, wkend = week(now)
months = num_items // 200
start = wkbeg - 2 * 7 * ONEDAY
until = wkend + (6 * 7) * ONEDAY
print(f"Generating {num_items} records from {start} to {until}...")


def parse_rruleset(rrule_text: str) -> rruleset:
    lines = rrule_text.strip().splitlines()
    rset = rruleset()
    dtstart = None

    for line in lines:
        if line.startswith("DTSTART"):
            _, dt_str = line.split(":", 1)
            dtstart = parse(dt_str)
        elif line.startswith("RRULE"):
            rule = rrulestr(line, dtstart=dtstart)
            rset.rrule(rule)
        elif line.startswith("RDATE"):
            _, dt_str = line.split(":", 1)
            for rdate in dt_str.split(","):
                rset.rdate(parse(rdate))

    return rset


def handle_new_entry(self, entry_str: str):
    try:
        item = Item()
        item.parse(entry_str)
    except ValueError as e:
        self.show_error(f"Invalid entry: {e}")
        return

    self.model.add_item(item)


datetimes = list(
    rrule.rrule(
        rrule.DAILY,
        byweekday=range(7),
        byhour=range(7, 20),
        byminute=range(0, 60, 30),
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
yesterday_date = (now - ONEDAY).strftime("%Y-%m-%d")
today_date = now.strftime("%Y-%m-%d")
tomorrow_date = (now + ONEDAY).strftime("%Y-%m-%d")
one_week_ago = (now - ONEWEEK).strftime("%Y-%m-%d")
in_one_week = (now + ONEWEEK).strftime("%Y-%m-%d")
# type, name, details, rrulestr, extent, alerts, location


one_off = [
    f"* {phrase()} @s {in_ten_minutes()} @a 10m, 5m, 0m: n @d notify test #lorem",
    f"? {phrase()} @d draft test #lorem",
    f"* {phrase()} @s {in_five_days()} @n 7d @d notice test #lorem",
    f"! {phrase()} @s {monday()} @t 3/1w @d goal test #lorem",
    f"! {phrase()} @s {monday()} @t 3/1w  @k 1 @d goal test #lorem",
    f"! {phrase()} @s {monday()} @t 3/1w  @k 2 @d goal test #lorem",
    f"! {phrase()} @s {monday()} @t 3/2w @d goal test #lorem",
    f"! {phrase()} @s {monday()} @t 3/2w  @k 1 @d goal test #lorem",
    f"! {phrase()} @s {monday()} @t 3/2w  @k 2 @d goal test #lorem",
    f"~ {phrase()} @s {in_one_hour()} @p 1 @d dated task test #lorem",
    # f"~ {phrase()} @s {in_one_day()} @p 3 @d dated task test #lorem",
    # f"~ {phrase()} @s {in_two_days()} @p 5 @d dated task test #lorem",
    f"~ {phrase()} @s {in_five_days()} @p 4  @d dated task test #lorem",
    f"~ {phrase()} @s {in_two_weeks()} @p 2 @d dated task test #lorem",
    f"~ {phrase()} @s {five_days_ago()} @d dated task test #lorem",
    f"~ {phrase()} @s {in_one_hour()} @p 5 @d dated task test #lorem",
    # f"~ {phrase()} @s {in_one_day()} @p 3 @d dated task test #lorem",
    # f"~ {phrase()} @s {in_two_days()} @p 1 @d dated task test #lorem",
    f"~ {phrase()} @s {in_five_days()} @p 2 @d dated task test #lorem",
    f"~ {phrase()} @s {in_two_weeks()} @p 3 @d dated task test #lorem",
    f"~ {phrase()} @s {five_days_ago()} @p 1 @d dated task test #lorem",
    f"~ {phrase()} @p 1 @d undated task test #lorem",
    f"~ {phrase()} @p 3 @d undated task test #lorem",
    f"~ {phrase()} @p 5 @d undated task test #lorem",
    # f"~ {phrase()} @p 2 @d undated task test #lorem",
    # f"~ {phrase()} @p 4 @d undated task test #lorem",
    # f"~ {phrase()} @p 3 @d undated task test #lorem",
]

items = []
count = 0
num_items = 100
while len(items) < num_items:
    count += 1
    t = random.choice(types)
    name = phrase()
    description = lorem.paragraph() + " #lorem"
    start = random.choice(datetimes)
    date = random.choice(dates)
    if date:
        # all day if event else end of day
        dtstart = start.strftime("%Y%m%d")
    else:
        dtstart = start.strftime("%Y-%m-%d %H:%M")
    # dtstart = local_dtstr_to_utc_str(dts)
    extent = f" @e {random.choice(duration)}" if (t == "*" and not date) else ""
    # add_bin = random.choice([0, 0, 0, 0, 1, 1])
    # bin = f" @b {random.choice(BINS)}" if add_bin else ""
    bin = f" @b {random.choice(BINS)}"
    if random.choice(repeat):
        items.append(
            f"{t} {name} @d {description} @s {dtstart}{extent} @r {random.choice(freq)} {bin}"
        )
    else:
        items.append(f"{t} {name} @d {description} @s {dtstart}{extent} {bin}")


id = 0
for entry in one_off + items:
    count += 1
    id += 1
    try:
        item = Item(raw=entry, env=env, final=True, controller=ctrl)  # .to_dict()
        # new_entry = item.to_entry()
        # print(f">>>\n{new_entry = }")
        # continue
        record_id = ctrl.add_item(item)  # .to_dict()
    except Exception as e:
        print(f"error processing {entry}\n{e = }")

try:
    ctrl.db_manager.populate_dependent_tables()
except Exception as e:
    print(f"Error: {e}")

print(f"Inserted {count} records into the database, last_id {id}.")
