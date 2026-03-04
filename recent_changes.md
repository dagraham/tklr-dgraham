# Recent Changes

## 1.0.5 — 2026-03-03

Since 1.0.4:

Why upgrade:
- 1 additions, 0 fixes, 2 behavior changes.

Added:
- implement daily log file retention with configurable limit

Changed:
- update default value of num_logs in TklrConfig to 3
- improve subject parsing to handle token boundaries correctly feat: allow email addresses in item descriptions and ensure non-space '@' is treated as literal

Docs:
- update README to improve clarity on reminder views and task listings

Technical:
- 6 files changed, 137 insertions(+), 6 deletions(-)

## 1.0.4 — 2026-03-02

Since 1.0.3:

Why upgrade:
- 1 additions, 0 fixes, 1 behavior changes.

Added:
- update terminology in README and code bindings to replace 'Next' with 'Later' and 'Last' with 'Earlier' and add "N" as a binding for create new.

Changed:
- clean up config file comments and improve key bindings layout in view.py

Technical:
- 4 files changed, 51 insertions(+), 44 deletions(-)

## 1.0.3 — 2026-03-02

Since 1.0.2:

Why upgrade:
- 1 additions, 0 fixes, 0 behavior changes.

Added:
- implement date formatting for comparison in controller feat(tests): add tests for unchanged year and month components in various views

Technical:
- 5 files changed, 258 insertions(+), 26 deletions(-)

Note: Highlight year, month and monthday changes in views listing reminders by date.
