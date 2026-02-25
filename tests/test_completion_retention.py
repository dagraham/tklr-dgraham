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


def test_delete_completion_by_id(test_controller, test_env):
    rid = _record_id_for_entry(test_controller, test_env, "~ delete one @s 2025-01-01")
    db = test_controller.db_manager
    db.add_completion(rid, (_dt(2025, 1, 1, 10), None))
    db.add_completion(rid, (_dt(2025, 1, 2, 10), None))

    rows = db.get_all_completions_with_ids()
    assert len(rows) == 2
    completion_id = rows[0][0]

    assert db.delete_completion(completion_id) is True
    assert db.delete_completion(completion_id) is False

    remaining_ids = [row[0] for row in db.get_all_completions_with_ids()]
    assert completion_id not in remaining_ids
    assert len(remaining_ids) == 1


def test_completions_view_tag_map_includes_completion_id(test_controller, test_env):
    rid = _record_id_for_entry(
        test_controller, test_env, "~ completion tags @s 2025-01-01"
    )
    db = test_controller.db_manager
    db.add_completion(rid, (_dt(2025, 1, 3, 10), None))

    pages, _header = test_controller.get_completions()
    assert pages
    _rows, tag_map = pages[0]
    assert tag_map

    first_payload = next(iter(tag_map.values()))
    assert first_payload[0] == rid
    completion_id = first_payload[2]
    assert isinstance(completion_id, int)

    db.cursor.execute("SELECT id FROM Completions WHERE record_id = ?", (rid,))
    known_ids = {row[0] for row in db.cursor.fetchall()}
    assert completion_id in known_ids
