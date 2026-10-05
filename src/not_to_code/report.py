"""Equal-deposit descriptive summaries and a standalone, escaped HTML report."""

import csv
import html
import json
from collections import Counter, defaultdict
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from .assessment import REGISTRY
from .pipeline import digest, write_json


def quantile(values, probability):
    if not values:
        return None
    values = sorted(values)
    pos = (len(values) - 1) * probability
    lo = int(pos)
    hi = min(lo + 1, len(values) - 1)
    return values[lo] + (values[hi] - values[lo]) * (pos - lo)


def summarize(rows):
    groups = defaultdict(list)
    for row in rows:
        groups[(row["language"], row["variant"], row["metric"])].append(row)
    result = []
    for (language, variant, metric), entries in sorted(groups.items()):
        counts = Counter(r["status"] for r in entries)
        for population in ("complete", "partial"):
            values = [
                r["value"]
                for r in entries
                if r["status"] == population and r["value"] is not None
            ]
            result.append(
                dict(
                    language=language,
                    variant=variant,
                    metric=metric,
                    population=population,
                    deposits=len(entries),
                    n=len(values),
                    complete=counts["complete"],
                    partial=counts["partial"],
                    missing=counts["missing"],
                    inapplicable=counts["inapplicable"],
                    unsupported=counts["unsupported"],
                    q25=quantile(values, 0.25),
                    median=quantile(values, 0.5),
                    q75=quantile(values, 0.75),
                    prevalence=(
                        sum(v > 0 for v in values) / len(values) if values else None
                    ),
                )
            )
    return result


def table(rows, fields):
    def fmt(value):
        if value is None:
            return "—"
        if isinstance(value, float):
            return f"{value:.4g}"
        return html.escape(str(value))

    return (
        "<table><thead><tr>"
        + "".join(f"<th>{html.escape(f)}</th>" for f in fields)
        + "</tr></thead><tbody>"
        + "".join(
            "<tr>" + "".join(f"<td>{fmt(r.get(f))}</td>" for f in fields) + "</tr>"
            for r in rows
        )
        + "</tbody></table>"
    )


def report(output, readme=None):
    manifest = json.loads((output / "manifest.json").read_text())
    if not manifest.get("completed"):
        raise ValueError("Assessment is incomplete")
    if (
        digest(Path(__file__).with_name("metrics.json"))
        != manifest["instrument_hashes"]["metrics.json"]
    ):
        raise ValueError("Metric dictionary differs from assessment instrument")
    for filename, expected in manifest["output_hashes"].items():
        if digest(output / filename) != expected:
            raise ValueError(f"Output hash mismatch: {filename}")
    for name, count in manifest["output_rows"].items():
        if pq.read_metadata(output / f"{name}.parquet").num_rows != count:
            raise ValueError(f"Row count mismatch: {name}")
    metrics = pq.read_table(output / "metrics.parquet").to_pylist()
    keys = [
        (r["dataset_version_uid"], r["language"], r["variant"], r["metric"])
        for r in metrics
    ]
    if len(keys) != len(set(keys)):
        raise ValueError("Duplicate deposit metrics")
    for row in metrics:
        if row["measured_units"] > row["eligible_units"]:
            raise ValueError("Invalid coverage denominator")
        if (
            row["metric"].startswith("clone_")
            and row["value"] is not None
            and not 0 <= row["value"] <= 1
        ):
            raise ValueError("Invalid clone coverage")
    summary = summarize(metrics)
    schema = pa.schema(
        [
            (
                k,
                (
                    pa.string()
                    if k in {"language", "variant", "metric", "population"}
                    else (
                        pa.float64()
                        if k in {"q25", "median", "q75", "prevalence"}
                        else pa.int64()
                    )
                ),
            )
            for k in (
                "language",
                "variant",
                "metric",
                "population",
                "deposits",
                "n",
                "complete",
                "partial",
                "missing",
                "inapplicable",
                "unsupported",
                "q25",
                "median",
                "q75",
                "prevalence",
            )
        ]
    )
    pq.write_table(
        pa.Table.from_pylist(summary, schema=schema),
        output / "summary.parquet",
        compression="zstd",
    )
    with (output / "summary.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=schema.names)
        writer.writeheader()
        writer.writerows(summary)
    coverage = Counter()
    for batch in pq.ParquetFile(output / "ledger.parquet").iter_batches(
        columns=["language", "eligibility", "read_status"]
    ):
        coverage.update(
            (r["language"], r["eligibility"], r["read_status"])
            for r in batch.to_pylist()
        )
    ledger = [
        dict(language=k[0], eligibility=k[1], read_status=k[2], files=n)
        for k, n in sorted(coverage.items())
    ]
    write_json(output / "coverage.json", ledger)
    unit_counts = Counter()
    for batch in pq.ParquetFile(output / "units.parquet").iter_batches(
        columns=["language", "token_status", "structure_status"]
    ):
        unit_counts.update(
            (r["language"], r["token_status"], r["structure_status"])
            for r in batch.to_pylist()
        )
    unit_coverage = [
        dict(language=k[0], token_status=k[1], structure_status=k[2], units=n)
        for k, n in sorted(unit_counts.items())
    ]
    write_json(output / "unit_coverage.json", unit_coverage)
    disclaimer = (
        "Observable engineering properties of candidate research code. "
        "No composite score or scientific-correctness claim. Medians weight "
        "deposits equally within language; partial measurements are shown "
        "separately. Environment zeros mean no recorded evidence. Clone "
        "occurrences are unions of covered spans, not inferred "
        "refactoring opportunities."
    )
    body = [
        "<!doctype html><meta charset='utf-8'><title>Research code profile</title>"
        "<style>body{font:16px system-ui;margin:3rem;max-width:1500px;"
        "color:#17232d}table{border-collapse:collapse;font-size:13px;"
        "margin-bottom:2rem}th,td{text-align:left;padding:.45rem;"
        "border-bottom:1px solid #ddd}th{background:#eff3f6;position:sticky;"
        "top:0}code{overflow-wrap:anywhere}</style>",
        "<h1>Research code engineering profile</h1>",
        f"<p>{disclaimer}</p>",
        f"<p>Assessed {manifest['deposits']:,} deposits. "
        f"Run <code>{manifest['fingerprint']}</code>.</p>",
    ]
    if manifest["deposit_limit"] is not None:
        body.append(
            "<p><strong>Pilot subset: these are not full-frame estimates.</strong></p>"
        )
    for language in ("r", "python", "stata"):
        body.append(f"<h2>{language}</h2>")
        body.append(
            table(
                [r for r in summary if r["language"] == language],
                [
                    "variant",
                    "metric",
                    "population",
                    "n",
                    "deposits",
                    "median",
                    "q25",
                    "q75",
                    "prevalence",
                    "missing",
                    "inapplicable",
                    "unsupported",
                ],
            )
        )
    body.append(
        "<h2>Recovery and eligibility</h2>"
        + table(ledger, ["language", "eligibility", "read_status", "files"])
    )
    body.append(
        "<h2>Instrument coverage</h2>"
        + table(
            unit_coverage, ["language", "token_status", "structure_status", "units"]
        )
    )
    body.append(
        "<h2>Metric dictionary</h2>"
        + table(
            [dict(metric=k, **v) for k, v in REGISTRY.items()],
            ["metric", "dimension", "definition", "denominator", "scale", "coverage"],
        )
    )
    (output / "report.html").write_text("\n".join(body))
    selected = [
        r
        for r in summary
        if r["variant"] == "primary"
        and r["population"] == "complete"
        and r["metric"] in {"clone_exact_union_50", "largest_file_share", "max_nesting"}
    ]
    markdown = (
        f"Run `{manifest['fingerprint'][:12]}`; {manifest['deposits']:,} deposits"
        + (" (pilot subset)" if manifest["deposit_limit"] is not None else "")
        + ". Equal-deposit medians among complete measurements.\n\n"
        "| Language | Property | Median | Complete / eligible deposits |\n"
        "|---|---|---:|---:|\n"
    )
    for row in selected:
        value = f"{row['median']:.4g}" if row["median"] is not None else "N/A"
        markdown += (
            f"| {row['language']} | {row['metric']} | {value} | "
            f"{row['n']} / {row['deposits']} |\n"
        )
    (output / "results.md").write_text(markdown)
    if readme:
        start, end = "<!-- results:start -->", "<!-- results:end -->"
        text = readme.read_text()
        if text.count(start) != 1 or text.count(end) != 1:
            raise ValueError("README needs one results marker pair")
        before, rest = text.split(start)
        _, after = rest.split(end)
        readme.write_text(before + start + "\n\n" + markdown + "\n" + end + after)
    return summary
