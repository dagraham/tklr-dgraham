# Jobs

## urgency config settings and calculation

For a task with jobs, the priority, extent, ... set in the task becomes the
default for each job but will be overruled by

### active

```toml
# At most one task/job can be designated the active task at any point in time.
# Is this task currently the active task? If so, add active_value to urgency.
active_value = 20.0
# urgency += active_value
```

### age

```toml
# How long since the task was created. The greater the age, the greater the urgency.
age_daily = 0.2
# urgency += (now - created).days() * age_daily
```

### blocking

```toml
# Is this
# 1) an available job (unfinished and with no unfinished prerequisites) and
# 2) itself a prerequisite for another job?
# If so, add blocking_value for each job for which this job is a prerequisite
blocking_value = 1.0
# urgency += blocking_value * blocking
```

### description

```toml
# Does this task/job have a description? If so add description_value to urgency.
description_value = 2.0
# urgency += description_value
```

### extent

```toml
# Does the task/job have an extent? If so, add urgency at this rate
# per hour of extent.
extent_hourly = 0.25
# urgency += extent.seconds()/3600.0 * extent_hourly
```

### jobs

```toml
# Does this task have unfinished jobs? Add job_value for each unfinished job
job_value = 2.0
# urgency += job_value
```

### priority

```toml
# Does this task have a priority setting? If so apply to the task itself
# if there are no jobs, otherwise to each job.
priority.next = 15.0
priority.high = 6.0
priority.medium = 2.0
priority.low = -2.0
priority.someday = -6.0
# urgency += priority['priority']
```

### tags

```toml
# Add tag_value to urgency for each assigned tag
tag_value = 1.0
# urgency += tag_value
```

### current

```toml
# How recently has the record been "touched"? The more recent, the greater the urgency.
# The contribution to urgency is positive over the interval from now == touched
# until now == touched + current_interval. Note that now >= touched is always true.
current_interval = 7d
# the maximum contribution to urgency when `now == touched`
current_value = 4.0
# urgency += max(0, current_value(1 - (now - current_interval)/current_interval))
```

### due

```toml
# How soon is the due (scheduled) date? Or how long ago? The sooner or the
# longer ago, the greater the urgency.
# How long before scheduled to start adding to urgency;
`due_interval = 7d`
# the maximum contribution to urgency when now = due
`due_value = 16.0`
# The ratio, due_value/due_interval, gives the rate at which urgency increases
# before scheduled. The rate after scheduled, when the task is past due, is
# obtained  by multiplying this rate by
`past_due_adjustment = 0.5`
# urgency +=  max(0, due_value(1 - max(scheduled - now, 0) * 1/due_interval + max(now - scheduled) * past_due_adjustment/due_interval))
```

age: 2.0 # coefficient for age
scheduled: 12.0 # past scheduled
due: 16.0 # past due or near due date
priority.next: 15.0 # next
priority.high: 6.0 # high
priority.medium: 2.0 # medium
priority.low: -2.0 # low
priority.someday: -6.0 # someday
note: 1.0 # has a note
project: 1.0 # is assigned to a project

tags: 1.0

### fields needed for calculations

- active
- touched (decreasing in -(now - touched) max at now == touched )
- created (increasing in now - created)
- scheduled (increasing in -(now - scheduled) to max at now == scheduled + d days)
- extent
- beginby
- priority
- has a note
- number tags

### calculation

now >= scheduled - min(beginby, 7d)

## urgency table (replaces jobs)

I've saved a branch corresponding to separate tables for events, tasks and notes but want to return now to the relative simplicity of a single records table and uploaded model.py from the working branch.

I want to replace "Jobs" with an "Urgency" table. It would have a record for each task without jobs and records for each job for a task with jobs. For a repeating task, these records would correspond to the first (unfinished) instance. Here is my guess at what the structure:

```python

    CREATE TABLE IF NOT EXISTS Urgency (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        job_id TEXT, -- not null for jobs but null for tasks
        record_id INTEGER NOT NULL,
        subject TEXT NOT NULL, -- for a job some combination of job_name and task subject
        urgency FLOAT NOT NULL, -- order by this, computed from the current datetime and the parameters of the task/job
        status TEXT NOT NULL,
        FOREIGN KEY (record_id) REFERENCES Records(id) ON DELETE CASCADE
    );
```

This would be populated by "populate_urgency_from_record" (replacing "sync_jobs_from_record") which would handle the urgency calculation. For tasks/jobs, it would be somewhat analogous to Datetimes for events. Thoughts?

## thoughts

The @s "scheduled" datetime is treated differently for tasks than for events. I want to have a separate view for tasks and jobs where they will be sorted by their computed "urgency". I'm thinking that a separate "Urgency" table (analagous to DateTimes) might be a good idea:

- Urgency table
  - id
  - record_id (of the relevant task)
  - job_id (None for a task without jobs)
  - urgency

Each task without jobs would have one entry in the urgency table and each task with jobs would have an entry in the table for each job.

An Agenda view would be used to display in two, vertically separated, scrolling panels:

1. events for 3 days beginning with the current datetime and including only events that have ending datetimes >= "now". I.e., events for today that have already ended would not be displayed.
2. The N most urgent tasks/jobs

Thoughts about all this?

## status

- ◻ available/not active
- active/paused (multiple) toggle
- ⚡: active/running (only one) toggle
- ◼ waiting
- ✅: marked for completion
- ❎: marked for deletion

## jobset (json)

> jobs:
> {'j': 'paint', 'node': 0, 'c': 'shop', 'i': 0, 'prereqs': {1, 2, 3, 4, 5, 6, 7, 8}, 'status': 'waiting'})
> {'j': 'sand', 'node': 1, 'c': 'shop', 'i': 1, 'prereqs': {2, 3, 4, 5, 6, 7}, 'status': 'waiting'})
> {'j': 'assemble', 'node': 2, 'c': 'shop', 'i': 2, 'prereqs': {3, 4, 5, 6, 7}, 'status': 'waiting'})
> {'j': 'cut pieces', 'node': 3, 'c': 'shop', 'i': 3, 'prereqs': {4, 5, 6}, 'status': 'waiting'})
> {'j': 'get wood', 'node': 4, 'c': 'Lowes', 'i': 4, 'prereqs': {5, 6}, 'status': 'waiting'})
> {'j': 'go to Lowes', 'node': 5, 'c': 'errands', 'i': 5, 'status': 'available'})
> {'j': 'create plan', 'node': 5, 'i': 6, 'status': 'available'})
> {'j': 'get hardware', 'node': 3, 'c': 'Lowes', 'i': 7, 'prereqs': {5, 6}, 'status': 'waiting'})
> {'j': 'go to Lowes', 'node': 4, 'c': 'errands', 'i': 5, 'status': 'available'})
> {'j': 'create plan', 'node': 4, 'i': 6, 'status': 'available'})
> {'j': 'get paint', 'node': 1, 'c': 'Lowes', 'i': 8, 'prereqs': {5, 6}, 'status': 'waiting'})
> {'j': 'go to Lowes', 'node': 2, 'c': 'errands', 'i': 5, 'status': 'available'})
> {'j': 'create plan', 'node': 2, 'i': 6, 'status': 'available'})
> jobset = '[{"j": "paint", "node": 0, "c": "shop", "i": 0, "prereqs": [1, 2, 3, 4, 5, 6, 7, 8], "status": "waiting"}, {"j": "sand", "node": 1, "c": "shop", "i": 1, "prereqs": [2, 3, 4, 5, 6, 7], "status": "waiting"}, {"j": "assemble", "node": 2, "c": "shop", "i": 2, "prereqs": [3, 4, 5, 6, 7], "status": "waiting"}, {"j": "cut pieces", "node": 3, "c": "shop", "i": 3, "prereqs": [4, 5, 6], "status": "waiting"}, {"j": "get wood", "node": 4, "c": "Lowes", "i": 4, "prereqs": [5, 6], "status": "waiting"}, {"j": "go to Lowes", "node": 5, "c": "errands", "i": 5, "status": "available"}, {"j": "create plan", "node": 5, "i": 6, "status": "available"}, {"j": "get hardware", "node": 3, "c": "Lowes", "i": 7, "prereqs": [5, 6], "status": "waiting"}, {"j": "go to Lowes", "node": 4, "c": "errands", "i": 5, "status": "available"}, {"j": "create plan", "node": 4, "i": 6, "status": "available"}, {"j": "get paint", "node": 1, "c": "Lowes", "i": 8, "prereqs": [5, 6], "status": "waiting"}, {"j": "go to Lowes", "node": 2, "c": "errands", "i": 5, "status": "available"}, {"j": "create plan", "node": 2, "i": 6, "status": "available"}]'

## sqlite

- [ ] add jobset to Item
- [ ] what & fields for jobs?
- [ ] normal tasks and tasks with jobs, all in -> jobs?

```

```
