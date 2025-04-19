# Notes

## item types and status

Three types of reminders are supported, 1) *task*, 2) *event* and 3) *note*.
The type of reminder is indicated by the first character of the subject line, which is one of the following:

- task: `-`
- event: `*`
- note: `%`

*tasks* and their component *jobs* are further characterized by their *status* so that while the recorded item type is `-`, the type that will be displayed in any list of tasks will be the first status code that applies from the following list:

- deleted: "x" - the task or job has been deleted, i.e., has either an `@x` (task) or an `&x` (job) datetime entry.
- finished: "✓" - the task or job has been finished, i.e., has either an `@f` (task) or an `&f` (job) entry.
- postponed: "~" - this is a task with a `@s datetime` entry and `datetime < now`.
- waiting: "+" - this is a job with one or more unfinished prerequisites.
- blocking: "⏹" - this is a job that is a prerequisite for another job.
- active: "!" - this is a task or job that is currently in progress, i.e., has an `@s` (task) or `&s` (job) entry with `datetime < now`.
- available: "-" - a task or job not meeting any of the above criteria.

Note that "⏹" and "-" correspond to tasks and jobs that are **available for completion** - these are the tasks and jobs listed by *urgency* in the default "agenda" view.

When a task or event is repeating, "↻" is appended to the subject.

## Standard Views

### Agenda

This is the "action" view for *tklr*. It lists *relevant* events for the current date and time and tasks and jobs that are available for completion. A *relevant* event is one that occupies part of the reminder of the current date. More formally, an event for which 1) in the `@s scheduled` entry, *scheduled* specifies a datetime object and not a date, 2) `scheduled.date() <= date.today()`, 3) an `@e extent` entry is specified with *extent* a timedelta object and with `extent.total_seconds() > 0` and 4) `scheduled + extent > now`.

Events and tasks are sorted as follows:

1) the event, if any, for which `datetime < now`. I.e., the busy period for the event is currently in progress.

2) tasks and jobs that are available for completion sorted by *urgency* (descending).

3) events, if any, for which `datetime > now` sorted by *datetime* (ascending).

Note that a period could be blocked off for a *sprint* using an *event* with a subject entry corresponding to the task(s) to be completed during the sprint and with `@s` and `@e` entries to block off the relevant period.

### Status History

When the details of a task are displayed, various keybindings are enabled including these which affect the "status" of the task:

Possible status values include:

- active
- inactive (default)
- paused
- completed
- deleted

- A)ctivate: change the status of the task to "active" and if another task is active, change its status to "paused".

## SQLite3 Database

Scheduled datetimes from `@s` entries become part of the record's rrulestr expression in one of two ways:

  1. for records that *have*  an accompanying @r entry, the datetime is stored as the *DTSTART* component, followed by the remaining rrulestr components. E.g.,

    ```python
    * datetime repeating @s 2024-08-07 14:00 @r d &i 2

# becomes

  {
      "itemtype": "*",
      "subject": "datetime repeating",
      "rruleset": "DTSTART:20240807T140000\nRRULE:FREQ=DAILY;INTERVAL=2",
  }
    ```

  1. for records that *do not have* an accompanying @r entry, the datetime is  stored as as the *RDATE* component, E.g.,

    ```python
    * datetime only @s 2024-08-07 14:00 @e 1h30m

# becomes

    {
      "itemtype": "*",
      "subject": "datetime only",
      "e": 5400,
      "rruleset": "RDATE:20240807T140000"
    }
    ```

### Tables

#### Records

- unique_id: int
- created: int (seconds since epoch)
- modified: int (seconds since epoch)
- input: text (string entered by the user)
- output: text (json version of the dictionary containing the parsed data from "input")

- Items
  - id
  - itemtype: text
  - scheduled: int (seconds since epoch)
  - created: int (seconds sinc e epoch)
  - modified: int (seconds since epoch)
  - entry: text
  - hash: text (json)

## examples

### Thanksgiving

input:

```python
* Thanksgiving @s 2010/11/26 @r y &m 11 &w +4TH
```

- Computed from input:

```python
all = ['+4TH'], bad = []
finalizing rruleset using self.parse_ok = True, len(self.rrule_tokens) = 1; len(components) = 0; len(rruleset_str) = 0
finalizing rrule token = ('@r y &m 11 &w +4TH', {'FREQ': 'YEARLY', 'DTSTART': '20101126T000000', 'rm': 'BYMONTH=11', 'rw': 'BYDAY=+4TH'}):  _ = '@r y &m 11 &w +4TH' with rrule_params = {'FREQ': 'YEARLY', 'DTSTART': '20101126T000000', 'rm': 'BYMONTH=11', 'rw': 'BYDAY=+4TH'}
rruleset_str = 'DTSTART:20101126T000000\nRRULE:FREQ=YEARLY;BYMONTH=11;BYDAY=+4TH'
```

- hash:

```python
 {'itemtype': '*', 'subject': 'Thanksgiving', 's': datetime.datetime(2010, 11, 26, 0, 0), 'rruleset': 'DTSTART:20101126T000000\nRRULE:FREQ=YEARLY;BYMONTH=11;BYDAY=+4TH', 'r': '@r y &M 11 &w +4TH  '}
```

### Dog house

input:

```python
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
```

# Computed from input

```python
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

 {'itemtype': '-', 'subject': 'dog house', 's': datetime.datetime(2025, 5, 15, 0, 0), 'j': [{'j': 'paint', 'node': 0, 'c': 'shop', 'i': 0}, {'j': 'sand', 'node': 1, 'c': 'shop', 'i': 1}, {'j': 'assemble', 'node': 2, 'c': 'shop', 'i': 2}, {'j': 'cut pieces', 'node': 3, 'c': 'shop', 'i': 3}, {'j': 'get wood', 'node': 4, 'c': 'Lowes', 'i': 4}, {'j': 'go to Lowes', 'node': 5, 'c': 'errands', 'f': '2025-03-26 4:00pm', 'i': 5}, {'j': 'create plan', 'node': 5, 'f': '2025-03-24 2:00pm', 'i': 6}, {'j': 'get hardware', 'node': 3, 'c': 'Lowes', 'i': 7}, {'j': 'go to Lowes', 'node': 4, 'c': 'errands', 'f': '2025-03-26 4:00pm', 'i': 5}, {'j': 'create plan', 'node': 4, 'f': '2025-03-24 2:00pm', 'i': 6}, {'j': 'get paint', 'node': 1, 'c': 'Lowes', 'i': 8}, {'j': 'go to Lowes', 'node': 2, 'c': 'errands', 'f': '2025-03-26 4:00pm', 'i': 5}, {'j': 'create plan', 'node': 2, 'f': '2025-03-24 2:00pm', 'i': 6}]}
```

# ChatGPT

My plan is to use SQLite3 as a data store with a table for "Items" with columns for

- id: text, unique
- created: int (seconds since epoch)
- modified: int (seconds since epoch)
- input: text
- output: text (json)

The column "input" would contain the string entered by the user and "output" would contain a JSON version of the dictionary containing the parsed data from "input". The column "created" would be the time the item was created and "modified" would be the time the item was last modified.

Here are two examples of input and the corresponding output:

- Thanksgiving:
  - input: "* Thanksgiving @s 2010/11/26 @r y &m 11 &w +4TH"
  - output:

    ```json
      
        "itemtype": "*",
        "subject": "Thanksgiving",
        "s": "2010-11-26T00:00:00",
        "rruleset": "DTSTART:20101126T000000\nRRULE:FREQ=YEARLY;BYMONTH=11;BYDAY=+4TH",
        "r": "@r y &m 11 &w +4TH"
      }
    ```

- Dog house:
  - input:

    ```
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

   ```
  - output: 
    ```json
      {
        "itemtype": "-",
        "subject": "dog house",
        "s": "2025-05-15T00:00:00",
        "j": [
          {"j": "paint", "node": 0, "c": "shop", "i": 0},
          {"j": "sand", "node": 1, "c": "shop", "i": 1},
          {"j": "assemble", "node": 2, "c": "shop", "i": 2},
          {"j": "cut pieces", "node": 3, "c": "shop", "i": 3},
          {"j": "get wood", "node": 4, "c": "Lowes", "i": 4},
          {"j": "go to Lowes", "node": 5, "c": "errands", "f": "2025-03-26T16:00:00", "i": 5},
          {"j": "create plan", "node": 5, "f": "2025-03-24T14:00:00", "i": 6},
          {"j": "get hardware", "node": 3, "c": "Lowes", "i": 7},
          {"j": "go to Lowes", "node": 4, "c": "errands", "f": "", i: 8},
          {"j": "", node: "", c: "", f: "", i: ""},
        ]
      }
    ```
