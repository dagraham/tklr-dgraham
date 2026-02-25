# Recent Changes

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

## 0.0.59 — 2026-02-24

Since 0.0.58:

Why upgrade:
- 1 additions, 0 fixes, 4 behavior changes.

Added:
- add recent_changes.md to track project changes

Changed:
- Update .githooks/commit-msg, .githooks/prepare-commit-msg, and 1 more
- Update index.md
- Update _config.yml
- Update bump.py

Docs:
- Update README.md

Technical:
- 6 files changed, 228 insertions(+), 35 deletions(-)

Note: first tag with the recent_changes messages
