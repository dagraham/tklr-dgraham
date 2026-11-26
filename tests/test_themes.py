"""Themes: built-in palettes, inheritance, user themes and readability."""

import re
import tomllib
from pathlib import Path

import pytest

import tklr.shared as shared
from tklr import themes
from tklr.named_colors import css_named_colors

SRC = Path(themes.__file__).parent

# get_theme_palette() output for the two original themes, captured before
# themes became TOML files. Changing these changes what every user sees.
LEGACY_PALETTES = {'dark': {'active_bin_color': '#FFD700',
          'am_color': '#DAA520',
          'at_color': '#DAA520',
          'available_color': '#87CEFA',
          'bin_color': '#DAA520',
          'chore_color': '#F0E68C',
          'draft_color': '#FF4500',
          'event_color': '#32CD32',
          'finished_color': '#808080',
          'goal_color': '#EEE8AA',
          'goal_max_color': '#FFFF00',
          'goal_min_color': '#87CEFA',
          'header_color': '#FFFACD',
          'jot_color': '#00BFFF',
          'jot_extent': '#DA70D6',
          'jot_full': '#98FB98',
          'jot_none': '#00BFFF',
          'jot_use': '#DAA520',
          'label_color': '#87CEFA',
          'note_color': '#E9967A',
          'notice_color': '#FFD700',
          'pastdue_color': '#FF8C00',
          'task_color': '#87CEFA',
          'type_color': '#DAA520',
          'urgency_max_color': '#FFFF00',
          'urgency_min_color': '#87CEFA',
          'waiting_color': '#A9A9A9'},
 'light': {'active_bin_color': '#808000',
           'am_color': '#B22222',
           'at_color': '#B22222',
           'available_color': '#0000FF',
           'bin_color': '#A52A2A',
           'chore_color': '#556B2F',
           'draft_color': '#DC143C',
           'event_color': '#008000',
           'finished_color': '#708090',
           'goal_color': '#8A2BE2',
           'goal_max_color': '#B22222',
           'goal_min_color': '#4682B4',
           'header_color': '#2F4F4F',
           'jot_color': '#4169E1',
           'jot_extent': '#9932CC',
           'jot_full': '#008000',
           'jot_none': '#4169E1',
           'jot_use': '#B8860B',
           'label_color': '#4169E1',
           'note_color': '#8B4513',
           'notice_color': '#A52A2A',
           'pastdue_color': '#A52A2A',
           'task_color': '#0000FF',
           'type_color': '#B22222',
           'urgency_max_color': '#B22222',
           'urgency_min_color': '#4682B4',
           'waiting_color': '#2F4F4F'}}


@pytest.mark.parametrize("name", ["dark", "light"])
def test_builtin_palettes_unchanged(name):
    palette = shared.get_theme_palette(name)
    assert {k: palette[k] for k in LEGACY_PALETTES[name]} == LEGACY_PALETTES[name]


def test_every_builtin_theme_resolves_completely():
    names = list(themes.available_themes())
    assert names[:2] == ["dark", "light"]
    for name in names:
        t = themes.load_theme(name)
        assert set(t.ui) == set(themes.UI_KEYS), name
        assert set(t.palette) == set(themes.PALETTE_KEYS), name


def test_config_overrides_still_apply():
    palette = shared.get_theme_palette("light", {"light": {"note_color": "#123456"}})
    assert palette["note_color"] == "#123456"
    # Overrides are per theme name: [ui.palette.dark] doesn't touch nord.
    nord = shared.get_theme_palette("nord", {"dark": {"note_color": "#123456"}})
    assert nord["note_color"] != "#123456"


def _write(directory: Path, name: str, text: str) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    (directory / f"{name}.toml").write_text(text)


def test_user_theme_inherits_and_derives(tmp_path):
    _write(
        tmp_path / "themes",
        "paper",
        'base = "light"\n[ui]\nbackground = "#fdf6e3"\n[palette]\nevent_color = "#00aa00"\n',
    )
    t = themes.load_theme("paper", tmp_path)
    light = themes.load_theme("light")
    assert t.chain == ["paper", "light"]
    assert t.dark is False
    assert t.palette["event_color"] == "#00aa00"
    assert t.palette["note_color"] == light.palette["note_color"]
    # Colours derived from background follow the new background...
    assert t.ui["surface"] == t.ui["message_background"] == "#fdf6e3"
    # ...while unrelated ones are inherited.
    assert t.ui["rule"] == light.ui["rule"]


def test_user_theme_replaces_builtin(tmp_path):
    _write(tmp_path / "themes", "nord", 'base = "dark"\n[palette]\nnote_color = "#010203"\n')
    assert themes.load_theme("nord", tmp_path).palette["note_color"] == "#010203"
    assert themes.load_theme("nord").palette["note_color"] != "#010203"


def test_base_cycle_and_unknown_fall_back(tmp_path):
    _write(tmp_path / "themes", "a", 'base = "b"\n')
    _write(tmp_path / "themes", "b", 'base = "a"\n')
    with pytest.raises(themes.ThemeError, match="cycle"):
        themes.load_theme("a", tmp_path)
    resolved, warning = themes.resolve_theme("a", tmp_path)
    assert resolved.name == "dark" and "cycle" in warning
    resolved, warning = themes.resolve_theme("no-such-theme", tmp_path)
    assert resolved.name == "dark" and "unknown theme" in warning


def test_theme_without_base_must_be_complete(tmp_path):
    _write(tmp_path / "themes", "bare", '[ui]\nbackground = "#000000"\n')
    with pytest.raises(themes.ThemeError, match="missing"):
        themes.load_theme("bare", tmp_path)


def test_css_uses_only_defined_variables():
    css = (SRC / "view.css").read_text()
    used = set(re.findall(r"\$(tklr-[a-z-]+)", css))
    defined = set(themes.load_theme("dark").css_variables())
    assert used and used <= defined


def test_theme_files_are_packaged():
    pyproject = tomllib.loads((SRC.parents[1] / "pyproject.toml").read_text())
    patterns = pyproject["tool"]["setuptools"]["package-data"]["tklr"]
    assert "themes/*.toml" in patterns and "*.css" in patterns


# Busy-bar roles are filled blocks, not text; Rich's terminal colour names
# ("green", "white", ...) are drawn in the terminal's own palette.
_NOT_TEXT = {"busy_color", "conflict_color", "allday_color", "dim_style"}


def _hex(value: str) -> str | None:
    if value.lower() in shared._ANSI_NAMES:
        return None
    return value if value.startswith("#") else css_named_colors.get(value.lower())


@pytest.mark.parametrize("name", list(themes.available_themes()))
def test_theme_text_is_readable(name):
    """Every text colour reaches 3:1 against the background it's drawn on."""
    t = themes.load_theme(name)
    checks = [(k, v, t.ui["surface"]) for k, v in t.palette.items() if k not in _NOT_TEXT]
    checks += [(f"ui.{k}", t.ui[k], t.ui["background"]) for k in ("foreground", "accent")]
    checks += [(f"ui.{k}", t.ui[k], t.ui["surface"]) for k in ("text", "list_text", "emphasis")]
    checks.append(("ui.muted", t.ui["muted"], t.ui["message_background"]))
    low = []
    for key, color, bg in checks:
        fg = _hex(color)
        if fg is None:
            continue
        ratio = themes.contrast_ratio(fg, bg)
        if ratio is not None and ratio < 3.0:
            low.append(f"{key} {color} on {bg}: {ratio:.2f}")
    assert not low, f"{name}: " + "; ".join(low)
