# Recent Changes

## 1.0.16 — 2026-03-23

Since 1.0.15:

Why upgrade:
- 0 additions, 0 fixes, 1 behavior changes.

Changed:
- Reverted last change. Show all instances of repeating events in Agenda view that fall within the relevant period.

Technical:
- 2 files changed, 26 deletions(-)

## 1.0.15 — 2026-03-22

Since 1.0.14:

Why upgrade:
- 0 additions, 0 fixes, 2 behavior changes.

Changed:
- Display on first instance of a repeating event in the events section of Agenda View.
- Clean up imports and remove unused FinishResult

Technical:
- 3 files changed, 135 insertions(+), 115 deletions(-)

## 1.0.14 — 2026-03-13

Since 1.0.13:

Why upgrade:
- 0 additions, 1 fixes, 0 behavior changes.

Fixed:
- Fixed several live-editing and recurrence regressions. Project entry feedback now preserves useful in-progress guidance: live @s parsing errors are no longer hidden by the project’s missing required @~ job, a bare trailing & in @r input is treated as an incomplete repetition modifier instead of an invalid frequency, and entering a bare @ still shows the required and available attribute keys. Repetitions handling was also corrected in two ways: the fallback parser for stored rruleset values now avoids naive/aware datetime comparison errors and respects localized wall time across DST, and the repetitions view now anchors its list on the selected instance shown in Details rather than always starting from the current time. Regression tests were added for all of these cases.

Technical:
- 5 files changed, 130 insertions(+), 10134 deletions(-)

Note: Fixed bug in batch add involving repetitions across DST.
