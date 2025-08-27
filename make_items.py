#! /usr/bin/env python3
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


# in_one_hour = (
#     datetime.now().replace(second=0, microsecond=0) + timedelta(hours=1)
# ).strftime("%Y%m%dT%H%M00")
def in_ten_minutes():
    now = datetime.now().replace(second=0, microsecond=0)
    delta_minutes = 10 + (10 - now.minute % 10)
    next = now + timedelta(minutes=delta_minutes)
    return next.strftime("%Y%m%dT%H%M%S")


def one_hour_ago():
    now = datetime.now().replace(second=0, microsecond=0)
    delta_minutes = 60 + (15 - now.minute % 15)
    next = now - timedelta(minutes=delta_minutes)
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


def in_five_days():
    now = datetime.now().replace(second=0, microsecond=0)
    delta_minutes = 60 + (15 - now.minute % 15)
    next = now + timedelta(days=5, minutes=delta_minutes)
    return next.strftime("%Y%m%dT%H%M%S")


def in_two_weeks():
    now = datetime.now().replace(second=0, microsecond=0)
    delta_minutes = 60 + (15 - now.minute % 15)
    next = now + timedelta(days=2 * 7, minutes=delta_minutes)
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
dbm = DatabaseManager("./example/tklr.db", env, reset=True)
# Insert the UTC records into the database

num_items = 20
types = ["-", "*"]

contexts = ["errands", "home", "office", "shop"]
tags = ["red", "green", "blue"]
dates = [0, 0, 0, 1, 0, 0, 0]  # dates 1/7 of the time
repeat = [0, 0, 0, 0, 1, 0, 0, 0, 0, 0]  # repeat 1/10 of the time
# duration = [to_tdstr(x) for x in range(6, 2 * 60 * 60, 6)]
duration = [to_tdstr(x) for x in range(0, 2 * 60 * 60, 300)]

now = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
num_konnections = 0
num_items = int(num_items)
wkbeg, wkend = week(now)
months = num_items // 200
start = wkbeg - 12 * 7 * ONEDAY
until = wkend + (40 * 7) * ONEDAY
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

first_of_month = now.replace(day=1).strftime("%Y%m%d")
yesterday_date = (now - ONEDAY).strftime("%Y%m%d")
today_date = now.strftime("%Y%m%d")
tomorrow_date = (now + ONEDAY).strftime("%Y%m%d")
# type, name, details, rrulestr, extent, alerts, location

items = [
    f"* first of the month @d all day event @s {first_of_month}",
    f"* yesterday @d all day event @s {yesterday_date}",
    f"* today @d all day event @s {today_date}",
    f"* tomorrow @d all day event @s {tomorrow_date}",
    f"~ all day yesterday @d all day task @p 2 @s {yesterday_date}",
    f"~ all day today @d all day task @p 2 @s {today_date}",
    f"~ all day tomorrow @d all day event @p 2 @s {tomorrow_date}",
    f"* zero extent naive @s {tomorrow_date}T100000 z none",
    f"* daily datetime US/Pacific @s {today_date} 1pm z US/Pacific @d whatever @c wherever @r d &i 3 &c 10",
    f"~ every other day @s {today_date} 10p @r d &i 2",
    f"~ due, tags, description, priority one @p 1 @s {tomorrow_date} @d This item has a description. Now is the time for all good men to come to the aid of their country. @t red @t white @t blue",
    f"* three datetimes @s {in_ten_minutes()} @e 45m  @+ {in_one_hour()}, {in_one_day()}",
    f"* ten minutes @s {in_ten_minutes()} @e {random.choice(duration)} @a 10m, 5m, 1m, 0m, -1m: d",  # ***
    f"* one hour @s {in_one_hour()} @e {random.choice(duration)} @a 1h, 30m, 10m, 5m, 0m, -5m: d",  # ***
    f"~ daily datetime @s {in_one_hour()} @e 1h30m @a 20m: d @r d &c 10",  # ***
    f"""% long formatted description @s {yesterday_date}
    @d Title
    1. This
       i. with part one
       ii. and this
    2. And finally this. 
    @t test @t red
    """,
    f"""^ dog house @s {in_five_days()} @e 3h @b 2w @p 3
    @~ create plan &s 1w &e 1h &r 1 &f {today_date}
    @~ go to Lowes &s 1w &e 2h &r 2: 1
    @~ buy lumber &s 1w &r 3: 2
    @~ buy hardware &s 1w &r 4: 2
    @~ buy paint &s 1w &r 5: 2
    @~ cut pieces &s 6d &e 3h &r 6: 3
    @~ assemble &s 4d &e 5h &r 7: 4, 6
    @~ sand &s 3d &e 1h &r 8: 7
    @~ paint &s 2d &e 2h &r 9: 8
    """,
    "~ no due date or datetime and priority one @p 1",
    f"~ one due date and priority one @s {today_date} @p 1",
    f"~ one due datetime and priority one @s {in_one_hour()} @p 1",
    "~ no due date and priority two @p 2",
    "~ no due date and priority three @p 3",
    "~ no due date and priority four @p 4",
    "~ no due date and no priority",
    "~ no due date and priority five @p 5",
    f"~ finished one hour ago @s {in_one_hour()} @f {one_hour_ago()}",
    f"^ no prerequisites @s {today_date} @b 1w @~ this &r 1 &f {today_date}  @~ that &r 2 &f {today_date}",
    "~ do over after 4 days when complete @s 22 12a @o 4d",
    "~ add another after 4 days when complete @s fri 12a @+ 26 12a",
    "? draft reminder - no checks",
    f"~ one date with priority three @s {yesterday_date} @p 3",
    "~ three datetimes @s 9am @+ 10am, 11am",
    "* multiday event @s 3p fri @e 2d2h30m",
    f"* single date @s {today_date}",
    "* daily datetime @s 3p @e 30m @r d",
]

records = []
num_items = 0
count = 0
while len(items) < num_items:
    t = random.choice(types)
    name = phrase()
    description = lorem.paragraph() + " #lorem"
    start = random.choice(datetimes)
    date = random.choice(dates)
    if date:
        # all day if event else end of day
        dts = start.strftime("%Y%m%d") if t == "*" else start.strftime("%Y%m%dT235959")
    else:
        dts = start.strftime("%Y%m%dT%H%M00")
    dtstart = local_dtstr_to_utc_str(dts)
    extent = random.choice(duration)
    if random.choice(repeat):
        items.append(
            f"{t} {name} @d {description} @s {dtstart} @e {extent} @r {random.choice(freq)} &i {random.choice(count)}"
        )
    else:
        items.append(f"{t} {name} @d {description} @s {dtstart} @e {extent}")


id = 0
for entry in items:
    count += 1
    id += 1
    print(f"---\n{entry = }")
    item = Item(raw=entry, env=env)  # .to_dict()
    # print(f"{item.structured_tokens = }\n{item.item = }")
    print(f"{item.item = }")

    dbm.add_item(item)
dbm.populate_dependent_tables()

print(f"Inserted {count} records into the database, last_id {id}.")
