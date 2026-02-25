import ast
from pathlib import Path
from typing import Any

README_PATH = Path("README.md")
ITEM_PATH = Path("src/tklr/item.py")

CONFIG_BEGIN = "<!-- BEGIN CONFIG -->"
CONFIG_END = "<!-- END CONFIG -->"
TOKENS_BEGIN = "<!-- BEGIN TOKEN KEYS -->"
TOKENS_END = "<!-- END TOKEN KEYS -->"

TYPE_ORDER = ["*", "~", "^", "%", "!", "-", "x", "?"]
TOP_LEVEL_CONSTANTS = [
    "common_methods",
    "repeating_methods",
    "datetime_methods",
    "task_methods",
    "job_methods",
    "multiple_allowed",
    "wrap_methods",
    "required",
    "all_keys",
    "allowed",
    "requires",
]


def _extract_assignment(nodes: list[ast.stmt], name: str) -> Any:
    for node in nodes:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == name:
                    return ast.literal_eval(node.value)
        elif isinstance(node, ast.AnnAssign):
            if isinstance(node.target, ast.Name) and node.target.id == name:
                return ast.literal_eval(node.value)
    raise ValueError(f"Could not find assignment for '{name}'")


def _assignment_target_names(node: ast.Assign | ast.AnnAssign) -> set[str]:
    if isinstance(node, ast.Assign):
        return {
            target.id
            for target in node.targets
            if isinstance(target, ast.Name)
        }
    if isinstance(node.target, ast.Name):
        return {node.target.id}
    return set()


def _evaluate_top_level_constants(tree: ast.Module) -> dict[str, Any]:
    namespace: dict[str, Any] = {}
    found: set[str] = set()
    wanted = set(TOP_LEVEL_CONSTANTS)

    for node in tree.body:
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        target_names = _assignment_target_names(node)
        if not target_names.intersection(wanted):
            continue
        code = compile(
            ast.Module(body=[node], type_ignores=[]),
            filename=str(ITEM_PATH),
            mode="exec",
        )
        exec(code, {}, namespace)
        found.update(target_names.intersection(wanted))

    missing = wanted - found
    if missing:
        names = ", ".join(sorted(missing))
        raise ValueError(f"Could not evaluate constants from item.py: {names}")

    return {name: namespace[name] for name in TOP_LEVEL_CONSTANTS}


def _load_item_constants() -> dict[str, Any]:
    source = ITEM_PATH.read_text()
    tree = ast.parse(source, filename=str(ITEM_PATH))

    top_level = _evaluate_top_level_constants(tree)
    multiple_allowed = top_level["multiple_allowed"]
    required = top_level["required"]
    allowed = top_level["allowed"]
    requires = top_level["requires"]

    item_class = next(
        (
            node
            for node in tree.body
            if isinstance(node, ast.ClassDef) and node.name == "Item"
        ),
        None,
    )
    if item_class is None:
        raise ValueError("Could not find class Item in src/tklr/item.py")
    token_keys = _extract_assignment(item_class.body, "token_keys")

    return {
        "multiple_allowed": multiple_allowed,
        "required": required,
        "allowed": allowed,
        "requires": requires,
        "token_keys": token_keys,
    }


def _token_usage_keys(constants: dict[str, Any]) -> set[str]:
    keys = set(constants["multiple_allowed"])
    for mapping_name in ("required", "allowed"):
        mapping = constants[mapping_name]
        for values in mapping.values():
            keys.update(values)

    keys.update(constants["requires"].keys())
    for values in constants["requires"].values():
        keys.update(values)
    return keys


def _key_to_display(key: str, *, include_arg: bool = True) -> str:
    if key == "rr":
        return "@r <freq>" if include_arg else "@r"
    if key == "~":
        return "@~"
    if len(key) == 1:
        return f"@{key}"
    if len(key) == 2 and key[0] == "r":
        return f"@r &{key[1]}"
    if len(key) == 2 and key[0] == "~":
        return f"@~ &{key[1]}"
    return key


def _format_types(types: list[str]) -> str:
    if not types:
        return " "
    return ", ".join(types)


def _format_keys(keys: list[str]) -> str:
    if not keys:
        return " "
    return ", ".join(f"`{_key_to_display(key, include_arg=False)}`" for key in keys)


def _md_escape(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", " ").strip()


def _row_sort_key(key: str) -> tuple[str, str]:
    """
    Sort rows alphabetically by user-facing @-key and keep grouped subkeys together.
    """
    base = _key_to_display(key, include_arg=False)
    shown = _key_to_display(key, include_arg=True)
    return (base, shown)


def render_token_keys_block() -> str:
    constants = _load_item_constants()
    token_keys: dict[str, list[str]] = constants["token_keys"]
    usage_keys = _token_usage_keys(constants)
    multiple_allowed = set(constants["multiple_allowed"])
    required = constants["required"]
    allowed = constants["allowed"]
    requires = constants["requires"]

    row_keys = sorted(
        (key for key in token_keys.keys() if key in usage_keys),
        key=_row_sort_key,
    )

    lines = [
        "| key | name | allowed | required | requires | multiple |",
        "| --- | --- | --- | --- | --- | --- |",
    ]

    for key in row_keys:
        info = token_keys[key]
        name = _md_escape(info[0]) if info else ""
        allowed_types = [type_key for type_key in TYPE_ORDER if key in allowed[type_key]]
        required_types = [type_key for type_key in TYPE_ORDER if key in required[type_key]]
        requires_keys = requires.get(key, [])
        multiple = "yes" if key in multiple_allowed else "no"

        lines.append(
            "| "
            + " | ".join(
                [
                    f"`{_key_to_display(key)}`",
                    name,
                    _format_types(allowed_types),
                    _format_types(required_types),
                    _format_keys(requires_keys),
                    multiple,
                ]
            )
            + " |"
        )

    return "\n".join(lines)


def render_config_block() -> str:
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parent / "src/tklr"))
    from jinja2 import Template
    from tklr_env import TklrConfig, CONFIG_TEMPLATE

    config = TklrConfig()
    template = Template(CONFIG_TEMPLATE)
    rendered = template.render(**config.model_dump()).strip()
    return f"```toml\n{rendered}\n```"


def replace_block(readme: str, begin: str, end: str, content: str) -> tuple[str, bool]:
    start = readme.find(begin)
    finish = readme.find(end)

    if start == -1 and finish == -1:
        return readme, False
    if start == -1 or finish == -1:
        raise ValueError(f"README.md must include both {begin} and {end}")
    if start > finish:
        raise ValueError(f"README.md has misplaced markers: {begin} after {end}")

    before = readme[:start]
    after = readme[finish + len(end) :]
    new_block = f"{begin}\n\n{content}\n\n{end}"
    return before + new_block + after, True


def update_readme() -> None:
    readme = README_PATH.read_text()
    updated_sections = []

    if CONFIG_BEGIN in readme or CONFIG_END in readme:
        readme, config_updated = replace_block(
            readme, CONFIG_BEGIN, CONFIG_END, render_config_block()
        )
        if config_updated:
            updated_sections.append("config")

    if TOKENS_BEGIN in readme or TOKENS_END in readme:
        readme, tokens_updated = replace_block(
            readme, TOKENS_BEGIN, TOKENS_END, render_token_keys_block()
        )
        if tokens_updated:
            updated_sections.append("token keys")

    if not updated_sections:
        raise ValueError(
            "README.md has no recognized update markers. "
            "Add token key markers or config markers first."
        )

    README_PATH.write_text(readme)
    print(f"✅ Updated README.md sections: {', '.join(updated_sections)}")


if __name__ == "__main__":
    update_readme()
