"""Narrow, inspectable formatting and portability observations."""

import ast
import re

from .model import Analysis

ABSOLUTE = re.compile(r"^(?:/[^ /]|[A-Za-z]:[/\\]|\\\\[^\\]+\\)")
FILESYSTEM = {
    "python": re.compile(
        r"\b(?:open|Path|read_csv|read_table|read_excel|to_csv|save|load|chdir|"
        r"read_parquet|write_parquet)\s*\($"
    ),
    "r": re.compile(
        r"\b(?:setwd|read\.[A-Za-z0-9_.]+|read_[A-Za-z0-9_]+|"
        r"write\.[A-Za-z0-9_.]+|write_[A-Za-z0-9_]+|load|save|saveRDS|"
        r"readRDS|source|file|dir\.create)\s*\($"
    ),
    "stata": re.compile(
        r"^\s*(?:(?:qui\w*|cap\w*|noi\w*)\s+)*"
        r"(?:cd|use|save|append|merge|import|export|insheet|outsheet|"
        r"do|run|include|log|file)\b"
    ),
}


def literal_value(text: str, language: str) -> str:
    if language in {"python", "r"}:
        try:
            value = ast.literal_eval(text)
            return value if isinstance(value, str) else ""
        except (ValueError, SyntaxError):
            return ""
    if language == "stata" and text.startswith('`"') and text.endswith("\"'"):
        return text[2:-2]
    return text.strip("\"'")


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
    for i, token in enumerate(a.tokens):
        if token.kind == "string":
            value = literal_value(token.value, a.unit.language)
            if ABSOLUTE.match(value):
                # Require the literal to be the first argument, rather than an
                # unrelated string on the same line as a filesystem call.
                before = "".join(
                    t.value
                    for t in a.tokens[max(0, i - 4) : i]
                    if t.kind != "structure"
                )
                recognized = bool(FILESYSTEM[a.unit.language].search(before))
                if a.unit.language == "stata":
                    recognized = bool(FILESYSTEM["stata"].search(lines[token.line - 1]))
                a.finding(
                    "absolute_path" if recognized else "path_like_literal",
                    token.line,
                    token.col,
                    token.value,
                )
        if (
            token.value == "setwd"
            and a.unit.language == "r"
            and i + 1 < len(a.tokens)
            and a.tokens[i + 1].value == "("
        ):
            a.finding(
                "working_directory_change", token.line, token.col, lines[token.line - 1]
            )
        if (
            token.value == "chdir"
            and a.unit.language == "python"
            and i + 1 < len(a.tokens)
            and a.tokens[i + 1].value == "("
        ):
            a.finding(
                "working_directory_change", token.line, token.col, lines[token.line - 1]
            )
        if (
            token.value == "cd"
            and a.unit.language == "stata"
            and token.kind == "keyword"
        ):
            a.finding(
                "working_directory_change", token.line, token.col, lines[token.line - 1]
            )
