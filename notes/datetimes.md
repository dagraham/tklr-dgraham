# Datetimes

There are a variety of user entries affecting dates and datetimes, the most important of which are `@s` (scheduled) and `@z` (timezone).

## Timezone Information

- The default timezone is the local timezone of the user's computer. This is used when there is no `@z` entry.

- An `@z` entry can be used to override this default:
  - `@s` 2024-08-07 14:00 @z America/New_York
  - `@s` 2024-08-07 14:00 @z Europe/Berlin
  - `@s` 2024-08-07 14:00 @z UTC
  - `@s` 2024-08-07 14:00 @z CET
  - `@s` 2024-08-07 14:00 @z none  
    In this last case, _none_ means the datetime is interpreted as _naive_ and will be displayed as 14:00 in the user's _current_ local timezone, wherever it may be.

## Dates and Datetimes

Dates and datetimes entered by the user are parsed using `parse()` from `dateutil.parser` using the `yearfirst` and `dayfirst` settings from the user configuration file.

| dayfirst | yearfirst | date     | interpretation | standard       |
| -------- | --------- | -------- | -------------- | -------------- |
| True     | True      | 12-10-11 | 2012-11-10     | Y-D-M ?        |
| True     | False     | 12-10-11 | 2011-10-12     | D-M-Y EU       |
| False    | True      | 12-10-11 | 2012-10-11     | Y-M-D ISO 8601 |
| False    | False     | 12-10-11 | 2011-12-10     | M-D-Y US       |

If `parse(user_entry)` succeeds the object returned will either be a date or a datetime. The object is serialized as follows:

### Dates

A date is serialized as `obj.strftime("%Y%m%d")`. E.g., `2025/8/24` -> `20250824`

### Datetimes

#### Serialization

- If the user entry specifies `@z = none`, the datetime is understood to be _naive_ and serialized as `obj.strftime("%Y%m%d%H%M%S")`. E.g., `2025/8/24 1:30pm` -> `20250824133000`
- Otherwise the datetime is understood to be _aware_ (not _naive_). The timezone is determined as follows:
  - If the user entry does not specify `@z`, then the timezone defaults to the local timezone of the user's computer, `timezone = tzlocal.get_localzone_name()`
  - If the user entry specifies `@z TZ`, then `timezone = dateutil.tz.gettz(TZ)`
  - The aware datetime is first converted from timezone to the equivalent datetime in UTC and then serialized as
  - `obj = obj.replace(tzinfo=gettz(timezone)).astimezone(tz.UTC)` and serialized as `obj.strftime("%Y%m%d%H%M%SZ")` (note the appended "Z"). E.g., with `@z US/Eastern`, `2024/8/24 1:30pm` -> `20240824173000Z`

#### Display

- Dates are displayed without consideration of timezone in whatever `strftime` format desired.
- Naive datetimes are similarly displayed without consideration of timezone in whatever `strftime` format desired.
- Aware datetimes are stored as UTC times and are displayed after conversion of the UTC time to the timezone of the user's computer wherever it might be. E.g., for the example given above with `@z US/Eastern`, `2024/8/24 1:30pm` would be serialized as `20240824173000Z`. If the user's computer were in California, this datetime would then be displayed using `"%Y-%m-%d %H:%M"` as the format for `strftime` as `"2025-08-24 10:30"`.

### Repetition

Repetition using `dateutil.rrulestr` requires all date/datetime values to be comparable. Accordingly: the `@s`, `@+`, `@-`, `@f` and `&f` values in a given reminder must _all_ be

1. dates or
2. _naive_ datetimes or
3. _aware_ datetimes

The entries for `@s` and `@z` determine which case will apply.

1. If the value of `@s` parses as a _date_, then the entry for `@z`, if given, is ignored and all other datetime entries are converted, if necessary, to date objects.
2. If `@s` parses as a datetime and `@z none` is given, then the value of `@s` is interpreted as naive and all other datetime entries are converted, if necessary, to naive datetimes.
3. If `@s` parses as a datetime and `@z` specifies a valid timezone, then the value of `@s` is interpreted as an aware datetime in the specified timezone. Otherwise, if `@z` is not given, the value of `@s` is interpreted as an aware datetime in the _local timezone_ of the user's computer. All other datetimes are interpreted as _aware datetimes_ in the same timezone.

The relevant serialized instances of a reminder, dates or datetimes, are stored in the _DateTimes_ table using the same serialization rules described above. All instances for a given reminder must be 1) dates (8 characters), 2) naive datetimes (12 or more characters long ending in a digit) or 3) aware datetimes (13 or more characters long, ending in "Z") .
