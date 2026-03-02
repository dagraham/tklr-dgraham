from datetime import date

import pytest


def _strip_markup(text: str) -> str:
    import re

    return re.sub(r"\[[^\]]+\]", "", text)


@pytest.mark.integration
def test_tasks_view_groups_contexts_and_jots(test_controller, item_factory, use_factory):
    use_factory("exercise.walking")

    entries = [
        "~ task in context @c errands",
        "~ task scheduled @s 2025-01-10",
        "~ task inbox",
        "- jot inbox",
        "- jot with extent @e 30m",
        "- jot with use @u exercise.walking",
    ]

    for entry in entries:
        item = item_factory(entry)
        assert item.parse_ok, item.parse_message
        test_controller.add_item(item)

    groups = test_controller.get_tasks_view_groups()
    by_context = {name: rows for name, rows in groups}

    assert "errands" in by_context
    assert "scheduled" in by_context
    assert "inbox" in by_context

    errands_rows = by_context["errands"]
    scheduled_rows = by_context["scheduled"]
    inbox_rows = by_context["inbox"]

    assert len(errands_rows) == 1
    assert "task in context" in errands_rows[0]["text"]

    assert len(scheduled_rows) == 1
    assert "task scheduled" in scheduled_rows[0]["text"]
    expected = test_controller.fmt_user_date_only(date(2025, 1, 10))
    assert expected in _strip_markup(scheduled_rows[0]["text"])

    assert len(inbox_rows) == 2
    inbox_text = " ".join(r["text"] for r in inbox_rows)
    assert "task inbox" in inbox_text
    assert "jot inbox" in inbox_text
    assert "jot with extent" not in inbox_text
    assert "jot with use" not in inbox_text


@pytest.mark.integration
def test_tasks_view_context_ordering(test_controller, item_factory):
    entries = [
        "~ waiting item @c waiting",
        "~ next item @c next",
        "~ alpha item @c alpha",
        "~ zebra item @c zebra",
        "~ someday item @c someday",
        "~ scheduled item @s 2025-01-10",
        "~ inbox item",
    ]

    for entry in entries:
        item = item_factory(entry)
        assert item.parse_ok, item.parse_message
        test_controller.add_item(item)

    groups = test_controller.get_tasks_view_groups()
    context_names = [name for name, _rows in groups]

    assert context_names == [
        "inbox",
        "waiting",
        "next",
        "alpha",
        "zebra",
        "someday",
        "scheduled",
    ]


@pytest.mark.integration
def test_tasks_view_scheduled_sorted_by_date(test_controller, item_factory):
    entries = [
        "~ zzz later @s 2025-01-20",
        "~ aaa sooner @s 2025-01-05",
    ]
    for entry in entries:
        item = item_factory(entry)
        assert item.parse_ok, item.parse_message
        test_controller.add_item(item)

    groups = dict(test_controller.get_tasks_view_groups())
    scheduled_rows = groups["scheduled"]

    assert "aaa sooner" in scheduled_rows[0]["text"]
    assert "zzz later" in scheduled_rows[1]["text"]


@pytest.mark.integration
def test_tasks_view_scheduled_rows_dim_unchanged_year_month(test_controller, item_factory):
    test_controller.dayfirst = False
    test_controller.yearfirst = True
    test_controller.two_digit_year = False

    entries = [
        "~ task one @s 2025-01-05",
        "~ task two @s 2025-01-20",
    ]
    for entry in entries:
        item = item_factory(entry)
        assert item.parse_ok, item.parse_message
        test_controller.add_item(item)

    groups = dict(test_controller.get_tasks_view_groups())
    scheduled_rows = groups["scheduled"]
    assert len(scheduled_rows) == 2

    first_text = scheduled_rows[0]["text"]
    second_text = scheduled_rows[1]["text"]
    dim = test_controller.dim_style

    assert "2025-01-05" in _strip_markup(first_text)
    assert "2025-01-20" in _strip_markup(second_text)
    assert f"[{dim}]2025[/{dim}]" in second_text
    assert f"[{dim}]01[/{dim}]" in second_text
