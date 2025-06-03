# Datetimes, Dates, and Timezones

- The default timezone is the local timezone of the user's computer.

  - An `@z` entry can be used to override this default:
    - `@s` 2024-08-07 14:00 @z America/New_York
    - `@s` 2024-08-07 14:00 @z Europe/Berlin
    - `@s` 2024-08-07 14:00 @z UTC
    - `@s` 2024-08-07 14:00 @z float  
      In this last case, _float_ means the datetime is interpreted as _naive_ and will be displayed as 14:00 in the user's _current_ local timezone, wherever it may be. This allows the time to “float” with the user's location.
  - Dates and datetimes entered by the user are parsed using `dateutil.parser.parse`. They are serialized as:
    - `YYYYMMDDTHHMM` for datetimes
    - `YYYYMMDD` for dates
      Datetimes are interpreted using timezone information (from `@z` or the default); dates are naive and have no timezone information.
  - `rruleset` requires all values to be comparable. Accordingly:
    - Either the `@s`, `@+`, `@-` values in a reminder must 1) _all_ be dates or 2) _all_ must be _naive_ datetimes. Dates and datetimes cannot be mixed within a reminder.
    - When displaying instances from a `rruleset`, naive values are interpreted using the timezone from `@z` and then converted to the user's current timezone for display.
  - When reminders will be sorted for display based on their dates or datetimes, these string representations are used for sorting:
    - All-day **events** (dates - not datetimes): `YYYYMMDDT000000`
    - All-day **tasks** (dates - not datetimes): `YYYYMMDDT235959`
    - Aware datetimes after converting to the user’s local timezone: `YYYYMMDDTHHMM00`
    - Naive datetimes, no conversion: `YYYYMMDDTHHMM00`
    - Sorting is done lexicographically based on these formatted strings. This ensures that on any given day, all-day events are listed first, followed by time-specific reminders and ending with all-day tasks.
