from __future__ import annotations
from textual.widgets import Tree
from rich.text import Text

"""
- Actions:
    - [bold]?[/bold]: Display this help screen
    - [bold]/[/bold]: Search
    - [bold]^Q[/bold]: Quit
    - [bold]^S[/bold]: Screenshot
    - [bold]a,b,...,z[/bold]: Display details for reminder with corresponding tag
    - [bold]A,B,...[/bold]: Display corresponding view
- Views: 
    - [bold]A[/bold]: Agenda 
    - [bold]B[/bold]: Bins 
    - [bold]C[/bold]: Completions
    - [bold]F[/bold]: Find 
    - [bold]H[/bold]: Hash Tags
    - [bold]L[/bold]: Last Instances
    - [bold]N[/bold]: Next Instances
    - [bold]R[/bold]: Remaining Alerts for Today
    - [bold]W[/bold]: Weeks
"""

HELP_SCHEMA = {
    "Actions": {
        "bindings": {
            "?": "Display this help screen",
            "/": "Search",
            "^Q": "Quit",
            "^S": "Screenshot",
            "a,b,...,z": "Display details for reminder with the corresponding tag",
            "A,B,...": "Display corresponding view",
        },
    },
    "Views": {
        "A: Agenda": {
            "description": "Shows the next 3 days of events + urgency-ranked tasks.",
            "bindings": {
                "→": "Next page",
                "←": "Previous page",
                "↑": "scroll up",
                "↓": "scroll down",
            },
        },
        "B: Bins": {},
        "C: Completions": {},
        "F: Find": {},
        "H: Hash Tags": {},
        "L: Last Instances": {},
        "N: Next Instances": {},
        "R: Remaining Alerts for Today": {},
        "W: Weeks": {},
    },
}
{}

# Hierarchical help schema for Tklr UI and CLI.
HELP_SCHEMA = {
    "UI (Textual)": {
        "Agenda View": {
            "description": "Shows 3-day pages + urgency-ranked tasks.",
            "bindings": {
                ">": "Next page",
                "<": "Previous page",
                "t": "Toggle tasks pane",
            },
        },
        "4-Week Table": {
            "description": "Calendar grid of 28 days with busy bars.",
            "bindings": {
                "j": "Jump to today",
                "w": "Cycle week focus",
            },
        },
        "Screens": {
            "BinHierarchyScreen": {
                "description": "Expandable bin navigation screen.",
                "bindings": {
                    "escape": "Dismiss",
                    "e": "Expand to depth",
                    "c": "Collapse node",
                },
            },
        },
    },
    "CLI (Click)": {
        "Bidding Simulation": {
            "description": "Bridge 2/1 Game Forcing with Stayman + Jacoby Transfers.",
            "bindings": {
                "b": "Begin bidding",
                "c": "Continue bidding",
                "n/e/s/w": "Reveal hand",
            },
        },
        "@-tokens": {
            "description": "Symbolic tokens for reminders, dates, bidding, urgency.",
            "items": {
                "@r": "New reminder record",
                "@f": "First instance datetime",
            },
        },
    },
    "Config & Environment": {
        "config.toml": {
            "description": "User preferences + conventions + recurrence rules.",
        },
        "tklr.db": {
            "description": "SQLite persistence for records, datetimes, bins, urgency.",
        },
    },
    "Some Feature": {
        "paragraph": (
            "This is one or more sentences of help text. It is not wrapped here. "
            "Rich + Textual will wrap it later based on terminal width."
        ),
        "Subfeature A": {
            "paragraph": "Even nested paragraphs are fine. They are attached under their node.",
        },
    },
}


def build_help_tree() -> Tree:
    """Build a Textual Tree from HELP_SCHEMA with paragraph leafs."""
    tree = Tree("Help", id="help-tree")

    def walk(parent, key: str, node_def: object) -> None:
        # Branch node (dict)
        if isinstance(node_def, dict):
            node = parent.add(key)

            # 1) Attach paragraph guidance if present on this branch
            if "paragraph" in node_def:
                node.add(Text(node_def["paragraph"], style="dim"))

            # 2) Recurse for real children (excluding structural keys)
            for k, v in node_def.items():
                if k in ("paragraph", "description", "bindings", "items"):
                    continue
                walk(node, k, v)

            # 3) Attach structured binding help under a collapsible group
            if "bindings" in node_def and isinstance(node_def["bindings"], dict):
                bind_group = node.add("⌨ Bindings")
                for bkey, bdesc in node_def["bindings"].items():
                    # bindings arrows kept short, children wrap if long
                    bind_group.add(Text(f"{bkey} → {bdesc}", style="bold"))

            # 4) Attach item lists (like token glossaries) under their own group
            if "items" in node_def and isinstance(node_def["items"], dict):
                item_group = node.add("🔖 Items")
                for ikey, idesc in node_def["items"].items():
                    item_group.add(Text(f"{ikey} → {idesc}", style="dim"))

        # Leaf paragraph (string)
        else:
            node = parent.add(key)
            # Attach inner string or treat paragraph payload as text
            if isinstance(node_def, str):
                node.add(Text(node_def, style="dim"))

    # Populate tree from schema
    for topic, definition in HELP_SCHEMA.items():
        walk(tree.root, topic, definition)

    # Default UX: expand only the root level
    if tree.root is not None:
        tree.root.expand()

    return tree


if __name__ == "__main__":
    tree = build_help_tree()
    tree.dump()
