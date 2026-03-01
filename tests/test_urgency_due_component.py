from tklr.model import UrgencyComputer, td_str_to_seconds


def test_urgency_due_is_zero_when_due_is_beyond_due_interval(test_env):
    uc = UrgencyComputer(test_env)
    due_max = float(test_env.config.urgency.due.max)
    interval_seconds = td_str_to_seconds(test_env.config.urgency.due.interval)

    now = 1_000_000
    due_far = now + interval_seconds + 60
    due_score = uc.urgency_due(due_far, now)

    assert due_max > 0
    assert interval_seconds > 0
    assert due_score == 0.0


def test_urgency_due_reaches_max_at_due_datetime(test_env):
    uc = UrgencyComputer(test_env)
    due_max = float(test_env.config.urgency.due.max)
    now = 1_000_000

    due_score = uc.urgency_due(now, now)
    assert due_score == due_max
