# Finish

Currently in Item's finalize_record:

```python
if self.has_f:
   self.itemtype = 'x'
   self.finish()
```

This is almost totally wrong. For starters, tasks with @o (offset) entries are never finished nor are repeating tasks unless it is the last instance.

If `self.has_f` is true it means that the task or project has an `@f <datetime>` entry. For a project, this means that all of the component jobs have been finished.

1. Deal with `@o offset` entries first. A task with an offset entry must also have an `@s <datetime>` entry and may NOT have any of these entries: `@r, @+, @-`. So no other type of repetition. The value of the offset token will optionally begin with `~` followed by a timedelta string such as "3d". Suppose that `learn` is true if it does and let `at_o` represent the timedelta. Similarly let `at_s` be the datetime corresponding to the @s token and `at_f` the datetime corresponding to @f. If `learn` is true, the interval needs to be adjusted `at_o = (self.history_weight * at_0 + at_f - at_s) / (history_weight + 1)`. Then the interval needs to be applied to get the next due datetime, `at_s = at_f + at_o`.

2. Otherwise, without an `@o offset` entry, the task or project might have an `@s datetime` entry and, if it does, perhaps `@r` and/or `@+` entries.
   a) No `@s` entry - a non-repeating, undated task or project. Remove the `@f` entry and change the itemtype to `x`. Record the completion datetime and the due datetime as None.
   b) An @s entry but non-repeating. Remove the `@f` entry, change the itemtype to `x` and record the completion datetime and the due datetime as the value of `@s`.
   c) Repeating and last instance. Remove the @f entry, change the itemtype to `x` and record the completion datetime and the due datetime as the value of this last instance.
   d) Repeating and not the last instance. Remove the @f entry. If the due datetime corresponds to a value in `@+`, remove it. Compute the next due datetime and set this as the new value of `@s`.

It might be that `self.finish()` satisfies (2):

```
    def finish(self) -> None:
        f_tokens = [t for t in self.relative_tokens if t.get("k") == "f"]
        if not f_tokens:
            return
        log_msg(f"{f_tokens = }")

        # completed_dt = max(parse_dt(t["token"].split(maxsplit=1)[1]) for t in f_tokens)
        completed_dt, was_due_dt = parse_f_token(f_tokens[0])

        due_dt = None  # default

        if offset_tok := next(
            (t for t in self.relative_tokens if t.get("k") == "o"), None
        ):
            due_dt = self._get_start_dt()
            td = td_str_to_td(offset_tok["token"].split(maxsplit=1)[1])
            self._replace_or_add_token("s", completed_dt + td)
            if offset_tok["token"].startswith("~") and due_dt:
                actual = completed_dt - due_dt
                td = self._smooth_interval(td, actual)
                offset_tok["token"] = f"@o {td_to_td_str(td)}"
                self._replace_or_add_token("s", completed_dt + td)

        elif self.rruleset:
            first, second = self._get_first_two_occurrences()
            due_dt = first
            if second:
                self._replace_or_add_token("s", second)
            else:
                self._remove_tokens({"s", "r", "+", "-"})
                self.itemtype = "x"

        else:
            # one-off
            due_dt = None
            self.itemtype = "x"

        # ⬇️ single assignment here
        self.completion = (completed_dt, due_dt)

        self._remove_tokens({"f"})
        self.reparse_finish_tokens()

```
