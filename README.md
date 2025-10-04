<table>
  <tr>
    <td>
  <h1>tklr</h1>
      The term <em>tickler file</em> originally referred to a file system for reminders which used 12 monthly files and 31 daily files. <em>Tklr</em>, pronounced "tickler", is a digital version that ranks tasks by urgency and generally facilitates the same purpose - discovering what's relevant <b>now</b> quickly and easily. It supports the entry format and projects of <strong>etm</strong>, the datetime parsing and recurrence features of <strong>dateutil</strong> and provides both command line (Click) and graphical user interfaces (Textual).</p>
  <p>Make the most of your time!</p>
      <p></p>
    <td style="width: 25%; vertical-align: middle;">
      <img src="https://raw.githubusercontent.com/dagraham/tklr-dgraham/master/tklr_logo.avif"
           alt="tklr" title="Tklr" style="max-width: 360px; width: 100%; height: auto;" />
    </td>

  </tr>
</table>

Join the conversation on the [Discussions tab](https://github.com/dagraham/tklr-dgraham/discussions)

❌ Preliminary and incomplete. This notice will be removed when the code is ready for general use.

## Overview

_tklr_ began life in 2013 as _etm-qt_ sporting a gui based on _Qt_. The intent was to provide an app supporting GTD (David Allen's Getting Things Done) and exploiting the power of python-dateutil. The name changed to _etmtk_ in 2014 when _Tk_ replaced _Qt_. Development of _etmtk_ continued until 2019 when name changed to _etm-dgraham_, to honor the PyPi naming convention, and the interface changed to a terminal based one based on _prompt_toolkit_. In 2025 the name changed to "tklr", the database to SQLite3 and the interface to Click (CLI) and Textual. Features have changed over the years but the text based interface and basic format of the reminders has changed very little. The goal has always been to be the Swiss Army Knife of tools for managing reminders.

## Reminders

_tklr_ offers a simple way to manage your events, tasks and other reminders.

Rather than filling out fields in a form to create or edit reminders, a simple text-based format is used. Each reminder in _tklr_ begins with a _type character_ followed by the _subject_ of the reminder and then, perhaps, by one or more _@key value_ pairs to specify other attributes of the reminder. Mnemonics are used to make the keys easy to remember, e.g, @s for scheduled datetime, @l for location, @d for description and so forth.

The 4 types of reminders in _tklr_ with their associated type characters:

| type    | char |
| ------- | ---- |
| event   | \*   |
| task    | ~    |
| project | ^    |
| goal    | +    |
| note    | %    |
| draft   | ?    |

### examples

- A _task_ (~) reminder to pick up milk.

        ~ pick up milk

- An _event_ (\*) reminder to have lunch with Ed starting (@s) next Tuesday at 12pm with an extent (@e) of 1 hour and 30 minutes, i.e., lasting from 12pm until 1:30pm.

        * Lunch with Ed @s tue 12p @e 1h30m

- A _note_ (%) reminder of a favorite Churchill quotation with the quote itself as the details (@d).

        % Give me a pig - Churchill @d Dogs look up at
          you. Cats look down at you. Give me a pig - they
          look you in the eye and treat you as an equal.

  The _subject_, "Give me a pig - Churchill" in this example, follows the type character and is meant to be brief - analogous to the subject of an email. The optional _details_ follows the "@d" and is meant to be more expansive - analogous to the body of an email.

- A _project_ (^) reminder to build a dog house with component tasks (@~).

        ^ Build dog house
          @~ pick up materials &r 1 &e 4h
          @~ cut pieces &r 2: 1 &e 3h
          @~ assemble &r 3: 2 &e 2h
          @~ sand &r 4: 3 &e 1h
          @~ paint &r 5: 4 &e 4h

  The "&r X: Y" entries set "X" as the label for the task and the task labeled "Y" as a prerequisite. E.g., "&r 3: 2" establishes "3" as the label for assemble and "2" (cut pieces) as a prerequisite. The "&e _extent_" entries give estimates of the times required to complete the various tasks.

- A _draft_ reminder, **!**: meet Alex for coffee Friday.

        ! Coffee with Alex @s fri @e 1h

  This can be changed to an event when the details are confirmed by replacing the **!** with an **\*** and adding the time to `@s`. This _draft_ will appear highlighted on the current day until you make the changes to complete it.

### Simple repetition

- An appointment (_event_) for a dental exam and cleaning at 2pm on Feb 5 and then again, **@+**, at 9am on Sep 3.

        * dental exam and cleaning @s 2p feb 5 @e 45m @+ 9am Sep 3

- A reminder (_task_) to fill the bird feeders starting Friday of the current week and repeat (do over) thereafter 4 days after the previous completion.

       ~ fill bird feeders @s fri @o 4d

### More complex repetition

- The full flexibility of the superb Python _dateutil_ package is supported. Consider, for example, a reminder for Presidential election day which starts in November, 2020 and repeats every 4 years on the first Tuesday after a Monday in November (a Tuesday whose month day falls between 2 and 8 in the 11th month). In _tklr_, this event would be

-        * Presidential election day @s nov 1 2020 @r y &i 4
            &w TU &m 2, 3, 4, 5, 6, 7, 8 &M 11

## Details

### Dates and times

Suppose it is Monday, September 15 2025 in the US/Eastern timezone. When a datetime is entered it is interpreted _relative_ to the current date, time and timezone. When entering the scheduled datetime for a reminder using `@s`, the following table illustrates how the entries would be interpreted

| @s entry           | scheduled datetime  |
| ------------------ | ------------------- |
| @s wed             | 25-09-17            |
| @s 9a              | 25-09-15 9:00am EST |
| @s 9a fri          | 25-09-19 9:00am EST |
| @s 9a 23 z none    | 25-09-23 9:00am     |
| @s 3p z US/Pacific | 25-09-15 3:00pm PST |
| @s 13h 23 z CET    | 25-09-23 13:00 CET  |
| @s 20h 23 z none   | 25-09-23 20:00      |

Datetimes entered with "z none" and dates are _naive_ - have no timezone information. Datetimes entered with "z TIMEZONE" are interpreted as _aware_ datetimes in TIMEZONE. Datetimes without a "z" entry are also interpreted as _aware_ but in the timezone of the user's computer.

When dates and datetimes are recorded, _aware_ datetimes are first converted to UTC time and then stored with a "Z" appended. E.g., the "25-09-15 3:00pm PST" datetime would be recorded as "20250915T2200Z". Dates and _naive_ datetimes are recorded without conversion and without the trailing "Z". When _aware_ datetimes are displayed to the user, they are first converted to the timezone of the user's computer. Thus the "PST" example would be displayed as scheduled for 6pm today in US/Eastern. Dates and _naive_ datetimes are displayed without change in every timezone.

When an `@s` scheduled entry specifies a date without a time, i.e., a date instead of a datetime, the interpretation is that the task is due sometime on that day. Specifically, it is not due until `00:00` on that day and not past due until `00:00` on the following day. The interpretation of `@b` and `@u` in this circumstance is similar. For example, if `@s 2025-04-06` is specified with `@b 3d` and `@u 2d` then the task status would change from waiting to pending at `2025-04-03 00:00` and, if not completed, to deleted at `2025-04-09 00:00`.

Note that times can only be specified, stored and displayed in hours and minutes - seconds and microseconds are not supported. Internally datetimes are interpreted as having seconds equal to 0.

### Intervals

An interval is just a period of time and is entered in _tklr_ using expressions such as

| entry | period of time          |
| ----- | ----------------------- |
| 2h    | 2 hours                 |
| -2h   | - 2 hours               |
| 1w7d  | 1 week and 7 days       |
| 2h30m | 2 hours and 30 minutes  |
| 1m27s | 1 minute and 27 seconds |

Note that w (weeks), d (days), h (hours), m (minutes) and s (seconds) are the available _units_ for entering _intervals_. Seconds are ignored save for their use in alerts - more on alerts later.

An interval, `I`, can be added to a datetime, `T`, to get a datetime, `T + I`, that will be after `T` if `I > 0` and before `T` if `I < 0`. Similarly, one datetime, `A`, can be subtracted from another, `B`, to get an interval, `I = B - A`, with `I > 0` if `B` is after (greater than) `A` and `I < 0` if `B` is before (less than) `A`.

### Scheduled datetimes and related intervals

For the discussion that follows, it will be assumed that the current date is `2025-10-01` and that `@s 2025-10-21 10a` so that the _scheduled datetime_ for the illustrative reminder is

    @s 2025-10-21 10:00am

#### extent

The entry `@e 2h30m` would set the _extent_ for the reminder to two hours and 30 minutes.

If the reminder were an _event_, this would schedule the "busy time" for the event to _extend_ from 10am until 12:30pm.

For a task, this same entry would indicate that attention to completing the task should begin no later than 10am and that 2 hours and 30 minutes is the _estimate_ of the time required for completion. The period from 10am until 12:30pm is not displayed as a busy time, however, since the task could be begun before or after 10am and could take more or less than 2 hours and 30 minutes to complete. For a task, both `@s` and `@e` are best regarded as _estimates_.

For a project, this same entry would similarly indicate that attention to completing the project should begin no later than 10am and that two hours and 30 minutes is estimated for completion subject to additional times specified in the jobs. A job entry containing `&s 2d &e 3h`, for example, would set the scheduled time for this job to be two days _after_ the `@s` entry for the project and would add three hours to the estimate of total time required for the project.

#### begin

The entry `@b B` where `B` is a _positive_ interval specifies the date on which the datetime `scheduled - B` falls. For the example, adding `@b 1d12h` would set _begin_ to the date corresponding to

      2025-10-21 10am - 1d12h = 2025-10-19 10pm

i.e., to `25-10-19`.

If the reminder is an event, then the agenda view would display an beginby notice for the event beginning on `25-10-19` and continuing on the `25-10-20`. For an _event_ think of this begin notice as a visual alert.

If the reminder is a task, then the task would _not_ appear in the agenda view until `25-10-19`, i.e., it would be hidden before that date.

#### wrap

The entry `@w BEFORE, AFTER`, where `BEFORE` and `AFTER` are _intervals_, can be used to wrap the _scheduled_ datetime of a reminder. Possible entries and the resulting values of BEFORE and AFTER are illustrated below:

| entry      | before | after      |
| ---------- | ------ | ---------- |
| @w 1h, 30m | 1 hour | 30 minutes |
| @w 1h,     | 1 hour | None       |
| @w , 30m   | None   | 30 minutes |

Consider an event with `@s 2025-10-21 10am @e 2h30m`, which starts at 10am and ends at 12:30pm and suppose that it will take an hour to travel to the location of the event and 30 minutes to travel from the event to the next location. The entry `@w 1h, 30m` could be used to indicate these travel periods from 9am until 10am before the event begins and from 12:30pm until 1pm after the event ends.

For a task, consider a situation in which the trash is picked up weekly on Monday mornings sometime between 8am and 10am and you would like a reminder to put the trash at the curb to appear in agenda view beginning at 6pm on Sunday and then disappear if marked completed between 6pm Sunday and 10am Monday or, if not marked completed by 10am Monday, then just disappear until the next Sunday. Here's the reminder to do that:

      ~ trash to curb @s 8a mon @r w @e 15m @w 14h, 2h

This reminder for a _task_ will appear weekly from 6pm Sunday until 10am Monday unless marked completed sometime during that interval. Note that the `@w` entry wraps the _scheduled_ datetime but, unlike the case for an _event_, ignores the _extent_.

#### alert

### Recurrence

#### @r and, by requirement, @s are given

When an item is specified with an `@r` entry, an `@s` entry is required and is used as the `DTSTART` entry in the recurrence rule. E.g.,

```python
* datetime repeating @s 2024-08-07 14:00 @r d &i 2
```

is serialized (stored) as

```python
  {
      "itemtype": "*",
      "subject": "datetime repeating",
      "rruleset": "DTSTART:20240807T1400Z\nRRULE:FREQ=DAILY;INTERVAL=2",
  }
```

**Note**: The datetimes generated by the rrulestr correspond to datetimes matching the specification of `@r` which occur **on or after** the datetime specified by `@s`. The datetime corresponding to `@s` itself will only be generated if it matches the specification of `@r`.

### @s is given but not @r

On the other hand, if an `@s` entry is specified, but `@r` is not, then the `@s` entry is stored as an `RDATE` in the recurrence rule. E.g.,

```python
* datetime only @s 2024-08-07  14:00 @e 1h30m
```

is serialized (stored) as

```python
{
  "itemtype": "*",
  "subject": "datetime only",
  "e": 5400,
  "rruleset": "RDATE:20240807T1400Z"
}
```

The datetime corresponding to `@s` itself is, of course, generated in this case.

### @+ is specified, with or without @r

When `@s` is specified, an `@+` entry can be used to specify one or more, comma separated datetimes. When `@r` is given, these datetimes are added to those generated by the `@r` specification. Otherwise, they are added to the datetime specified by `@s`. E.g., is a special case. It is used to specify a datetime that is relative to the current datetime. E.g.,

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

**Note**: Without `@r`, the `@s` datetime is included in the datetimes generated but with `@r`, it is only used to set the beginning of the recurrence and otherwise ignored.

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

### Urgency

Since urgency values are used ultimately to give an ordinal ranking of tasks, all that matters is the relative values used to compute the urgency scores. Accordingly, all urgency scores are constrained to fall within the interval from -1.0 to 1.0. The default urgency is 0.0 for a task with no urgency components.

There are some situations in which a task will _not_ be displayed in the "urgency list" and there is no need, therefore, to compute its urgency:

- Completed tasks are not displayed.
- Hidden tasks are not displayed. The task is hidden if it has an `@s` entry and an `@b` entry and the date corresponding to `@s - @b` falls sometime after the current date.
- Waiting tasks are not displayed. A task is waiting if it belongs to a project and has unfinished prerequisites.
- Only the first _unfinished_ instance of a repeating task is displayed. Subsequent instances are not displayed.

There is one other circumstance in which urgency need not be computed. When the _pinned_ status of the task is toggled on in the user interface, the task is treated as if the computed urgency were equal to `1.0` without any actual computations.

All other tasks will be displayed and ordered by their computed urgency scores. Many of these computations involve datetimes and/or intervals and it is necessary to understand both are represented by integer numbers of seconds - datetimes by the integer number of seconds _since the epoch_ (1970-01-01 00:00:00 UTC) and intervals by the integer numbers of seconds it spans. E.g., for the datetime "2025-01-01 00:00 UTC" this would be `1735689600` and for the interval "1w" this would be the number of seconds in 1 week, `7*24*60*60 = 604800`. This means that an interval can be subtracted from a datetime to obtain another datetime which is "interval" earlier or added to get a datetime "interval" later. One datetime can also be subtracted from another to get the "interval" between the two, with the sign indicating whether the first is later (positive) or earlier (negative). (Adding datetimes, on the other hand, is meaningless.)

Briefly, here is the essence of this method used to compute the urgency scores using "due" as an example. Here is the relevant section from config.toml with the default values:

```toml
[urgency.due]
# The "due" urgency increases from 0.0 to "max" as now passes from
# due - interval to due.
interval = "1w"
max = 8.0
```

The "due" urgency of a task with an `@s` entry is computed from _now_ (the current datetime), _due_ (the datetime specified by `@s`) and the _interval_ and _max_ settings from _urgency.due_. The computation returns:

- `0.0`
  if `now < due - interval`
- `max * (1.0 - (now - due) / interval)`
  if `due - interval < now <= due`
- `max`
  if `now > due`

For a task without an `@s` entry, the "due" urgency is 0.0.

Other contributions of the task to urgency are computed similarly. Depending on the configuration settings and the characteristics of the task, the value can be either positive or negative or 0.0 when missing the requisite characteristic(s).

Once all the contributions of a task have been computed, they are aggregated into a single urgency value in the following way. The process begins by setting the initial values of variables `Wn = 1.0` and `Wp = 1.0`. Then for each of the urgency contributions, `v`, the value is added to `Wp` if `v > 0` or `abs(v)` is added to `Wn` if `v` negative. Thus either `Wp` or `Wn` is increased by each addition unless `v = 0`. When each contribution has been added, the urgency value of the task is computed as follows:

```python
urgency = (Wp - Wn) / (Wp + Wn)
```

Equivalently, urgency can be regarded as a weighted average of `-1.0` and `1.0` with `Wn/(Wn + Wp)` and `Wp/(Wn + Wp)` as the weights:

```python
urgency = -1.0 * Wn / (Wn + Wp) + 1.0 * Wp / (Wn + Wp) = (Wp - Wn) / (Wn + Wp)
```

Observations from the weighted average perspective and the fact that `Wn >= 1` and `Wp >= 1`:

- `-1.0 < urgency < 1`
- `urgency = 0.0` if and only if `Wn = Wp`
- `urgency` is _always increasing_ in `Wp` and _always decreasing_ in `Wn`
- `urgency` approaches `1.0` as `Wn/Wp` approaches `0.0` - as `Wp` increases relative to `Wn`
- `urgency` approaches `-1.0` as `Wp/Wn` approaches `0.0` - as `Wn` increases relative to `Wp`

Thus positive contributions _always_ increase urgency and negative contributions _always_ decrease urgency. The fact that the urgency derived from contributions is always less than `1.0` means that _pinned_ tasks with `urgency = 1` will always be listed first.

## Getting Started

### Developer Install Guide

This guide walks you through setting up a development environment for `tklr` using [`uv`](https://github.com/astral-sh/uv) and a local virtual environment. Eventually the normal python installation procedures using pip or pipx will be available.

### ✅ Step 1: Clone the repository

This step will create a directory named _tklr-dgrham_ in your current working directory that contains a clone of the github repository for _tklr_.

```bash
git clone https://github.com/dagraham/tklr-dgraham.git
cd tklr-dgraham
```

### ✅ Step 2: Install uv (if needed)

```bash
which uv || curl -LsSf https://astral.sh/uv/install.sh | sh
```

### ✅ Step 3: Create a virtual environment with `uv`

This will create a `.venv/` directory inside your project to hold all the relevant imports.

```bash
uv venv
```

### ✅ Step 4: Install the project in editable mode

```bash
uv pip install -e .
```

### ✅ Step 5: Use the CLI

You have two options for activating the virtual environment for the CLI:

#### ☑️ Option 1: Manual activation (every session)

```bash
source .venv/bin/activate
```

Then you can run:

```bash
tklr --version
tklr add "- test task @s 2025-08-01"
tklr ui
```

To deactivate:

```bash
deactivate
```

#### ☑️ Option 2: Automatic activation with `direnv` (recommended)

##### 1. Install `direnv`

```bash
brew install direnv        # macOS
sudo apt install direnv    # Ubuntu/Debian
```

##### 2. Add the shell hook to your `~/.zshrc` or `~/.bashrc`

```sh
eval "$(direnv hook zsh)"   # or bash
```

Restart your shell or run `source ~/.zshrc`.

##### 3. In the project directory, create a `.envrc` file

```bash
echo 'export PATH="$PWD/.venv/bin:$PATH"' > .envrc
```

##### 4. Allow it

```bash
direnv allow
```

Now every time you `cd` into the project, your environment is activated automatically and, as with the manual option, test your setup with

```bash
tklr --version
tklr add "- test task @s 2025-08-01"
tklr ui
```

You're now ready to develop, test, and run `tklr` locally with full CLI and UI support.

### ✅ Step 6: Updating your repository

To update your local copy of **Tklr** to the latest version:

```bash
# Navigate to your project directory
cd ~/Projects/tklr-dgraham  # adjust this path as needed

# Pull the latest changes from GitHub
git pull origin master

# Reinstall in editable mode (picks up new code and dependencies)
uv pip install -e .
```

### Starting tklr for the first time

**Tklr** needs a _home_ directory to store its files - most importantly these two:

- _config.toml_: An editable file that holds user configuration settings
- _tkrl.db_: An _SQLite3_ database file that holds all the records for events, tasks and other reminders created when using _tklr_

Any directory can be used for _home_. These are the options:

1. If started using the command `tklr --home <path_to_home>` and the directory `<path_to_home>` exists then _tklr_ will use this directory and, if necessary, create the files `config.toml` and `tklr.db` in this directory.
2. If the `--home <path_to_home>` is not passed to _tklr_ then the _home_ will be selected in this order:

   - If the current working directory contains files named `config.toml` and `tklr.db` then it will be used as _home_
   - Else if the environmental variable `TKLR_HOME` is set and specifies a path to an existing directory then it will be used as _home_
   - Else if the environmental variable `XDG_CONFIG_HOME` is set, and specifies a path to an existing directory which contains a directory named `tklr`, then that directory will be used.
   - Else the directory `~/.config/tklr` will be used.

### Configuration

These are the default settings in _config.toml_:

<!-- BEGIN CONFIG -->

```toml
# DO NOT EDIT TITLE
title = "Tklr Configuration"

[ui]
# theme: str = 'dark' | 'light'
theme = "dark"

# ampm: bool = true | false
# Use 12 hour AM/PM when true else 24 hour
ampm = false

# dayfirst and yearfirst settings
# These settings are used to resolve ambiguous date entries involving
# 2-digit components. E.g., the interpretation of the date "12-10-11"
# with the various possible settings for dayfirst and yearfirst:
#
# dayfirst  yearfirst    date     interpretation  standard
# ========  =========  ========   ==============  ========
#   True     True      12-10-11    2012-11-10     Y-D-M ??
#   True     False     12-10-11    2011-10-12     D-M-Y EU
#   False    True      12-10-11    2012-10-11     Y-M-D ISO 8601
#   False    False     12-10-11    2011-12-10     M-D-Y US
#
# The defaults:
#   dayfirst = false
#   yearfirst = true
# correspond to the Y-M-D ISO 8601 standard.

# dayfirst: bool = true | false
dayfirst = false

# yearfirst: bool = true | false
yearfirst = true

[alerts]
# dict[str, str]: character -> command_str.
# E.g., this entry
#   d: '/usr/bin/say -v Alex "[[volm 0.5]] {subject}, {when}"'
# would, on my macbook, invoke the system voice to speak the subject
# of the reminder and the time remaining until the scheduled datetime.
# The character "d" would be associated with this command so that, e.g.,
# the alert entry "@a 30m, 15m: d" would trigger this command 30
# minutes before and again 15 minutes before the scheduled datetime.


# ─── Urgency Configuration ─────────────────────────────────────

[urgency.due]
# The "due" urgency increases from 0.0 to "max" as now passes from
# due - interval to due.
interval = "1w"
max = 8.0

[urgency.pastdue]
# The "pastdue" urgency increases from 0.0 to "max" as now passes
# from due to due + interval.
interval = "2d"
max = 2.0

[urgency.recent]
# The "recent" urgency decreases from "max" to 0.0 as now passes
# from modified to modified + interval.
interval = "2w"
max = 4.0

[urgency.age]
# The "age" urgency  increases from 0.0 to "max" as now increases
# from modified to modified + interval.
interval = "26w"
max = 10.0

[urgency.extent]
# The "@e extent" urgency increases from 0.0 when extent = "0m" to "max"
# when extent >= interval.
interval = "12h"
max = 4.0

[urgency.blocking]
# The "blocking" urgency increases from 0.0 when blocked = 0 to "max"
# when blocked >= count. Blocked is the integer count of tasks in a project for which the given task is an unfinished prerequisite.
count = 3
max = 6.0

[urgency.tags]
# The "tags" urgency increases from 0.0 when tags = 0 to "max" when
# when tags >= count. Tags is the count of "@t" entries given in the task.
count = 3
max = 3.0

[urgency.priority]
# The "priority" urgency corresponds to the value from "1" to "5" of `@p`
# specified in the task. E.g, with "@p 3", the value would correspond to
# the "3" entry below. Absent an entry for "@p", the value would be 0.0.

"1" = -5.0

"2" = 2.0

"3" = 5.0

"4" = 8.0

"5" = 10.0


# In the default settings, a priority of "1" is the only one that yields
# a negative value, `-5`, and thus reduces the urgency of the task.

[urgency.description]
# The "description" urgency equals "max" if the task has an "@d" entry and
# 0.0 otherwise.
max = 2.0

[urgency.project]
# The "project" urgency equals "max" if the task belongs to a project and
# 0.0 otherwise.
max = 3.0
```

<!-- END CONFIG -->

## Keyboard Shortcuts

| Key       | Context         | Action                       |
| --------- | --------------- | ---------------------------- |
| `a` … `z` | Agenda/List     | Show details for tagged item |
| `ctrl+e`  | Details         | Edit selected item           |
| `ctrl+f`  | Details (task)  | Finish task / occurrence     |
| `ctrl+n`  | Anywhere        | Create new item              |
| `ctrl+r`  | Details (recur) | Show repetitions             |
| `ctrl+p`  | Details (task)  | Toggle pin                   |
| `ctrl+t`  | Details         | Touch (update modified time) |
| `escape`  | Any             | Back / Close screen          |
| `?`       | Any             | Show help                    |
