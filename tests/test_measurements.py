import json

import pytest

from not_to_code.adapter import eligibility
from not_to_code.assessment import assess_language
from not_to_code.duplicates import coverage, measure_duplicates
from not_to_code.model import Analysis, Token, Unit
from not_to_code.structure import routine_lengths, top_level_lines


@pytest.mark.parametrize(
    "language,source,formatted",
    [
        ("python", "x=1\ny=2\n", "# prose\nx = 1 # comment\n\ny = 2\n"),
        ("r", "x<-1\ny<-2\n", "# prose\nx <- 1; y <- 2 # comment\n"),
        (
            "stata",
            "gen x=1\nreplace x=2\n",
            "* prose\ngen x = 1 // comment\n\nreplace x = 2\n",
        ),
    ],
)
def test_presentation_invariance(analyze, language, source, formatted):
    one, two = analyze(language, source), analyze(language, formatted)
    assert one.token_status == two.token_status == "complete"
    assert [t.value for t in one.tokens] == [t.value for t in two.tokens]


@pytest.mark.parametrize(
    "language,source",
    [
        (
            "python",
            'def f(x):\n    """documentation"""\n    if x:\n        for y in x:\n'
            "            print(y)\nf([1])\n",
        ),
        ("r", "f <- function(x) {\n if (x) {\n  for (y in x) print(y)\n }\n}\nf(1)\n"),
        (
            "stata",
            "program define f\nif x {\n foreach y in a b {\n"
            " display y\n }\n}\nend\nf\n",
        ),
    ],
)
def test_structure(analyze, language, source):
    a = analyze(language, source)
    assert a.structure_status == "complete"
    assert a.branch_count == 2
    assert a.max_nesting == 2
    assert len(a.routines) == 1
    assert top_level_lines(a) == 1
    assert routine_lengths(a)[0] > 0


def test_docstrings_and_data_literals(analyze):
    a = analyze(
        "python",
        '"""doc\ntext"""\nx = """data\nvalues"""\nif True:\n    "not a docstring"\n',
    )
    assert a.code_lines == {3, 4, 5, 6}
    assert any(t.value == '"not a docstring"' for t in a.tokens)


@pytest.mark.parametrize(
    "language,source",
    [
        ("python", 'x = "unclosed'),
        ("r", "f <- function( {"),
        ("stata", 'display "unclosed'),
        ("stata", "/* unclosed"),
    ],
)
def test_failures_are_not_zero(analyze, language, source):
    a = analyze(language, source)
    assert a.token_status == "failed"
    rows, _ = assess_language([a], language, {"a": "included"}, set(), "primary")
    m = {r["metric"]: r for r in rows}
    assert m["clone_exact_union_50"]["value"] is None
    assert m["clone_exact_union_50"]["status"] == "missing"
    assert m["file_count"]["value"] == 1


def test_python_structure_failure_keeps_tokens(analyze):
    a = analyze("python", "if x\n    y = 1\n")
    assert a.token_status == "complete"
    assert a.structure_status == "failed"


def test_stata_continuations_delimiters_positions(analyze):
    a = analyze(
        "stata", "#delimit ;\ngen x =\n 1;\n#delimit cr\nreplace x = /// comment\n 2\n"
    )
    b = analyze("stata", "gen x = 1\nreplace x = 2\n")
    assert [t.value for t in a.tokens] == [t.value for t in b.tokens]
    assert next(t for t in a.tokens if t.value == "1").line == 3
    assert next(t for t in a.tokens if t.value == "2").line == 6


def test_stata_strings_macros_and_braces(analyze):
    a = analyze(
        "stata",
        'local path `"C:/x/"\'\nuse "${root}/a.dta", clear\n'
        "foreach x in a b {\n gen y = `x'\n}\n",
    )
    assert a.token_status == a.structure_status == "complete"
    assert a.max_nesting == 1
    assert any(t.value == "`x'" and t.kind == "macro" for t in a.tokens)
    assert sum(t.value == "{" for t in a.tokens) == 1


def fake(values, uid="a", file_uid=None):
    a = Analysis(Unit(uid, file_uid or uid, "python", ""))
    a.tokens = [
        Token(str(v), "id", i + 1, 1, i + 1, "identifier") for i, v in enumerate(values)
    ]
    return a


def test_clone_overlap_and_nonoverlap():
    assert sum(coverage([fake([1] * 7)], 4)["union"][0]) == 0
    assert sum(coverage([fake([1] * 8)], 4)["union"][0]) == 8
    masks = coverage([fake([1, 2, 3, 4, 5]), fake([1, 2, 3, 4, 5], "b")], 4)
    assert sum(map(sum, masks["between"])) == 10
    assert sum(map(sum, masks["within"])) == 0


def test_clone_cells_same_file_and_boundary():
    a, b = fake([1, 2, 3], "a", "f"), fake([1, 2, 3], "b", "f")
    assert sum(map(sum, coverage([a, b], 4)["union"])) == 0
    assert sum(map(sum, coverage([a, b], 3)["within"])) == 6
    assert sum(map(sum, coverage([a, b], 3)["between"])) == 0


def test_clone_collision_verification(monkeypatch):
    from not_to_code.duplicates import windows

    class Colliding(bytes):
        def __hash__(self):
            return 0

    monkeypatch.setattr(
        "not_to_code.duplicates.windows",
        lambda values, size: [(i, Colliding(k)) for i, k in windows(values, size)],
    )
    assert sum(map(sum, coverage([fake([1, 2]), fake([3, 4], "b")], 2)["union"])) == 0


def test_rename_is_supplementary_and_short_code_in_denominator(analyze):
    a = analyze("python", "\n".join(f"x{i} = {i}" for i in range(20)), "a")
    b = analyze("python", "\n".join(f"y{i} = {i+100}" for i in range(20)), "b")
    short = analyze("python", "q=1\n", "c")
    metrics, _ = measure_duplicates([a, b, short])
    assert metrics["clone_exact_union_50"][0] == 0
    assert metrics["clone_normalized_increment_50"][0] == len(a.tokens) + len(b.tokens)
    assert metrics["clone_exact_union_50"][1] == sum(
        len(x.tokens) for x in (a, b, short)
    )
    metrics, _ = measure_duplicates([a, analyze("python", a.unit.source, "d")])
    assert metrics["clone_exact_union_50"][0] == metrics["clone_exact_union_50"][1]


@pytest.mark.parametrize(
    "language,source",
    [
        (
            "python",
            'open("/tmp/a.csv")\nos.chdir(r"C:\\data")\nurl = "https://example.com"\n',
        ),
        (
            "r",
            'read.csv("/tmp/a.csv")\nsetwd("C:/data")\nurl <- "https://example.com"\n',
        ),
        (
            "stata",
            'use "/tmp/a.dta", clear\ncd "C:/data"\nlocal url "https://example.com"\n',
        ),
    ],
)
def test_portability(analyze, language, source):
    a = analyze(language, source)
    rules = [f["rule"] for f in a.findings]
    assert rules.count("absolute_path") == 2
    assert rules.count("working_directory_change") == 1
    assert "path_like_literal" not in rules


def test_zero_no_routines_and_partial(analyze):
    a = analyze("python", "x=1\n")
    b = analyze("python", 'x="oops', "b")
    rows, _ = assess_language([a], "python", {"a": "included"}, set(), "primary")
    m = {r["metric"]: r for r in rows}
    assert m["median_routine_lines"]["status"] == "inapplicable"
    assert m["line_over_100"]["value"] == 0
    rows, _ = assess_language(
        [a, b], "python", {"a": "included", "b": "uncertain"}, set(), "primary"
    )
    assert next(r for r in rows if r["metric"] == "code_lines")["status"] == "partial"
    rows, _ = assess_language(
        [a, b],
        "python",
        {"a": "included", "b": "uncertain"},
        set(),
        "exclude_uncertain",
    )
    assert next(r for r in rows if r["metric"] == "code_lines")["status"] == "complete"


def test_containers(adapter):
    row = dict(file_uid="a", language="rmarkdown")
    units = adapter.units(
        row, "Prose\n```{r first}\nx <- 1\n```\n\n```{python}\nx=1\n```\n"
    )
    assert [u.language for u in units] == ["r", "python"]
    assert units[0].first_line == 3
    assert not any(u.incomplete for u in units)
    assert adapter.units(row, "```{r}\nx <- 1\n")[0].incomplete
    payload = {
        "metadata": {"kernelspec": {"language": "python", "name": "python3"}},
        "cells": [
            {"cell_type": "markdown", "source": ["prose"]},
            {"cell_type": "code", "source": ["x=1\n"]},
            {"cell_type": "code", "source": ["%%R\nx<-1\n"]},
        ],
    }
    units = adapter.units(dict(row, language="notebook"), json.dumps(payload))
    assert [u.language for u in units] == ["python", "r"]
    assert [u.cell_index for u in units] == [1, 2]


@pytest.mark.parametrize(
    "path,vendored,status",
    [
        ("code/a.py", False, "included"),
        ("vendor/a.py", True, "uncertain"),
        ("old/a.do", False, "uncertain"),
        (".ipynb_checkpoints/a.ipynb", False, "excluded"),
        ("renv/library/foo/a.R", True, "excluded"),
        ("x/site-packages/foo/a.py", True, "excluded"),
    ],
)
def test_eligibility(path, vendored, status):
    assert eligibility(dict(relative_path=path, is_vendored=vendored))[0] == status
