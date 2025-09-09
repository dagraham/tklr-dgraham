# For ChatGPT

## 20250903 do_f

### do_f

combine do_f and do_completion

- parse token
- add local datetime to self.completions as local time aware
- replace token with formatted datetime?

A test for self.completions having one or more entries

### finalize_completions and finish_without_exdate combined

- parse entry
- @o action
- not @o:
  - undated task

## 20250903 detail commands

In cases requiring input, pressing "escape" cancels.
When canceling an "Edit" in which changes have been made, a confirmation is required.

- Selection (in details)
  - C (copy):
    - Edit (default copy of selected item)
  - D (delete):
    - Confirmation:
      - repeating: Delete t) this instance, s) this and all subsequent instances, i) the item itself, n) nothing? t/s/i/N
      - single instance or none: Delete this item? y/N
  - E (edit):
    - Edit (default selected item)
  - F (finish):
    - Confirmation / datetime (default now)
  - P toggle pinned:
    - no input
  - R (reschedule):
    - Confirmation / datetime (no default)
  - S (schedule new):
    - Confirmation / datetime (no default)
  - T (touch):
    - Confirmation / datetime (default now)
- No selection (possibly outside details)
  - N (new):
    - Edit (default "")

### Edit

- header: 1 line
- message: as many lines as needed, typically 1 - 3
- entry: 12 lines

### Confirmation

- header: 1 line
- message: as many lines as needed, typically 1 - 3
- entry: 1 line

```python
  if key == "E":
      ctrl.edit_item(record_id)
  elif key == "C":
      ctrl.copy_item(record_id)
  elif key == "D":
      ctrl.delete_item(record_id, job_id=job_id)
  elif key == "F":
      if itemtype == "~":
          ctrl.finish_task(record_id, job_id=job_id)
  elif key == "p":
      if itemtype == "~":
          ctrl.toggle_pinned(record_id)
          self._reopen_details(details_host, tag_meta=meta)
  elif key == "P":
      if itemtype == "~":
          ctrl.toggle_pinned(record_id)
  elif key == "S":
      ctrl.schedule_new(record_id)
  elif key == "R":
      yrwk = week_provider() if week_provider else None
      ctrl.reschedule(record_id, context=view_name, yrwk=yrwk)
  elif key == "T":
      ctrl.touch_item(record_id)
  elif key == "ctrl+r":
      ctrl.show_repetitions(record_id)
  # else: ignore unhandled keys

```

## 2025-08-25 do_s()

### original

```python
    def do_s(self, token):
      """
      Initialize the starting values for rruleset.
      self.rdstart_str will be used if there is no recurrence rule
      self.dtstart_str will be used if there is a recurrence rule
      """
        datetime_str = token["token"][2:].strip()
        # ok, dt = do_datetime(datetime_str)
        dt = parse(datetime_str)
        if is_date(dt):
            self.enforce_dates = True
            self.dtstart = dt.strftime("%Y%m%d")
            self.dtstart_str = f"DTSTART;VALUE=DATE:{dt.strftime('%Y%m%d')}"
            self.rdstart_str = f"RDATE;VALUE=DATE:{dt.strftime('%Y%m%d')}"
        else:
            self.dtstart = dt.str bftime("%Y%m%dT%H%M")
            self.dtstart_str = f"DTSTART:{dt.strftime('%Y%m%dT%H%M%S')}"
            self.rdstart_str = f"RDATE:{dt.strftime('%Y%m%dT%H%M%S')}"
        log_msg(f"scheduled date/datetime {self.dtstart_str = }, {self.rdstart_str = }")
        return True, self.dtstart, []
```

### chat version

```python
    def do_s(self, token: dict):
        """
        Parse @s, with timezone controlled *only* by grouped '&z'.
        Cases:
        1) date-only               -> 'YYYYMMDD'
        2) datetime + &z none      -> naive -> 'YYYYMMDDTHHMMSS'
        3) datetime + &z TZ (or no &z -> local) -> aware UTC 'YYYYMMDDTHHMMSSZ'
        """
        try:
            raw = token["token"][2:].strip()  # after '@s '
            if not raw:
                return False, "Missing @s value", []

            # grouped &z (if tokenizer didn’t add 's' yet, fall back to empty list)
            s_groups = self.token_group_map.get("s", [])
            z_val = None
            for k, v in s_groups:
                if k == "z":
                    z_val = (v or "").strip()
                    break

            parsed = parse(raw)
            if parsed is None:
                return False, f"Could not parse '{raw}'", []

            if isinstance(parsed, date) and not isinstance(parsed, datetime):
                # Case 1: date
                compact = self._serialize_date(parsed)
                tz_kind = "date"
                self.dtstart_str = ""  # no DTSTART in pure date mode
            else:
                # Case 2/3: datetime
                if z_val and z_val.lower() == "none":
                    # naive
                    compact = self._serialize_naive_dt(parsed)
                    tz_kind = "naive"
                    self.dtstart_str = f"DTSTART:{compact}"
                else:
                    # aware → use explicit tz if given, else local tz
                    zone = tz.gettz(z_val) if z_val else tz.tzlocal()
                    if zone is None:
                        return False, f"Unknown timezone: {z_val!r}", []
                    compact = self._serialize_aware_dt_as_utc_Z(parsed, zone)
                    tz_kind = "aware"
                    self.dtstart_str = f"DTSTART:{compact}"

            # reflect into token_map
            self.token_map["s"] = compact
            self.s_kind = tz_kind
            self.s_tz = z_val or ""  # empty string means "local"

            # keep the visible @s token text in sync with the serialized compact value
            token["token"] = f"@s {compact} "

            return True, compact, []
        except Exception as e:
            return False, f"Invalid @s value: {e}", []


```

## 2025-08-18 let Item do it

First a question. I don't understand the need for "self.enforce_dates". For reasons already discussed, dates are treated as datetimes corresponding to "00:00:00" hours. Why enforce_dates?

I want to back off and look at the big picture.

For now, implementing finish **completely inside** Item in a way that does not use EXDATE unless absolutely necessary.

Focus on tasks that do not have "@o" entries!

There should be a prompt for the completion datetime with the default, now, already entered. Options: accept as is - press enter, modify and then press enter, cancel - press escape. The entry should be processed one character at a time so that the dateutil.parser.parse interpretation of what's been entered so far is clear. Perhaps the three line interface that will also be used for complete item entry?

The mechanics of processing a "completed" datetime from the user input.

- Let "completion" be a (completed datetime, due datetime or NULL) tuple or None.
- Understand "submit" to mean passing the Item instance to be updated, its record_id and "completion" to the controller update method.

Sequence:

1. if this is a job and more than one job is unfinished, add &f to this job and "submit". Completion will be None, but the Item will have changes in job status in addition to the added &f entry.
2. if there is only one unfinished job, consider the entire project as a task and continue with the following:
3. if there is no @s entry: set itemtype = "x" and submit. The due part of Completion will be NULL.
4. if the method to determine the next two instances returns only one instance: set itemtype = "x" and submit. The due part of completion should be the one instance.

If we get here we have two instances, due and next, and thus @s and either @r, @+ or both. (Recall that we are precluding consideration of an "@o" entry.) Since @s is used as DTSTART for @r, due must either be @s, the first @r instance >= @s or one of the @+ entries.

Suppose, for convenience, that there are no duplicates in @+ for instances generated by @r. Why would there be? An extra step could be used to remove any duplicates if necessary.

It then follows that next must either be from @+ or one of the instances generated from @r > due. 5) if due is in @+, remove it 6) set @s = next and submit. This works for both possibilities:

- if next is in @+, setting @s = next (will not affect @r instances since they were all > next).
- if next came from @r, setting @s = next (will not affect @+ instances since they were all > next).

For example, when a new item is being created and the entry string is empty:

```
item type
Please choose a character from * (event), ~ (task), ...
---
> _
```

Then when "\*" has been entered:

```
subject
The subject of the item. Append an "@" to add an option
---
> *_
```

When the subject and an "@" has been entered:

```
@-key
required: @s (scheduled)
available: @+ (include), @+ (exclude),
   @a (alert), @b (begin), @c (context),
   ...
---
> * my event @_
```

When scheduled is being entered:

```
scheduled
Sat Aug 9, 2025
---
> * my event @s 9_
```

### Thinking about @f finished_datetime

`self.completions`

### project

- if the last task is being finished, then the project itself should be regarded as being finished in the same way that any other task would be finished.
- otherwise, if this is not the last task, then an &f entry will be processed by Item and no completion need be added to the database, just an update to jobs.

### no @s

- add (finished_datetime, None) to completions
- change itemtype to x
- when processed, add the completion to the completions table

### @s, but neither @r, @+ or @o (no repetition or offset)

- add (finished_datetime, None) to completions
- change itemtype to x
- when processed, add the completion to the completions table

### ChatGPT

I think I've gotten things out of order. Instead of implementing finish, the first priority would have been to implement an "add" in ui to parallel the "add" click command. While the interface would be different, the basic idea of 1) get an input string, 2) create an instance of Item using the string, 3) add the resulting item to the database using the add_item method of DatabaseManager and then 4) invoke the populate_dependent_tables method of DatabaseManager.

With "add" implemented, "edit" (called from the details display) should be straightforward - essentially the same as add but start with an existing string and a record_id and then call the update_item method of DatabaseManager instead of add_item.

Here is an example using the entry string for "dog house":

```python
    """^ dog house @s 2025-08-23 @e 3h @b 2w @p 3
    @~ create plan &s 1w &e 1h &r 1 &f 2025-08-18
    @~ go to Lowes &s 1w &e 2h &r 2: 1
    @~ buy lumber &s 1w &r 3: 2
    @~ buy hardware &s 1w &r 4: 2
    @~ buy paint &s 1w &r 5: 2
    @~ cut pieces &s 6d &e 3h &r 6: 3
    @~ assemble &s 4d &e 5h &r 7: 4, 6
    @~ sand &s 3d &e 1h &r 8: 7
    @~ paint &s 2d &e 2h &r 9: 8
    """
```

and the resulting json "jobs" entry in the database

```json
[
  {
    "~": "create plan",
    "s": "1w",
    "e": "1h",
    "i": 1,
    "reqs": [],
    "f": "20250818T000000",
    "prereqs": [],
    "status": "finished",
    "display_subject": "create plan \u220a dog house 1/7/1"
  },
  {
    "~": "go to Lowes",
    "s": "1w",
    "e": "2h",
    "i": 2,
    "reqs": [1],
    "prereqs": [],
    "status": "available",
    "blocking": 7.0,
    "display_subject": "go to Lowes \u220a dog house 1/7/1"
  },
  {
    "~": "buy lumber",
    "s": "1w",
    "i": 3,
    "reqs": [2],
    "prereqs": [1, 2],
    "status": "waiting",
    "display_subject": "buy lumber \u220a dog house 1/7/1"
  },
  {
    "~": "buy hardware",
    "s": "1w",
    "i": 4,
    "reqs": [2],
    "prereqs": [1, 2],
    "status": "waiting",
    "display_subject": "buy hardware \u220a dog house 1/7/1"
  },
  {
    "~": "buy paint",
    "s": "1w",
    "i": 5,
    "reqs": [2],
    "prereqs": [1, 2],
    "status": "waiting",
    "display_subject": "buy paint \u220a dog house 1/7/1"
  },
  {
    "~": "cut pieces",
    "s": "6d",
    "e": "3h",
    "i": 6,
    "reqs": [3],
    "prereqs": [1, 2, 3],
    "status": "waiting",
    "display_subject": "cut pieces \u220a dog house 1/7/1"
  },
  {
    "~": "assemble",
    "s": "4d",
    "e": "5h",
    "i": 7,
    "reqs": [4, 6],
    "prereqs": [1, 2, 3, 4, 6],
    "status": "waiting",
    "display_subject": "assemble \u220a dog house 1/7/1"
  },
  {
    "~": "sand",
    "s": "3d",
    "e": "1h",
    "i": 8,
    "reqs": [7],
    "prereqs": [1, 2, 3, 4, 6, 7],
    "status": "waiting",
    "display_subject": "sand \u220a dog house 1/7/1"
  },
  {
    "~": "paint",
    "s": "2d",
    "e": "2h",
    "i": 9,
    "reqs": [8],
    "prereqs": [1, 2, 3, 4, 6, 7, 8],
    "status": "waiting",
    "display_subject": "paint \u220a dog house 1/7/1"
  }
]
```

Note that the first job, "create plan" included an "&f 2025-08-18" entry and that the result in the "jobs" was to give the status "finished" to this job and to make the requisite adjustments to the status of the other jobs. All this was done by Item. When the "&f 2025-08-18" token was encountered, it was dispatched to "do_complete" (not finish) which handled all the details.

## 2025-08-15 more finished

I had thought that "do_complete()" in Item would simply add an "&f datetime" entry to a job (task in a project) or an "@f datetime" entry to a task and then, when the entry is complete, there would be a new "finalize_completions()" method, also in Item, similar to finalize_rruleset() or finalize_jobs() that would, based on @f and &f entries, do the requisite updates for @s, @r, @+, @-, @r and @o before finalize_rruleset and finalize_jobs are called. The resulting instance of Item would then be ready to be submitted to update_item.

## 25-08-12 Finish

### Goals

Different from events, a goal doesn't go away if ignored. Different from tasks, where the target is to finish the task, perhaps by a specified date. With a goal the target is to record a specified number of completions (or more, or less) within each of the specified periods.

```
[+-]M/Np N: int frequency, Mp M int, p in d, w, m, y
```

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
