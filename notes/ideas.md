# Random Ideas

## urgency

### All Relative

Since urgency values are used ultimately to give an ordinal ranking of tasks, all that matters is the relative values used to compute the urgency scores. Accordingly, all scores will be constrained to fall within the interval from -10.0 to 10.0. The default urgency is 0.0 for a component that is not given.

These are the components that potentially contribute to the urgency of a task together with their default values:

- max_interval components:
  - age: how long since modified - the longer, the greater the urgency:
    - max = 9.0
    - interval = "26w"
  - recent: how long since modified - the more recent, the greater the urgency:
    - max = 6.0
    - interval = "2w"
  - due: how soon is the task due - the sooner, the greater the urgency:
    - max = 8.0
    - interval = "1w"
  - pastdue: how long since the task was due - the longer, the greater the urgency:
    - max = 10.0
    - interval = "2w"
  - extent: how long is the expected completion time - the longer the greater the urgency:
    - max = 5.0
    - interval = "12h"
- count components:
  - blocking: how many tasks are waiting for the completion of this task - the more, the greater the urgency:
    - max = 6.0
    - count = 3
  - tag: how many tags does this task have - the more, the greater the urgency:
    - max = 4.0
    - count = 2
- value components:
  - active: if this task is the unique, active task:
    - value = 10.0
  - description: if this task has a description:
    - value = 5.0
  - priority:
    - someday: value = -5.0
    - low: value = 2.0
    - medium: value = 5.0
    - high: value = 8.0
    - next: value = 10.0
  - project: if this task belongs to a project

For each of the max_interval components, a method is defined that takes the maximum value and interval from the parameters given in config.toml for the component combined with the characteristics of the task and returns a float in the interval \[0.0, 10.0\]. Note that the computed urgency will be at least as great as the default, 0.0. Additionally:

- recent and age are combined to return a single urgency, _recent_age_, which is the greater of the two components
- due and past*due are combined to return a single urgency, \_due_pastdue*, which is the greater of the two components

For both of the count components, a method is defined that takes a maximum value from config.toml and a count from the task and returns a float in [0.0, 10.0]. Again the computed value will be at least as great as the default.

For each of the value components, the provided method simply returns the value for the component from config.toml.

Non-negative, _relative weights_ are specified in config.toml for each these urgency components:

- _recent_age_: max(recent, age)
- _due_pastdue_: max(due, pastdue)
- extent
- blocking
- tag
- active
- description
- priority
- project

_Absolute weights_ for each component are then obtained by dividing each of the relative weights by sum of all of the relative weights.

The _task urgency_ is then computed as the weighted average of the component values using the _absolute weights_.

### touch

- refresh modified
- urgency age based on modified
- urgency recent based on modified

## What's next?

- Click interface

- Agenda view

## CLI interface

```python3
from rich import print
from tklr.item import Item
from tklr.model import DatabaseManager

dbm = DatabaseManager("./example/tklr.db")

def add_item(entry: str) -> None:
    print(f"{entry = }")
    item = Item(entry)  # .to_dict()
    print(f"{item = }")
    dbm.add_item(item)
dbm.populate_dependent_tables()
```

Note: these are both tasks with itemtype character `-` but use `@o` to schedule recurrences instead of `@r`.

### recurrent task

There is a set interval between the _actual_ datetime of a completion and the datetime _scheduled_ for the next completion.

- relevant task fields:
  - `@s datetime` scheduled datetime for next completion
  - `@o timedelta` interval between completions
- on completion
  - completion_datetime = datetime of this completion
  - set @s = completion_datetime + @o

### recurrent chore

The interval between the datetime of an _actual_ completion and the datetime _scheduled_ for the next completion is based on a weighted average of the last _expected_ interval and the last _actual_ interval. The expected interval thus adjusts over time to reflect the history of realizations.

- `chore_history_weight: int` is set in config, e.g. `chore_weight = 3`
- relevant chore fields:
  - `@s datetime` the datetime when the next completion is expected to be needed
  - `@o timedelta` the expected interval between the last completion and the next
    needed completion_datetime
  - Note: this implies that the last_completion occurred at @s - @o
- on completion
  - completion_datetime = datetime of this completion
  - last_completion = @s - @o (see note above)
  - last_interval = completion_datetime - last_completion
  - new_interval = (chore_history_weight \* @o + last_interval) / (chore_history_weight + 1)
  - set @o = new_interval
  - set @s = completion_datetime + new_interval

## goals

Between a task (something to be done) and an event (cannot be past due). Event but with different, attention getting color?

```
~ trash to curb @s 8a mon @r w
~ stationary bike @s mon @r w &w TU, WE, FR, SA
```

- `~`: itemtype character for goal
- `@r` for goals, e.g., `+3/6d`, because of the `+`, set goal for at least 3 times every 6 days `-2/w`, because of the minus sign, set goal for no more than 2 times per week.

- relevant fields
  - `@s datetime` starting datetime
  - `@o [+-]goal/interval` the goal
  - `@h list[datetime]` history of up to freq most recent completions

Say that it is currently 09:00 and the goal specifies `@s 09:00` today and `@o +3/6d` and that there have been no completions. Since there has been no opportunity for completions this is not surprising and a status report for this goal should note that 6 days of 6 days are still available to record the 3 completions needed for the goal. On the other hand, at 09:00 five days from now, no completions would be bad news with only 1 day remaining to record 3 completions - a rate of 3 per day compared to the goal rate of 3 per 6 days or 1/2 per day. I.e., the rate needed to achieve the goal is 6 times the rate specified in the goal. Bad news.

How best to handle this progress evaluation generally? Cases:

- Suppose there goal completions in the period from now - interval until now.
  This means no completions are needed to achieve the goal for the current interval.
- Suppose the period from now - interval until now contains fewer than goal completions. Cases
  - Zero completions
  -
