"""Stata source: a position-preserving lexer that does not validate syntax.

Statement prefixes and embedded-language detection come from Softverse's lexer.
"""

import re

from ..model import Analysis, Token

FILESYSTEM = re.compile(
    r"^\s*(?:(?:qui\w*|cap\w*|noi\w*)\s+)*"
    r"(?:cd|use|save|append|merge|import|export|insheet|outsheet|"
    r"do|run|include|log|file)\b"
)
WORD = re.compile(
    r"[A-Za-z_][A-Za-z_0-9.]*|\d+(?:\.\d*)?(?:[eE][+-]?\d+)?|==|!=|<=|>=|[&|]{2}|[^\s]"
)
DIRECTIVE = re.compile(r"#[ \t]*d(?:e(?:l(?:i(?:m(?:it?)?)?)?)?)?\s+(cr|;)")


def lex(source: str) -> list[Token]:
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


def read_tokens(a: Analysis, adapter) -> None:
    try:
        a.tokens = lex(a.unit.source)
        if any(
            t.kind == "keyword" and t.value.lower() in {"mata", "python", "rsource"}
            for t in a.tokens
        ) or any(
            (st.command or "").lower() in {"mata", "python", "rsource"}
            for st in adapter.stata.lex(a.unit.source)
        ):
            a.token_status = "partial"
            a.detail = "Embedded language: whole source unit withheld"
            a.tokens.clear()
    except ValueError as exc:
        a.token_status, a.detail = "failed", str(exc)
        a.tokens.clear()


def read_structure(a: Analysis, adapter) -> None:
    blocks = []
    routine_start = None
    statement = []
    for token in a.tokens:
        if token.value not in {"<STMT>", "{", "}"} or token.kind not in {
            "structure",
            "other",
        }:
            statement.append(token)
            continue
        if token.value == "}":
            if blocks:
                blocks.pop()
            else:
                a.structure_status = "partial"
        text = " ".join(t.value for t in statement)
        if statement:
            _, rest = adapter.stata._strip_prefixes(text.split())
            head = rest[0].lower().rstrip(":,") if rest else ""
            if "`" in head or "$" in head or head in {"mata", "python", "rsource"}:
                a.structure_status, a.detail = "partial", "Dynamic or embedded language"
            if re.match(
                r"^(?:pr|pro|prog|progr|progra|program)\s+(?!(?:drop|list|dir)\b)",
                " ".join(rest),
            ):
                routine_start = statement[0].line
                blocks = []
            elif head == "end" and routine_start is not None:
                a.routines.append((routine_start, token.line))
                routine_start = None
                blocks = []
            control = head in {
                "if",
                "foreach",
                "forvalues",
                "forval",
                "forv",
                "while",
            } or bool(head == "else" and re.match(r"else\s+if\b", text))
            if control:
                a.branch_count += 1
                a.max_nesting = max(a.max_nesting, sum(blocks) + 1)
        else:
            control = False
        if token.value == "{":
            blocks.append(control or bool(statement and head == "else"))
        statement = []
    if blocks or routine_start is not None:
        a.structure_status, a.detail = "partial", "Unclosed Stata block"


def read_string(text: str) -> str:
    if text.startswith('`"') and text.endswith("\"'"):
        return text[2:-2]
    return text.strip("\"'")


def is_filesystem_call(tokens, i, lines) -> bool:
    return bool(FILESYSTEM.search(lines[tokens[i].line - 1]))


def is_directory_change(tokens, i) -> bool:
    return tokens[i].value == "cd" and tokens[i].kind == "keyword"
