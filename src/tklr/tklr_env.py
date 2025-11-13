from pathlib import Path
import os
import sys
import tomllib
from pydantic import BaseModel, Field, ValidationError
from typing import Dict, List, Optional
from jinja2 import Template

from pydantic import RootModel


class PriorityConfig(RootModel[dict[str, float]]):
    pass


# ─── Config Schema ─────────────────────────────────────────────────
class UIConfig(BaseModel):
    theme: str = Field("dark", pattern="^(dark|light)$")
    show_completed: bool = True
    ampm: bool = False
    dayfirst: bool = False
    yearfirst: bool = True
    two_digit_year: bool = True
    history_weight: int = 3


class DueConfig(BaseModel):
    interval: str = "1w"
    max: float = 8.0


class PastdueConfig(BaseModel):
    interval: str = "2d"
    max: float = 2.0


class RecentConfig(BaseModel):
    interval: str = "2w"
    max: float = 4.0


class AgeConfig(BaseModel):
    interval: str = "26w"
    max: float = 10.0


class ExtentConfig(BaseModel):
    interval: str = "12h"
    max: float = 4.0


class BlockingConfig(BaseModel):
    count: int = 3
    max: float = 6.0


class TagsConfig(BaseModel):
    count: int = 3
    max: float = 3.0


class ProjectConfig(BaseModel):
    max: float = 3.0


class DescriptionConfig(BaseModel):
    max: float = 2.0


class ColorsConfig(BaseModel):
    min_hex_color: str = "#6495ed"
    max_hex_color: str = "#ffff00"
    min_urgency: float = 0.5
    steps: int = 10


class UrgencyConfig(BaseModel):
    colors: ColorsConfig = ColorsConfig()
    project: float = 2.0
    due: DueConfig = DueConfig()
    pastdue: PastdueConfig = PastdueConfig()
    recent: RecentConfig = RecentConfig()
    age: AgeConfig = AgeConfig()
    extent: ExtentConfig = ExtentConfig()
    blocking: BlockingConfig = BlockingConfig()
    tags: TagsConfig = TagsConfig()
    project: ProjectConfig = ProjectConfig()
    description: DescriptionConfig = DescriptionConfig()

    priority: PriorityConfig = PriorityConfig(
        {
            "1": 10.0,
            "2": 8.0,
            "3": 5.0,
            "4": 2.0,
            "5": -5.0,
        }
    )


class TklrConfig(BaseModel):
    title: str = "Tklr Configuration"
    ui: UIConfig = UIConfig()
    alerts: dict[str, str] = {}
    urgency: UrgencyConfig = UrgencyConfig()
    bin_orders: Dict[str, List[str]] = Field(default_factory=dict)


CONFIG_TEMPLATE = """\
# DO NOT EDIT TITLE
title = "{{ title }}"

[ui]
# theme: str = 'dark' | 'light'
theme = "{{ ui.theme }}"

# ampm: bool = true | false
# Use 12 hour AM/PM when true else 24 hour
ampm = {{ ui.ampm | lower }}

# history_weight: int 
# Apply this weight to the prior history when computing
# the next offset for a task
history_weight = {{ ui.history_weight }}

# dayfirst and yearfirst settings
# These settings are used to resolve ambiguous date entries involving
# 2-digit components. E.g., the interpretation of the date "12-10-11" 
# with the various possible settings for dayfirst and yearfirst: 
#
# dayfirst  yearfirst    date     interpretation  standard
# ========  =========  ========   ==============  ========
#   True     True      12-10-11    2012-11-10     Y-D-M ??
#   True     False     12-10-11    2011-10-12     D-M-Y EU
#   False    True      12-10-11    2012-10-11     Y-M-D ISO 8601
#   False    False     12-10-11    2011-12-10     M-D-Y US
#
# The defaults:
#   dayfirst = false
#   yearfirst = true 
# correspond to the Y-M-D ISO 8601 standard.

# dayfirst: bool = true | false 
dayfirst = {{ ui.dayfirst | lower }}

# yearfirst: bool = true | false
yearfirst = {{ ui.yearfirst | lower }}

# two_digit_year: bool = true | false 
# If true, years are displayed using the last two digits, e.g.,
# 25 instead of 2025. 
two_digit_year = {{ ui.two_digit_year | lower }} 

[alerts]
# dict[str, str]: character -> command_str.
# E.g., this entry
#   v = '/usr/bin/say -v Alex "{name}, {when}"'
# would, on my macbook, invoke the system voice to speak the name (subject)
# of the reminder and when (the time remaining until the scheduled datetime).
# The character "d" would be associated with this command so that, e.g.,
# the alert entry "@a 30m, 15m: d" would trigger this command 30
# minutes before and again 15 minutes before the scheduled datetime. 
# Additional keys: start (scheduled datetime), time (spoken version of
# start), location, description.  
{% for key, value in alerts.items() %}
{{ key }} = '{{ value }}'
{% endfor %}

# ─── Urgency Configuration ─────────────────────────────────────

[urgency.colors]
# The hex color "min_hex_color" applies to urgencies in [-1.0, min_urgency]. 
# Hex colors for the interval [min_urgency, 1.0] are broken into "steps" 
# equal steps along the gradient from "min_hex_color" to "max_hex_color". 
# These colors are used for tasks in the urgency listing. 
min_hex_color = "{{ urgency.colors.min_hex_color }}"
max_hex_color = "{{ urgency.colors.max_hex_color }}"
min_urgency = {{ urgency.colors.min_urgency }}
steps = {{ urgency.colors.steps }}

[urgency.due]
# The "due" urgency increases from 0.0 to "max" as now passes from
# due - interval to due.
interval = "{{ urgency.due.interval }}"
max = {{ urgency.due.max }}


[urgency.pastdue]
# The "pastdue" urgency increases from 0.0 to "max" as now passes
# from due to due + interval.
interval = "{{ urgency.pastdue.interval }}"
max = {{ urgency.pastdue.max }}

[urgency.recent]
# The "recent" urgency decreases from "max" to 0.0 as now passes
# from modified to modified + interval.
interval = "{{ urgency.recent.interval }}"
max = {{ urgency.recent.max }}

[urgency.age]
# The "age" urgency  increases from 0.0 to "max" as now increases
# from modified to modified + interval.
interval = "{{ urgency.age.interval }}"
max = {{ urgency.age.max }}

[urgency.extent]
# The "extent" urgency increases from 0.0 when extent = "0m" to "max"
# when extent >= interval.
interval = "{{ urgency.extent.interval }}"
max = {{ urgency.extent.max }}

[urgency.blocking]
# The "blocking" urgency increases from 0.0 when blocked = 0 to "max"
# when blocked >= count.
count = {{ urgency.blocking.count }}
max = {{ urgency.blocking.max }}

[urgency.tags]
# The "tags" urgency increases from 0.0 when tags = 0 to "max" when
# when tags >= count.
count = {{ urgency.tags.count }}
max = {{ urgency.tags.max }}

[urgency.priority]
# The "priority" urgency corresponds to the value from "1" to "5" of `@p`
# specified in the task. E.g, with "@p 3", the value would correspond to
# the "3" entry below. Absent an entry for "@p", the value would be 0.0.
{% for key, value in urgency.priority.items() %}
"{{ key }}" = {{ value }}
{% endfor %}

# In the default settings, a priority of "5" is the only one that yields
# a negative value, `-5`, and thus reduces the urgency of the task.

[urgency.description]
# The "description" urgency equals "max" if the task has an "@d" entry and
# 0.0 otherwise.
max = {{ urgency.description.max }}

[urgency.project]
# The "project" urgency equals "max" if the task belongs to a project and
# 0.0 otherwise.
max = {{ urgency.project.max }}

[bin_orders]
# Specify custom ordering of children for a root bin.
# Example:
#   seedbed = ["seed", "germination", "seedling", "growth", "flowering"]
{% for root, order_list in bin_orders.items() %}
{{ root }} = ["{{ order_list | join('","') }}"]
{% endfor %}

"""
# # ─── Commented Template ────────────────────────────────────
# CONFIG_TEMPLATE = """\
# title = "{{ title }}"
#
# [ui]
# # theme: str = 'dark' | 'light'
# theme = "{{ ui.theme }}"
#
# # ampm: bool = true | false
# ampm = {{ ui.ampm | lower }}
#
# # dayfirst: bool = true | false
# dayfirst = {{ ui.dayfirst | lower }}
#
# # yearfirst: bool = true | false
# yearfirst = {{ ui.yearfirst | lower }}
#
# [alerts]
# # dict[str, str]: character -> command_str
# {% for key, value in alerts.items() %}
# {{ key }} = '{{ value }}'
# {% endfor %}
#
# [urgency]
# # values for task urgency calculation
#
# # does this task or job have a description?
# description = {{ urgency.description }}
#
# # is this a job and thus part of a project?
# project = {{ urgency.project }}
#
# # Each of the "max/interval" settings below involves a
# # max and an interval over which the contribution ranges
# # between the max value and 0.0. In each case, "now" refers
# # to the current datetime, "due" to the scheduled datetime
# # and "modified" to the last modified datetime. Note that
# # necessarily, "now" >= "modified". The returned value
# # varies linearly over the interval in each case.
#
# [urgency.due]
# # Return 0.0 when now <= due - interval and max when
# # now >= due.
#
# max = {{ urgency.due.max }}
# interval = "{{ urgency.due.interval }}"
#
# [urgency.pastdue]
# # Return 0.0 when now <= due and max when now >=
# # due + interval.
#
# max = {{ urgency.pastdue.max }}
# interval = "{{ urgency.pastdue.interval }}"
#
# [urgency.recent]
# # The "recent" value is max when now = modified and
# # 0.0 when now >= modified + interval. The maximum of
# # this value and "age" (below) is returned. The returned
# # value thus decreases initially over the
#
# max = {{ urgency.recent.max }}
# interval = "{{ urgency.recent.interval }}"
#
# [urgency.age]
# # The "age" value is 0.0 when now = modified and max
# # when now >= modified + interval. The maximum of this
# # value and "recent" (above) is returned.
#
# max = {{ urgency.age.max }}
# interval = "{{ urgency.age.interval }}"
#
# [urgency.extent]
# # The "extent" value is 0.0 when extent = "0m" and max
# # when extent >= interval.
#
# max = {{ urgency.extent.max }}
# interval = "{{ urgency.extent.interval }}"
#
# [urgency.blocking]
# # The "blocking" value is 0.0 when blocking = 0 and max
# # when blocking >= count.
#
# max = {{ urgency.blocking.max }}
# count = {{ urgency.blocking.count }}
#
# [urgency.tags]
# # The "tags" value is 0.0 when len(tags) = 0 and max
# # when len(tags) >= count.
#
# max = {{ urgency.tags.max }}
# count = {{ urgency.tags.count }}
#
# [urgency.priority]
# # Priority levels used in urgency calculation.
# # These are mapped from user input `@p 1` through `@p 5`
# # so that entering "@p 1" entails the priority value for
# # "someday", "@p 2" the priority value for "low" and so forth.
# #
# #   @p 1 = someday  → least urgent
# #   @p 2 = low
# #   @p 3 = medium
# #   @p 4 = high
# #   @p 5 = next     → most urgent
# #
# # Set these values to tune the effect of each level. Note
# # that omitting @p in a task is equivalent to setting
# # priority = 0.0 for the task.
#
# someday = {{ urgency.priority.someday }}
# low     = {{ urgency.priority.low }}
# medium = {{ urgency.priority.medium }}
# high    = {{ urgency.priority.high }}
# next    = {{ urgency.priority.next }}
#
# [bin_orders]
# # Specify custom ordering of children for a root bin.
# # Example:
# #   seedbed = ["seed", "germination", "seedling", "growth", "flowering"]
# {% for root, order_list in bin_orders.items() %}
# {{ root }} = ["{{ order_list | join('","') }}"]
# {% endfor %}

# ─── Save Config with Comments ───────────────────────────────


def save_config_from_template(config: TklrConfig, path: Path):
    template = Template(CONFIG_TEMPLATE)
    rendered = template.render(**config.model_dump())
    path.write_text(rendered.strip() + "\n", encoding="utf-8")
    print(f"✅ Config with comments written to: {path}")


# ─── Main Environment Class ───────────────────────────────


def collapse_home(path: str | Path) -> str:
    path = Path(path).expanduser().resolve()
    str_path = path.as_posix()
    str_path = str_path.replace(str(Path.home()), "~")
    return str_path


class TklrEnvironment:
    def __init__(self):
        # self.cwd = Path.cwd()
        self._home = self._resolve_home()
        # self.usrhome = Path.home()
        self._config: Optional[TklrConfig] = None

    # def norm_path(self, path: Path):
    #     rpath = path.resolve()
    #     if rpath.is_relative_to(self.usrhome):
    #         return rpath.relative_to(self.usrhome).as_posix()
    #     return rpath.as_posix()

    def get_paths(self):
        return [collapse_home(p) for p in [self.home, self.db_path, self.config_path]]

    def get_home(self):
        return collapse_home(self.home)

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
