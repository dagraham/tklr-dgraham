from datetime import datetime, timezone

from tklr.item import Item


def _dt(y: int, m: int, d: int, hh: int = 0, mm: int = 0) -> datetime:
    return datetime(y, m, d, hh, mm, tzinfo=timezone.utc)


def _record_id_for_entry(test_controller, test_env, entry: str) -> int:
    item = Item(raw=entry, env=test_env, final=True, controller=test_controller)
    assert item.parse_ok, item.parse_message
    return test_controller.add_item(item)


def test_completion_retention_prunes_infinite_repeating_tasks(test_controller, test_env):
    test_controller.env.config.num_completions = 2
    rid = _record_id_for_entry(test_controller, test_env, "~ repeat forever @s 2025-01-01 @r d")

    db = test_controller.db_manager
    db.add_completion(rid, (_dt(2025, 1, 1, 10), None))
    db.add_completion(rid, (_dt(2025, 1, 2, 10), None))
    db.add_completion(rid, (_dt(2025, 1, 3, 10), None))

    db.cursor.execute("SELECT COUNT(*) FROM Completions WHERE record_id = ?", (rid,))
    assert db.cursor.fetchone()[0] == 2


def test_completion_retention_does_not_prune_finite_repeating_tasks(
    test_controller, test_env
):
    test_controller.env.config.num_completions = 2
    rid = _record_id_for_entry(
        test_controller,
        test_env,
        "~ repeat three times @s 2025-01-01 @r d &c 3",
    )

    db = test_controller.db_manager
    db.add_completion(rid, (_dt(2025, 1, 1, 10), None))
    db.add_completion(rid, (_dt(2025, 1, 2, 10), None))
    db.add_completion(rid, (_dt(2025, 1, 3, 10), None))

    db.cursor.execute("SELECT COUNT(*) FROM Completions WHERE record_id = ?", (rid,))
    assert db.cursor.fetchone()[0] == 3


def test_completion_retention_zero_keeps_all(test_controller, test_env):
    test_controller.env.config.num_completions = 0
    rid = _record_id_for_entry(test_controller, test_env, "~ keep all @s 2025-01-01 @r d")

    db = test_controller.db_manager
    db.add_completion(rid, (_dt(2025, 1, 1, 10), None))
    db.add_completion(rid, (_dt(2025, 1, 2, 10), None))
    db.add_completion(rid, (_dt(2025, 1, 3, 10), None))

    db.cursor.execute("SELECT COUNT(*) FROM Completions WHERE record_id = ?", (rid,))
    assert db.cursor.fetchone()[0] == 3
