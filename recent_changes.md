# Recent Changes

## 1.0.2 — 2026-03-02

Since 1.0.1:

Why upgrade:
- 1 additions, 0 fixes, 0 behavior changes.

Added:
- preserve date-only instances in time zone conversion test: add test for finishing repeating date-only tasks advancing schedule

Docs:
- update README to improve clarity on offset and notice attributes

Technical:
- 4 files changed, 38 insertions(+), 4 deletions(-)

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
