from pathlib import Path
import os
import tomllib
from pydantic import BaseModel, Field, ValidationError
from typing import Optional


# ─── Config Schema ─────────────────────────────────────────────────
class UIConfig(BaseModel):
    theme: str = Field("dark", pattern="^(dark|light)$")
    show_completed: bool = True


class PathsConfig(BaseModel):
    db: str = "tklr.db"


class TklrConfig(BaseModel):
    title: str = "Tklr Configuration"
    ui: UIConfig = UIConfig()
    paths: PathsConfig = PathsConfig()


# ─── Commented Template ────────────────────────────────────
CONFIG_TEMPLATE = """\
title = {title}

[ui]
# theme: str = 'dark' | 'light'
theme = {ui.theme}

# show_completed: bool
show_completed = {ui.show_completed}

[paths]
# db: str = path to SQLite database file
db = {paths.db}
"""

# ─── Format Values as TOML Literals ──────────────────────────────


def format_value(value):
    if isinstance(value, bool):
        return "true" if value else "false"
    elif isinstance(value, (int, float)):
        return str(value)
    elif isinstance(value, str):
        return f'"{value}"'
    else:
        raise TypeError(f"Unsupported value type: {type(value)}")


# ─── Save Config with Comments ───────────────────────────────


def save_config_from_template(config: TklrConfig, path: Path):
    rendered = CONFIG_TEMPLATE.format(
        title=format_value(config.title),
        ui=type(
            "Obj",
            (),
            {
                "theme": format_value(config.ui.theme),
                "show_completed": format_value(config.ui.show_completed),
            },
        )(),
        paths=type("Obj", (), {"db": format_value(config.paths.db)})(),
    )
    path.write_text(rendered.strip() + "\n", encoding="utf-8")
    print(f"✅ Config with comments written to: {path}")


# ─── Main Environment Class ───────────────────────────────


class TklrEnvironment:
    def __init__(self):
        self._home = self._resolve_home()
        self._config: Optional[TklrConfig] = None

    @property
    def home(self) -> Path:
        return self._home

    @property
    def config_path(self) -> Path:
        return self.home / "config.toml"

    @property
    def db_path(self) -> Path:
        return self.home / "tklr.db"

    def ensure(self, init_config: bool = True, init_db_fn: Optional[callable] = None):
        self.home.mkdir(parents=True, exist_ok=True)

        if init_config and not self.config_path.exists():
            save_config_from_template(TklrConfig(), self.config_path)

        if init_db_fn and not self.db_path.exists():
            init_db_fn(self.db_path)

    def load_config(self) -> TklrConfig:
        try:
            with open(self.config_path, "rb") as f:
                data = tomllib.load(f)
            config = TklrConfig.model_validate(data)
        except (ValidationError, tomllib.TOMLDecodeError) as e:
            print(f"⚠️ Config error in {self.config_path}: {e}\nUsing defaults.")
            config = TklrConfig()
            save_config_from_template(config, self.config_path)

        self._config = config
        return config

    @property
    def config(self) -> TklrConfig:
        if self._config is None:
            return self.load_config()
        return self._config

    def _resolve_home(self) -> Path:
        cwd = Path.cwd()
        if (cwd / "config.toml").exists() and (cwd / "tklr.db").exists():
            return cwd

        env_home = os.getenv("TKLR_HOME")
        if env_home:
            return Path(env_home).expanduser()

        xdg_home = os.getenv("XDG_CONFIG_HOME")
        if xdg_home:
            return Path(xdg_home).expanduser() / "tklr"
        else:
            return Path.home() / ".config" / "tklr"
