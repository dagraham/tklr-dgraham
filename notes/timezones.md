# Timezone considerations

Python supports datetime objects that can be either timezone-aware or naive (without timezone information). The program *python-dateutil* provides 1) datetime parsing, 2) timezone handling and 3) recurrence rules. Much experience dealing with aware datetimes

1) Datetimes entered by a user for, say, `@s` should be interpreted as aware datetimes in the local timezone unless an `@z` entry specifies otherwise. E.g., in New York, the first two of the following would be equivalent:

   - `@s` 2024-08-07 14:00
   - `@s` 2024-08-07 14:00 @z America/New_York
   - `@s` 2024-08-07 14:00 @z Europe/Berlin
   - `@s` 2024-08-07 14:00 @z UTC
   - `@s` 2024-08-07 14:00 @z float

    In the last, the timezone "float" means that the datetime is naive and thus will be displayed as occurring at 14:00 in whatever timezone the user happens to be.

2) To serialize (encode) a datetime object, a convenient method is first to convert an aware datetime to UTC, and then to store is as a string in some convenient format, e.g., `YYYYMMDDTHHMMSS` and then to append an "A" for "aware": `YYYYMMDDTHHMMSSA`. Similarly a naive datetime would, without conversion, be stored as `YYYYMMDDTHHMMSSN` for "naive". The format doesn't matter, "seconds since the epoch" with an "A" or "N" appended would work as well.

3) To de-serialize (decode) a datetime string is then just a matter of parsing everything but last character as a datetime and then, if "A" is the last character, first converting the datetime to the local timezone before returning it as an *aware* datetime and otherwise, if "N", returning it without conversion as a *naive* datetime.

But for recurrence and *daylight saving time*, this would be the simple end of the story.

I have this method to process a datetime token string:

```python
    def do_datetime(self, token):
        """
        Process a datetime token such as "@s 2024-08-07 14:00" using "parse" from dateutil.parser and 
        return the corresponding datetime object.
        """
        # Process datetime token
        print(f"Processing datetime token: {token}")
        try:
            datetime_str = re.sub("^@. ", "", token)
            datetime_obj = parse(datetime_str)
            if datetime_obj.tzinfo is None:
                datetime_obj = datetime_obj.astimezone(tz.tzlocal())
            self.dtstart = datetime_obj
            return True, datetime_obj, []
        except ValueError as e:
            return False, f"Invalid datetime: {datetime_str}. Error: {e}", []
```

I want modify this to allow for a string with "&z TZInfo" appended - e.g., "@s 3p fri &z US/Pacific".
The following cases should be handled:

- &z is not present: Use tzlocal() as before.
- &z XXX is present.
  - if XXX is a recognized timezone, e.g., "US/Pacific", use it as the timezone.
  - if XXX is in ['float', 'naive', 'none'], then treat the datetime as naive

Here is my problem. A user might want to create a reminder for a meeting at 15:00 on the first Friday of each month. Entered as a "float" this works perfectly:

```python
item.entry = '- xyz float meeting @s 3p &z float @e 1h30m @r m &w +1FR &c 12'
{
  "itemtype": "-",
  "subject": "xyz float meeting",
  "e": 5400,
  "scheduled": "20250424T150000",
  "rruleset": "DTSTART:20250424T150000\nRRULE:FREQ=MONTHLY;BYDAY=+1FR;COUNT=12"
}
  Fri 2025-05-02 15:00
  Fri 2025-06-06 15:00
  Fri 2025-07-04 15:00
  Fri 2025-08-01 15:00
  Fri 2025-09-05 15:00
  Fri 2025-10-03 15:00
  Fri 2025-11-07 15:00
  Fri 2025-12-05 15:00
  Fri 2026-01-02 15:00
  Fri 2026-02-06 15:00
```

But if this is, e.g, a zoom meeting that is to be held at 15:00 in the US/Eastern timezone then this will display as 15:00 even if the user is in California.

Entered as US/Eastern, this works until DST rears its ugly head:

```python
item.entry = '- xyz US/Eastern meeting @s 3p &z US/Eastern @e 1h30m @r m &w +1FR &c 12'
{
  "itemtype": "-",
  "subject": "xyz US/Eastern meeting",
  "e": 5400,
  "scheduled": "20250424T190000+0000",
  "rruleset": "DTSTART:20250424T190000+0000\nRRULE:FREQ=MONTHLY;BYDAY=+1FR;COUNT=12"
}
  Fri 2025-05-02 15:00 EDT -0400
  Fri 2025-06-06 15:00 EDT -0400
  Fri 2025-07-04 15:00 EDT -0400
  Fri 2025-08-01 15:00 EDT -0400
  Fri 2025-09-05 15:00 EDT -0400
  Fri 2025-10-03 15:00 EDT -0400
  Fri 2025-11-07 14:00 EST -0500
  Fri 2025-12-05 14:00 EST -0500
  Fri 2026-01-02 14:00 EST -0500
  Fri 2026-02-06 14:00 EST -0500
```

and starts displaying the meeting time as 14:00 EST instead of 15:00 EST.

So I thought, I'll just add a specification for the HOUR, being careful to specify the 19 as the appropriate UTC hour:

```python
item.entry = '- xyz US/Eastern meeting with HOURS @s 3p &z US/Eastern @e 1h30m @r m &w +1FR &H 19 &c 12'
{
  "itemtype": "-",
  "subject": "xyz US/Eastern meeting with HOURS",
  "e": 5400,
  "scheduled": "20250424T190000+0000",
  "rruleset": "DTSTART:20250424T190000+0000\nRRULE:FREQ=MONTHLY;BYDAY=+1FR;BYHOUR=19;COUNT=12"
}
  Fri 2025-05-02 15:00 EDT -0400
  Fri 2025-06-06 15:00 EDT -0400
  Fri 2025-07-04 15:00 EDT -0400
  Fri 2025-08-01 15:00 EDT -0400
  Fri 2025-09-05 15:00 EDT -0400
  Fri 2025-10-03 15:00 EDT -0400
  Fri 2025-11-07 14:00 EST -0500
  Fri 2025-12-05 14:00 EST -0500
  Fri 2026-01-02 14:00 EST -0500
  Fri 2026-02-06 14:00 EST -0500
```

But this doesn't work either. The hour is set to 19 UTC, but the time still switches from 15:00 EDT to 14:00 EST in Novembe because the recurrence rule is generating the times as UTC and then converting to the local timezone which is now EST.

My next idea is to convert DTSTART to local time first and then generate the rrule times. Problems with this?  Better idea?

This seems to work for me.

In item.__init__,  self.timezone = get_local_zoneinfo()

two-pass solution:

```python
    def _parse_all_tokens(self):
        print(f"{self.tokens = }")
        second_pass = []

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
                if token_type == "z":
                    print(f"1 processing token: {token_type}")
                    self._dispatch_token(token, start_pos, end_pos, token_type)
                else:
                    continue
        # second pass
        for i, token_info in enumerate(self.tokens):
            token, start_pos, end_pos = token_info
            if i in [0, 1]:
                continue
            else:
                token_type = token.split()[0][
                    1:
                ]  # Extract token type (e.g., 's' from '@s')
                if token_type != "z":
                    print(f"2 processing token: {token_type}")
                    self._dispatch_token(token, start_pos, end_pos, token_type)
                else:
                    continue
```

```python
    def do_datetime(self, token):
        """
        Process a datetime token such as "@s 3p fri &z US/Eastern" or "@s 2025-04-24".
        Sets both self.dtstart and self.dtstart_str.
        """
        # print(f"Processing datetime token: {token}")
        try:
            # Split on '&z' inline if still supported
            parts = token.split("&z", 1)
            datetime_str = parts[0].strip()
            tz_str = parts[1].strip() if len(parts) > 1 else None

            # Remove prefix like '@s '
            datetime_str = re.sub(r"^@.\s+", "", datetime_str)

            # Parse the datetime
            dt = parse(datetime_str)

            # my zone logic
            if self.timezone:
                print(f"{self.timezone = }, {dt = }")
                dt = dt.replace(tzinfo=self.timezone)
                print(f"timezone replaced {dt = }")
                self.dtstart_str = (
                    f"DTSTART;TZID={self.timezone.key}:{dt.strftime('%Y%m%dT%H%M%S')}"
                )
                dt = dt.astimezone(tz.UTC)
                print(f"as UTC {dt = }")

            # Promote pure date to datetime if necessary
            if isinstance(dt, date) and not isinstance(dt, datetime):
                if self.item.get("itemtype") == "-":
                    dt = datetime(
                        dt.year, dt.month, dt.day, 23, 59, 59, tzinfo=dt.tzinfo
                    )
                else:
                    dt = datetime(dt.year, dt.month, dt.day, 0, 0, 0, tzinfo=dt.tzinfo)

            self.dtstart = dt
            return True, dt, []

        except ValueError as e:
            return False, f"Invalid datetime: {datetime_str}. Error: {e}", []
```

input:
- Tiki Roundtable Meeting @s 14:00 @z UTC @e 1h30m @r m &w +3TH &c 12

# Computed from input

self.tokens = [('*', 0, 1), ('Tiki Roundtable Meeting ', 2, 26), ('@s 14:00 ', 26, 35), ('@z UTC ', 35, 42), ('@e 1h30m ', 42, 51), ('@r m &w +3TH &c 12', 51, 69)]
item.entry = '* Tiki Roundtable Meeting @s 14:00 @z UTC @e 1h30m @r m &w +3TH &c 12'

item.item = {'itemtype': '*', 'subject': 'Tiki Roundtable Meeting', 'z': zoneinfo.ZoneInfo(key='UTC'), 'e': 5400, 'scheduled': '20250425T140000+0000', 'rruleset': 'DTSTART;TZID=UTC:20250425T140000\nRRULE:FREQ=MONTHLY;BYDAY=+3TH;COUNT=12'}

json_dumps(item.item):
{
  "itemtype": "*",
  "subject": "Tiki Roundtable Meeting",
  "z": "UTC",
  "e": 5400,
  "scheduled": "20250425T140000+0000",
  "rruleset": "DTSTART;TZID=UTC:20250425T140000\nRRULE:FREQ=MONTHLY;BYDAY=+3TH;COUNT=12"
}

Without conversion:
  Thu 2025-05-15 14:00 UTC +0000
  Thu 2025-06-19 14:00 UTC +0000
  Thu 2025-07-17 14:00 UTC +0000
  Thu 2025-08-21 14:00 UTC +0000
  Thu 2025-09-18 14:00 UTC +0000
  Thu 2025-10-16 14:00 UTC +0000
  Thu 2025-11-20 14:00 UTC +0000
  Thu 2025-12-18 14:00 UTC +0000
  Thu 2026-01-15 14:00 UTC +0000
  Thu 2026-02-19 14:00 UTC +0000
