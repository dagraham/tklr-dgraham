# Recent Changes

## 1.0.1 — 2026-03-01

Since 1.0.0:

Why upgrade:
- 1 additions, 1 fixes, 1 behavior changes.

Added:
- Revise README.md: added omitted Tasks View to list

Fixed:
- Implement urgency components retrieval for records and jobs feat: add urgency entry retrieval method in DatabaseManager fix: correct urgency calculation logic in UrgencyComputer test: add integration tests for urgency components and due calculations

Changed:
- improve commit message validation by normalizing AI-generated prefixes and enforcing leading verb requirement

Docs:
- Revise README.md: Feb 2026: 1.0h

Technical:
- 9 files changed, 245 insertions(+), 15 deletions(-)

Note: Added details menu option for tasks to show "Urgency components" for the selected task.

## 1.0.0 — 2026-02-28

Since 0.0.65:

Why upgrade:
- 0 additions, 0 fixes, 1 behavior changes.

Changed:
- Refine markdown explanations for dated list views

Docs:
- Update README.md section title for weeks view

Technical:
- 1 file changed, 23 insertions(+), 19 deletions(-)

Note: Production stable - all planned features, methods and tests in place

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
