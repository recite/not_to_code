"""Deposit-level measurements and coverage, derived from the metric dictionary."""

from collections import Counter, defaultdict
from statistics import median

from .duplicates import measure_duplicates
from .registry import REGISTRY, measures
from .structure import routine_lengths, top_level_lines


def assess_language(analyses, language, eligibility_by_uid, environment, variant):
    selected = [
        a
        for a in analyses
        if a.unit.language == language
        and (variant == "primary" or eligibility_by_uid[a.unit.file_uid] == "included")
    ]
    if not selected:
        return [], []
    unresolved = [
        a
        for a in analyses
        if a.unit.language in {"notebook", "rmarkdown", "unknown"}
        and (variant == "primary" or eligibility_by_uid[a.unit.file_uid] == "included")
    ]
    tokenized = [a for a in selected if a.token_status == "complete"]
    structured = [a for a in selected if a.structure_status == "complete"]
    values, clones = measure_duplicates(tokenized)
    lines = sum(len(a.code_lines) for a in tokenized)
    files = defaultdict(int)
    for a in tokenized:
        files[a.unit.file_uid] += len(a.code_lines)
    lengths = [n for a in structured for n in routine_lengths(a)]
    values.update(
        {
            "file_count": (len({a.unit.file_uid for a in selected}), 1),
            "code_lines": (lines, 1),
            "token_count": (sum(len(a.tokens) for a in tokenized), 1),
            "median_file_lines": (median(files.values()) if files else None, 1),
            "largest_file_share": (max(files.values(), default=0), lines),
            "routine_count": (sum(len(a.routines) for a in structured), 1),
            "median_routine_lines": (median(lengths) if lengths else None, 1),
            "max_routine_lines": (max(lengths) if lengths else None, 1),
            "branch_count": (sum(a.branch_count for a in structured), 1),
            "max_nesting": (max((a.max_nesting for a in structured), default=0), 1),
            "top_level_share": (
                sum(top_level_lines(a) for a in structured),
                sum(len(a.code_lines) for a in structured),
            ),
        }
    )
    counts = Counter(f["rule"] for a in tokenized for f in a.findings)
    applicable = measures(language, "baseline")
    for name, spec in applicable.items():
        if spec["dimension"] in {"formatting", "portability"}:
            values[name] = (counts[name], lines)
        elif spec["dimension"] == "environment":
            values[name] = (int(name in environment), 1)
    rows = []
    for name, (numerator, denominator) in values.items():
        if name not in applicable:
            continue
        spec = REGISTRY[name]
        measured = (
            len(structured) if spec["coverage"] == "structure" else len(tokenized)
        )
        eligible = len(selected) + len(unresolved)
        if spec["coverage"] == "inventory":
            measured = len(selected)
        if spec["coverage"] == "environment":
            measured = eligible
        status = (
            "complete" if measured == eligible else "partial" if measured else "missing"
        )
        value = (
            numerator / denominator * spec["scale"]
            if numerator is not None and denominator
            else None
        )
        if not measured:
            value = None
        if value is None and status == "complete":
            status = "inapplicable"
        if spec["coverage"] == "environment" and value is not None:
            status = "inventory_only"
        if (
            language == "stata"
            and spec["dimension"] == "environment"
            and name != "interpreter_version"
        ):
            value, status, numerator, denominator = None, "unsupported", None, None
        rows.append(
            dict(
                language=language,
                variant=variant,
                metric=name,
                numerator=numerator if measured else None,
                denominator=denominator if measured else None,
                value=value,
                status=status,
                eligible_units=eligible,
                measured_units=measured,
            )
        )
    for row in clones:
        row["variant"] = variant
    return rows, clones
