"""R source: tokens and structure from the tree-sitter grammar.

The lintr and flowR measures are in r_native.py; they run outside Python.
"""

import re
from functools import cache

from tree_sitter_language_pack import get_parser

from ..model import Analysis, Token
from . import call_syntax

FILESYSTEM = re.compile(
    r"\b(?:setwd|read\.[A-Za-z0-9_.]+|read_[A-Za-z0-9_]+|"
    r"write\.[A-Za-z0-9_.]+|write_[A-Za-z0-9_]+|load|save|saveRDS|"
    r"readRDS|source|file|dir\.create)\s*\($"
)

read_string = call_syntax.read_string


@cache
def parser():
    return get_parser("r")


def read_tokens(a: Analysis, adapter) -> None:
    source = a.unit.source.encode("utf-8")
    tree = parser().parse(source)
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


def read_structure(a: Analysis, adapter) -> None:
    root = parser().parse(a.unit.source.encode()).root_node
    if root.has_error:
        a.structure_status, a.detail = "failed", "R grammar contains errors"
        return
    controls = {"if_statement", "for_statement", "while_statement", "repeat_statement"}
    stack = [(root, 0)]
    while stack:
        node, depth = stack.pop()
        if node.type == "function_definition":
            a.routines.append((node.start_point.row + 1, node.end_point.row + 1))
            depth = 0
        if node.type in controls:
            depth += 1
            a.branch_count += 1
            a.max_nesting = max(a.max_nesting, depth)
        stack.extend((n, depth) for n in node.named_children)


def is_filesystem_call(tokens, i, lines) -> bool:
    return call_syntax.is_first_argument(tokens, i, FILESYSTEM)


def is_directory_change(tokens, i) -> bool:
    return (
        tokens[i].value == "setwd"
        and i + 1 < len(tokens)
        and tokens[i + 1].value == "("
    )
