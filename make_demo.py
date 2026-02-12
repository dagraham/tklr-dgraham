#!/usr/bin/env python3
"""Create a small, always-current demo database for recordings."""

from __future__ import annotations

import os
from datetime import datetime, timedelta

from tklr.controller import Controller
from tklr.item import Item
from tklr.tklr_env import TklrEnvironment


os.environ["TKLR_HOME"] = "/Users/dag/Projects/tklr-uv/demo"


def today() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def yesterday() -> str:
    return (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")


def tomorrow() -> str:
    return (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")


def build_entries() -> list[str]:
    return [
        f"* Client kickoff #work @s {today()} 10:00 @e 1h @b clients/acme",
        f"~ Send January invoice #finance @s {today()} 17:00 @p 1 @b admin/billing",
        f"~ Follow up with Sam #urgent @s {yesterday()} 16:00 @p 1",
        f"* Weekly review #ops @s {tomorrow()} 16:00 @e 45m @r w @b admin/review",
        f"* Call with London #timezone @s {today()} 09:00 z CET @e 30m @b clients/uk",
        f"~ Prepare Q1 proposal #proposal @s {tomorrow()} @p 2 @b clients/acme",
        f"* Deep work block #billable @s {today()} 13:00 @e 2h @b focus/time",
        f"~ Log billable hours #billable @s {today()} 18:00 @b admin/billing",
        f"! Billable target #billable @s {yesterday()} @t 20/1w",
        "% Client preferences @d Prefers weekly status email on Fridays. #client",
        "- Capture idea #idea",
        "? Draft: follow-up email template #draft",
        f"* Project check-in #project @s {tomorrow()} 11:00 @e 30m @b clients/acme",
    ]


def main() -> None:
    env = TklrEnvironment()
    env.ensure(init_config=True)
    controller = Controller(str(env.db_path), env, reset=True)

    count = 0
    for entry in build_entries():
        item = Item(raw=entry, env=env, final=True, controller=controller)
        if item.parse_ok:
            controller.add_item(item)
            count += 1
        else:
            print(f"parse failed: {entry}")
            print(f"  {item.parse_message}")

    controller.db_manager.populate_dependent_tables()
    print(f"Inserted {count} records into {env.db_path}.")


if __name__ == "__main__":
    main()
