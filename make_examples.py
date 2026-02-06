#! /usr/bin/env python3
# To illustrate tklr
import random
import shutil
from pathlib import Path
import os
import re

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

os.environ["TKLR_HOME"] = "/Users/dag/Projects/tklr-uv/examples_dark"

ONEDAY = timedelta(days=1)
ONEWEEK = timedelta(days=7)


BINS = [
    "activities/root",
    "2025:11/2025/journal/root",
    "2025:12/2025/journal/root",
    "2026:01/2026/journal/root",
    "library/root",
    "books/library/root",
    "ideas/library/root",
    "movies/library/root",
    "series/library/root",
    "poetry/library/root",
    "quotations/library/root",
    "people:A/people/root",
    "people:B/people/root",
    "people:C/people/root",
    "places/root",
    "projects/root",
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


def minutes_ago(minutes: int) -> str:
    now = datetime.now().replace(second=0, microsecond=0)
    next = now - timedelta(minutes=minutes)
    return next.strftime("%Y-%m-%d %H:%M")


def days_ago() -> str:
    now = datetime.now().replace(second=0, microsecond=0)
    num_days = random.choice([3, 4, 5, 6, 7, 8, 9])
    next = now - timedelta(days=num_days)
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


def one_weeks_ago():
    now = datetime.now().replace(second=0, microsecond=0)
    delta_minutes = 60 + (15 - now.minute % 15)
    next = now - timedelta(days=7, minutes=delta_minutes)
    return next.strftime("%Y-%m-%d %H:%M")


def two_weeks_ago():
    now = datetime.now().replace(second=0, microsecond=0)
    delta_minutes = 60 + (15 - now.minute % 15)
    next = now - timedelta(days=2 * 7, minutes=delta_minutes)
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
ctrl = Controller("./examples_dark/tklr.db", env, reset=True)
# Insert the UTC records into the database

num_items = 0
types = ["*", "*", "*", "*", "*", "%", "~", "~", "-", "-"]

contexts = ["errands", "home", "office", "shop"]
use_cases = ["writing", "reading", "exercise", "meditation", "coding"]
tags = ["amber", "cyan", "blue"]
dates = [0, 0, 0, 1, 0, 0, 0]  # dates 1/7 of the time
repeats = [0, 0, 0, 0, 1, 0, 0, 0, 0, 0]  # repeat 1/10 of the time
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


def use():
    return " ".join(lorem.sentence()[:-1].split(" ")[:2])


def collect_use_names(entries: list[str], env: TklrEnvironment) -> list[str]:
    names: set[str] = set()
    for entry in entries:
        if "@u" not in entry:
            continue
        try:
            probe = Item(raw=entry, env=env)
        except Exception:
            continue
        if probe.use:
            names.add(probe.use)
    return sorted(names)


freq = [
    "FREQ=WEEKLY;INTERVAL=1",
    "FREQ=WEEKLY;INTERVAL=1;BYDAY=MO,WE,FR",
    "FREQ=WEEKLY;INTERVAL=2",
    "FREQ=DAILY",
    "FREQ=DAILY;INTERVAL=2",
    "FREQ=DAILY;INTERVAL=3",
]


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
    f"* {phrase()} @s {monday()} 10a @a 0m: n @d dated task test #lorem",
    f"~ {phrase()} @s {in_one_hour()} @p 1 @d dated task test #lorem",
    f"* {phrase()} @s {in_one_day()} 9a @a 0m: n @d dated task test #lorem",
    f"* {phrase()} @s {in_two_days()} 10a @a 0m: n @d dated task test #lorem",
    f"* {phrase()} @s {in_five_days()} 11a @a 0m: n @d dated task test #lorem",
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
    f"- {phrase()} @s {one_weeks_ago()} @u {use()} @d u without e  #lorem",
    f"- {phrase()} @s {one_weeks_ago()} @u {use()} @e 25m @d u and e #lorem",
    f"- {phrase()} @s {one_weeks_ago()} @e 1h5m @d e without u #lorem",
    f"- {phrase()} @s {one_weeks_ago()} @d neither u nor e #lorem",
    f"- {phrase()} @s {two_weeks_ago()} @u {use()} @d u without e  #lorem",
    f"- {phrase()} @s {two_weeks_ago()} @u {use()} @e 25m @d u and e #lorem",
    f"- {phrase()} @s {two_weeks_ago()} @e 1h5m @d e without u #lorem",
    f"- {phrase()} @s {two_weeks_ago()} @d neither u nor e #lorem",
    f"- {phrase()} @s {minutes_ago(10)} @u {use()} @d u without e  #lorem",
    f"- {phrase()} @s {minutes_ago(40)} @u {use()} @e 25m @d u and e #lorem",
    f"- {phrase()} @s {minutes_ago(90)} @e 1h5m @d e without u #lorem",
    f"- {phrase()} @s {minutes_ago(120)} @d neither u nor e #lorem",
    f"- {phrase()} @d neither s, e or u #lorem",
    # f"~ {phrase()} @p 2 @d undated task test #lorem",
    # f"~ {phrase()} @p 4 @d undated task test #lorem",
    # f"~ {phrase()} @p 3 @d undated task test #lorem",
    "% Waldo Jones @d Plumber who fixed drain, June 2025, very good. Mobile 1 919 123-4567 @b people:J/people",
]

items = []
count = 0
num_items = 100
while len(items) < num_items:
    count += 1
    t = random.choice(types)
    extent = f" @e {random.choice(duration)}" if t in ["*", "-"] else ""
    name = phrase()
    description = lorem.paragraph() + " #lorem"
    if t == "-":
        dtstart = days_ago()
        date = 0
        bin = ""
        repeat = ""
    else:
        start = random.choice(datetimes)
        date = random.choice(dates)
        bin = f" @b {random.choice(BINS)}"
        dtstart = start.strftime("%Y%m%d") if date else start.strftime("%Y-%m-%d %H:%M")
        if t in ["*", "~"] and random.choice(repeats):
            repeat = f" @r {random.choice(freq)};COUNT={random.choice([2, 3, 4, 5])}"
        else:
            repeat = ""
    tag = f" #{random.choice(tags)}"

    # dtstart = local_dtstr_to_utc_str(dts)
    # add_bin = random.choice([0, 0, 0, 0, 1, 1])
    # bin = f" @b {random.choice(BINS)}" if add_bin else ""
    items.append(
        f"{t} {name} @d {description}{tag}  @s {dtstart}{extent}{repeat} {bin}"
    )
    # if random.choice(repeat):
    #     items.append(
    #         f"{t} {name} @d {description} #{random.choice(tags)}  @s {dtstart}{extent} @r {random.choice(freq)} {bin}"
    #     )
    # else:
    #     items.append(f"{t} {name} @d {description} @s {dtstart}{extent} {bin}")


id = 0
try:
    for name in collect_use_names(one_off + items, env):
        ctrl.add_use(name)
except Exception as e:
    print(f"Error while creating uses: {e}")

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

# Duplicate the generated DB for the light-themed example home.
src_db = Path("./examples_dark/tklr.db")
dst_home = Path("./examples_light")
dst_db = dst_home / "tklr.db"
try:
    dst_home.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src_db, dst_db)
    print(f"Copied database to {dst_db}")
except Exception as exc:
    print(f"[red]Failed to copy database to examples_light:[/red] {exc}")
