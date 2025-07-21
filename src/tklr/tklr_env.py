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
    next: float = 12.0
    high: float = 8.0
    medium: float = 4.0
    low: float = 0.0
    someday: float = -4.0


class DueConfig(BaseModel):
    max: float = 15.0
    interval: str = "1w"


class PastdueConfig(BaseModel):
    max: float = 5.0
    interval: str = "1w"


class RecentConfig(BaseModel):
    max: float = 3.0
    interval: str = "1w"


class AgeConfig(BaseModel):
    max: float = 20.0
    interval: str = "26w"


class UrgencyConfig(BaseModel):
    active: float = 20.0
    blocking: float = 1.0
    description: float = 1.0
    extent: float = 0.25
    project: float = 1.0
    tag: float = 1.0

    due: DueConfig = DueConfig()
    pastdue: PastdueConfig = PastdueConfig()
    recent: RecentConfig = RecentConfig()
    age: AgeConfig = AgeConfig()

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
# all values are floats.

# is this the active task or job?
active = {{ urgency.active }}

# are other jobs waiting for this job to be finished
blocking = {{ urgency.blocking }}
#
# does this task or job have a description?
description = {{ urgency.description }}

# if there is an extent, apply this hourly rate
extent = {{ urgency.extent }}

# is this a job and thus part of a project?
project = {{ urgency.project }}

# are there tags?
tag = {{ urgency.tag }}

# Each of the "max/interval" settings below involves a 
# max and an interval over which the contribution ranges
# between the max value and 0.0. In each case, "now" refers
# to the current datetime, "due" to the scheduled datetime 
# and "modified" to the last modified datetime. Note that 
# necessarily, "now" >= "modified". The returned value 
# varies linearly over the interval in each case. 

[urgency.due]
# Return 0.0 when now <= due - interval and max when 
# now >= due.

max = {{ urgency.due.max }}
interval = "{{ urgency.due.interval }}"

[urgency.pastdue]
# Return 0.0 when now <= due and max when now >= 
# due + interval. 

max = {{ urgency.pastdue.max }}
interval = "{{ urgency.pastdue.interval }}"

[urgency.recent]
# The "recent" value is max when now = modified and 
# 0.0 when now >= modified + interval. The maximum of 
# this value and "age" (below) is returned. The returned 
# value thus decreases initially over the 

max = {{ urgency.recent.max }}
interval = "{{ urgency.recent.interval }}"

[urgency.age]
# The "age" value is 0.0 when now = modified and max 
# when now >= modified + interval. The maximum of this 
# value and "recent" (above) is returned. 

max = {{ urgency.age.max }}
interval = "{{ urgency.age.interval }}"

[urgency.priority]
# Priority levels used in urgency calculation.
# These are mapped from user input `@p 1` through `@p 5` 
# so that entering "@p 1" entails the priority value for 
# "someday", "@p 2" the priority value for "low" and so forth.
#
#   @p 1 = someday  → least urgent
#   @p 2 = low
#   @p 3 = medium
#   @p 4 = high
#   @p 5 = next     → most urgent
#
# Set these values to tune the effect of each level.

someday = {{ urgency.priority.someday }}
low     = {{ urgency.priority.low }}
medium  = {{ urgency.priority.medium }}
high    = {{ urgency.priority.high }}
next    = {{ urgency.priority.next }}

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

    def load_config(self) -> TklrConfig:
        from jinja2 import Template

        # Step 1: Create the file if it doesn't exist
        if not os.path.exists(self.config_path):
            config = TklrConfig()
            template = Template(CONFIG_TEMPLATE)
            rendered = template.render(**config.model_dump()).strip() + "\n"
            with open(self.config_path, "w", encoding="utf-8") as f:
                f.write(rendered)
            print(f"✅ Created new config file at {self.config_path}")
            self._config = config
            return config

        # Step 2: Try to load and validate the config
        try:
            with open(self.config_path, "rb") as f:
                data = tomllib.load(f)
            config = TklrConfig.model_validate(data)
        except (ValidationError, tomllib.TOMLDecodeError) as e:
            print(f"⚠️ Config error in {self.config_path}: {e}\nUsing defaults.")
            config = TklrConfig()

        # Step 3: Always regenerate the canonical version
        template = Template(CONFIG_TEMPLATE)
        rendered = template.render(**config.model_dump()).strip() + "\n"

        with open(self.config_path, "r", encoding="utf-8") as f:
            current_text = f.read()

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
