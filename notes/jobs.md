# Jobs

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
