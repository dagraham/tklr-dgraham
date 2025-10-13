# overdue/restart

Here is an illustrative json entry:

```json
  "2697": {
   "created": "{T}:20230128T1311A",
   "itemtype": "-",
   "summary": "Change toothbrush head",
   "s": "{T}:20260318T1912A",
   "r": [
    {
     "r": "m",
     "i": 6
    }
   ],
   "o": "r",
   ...
```

The key features are

- itemtype == "-"
- has key "r" with a list of dict, one of which:
  - has key "r" with value "freq" in "ymwd"
  - and key "i" (optionally - default 1) with integer value "interval".

Such an item should migrate to an item str in which there is no @r entry and
@o is replaced by "@o <interval><freq>". For the example:

`~ Change toothbrush head @s 2026-03-18 19:12 z UTC @o 6m`
