"""Python source: tokens from the standard tokenizer, structure from the AST."""

import ast
import io
import keyword
import re
import tokenize

from ..model import Analysis, Token
from . import call_syntax

FILESYSTEM = re.compile(
    r"\b(?:open|Path|read_csv|read_table|read_excel|to_csv|save|load|chdir|"
    r"read_parquet|write_parquet)\s*\($"
)

read_string = call_syntax.read_string


def read_tokens(a: Analysis, adapter) -> None:
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
            elif tokenize.tok_name[t.type] in {"FSTRING_MIDDLE", "TSTRING_MIDDLE"}:
                normalized, kind = "<string>", "string_fragment"
            elif tokenize.tok_name[t.type] in {
                "FSTRING_START",
                "FSTRING_END",
                "TSTRING_START",
                "TSTRING_END",
            }:
                normalized = f"<{tokenize.tok_name[t.type]}>"
            if not value.strip() and kind != "string_fragment":
                continue
            a.tokens.append(
                Token(value, normalized, t.start[0], t.start[1] + 1, t.end[0], kind)
            )
    except (tokenize.TokenError, IndentationError, SyntaxError, ValueError) as exc:
        a.token_status, a.detail = "failed", str(exc)
        a.tokens.clear()


def read_structure(a: Analysis, adapter) -> None:
    try:
        root = ast.parse(a.unit.source)
    except (SyntaxError, ValueError, RecursionError) as exc:
        a.structure_status, a.detail = "failed", str(exc)
        return
    controls = (
        ast.If,
        ast.IfExp,
        ast.For,
        ast.AsyncFor,
        ast.While,
        ast.Try,
        ast.TryStar,
        ast.Match,
    )
    routines = (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)
    stack = [(root, 0)]
    while stack:
        node, depth = stack.pop()
        if isinstance(node, routines):
            a.routines.append((node.lineno, node.end_lineno))
            depth = 0
        if isinstance(node, controls):
            depth += 1
            a.branch_count += 1
            a.max_nesting = max(a.max_nesting, depth)
        stack.extend((n, depth) for n in ast.iter_child_nodes(node))


def is_filesystem_call(tokens, i, lines) -> bool:
    return call_syntax.is_first_argument(tokens, i, FILESYSTEM)


def is_directory_change(tokens, i) -> bool:
    return (
        tokens[i].value == "chdir"
        and i + 1 < len(tokens)
        and tokens[i + 1].value == "("
        and (i == 0 or tokens[i - 1].value != "def")
    )
