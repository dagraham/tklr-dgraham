from datetime import date, datetime, timedelta

import pytest

from tklr.item import parse_dt
from tklr.shared import split_period_offset


@pytest.mark.parametrize(
    "text, expected",
    [
        ("today + 90d", ("today", timedelta(days=90))),
        ("10/13 8:30p + 17h15", ("10/13 8:30p", timedelta(hours=17, minutes=15))),
        ("10/13 9a - 1w2d", ("10/13 9a", -timedelta(days=9))),
        ("today+1d12", ("today", timedelta(days=1, hours=12))),
        ("+2d", ("", timedelta(days=2))),
    ],
)
def test_split_period_offset(text, expected):
    assert split_period_offset(text) == expected


@pytest.mark.parametrize(
    "text",
    ["2026-10-13", "10/13 8:30p", "2026-10-13T08:30-04:00", "10/13 + 5x"],
)
def test_no_offset_detected(text):
    assert split_period_offset(text)[1] is None


def test_today_plus_days_is_a_date():
    assert parse_dt("today + 90d") == date.today() + timedelta(days=90)


def test_datetime_plus_hours_minutes():
    assert parse_dt("2026-10-13 8:30pm + 17h15") == datetime(2026, 10, 14, 13, 45)


def test_date_minus_days():
    assert parse_dt("2026-10-13 - 2d") == datetime(2026, 10, 11)


def test_date_plus_hours_becomes_datetime():
    assert parse_dt("2026-10-13 + 9h") == datetime(2026, 10, 13, 9, 0)


def test_offset_in_scheduled_entry(item_factory):
    with_offset = item_factory("* offset event @s 2026-10-13 8:30pm + 17h15 @e 1h")
    plain = item_factory("* offset event @s 2026-10-14 1:45pm @e 1h")
    assert with_offset.parse_ok, with_offset.parse_message
    assert with_offset.rruleset == plain.rruleset
