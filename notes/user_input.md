# User Input

This is a rather long-winded way of posing three questions in Section 3 below.

To specify a reminder, users provide a string input which specifies its properties, e.g.,

`* Thanksgiving @s 2025/11/1 @r y &m 11 &w +4TH`

This input string always beings with a type character from '\*' (event), '-' (task), '%' (note) or '!' (inbox) which is followed immediately by the subject of the reminder. What follows is flexible but involves the use of '@' characters preceded by a space and followed by a key (character) and a value. In the Thanksgiving example, `@s 2025/11/1` provides the key 's' and value '2025/11/1' and `@r y &m 11 &w +4TH` provides the key 'r' and the value 'y &m 11 &w +4TH'.

## 1. Just-in-time user assistance and validation

The process of entering user input is intended to provide "just in time" assistance and validation using two display panes and one entry pane. E.g., when a user begins to create a new reminder the first pane (single line) would display a request for the item type character, the second pane (possibly multi line) would display the options and the third pane would have the focus and receive the entry:

> item type
> choose a character from '\*' (event), '-' (task), '%' (note) or '!' (inbox)
>
> ---
>
> \_

Then, when the type character has been entered:

> subject
> enter the subject of the reminder - an @ may be appended to specify an option
>
> ---
>
> \* \_

When '\* Thanksgiving @' has been entered, the display would change to

> @-key options
> required: @s scheduled datetime
> available: @+ (include datetimes), @- (exclude datetimes), ...
>
> ---
>
> \* Thanksgiving @\_

If an invalid key is entered:

> unrecognized key
> @y is invalid
>
> ---
>
> \* Thanksgiving @y\_

With a valid key, @s, and the beginning of an entry (currently May 2025):

> scheduled
> Sun, May 11 2025
>
> ---
>
> \* Thanksgiving @s 11\_

And then as the entry is expanded

> scheduled
> Sat, Nov 1 2025
>
> ---
>
> \* Thanksgiving @s 11/1\_

## 2. Implementation

1. For _each_ item type, there are corresponding lists of _required_ @-keys and _allowed_ @-keys. By implication, @-keys not appearing on either list are _not allowed_ for the that item type. E.g., for an event, @s is required and @f is not allowed. For a task, both @s and @f are allowed.

2. Some @-keys, when required or allowed, may be entered more than once in a reminder. E.g., @t (tag) may be used more than once but @s can only be used once. There is an _allow_multiple_ list that specifies which @-keys can be used more than once.

3. Some @-keys require the presence of other @-keys. E.g., @r requires @s. Other @-keys preclude the use of other @-keys. This is specified by two dictionaries, _requires_ which gives for each @-key which requires other @-keys, the list of such @-keys and _precludes_ which gives for each @key which precludes other @-keys, the list of such @keys.

4. There is a dictionary, _token_keys_, with keys corresponding to each of the @-keys and with values including information about the key and the method to be dispatched to process the value of the key. E.g., For @s, the dictionary entry is
   `"s": ["scheduled", "date or datetime", "do_datetime"]`
   When the value for @s is being entered by the user, the first component is used for the first pane, the second component for the second pane and, when there is an entry, the third component is passed the entry and the result used to replace the generic information in the second pane.

5. The tokenize and parse methods (Section 4) are responsible for parsing the user input, displaying the relevant information and dispatching the relevant methods. Here is the result of parsing the entire "Thanksgiving" string:

```
entry:
  * Thanksgiving @s 2025/11/1 @r y &m 11 &w +4TH
input_hsh = {'itemtype': '*', 'subject': 'Thanksgiving', 's': '2025/11/1', 'r': 'y &m 11 &w +4TH'}
tokens = [('*', 0, 1), ('Thanksgiving ', 2, 15), ('@s 2025/11/1 ', 15, 28), ('@r y ', 28, 33), ('&m 11 ', 33, 39), ('&w +4TH', 39, 46)];
jobs = []
item:
  {"itemtype": "*", "subject": "Thanksgiving", "rruleset": "DTSTART;VALUE=DATE:20251101\nRRULE:FREQ=y;BYMONTH=11;BYDAY=+4TH"}
```

## 3. Questions

1. Does the overall implementation make sense? Any better ideas?
1. The \_tokenize and \_parse methods do a wonderful job of parsing the '@' and '&' tokens but not the beginning type character and subject. If, for example, the 'Thanksgiving' were omitted, then the 2nd token, '@s 2025/11/1' would erroneously be used as the subject. How can the itemtype and subject be better handled?
1. Given that the list of _tokens_, e.g.,
   `[('*', 0, 1), ('Thanksgiving ', 2, 15), ('@s 2025/11/1 ', 15, 28), ('@r y ', 28, 33), ('&m 11 ', 33, 39), ('&w +4TH', 39, 46)]`
   contains the starting and ending positions of each token in the input string, would it be possible for a textual interface to use the cursor position to get the token containing the cursor and thus the key correspond to the cursor position and then the _token_keys_ dictionary to show the information regarding the relevant @-key or &-key in the user interface?

## 4. Tokenize and Parse

```python
    def _tokenize(self, entry: str):
        print("_tokenize")
        self.entry = entry
        pattern = r"(@\w+ [^@]+)|(^\S+)|(\S[^@]*)"
        matches = re.finditer(pattern, self.entry)
        tokens_with_positions = []
        if not matches:
            print("no tokens")
            return
        for match in matches:
            # Get the matched token
            token = match.group(0)
            # Get the start and end positions
            start_pos = match.start()
            end_pos = match.end()
            print(f"processing {token = }, {start_pos = }, {end_pos = }")
            # Append the token and its positions as a tuple
            tokens_with_positions.append((token, start_pos, end_pos))
        self.tokens = tokens_with_positions
        print("calling tokens_to_hsh")
        self.input_hsh = tokens_to_hsh(self.tokens)
        print(f"{self.input_hsh = }")
        input_str = hsh_to_input(self.input_hsh)
        print(f"{input_str = }")

    def _sub_tokenize(self, entry):
        print("_sub_tokenize")
        pattern = r"(@\w+ [^&]+)|(^\S+)|(\S[^&]*)"
        matches = re.finditer(pattern, entry)
        if matches is None:
            return []
        tokens_with_positions = []
        for match in matches:
            # print(f"{match = }")
            # Get the matched token
            token = match.group(0)
            # Get the start and end positions
            start_pos = match.start()
            end_pos = match.end()
            # Append the token and its positions as a tuple
            # tokens_with_positions.append((token, start_pos, end_pos))
            tokens_with_positions.append(tuple(token.split()))
        return tokens_with_positions

    def _parse_tokens(self, entry: str):
        if not self.previous_entry:
            # If there is no previous entry, parse all tokens
            self._parse_all_tokens()
            return

        # Identify the affected tokens based on the change
        changes = self._find_changes(self.previous_entry, entry)
        affected_tokens = self._identify_affected_tokens(changes)

        # Parse only the affected tokens
        for token_info in affected_tokens:
            token, start_pos, end_pos = token_info
            # Check if the token has actually changed
            if self._token_has_changed(token_info):
                # print(f"processing changed token: {token_info}")
                if start_pos == 0:
                    self._dispatch_token(token, start_pos, end_pos, "itemtype")
                elif start_pos == 2:
                    self._dispatch_token(token, start_pos, end_pos, "subject")
                else:
                    self._dispatch_token(token, start_pos, end_pos)

    def _parse_all_tokens(self):
        # print(f"{self.tokens = }")
        # second_pass = []

        # first pass
        for i, token_info in enumerate(self.tokens):
            token, start_pos, end_pos = token_info
            if i == 0:
                self._dispatch_token(token, start_pos, end_pos, "itemtype")
            elif i == 1:
                self._dispatch_token(token, start_pos, end_pos, "subject")
            else:
                token_type = token.split()[0][
                    1:
                ]  # Extract token type (e.g., 's' from '@s')
                self._dispatch_token(token, start_pos, end_pos, token_type)
```

The advantage of the original \_tokenize is that by keeping the &-key components of @r together, they are available to complete rruleset:

```
\* Thanksgiving @s 2025/11/1 @r y &m 11 &w +4TH
self.input*hsh = {'itemtype': '*', 'subject': 'Thanksgiving', 's': '2025/11/1', 'r': 'y &m 11 &w +4TH'}
self.tokens = [('_', 0, 1), ('Thanksgiving ', 2, 15), ('@s 2025/11/1 ', 15, 28), ('@r y ', 28, 33), ('&m 11 ', 33, 39), ('&w +4TH', 39, 46)];
self.jobs = []
item:
{"itemtype": "\*", "subject": "Thanksgiving", "rruleset":
"DTSTART;VALUE=DATE:20251101\nRRULE:FREQ=y;BYMONTH=11;BYDAY=+4TH"}
errors: []
```

While with the new, the logic of collecting the components would have to be added

```
\* Thanksgiving @s 2025/11/1 @r y &m 11 &w +4TH
\_tokenize
input*str = '* Thanksgiving @s 2025/11/1 @r y @& +4TH'
self.tokens = [('_', 0, 1), ('Thanksgiving ', 2, 15), ('@s 2025/11/1 ', 15, 28), ('@r y ', 28, 33), ('&m 11 ', 33, 39), ('&w +4TH', 39, 46)];
self.jobs = []
item:
{"itemtype": "\*", "subject": "Thanksgiving", "rruleset": "RDATE;VALUE=DATE:20251101"}
errors: []
```
