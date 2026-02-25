# Recent Changes

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

## 0.0.61 — 2026-02-25

Since 0.0.60:

Why upgrade:
- Mostly maintenance/internal updates in this release.

Docs:
- Update README.md token keys section for improved formatting and adjust update_readme.py for better handling of empty types and keys
- Refactor token keys section in README.md for clarity and simplify type formatting in update_readme.py
- Enhance README.md with examples for jotting reminders and update token keys table for clarity
- Update README.md with token keys section and enhance update_readme.py for dynamic content generation
- Update README.md

Internal:
- Refactor token handling for completions: update '@k' to 'kompletions', enforce positive integer validation, and adjust related tests for improved error messaging.

Technical:
- 6 files changed, 360 insertions(+), 42 deletions(-)

## 0.0.60 — 2026-02-24

Since 0.0.59:

Why upgrade:
- 0 additions, 0 fixes, 2 behavior changes.

Changed:
- Update src/tklr/controller.py
- Update .github/workflows/sync-recent-changes-discussion.yml and scripts/sync_recent_changes_discussion.py

Docs:
- Update README.md

Internal:
- Refactor inbox entry normalization and logging; adjust sync interval
- Update src/tklr/controller.py and tests/test_inbox_sync.py

Technical:
- 7 files changed, 217 insertions(+), 14 deletions(-)
