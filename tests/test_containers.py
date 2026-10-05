import json
import token

import pytest

from not_to_code.duplicates import measure_duplicates
from not_to_code.lexical import tokenize_unit
from not_to_code.model import Analysis


@pytest.mark.parametrize("language", ["javascript", "rust", "unknown"])
def test_notebook_kernel_does_not_default_to_python(adapter, language):
    metadata = {} if language == "unknown" else {"language_info": {"name": language}}
    payload = {
        "metadata": metadata,
        "cells": [{"cell_type": "code", "source": "foo(1)\n"}],
    }
    units = adapter.units(dict(file_uid="a", language="notebook"), json.dumps(payload))
    assert units[0].language == language
    a = Analysis(units[0])
    tokenize_unit(a, adapter)
    assert a.token_status == "unsupported"


def test_unsupported_literate_engine_remains_in_coverage(adapter):
    units = adapter.units(
        dict(file_uid="a", language="rmarkdown"),
        "```{r}\nx <- 1\n```\n```{rust}\nfn main() {}\n```\n",
    )
    assert [u.language for u in units] == ["r", "rust"]
    assert units[1].first_line == 5
    a = Analysis(units[1])
    tokenize_unit(a, adapter)
    assert a.token_status == "unsupported"


@pytest.mark.parametrize(
    "prefix", ["f"] + (["t"] if hasattr(token, "TSTRING_MIDDLE") else [])
)
def test_interpolated_literal_changes_are_normalized(analyze, prefix):
    analyses = [
        analyze(
            "python",
            "".join(f'x{i} = {prefix}"{literal} {{person}}"\n' for i in range(20)),
            uid=uid,
        )
        for uid, literal in [("a", "hello"), ("b", "goodbye")]
    ]
    metrics, _ = measure_duplicates(analyses)
    numerator, denominator = metrics["clone_normalized_increment_50"]
    assert numerator == denominator > 0


def test_fstring_literal_whitespace_is_not_presentation_whitespace(analyze):
    a = analyze("python", 'x = f" "\n')
    b = analyze("python", 'x = f""\n')
    assert [t.value for t in a.tokens] != [t.value for t in b.tokens]


def test_notebook_fstring_content_is_not_magic(adapter):
    payload = {
        "metadata": {"kernelspec": {"language": "python"}},
        "cells": [{"cell_type": "code", "source": 'x = f"""\n%example\n"""\n'}],
    }
    units = adapter.units(dict(file_uid="a", language="notebook"), json.dumps(payload))
    assert not units[0].incomplete


def test_empty_unclosed_and_overridden_chunks_are_retained(adapter):
    units = adapter.units(
        dict(file_uid="a", language="rmarkdown"),
        "```{r}\n```\n```{r, engine='python'}\nx = 1\n```\n```{rust}\n",
    )
    assert [u.language for u in units] == ["r", "unknown", "rust"]
    assert not units[0].incomplete
    assert units[-1].incomplete


def test_literate_fences_match_opening_character_and_length(adapter):
    units = adapter.units(
        dict(file_uid="a", language="rmarkdown"),
        "````{rust}\n~~~\n```\n````\nText `r 1`\n",
    )
    assert units[0].source == "~~~\n```"
    assert not units[0].incomplete
    assert units[1].language == "r"
    assert units[1].source == "1"


def test_chunk_named_inline_does_not_extract_expressions_from_comments(adapter):
    units = adapter.units(
        dict(file_uid="a", language="rmarkdown"),
        "```{r inline}\n# example `r 1 + 1`\nx <- 1\n```\n",
    )
    assert len(units) == 1
    assert units[0].chunk_label == "inline"
