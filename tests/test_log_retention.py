from freezegun import freeze_time

from tklr.shared import bug_msg, log_msg
from tklr.tklr_env import TklrEnvironment, save_config_from_template


def _init_home_with_log_limit(tmp_path, monkeypatch, keep: int = 2):
    home = tmp_path / "tklr-home"
    monkeypatch.setenv("TKLR_HOME", str(home))
    env = TklrEnvironment()
    env.ensure(init_config=True)
    cfg = env.load_config()
    cfg.num_logs = keep
    save_config_from_template(cfg, env.config_path)
    return home


def test_daily_log_file_retention_for_log_and_bug(tmp_path, monkeypatch):
    home = _init_home_with_log_limit(tmp_path, monkeypatch, keep=2)

    for day in ("2026-01-01 10:00:00", "2026-01-02 10:00:00", "2026-01-03 10:00:00"):
        with freeze_time(day):
            log_msg("log entry")
            bug_msg("bug entry")

    log_files = sorted((home / "logs").glob("log_*.md"))
    bug_files = sorted((home / "logs").glob("bug_*.md"))

    assert [p.name for p in log_files] == ["log_260102.md", "log_260103.md"]
    assert [p.name for p in bug_files] == ["bug_260102.md", "bug_260103.md"]
