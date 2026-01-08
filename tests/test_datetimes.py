import os
import time

import pytest

from tklr.tklr_env import TklrEnvironment
from tklr.model import DatabaseManager
from tklr.item import Item


@pytest.mark.parametrize("tz_name", ["Etc/GMT+5"])
def test_rdate_rows_use_local_time(tmp_path, monkeypatch, tz_name):
    """
    Regression test: RDATE-only reminders must emit local-naive timestamps
    into DateTimes even though the rruleset stores UTC ('...Z').
    """

    monkeypatch.setenv("TZ", tz_name)
    if hasattr(time, "tzset"):
        time.tzset()

    home = tmp_path / "tklr-home"
    monkeypatch.setenv("TKLR_HOME", str(home))

    env = TklrEnvironment()
    env.ensure(init_config=True, init_db_fn=None)

    dbm = DatabaseManager(str(env.db_path), env, reset=True, auto_populate=False)

    single = Item(env=env, raw="* single @s 2026-01-08 11:00 @e 1h", final=True)
    recurring = Item(
        env=env,
        raw="* repeating @s 2026-01-08 11:00 @e 1h @r w",
        final=True,
    )

    single_id = dbm.add_item(single)
    repeat_id = dbm.add_item(recurring)

    dbm.generate_datetimes_for_record(single_id, clear_existing=True)
    dbm.generate_datetimes_for_record(repeat_id, clear_existing=True)
    dbm.conn.commit()

    (rruleset_single,) = dbm.cursor.execute(
        "SELECT rruleset FROM Records WHERE id=?", (single_id,)
    ).fetchone()
    assert "RDATE:20260108T1600Z" in rruleset_single

    rows = dbm.cursor.execute(
        "SELECT start_datetime FROM DateTimes WHERE record_id=? ORDER BY start_datetime",
        (single_id,),
    ).fetchall()
    assert rows == [("20260108T1100",)]

    repeat_rows = dbm.cursor.execute(
        "SELECT start_datetime FROM DateTimes WHERE record_id=? ORDER BY start_datetime LIMIT 2",
        (repeat_id,),
    ).fetchall()
    assert repeat_rows[0][0].endswith("1100")
    assert repeat_rows[1][0].endswith("1100")

    dbm.conn.close()
