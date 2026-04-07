from click.testing import CliRunner

from tklr.cli.main import cli


def test_cli_urgency_report_runs(monkeypatch, tmp_path):
    home = tmp_path / "home"
    home.mkdir()

    monkeypatch.setenv("TKLR_HOME", str(home))
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)

    runner = CliRunner()
    result = runner.invoke(cli, ["urgency-report"])

    assert result.exit_code == 0
    assert "Urgency screening report (base)" in result.output
    assert "Current urgency settings:" in result.output
    assert "due:" in result.output
    assert "priority:" in result.output
    assert "run1" in result.output
    assert "run8" in result.output


def test_cli_urgency_report_json_runs(monkeypatch, tmp_path):
    home = tmp_path / "home"
    home.mkdir()

    monkeypatch.setenv("TKLR_HOME", str(home))
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)

    runner = CliRunner()
    result = runner.invoke(cli, ["urgency-report", "--json"])

    assert result.exit_code == 0
    assert '"label"' in result.output
    assert '"urgency"' in result.output


def test_cli_urgency_report_now_option_runs(monkeypatch, tmp_path):
    home = tmp_path / "home"
    home.mkdir()

    monkeypatch.setenv("TKLR_HOME", str(home))
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["urgency-report", "--now", "2026-04-01 12:00"],
    )

    assert result.exit_code == 0
    assert "Urgency screening report (base)" in result.output
    assert "run1" in result.output
    assert "run8" in result.output


def test_cli_urgency_report_now_option_json_runs(monkeypatch, tmp_path):
    home = tmp_path / "home"
    home.mkdir()

    monkeypatch.setenv("TKLR_HOME", str(home))
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["urgency-report", "--json", "--now", "2026-04-01 12:00"],
    )

    assert result.exit_code == 0
    assert '"label"' in result.output
    assert '"urgency"' in result.output


def test_cli_urgency_report_structure_design_runs(monkeypatch, tmp_path):
    home = tmp_path / "home"
    home.mkdir()

    monkeypatch.setenv("TKLR_HOME", str(home))
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)

    runner = CliRunner()
    result = runner.invoke(cli, ["urgency-report", "--design", "structure"])

    assert result.exit_code == 0
    assert "Urgency screening report (structure)" in result.output
    assert "Current urgency settings:" in result.output
    assert "run1" in result.output
    assert "run8" in result.output


def test_cli_urgency_report_structure_design_json_runs(monkeypatch, tmp_path):
    home = tmp_path / "home"
    home.mkdir()

    monkeypatch.setenv("TKLR_HOME", str(home))
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)

    runner = CliRunner()
    result = runner.invoke(cli, ["urgency-report", "--json", "--design", "structure"])

    assert result.exit_code == 0
    assert '"label"' in result.output
    assert '"urgency"' in result.output
