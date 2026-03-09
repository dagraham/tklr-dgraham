# Recent Changes

## 1.0.9 — 2026-03-09

Since 1.0.8rc0:

Why upgrade:
- 1 additions, 1 fixes, 0 behavior changes.

Added:
- Added migration guide for transitioning reminders from etm to tklr

Fixed:
- Enhance timezone handling in item and database manager - Introduce environment-based timezone detection - Update methods to localize recurrence rules - Ensure correct timezone representation in serialized data

Docs:
- Update README to clarify task prerequisites wording
- Update task references to use '&r' instead of '@r' in README.md
- Updated README to reflect changes in project examples and task labels

Technical:
- 5 files changed, 256 insertions(+), 25 deletions(-)

Note: Daylight saving time fix

## 1.0.8rc0 — 2026-03-08

Since 1.0.8:

Why upgrade:
- 0 additions, 0 fixes, 1 behavior changes.

Changed:
- Updated sync-recent-changes-discussion avoiding copilot hooks.

Technical:
- 1 file changed, 14 insertions(+), 4 deletions(-)

## 1.0.8 — 2026-03-08

Since 1.0.7:

Why upgrade:
- 0 additions, 1 fixes, 0 behavior changes.

Fixed:
- Fixed bug in processing incomplete project task entries

Technical:
- 4 files changed, 42 insertions(+), 12 deletions(-)
