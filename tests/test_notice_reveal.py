from datetime import datetime, timedelta

import tklr.model as model


def _agenda_record_ids(test_controller):
    return {row[0] for row in test_controller.db_manager.get_urgency()}


def test_notice_hidden_task_appears_when_window_opens(
    test_controller, item_factory, monkeypatch
):
    # Due in 2 days + 1 hour with @n 2d: notice window opens 1 hour from now.
    due = (datetime.now() + timedelta(days=2, hours=1)).replace(second=0, microsecond=0)
    item = item_factory(f"~ notice test @s {due:%Y-%m-%d %H:%M} @n 2d")
    assert item.parse_ok, item.parse_message
    rid = test_controller.add_item(item)
    db = test_controller.db_manager

    assert rid not in _agenda_record_ids(test_controller)

    # Two hours later, with no save and no rebuild in between.
    later = model.utc_now_to_seconds() + 2 * 3600
    monkeypatch.setattr(model, "utc_now_to_seconds", lambda: later)

    assert rid in _agenda_record_ids(test_controller)
    assert db.urgency_revealed_between(later - 3 * 3600, later)
    assert not db.urgency_revealed_between(later, later + 60)
