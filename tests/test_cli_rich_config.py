import importlib

import pytest
from click.testing import CliRunner

from tklr.model import DatabaseManager
from tklr.tklr_env import TklrConfig, TklrEnvironment, save_config_from_template


def _prepare_home(monkeypatch, tmp_path, cli_rich: bool):
    home = tmp_path / "home"
    home.mkdir()

    monkeypatch.setenv("TKLR_HOME", str(home))
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)

    env = TklrEnvironment()
    config = TklrConfig()
    config.ui.cli_rich = cli_rich
    save_config_from_template(config, env.config_path)
    dbm = DatabaseManager(str(env.db_path), env)
    dbm.conn.close()
    return env


def _reload_cli():
    import tklr.cli.main as cli_main

    return importlib.reload(cli_main)


class FakeConsole:
    instances = []

    def __init__(self, *args, **kwargs):
        self.kwargs = kwargs
        type(self).instances.append(self)

    def print(self, *args, **kwargs):
        return None


class _FakeDBManager:
    def get_events_for_period(self, start_dt, end_dt):
        return []


class FakeController:
    def __init__(self, db_path, env):
        self.db_manager = _FakeDBManager()
        self.AMPM = env.config.ui.ampm

    def get_agenda(self, yield_rows=False):
        return []


@pytest.mark.unit
@pytest.mark.parametrize("command", ["agenda", "days", "weeks"])
def test_cli_rich_uses_config_default(monkeypatch, tmp_path, command):
    _prepare_home(monkeypatch, tmp_path, cli_rich=True)
    cli_main = _reload_cli()
    FakeConsole.instances = []
    monkeypatch.setattr(cli_main, "Console", FakeConsole)
    monkeypatch.setattr(cli_main, "Controller", FakeController)

    runner = CliRunner()
    result = runner.invoke(cli_main.cli, [command])

    assert result.exit_code == 0
    assert len(FakeConsole.instances) == 1
    assert FakeConsole.instances[0].kwargs["markup"] is True
    assert FakeConsole.instances[0].kwargs["no_color"] is False


@pytest.mark.unit
@pytest.mark.parametrize("command", ["agenda", "days", "weeks"])
def test_cli_plain_overrides_config_default(monkeypatch, tmp_path, command):
    _prepare_home(monkeypatch, tmp_path, cli_rich=True)
    cli_main = _reload_cli()
    FakeConsole.instances = []
    monkeypatch.setattr(cli_main, "Console", FakeConsole)
    monkeypatch.setattr(cli_main, "Controller", FakeController)

    runner = CliRunner()
    result = runner.invoke(cli_main.cli, [command, "--plain"])

    assert result.exit_code == 0
    assert len(FakeConsole.instances) == 1
    assert FakeConsole.instances[0].kwargs["markup"] is False
    assert FakeConsole.instances[0].kwargs["no_color"] is True


@pytest.mark.unit
@pytest.mark.parametrize("command", ["agenda", "days", "weeks"])
def test_cli_rich_overrides_plain_config_default(monkeypatch, tmp_path, command):
    _prepare_home(monkeypatch, tmp_path, cli_rich=False)
    cli_main = _reload_cli()
    FakeConsole.instances = []
    monkeypatch.setattr(cli_main, "Console", FakeConsole)
    monkeypatch.setattr(cli_main, "Controller", FakeController)

    runner = CliRunner()
    result = runner.invoke(cli_main.cli, [command, "--rich"])

    assert result.exit_code == 0
    assert len(FakeConsole.instances) == 1
    assert FakeConsole.instances[0].kwargs["markup"] is True
    assert FakeConsole.instances[0].kwargs["no_color"] is False
