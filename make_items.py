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
ONEWEEK = timedelta(days=7)


# in_one_hour = (
#     datetime.now().replace(second=0, microsecond=0) + timedelta(hours=1)
# ).strftime("%Y-%m-%d %H:%M00")
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
# dbm = DatabaseManager("./example/tklr.db", env, reset=True)
ctrl = Controller("./example/tklr.db", env, reset=True)
# Insert the UTC records into the database

num_items = 0
types = ["~", "~", "*", "~", "*", "*", "*", "*", "%"]

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
until = wkend + (10 * 7) * ONEDAY
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


busy = [
    f"* all-day yesterday @d all day event @s {yesterday_date}",
    f"* all-day today @d all day event @s {today_date}",
    f"* all-day tomorrow @d all day event @s {tomorrow_date}",
    f"* one hour yesterday @s {yesterday_date} 9a @e 1h",
    f"* one hour today @s {today_date} 10a @e 1h",
    f"* one hour tomorrow @s {tomorrow_date} 11a @e 1h",
    "* all-day every Tuesday @s tue @r w &c 3",
    "* all-day every fourth day @s wed @r d &i 3 &c 5",
    f"* 2-hours every third day @s {in_one_week} 9a @e 2h @r d &i 3 &c 5",
    "* spanning 3 days @s sat 7p @e 2d2h30m",
    f"* 1-hour last, this and next week @s {one_week_ago} 4p @e 1h  @+ {today_date} 4p, {in_one_week} 4p",
]


items = [
    f"* first of the month @d all day event @s {first_of_month}",
    f"* event in 2 days with 1d beginby @s {in_two_days()} @n 1d",
    f"~ task in 5 days with 1w beginby @s {in_five_days()} @n 1w",
    f"* event in 1 day with beginby @s {tomorrow_date} @n 1w",
    f"~ all day yesterday @d all day task @p 2 @s {yesterday_date}",
    f"~ all day today @d all day task @p 2 @s {today_date}",
    f"~ all day tomorrow @d all day event @p 2 @s {tomorrow_date}",
    f"* zero extent naive @s {tomorrow_date} 10h @z none",
    f"* zero extent naive from z @s {tomorrow_date} 10h z none",
    "* daily with US/Pacific from z @s 3pm z US/Pacific @d whatever @c wherever @r d &i 3 &c 10",
    "* daily datetime US/Pacific @s 1pm @z US/Pacific @d whatever @c wherever @r d &i 3 &c 10",
    f"~ every other day @s {today_date} 10p @r d &i 2",
    f"* starting in 5 days repeating for 3 days @s {in_five_days()} 8:30a @e 4h @r d &c 3 @n 1w",
    f"~ repeating and rdates @s {today_date} 1:30p @r d @+ 2:30p, 3:30p",
    f"~ repeating, rdates and finish  @s {today_date} 1:30p @r d &c 3 @+ 10:30a, 3:30p @f 8:15a",
    f"* repeating until  @s {today_date} 7:30p @e 1h @r d &u {in_two_weeks()}",
    f"~ due, tags, description, priority one @p 1 @s {tomorrow_date} @d This item has a description. Now is the time for all good men to come to the aid of their country. @t red @t white @t blue",
    f"* three datetimes @s {in_ten_minutes()} @e 45m  @+ {in_one_hour()}, {in_one_day()}",
    f"""% long formatted description @s {yesterday_date}
    @d Title
    1. This
       i. with part one
       ii. and this
    2. And finally this. 
    """,
    f"""^ dog house @s {in_five_days()} @e 3h @n 2w @p 3 @~ create plan &s 1w &e 1h &r 1 &f {one_hour_ago()} @~ go to Lowes &s 1w &e 2h &r 2: 1 @~ buy lumber &s 1w &r 3: 2 @~ buy hardware &s 1w &r 4: 2 @~ buy paint &s 1w &r 5: 2 @~ cut pieces &s 6d &e 3h &r 6: 3 @~ assemble &s 4d &e 5h &r 7: 4, 6 @~ sand &s 3d &e 1h &r 8: 7 @~ paint &s 2d &e 2h &r 9: 8 """,
    "~ no due date or datetime and priority one @p 1",
    f"~ one due date and priority one @s {today_date} @p 1",
    f"~ one due datetime and priority one @s {in_one_hour()} @p 1",
    "~ no due date and priority two @p 2",
    "~ no due date and priority three @p 3",
    "~ no due date and priority four @p 4",
    "~ no due date and no priority",
    "~ no due date and priority five @p 5",
    f"~ finished one hour ago @s {in_one_hour()} @f {one_hour_ago()}",
    f"^ no prerequisites @s {today_date} @n 1w @~ this &r 1 &f {today_date}  @~ that &r 2",
    f"~ do over with finish @s {five_days_ago()} 12:00pm  @f {today_date} 10:00am @o 4d",
    f"~ do over learn with finish  @s {five_days_ago()} 12:00pm  @f {today_date} 10:00am @o ~4d",
    "? draft reminder - no checks",
    f"~ one date with priority three @s {yesterday_date} @p 3",
    "~ three datetimes @s 9am @+ 10am, 11am",
    "* event spread over multiple days @s 3p fri @e 2d2h30m",
    "* daily datetime @s 3p @e 30m @r d",
    "* gour Tiki Roundtable Meeting @s 1/1 14:00 z UTC @e 1h30m @r m &w +3TH &c 10",
    "* timezone test for noon CET @s 12p z CET @e 1h",
    "* timezone test for noon naive @s 12p z none @e 1h",
]

bins = [
    "% Journal entry for October @b 2025:10/2025/journal @s 2p @d Test bin entries",
    "% Churchill - Give me a pig @b Churchill/quotations/library @d Dogs look up at you.\nCats look down at you.\nGive me a pig. They look you in the eye and treat you as an equal.",
    "* Ellen's French adventure @s mon @r d &c 7 @b travel/activities @b Lille/France/places",
    "% Charles and Bonnie Smith @b SmithCB/people:S/people @d details about Charles and Bonnie @b Athens/Greece/places",
    "% itenerary  @b Athens-Istanbul/travel/activities @b Istanbul/Turkey/places",
]

alerts = [
    f"* alert test  @s {in_five_minutes()} @a 3m, 1m: v",
    f"* notify test @s {in_five_minutes()} @a 4m, 2m, 0m: n",
]

records = []
count = 0
# items = []
# num_items = 0
while len(items) < num_items:
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
    if random.choice(repeat):
        items.append(
            f"{t} {name} @d {description} @s {dtstart}{extent} @r {random.choice(freq)} "
        )
    else:
        items.append(f"{t} {name} @d {description} @s {dtstart}{extent}")


id = 0
# for entry in items:  # + alerts:
# for entry in busy + items:
for entry in items + bins + alerts:
    count += 1
    id += 1
    try:
        item = Item(raw=entry, env=env, final=True, controller=ctrl)  # .to_dict()
        # new_entry = item.to_entry()
        # print(f">>>\n{new_entry = }")
        # continue
        record_id = ctrl.add_item(item)  # .to_dict()
        if count % 20 == 0:
            print(f"---\n{count} {entry = }")
    except:
        print(f"\n{item.entry}\n")
        print(f"{record_id = }, {item.tokens = }; {item.rruleset = }")

try:
    ctrl.db_manager.populate_dependent_tables()
except Exception as e:
    print(f"Error: {e}")

print(f"Inserted {count} records into the database, last_id {id}.")
