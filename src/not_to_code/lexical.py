"""Language-aware tokens with source positions and explicit lexical failures."""

from .languages import LANGUAGES
from .model import Analysis


def tokenize_unit(a: Analysis, adapter) -> None:
    if a.unit.incomplete:
        a.token_status, a.detail = (
            "failed",
            "Incomplete chunk or unsupported notebook magic",
        )
        return
    language = LANGUAGES.get(a.unit.language)
    if language:
        language.read_tokens(a, adapter)
    else:
        a.token_status, a.detail = "unsupported", "Unsupported source language"
    for t in a.tokens:
        if t.kind != "structure":
            a.code_lines.update(range(t.line, t.end_line + 1))
