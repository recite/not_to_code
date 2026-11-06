"""Narrow, inspectable formatting and portability observations."""

import re

from .languages import LANGUAGES
from .model import Analysis

ABSOLUTE = re.compile(r"^(?:/[^ /]|[A-Za-z]:[/\\]|\\\\[^\\]+\\)")


def measure_findings(a: Analysis) -> None:
    if a.token_status != "complete":
        return
    lines = a.unit.source.splitlines()
    for n in sorted(a.code_lines):
        if n > len(lines):
            continue
        line = lines[n - 1]
        if len(line) > 100:
            a.finding("line_over_100", n, 101, line)
        if line.rstrip(" \t") != line:
            a.finding("trailing_whitespace", n, len(line.rstrip()) + 1, line)
        prefix = line[: len(line) - len(line.lstrip(" \t"))]
        if " " in prefix and "\t" in prefix:
            a.finding("mixed_indentation", n, 1, line)
    language = LANGUAGES.get(a.unit.language)
    if not language:
        return
    for i, token in enumerate(a.tokens):
        if token.kind == "string" and ABSOLUTE.match(language.read_string(token.value)):
            a.finding(
                (
                    "absolute_path"
                    if language.is_filesystem_call(a.tokens, i, lines)
                    else "path_like_literal"
                ),
                token.line,
                token.col,
                token.value,
            )
        if language.is_directory_change(a.tokens, i):
            a.finding(
                "working_directory_change", token.line, token.col, lines[token.line - 1]
            )
