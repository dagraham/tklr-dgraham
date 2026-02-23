def test_urgency_rebuilds_when_priority_config_changes(test_controller):
    db = test_controller.db_manager

    # Seed derived-state entries.
    db.populate_dependent_tables(force=True)
    before = db._get_state_value("urgency", {}) or {}
    before_cfg = before.get("config_version")
    assert before_cfg

    # Change urgency config only (no record changes).
    priority_cfg = test_controller.env.config.urgency.priority.root
    priority_cfg["first"] = float(priority_cfg.get("first", 10.0)) + 1.0

    db.populate_dependent_tables(force=False)
    after = db._get_state_value("urgency", {}) or {}
    after_cfg = after.get("config_version")

    assert after_cfg
    assert after_cfg != before_cfg
