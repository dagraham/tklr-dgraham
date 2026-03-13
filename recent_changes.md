# Recent Changes

## 1.0.14 — 2026-03-13

Since 1.0.13:

Why upgrade:
- 0 additions, 1 fixes, 0 behavior changes.

Fixed:
- Fixed several live-editing and recurrence regressions. Project entry feedback now preserves useful in-progress guidance: live @s parsing errors are no longer hidden by the project’s missing required @~ job, a bare trailing & in @r input is treated as an incomplete repetition modifier instead of an invalid frequency, and entering a bare @ still shows the required and available attribute keys. Repetitions handling was also corrected in two ways: the fallback parser for stored rruleset values now avoids naive/aware datetime comparison errors and respects localized wall time across DST, and the repetitions view now anchors its list on the selected instance shown in Details rather than always starting from the current time. Regression tests were added for all of these cases.

Technical:
- 5 files changed, 130 insertions(+), 10134 deletions(-)

Note: Fixed bug in batch add involving repetitions across DST.

## 1.0.13 — 2026-03-12

Since 1.0.12:

Why upgrade:
- 1 additions, 0 fixes, 1 behavior changes.

Added:
- Updated README with GTD support and improve clarity in examples

Changed:
- update condition for checking needed keys in item parsing feat: handle trailing ampersand in frequency part and provide feedback for missing rrule frequency

Docs:
- update installation instructions for tklr in README.md
- update README to clarify reminder import behavior and jot handling
- update README to clarify jot recording behavior in inbox.txt

Technical:
- 3 files changed, 66 insertions(+), 6 deletions(-)

## 1.0.12 — 2026-03-10

Since 1.0.11:

Why upgrade:
- 1 additions, 1 fixes, 0 behavior changes.

Added:
- Added table of contents links in README for better navigation

Fixed:
- Update README to clarify tklr settings and migration process Correct description of the 'r' modifier in EditorScreen

Docs:
- Update README with migration command details and task modifier changes

Technical:
- 2 files changed, 24 insertions(+), 17 deletions(-)
