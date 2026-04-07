from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from .model import UrgencyComputer


def format_urgency_config_summary(env) -> list[str]:
    urgency = env.config.urgency
    priority_map = urgency.priority.root

    lines = []
    lines.append("Current urgency settings:")
    lines.append(
        f"  due:         max={urgency.due.max} interval={urgency.due.interval}"
    )
    lines.append(
        f"  pastdue:     max={urgency.pastdue.max} interval={urgency.pastdue.interval}"
    )
    lines.append(
        f"  age:         max={urgency.age.max} interval={urgency.age.interval}"
    )
    lines.append(
        f"  recent:      max={urgency.recent.max} interval={urgency.recent.interval}"
    )
    lines.append(f"  tags:        max={urgency.tags.max} count={urgency.tags.count}")
    lines.append(f"  description: max={urgency.description.max}")
    lines.append(
        f"  extent:      max={urgency.extent.max} interval={urgency.extent.interval}"
    )
    lines.append(
        f"  blocking:    max={urgency.blocking.max} count={urgency.blocking.count}"
    )
    lines.append(f"  project:     max={urgency.project.max}")
    lines.append(
        "  priority:    "
        f"1={priority_map.get('first', 0.0)} "
        f"2={priority_map.get('second', 0.0)} "
        f"3={priority_map.get('third', 0.0)} "
        f"4={priority_map.get('fourth', 0.0)} "
        f"5={priority_map.get('fifth', 0.0)}"
    )
    return lines


def build_urgency_screening_examples(now_dt: datetime) -> list[dict[str, Any]]:
    """
    Build a small balanced screening set for urgency tuning.

    Factors:
      P = priority        (- low, + high)
      D = due status      (- far future, + overdue)
      A = age / created   (- new, + old)
      R = recent / mod    (- stale, + recent)
      T = tags            (- none, + many)
      E = description     (- absent, + present)

    Returned rows are ready to pass into
    ``UrgencyComputer.from_args_and_weights(...)``.
    """
    now_seconds = int(now_dt.timestamp())

    def created_seconds(level: int) -> int:
        # A- -> new, A+ -> old
        delta = timedelta(days=1) if level < 0 else timedelta(days=180)
        return int((now_dt - delta).timestamp())

    def modified_seconds(level: int) -> int:
        # R- -> stale, R+ -> recent
        delta = timedelta(days=30) if level < 0 else timedelta(hours=1)
        return int((now_dt - delta).timestamp())

    def due_seconds(level: int) -> int:
        # D- -> far future, D+ -> overdue
        delta = timedelta(days=30) if level < 0 else timedelta(days=-3)
        return int((now_dt + delta).timestamp())

    def priority_level(level: int) -> int:
        # P- -> lower urgency priority, P+ -> higher urgency priority
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

        label = (
            f"run{row['run']} "
            f"P{'+' if p > 0 else '-'} "
            f"D{'+' if d > 0 else '-'} "
            f"A{'+' if a > 0 else '-'} "
            f"R{'+' if r > 0 else '-'} "
            f"T{'+' if t > 0 else '-'} "
            f"E{'+' if e > 0 else '-'}"
        )

        examples.append(
            {
                "label": label,
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
    """
    Build a second balanced screening set focused on structural task properties.

    Factors:
      P = priority     (- low, + high)
      D = due status   (- far future, + overdue)
      X = extent       (- none, + substantial)
      B = blocking     (- none, + many)
      J = jobs/project (- no, + yes)
      A = age/created  (- new, + old)
    """
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

        label = (
            f"run{row['run']} "
            f"P{'+' if p > 0 else '-'} "
            f"D{'+' if d > 0 else '-'} "
            f"X{'+' if x > 0 else '-'} "
            f"B{'+' if b > 0 else '-'} "
            f"J{'+' if j > 0 else '-'} "
            f"A{'+' if a > 0 else '-'}"
        )

        examples.append(
            {
                "label": label,
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
    """
    Compute urgency values for the requested screening design using the current config.
    """
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


def format_urgency_screening_report(
    env,
    rows: list[dict[str, Any]],
    design: str = "base",
) -> list[str]:
    """
    Format screening rows for simple CLI display.
    """
    lines: list[str] = []
    lines.append(f"Urgency screening report ({design})")
    lines.append("")
    lines.extend(format_urgency_config_summary(env))
    lines.append("")

    keys = ["due", "pastdue", "age", "recent", "priority", "tags", "description"]

    for row in rows:
        label = row["label"]
        percent = row["percent"]
        weights = row.get("weights") or {}
        parts = []
        for key in keys:
            if key in weights:
                value = weights[key]
                if isinstance(value, (int, float)):
                    parts.append(f"{key}={value:.1f}")
                else:
                    parts.append(f"{key}={value}")

        lines.append(f"{label:<24} {percent:>3}")
        if parts:
            lines.append("  " + " ".join(parts))
        lines.append("")

    return lines
