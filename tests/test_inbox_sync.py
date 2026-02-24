from datetime import datetime

import pytest

from tklr.item import Item


@pytest.mark.unit
@pytest.mark.parametrize(
    ("entry", "expected"),
    [
        ("* kickoff", "? * kickoff"),
        ("~ task", "? ~ task"),
        ("^ project", "? ^ project"),
        ("! goal", "? ! goal"),
        ("% note", "? % note"),
    ],
)
def test_normalize_inbox_keeps_prefixed_itemtype(test_controller, entry, expected):
    normalized = test_controller._normalize_inbox_entry(entry)
    assert normalized == expected


@pytest.mark.unit
def test_normalize_inbox_keeps_jot_type_for_auto_schedule(test_controller, frozen_time):
    normalized = test_controller._normalize_inbox_entry("- jot entry")
    assert normalized == "- jot entry"

    item = Item(
        raw=normalized,
        env=test_controller.env,
        controller=test_controller,
        final=True,
    )
    assert item.parse_ok, item.parse_message
    assert item.itemtype == "-"
    assert item.auto_log_timestamp == datetime.now().astimezone()
    assert any(
        tok.get("t") == "@" and tok.get("k") == "s" for tok in item.relative_tokens
    )
