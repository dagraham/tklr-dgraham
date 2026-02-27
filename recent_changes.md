# Recent Changes

## 0.0.65 — 2026-02-27

Since 0.0.64:

Why upgrade:
- 7 additions, 2 fixes, 4 behavior changes.

Added:
- Added discussion of dayfirst and yearfirst with table to README.md
- Add invitees feature with parsing and validation in Item class
- Add SVG screenshot for wrap_args command and improve layout in README.md
- Add SVG screenshot for wrap_noargs command and improve layout in README.md
- Add SVG screenshot for wrap_noargs command output
- (+2 more)

Fixed:
- Fix list formatting in README.md for scheduled time instructions
- Fix formatting in README.md for calendar URL example

Changed:
- Respect dayfirst, yearfirst and two_digit_year settings in Last, Modified, Completed and Task scheduled displays.
- Update prepare-commit-msg: SOURCE="${2:-}"
- Refresh agenda when the pin/unpin status of a task is toggled.
- Refine common methods and wrap descriptions in item.py for clarity

Docs:
- Update token-keys link in README
- Refine README.md Makefile and related updates for linting and testing
- Update README
- Revise README.md: How can you remember all the <em>tklr</em> options?
- Revise README.md: In comparison, here is how the reminder would be created
- (+14 more)

Technical:
- 15 files changed, 1407 insertions(+), 262 deletions(-)

Note: Respect two_digit_year, dayfirst and yearfirst settings in Last, Modified, Completed and Task scheduled listings.

## 0.0.64 — 2026-02-26

Since 0.0.63:

Why upgrade:
- 0 additions, 0 fixes, 1 behavior changes.

Changed:
- Enhance editor functionality by stabilizing focus and adding Tab completion for live replacements for bin, context, location and use.

Docs:
- Remove repetition entry from the list of @-keys in README.md

Internal:
- Refactor matching functions to return case-insensitive prefix matches for bins, contexts, locations and uses.  Update related tests for improved accuracy and consistency.

Technical:
- 6 files changed, 67 insertions(+), 32 deletions(-)

Note: Implemented tab completion for bins, contexts, locations and uses.

## 0.0.63 — 2026-02-25

Since 0.0.62:

Why upgrade:
- 1 additions, 0 fixes, 1 behavior changes.

Added:
- Implement live attribute matching and deduplication for bin, context, location, and use tokens in Item and Controller

Changed:
- Remove unnecessary log messages in Controller and enhance recurrence rule descriptions in Item

Docs:
- Refactor terminology in README.md and item.py for clarity on repetition settings

Technical:
- 6 files changed, 372 insertions(+), 51 deletions(-)
