# Recent Changes

## 1.0.11 — 2026-03-09

Since 1.0.10:

Why upgrade:
- 0 additions, 0 fixes, 1 behavior changes.

Changed:
- Enhance job parsing to require &r label for @~ jobs and improve error messaging

Technical:
- 4 files changed, 74 insertions(+), 2 deletions(-)

Note: Require &r labels in project @~ tasks

## 1.0.10 — 2026-03-09

Since 1.0.9:

Why upgrade:
- 1 additions, 0 fixes, 0 behavior changes.

Added:
- Add datetime derived versioning to DatabaseManager and update methods to use it

Technical:
- 1 file changed, 11 insertions(+), 4 deletions(-)

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
