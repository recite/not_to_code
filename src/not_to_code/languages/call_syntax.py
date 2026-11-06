"""Path rules shared by Python and R, which both write calls as name(arguments)."""

import ast


def read_string(text: str) -> str:
    try:
        value = ast.literal_eval(text)
    except (ValueError, SyntaxError):
        return ""
    return value if isinstance(value, str) else ""


def is_first_argument(tokens, i, callee) -> bool:
    before = tokens[max(0, i - 2) : i]
    return bool(
        len(before) == 2
        and before[0].kind == "identifier"
        and before[1].value == "("
        and callee.fullmatch(before[0].value + "(")
    )
