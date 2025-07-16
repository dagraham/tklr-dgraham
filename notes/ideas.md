# Random Ideas

## What's next?

- Agenda view

## recurrent tasks and chores

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
