"""Observable control-flow and routine structure, not semantic complexity."""

import ast
import re

from .lexical import r_parser
from .model import Analysis


def python_structure(a: Analysis) -> None:
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


def r_structure(a: Analysis) -> None:
    root = r_parser().parse(a.unit.source.encode()).root_node
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


def stata_structure(a: Analysis, adapter) -> None:
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


def measure_structure(a: Analysis, adapter) -> None:
    if a.token_status != "complete":
        a.structure_status = a.token_status
        return
    if a.unit.language == "python":
        python_structure(a)
    elif a.unit.language == "r":
        r_structure(a)
    elif a.unit.language == "stata":
        stata_structure(a, adapter)


def routine_lengths(a: Analysis) -> list[int]:
    return [
        sum(start <= line <= end for line in a.code_lines) for start, end in a.routines
    ]


def top_level_lines(a: Analysis) -> int:
    return sum(
        not any(start <= line <= end for start, end in a.routines)
        for line in a.code_lines
    )
