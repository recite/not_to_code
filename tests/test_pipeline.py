import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from not_to_code.pipeline import environment_index, process_deposit, read_source
from not_to_code.report import report, summarize


def row(path, language="python", uid="a"):
    return dict(
        file_uid=uid,
        dataset_version_uid="v1",
        dataset_doi="doi:1",
        collection_id="journal",
        relative_path=path.name,
        local_path=str(path),
        language=language,
        sha256_local=hashlib.sha256(path.read_bytes()).hexdigest(),
        encoding="utf-8",
        encoding_confidence=1.0,
        is_vendored=False,
    )


def test_source_integrity_and_decoding(tmp_path):
    path = tmp_path / "a.py"
    path.write_text("x=1\n")
    entry = row(path)
    assert read_source(entry)[1] == "complete"
    path.write_text("x=2\n")
    assert read_source(entry)[1] == "hash_mismatch"
    path.unlink()
    assert read_source(entry)[1] == "unavailable"
    path.write_bytes(b"x='\xff'")
    assert read_source(row(path))[1] == "decode_failed"


def test_unresolved_container_blocks_complete_claim(tmp_path, adapter):
    path = tmp_path / "a.py"
    path.write_text("x=1\n")
    notebook = tmp_path / "a.ipynb"
    notebook.write_text("malformed JSON")
    result = process_deposit([row(path), row(notebook, "notebook", "b")], adapter, {})
    metric = next(
        r
        for r in result["metrics"]
        if r["metric"] == "code_lines" and r["variant"] == "primary"
    )
    assert metric["status"] == "partial"
    assert metric["eligible_units"] == 2
    assert metric["measured_units"] == 1
    assert result["ledger"][1]["read_status"] == "container_failed"


def test_equal_deposit_summary_excludes_partial():
    entries = [
        dict(
            language="r",
            variant="primary",
            metric="code_lines",
            status="complete",
            value=n,
        )
        for n in [1, 3, 100]
    ]
    entries.append(dict(entries[0], status="partial", value=999))
    result = summarize(entries)
    assert result[0]["median"] == 3
    assert result[0]["n"] == 3
    assert result[0]["deposits"] == 4
    assert result[1]["median"] == 999


def test_cli_resume_and_changed_inputs(tmp_path, adapter):
    root = tmp_path / "softverse"
    upstream = Path(adapter.stata.__file__).parents[2]
    shutil.copytree(
        upstream / "softverse",
        root / "softverse",
        ignore=shutil.ignore_patterns("__pycache__"),
    )
    tally = root / "build/tally"
    tally.mkdir(parents=True)
    frame = root / "data/frame"
    frame.mkdir(parents=True)
    (frame / "frame.csv").write_text("collection_id\njournal\n")
    path = tmp_path / "a.py"
    path.write_text("\n".join(f"x{i} = {i}" for i in range(20)))
    copy = tmp_path / "b.py"
    copy.write_text(path.read_text())
    pq.write_table(
        pa.Table.from_pylist([row(path), row(copy, uid="b")]), tally / "files.parquet"
    )
    pq.write_table(
        pa.Table.from_pylist(
            [
                dict(
                    dataset_doi="doi:1",
                    source_file_uid="a",
                    manifest_kind="requirements",
                    package="numpy",
                    version_constraint=">=1",
                    ecosystem="pypi",
                    dependency_role="direct",
                )
            ]
        ),
        tally / "declared_dependencies.parquet",
    )
    pq.write_table(
        pa.Table.from_pylist(
            [
                dict(
                    dataset_doi="doi:1",
                    source_file_uid="a",
                    manifest_kind="notebook",
                    signal="python_version",
                    value="3.11",
                )
            ]
        ),
        tally / "environment_signals.parquet",
    )
    output = tmp_path / "assessment"
    command = [
        sys.executable,
        "-c",
        "from not_to_code.cli import main; main()",
        "assess",
        "--softverse-root",
        str(root),
        "--output",
        str(output),
    ]
    first = subprocess.run(command, text=True, capture_output=True)
    assert first.returncode == 0, first.stderr
    manifest = json.loads((output / "manifest.json").read_text())
    metrics = pq.read_table(output / "metrics.parquet").to_pylist()
    exact = next(r for r in metrics if r["metric"] == "clone_exact_union_50")
    assert exact["value"] == 1
    assert manifest["output_rows"]["ledger"] == 2
    second = subprocess.run(command, text=True, capture_output=True)
    assert second.returncode == 0, second.stderr
    assert (
        json.loads((output / "manifest.json").read_text())["output_hashes"]
        == manifest["output_hashes"]
    )
    assert (output / "report.html").exists()
    altered = json.loads(json.dumps(manifest))
    altered["instrument_hashes"]["metrics.json"] = "0" * 64
    (output / "manifest.json").write_text(json.dumps(altered))
    with pytest.raises(ValueError, match="dictionary differs"):
        report(output)
    (output / "manifest.json").write_text(json.dumps(manifest))
    parallel = subprocess.run(
        command + ["--workers", "2"], text=True, capture_output=True
    )
    assert parallel.returncode == 0, parallel.stderr
    assert (
        json.loads((output / "manifest.json").read_text())["output_hashes"]
        == manifest["output_hashes"]
    )
    path.write_text("changed source")
    third = subprocess.run(command, text=True, capture_output=True)
    assert third.returncode != 0
    assert "Cached source changed" in third.stderr
    (frame / "frame.csv").write_text("collection_id\njournal\nother\n")
    fourth = subprocess.run(command, text=True, capture_output=True)
    assert fourth.returncode != 0
    assert "Run inputs or instrument changed" in fourth.stderr


@pytest.mark.parametrize("source", ['"a" "b"\nx=1\n', '("a"\n "b")\nx=1\n'])
def test_full_docstring_span(analyze, source):
    a = analyze("python", source)
    assert all(t.value not in {'"a"', '"b"', "(", ")"} for t in a.tokens)
    assert len(a.code_lines) == 1


@pytest.mark.parametrize(
    "language,source", [("python", 'open(x, "/tmp/a")'), ("r", 'read.csv(x, "/tmp/a")')]
)
def test_nonpath_arguments(analyze, language, source):
    a = analyze(language, source)
    assert [f["rule"] for f in a.findings] == ["path_like_literal"]


@pytest.mark.parametrize(
    "language,call,prefix",
    [
        ("python", 'open("/tmp/a")', "x = 1\n"),
        ("python", 'pathlib.Path("/tmp/a")', "x = 1\n"),
        ("python", 'open(\n    "/tmp/a"\n)', "x = 1\n"),
        ("python", '1 + open("/tmp/a")', "x = 1\n"),
        ("r", 'read.csv("/tmp/a")', "x <- 1\n"),
        ("r", 'utils::read.csv("/tmp/a")', "x <- 1\n"),
        ("r", 'read.csv(\n    "/tmp/a"\n)', "x <- 1; "),
    ],
)
def test_path_call_recognition_ignores_unrelated_statements(
    analyze, language, call, prefix
):
    for source in (call, prefix + call):
        a = analyze(language, source)
        assert [f["rule"] for f in a.findings] == ["absolute_path"]


@pytest.mark.parametrize(
    "language,source",
    [
        ("python", 'x = "open"\n("/tmp/a")'),
        ("python", 'open\n("/tmp/a")'),
        ("r", '"read.csv"\n("/tmp/a")'),
        ("r", 'read.csv\n("/tmp/a")'),
        ("python", 'open(("/tmp/a"))'),
    ],
)
def test_path_call_recognition_keeps_token_boundaries(analyze, language, source):
    a = analyze(language, source)
    assert [f["rule"] for f in a.findings] == ["path_like_literal"]


@pytest.mark.parametrize("prefix", ["", "async "])
def test_directory_change_requires_call_not_definition(analyze, prefix):
    a = analyze("python", prefix + "def chdir(path):\n    return path\n")
    assert not a.findings
    a = analyze("python", prefix + 'def chdir(path):\n    os.chdir("/tmp/a")\n')
    assert [f["rule"] for f in a.findings] == [
        "working_directory_change",
        "absolute_path",
    ]


def test_else_nesting(analyze):
    a = analyze("stata", "if x {\n display 1\n}\nelse {\n if y {\n display 2\n }\n}\n")
    assert a.max_nesting == 2


def test_notebook_string_is_not_magic(adapter):
    payload = {
        "metadata": {"kernelspec": {"language": "python", "name": "python3"}},
        "cells": [{"cell_type": "code", "source": 'x = """\n%example\n"""\n'}],
    }
    units = adapter.units(dict(file_uid="a", language="notebook"), json.dumps(payload))
    assert not units[0].incomplete


def test_r_regex_is_not_unc_path(analyze):
    a = analyze("r", 'pattern <- "\\\\s*\\\\\\\\begin\\\\{document\\\\}"\n')
    assert not a.findings


def test_embedded_stata_is_withheld(analyze):
    a = analyze("stata", 'gen x=1\nmata x = st_matrix("x")\n')
    assert a.token_status == a.structure_status == "partial"
    assert not a.tokens


def test_stata_unclosed_string_position(analyze):
    a = analyze("stata", 'display "oops\nuse "file"\n')
    assert a.token_status == "failed"
    assert "1:9" in a.detail


def test_inline_expression_does_not_hide_unclosed_chunk(adapter):
    units = adapter.units(
        dict(file_uid="a", language="rmarkdown"),
        "Text `r 1+1`\n```{r}\nx <- 1\n",
    )
    assert units[0].incomplete
    assert not units[1].incomplete


def test_orphan_environment_evidence_is_rejected(tmp_path, monkeypatch):
    table = pa.Table.from_pylist(
        [dict(source_file_uid="unrecovered", dataset_doi="doi:1")]
    )
    monkeypatch.setattr("not_to_code.pipeline.pq.read_table", lambda path: table)
    with pytest.raises(ValueError, match="does not join"):
        environment_index(tmp_path, {})


def test_multiple_inline_expressions_preserve_positions(adapter):
    units = adapter.units(
        dict(file_uid="a", language="rmarkdown"), "Text `r 1` then `r 2`."
    )
    assert [u.source for u in units] == ["1", "2"]
    assert [u.first_col for u in units] == [9, 20]


@pytest.mark.parametrize("magic", ["%%", "%%capture"])
def test_unrecognized_notebook_magic_is_unresolved(adapter, magic):
    payload = {
        "metadata": {"kernelspec": {"language": "python", "name": "python3"}},
        "cells": [{"cell_type": "code", "source": magic + "\nx=1\n"}],
    }
    units = adapter.units(dict(file_uid="a", language="notebook"), json.dumps(payload))
    assert units[0].language == "unknown"


def test_unified_pipeline_includes_container_only_r(tmp_path, adapter, monkeypatch):
    from not_to_code import pipeline

    monkeypatch.setattr(pipeline, "Softverse", lambda root: adapter)
    root = tmp_path / "softverse"
    upstream = Path(adapter.stata.__file__).parents[2]
    shutil.copytree(
        upstream / "softverse",
        root / "softverse",
        ignore=shutil.ignore_patterns("__pycache__"),
    )
    (root / "data/frame").mkdir(parents=True)
    (root / "data/frame/frame.csv").write_text(
        "collection_id,discipline\njournal,test\n"
    )
    tally = root / "build/tally"
    tally.mkdir(parents=True)
    source = tmp_path / "analysis.Rmd"
    source.write_text("Prose\n```{r}\nrnorm(1)\n```\n")
    pq.write_table(
        pa.Table.from_pylist([row(source, "rmarkdown")]), tally / "files.parquet"
    )
    for name in ("declared_dependencies", "environment_signals"):
        pq.write_table(
            pa.table({"source_file_uid": pa.array([], type=pa.string())}),
            tally / f"{name}.parquet",
        )
    monkeypatch.setattr(pipeline, "tool_contract", lambda tools: {"root": "unused"})
    calls = []

    def analyze_unit(unit, readable, contract, cache):
        assert readable
        calls.append(unit.source)
        return {
            "lintr": {"status": "processed", "findings": []},
            "flowR": {
                "status": "processed",
                "calls": [{"kind": "stochastic"}],
                "results": {
                    "linter": {"results": {"absolute-file-paths": {"results": []}}}
                },
            },
        }

    monkeypatch.setattr(pipeline, "analyze_unit", analyze_unit)
    output = tmp_path / "output"
    manifest = pipeline.assess(root, output, language="r", r_tools=tmp_path)
    assert manifest["deposits"] == 1
    assert len(calls) == 1
    metrics = pq.read_table(output / "metrics.parquet").to_pylist()
    seeds = [r for r in metrics if r["metric"] == "random_without_seed_call"]
    assert {r["variant"] for r in seeds} == {"primary", "exclude_uncertain"}
    assert all(r["status"] == "complete" and r["value"] == 1 for r in seeds)
    native = pq.read_table(output / "native.parquet").to_pylist()
    assert len(native) == 2 and all(r["first_line"] == 3 for r in native)
    assert (output / "dictionary.json").read_bytes() == Path(
        pipeline.__file__
    ).with_name("metrics.json").read_bytes()
    report(output)
    assert (output / "paired-sensitivity.csv").exists()


def test_unreadable_native_source_has_no_content_hash(tmp_path, adapter):
    source = tmp_path / "missing.R"
    source.write_text("rnorm(1)\n")
    entry = row(source, "r")
    source.unlink()
    result = process_deposit([entry], adapter, {})
    assert result["native"]
    assert all(r["source_sha256"] is None for r in result["native"])
