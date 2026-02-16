import importlib

import pytest
from click.testing import CliRunner


@pytest.mark.unit
def test_help_does_not_require_config(monkeypatch, tmp_path):
    home = tmp_path / "home"
    xdg = tmp_path / "xdg"

    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(xdg))
    monkeypatch.delenv("TKLR_HOME", raising=False)

    import tklr.cli.main as cli_main

    importlib.reload(cli_main)

    runner = CliRunner()
    result = runner.invoke(cli_main.cli, ["--help"])

    assert result.exit_code == 0
    assert "Usage:" in result.output
    assert not (xdg / "tklr" / "config.toml").exists()
