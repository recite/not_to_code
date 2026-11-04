import hashlib

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from not_to_code.model import Analysis, Unit
from not_to_code.native import assess_native
from not_to_code.registry import REGISTRY
from not_to_code.report import paired_sensitivity, summarize
from not_to_code.sources import restore_sources


def records(*calls, status="processed", findings=None):
    return {
        "flowR": {
            "status": status,
            "calls": list(calls),
            "results": {
                "linter": {"results": {"absolute-file-paths": {"results": []}}}
            },
        },
        "lintr": {"status": status, "findings": findings or []},
    }


def metric(rows, name):
    return next(r for r in rows if r["metric"] == name)


def test_native_eligibility_filters_seed_evidence(analyze):
    a = analyze("r", "rnorm(1)", "a")
    b = analyze("r", "set.seed(1)", "b")
    native = {
        "a": records({"kind": "stochastic"}),
        "b": records({"kind": "seed", "seed_value": "literal_number"}),
    }
    flags = {"a": "included", "b": "uncertain"}
    primary = assess_native([a, b], flags, native, "primary")
    sensitivity = assess_native([a, b], flags, native, "exclude_uncertain")
    assert metric(primary, "random_without_seed_call")["value"] == 0
    assert metric(sensitivity, "random_without_seed_call")["value"] == 1
    assert metric(sensitivity, "random_without_seed_call")["eligible_units"] == 1


@pytest.mark.parametrize(
    "seed,gap",
    [("null", 1), ("missing", 1), ("unresolved_expression", 0), ("literal_number", 0)],
)
def test_seed_presence_is_not_effectiveness(analyze, seed, gap):
    a = analyze("r", "rnorm(1)")
    native = {
        "a": records({"kind": "stochastic"}, {"kind": "seed", "seed_value": seed})
    }
    rows = assess_native([a], {"a": "included"}, native, "primary")
    assert metric(rows, "random_without_seed_call")["value"] == gap


def test_missing_unknown_and_unneeded_seed_measurements(analyze):
    a = analyze("r", "rnorm(1)")
    unknown = Analysis(Unit("b", "b", "unknown", ""))
    flags = {"a": "included", "b": "included"}
    native = {"a": records({"kind": "stochastic"}), "b": records(status="unsupported")}
    rows = assess_native([a, unknown], flags, native, "primary")
    seed = metric(rows, "random_without_seed_call")
    assert seed["status"] == "partial"
    assert seed["value"] is None
    assert seed["measured_units"] == 1
    rows = assess_native([a], flags, {"a": records()}, "primary")
    assert metric(rows, "random_without_seed_call")["status"] == "inapplicable"
    rows = assess_native([a], flags, {"a": records(status="not_measured")}, "primary")
    assert all(r["status"] == "not_measured" and r["value"] is None for r in rows)
    rows = assess_native([a], flags, {"a": records(status="timeout")}, "primary")
    assert all(r["status"] == "missing" and r["value"] is None for r in rows)


def test_lint_rate_uses_only_units_with_both_measurements(analyze):
    a = analyze("r", "x <- 1")
    b = analyze("r", "x <- 2", "b")
    b.token_status = "failed"
    native = {
        uid: records(findings=[{"linter": "indentation_linter"}]) for uid in ["a", "b"]
    }
    rows = assess_native([a, b], dict.fromkeys(native, "included"), native, "primary")
    result = metric(rows, "indentation_linter")
    assert result["status"] == "partial"
    assert result["value"] == 1000
    assert result["numerator"] == result["denominator"] == result["measured_units"] == 1


def test_summary_keeps_language_variant_and_inventory_populations_separate():
    rows = [
        dict(
            language=lang,
            variant=variant,
            metric="x",
            value=value,
            status=status,
            collection="A",
        )
        for lang, variant, value, status in [
            ("r", "primary", 0, "complete"),
            ("r", "primary", 10, "complete"),
            ("r", "primary", 1000, "partial"),
            ("r", "exclude_uncertain", 50, "complete"),
            ("python", "primary", 80, "complete"),
            ("r", "primary", 1, "inventory_only"),
        ]
    ]
    result = summarize(rows, "collection")
    r = next(
        r
        for r in result
        if r["language"] == "r"
        and r["variant"] == "primary"
        and r["population"] == "complete"
    )
    assert r["median"] == 5 and r["q25"] == 2.5 and r["q75"] == 7.5 and r["n"] == 2
    assert r["partial"] == 1 and r["inventory_only"] == 1 and r["zero"] == 1


def test_paired_sensitivity_does_not_compare_changing_populations():
    rows = [
        dict(
            dataset_version_uid=uid,
            language="r",
            metric="x",
            variant=variant,
            value=value,
            status="complete",
        )
        for uid, variant, value in [
            ("a", "primary", 0.6),
            ("a", "exclude_uncertain", 0.4),
            ("b", "primary", 1),
            ("c", "exclude_uncertain", 0),
        ]
    ]
    pair = paired_sensitivity(rows)[0]
    assert pair["paired_deposits"] == 1
    assert pair["primary_median"] == 0.6
    assert pair["exclude_uncertain_median"] == 0.4
    assert pair["median_change"] == pytest.approx(-0.2)


def test_registry_has_interpretations_and_no_retired_scores():
    assert (
        not {
            "absolute_path",
            "path_like_literal",
            "trailing_whitespace",
            "mixed_indentation",
        }
        & REGISTRY.keys()
    )
    assert REGISTRY["top_level_share"]["role"] == "context"
    assert REGISTRY["bundled_dependency"]["role"] == "context"
    assert REGISTRY["clone_normalized_increment_50"]["role"] == "sensitivity"
    assert "r" not in REGISTRY["line_over_100"]["languages"]
    for spec in REGISTRY.values():
        assert all(
            spec[k]
            for k in (
                "version",
                "attribute",
                "role",
                "definition",
                "rationale",
                "limit",
                "unit",
                "source",
            )
        )


def test_release_recovery_requires_exact_inventory_bytes(tmp_path):
    root, output = tmp_path / "upstream", tmp_path / "output"
    (root / "build/release/corpus/contents").mkdir(parents=True)
    output.mkdir()
    text = "x <- 1\n"
    sha = hashlib.sha256(text.encode()).hexdigest()
    changed = tmp_path / "changed.R"
    changed.write_text("x <- 2\n")
    groups = {
        "a": [
            {"sha256_local": sha, "local_path": "/nonexistent/a"},
            {"sha256_local": "0" * 64, "local_path": "/nonexistent/b"},
            {"sha256_local": sha, "local_path": str(changed)},
        ]
    }
    pq.write_table(
        pa.Table.from_pylist(
            [
                {
                    "sha256": sha,
                    "content": text,
                    "exact": True,
                    "src_encoding": "utf-8",
                },
                {
                    "sha256": "0" * 64,
                    "content": text,
                    "exact": True,
                    "src_encoding": "utf-8",
                },
            ]
        ),
        root / "build/release/corpus/contents/a.parquet",
    )
    assert restore_sources(root, output, groups, ["a"]) == [sha]
    assert groups["a"][1]["local_path"] == "/nonexistent/b"
    assert groups["a"][2]["local_path"] == str(changed)
    assert changed.read_text() == "x <- 2\n"
    assert (output / "restored" / sha).read_text() == text


def test_failed_path_feature_does_not_discard_successful_call_analysis(analyze):
    a = analyze("r", "rnorm(1)")
    native = {"a": records({"kind": "stochastic"}, status="partial")}
    native["a"]["flowR"]["feature_status"] = {
        "paths": "analysis_failed",
        "calls": "processed",
    }
    rows = assess_native([a], {"a": "included"}, native, "primary")
    assert metric(rows, "absolute-file-paths")["status"] == "missing"
    assert metric(rows, "random_without_seed_call")["value"] == 1
    assert metric(rows, "random_without_seed_call")["status"] == "complete"
