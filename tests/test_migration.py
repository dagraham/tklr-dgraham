from tklr.migration import etm_to_jot_tokens, etm_to_tokens, format_subvalue


def make_item(**overrides):
    base = {
        "itemtype": "%",
        "summary": "Sample",
    }
    base.update(overrides)
    return base


def test_migration_appends_hashtags_to_existing_description():
    item = make_item(d="Keep this", t=["Personal Items", "acme"])
    tokens = etm_to_tokens(item, None, include_record_id=False, secret=None)

    assert "@d Keep this #Personal_Items #acme" in tokens


def test_migration_creates_description_when_only_tags_present():
    item = make_item(t=["blue green", "Odd"])
    tokens = etm_to_tokens(item, None, include_record_id=False, secret=None)

    assert "@d #blue_green #Odd" in tokens


def test_migration_handles_tags_before_description():
    item = {
        "itemtype": "%",
        "summary": "Out of order",
        "t": ["mixed case"],
        "d": "Base",
    }
    tokens = etm_to_tokens(item, None, include_record_id=False, secret=None)

    assert "@d Base #mixed_case" in tokens


def test_migration_generates_derived_jot_from_use_and_index_fields():
    item = {
        "created": "{T}:20260402T1155A",
        "itemtype": "-",
        "summary": "Tempora quaerat eius adipisci",
        "s": "{T}:20261204T0115A",
        "i": "$billing/Voluptatem, Etincidunt/project d1",
        "f": "{P}:20261204T0115A -> 20261204T0115A",
        "u": [
            [
                "{I}:1h30m",
                "{T}:20261204T0245A",
            ]
        ],
        "d": "Modi neque eius dolor modi quiquia eius tempora.",
        "t": ["lorem"],
        "k": [154, 52, 173],
    }

    jot_entries = etm_to_jot_tokens(item)

    assert jot_entries == [
        [
            "- Tempora quaerat eius adipisci",
            "@s 20261204T0245 z UTC",
            "@e 1h30m",
            "@u Etincidunt/project d1",
            "@b $billing/Voluptatem",
        ]
    ]


def test_migration_appends_etm_metadata_tags_to_description():
    item = {
        "created": "{T}:20260402T1155A",
        "modified": "{T}:20261204T1135A",
        "itemtype": "-",
        "summary": "Tempora quaerat eius adipisci",
        "d": "Modi neque eius dolor modi quiquia eius tempora.",
    }

    tokens = etm_to_tokens(item, "13", include_record_id=False, secret=None)

    created_tag = (
        format_subvalue(item["created"])[0]
        .replace("-", "")
        .replace(":", "")
        .replace(" ", "T")
    )
    modified_tag = (
        format_subvalue(item["modified"])[0]
        .replace("-", "")
        .replace(":", "")
        .replace(" ", "T")
    )
    metadata_tag = f"#etm13_{created_tag}_{modified_tag}"

    assert any(token.startswith("@d ") and metadata_tag in token for token in tokens)


def test_migration_creates_description_from_etm_metadata_when_absent():
    item = {
        "created": "{T}:20260402T1155A",
        "modified": "{T}:20261204T1135A",
        "itemtype": "-",
        "summary": "Tempora quaerat eius adipisci",
    }

    tokens = etm_to_tokens(item, "13", include_record_id=False, secret=None)

    created_tag = (
        format_subvalue(item["created"])[0]
        .replace("-", "")
        .replace(":", "")
        .replace(" ", "T")
    )
    modified_tag = (
        format_subvalue(item["modified"])[0]
        .replace("-", "")
        .replace(":", "")
        .replace(" ", "T")
    )
    metadata_tag = f"#etm13_{created_tag}_{modified_tag}"

    assert any(token.startswith("@d ") and metadata_tag in token for token in tokens)


def test_migration_index_field_maps_only_bin_portion_to_reminder_bin():
    item = {
        "itemtype": "-",
        "summary": "Adipisci est ipsum",
        "i": "$billing/Quisquam, Adipisci/project d1",
    }

    tokens = etm_to_tokens(item, None, include_record_id=False, secret=None)

    assert "@b $billing/Quisquam" in tokens
    assert "@b $billing/Quisquam, Adipisci/project d1" not in tokens


def test_migration_maps_etm_goal_q_field_to_target_token():
    item = {
        "created": "{T}:20260403T1517A",
        "itemtype": "~",
        "summary": "Quaerat sit neque non",
        "s": "{T}:20260304T0500A",
        "q": ["2", "w", []],
        "t": ["lorem"],
    }

    tokens = etm_to_tokens(item, "182", include_record_id=False, secret=None)

    assert "! Quaerat sit neque non" in tokens
    assert "@s 2026-03-04 00:00" in tokens
    assert "@t 2/1w" in tokens


def test_migration_maps_etm_recurrence_minutes_to_uppercase_M():
    item = {
        "created": "{T}:20260403T1517A",
        "itemtype": "*",
        "summary": "fall daylight -> standard time",
        "s": "{T}:20260304T0500A",
        "t": ["lorem"],
        "r": [
            {
                "r": "y",
                "M": [11],
                "w": ["{W}:1SU"],
                "h": [0, 1, 2, 3],
                "n": [30],
            }
        ],
    }

    tokens = etm_to_tokens(item, "191", include_record_id=False, secret=None)

    assert "@r y &m 11 &w 1SU &H 0, 1, 2, 3 &M 30" in tokens
    assert "@r y &m 11 &w 1SU &H 0, 1, 2, 3 &m 30" not in tokens


def test_migration_maps_etm_finish_pair_to_completion_datetime_only():
    item = {
        "created": "{T}:20260403T1517A",
        "itemtype": "-",
        "summary": "Tempora quaerat eius adipisci",
        "s": "{T}:20261204T0115A",
        "f": "{P}:20261204T0115A -> 20261204T0245A",
    }

    tokens = etm_to_tokens(item, "13", include_record_id=False, secret=None)

    assert "@f 2026-12-03 21:45" in tokens
    assert "@f 2026-12-03 20:15, 2026-12-03 21:45" not in tokens
