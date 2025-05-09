<table>
  <tr>
    <td>
  <h1>tklr</h1>
      Short for "Task Lister" but pronounced "Tickler" -
      a task manager that adopts TaskWarrior's urgency approach to ranking tasks but supports the entry format, component jobs, datetime parsing and recurrence features of <strong>etm</strong>.</p>
  <p>Make the most of your time!</p>
      <p></p>
    </td>
    <td style="width: 240px; vertical-align: top;">
      <img src="https://raw.githubusercontent.com/dagraham/tklr-dgraham/master/tklr_logo.avif" alt="tklr" title="Tklr" width="240px" />
      <!-- <img src="mouse_short_bkgrnd.avif" alt="tklr" title="Tklr" width="180px" /> -->
    </td>

  </tr>
</table>

Requires: Python, SQLite3, DateUtil and Textual.

💬 Join the conversation on the [Discussions tab](https://github.com/dagraham/tklr-dgraham/discussions)

_Preliminary and incomplete version._ This notice will be removed when the code is ready for use.

## Task attributes

Generally the same format as _etm_ for a task entry but without the beginning item type character: the name of the task, followed by a list of @ and & delineated attributes. The attributes are separated by spaces and include the following:

- @b begin:timedelta requires @s (task status = postponed before @s - @b then available)
- @c context:str (home, shop, work, ...) alternatives specified in config.
  As with TW, specifying a context would limit the list display to tasks with that context.
- @d due:datetime -
- @e estimate:timedelta estimated time required for completion

    a. Perhaps a "quick" command to order tasks by extent, shortest first? Someway of taking advantage of having, say 15 minutes, before a meeting?
    b. Maybe a command to limit the list display to tasks for which the estimated completion times add up to less than a specified time?
    c. Should due urgency be adjusted for the estimated time?

- @f finished:datetime
- @i importance:[N)ext, H)igh, M)edium, L)low, S)omeday] numeric values in config (corresponds to next (tag) and priority in TW)
- @j job (can be used multiple times - examples below)
- @n note:str
- @p project:str
- @r rrule - requires @s (as implemented in _etm_)
- @s scheduled:datetime - a date or datetime (corresponds to due date in TW)
- @t tag:str (can be used multiple times)
- @u until:timedelta - requires @s (task status = deleted after @s + @u if pending before)
- @x deleted:d/noteatetime

- The (unique) id for a task and its _created_ and (last) _modified_ dates are maintained internally.

## Task status characters and meaning

- -) Available (not waiting, finished, postponed or deleted - corresponds to pending in TW)
- *) Available and now - modified <= 1 week (modified within the last week - corresponds to current in TW)
- D) Deleted (has an @d entry or @s and @u entries with @s + @u <= now)
- F) Finished (task with an @f entry or job with an &f entry)
- P) Postponed (has @b and @s entries and @s - @b is in the future - corresponds to waiting in TW)
- W) Waiting (has one or more unfinished prerequisites - corresponds to blocked in TW)

## Repeating tasks

The @r entry is a _rrule_ (recurrence rule) as implemented in _etm_. A copy of the task is created in the Instances table with the id of parent task used as the task_id, the next occurrence of the task used for @s, the current datetime for the _created_ and _modified_ datetimes and with the @r entry removed. This instance of the recurring task is then treated as a normal task with a scheduled date and time.

If and when an instance is completed or the single instance deleted and the recurrence rule in the parent task calls for another instance, this process is repeated.

## Tasks with component jobs

This is a simplification of the current implementation in _etm_. __The need to manually enter job ids and prerequisites has been eliminated by using the position of the job in the sequence and its indentation level.__

A task with @j (job) entries forms a group of related implied tasks, one for each @j entry. The prerequisites for a job, if any, are

Here are some examples of tasks with jobs. In each case "input" gives the multiline task as it would be entered. What follows are the results of processing by _tklr_. The list of jobs adds an id, "i" for each job, just the jobs position in the list starting from 0, and an integer indention level, "node", again starting from 0.   Using the "i" (id) elements from the list of "jobs", "prereqs" gives the prerequisites for each job, if any, using the "i" entries of the relevant jobs. Similarly "available" gives the ids of jobs that are available for completion, i.e., jobs without unfinished prerequisites, "waiting"  gives the ids of the jobs that are not available because of unfinished prerequisites and "finished" give the ids of the jobs that have been finished.  

### jobs without prerequisites

```python
input:
- jobs without prerequisites @d No prerequisites for any job
    @j A
    @j B
    @j C


# Computed from input:
jobs:
  {'j': 'A', 'node': 0, 'i': 0})
  {'j': 'B', 'node': 0, 'i': 1})
  {'j': 'C', 'node': 0, 'i': 2})
prereqs
available = {0, 1, 2}
waiting = {}
finished = {}
```

### each job depends on the following jobs

```python
input:
- jobs without prerequisites @d No prerequisites for any job
    @j A
    @j B
    @j C


# Computed from input:
jobs:
  {'j': 'A', 'node': 0, 'i': 0})
  {'j': 'B', 'node': 0, 'i': 1})
  {'j': 'C', 'node': 0, 'i': 2})
prereqs
available = {0, 1, 2}
waiting = {}
finished = {}
```

### more complex prerequisites - make a dog house

```python
input:
- dog house @s 2025-05-15
    @j paint &c shop
    @j   sand &c shop
    @j     assemble &c shop
    @j       cut pieces &c shop
    @j          get wood &c Lowes
    @j       get hardware &c Lowes
    @j   get paint &c Lowes


# Computed from input:
jobs:
  {'j': 'paint', 'node': 0, 'c': 'shop', 'i': 0})
  {'j': 'sand', 'node': 1, 'c': 'shop', 'i': 1})
  {'j': 'assemble', 'node': 2, 'c': 'shop', 'i': 2})
  {'j': 'cut pieces', 'node': 3, 'c': 'shop', 'i': 3})
  {'j': 'get wood', 'node': 4, 'c': 'Lowes', 'i': 4})
  {'j': 'get hardware', 'node': 3, 'c': 'Lowes', 'i': 5})
  {'j': 'get paint', 'node': 1, 'c': 'Lowes', 'i': 6})
prereqs
  0: {1, 2, 3, 4, 5, 6}
  1: {2, 3, 4, 5}
  2: {3, 4, 5}
  3: {4}
available = {4, 5, 6}
waiting = {0, 1, 2, 3}
finished = {}
```

Note that the outline structure incorporates _backward induction_ - what must be done last is considered first. When will "dog house" be done? When "paint" is completed. What has to be done before "paint"? The jobs "sand" and "get paint". And so forth. Also note the handy role of _context_.

### more complex prerequisites - dog house with shared jobs

Here two jobs are added, "go to Lowes" and "create plan and parts list", which are both prerequisites for the jobs "get wood", "get hardware" and "get paint". Since the latter three jobs are on different branches, the "lowes" and "plan" jobs will need to be added to each of the three branches. To do this without creating copies of the jobs, labels will be created the first time the jobs are inserted using "&l" and then the label will be used subsequently to represent the same job.

```python
input:
- dog house @s 2025-05-15
    @j paint &c shop
    @j   sand &c shop
    @j     assemble &c shop
    @j       cut pieces &c shop
    @j          get wood &c Lowes
    @j            go to Lowes &l lowes &c errands
    @j            create plan &l plan
    @j       get hardware &c Lowes
    @j         lowes
    @j         plan
    @j   get paint &c Lowes
    @j     lowes
    @j     plan


# Computed from input:
jobs:
  {'j': 'paint', 'node': 0, 'c': 'shop', 'i': 0})
  {'j': 'sand', 'node': 1, 'c': 'shop', 'i': 1})
  {'j': 'assemble', 'node': 2, 'c': 'shop', 'i': 2})
  {'j': 'cut pieces', 'node': 3, 'c': 'shop', 'i': 3})
  {'j': 'get wood', 'node': 4, 'c': 'Lowes', 'i': 4})
  {'j': 'go to Lowes', 'node': 5, 'c': 'errands', 'i': 5})
  {'j': 'create plan', 'node': 5, 'i': 6})
  {'j': 'get hardware', 'node': 3, 'c': 'Lowes', 'i': 7})
  {'j': 'go to Lowes', 'node': 4, 'c': 'errands', 'i': 5})
  {'j': 'create plan', 'node': 4, 'i': 6})
  {'j': 'get paint', 'node': 1, 'c': 'Lowes', 'i': 8})
  {'j': 'go to Lowes', 'node': 2, 'c': 'errands', 'i': 5})
  {'j': 'create plan', 'node': 2, 'i': 6})
prereqs
  0: {1, 2, 3, 4, 5, 6, 7, 8}
  1: {2, 3, 4, 5, 6, 7}
  2: {3, 4, 5, 6, 7}
  3: {4, 5, 6}
  4: {5, 6}
  7: {5, 6}
  8: {5, 6}
available = {5, 6}
waiting = {0, 1, 2, 3, 4, 7, 8}
finished = {}
```

### more complex prerequisites - dog house with shared jobs and completions

Here the 2 shared jobs "lowes" and "plan" have been finished and the 3 lowes jobs "get wood", "get hardware" and "get paint" have thus become available.

```python
input:
- dog house @s 2025-05-15
    @j paint &c shop
    @j   sand &c shop
    @j     assemble &c shop
    @j       cut pieces &c shop
    @j          get wood &c Lowes
    @j            go to Lowes &l lowes &c errands &f 2025-03-26 4:00pm
    @j            create plan &l plan &f 2025-03-24 2:00pm
    @j       get hardware &c Lowes
    @j         lowes
    @j         plan
    @j   get paint &c Lowes
    @j     lowes
    @j     plan


# Computed from input:
TODO: do_completion() -> implement
jobs:
  {'j': 'paint', 'node': 0, 'c': 'shop', 'i': 0})
  {'j': 'sand', 'node': 1, 'c': 'shop', 'i': 1})
  {'j': 'assemble', 'node': 2, 'c': 'shop', 'i': 2})
  {'j': 'cut pieces', 'node': 3, 'c': 'shop', 'i': 3})
  {'j': 'get wood', 'node': 4, 'c': 'Lowes', 'i': 4})
  {'j': 'go to Lowes', 'node': 5, 'c': 'errands', 'f': '2025-03-26 4:00pm', 'i': 5})
  {'j': 'create plan', 'node': 5, 'f': '2025-03-24 2:00pm', 'i': 6})
  {'j': 'get hardware', 'node': 3, 'c': 'Lowes', 'i': 7})
  {'j': 'go to Lowes', 'node': 4, 'c': 'errands', 'f': '2025-03-26 4:00pm', 'i': 5})
  {'j': 'create plan', 'node': 4, 'f': '2025-03-24 2:00pm', 'i': 6})
  {'j': 'get paint', 'node': 1, 'c': 'Lowes', 'i': 8})
  {'j': 'go to Lowes', 'node': 2, 'c': 'errands', 'f': '2025-03-26 4:00pm', 'i': 5})
  {'j': 'create plan', 'node': 2, 'f': '2025-03-24 2:00pm', 'i': 6})
prereqs
  0: {1, 2, 3, 4, 7, 8}
  1: {2, 3, 4, 7}
  2: {3, 4, 7}
  3: {4}
available = {8, 4, 7}
waiting = {0, 1, 2, 3}
finished = {5, 6}
```

Note that the two available jobs, "cut pieces" and "get paint", would each be "blocking" since they are prerequisites for other jobs and would thus get the associated urgency.blocking points.

My idea is that available jobs and only available jobs should also get any relevant urgency points for "next" and "due". Furthermore, since jobs can have "&s" timedelta entries so that the scheduled (TW due) date for a job would actually be @s - &s, the urgency.due points should be calculated based on this adjusted scheduled date. Reactions?

By way of contrast, a list of jobs with the same zero indention level would be treated as a list of independent tasks since none have prerequisites.

## Dates and times

When an `@s` scheduled entry specifies a date without a time, i.e., a date instead of a datetime, the interpretation is that the task is due sometime on that day. Specifically, it is not due until `00:00:00` on that day and not past due until `00:00:00` on the following day. The interpretation of `@b` and `@u` in this circumstance is similar. For example, if `@s 2025-04-06` is specified with `@b 3d` and `@u 2d` then the task status would change from waiting to pending at `2025-04-03 00:00:00` and, if not completed, to deleted at `2025-04-09 00:00:00`.

## Recurrence

### @r and, by requirement, @s are given

When an item is specified with an `@r` entry, an `@s` entry is required and is used as the `DTSTART` entry in the recurrence rule. E.g.,

  ```python
  * datetime repeating @s 2024-08-07 14:00 @r d &i 2
  ```

  is serialized (stored) as

  ```python
    {
        "itemtype": "*",
        "subject": "datetime repeating",
        "rruleset": "DTSTART:20240807T140000\nRRULE:FREQ=DAILY;INTERVAL=2",
    }
  ```

__Note__: The datetimes generated by the rrulestr correspond to datetimes matching the specification of `@r` which  occur __on or after__ the datetime specified by `@s`. The datetime corresponding to `@s` itself will only be generated if it matches the specification of `@r`.

### @s is given but not @r

On the other hand, if an `@s` entry is specified, but `@r` is not, then the `@s` entry is stored as an `RDATE` in the recurrence rule. E.g.,

  ```python
  * datetime only @s 2024-08-07 14:00 @e 1h30m
  ```

  is serialized (stored) as

  ```python
  {
    "itemtype": "*",
    "subject": "datetime only",
    "e": 5400,
    "rruleset": "RDATE:20240807T140000"
  }
  ```

The datetime corresponding to `@s` itself is, of course, generated in this case.

### @+ is specified, with or without @r

When `@s` is specified, an `@+` entry can be used to specify one or more, comma separated datetimes.  When `@r` is given, these datetimes are added to those generated by the `@r` specification. Otherwise, they are added to the datetime specified by `@s`. E.g.,   is a special case. It is used to specify a datetime that is relative to the current datetime. E.g.,

  ```python
  * rdates @s 2024-08-07 14:00 @+ 2024-08-09 21:00 
  ```

  would be serialized (stored) as

  ```python
  {
    "itemtype": "*",
    "subject": "rdates",
    "rruleset": "RDATE:20240807T140000, 20240809T210000"
  }
  ```

This option is particularly useful for irregular recurrences such as annual doctor visits. After the initial visit, subsequent visits can simply be added to the `@+` entry of the existing event once the new appointment is made.

__Note__: Without `@r`, the `@s` datetime is included in the datetimes generated but with `@r`, it is only used to set the beginning of the recurrence and otherwise ignored.

### Timezone considerations

[[timezones.md]]

When a datetime is specified, the timezone is assumed to be the local timezone. The datetime is converted to UTC for storage in the database. When a datetime is displayed, it is converted back to the local timezone.

This would work perfectly but for _recurrence_ and _daylight savings time_. The recurrence rules are stored in UTC and the datetimes generated by the rules are also in UTC. When these datetimes are displayed, they are converted to the local timezone.  

```python
- fall back @s 2024-11-01 10:00 EST  @r d &i 1 &c 4
```

```python
rruleset_str = 'DTSTART:20241101T140000\nRRULE:FREQ=DAILY;INTERVAL=1;COUNT=4'
item.entry = '- fall back @s 2024-11-01 10:00 EST  @r d &i 1 &c 4'
{
  "itemtype": "-",
  "subject": "fall back",
  "rruleset": "DTSTART:20241101T140000\nRRULE:FREQ=DAILY;INTERVAL=1;COUNT=4"
}
  Fri 2024-11-01 10:00 EDT -0400
  Sat 2024-11-02 10:00 EDT -0400
  Sun 2024-11-03 09:00 EST -0500
  Mon 2024-11-04 09:00 EST -0500
```

## configuration

```yaml
# cfg.yaml - variables and default values

task.contexts: 
  - errands 
  - home
  - shop
  - work

datetime.ambiguous.day_first: false
datetime.ambiguous.year_first: true 
# for parsing ambiguous dates

datetime.ampm: false 
# 12 hour clock if true else 24 hour clock

urgency.current: 4.0 
# now - modified <= 1 week (modified within the last week)

urgency.blocking: 8.0 
# is pending and a prerequisite for another job

urgency.age: 2.0 # coefficient for age
urgency.scheduled: 12.0 # past scheduled
urgency.due: 16.0 # past due or near due date
urgency.importance.next: 15.0 # next 
urgency.importance.high: 6.0 # high 
urgency.importance.medium: 2.0 # medium 
urgency.importance.low: -2.0 # low 
urgency.importance.someday: -6.0 # someday 
urgency.note: 1.0 # has a note
urgency.project: 1.0 # is assigned to a project

urgency.tags: 1.0 
# each tag (other than "next") up to a maximum of 3 
```

## urgency

As in TaskWarrior the most important urgency components are (1) having a "next" tag which gets an urgency component of 15 and (2) having a due date which gets a maximum urgency of 12. The intent seems to be to have the "next" tasks always at the top of the default (next) list with other pending tasks sorted by their urgency. This places unfinished tasks with due dates falling on or before the current date near the top of the default "next" list.  

### due

For tasks with an `@d` due datetime, the contribution of due to the urgency of the task is calculated as follows:

```python
def urgency_due(due: datetime) -> float:
    """
    This function calculates the urgency coefficient for a task based
    on its due datetime relative to the current datetime and returns 
    a float value between 0.2 when (due >= now + 14 days) and 1.0 when
    (due <= now - 7 days). This coefficient is then multiplied by the 
    urgency.due.coefficient (12.0) to get the due contribution to the
    overall urgency of the task.
    """
    if not due or not isinstance(due, datetime):
        return 0.0

    now = datetime.now()

    days_past = (now - due).total_seconds() / 86400.0
    if days_past >= 7.0:
        return 1.0  # < 1 wk ago
    elif days_past >= -14.0:
        return ((days_past + 14.0) * 0.8 / 21.0) + 0.2
    else:
        return 0.2  # > 2 wks
```

Note that the 14 days, the 7 days and the 0.2 - 1.0 range are hard coded in TaskWarrior - the only user configuration variable is the urgency.due.coefficient (12.0). Here is the range of values when due differs from now by an integer number of days between -7 and +14:

```python
Today: 2025-04-06
days  due date    c     12c
 -7  2025-03-30  1.00  12.00
 -6  2025-03-31  0.96  11.54
 -5  2025-04-01  0.92  11.09
 -4  2025-04-02  0.89  10.63
 -3  2025-04-03  0.85  10.17
 -2  2025-04-04  0.81   9.71
 -1  2025-04-05  0.77   9.26
  0  2025-04-06  0.73   8.80
  1  2025-04-07  0.70   8.34
  2  2025-04-08  0.66   7.89
  3  2025-04-09  0.62   7.43
  4  2025-04-10  0.58   6.97
  5  2025-04-11  0.54   6.51
  6  2025-04-12  0.50   6.06
  7  2025-04-13  0.47   5.60
  8  2025-04-14  0.43   5.14
  9  2025-04-15  0.39   4.69
 10  2025-04-16  0.35   4.23
 11  2025-04-17  0.31   3.77
 12  2025-04-18  0.28   3.31
 13  2025-04-19  0.24   2.86
 14  2025-04-20  0.20   2.40
```

### age

The contribution of age to the urgency of the task is calculated as follows:

```python
def urgency_age(created:datetime) -> float:
    """
    This function calculates the urgency coefficient for a task based
    on its age relative to the current datetime and returns a float
    value between 0.0 (when created = now) and 1.0 (when created =
    now - 365 days). This coefficient is then multiplied by the 
    urgency.age.coefficient (2.0) to get the age contribution to the
    overall urgency of the task.
    """
    if not created or not isinstance(created, datetime):
        return 0.0

    days_old = (now - created).total_seconds() / 86400.0
    if days_old >= 365.0:
        return 1.0  # > 365 days old
    elif days_old <= 0.0:
        return 0.0  # created today
    else:
        return days_old / 365.0 
```

## Views

The style for each list view is similar - a table with columns for variables and a row for each listed task. Rows are numbered (base-26) using lower case alphabetic characters where a = 0, ..., z = 25.

Pressing the key or keys corresponding to row number opens a view showing the details for that task and enables keys bound to various commands associated with the displayed task including:

- A) activate
- B) begin
- C) context
- D) delete
- E) edit
- F) finish
- I) importance
- M) refresh modified date (makes the task current for a week)
- P) project
- S) scheduled date
- T) tags
- U) until

### Next - the default view

Tasks are ordered by __urgency__. Columns include

- row number (a, b, c, ...)
- status
- name
- (context)
- (project)
