# Recent Changes

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

## 0.0.62 — 2026-02-25

Since 0.0.61:

Why upgrade:
- 2 additions, 1 fixes, 3 behavior changes.

Added:
- Implement completion deduplication script and enhance Controller and DatabaseManager for completion management
- Add record_completions parameter to Controller methods and enhance completion handling in DatabaseManager

Fixed:
- Fix typo in README.md for token keys section description

Changed:
- Enhance config.toml with additional settings for num_completions, minutes, and UI palette overrides
- Comment out completions section in item.py for future reference
- Update src/tklr/item.py

Docs:
- Clarify token keys section in README.md and update description for automatic generation from source code
- Update README.md token keys section for clarity and formatting
- Enhance README.md token keys section and update update_readme.py for improved sorting of token rows
- Update README.md and update_readme.py for improved token display logic and formatting

Technical:
- 10 files changed, 624 insertions(+), 57 deletions(-)
