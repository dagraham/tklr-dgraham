from datetime import datetime, timedelta, timezone

from tklr.item import Item


def _dt(y: int, m: int, d: int, hh: int = 0, mm: int = 0) -> datetime:
    return datetime(y, m, d, hh, mm, tzinfo=timezone.utc)


def _record_id_for_entry(test_controller, test_env, entry: str) -> int:
    item = Item(raw=entry, env=test_env, final=True, controller=test_controller)
    assert item.parse_ok, item.parse_message
    return test_controller.add_item(item)


def _tag_count(pages):
    return sum(len(tag_map) for _rows, tag_map in pages)


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


def test_completions_view_omits_midnight_time(test_controller, test_env):
    rid = _record_id_for_entry(
        test_controller, test_env, "~ completion formatting @s 2025-01-01"
    )
    test_controller.dayfirst = True
    test_controller.yearfirst = False
    test_controller.two_digit_year = False
    test_controller.AMPM = True

    completed_local = datetime(2025, 1, 5, 10, 15).astimezone()
    test_controller.db_manager.add_completion(rid, (completed_local, None))

    pages, _header = test_controller.get_completions()
    assert pages
    rows, _tag_map = pages[0]
    record_rows = [row for row in rows if "[/not bold]   [" in row]
    assert record_rows
    row_text = record_rows[0]
    assert "[not bold]05-01-2025[/not bold]" in row_text, row_text
    assert "00:00" not in row_text
    assert "12a" not in row_text


def test_completions_view_keeps_non_midnight_time(test_controller, test_env):
    rid = _record_id_for_entry(test_controller, test_env, "~ completion time @s 2025-01-01")
    test_controller.dayfirst = False
    test_controller.yearfirst = True
    test_controller.two_digit_year = True
    test_controller.AMPM = False

    test_controller.db_manager.add_completion(rid, (_dt(2025, 1, 5, 0, 0), None))
    cursor = test_controller.db_manager.cursor
    cursor.execute(
        "UPDATE Completions SET completed = ? WHERE record_id = ?",
        ("2025-01-05 10:15", rid),
    )
    test_controller.db_manager.conn.commit()

    pages, _header = test_controller.get_completions()
    assert pages
    rows, _tag_map = pages[0]
    record_rows = [row for row in rows if "[/not bold]   [" in row]
    assert record_rows
    assert "[not bold]25-01-05 10:15[/not bold]" in record_rows[0], record_rows[0]


def test_completions_view_paginates_when_tags_exhausted(test_controller, test_env):
    base_local = datetime(2025, 1, 1, 9, 0).astimezone()
    for i in range(30):
        rid = _record_id_for_entry(test_controller, test_env, f"~ completion row {i}")
        completed_local = base_local + timedelta(minutes=i)
        test_controller.db_manager.add_completion(rid, (completed_local, None))

    pages, _header = test_controller.get_completions()
    assert len(pages) >= 2
    assert _tag_count(pages) == 30


def test_completions_view_dims_unchanged_year_month_components(
    test_controller, test_env
):
    test_controller.dayfirst = False
    test_controller.yearfirst = True
    test_controller.two_digit_year = False
    test_controller.AMPM = False

    rid_new = _record_id_for_entry(test_controller, test_env, "~ newer completion")
    rid_old = _record_id_for_entry(test_controller, test_env, "~ older completion")
    test_controller.db_manager.add_completion(rid_new, (_dt(2025, 1, 5, 10, 15), None))
    test_controller.db_manager.add_completion(rid_old, (_dt(2025, 1, 3, 10, 15), None))

    pages, _header = test_controller.get_completions()
    assert pages
    rows, _tag_map = pages[0]
    record_rows = [row for row in rows if "[/not bold]   [" in row]
    assert len(record_rows) >= 2

    second_row = record_rows[1]
    dim = test_controller.dim_style
    assert f"[{dim}]2025[/{dim}]" in second_row, second_row
    assert f"[{dim}]01[/{dim}]" in second_row, second_row
