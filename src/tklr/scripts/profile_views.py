from __future__ import annotations

import argparse
import os
import shutil
from datetime import datetime, timedelta, time
from pathlib import Path

from tklr.cli.main import _group_instances_by_date_for_weeks
from tklr.controller import Controller
from tklr.item import Item
from tklr.model import DatabaseManager
from tklr.tklr_env import TklrEnvironment


BASE_HOME = Path(__file__).resolve().parent.parent / "src" / "tklr" / ".profile-home"


def bootstrap_env(home: Path) -> TklrEnvironment:
    """Create a fresh TKLR_HOME with config + database."""
    if home.exists():
        shutil.rmtree(home)
    home.mkdir(parents=True, exist_ok=True)
    os.environ["TKLR_HOME"] = str(home)

    env = TklrEnvironment()
    env.ensure(init_config=True, init_db_fn=lambda path: DatabaseManager(path, env).setup_database())
    return env


def populate_sample_data(controller: Controller, env: TklrEnvironment, *, events: int = 400, tasks: int = 600) -> None:
    """Insert synthetic events/tasks so agenda/weeks have something to chew on."""
    base = datetime.now().replace(hour=9, minute=0, second=0, microsecond=0)

    def add_entry(raw: str) -> None:
        item = Item(env=env, raw=raw, final=True)
        if item.parse_ok:
            controller.add_item(item)

    for i in range(events):
        start = base + timedelta(days=i % 30, hours=(i % 8))
        end = start + timedelta(hours=1)
        raw = f"* Sample Event {i} @s {start:%Y-%m-%d %H:%M} @e {end:%Y-%m-%d %H:%M}"
        add_entry(raw)

    for i in range(tasks):
        due = base + timedelta(days=i % 21)
        priority = (i % 5) + 1
        raw = f"~ Sample Task {i} @s {due:%Y-%m-%d} @p {priority}"
        add_entry(raw)

    controller.db_manager.populate_dependent_tables()


def run_agenda(controller: Controller, iterations: int) -> None:
    for _ in range(iterations):
        controller.get_agenda(yield_rows=True)


def run_weeks(controller: Controller, iterations: int, weeks_span: int) -> None:
    dbm = controller.db_manager
    for _ in range(iterations):
        start_date = datetime.now().date()
        start_monday = start_date - timedelta(days=start_date.weekday())
        end_sunday = start_monday + timedelta(weeks=weeks_span, days=6)
        start_dt = datetime.combine(start_monday, time(0, 0))
        end_dt = datetime.combine(end_sunday, time(23, 59))
        events = dbm.get_events_for_period(start_dt, end_dt)
        _group_instances_by_date_for_weeks(events, dbm, controller)


def main() -> None:
    parser = argparse.ArgumentParser(description="Profile agenda/weeks loading.")
    parser.add_argument("--mode", choices=["agenda", "weeks"], required=True)
    parser.add_argument("--iterations", type=int, default=50)
    parser.add_argument("--weeks-span", type=int, default=4, help="Number of weeks for the weeks run")
    parser.add_argument("--home", type=Path, default=BASE_HOME, help="Where to create the synthetic TKLR_HOME")
    args = parser.parse_args()

    env = bootstrap_env(args.home)
    controller = Controller(str(env.db_path), env, reset=False)
    populate_sample_data(controller, env)

    if args.mode == "agenda":
        run_agenda(controller, args.iterations)
    else:
        run_weeks(controller, args.iterations, args.weeks_span)


if __name__ == "__main__":
    main()
