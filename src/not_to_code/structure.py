"""Observable control-flow and routine structure, not semantic complexity."""

from .languages import LANGUAGES
from .model import Analysis


def measure_structure(a: Analysis, adapter) -> None:
    if a.token_status != "complete":
        a.structure_status = a.token_status
        return
    language = LANGUAGES.get(a.unit.language)
    if language:
        language.read_structure(a, adapter)


def routine_lengths(a: Analysis) -> list[int]:
    return [
        sum(start <= line <= end for line in a.code_lines) for start, end in a.routines
    ]


def top_level_lines(a: Analysis) -> int:
    return sum(
        not any(start <= line <= end for start, end in a.routines)
        for line in a.code_lines
    )
