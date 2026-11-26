"""Colour themes.

A theme is one TOML file. Built-in themes live in ``tklr/themes/``; users can
add themes, or replace a built-in one, in ``$TKLR_HOME/themes/``. A theme may
name a ``base`` theme and then only list the colours that differ::

    name = "nord"
    base = "dark"

    [ui]        # window colours (Textual CSS variables $tklr-<key>)
    background = "#2e3440"

    [palette]   # colours used in reminder text, lists and details
    event_color = "#a3be8c"

Keys are resolved, lowest to highest priority: base theme(s), the theme file,
then ``[ui.palette.<theme>]`` in config.toml (palette keys only).

When a theme sets one of the core ``[ui]`` colours (background, foreground,
rule) but not a colour normally derived from it, the derived colour follows
the theme's own core colour instead of the base theme's. So a light theme with
a cream background doesn't inherit the white input fields of ``light``.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path

BUILTIN_DIR = Path(__file__).with_name("themes")
DEFAULT_THEME = "dark"

# [ui] keys, each becoming the Textual CSS variable $tklr-<key with "-">.
UI_KEYS: tuple[str, ...] = (
    "background",  # screen background
    "foreground",  # titles, footer text
    "text",  # details and tree text
    "list_text",  # list text (a Rich colour; "white" follows the terminal)
    "muted",  # prompt messages and instructions
    "rule",  # borders and separators
    "dim_rule",  # the faint horizontal rule in prompts
    "accent",  # live feedback in the entry prompts
    "emphasis",  # highlighted details text
    "surface",  # lists, details pane, help, bins tree
    "message_background",  # prompt message and instruction rows
    "input_background",  # focused entry fields
    "input_border",  # focused entry field border
    "highlight",  # cursor row in the bins tree
)

# derived key -> core key it follows when a theme sets only the core key.
UI_DERIVED: dict[str, str] = {
    "text": "foreground",
    "list_text": "foreground",
    "muted": "foreground",
    "emphasis": "foreground",
    "dim_rule": "rule",
    "input_border": "rule",
    "surface": "background",
    "message_background": "background",
    "input_background": "background",
    "highlight": "background",
}

# The palette roles shipped before themes were files, in their original order.
LEGACY_PALETTE_KEYS: tuple[str, ...] = (
    "label_color",
    "type_color",
    "at_color",
    "am_color",
    "header_color",
    "event_color",
    "available_color",
    "task_color",
    "waiting_color",
    "finished_color",
    "note_color",
    "pastdue_color",
    "notice_color",
    "goal_color",
    "draft_color",
    "bin_color",
    "active_bin_color",
    "chore_color",
    "jot_color",
    "jot_none",
    "jot_extent",
    "jot_use",
    "jot_full",
    "urgency_min_color",
    "urgency_max_color",
    "goal_min_color",
    "goal_max_color",
)

# Roles that used to be hard-coded per theme in controller.py and view.py.
EXTRA_PALETTE_KEYS: tuple[str, ...] = (
    "title_color",  # screen and help titles
    "footer_color",  # key hints in footers
    "dim_style",  # Rich style for de-emphasised text ("dim" or a colour)
    "busy_color",  # busy bar: busy period
    "conflict_color",  # busy bar: overlapping events
    "allday_color",  # busy bar: all-day event
    "busy_header_color",  # busy bar: day names and frame
    "match_color",  # search matches
    "status_info",  # status line messages
    "status_warning",
    "status_error",
)

PALETTE_KEYS: tuple[str, ...] = LEGACY_PALETTE_KEYS + EXTRA_PALETTE_KEYS

# Palette roles that are Rich styles rather than colours.
NON_COLOR_KEYS = frozenset({"dim_style"})


class ThemeError(ValueError):
    pass


@dataclass
class ResolvedTheme:
    name: str
    dark: bool
    textual: str  # Textual base theme for its own widgets (inputs, toasts, ...)
    ui: dict[str, str]
    palette: dict[str, str]
    chain: list[str] = field(default_factory=list)  # name, base, base's base, ...
    credit: str = ""

    def css_variables(self) -> dict[str, str]:
        return {f"tklr-{k.replace('_', '-')}": v for k, v in self.ui.items()}


def theme_dirs(home: Path | str | None = None) -> list[Path]:
    """Directories searched for themes, highest priority first."""
    dirs: list[Path] = []
    if home:
        dirs.append(Path(home).expanduser() / "themes")
    dirs.append(BUILTIN_DIR)
    return dirs


def available_themes(home: Path | str | None = None) -> dict[str, Path]:
    """Theme name -> file. A user theme replaces a built-in of the same name."""
    found: dict[str, Path] = {}
    for directory in reversed(theme_dirs(home)):
        if not directory.is_dir():
            continue
        for path in sorted(directory.glob("*.toml")):
            found[path.stem] = path
    # dark and light first, then alphabetical
    order = sorted(found, key=lambda n: (n not in ("dark", "light"), n != "dark", n))
    return {name: found[name] for name in order}


def _read(path: Path) -> dict:
    try:
        with path.open("rb") as fh:
            data = tomllib.load(fh)
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise ThemeError(f"cannot read theme {path}: {exc}") from exc
    for section in ("ui", "palette"):
        values = data.get(section, {})
        if not isinstance(values, dict):
            raise ThemeError(f"{path}: [{section}] must be a table")
        bad = [k for k, v in values.items() if not isinstance(v, str)]
        if bad:
            raise ThemeError(f"{path}: [{section}] values must be strings: {bad}")
    return data


def _resolve(
    name: str, files: dict[str, Path], seen: tuple[str, ...]
) -> ResolvedTheme:
    if name in seen:
        cycle = " -> ".join(seen + (name,))
        raise ThemeError(f"theme base cycle: {cycle}")
    path = files.get(name)
    if path is None:
        raise ThemeError(f"unknown theme {name!r}")
    data = _read(path)
    ui_own = {k: v.strip() for k, v in data.get("ui", {}).items() if k in UI_KEYS}
    pal_own = {
        k: v.strip() for k, v in data.get("palette", {}).items() if k in PALETTE_KEYS
    }
    base_name = data.get("base")

    if base_name:
        base = _resolve(str(base_name), files, seen + (name,))
        ui = dict(base.ui)
        for key, core in UI_DERIVED.items():
            if key not in ui_own and core in ui_own:
                ui[key] = ui_own[core]
        ui.update(ui_own)
        palette = dict(base.palette)
        palette.update(pal_own)
        dark = bool(data.get("dark", base.dark))
        textual = str(data.get("textual", base.textual))
        chain = [name] + base.chain
    else:
        missing = [k for k in UI_KEYS if k not in ui_own] + [
            k for k in PALETTE_KEYS if k not in pal_own
        ]
        if missing:
            raise ThemeError(
                f"{path}: a theme without a base must set every key; missing {missing}"
            )
        ui, palette = ui_own, pal_own
        dark = bool(data.get("dark", True))
        textual = str(data.get("textual", "textual-dark" if dark else "textual-light"))
        chain = [name]

    return ResolvedTheme(
        name=name,
        dark=dark,
        textual=textual,
        ui=ui,
        palette=palette,
        chain=chain,
        credit=str(data.get("credit", "")),
    )


def load_theme(name: str, home: Path | str | None = None) -> ResolvedTheme:
    """Resolve ``name`` (and its bases). Raises ThemeError."""
    return _resolve(name, available_themes(home), ())


def resolve_theme(
    name: str | None, home: Path | str | None = None
) -> tuple[ResolvedTheme, str | None]:
    """Like load_theme, but falls back to the default theme with a warning."""
    name = (name or DEFAULT_THEME).strip() or DEFAULT_THEME
    try:
        return load_theme(name, home), None
    except ThemeError as exc:
        warning = f"Theme {name!r} not usable ({exc}); using {DEFAULT_THEME!r}."
    try:
        return load_theme(DEFAULT_THEME, home), warning
    except ThemeError:
        # A broken user dark.toml must not stop tklr from starting.
        return load_theme(DEFAULT_THEME, None), warning


# ── Contrast (WCAG 2.x) ─────────────────────────────────────────────


def _hex_to_rgb(value: str) -> tuple[float, float, float] | None:
    v = value.strip().lstrip("#")
    if len(v) == 3:
        v = "".join(c * 2 for c in v)
    if len(v) != 6:
        return None
    try:
        return tuple(int(v[i : i + 2], 16) / 255 for i in (0, 2, 4))  # type: ignore[return-value]
    except ValueError:
        return None


def _luminance(rgb: tuple[float, float, float]) -> float:
    def channel(c: float) -> float:
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = (channel(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast_ratio(fg: str, bg: str) -> float | None:
    a, b = _hex_to_rgb(fg), _hex_to_rgb(bg)
    if a is None or b is None:
        return None
    la, lb = sorted((_luminance(a), _luminance(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)
