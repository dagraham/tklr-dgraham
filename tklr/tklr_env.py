from pathlib import Path
import os
import tomllib
from pydantic import BaseModel, Field, ValidationError
from typing import Optional
from jinja2 import Template


# ─── Config Schema ─────────────────────────────────────────────────
class UIConfig(BaseModel):
    theme: str = Field("dark", pattern="^(dark|light)$")
    show_completed: bool = True
    ampm: bool = False
    dayfirst: bool = False
    yearfirst: bool = True


# class PathsConfig(BaseModel):
#     db: str = "tklr.db"


class PriorityConfig(BaseModel):
    next: float = 15.0
    high: float = 6.0
    medium: float = 2.0
    low: float = -2.0
    someday: float = -6.0


class CurrentConfig(BaseModel):
    interval: str = "7d"
    value: float = 4.0


class DueConfig(BaseModel):
    interval: str = "7d"
    value: float = 16.0
    pastdue_adjustment: float = 0.5


class UrgencyConfig(BaseModel):
    active_value: float = 20.0
    age_daily: float = 0.2
    blocking_value: float = 1.0
    description_value: float = 1.0
    extent_hourly: float = 0.25
    project_value: float = 1.0
    tag_value: float = 1.0

    priority: PriorityConfig = PriorityConfig()


class TklrConfig(BaseModel):
    title: str = "Tklr Configuration"
    ui: UIConfig = UIConfig()
    alerts: dict[str, str] = {}
    urgency: UrgencyConfig = UrgencyConfig()


# ─── Commented Template ────────────────────────────────────
CONFIG_TEMPLATE = """\
title = "{{ title }}"

[ui]
# theme: str = 'dark' | 'light'
theme = "{{ ui.theme }}"

# ampm: bool = true | false
ampm = {{ ui.ampm | lower }}

# dayfirst: bool = true | false 
dayfirst = {{ ui.dayfirst | lower }}

# yearfirst: bool = true | false
yearfirst = {{ ui.yearfirst | lower }}

[alerts]
# dict[str, str]: character -> command_str  
{% for key, value in alerts.items() %}
{{ key }} = "{{ value }}"
{% endfor %}

[urgency]
# values for item urgency calculation
# all values are float

# is this the active task or job?
active_value = {{ urgency.active_value }}

# how long since the task or job was created?
age_daily = {{ urgency.age_daily }}
# are other jobs waiting for this job to be finished
blocking_value = {{ urgency.blocking_value }}
# does this task or job have a description?
description_value = {{ urgency.description_value }}
# if there is an extent, apply this hourly rate
extent_hourly = {{ urgency.extent_hourly }}
# is this a job and thus part of a project?
project_value = {{ urgency.project_value }}
# are there tags?
tag_value = {{ urgency.tag_value }}

[urgency.priority]
# priority levels for item urgency calculation
# all values are float

next = {{ urgency.priority.next }}
high = {{ urgency.priority.high }}
medium = {{ urgency.priority.medium }}
low = {{ urgency.priority.low }}
someday = {{ urgency.priority.someday }}
"""

# ─── Save Config with Comments ───────────────────────────────


def save_config_from_template(config: TklrConfig, path: Path):
    template = Template(CONFIG_TEMPLATE)
    rendered = template.render(**config.model_dump())
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

    # def load_config(self) -> TklrConfig:
    #     try:
    #         with open(self.config_path, "rb") as f:
    #             data = tomllib.load(f)
    #         config = TklrConfig.model_validate(data)
    #     except (ValidationError, tomllib.TOMLDecodeError) as e:
    #         print(f"⚠️ Config error in {self.config_path}: {e}\nUsing defaults.")
    #         config = TklrConfig()
    #         save_config_from_template(config, self.config_path)
    #
    #     self._config = config
    #     return config

    def load_config(self) -> TklrConfig:
        try:
            with open(self.config_path, "rb") as f:
                data = tomllib.load(f)
            config = TklrConfig.model_validate(data)
        except (ValidationError, tomllib.TOMLDecodeError) as e:
            print(f"⚠️ Config error in {self.config_path}: {e}\nUsing defaults.")
            config = TklrConfig()

        # Always regenerate the canonical version
        from jinja2 import Template

        template = Template(CONFIG_TEMPLATE)
        rendered = template.render(**config.model_dump()).strip() + "\n"

        # Read the current file contents
        with open(self.config_path, "r", encoding="utf-8") as f:
            current_text = f.read()

        # Only write if something changed
        if rendered != current_text:
            with open(self.config_path, "w", encoding="utf-8") as f:
                f.write(rendered)
            print(f"✅ Updated {self.config_path} with any missing defaults.")

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
