#!/usr/bin/env python3
"""Low-noise HTML structure checker for markdown files with embedded HTML.

Focuses on mismatched/unclosed tags and reports useful source line numbers.
Intentionally ignores markdown style issues such as line length.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path


TAG_RE = re.compile(r"<(/?)([A-Za-z][A-Za-z0-9-]*)([^>]*)>")
FENCE_RE = re.compile(r"^\s*```")

# Restrict to standard HTML tags commonly used in README content.
# This avoids false positives from placeholder text such as "<list>".
KNOWN_TAGS = {
    "a",
    "article",
    "aside",
    "b",
    "blockquote",
    "br",
    "code",
    "dd",
    "details",
    "div",
    "dl",
    "dt",
    "em",
    "figcaption",
    "figure",
    "footer",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "header",
    "hr",
    "i",
    "img",
    "li",
    "main",
    "nav",
    "ol",
    "p",
    "pre",
    "section",
    "span",
    "strong",
    "summary",
    "table",
    "tbody",
    "td",
    "th",
    "thead",
    "tr",
    "u",
    "ul",
}

VOID_TAGS = {
    "area",
    "base",
    "br",
    "col",
    "embed",
    "hr",
    "img",
    "input",
    "link",
    "meta",
    "param",
    "source",
    "track",
    "wbr",
}

# These starts can implicitly terminate a <p> in HTML parsing.
P_TERMINATORS = {
    "address",
    "article",
    "aside",
    "blockquote",
    "details",
    "div",
    "dl",
    "fieldset",
    "figcaption",
    "figure",
    "footer",
    "form",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "header",
    "hgroup",
    "hr",
    "main",
    "menu",
    "nav",
    "ol",
    "p",
    "pre",
    "section",
    "table",
    "ul",
}


@dataclass
class OpenTag:
    name: str
    line: int
    col: int


@dataclass
class Issue:
    line: int
    col: int
    message: str
    code: str = "generic"
    tag: str | None = None
    related_line: int | None = None
    related_col: int | None = None


def parse_lines(lines: list[str]) -> list[Issue]:
    stack: list[OpenTag] = []
    issues: list[Issue] = []
    in_fence = False

    for line_no, raw in enumerate(lines, start=1):
        if FENCE_RE.match(raw):
            in_fence = not in_fence
            continue
        if in_fence:
            continue

        for match in TAG_RE.finditer(raw):
            slash, tag_name, attrs = match.groups()
            tag = tag_name.lower()
            col = match.start() + 1
            full = match.group(0)

            if full.startswith("<!--"):
                continue

            is_self_closing = attrs.rstrip().endswith("/")
            if tag not in KNOWN_TAGS:
                continue
            if tag in VOID_TAGS:
                continue

            if slash:
                if not stack:
                    issues.append(
                        Issue(
                            line_no,
                            col,
                            f"Unexpected closing tag </{tag}> with no matching opener",
                            code="unexpected_close",
                            tag=tag,
                        )
                    )
                    continue

                top = stack[-1]
                if top.name == tag:
                    stack.pop()
                    continue

                match_index = -1
                for i in range(len(stack) - 1, -1, -1):
                    if stack[i].name == tag:
                        match_index = i
                        break

                if match_index == -1:
                    issues.append(
                        Issue(
                            line_no,
                            col,
                            f"Unexpected closing tag </{tag}> with no matching opener",
                            code="unexpected_close",
                            tag=tag,
                        )
                    )
                    continue

                expected = top.name
                issues.append(
                    Issue(
                        line_no,
                        col,
                        f"Mismatched closing tag </{tag}>; top open tag is <{expected}>"
                        f" from line {top.line}",
                        code="mismatched_close",
                        tag=tag,
                    )
                )
                while stack and stack[-1].name != tag:
                    unclosed = stack.pop()
                    issues.append(
                        Issue(
                            unclosed.line,
                            unclosed.col,
                            f"Tag <{unclosed.name}> opened here was not properly closed",
                            code="broken_nesting",
                            tag=unclosed.name,
                        )
                    )
                if stack and stack[-1].name == tag:
                    stack.pop()
                continue

            if is_self_closing:
                continue

            # Report the common markdown/HTML mistake explicitly:
            # an open <p> followed by a block-level tag.
            if stack and stack[-1].name == "p" and tag in P_TERMINATORS:
                p_tag = stack.pop()
                issues.append(
                    Issue(
                        p_tag.line,
                        p_tag.col,
                        f"<p> opened here is implicitly closed by <{tag}> at line {line_no};"
                        " add an explicit </p>",
                        code="implicit_p_close",
                        tag="p",
                        related_line=line_no,
                        related_col=col,
                    )
                )

            stack.append(OpenTag(tag, line_no, col))

    for unclosed in stack:
        issues.append(
            Issue(
                unclosed.line,
                unclosed.col,
                f"Unclosed tag <{unclosed.name}>",
                code="unclosed_tag",
                tag=unclosed.name,
            )
        )

    return issues


def parse_file(path: Path) -> list[Issue]:
    text = path.read_text(encoding="utf-8")
    return parse_lines(text.splitlines())


def apply_fixes(path: Path) -> bool:
    """Apply safe, low-risk fixes in place.

    Current auto-fixes:
    1) Insert explicit </p> before a block tag that implicitly closes <p>.
    2) Remove unmatched stray </p> tags left behind by (1).
    """
    text = path.read_text(encoding="utf-8")
    had_trailing_newline = text.endswith("\n")
    lines = text.splitlines()
    changed = False

    issues = parse_lines(lines)
    implicit_p = [
        issue
        for issue in issues
        if issue.code == "implicit_p_close"
        and issue.related_line is not None
        and issue.related_col is not None
    ]
    for issue in sorted(
        implicit_p,
        key=lambda x: (x.related_line or 0, x.related_col or 0),
        reverse=True,
    ):
        line_idx = (issue.related_line or 1) - 1
        col_idx = max(0, (issue.related_col or 1) - 1)
        line = lines[line_idx]
        if line[max(0, col_idx - 4) : col_idx].lower() == "</p>":
            continue
        lines[line_idx] = f"{line[:col_idx]}</p>{line[col_idx:]}"
        changed = True

    # Reparse after insertions and drop unmatched trailing </p>.
    issues_after_insert = parse_lines(lines)
    stray_p = [
        issue
        for issue in issues_after_insert
        if issue.code == "unexpected_close" and issue.tag == "p"
    ]
    for issue in sorted(stray_p, key=lambda x: (x.line, x.col), reverse=True):
        line_idx = issue.line - 1
        line = lines[line_idx]
        search_start = max(0, issue.col - 2)
        lower = line.lower()
        pos = lower.find("</p>", search_start)
        if pos == -1:
            pos = lower.find("</p>")
        if pos == -1:
            continue
        lines[line_idx] = f"{line[:pos]}{line[pos + 4:]}"
        changed = True

    if changed:
        new_text = "\n".join(lines)
        if had_trailing_newline:
            new_text += "\n"
        path.write_text(new_text, encoding="utf-8")
    return changed


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description="Check embedded HTML structure in markdown files."
    )
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Apply safe automatic fixes for paragraph/list mismatch cases.",
    )
    parser.add_argument("paths", nargs="*", default=["README.md"])
    args = parser.parse_args(argv)

    paths = [Path(x) for x in args.paths]
    exit_code = 0
    for path in paths:
        if not path.exists():
            print(f"{path}:0:0: File not found")
            exit_code = 2
            continue

        fixed = False
        if args.fix:
            fixed = apply_fixes(path)

        issues = parse_file(path)
        if issues:
            exit_code = 1
            if fixed:
                print(f"{path}: auto-fix applied; remaining issues:")
            for issue in issues:
                print(f"{path}:{issue.line}:{issue.col}: {issue.message}")
        else:
            suffix = " (fixed)" if fixed else ""
            print(f"{path}: OK{suffix}")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
