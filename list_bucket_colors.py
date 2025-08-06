from typing import List, Tuple
import click
from rich.table import Table
from rich.console import Console

# from rich.color import Color
from rich.style import Style
from colorsys import rgb_to_hls


def hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i : i + 2], 16) for i in (0, 2, 4))


def rgb_to_hex(rgb: Tuple[int, int, int]) -> str:
    return "#{:02x}{:02x}{:02x}".format(*rgb)


def get_urgency_color_buckets(neg_hex: str, max_hex: str, steps: int = 10) -> List[str]:
    neg_rgb = hex_to_rgb(neg_hex)
    max_rgb = hex_to_rgb(max_hex)

    buckets = []
    for i in range(steps):
        t = i / (steps - 1)
        rgb = tuple(
            round(neg + t * (maxc - neg)) for neg, maxc in zip(neg_rgb, max_rgb)
        )
        buckets.append(rgb_to_hex(rgb))
    return buckets


def urgency_to_bucket_color(urgency: float, buckets: List[str], neg_color: str) -> str:
    if urgency <= 0.0:
        return neg_color
    i = min(int(urgency * len(buckets)), len(buckets) - 1)
    return buckets[i]


def get_contrasting_text_color(hex_color: str) -> str:
    hex_color = hex_color.lstrip("#")
    r, g, b = [int(hex_color[i : i + 2], 16) for i in (0, 2, 4)]
    brightness = (r * 299 + g * 587 + b * 114) / 1000
    return "black" if brightness > 128 else "white"


if __name__ == "__main__":
    # neg_color = "#4169E1"
    min_color = "#6495ED"  # cornflowerblue (config.ui.negative_urgency)
    max_color = "#FFFF00"  # yellow (config.ui.maximum_urgency)
    # low_buckets = get_urgency_color_buckets(neg_color, low_color, 4)
    # high_buckets = get_urgency_color_buckets("#75a1d3", max_color, 6)
    # buckets = low_buckets + high_buckets

    num_buckets = 6
    ranges = [
        "-1.0 - 0.0",
    ]

    beg = 0.0
    inc = 1 / (num_buckets - 1)
    for i in range(num_buckets):
        end = beg + inc
        ranges.append(f"{beg:.2} - {end:.2}")
        beg = end

    buckets = get_urgency_color_buckets(min_color, max_color, num_buckets)
    # buckets.insert(0, neg_color)

    console = Console()
    table = Table(title="Urgency Colors")
    table.add_column("Urgency")
    table.add_column("Hex Value")

    num_buckets = len(buckets)
    count = 0
    for hex_val in buckets:
        name = ranges.pop(0)
        name_style = Style(color=hex_val)
        hex_style = Style(color=get_contrasting_text_color(hex_val), bgcolor=hex_val)

        table.add_row(f"[{hex_val}]{name}[/]", f"[{hex_style}]{hex_val}[/]")

    console.print(table)
