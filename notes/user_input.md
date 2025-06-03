# User Input

### Just-in-time user assistance and validation

The process of entering user input is intended to provide "just in time" assistance and validation using two display panes and one entry pane. E.g., when a user begins to create a new reminder the first pane (single line) would display a request for the item type character, the second pane (possibly multi line) would display the options and the third pane would have the focus and receive the entry. The contents of the 3 panes are illustrated below with an \_ (underscore character) indicating the position of the cursor in the third pane:

#### new entry, nothing entered - an empty string is being processed

> itemtype
> a character from \* (event), - (task), ...
> \_

#### itemtype character entered but no subject

> subject
> the subject of the reminder
> \*\_

#### @ character entered, both itemtype and subject have been entered

> @-key
> required: list of required keys and their descriptions
> optional: list of optional (allowed but not required) keys and their descriptions
> ... @\_

#### @X entered where X is not a valid key for type "@", e.g.,

> Invalid @-key
> @K is unrecognized (OR not allowed for this itemtype OR already entered and only one instance allowed)
> ... @K\_

#### @X entered where X is valid

Examples

> scheduled
> the scheduled date or datetime for this item
> ... @s\_

---

> repetition frequency
> a character from (y)early, (m)onthly, (h)ourly or mi(n)utely. Append an '&' to add a repetition option
> ... @r\_

---

> job name
> the name of this job, prepend 2 an additional spaces before the name to make this job a requirement for prior jobs with fewer spaces. Append an '&' to add a job option
> ... @j\_

---

#### @X xxx entered where X is valid and xxx is the current entry, e.g.,

Supposing that it is currently May 27, 2025

> scheduled
> Tue May 27, 2025 9:00am EDT
> ... @s 9a\_

### Issues:

- There is a dictionary, _token_keys_, with keys corresponding to each of the @-keys and with values including information about the key and the method to be dispatched to process the value of the key. E.g., For @s, the dictionary entry is
  `"s": ["scheduled", "the scheduled date or datetime for this item", "do_datetime"]`
  When the value for @s is being entered by the user, the first component is used for the first pane, the second component for the second pane and, when there is an entry, the third component is passed the entry and the result used to replace the generic information in the second pane. This dictionary also contains keys such as
  `"rw": [ "weekdays", "list from SU, MO, ..., SA, possibly prepended with a positive or negative integer", "do_weekdays", ],`
  to be used when &w is entered following @r. There are similar keys beginning with "j" to be used for &-key entries following @j.

- How best to update the contents of the 2 display panes appropriately? I'm guessing that "buffer modified" in Textual could trigger the method to process the current content of the buffer?

- For _each_ item type, there are corresponding lists of _required_ @-keys and _allowed_ @-keys. By implication, @-keys not appearing on either list are _not allowed_ for the that item type. E.g., for an event, @s is required and @f is not allowed. For a task, both @s and @f are allowed. Similarly there are lists of keys for &-tokens following @r and @j entries.

- Neither an @ character nor an & character at the end of the entry is recognized as a token - how best to capture this situation to set the 2 display panes correctly for the required and optional keys for these types?

- Some @-keys, when required or allowed, may be entered more than once in a reminder. E.g., @t (tag) may be used more than once but @s can only be used once. There is an _allow_multiple_ list that specifies which @-keys can be used more than once. How best to validate this?

- Some @-keys require the presence of other @-keys. E.g., @r requires @s. Other @-keys preclude the use of other @-keys. This is specified by two dictionaries, _requires_ which gives for each @-key which requires other @-keys, the list of such @-keys and _precludes_ which gives for each @key which precludes other @-keys, the list of such @keys. Again, how best to validate this?
-

## validation

```
    def parse_input(self, entry: str):
        """
        Parses the input string to extract tokens, then processes and validates the tokens.
        """
        print("--- begin entry ---\n", f"{entry}", "\n--- end entry --- ")
        digits = "1234567890" * ceil(len(entry) / 10)
        self._tokenize(entry)
        self._parse_tokens(entry)
        #TODO: good place for validation?
```

```
def validate(self):
    if len(self.structured_tokens) < 2:
#
    return
  for token in self.structured_tokens:

```
