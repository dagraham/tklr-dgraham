# Jobs

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
- [ ] all tasks -> jobs? 
