from tklr.tklr_env import PriorityConfig


def test_priority_config_defaults_to_first_through_fifth():
    cfg = PriorityConfig.model_validate(None)
    assert cfg.root == {
        "first": 10.0,
        "second": 8.0,
        "third": 5.0,
        "fourth": 2.0,
        "fifth": -5.0,
    }


def test_priority_config_migrates_legacy_names():
    cfg = PriorityConfig.model_validate(
        {
            "next": 9,
            "high": 7,
            "medium": 4,
            "low": 1,
            "someday": -4,
        }
    )
    assert cfg.root == {
        "first": 9.0,
        "second": 7.0,
        "third": 4.0,
        "fourth": 1.0,
        "fifth": -4.0,
    }


def test_priority_config_migrates_numeric_names():
    cfg = PriorityConfig.model_validate({"1": 11, "3": 6, "5": -6})
    assert cfg.root == {
        "first": 11.0,
        "second": 8.0,
        "third": 6.0,
        "fourth": 2.0,
        "fifth": -6.0,
    }

