# Notes

## SQLite3 Database

### Tables

- Items
  - id
  - itemtype: text
  - scheduled: int (seconds since epoch)
  - created: int (seconds since epoch)
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
