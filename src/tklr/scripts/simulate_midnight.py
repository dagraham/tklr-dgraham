#!/usr/bin/env python3
"""
Launch the TKLR Textual UI with a simulated clock.

Time is frozen at 23:59 on the upcoming day (or a user-provided timestamp),
with `tick=True` so virtual time advances while the app is running. This allows
you to watch how Agenda/Weeks react as midnight passes without waiting in real
time.

Usage:
    python scripts/simulate_midnight.py
    python scripts/simulate_midnight.py --home ~/iCloud/tklr
    python scripts/simulate_midnight.py --start "2025-01-10 23:58"
"""

from __future__ import annotations

import argparse
import os
from datetime import datetime, timedelta

from freezegun import freeze_time

from tklr.cli.main import ensure_database
from tklr.tklr_env import TklrEnvironment
from tklr.controller import Controller
from tklr.view import DynamicViewApp


def _resolve_env(home: str | None) -> TklrEnvironment:
    if home:
        os.environ["TKLR_HOME"] = os.path.expanduser(home)

    env = TklrEnvironment()
    env.ensure(init_config=True, init_db_fn=lambda path: ensure_database(path, env))
    env.load_config()
    return env


def _compute_start(timestamp: str | None) -> datetime:
    if timestamp:
        try:
            return datetime.strptime(timestamp, "%Y-%m-%d %H:%M")
        except ValueError as exc:
            raise SystemExit(f"Could not parse --start '{timestamp}': {exc}") from exc

    now = datetime.now()
    default = now.replace(hour=23, minute=59, second=0, microsecond=0)
    if default <= now:
        default = (now + timedelta(days=1)).replace(
            hour=23, minute=59, second=0, microsecond=0
        )
    return default


def main() -> None:
    parser = argparse.ArgumentParser(description="Simulate the TKLR UI across midnight.")
    parser.add_argument(
        "--home",
        help="Override TKLR_HOME for this run (useful for iCloud-synced data).",
    )
    parser.add_argument(
        "--start",
        help="Explicit timestamp (YYYY-MM-DD HH:MM) to freeze. "
        "Defaults to 23:59 of the upcoming day.",
    )
    args = parser.parse_args()

    env = _resolve_env(args.home)
    controller = Controller(env.db_path, env)

    freeze_at = _compute_start(args.start)
    print(
        f"→ Freezing time at {freeze_at:%Y-%m-%d %H:%M} with tick=True.\n"
        "  Close the UI when you’re done observing the midnight rollover."
    )

    with freeze_time(freeze_at, tick=True):
        DynamicViewApp(controller).run()


if __name__ == "__main__":
    main()
