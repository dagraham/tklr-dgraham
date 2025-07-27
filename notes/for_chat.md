# For ChatGPT

## 2025-07-23

- When a task is completed, an action needs to be taken that will depend upon whether the task is a component task in a project, an instance of a repeating task and various other considerations. My question is, where should the logic for this go? In item.py, controller.py, model.py, ...?

Answer: controller.py

## 2025-07-25

```python
def get_due(record:dict):
  # called with available task or project
  rruleset = record.get("rruleset", "")
  if not rruleset:
    # no due date or datetime
    return None
  jobs = json.loads(record.get("jobs", "[]"))
  if jobs:
  _ scheduled =

```

```python
def hide(record: dict, now:) -> bool:
  rruleset = record.get("rruleset", "")
  if not rruleset:
    return False
  beginby = record.get("beginby", "")
  if not beginby:
    return False

```

## 2025-07-24 Urgency calculation

I'm in a muddle trying to get a reasonably simple urgency computation. Here's what I have so far.

The urgency section from config.toml

```toml
[urgency]
# values for task urgency calculation

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

recent_age   = 1.0
due_pastdue  = 1.0
extent       = 1.0
blocking     = 1.0
tag          = 1.0
active       = 1.0
description  = 1.0
priority     = 1.0
project      = 1.0
```

At the beginning of model.py, I make the urgency values available using:

```python
env = TklrEnvironment()
urgency = env.config.urgency
```

I then define these supporting computation methods, again in model.py:

```python
def urgency_due(due: datetime) -> float:
    """
    This function calculates the urgency contribution for a task based
    on its due datetime relative to the current datetime and returns
    a float value between 0.0 when (now <= due - interval) and due_max when
    (now >= due).
    """
    now_seconds = utc_now_to_seconds()
    due_seconds = dt_str_to_seconds(due)
    value = urgency.due.max
    interval = urgency.due.interval
    if value and interval:
        interval_seconds = td_str_to_seconds(interval)
        return max(
            0.0,
            min(
                value,
                value * (1.0 - (now_seconds - due_seconds) / interval_seconds),
            ),
        )
    return 0.0


def urgency_past_due(due: datetime) -> float:
    """
    This function calculates the urgency contribution for a task based
    on its due datetime relative to the current datetime and returns
    a float value between 0.0 when (now <= due) and past_max when
    (now >= due + interval). Note: this adds to "due_max".
    """
    now_seconds = utc_now_to_seconds()
    due_seconds = dt_str_to_seconds(due)

    value = urgency.pastdue.max
    interval = urgency.pastdue.interval
    if value and interval:
        interval_seconds = td_str_to_seconds(interval)
        return max(
            0.0,
            min(
                value,
                value * (now_seconds - due_seconds) / interval_seconds,
            ),
        )
    return 0.0


def urgency_age(modified: datetime) -> float:
    """
    This function calculates the urgency contribution for a task based
    on the current datetime relative to the (last) modified datetime. It
    represents a combination of a decreasing contribution from recent_max
    based on how recently it was modified and an increasing contribution
    from 0 based on how long ago it was modified. The maximum of the two
    is the age contribution.
    """
    recent_contribution = age_contribution = 0
    now_seconds = utc_now_to_seconds()
    modified_seconds = dt_str_to_seconds(modified)
    recent_max = urgency.recent.max
    recent_interval = urgency.recent.interval
    age_max = urgency.age.max
    age_interval = urgency.age.interval
    if recent_max and recent_interval:
        recent_interval_seconds = td_str_to_seconds(recent_interval)
        recent_contribution = max(
            0.0,
            min(
                recent_max,
                recent_max
                * (1 - (now_seconds - modified_seconds) / recent_interval_seconds),
            ),
        )

    if age_max and age_interval:
        age_interval_seconds = td_str_to_seconds(age_interval)
        age_contribution = max(
            0.0,
            min(
                age_max,
                age_max * (now_seconds - modified_seconds) / age_interval_seconds,
            ),
        )
    return max(recent_contribution, age_contribution)
```

The muddle comes in defining compute_task_urgency() and compute_job_urgency() for this:

```python
    def populate_urgency_from_record(self, record: dict):
        log_msg(f"{record = }")
        record_id = record["id"]
        subject = record["subject"]
        created = record["created"]
        modified = record["modified"]
        priority = record.get("priority", "")
        rruleset = record.get("rruleset", "") # due will come from this
        extent = record.get("extent", "")
        beginby = record.get("beginby", "")
        jobs = json.loads(record.get("jobs", "[]"))
        tags = json.loads(record.get("tags", "[]"))
        status = record.get("status", "next")
        # touched = record.get("touched")
        now = datetime.utcnow()
        print(f"{subject = }, {modified = }, {priority = }, {rruleset = }, {extent = }")

        priority_map = self.env.config.urgency.priority.model_dump()

        self.cursor.execute("DELETE FROM Urgency WHERE record_id = ?", (record_id,))

        def compute_task_urgency() -> float:
            # if touched_str:
            #     try:
            #         touched_dt = datetime.fromisoformat(touched_str)
            #         age_days = (now - touched_dt).total_seconds() / 86400
            #         base += min(age_days, 30)
            #     except Exception:
            #         pass
            return round(base, 2)

        if jobs:
            for job in jobs:
                log_msg(f"{job = }")
                job_id = job.get("i", "")
                job_status = job.get("status", "")
                subject = job.get("display_subject", "")
                s = job.get("s", "")
                e = job.get("e", "")
                print(f"job {job_status = }, {subject = }, {s = }, {e = }")
                if job_status == "available":
                    urgency = compute_urgency(job_status)
                    self.cursor.execute(
                        """
                        INSERT INTO Urgency (record_id, job_id, subject, urgency, status)
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        (
                            record_id,
                            job_id,
                            subject,
                            urgency,
                            job_status,
                        ),
                    )
        else:
            urgency = compute_urgency()
            self.cursor.execute(
                """
                INSERT INTO Urgency (record_id, job_id, subject, urgency, status)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    record_id,
                    None,
                    subject,
                    urgency,
                    status,
                ),
            )

        self.conn.commit()
```
