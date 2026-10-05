"""Language-aware tokens with source positions and explicit lexical failures."""

import ast
import io
import keyword
import tokenize
from functools import cache

from tree_sitter_language_pack import get_parser

from .model import Analysis, Token


@cache
def r_parser():
    return get_parser("r")


def python_tokens(a: Analysis) -> None:
    docstrings = []
    lines = a.unit.source.splitlines()
    try:
        tree = ast.parse(a.unit.source)
        for node in ast.walk(tree):
            body = getattr(node, "body", None)
            if (
                isinstance(
                    node,
                    (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef),
                )
                and isinstance(body, list)
                and body
                and isinstance(body[0], ast.Expr)
                and isinstance(body[0].value, ast.Constant)
                and isinstance(body[0].value.value, str)
            ):
                docstrings.append(
                    (
                        body[0].lineno,
                        len(
                            lines[body[0].lineno - 1]
                            .encode()[: body[0].col_offset]
                            .decode()
                        ),
                        body[0].end_lineno,
                        len(
                            lines[body[0].end_lineno - 1]
                            .encode()[: body[0].end_col_offset]
                            .decode()
                        ),
                    )
                )
    except (SyntaxError, ValueError, RecursionError):
        pass
    try:
        for t in tokenize.generate_tokens(io.StringIO(a.unit.source).readline):
            if t.type in {
                tokenize.COMMENT,
                tokenize.NL,
                tokenize.ENDMARKER,
                tokenize.ENCODING,
            }:
                continue
            if t.type == tokenize.ERRORTOKEN and not t.string.isspace():
                raise ValueError(f"Invalid token at {t.start}")
            if any(
                (line, col) <= t.start < (end_line, end_col)
                for line, col, end_line, end_col in docstrings
            ):
                continue
            if t.type == tokenize.NEWLINE and any(
                t.start == (end_line, end_col) for _, _, end_line, end_col in docstrings
            ):
                continue
            kind = "other"
            value = t.string
            normalized = value
            if t.type in {tokenize.INDENT, tokenize.DEDENT, tokenize.NEWLINE}:
                value = normalized = f"<{tokenize.tok_name[t.type]}>"
                kind = "structure"
            elif t.type == tokenize.NAME and not keyword.iskeyword(value):
                normalized, kind = "<identifier>", "identifier"
            elif t.type in {tokenize.STRING, tokenize.NUMBER}:
                kind = "string" if t.type == tokenize.STRING else "number"
                normalized = f"<{kind}>"
            if not value.strip():
                continue
            a.tokens.append(
                Token(value, normalized, t.start[0], t.start[1] + 1, t.end[0], kind)
            )
    except (tokenize.TokenError, IndentationError, SyntaxError, ValueError) as exc:
        a.token_status, a.detail = "failed", str(exc)
        a.tokens.clear()


def r_tokens(a: Analysis) -> None:
    source = a.unit.source.encode("utf-8")
    tree = r_parser().parse(source)
    stack = [tree.root_node]
    terminals = []
    boundaries = set()
    while stack:
        n = stack.pop()
        if n.type == "comment":
            continue
        if n.type in {"program", "braced_expression"}:
            boundaries.update(
                c.end_byte for c in n.named_children if c.type != "comment"
            )
        if (
            n.type in {"string", "identifier", "float", "integer", "complex"}
            or not n.children
        ):
            terminals.append(n)
        else:
            stack.extend(reversed(n.children))
    for n in terminals:
        value = source[n.start_byte : n.end_byte].decode("utf-8")
        if not value.strip():
            continue
        if value == ";":
            continue
        kind = (
            "identifier"
            if n.type == "identifier"
            else (
                "string"
                if n.type == "string"
                else "number" if n.type in {"float", "integer", "complex"} else "other"
            )
        )
        normalized = f"<{kind}>" if kind != "other" else value
        a.tokens.append(
            Token(
                value,
                normalized,
                n.start_point.row + 1,
                len(
                    source[
                        source.rfind(b"\n", 0, n.start_byte) + 1 : n.start_byte
                    ].decode()
                )
                + 1,
                n.end_point.row + 1,
                kind,
            )
        )
        if n.end_byte in boundaries:
            a.tokens.append(
                Token(
                    "<STMT>",
                    "<STMT>",
                    n.end_point.row + 1,
                    1,
                    n.end_point.row + 1,
                    "structure",
                )
            )
    if tree.root_node.has_error:
        a.token_status = "failed"
        a.detail = "R grammar contains error or missing nodes"
        a.tokens.clear()


def stata_tokens(a: Analysis, adapter) -> None:
    from .stata import tokens

    try:
        a.tokens = tokens(a.unit.source)
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


def tokenize_unit(a: Analysis, adapter) -> None:
    if a.unit.incomplete:
        a.token_status, a.detail = (
            "failed",
            "Incomplete chunk or unsupported notebook magic",
        )
        return
    if a.unit.language == "python":
        python_tokens(a)
    elif a.unit.language == "r":
        r_tokens(a)
    elif a.unit.language == "stata":
        stata_tokens(a, adapter)
    else:
        a.token_status, a.detail = "unsupported", "Unsupported source language"
    for t in a.tokens:
        if t.kind != "structure":
            a.code_lines.update(range(t.line, t.end_line + 1))
