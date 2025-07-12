# Goals

`day_begin` and `day_end` set the period available for completions. E.g., with `06:00` and `18:00` ,respectively, a goal of 1 daily would become available at 06:00 and would not be past due until 18:00. Similarly, with a goal of 2 daily and with no completions, 1 would become past due at 12:00 and 2 would be past due at 18:00. The status for the last example would be 0/0/2 between 06:00 and 12:00, then 0/1/2 until 18:00 and finally 0/2/2 after 18:00.

Status: done / due / total

## Entry

`~`: itemtype character

> [!Tip] Check do_quota in etm

### required fields

#### scheduled: `@s <date>`

Begin with the period containing this date

#### goal: `@q <int>/<[d,w,m,q,y]>[: list[int]]`

The goal is to complete the item `<int>` times within each period specified by

- `d`: day - optional weekday integers, e.g.,
  `0-4`: Monday - Friday or `5, 6`: Saturday and Sunday
- `w`: week - optional week numbers
- `m`: month - optional month numbers
  > [!Note] `y`: year?

> [!Tip] The range operator is not Pythonic - the last is included.

## Display

For daily goals, add goal_start_hour (default 6) to config. The period for completion then begins at 06:00 and ends at 23:59. With `@q 3d`, e.g., the first instance would not be past due until 6 + 18/3 = 12:00, the second until 18:00 and the third until 23:59.

Have a goals table similar to alerts, for status updates. E.g., for the previous example the status would change to one past due at 12:00, two past due at 18:00 and three past due at 23:59. These would be updated with each completion.
