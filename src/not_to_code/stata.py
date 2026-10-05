"""Position-preserving lexical instrument; does not validate Stata syntax."""

import re

from .model import Token

WORD = re.compile(
    r"[A-Za-z_][A-Za-z_0-9.]*|\d+(?:\.\d*)?(?:[eE][+-]?\d+)?|==|!=|<=|>=|[&|]{2}|[^\s]"
)
DIRECTIVE = re.compile(r"#[ \t]*d(?:e(?:l(?:i(?:m(?:it?)?)?)?)?)?\s+(cr|;)")


def tokens(source: str) -> list[Token]:
    result = []
    i, line, col = 0, 1, 1
    semicolon = False
    first = True
    line_first = True
    parens = 0

    def advance(text):
        nonlocal line, col
        if "\n" in text:
            line += text.count("\n")
            col = len(text.rsplit("\n", 1)[-1]) + 1
        else:
            col += len(text)

    def emit(value, kind, end_line=None):
        normalized = (
            f"<{kind}>"
            if kind in {"identifier", "string", "number", "macro"}
            else value
        )
        result.append(Token(value, normalized, line, col, end_line or line, kind))

    while i < len(source):
        ch = source[i]
        if line_first and ch == "#":
            match = DIRECTIVE.match(source, i)
            if match:
                semicolon = match[1] == ";"
                end = source.find("\n", i)
                end = len(source) if end < 0 else end
                advance(source[i:end])
                i = end
                continue
        if source.startswith("/*", i):
            j, depth = i + 2, 1
            while j < len(source) and depth:
                if source.startswith("/*", j):
                    depth += 1
                    j += 2
                elif source.startswith("*/", j):
                    depth -= 1
                    j += 2
                else:
                    j += 1
            if depth:
                raise ValueError(f"Unclosed block comment at {line}:{col}")
            advance(source[i:j])
            i = j
            continue
        slash = source.startswith("//", i) and (i == 0 or source[i - 1].isspace())
        if slash or (ch == "*" and line_first):
            end = source.find("\n", i)
            end = len(source) if end < 0 else end
            if slash and source.startswith("///", i) and end < len(source):
                end += 1
            advance(source[i:end])
            i = end
            continue
        if ch == "\n" or (ch == ";" and semicolon and not parens):
            if (ch == ";" or not semicolon) and not first:
                emit("<STMT>", "structure")
                first = True
            advance(ch)
            line_first = True
            i += 1
            continue
        if ch.isspace():
            advance(ch)
            i += 1
            continue
        start = i
        if source.startswith('`"', i):
            i += 2
            depth = 1
            while i < len(source) and depth:
                if source.startswith('`"', i):
                    depth += 1
                    i += 2
                elif source.startswith("\"'", i):
                    depth -= 1
                    i += 2
                else:
                    i += 1
            if depth:
                raise ValueError(f"Unclosed compound string at {line}:{col}")
            kind = "string"
        elif ch == '"':
            end = source.find('"', i + 1)
            if end < 0 or (not semicolon and "\n" in source[i:end]):
                raise ValueError(f"Unclosed string at {line}:{col}")
            i, kind = end + 1, "string"
        elif ch == "`":
            end = source.find("'", i + 1)
            if end < 0:
                raise ValueError(f"Unclosed local macro at {line}:{col}")
            i, kind = end + 1, "macro"
        elif ch == "$":
            match = re.match(r"\$(?:\{[^}]+\}|[A-Za-z_0-9]+)", source[i:])
            if not match:
                raise ValueError(f"Unresolved global macro at {line}:{col}")
            i, kind = i + len(match[0]), "macro"
        else:
            match = WORD.match(source, i)
            value = match[0]
            kind = (
                "keyword"
                if (first or value in {"if", "else", "in", "using"})
                and value[0].isalpha()
                else (
                    "identifier"
                    if value[0].isalpha() or value[0] == "_"
                    else "number" if value[0].isdigit() else "other"
                )
            )
            i = match.end()
        value = source[start:i]
        emit(value, kind, line + value.count("\n"))
        advance(value)
        parens += (value == "(") - (value == ")")
        parens = max(parens, 0)
        first = value in {"{", "}"} and kind == "other" and not parens
        line_first = False
    if result and result[-1].value != "<STMT>":
        emit("<STMT>", "structure")
    return result
