from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from .model import UrgencyComputer


def fmt_num(value) -> str:
    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        if value.is_integer():
            return str(int(value))
        return f"{value:g}"
    return str(value)


def _get_priority_values(env) -> dict[str, float]:
    priority_map = env.config.urgency.priority.root
    return {
        "1": float(priority_map.get("first", priority_map.get("1", 0.0))),
        "2": float(priority_map.get("second", priority_map.get("2", 0.0))),
        "3": float(priority_map.get("third", priority_map.get("3", 0.0))),
        "4": float(priority_map.get("fourth", priority_map.get("4", 0.0))),
        "5": float(priority_map.get("fifth", priority_map.get("5", 0.0))),
    }


def get_urgency_model_summary(env) -> list[str]:
    urgency = env.config.urgency
    priority_values = _get_priority_values(env)

    return [
        "Current urgency model and settings:",
        "",
        "  primary = due_pastdue if due else max(priority, age_recent)",
        "",
        f"    due:         max={fmt_num(urgency.due.max)} interval={urgency.due.interval}",
        f"    pastdue:     max={fmt_num(urgency.pastdue.max)} interval={urgency.pastdue.interval}",
        "    due_pastdue = due + pastdue",
        "",
        f"    age:         max={fmt_num(urgency.age.max)} interval={urgency.age.interval}",
        f"    recent:      max={fmt_num(urgency.recent.max)} interval={urgency.recent.interval}",
        "    age_recent = max(age, recent)",
        "",
        (
            "    priority:    "
            f"1={fmt_num(priority_values['1'])} "
            f"2={fmt_num(priority_values['2'])} "
            f"3={fmt_num(priority_values['3'])} "
            f"4={fmt_num(priority_values['4'])} "
            f"5={fmt_num(priority_values['5'])}"
        ),
        "",
        "  secondary = tags + description + ... + project",
        "",
        f"    tags:        max={fmt_num(urgency.tags.max)} count={fmt_num(urgency.tags.count)}",
        f"    description: max={fmt_num(urgency.description.max)}",
        f"    extent:      max={fmt_num(urgency.extent.max)} interval={urgency.extent.interval}",
        f"    blocking:    max={fmt_num(urgency.blocking.max)} count={fmt_num(urgency.blocking.count)}",
        f"    project:     max={fmt_num(urgency.project.max)}",
    ]


def get_urgency_computed_values(env) -> dict[str, float]:
    urgency = env.config.urgency
    priority_values = _get_priority_values(env)

    due_pastdue_max = float(urgency.due.max) + float(urgency.pastdue.max)
    age_recent_max = max(float(urgency.age.max), float(urgency.recent.max))
    priority_max = max(priority_values.values(), default=0.0)
    primary_max = max(due_pastdue_max, age_recent_max, priority_max)
    secondary_max = (
        float(urgency.tags.max)
        + float(urgency.description.max)
        + float(urgency.extent.max)
        + float(urgency.blocking.max)
        + float(urgency.project.max)
    )
    maximum_possible_urgency = primary_max + secondary_max

    return {
        "due_pastdue_max": due_pastdue_max,
        "age_recent_max": age_recent_max,
        "priority_max": priority_max,
        "primary_max": primary_max,
        "secondary_max": secondary_max,
        "maximum_possible_urgency": maximum_possible_urgency,
    }


def format_urgency_computed_values(env) -> list[str]:
    values = get_urgency_computed_values(env)
    urgency = env.config.urgency
    priority_values = _get_priority_values(env)

    return [
        "Computed urgency values:",
        "",
        (
            "  due_pastdue_max: due.max + pastdue.max = "
            f"{fmt_num(urgency.due.max)} + {fmt_num(urgency.pastdue.max)} = "
            f"{fmt_num(values['due_pastdue_max'])}"
        ),
        (
            "  age_recent_max:  max(age.max, recent.max) \n                   = "
            f"max({fmt_num(urgency.age.max)}, {fmt_num(urgency.recent.max)}) = "
            f"{fmt_num(values['age_recent_max'])}"
        ),
        (f"  priority_max:    priority.1 = {fmt_num(priority_values['1'])}"),
        "",
        (
            "  primary_max:     max(due_pastdue_max, age_recent_max, \n                   priority_max) = "
            f"max({fmt_num(values['due_pastdue_max'])}, "
            f"{fmt_num(values['age_recent_max'])}, "
            f"{fmt_num(values['priority_max'])}) = "
            f"{fmt_num(values['primary_max'])}"
        ),
        "",
        (
            "  secondary_max:   tags.max + description.max + extent.max \n                   + blocking.max + project.max \n                   = "
            f"{fmt_num(urgency.tags.max)} + "
            f"{fmt_num(urgency.description.max)} + "
            f"{fmt_num(urgency.extent.max)} + "
            f"{fmt_num(urgency.blocking.max)} + "
            f"{fmt_num(urgency.project.max)} = "
            f"{fmt_num(values['secondary_max'])}"
        ),
        "",
        (
            "  maximum_possible_urgency: primary_max + secondary_max \n                   = "
            f"{fmt_num(values['primary_max'])} + {fmt_num(values['secondary_max'])} = "
            f"{fmt_num(values['maximum_possible_urgency'])}"
        ),
    ]


def build_urgency_screening_examples(now_dt: datetime) -> list[dict[str, Any]]:
    now_seconds = int(now_dt.timestamp())

    def created_seconds(level: int) -> int:
        delta = timedelta(days=1) if level < 0 else timedelta(days=180)
        return int((now_dt - delta).timestamp())

    def modified_seconds(level: int) -> int:
        delta = timedelta(days=30) if level < 0 else timedelta(hours=1)
        return int((now_dt - delta).timestamp())

    def due_seconds(level: int) -> int:
        delta = timedelta(days=30) if level < 0 else timedelta(days=-3)
        return int((now_dt + delta).timestamp())

    def priority_level(level: int) -> int:
        return 4 if level < 0 else 1

    def tag_count(level: int) -> int:
        return 0 if level < 0 else 3

    def has_description(level: int) -> bool:
        return level > 0

    design = [
        {"run": 1, "P": -1, "D": -1, "A": -1, "R": -1, "T": -1, "E": -1},
        {"run": 2, "P": -1, "D": -1, "A": +1, "R": +1, "T": +1, "E": +1},
        {"run": 3, "P": -1, "D": +1, "A": -1, "R": -1, "T": +1, "E": +1},
        {"run": 4, "P": -1, "D": +1, "A": +1, "R": +1, "T": -1, "E": -1},
        {"run": 5, "P": +1, "D": -1, "A": -1, "R": +1, "T": -1, "E": +1},
        {"run": 6, "P": +1, "D": -1, "A": +1, "R": -1, "T": +1, "E": -1},
        {"run": 7, "P": +1, "D": +1, "A": -1, "R": +1, "T": +1, "E": -1},
        {"run": 8, "P": +1, "D": +1, "A": +1, "R": -1, "T": -1, "E": +1},
    ]

    examples: list[dict[str, Any]] = []

    for row in design:
        p = row["P"]
        d = row["D"]
        a = row["A"]
        r = row["R"]
        t = row["T"]
        e = row["E"]

        examples.append(
            {
                "label": (
                    f"run{row['run']} "
                    f"P{'+' if p > 0 else '-'} "
                    f"D{'+' if d > 0 else '-'} "
                    f"A{'+' if a > 0 else '-'} "
                    f"R{'+' if r > 0 else '-'} "
                    f"T{'+' if t > 0 else '-'} "
                    f"E{'+' if e > 0 else '-'}"
                ),
                "now": now_seconds,
                "created": created_seconds(a),
                "modified": modified_seconds(r),
                "due": due_seconds(d),
                "extent": 0,
                "priority_level": priority_level(p),
                "blocking": 0,
                "tags": tag_count(t),
                "description": has_description(e),
                "jobs": False,
                "pinned": False,
            }
        )

    return examples


def build_urgency_structure_examples(now_dt: datetime) -> list[dict[str, Any]]:
    now_seconds = int(now_dt.timestamp())

    def created_seconds(level: int) -> int:
        delta = timedelta(days=1) if level < 0 else timedelta(days=180)
        return int((now_dt - delta).timestamp())

    def due_seconds(level: int) -> int:
        delta = timedelta(days=30) if level < 0 else timedelta(days=-3)
        return int((now_dt + delta).timestamp())

    def priority_level(level: int) -> int:
        return 4 if level < 0 else 1

    def extent_seconds(level: int) -> int:
        return 0 if level < 0 else 4 * 60 * 60

    def blocking_count(level: int) -> int:
        return 0 if level < 0 else 3

    def has_jobs(level: int) -> bool:
        return level > 0

    design = [
        {"run": 1, "P": -1, "D": -1, "X": -1, "B": -1, "J": -1, "A": -1},
        {"run": 2, "P": -1, "D": -1, "X": +1, "B": +1, "J": +1, "A": +1},
        {"run": 3, "P": -1, "D": +1, "X": -1, "B": -1, "J": +1, "A": +1},
        {"run": 4, "P": -1, "D": +1, "X": +1, "B": +1, "J": -1, "A": -1},
        {"run": 5, "P": +1, "D": -1, "X": -1, "B": +1, "J": -1, "A": +1},
        {"run": 6, "P": +1, "D": -1, "X": +1, "B": -1, "J": +1, "A": -1},
        {"run": 7, "P": +1, "D": +1, "X": -1, "B": +1, "J": +1, "A": -1},
        {"run": 8, "P": +1, "D": +1, "X": +1, "B": -1, "J": -1, "A": +1},
    ]

    examples: list[dict[str, Any]] = []

    for row in design:
        p = row["P"]
        d = row["D"]
        x = row["X"]
        b = row["B"]
        j = row["J"]
        a = row["A"]

        examples.append(
            {
                "label": (
                    f"run{row['run']} "
                    f"P{'+' if p > 0 else '-'} "
                    f"D{'+' if d > 0 else '-'} "
                    f"X{'+' if x > 0 else '-'} "
                    f"B{'+' if b > 0 else '-'} "
                    f"J{'+' if j > 0 else '-'} "
                    f"A{'+' if a > 0 else '-'}"
                ),
                "now": now_seconds,
                "created": created_seconds(a),
                "modified": now_seconds,
                "due": due_seconds(d),
                "extent": extent_seconds(x),
                "priority_level": priority_level(p),
                "blocking": blocking_count(b),
                "tags": 0,
                "description": False,
                "jobs": has_jobs(j),
                "pinned": False,
            }
        )

    return examples


def compute_urgency_screening_report(
    env,
    now_dt: datetime | None = None,
    design: str = "base",
) -> list[dict[str, Any]]:
    if now_dt is None:
        now_dt = datetime.now()

    urgency = UrgencyComputer(env)
    if design == "structure":
        examples = build_urgency_structure_examples(now_dt)
    else:
        examples = build_urgency_screening_examples(now_dt)

    rows: list[dict[str, Any]] = []

    for ex in examples:
        urgency_value, color, weights = urgency.from_args_and_weights(
            now=ex["now"],
            created=ex["created"],
            modified=ex["modified"],
            due=ex["due"],
            extent=ex["extent"],
            priority_level=ex["priority_level"],
            blocking=ex["blocking"],
            tags=ex["tags"],
            description=ex["description"],
            jobs=ex["jobs"],
            pinned=ex["pinned"],
        )
        rows.append(
            {
                "label": ex["label"],
                "urgency": urgency_value,
                "percent": round(urgency_value * 100),
                "color": color,
                "weights": weights,
                "args": ex,
            }
        )

    rows.sort(key=lambda row: row["urgency"], reverse=True)
    return rows


_PRIMARY_KEYS = ("due", "pastdue", "age", "recent", "priority")
_SECONDARY_KEYS = ("tags", "description", "extent", "blocking", "project")


def format_task_urgency_explanation(
    weights: dict,
    urgency_pct: int,
    max_possible: float,
) -> list[str]:
    """
    Return plain-text lines explaining how urgency_pct was computed from weights.

    Outer indent (6 spaces) aligns the block with the detail lines shown below
    the task line.  Inner indent (10 spaces) is used for the primary/secondary
    breakdown sub-lines.

    Only non-zero weight entries are mentioned; the weights dict already
    stores only the winning primary component as non-zero.
    """
    outer = "      "  # 6 spaces
    inner = "          "  # 10 spaces

    primary_parts = [
        (k, float(weights.get(k, 0.0)))
        for k in _PRIMARY_KEYS
        if float(weights.get(k, 0.0))
    ]
    secondary_parts = [
        (k, float(weights.get(k, 0.0)))
        for k in _SECONDARY_KEYS
        if float(weights.get(k, 0.0))
    ]

    primary = sum(v for _, v in primary_parts)
    secondary = sum(v for _, v in secondary_parts)
    mp = fmt_num(max_possible)

    lines: list[str] = []

    # Score header line
    score_expr = (
        f"({fmt_num(primary)} + {fmt_num(secondary)})"
        if secondary
        else fmt_num(primary)
    )
    lines.append(f"{outer}{urgency_pct} \u2248 100 * {score_expr} / {mp}:")

    # Primary breakdown
    if primary_parts:
        args = weights.get("args", {})
        detail_parts = []
        for k, v in primary_parts:
            if k == "priority":
                level = args.get("priority_level", "?")
                detail_parts.append(f"priority(@p{level} = {fmt_num(v)})")
            else:
                detail_parts.append(f"{k}({fmt_num(v)})")
        lines.append(
            f"{inner}primary = {fmt_num(primary)}:  {' + '.join(detail_parts)}"
        )
    else:
        lines.append(f"{inner}primary = 0")

    # Secondary breakdown
    if secondary_parts:
        detail = " + ".join(f"{k}({fmt_num(v)})" for k, v in secondary_parts)
        lines.append(f"{inner}secondary = {fmt_num(secondary)}:  {detail}")
    else:
        lines.append(f"{inner}secondary = 0")

    return lines


def format_urgency_report(env) -> list[str]:
    lines: list[str] = []
    lines.append("Urgency report")
    lines.append("")
    lines.append("Using settings from config.toml.")
    lines.append("")
    lines.extend(get_urgency_model_summary(env))
    lines.append("")
    lines.extend(format_urgency_computed_values(env))
    lines.append("")
    lines.append("urgency: (primary + secondary) / maximum_possible_urgency")
    lines.append("")
    return lines
