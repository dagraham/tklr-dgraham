# For ChatGPT

## 2025-08-15 more finished

I had thought that "do_complete()" in Item would simply add an "&f datetime" entry to a job (task in a project) or an "@f datetime" entry to a task and then, when the entry is complete, there would be a new "finalize_completions()" method, also in Item, similar to finalize_rruleset() or finalize_jobs() that would, based on @f and &f entries, do the requisite updates for @s, @r, @+, @-, @r and @o before finalize_rruleset and finalize_jobs are called. The resulting instance of Item would then be ready to be submitted to update_item.

## 25-08-12 Finish

### Goals

```
[+-]M/Np N: int frequency, Mp M int, p in d, w, m, y
```

b
E.g., +3/2w => 3 or more (+) completions every 2 weeks

Use beg_hour and end_hour from config to set period available in each day. Given the @s scheduled datetime, the relevant period begins at the beginning of the current period. E.g., for the `+3/2w` example, the first period would begin at scheduled datetime and extend until end_hour on the Sunday of the following week. Subsequent periods would start at beg_hour on Monday and end at end_hour on the Sunday of the 2nd week.

### record completion

- Record completions in a completions table
- Work out @o or @r - not both
-
- finished: urgency status -> finished

- get datetime, default now with prompt to modify

- if goal, record completion

  - get goal for period, num completions and num remaining
  - get seconds in period
  - get goal for period
  - compare goal / period seconds to
    - remaining / remaining seconds
    - or done / seconds used

- neither @r nor @o: add completion, status finished
- @r: add completion (work out @+ issues)
  - if this is the last instance, status -> finished, return
  - set @s to next instance
-

## 2025-08-10 Details

- Add Completions table: id, record_id, completion (int timestamp)
- Commands for detail view:
  - E Edit
  - C Edit Copy
  - D Delete (instance/remaining/item if repeating)
  - F Finish (tasks only)
  - P Toggle Pinned
  - S Schedule new
  - R Reschedule
  - T Touch (modified timestamp)
  - ^R Show repetitions
  - ^C Show Completions (tasks only)

## 2025-08-08

It remains to add tags to the events and tasks which, in both cases, link the tag to the relevant record id.

Here is the setup in controller for tag indexing

```python
  def set_afill(self, details: list, method: str):
      new_afill = 1 if len(details) <= 26 else 2 if len(details) <= 676 else 3
      if new_afill != self.afill:
          old_afill = self.afill
          self.afill = new_afill
```

```python
def decimal_to_base26(decimal_num):
    """
    Convert a decimal number to its equivalent base-26 string.

    Args:
        decimal_num (int): The decimal number to convert.

    Returns:
        str: The base-26 representation where 'a' = 0, 'b' = 1, ..., 'z' = 25.
    """
    if decimal_num < 0:
        raise ValueError("Decimal number must be non-negative.")

    if decimal_num == 0:
        return "a"  # Special case for zero

    base26 = ""
    while decimal_num > 0:
        digit = decimal_num % 26
        base26 = chr(digit + ord("a")) + base26  # Map digit to 'a'-'z'
        decimal_num //= 26

    return base26
```

```python
def indx_to_tag(indx: int, fill: int = 1):
    """
    Convert an index to a base-26 tag.
    """
    return decimal_to_base26(indx).rjust(fill, "a")
```

Then in, e.g., get_next (one of the views), this setup:

```python
...
    events = self.db_manager.get_next_instances()
...
    self.set_afill(events, "get_next")
    self.list_tag_to_id.setdefault("next", {})
...
    index = 0
    tag = indx_to_tag(indx, self.afill)
```

and then repeatedly as records are added:

```python
...
    tag = indx_to_tag(indx, self.afill)
    self.list_tag_to_id["next"][tag] = event_id
    display.append(f"  [dim]{tag}[/dim]  {event_str}")
    indx += 1
```

Is there a good way to encapsulate the last, recurrent bit, in a method?

```python
def add_tag(self, view: str, indx: int, id: int) -> Tuple[str, indx]:
    tag = indx_to_tag(indx, self.afill)
    tag_fmt = f"[dim]{tag}[/dim]"
    self.list_tag_to_id[view][tag] = id
    indx += 1
    return tag_fmt, indx
```

Then, for example,

```python
        for record_id, days_remaining, subject in begin_records:
            tag_fmt, indx = add_tag("event", indx)
            events_by_date[today].append(
                (   "f{tag_fmt}",
                    f"[{BEGIN_COLOR}]+{days_remaining}⮕ [/{BEGIN_COLOR}]",
                    f"[{BEGIN_COLOR}]{subject}[/{BEGIN_COLOR}]",
                    record_id,
                )
            )
```

## 2025-08-04 goals and friends

1. goals: `@o 3/w`
2. chores: `@o ~11d`
   arg again is timedelta string preceded by "~". Learn by experience.
3. do-overs: `@o 11d`
   arg is timedelta string, set start to now + timedelta on completion.

If "/" then 1 elif "~" then 2 else 3

### Goals

config:

- `begin_hour = 8`
- `end_hour = 20`

With these defaults, 20 - 8 = 12 hours would be available each day for goal completions so that at 09:00, 1 available hour of 12 would have passed and at 20:00, all 12 available hours would have passed. The assumption is that these same hours will be available each day of the week and each month day of the month. E.g.,

`@o <freq: int>/<period>`
Allowed periods:

- `d`: day (current period is today)
- `w`: week (current period is the current week: MO = 0, TU = 1, ..., SU = 6)
- m: month (current period is the current month)

Data:

- `c`: completions this period
- `f`: fraction of period currently passed, e.g.:

  - for day:
    - at 08:42, `f = (8-8)/12 = 0.0`
    - at 14:37, `f = (14-8)/12 = 0.5`
    - at 20:15, `f = (20-8)/12 = 1`
  - for week, e.g, on WE (day 2) at 14:37, `f = (2 * 12 + 6) / (7 * 12) = 15/42 = 0.357`
  - for month, e.g., on 3/27 at 14:37, `f = (26 * 12 + 6) / (31 * 12) = 318/372 = 0.855`
  - More generally when `d` of `D` days have passed in the relevant period and `h` is the current hour:
    `f = (d * (end_hour - begin_hour) + min(max(h - begin_hour, 0), end_hour - begin_hour) / (D * (end_hour - begin_hour))`

- `g`: completions goal for period
- `h`: average of completions for previous periods

## The path to successful goal completion

Since success requires satisfying the inequality `c >= f * g` as `f` reaches one, `gp = f * g` can be regarded as the path to success. Accordingly, `dev = 1 - c / (f * g)`, is a normalized measure of how bad things are, `dev = 1` when `c = 0` being the worst, `dev = 0` corresponding to being on the path when `c = f * g` and `dev < 0` to being above the path when `c > f \* g.

Using `dev` we can color goals in the same way as urgency where negative values get the same "cool" color and positive values get hotter colors approaching one.

### Chores - learn from experience

From config, `old_history_weight = 3`
From entry: `@s 2025-08-3 13h` and `@o ~11d4h`

- previous completion: `@s - @o`

From this completion at `done = 2025-08-03 22h`

We get the new average interval to replace `@o`:
`(weight * old_interval + new interval)/(weight + 1)`
`@O = (3 * @o + (@o + done - @s)/4`
`@O = @o + (done - @s)/4`

and the new due to replace `@s`
`@S = done + @O`

From config, with `history_weight = 3`, `@o ~11d4h`, `@s 2025-07-23 09:00` and completion at `2025-08-03 22:00`, it follows that the last completion was at `completion - 11d4h = 2025-07-23 09:00`
interval since the last completion is `11d4h +`:

- the most recent interval = completion - @s =
  11d46800s
- the new average interval = (3 \* 11d4h + 11d46800s)/4 =
  11d22500s
- new @s = 20

11d4h + @s -

## 2025-08-03

More thinking. What about an --agenda option for tklr that would display prepared output and then enter a loop waiting for further commands?

The output would consist of two sections, one for events and the other for tasks listed by urgency. The events would come from a events list ordered by datetime and grouped by day starting from now and extending forward to include the next 14 days with events. The tasks would come from the list of urgency tasks ordered by urgency (desc).

Illustrative content for the two sections:

>

    ```
    Events (showing page n of N)
    Wed July 30 (Today)
      a  12-2p  Lunch with Burk
      b   3-4p  Discussion group
      c  +5 >   Front door refinish
      d   !     Saturday ride
    Thu July 31 (Tomorrow)
      c  8a-5p   Sunroom power wash
    ...
    Tasks (showing page m of M)
      a  91  multiple rdates with priority 5
      b  89  create plan [dog house 1/8/0]
      c  86  once more when complete
      d  ❎ 𐄂 ☒
      e  ✅ ✔ ☑
      f  ⬜ ☐ ☐
    ...

I ? Help

````

If all events and tasks will fit in the available space then the "(showing page ...)" would not be displayed. Otherwise events and tasks would each be split into pages with the goal being to have the events and tasks sections to be roughly equal in length.

The Help display, activated by pressing "?":

- _tags_ are lower case letter(s) that begin each
  record.
- Press e (for events) or t (for tasks) and then
  the key(s) corresponding to the tag to show
  details for the item with further options.
- Press e (for events) or t (for tasks) and then
  > (next) or < (previous) to change pages.

The tags are consecutive "base 26 numbers" using a, b, ... z for 0, ... When displaying details for an item, the entire terminal would be used.

1. Create header for events and append to output
2. get events for (first) 3 days
3. get begins and drafts
   if beings or drafts:
   the first day is "today", append begins and drafts to today rows
   in this case there will be no more than 3 days
   else:
   create "today", insert begins and drafts
   in this case there will be no more than 4 days

4. Append days (as many as 4) to output
5. Create header for task urgency list and append to output
6.

7. Determine the number of lines available in the display and then count the lines required to:
   a. Display a header plus the first two days from the events list including begins and drafts in "today"
   b. Display a header plus as many lines from the task urgency

I have this method to collect records for a relevant period. I would like another method that would limit the records to those with itemtype "\*" and, perhaps in separate method, group the results by date and, within date, by time.

```python
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

````

## 2025-07-29 Agenda

### UI view with scrolling

#### how many rows?

Maybe target 15 for scheduled (begins, drafts, events) and 15 for tasks:

- scheduled: Use `get_events_for_period` with now and now + 14d to get events ending after now and starting before 21 days from now. Take the first "num_events" from list for display.
  - Show 3 days at a time on a page with, say, 15 rows using scrolling if necessary to show all 3 days. This would allow for 3 day headings and 12 events, begins and drafts with out scrolling.
  - And then as many as 6 subsequent pages to show the subsequent groups of days:
    page 1: days 1-3, page 2: days 3-5, ..., page 6: days 11-14
    so that pages always overlap by 1 day.
  - Tags refresh for each page.
  - To open event tag "a", press "e" and then "a"
- tasks: Use new method to retrieve rows corresponding to urgency table records ordered by urgency (DESC). Details for task should show urgency computation (dict of weights?)

#### event rows

- since only events, type character not necessary
- maybe color begin, draft and all day items or put char in the time column?
- maybe only show tags/allow selection when expanded?

#### task rows

### Events (press E to toggle expansion of this section)

- Tue July 29 (Today) like today in etm but with tags and only events
  - all day events
  - events for the _REST_ of today
  - begin warnings
  - drafts
- Wed July 30 (Tomorrow) 2nd day with events
- Thu July 31 3rd day with events

### Tasks (press T to toggle expansion of this section)

- tasks ordered by urgency
