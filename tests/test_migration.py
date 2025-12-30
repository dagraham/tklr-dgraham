from tklr.migration import etm_to_tokens


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
