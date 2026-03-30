import re
from datetime import datetime

import pytest


def _strip_markup(text: str) -> str:
    return re.sub(r"\[[^\]]+\]", "", text)


def _add_entry(test_controller, item_factory, entry: str) -> None:
    item = item_factory(entry)
    assert item.parse_ok, item.parse_message
    test_controller.add_item(item)


@pytest.mark.integration
def test_agenda_tasks_due_prefix_for_overdue_and_next_week(
    test_controller, item_factory
):
    _add_entry(test_controller, item_factory, "~ overdue task @s 2025-01-06")
    _add_entry(test_controller, item_factory, "~ due today task @s 2025-01-10")
    _add_entry(test_controller, item_factory, "~ due soon task @s 2025-01-13")
    _add_entry(test_controller, item_factory, "~ due later task @s 2025-01-20")
    test_controller.db_manager.populate_dependent_tables(force=True)

    rows = test_controller.get_agenda_tasks(now=datetime(2025, 1, 10, 12, 0))
    texts = [_strip_markup(r["text"]) for r in rows if r.get("record_id") is not None]

    overdue = next(t for t in texts if "overdue task" in t)
    today = next(t for t in texts if "due today task" in t)
    soon = next(t for t in texts if "due soon task" in t)
    later = next(t for t in texts if "due later task" in t)

    assert "-4d overdue task" in overdue
    assert "+0d due today task" in today
    assert "+3d due soon task" in soon
    assert "+10d due later task" in later


@pytest.mark.integration
def test_agenda_tasks_due_prefix_uses_current_date_not_time(
    test_controller, item_factory
):
    _add_entry(test_controller, item_factory, "~ morning deadline @s 2025-01-10 09:00")
    test_controller.db_manager.populate_dependent_tables(force=True)

    rows = test_controller.get_agenda_tasks(now=datetime(2025, 1, 10, 18, 0))
    texts = [_strip_markup(r["text"]) for r in rows if r.get("record_id") is not None]
    row = next(t for t in texts if "morning deadline" in t)

    assert "+0d morning deadline" in row
