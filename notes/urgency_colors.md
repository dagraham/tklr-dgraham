# Urgency Colors

## 1. Color Interpolation Function (Shared)

```python
def interpolate_color(urgency, color1, color2):
    """
    Map urgency ∈ [-1, 1] to a color between color1 and color2 (RGB tuples).
    """
    t = (urgency + 1) / 2  # Normalize to [0.0, 1.0]
    return tuple(round(c1 + t * (c2 - c1)) for c1, c2 in zip(color1, color2))


def rgb_to_hex(rgb):
    return "#{:02x}{:02x}{:02x}".format(*rgb)
```

You can call

```python
rgb = interpolate_color(urgency, (150, 150, 150), (255, 0, 0))
hex_color = rgb_to_hex(rgb)
```

## Rich use example

```python
from rich.console import Console
from rich.text import Text

def show_urgency_rich(urgency, subject):
    rgb = interpolate_color(urgency, (150, 150, 150), (255, 0, 0))
    hex_color = rgb_to_hex(rgb)
    text = Text(subject, style=f"bold {hex_color}")
    Console().print(text)
```

## 3. Textual (Text Widget or Label)

If using a Label or Static, you’d do:

```python
from textual.widgets import Label
from textual.reactive import reactive

class UrgencyLabel(Label):
    urgency = reactive(0.0)

    def watch_urgency(self, urgency):
        rgb = interpolate_color(urgency, (150, 150, 150), (255, 0, 0))
        self.styles.color = rgb_to_hex(rgb)
        self.update(f"{urgency:.2f}")
```

## 4. Click Output with Rich

Click doesn’t support colored text natively, but you can use rich-click or just print with rich:

```python
import click
from rich.console import Console
from rich.text import Text

@click.command()
@click.argument("urgency", type=float)
def show_click_urgency(urgency):
    subject = "Task: Write docs"
    rgb = interpolate_color(urgency, (150, 150, 150), (255, 0, 0))
    hex_color = rgb_to_hex(rgb)
    text = Text(subject, style=hex_color)
    Console().print(text)

if __name__ == "__main__":
    show_click_urgency()
```

## Summary

| Context | Output Style                                               |
| ------- | ---------------------------------------------------------- |
| Textual | widget.styles.color = #rrggbb                              |
| Rich    | Text("msg", style="#rrggbb")                               |
| Click   | Use rich.print() or Console().print() with Rich formatting |

## Buckets

```python
from typing import List, Tuple

def hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

def rgb_to_hex(rgb: Tuple[int, int, int]) -> str:
    return "#{:02x}{:02x}{:02x}".format(*rgb)

def get_urgency_color_buckets(neg_hex: str, max_hex: str, steps: int = 10) -> List[str]:
    neg_rgb = hex_to_rgb(neg_hex)
    max_rgb = hex_to_rgb(max_hex)

    buckets = []
    for i in range(steps):
        t = i / (steps - 1)
        rgb = tuple(round(neg + t * (maxc - neg)) for neg, maxc in zip(neg_rgb, max_rgb))
        buckets.append(rgb_to_hex(rgb))
    return buckets

def urgency_to_bucket_color(urgency: float, buckets: List[str], neg_color: str) -> str:
    if urgency <= 0.0:
        return neg_color
    i = min(int(urgency * len(buckets)), len(buckets) - 1)
    return buckets[i]

# Demonstration of color buckets

if __name__ == "__main__":
    neg_color = "#6495ED"
    neg_color = "#B0C4DE"
    neg_color = "#708090"
    max_color = "#FFFF00"  # config.ui.maximum_urgency
    buckets = get_urgency_color_buckets(neg_color, max_color, 5)

    for bucket_color in buckets:




```
