<table>
  <tr>
    <td>
  <h1>tklr</h1>
      The term <em>tickler file</em> originally referred to a file system for reminders which used 12 monthly files and 31 daily files. <em>Tklr</em>, pronounced "tickler", is a digital version that ranks tasks by urgency and generally facilitates the same purpose - discovering what's relevant <b>now</b> quickly and easily. It supports the entry format and project support of <strong>etm</strong>, the datetime parsing and recurrence features of <strong>dateutil</strong> and provides both command line (Click) and graphical user interfaces (Textual).</p>
  <p>Make the most of your time!</p>
      <p></p>
    <td style="width: 25%; vertical-align: middle;">
      <img src="https://raw.githubusercontent.com/dagraham/tklr-dgraham/master/tklr_logo.avif"
           alt="tklr" title="Tklr" style="max-width: 360px; width: 100%; height: auto;" />
    </td>

  </tr>
</table>

💬 Join the conversation on the [Discussions tab](https://github.com/dagraham/tklr-dgraham/discussions)

> [!WARNING] Preliminary and incomplete version. This notice will be removed when the code is ready for general use.

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
| note    | %    |
| draft   | !    |

### examples

- A _task_, **~**: pick up milk.

        ~ pick up milk

- An _event_ reminder, **\***: have lunch with Ed [s]tarting next Tuesday at 12pm with an **e**xtent of 1 hour and 30 minutes, i.e., lasting from 12pm until 1:30pm.

        * Lunch with Ed @s tue 12p @e 1h30m

- A _note_ reminder, **%**: a favorite Churchill quotation that you heard at 2pm today with the quote itself as the **d**escription.

        % Give me a pig - Churchill @s 2p @d Dogs look up at
          you. Cats look down at you. Give me a pig - they
          look you in the eye and treat you as an equal.

  The _subject_, "Give me a pig - Churchill" in this example, follows the type character and is meant to be brief - analogous to the subject of an email. The optional _description_ follows the "@d" and is meant to be more expansive - analogous to the body of an email.

- A _project_ reminder, **^**: build a dog house, with component **@~** tasks.

        ^ Build dog house @~ pick up materials &r 1  @~ cut pieces &r 2: 1
          @~ assemble &r 3: 2 @~ sand &r 4: 3 @~ paint &r 5: 4

  The "&r X: Y" entries set "X" as the label for the task and the task labeled "Y" as a prerequisite. E.g., "&r 3: 2" establishes "3" as the label for assemble and "2" (cut pieces) as a prerequisite.

- A _draft_ reminder, **!**: meet Alex for coffee Friday.

        ! Coffee with Alex @s fri @e 1h

  This can be changed to an event when the details are confirmed by replacing the **!** with an **\*** and adding the time to `@s`. This _draft_ will appear highlighted on the current day until you make the changes to complete it.

### Simple repetition

- An appointment (_event_) for a dental exam and cleaning at 2pm on Feb 5 and then again, **@+**, at 9am on Sep 3.

        * dental exam and cleaning @s 2p feb 5 @e 45m @+ 9am Sep 3

- A reminder (_task_) to fill the bird feeders starting Friday of the current week and repeat thereafter 4 days after the previous completion.

       ~ fill bird feeders @s fri @o 4d

### More complex repetition

- The full flexibility of the superb Python _dateutil_ package is supported. Consider, for example, a reminder for Presidential election day which starts in November, 2020 and repeats every 4 years on the first Tuesday after a Monday in November (a Tuesday whose month day falls between 2 and 8 in the 11th month). In _tklr_, this event would be

-        * Presidential election day @s nov 1 2020 @r y &i 4
            &w TU &m 2, 3, 4, 5, 6, 7, 8 &M 11

## Developer Install Guide

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

✅ You're now ready to develop, test, and run `tklr` locally with full CLI and UI support.

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

## Starting tklr for the first time

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

**Note**: The datetimes generated by the rrulestr correspond to datetimes matching the specification of `@r` which occur **on or after** the datetime specified by `@s`. The datetime corresponding to `@s` itself will only be generated if it matches the specification of `@r`.

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

## Urgency

Since urgency values are used ultimately to give an ordinal ranking of tasks, all that matters is the relative values used to compute the urgency scores. Accordingly, all urgency scores are constrained to fall within the interval from -10.0 to 10.0. The default urgency is 0.0 for a component that is not given.

In these cases a task will not be displayed in the "urgency list" and there is no need, therefore, to compute its urgency:

- The task does not repeat and has been completed or, if it does repeat, the last instance has been completed.
- The task has an `@s` entry and an `@b` entry and the date corresponding to `@s - @b` falls sometime after the current date.
- The task belongs to a project and has unfinished prerequisites.

Additionally, when a task is repeating, only the first unfinished instance will be displayed.

These are the components that potentially contribute to the urgency - default settings in _config.toml_ are in the next section:

- max_interval components:
  - urgency.age: how long since modified - the longer, the greater the urgency:
  - urgency.recent: how long since modified - the more recent, the greater the urgency:
  - urgency.due: how soon is the task due - the sooner, the greater the urgency:
  - urgency.pastdue: how long since the task was due - the longer, the greater the urgency:
  - urgency.extent: how long is the expected completion time - the longer the greater the urgency:
- count components:
  - urgency.blocking: how many tasks are waiting for the completion of this task - the more, the greater the urgency:
  - urgency.tags: how many tags does this task have - the more, the greater the urgency:
- value components:
  - urgency.active: if this task is the unique, active task:
  - urgency.description: if this task has a description:
  - urgency.priority: if this task has a priority setting
  - urgency.project: if this task belongs to a project

For each of the max_interval components, a method is defined that takes the maximum value and interval from the parameters given in config.toml for the component combined with the characteristics of the task and returns a float in the interval \[0.0, 10.0\]. Note that the computed urgency will be at least as great as the default, 0.0. Additionally:

- _recent_ and _age_ are combined to return a single urgency, _recent_age_, which is the greater of the two components
- _due_ and _pastdue_ are combined to return a single urgency, _due_pastdue_, which is the greater of the two components

For both of the count components, a method is defined that takes a maximum value from _config.toml_ and a count from the task and returns a float in [0.0, 10.0]. Again the computed value will be at least as great as the default.

For each of the value components, the provided method simply returns the value for the component from _config.toml_.

Non-negative, _relative weights_ are specified in _config.toml_ for each these urgency components. _Absolute weights_ for each component are then obtained by dividing each of the relative weights by sum of all of the relative weights.

The _task urgency_ is then computed as the weighted average of the component values using the _absolute weights_.

### Urgency settings in _config.toml_

```toml
title = "Tklr Configuration"

[ui]
# theme: str = 'dark' | 'light'
theme = "dark"

# ampm: bool = true | false
ampm = false

# dayfirst: bool = true | false
dayfirst = false

# yearfirst: bool = true | false
yearfirst = true

[alerts]
# dict[str, str]: character -> command_str


[urgency]
# values for item urgency calculation
# all values are floats.

# is this the active task or job?
active = 10.0

# does this task or job have a description?
description = 1.0

# is this a job and thus part of a project?
project = 2.0

# Each of the "max/interval" settings below involves a
# max and an interval over which the contribution ranges
# between the max value and 0.0. In each case, "now" refers
# to the current datetime, "due" to the scheduled datetime
# and "modified" to the last modified datetime. Note that
# necessarily, "now" >= "modified". The returned value
# varies linearly over the interval in each case.

[urgency.due]
# Return 0.0 when now <= due - interval and max when
# now >= due.

max = 8.0
interval = "1w"

[urgency.pastdue]
# Return 0.0 when now <= due and max when now >=
# due + interval.

max = 10.0
interval = "2w"

[urgency.recent]
# The "recent" value is max when now = modified and
# 0.0 when now >= modified + interval. The maximum of
# this value and "age" (below) is returned. The returned
# value thus decreases initially over the

max = 6.0
interval = "2w"

[urgency.age]
# The "age" value is 0.0 when now = modified and max
# when now >= modified + interval. The maximum of this
# value and "recent" (above) is returned.

max = 9.0
interval = "26w"

[urgency.extent]
# The "extent" value is 0.0 when extent = "0m" and max
# when extent >= interval.

max = 5.0
interval = "12h"

[urgency.blocking]
# The "blocking" value is 0.0 when blocking = 0 and max
# when blocking >= count.

max = 6.0
count = 3

[urgency.tags]
# The "tags" value is 0.0 when len(tags) = 0 and max
# when len(tags) >= count.

max = 4.0
count = 2

[urgency.priority]
# Priority levels used in urgency calculation.
# These are mapped from user input `@p 1` through `@p 5`
# so that entering "@p 1" entails the priority value for
# "someday", "@p 2" the priority value for "low" and so forth.
#
#   @p 1 = someday  → least urgent
#   @p 2 = low
#   @p 3 = medium
#   @p 4 = high
#   @p 5 = next     → most urgent
#
# Set these values to tune the effect of each level. Note
# that omitting @p in a task is equivalent to setting
# priority = 0.0 for the task.

someday = -5.0
low     = 2.0
weights = 5.0
high    = 8.0
next    = 10.0

[urgency.weights]
# These weights give the relative importance of the various
# components. The weights used to compute urgency correspond
# to each of these weights divided by the sum of all of the
# weights.

recent_age   = 2.0
due_pastdue  = 2.0
extent       = 1.0
blocking     = 1.0
tag          = 1.0
active       = 2.0
description  = 1.0
priority     = 1.0
project      = 1.0
```
