"""One aggregation path for the versioned measurement profile and its reports."""

import csv
import json
from collections import Counter, defaultdict
from pathlib import Path
from statistics import median

import pyarrow as pa
import pyarrow.parquet as pq

from .pipeline import digest, write_json


def quantile(values, probability):
    if not values:
        return None
    values = sorted(values)
    pos = (len(values) - 1) * probability
    lo = int(pos)
    hi = min(lo + 1, len(values) - 1)
    return values[lo] + (values[hi] - values[lo]) * (pos - lo)


def summarize(rows, group_by=None):
    groups = defaultdict(list)
    for row in rows:
        group = str(row.get(group_by) or "Unknown") if group_by else "All"
        groups[(group, row["language"], row["variant"], row["metric"])].append(row)
    result = []
    for (group, language, variant, metric), entries in sorted(groups.items()):
        counts = Counter(r["status"] for r in entries)
        for population in ("complete", "partial", "inventory_only"):
            values = [
                r["value"]
                for r in entries
                if r["status"] == population and r["value"] is not None
            ]
            result.append(
                dict(
                    group_by=group_by or "all",
                    group=group,
                    language=language,
                    variant=variant,
                    metric=metric,
                    population=population,
                    deposits=len(entries),
                    n=len(values),
                    **{
                        k: counts[k]
                        for k in (
                            "complete",
                            "partial",
                            "missing",
                            "inapplicable",
                            "unsupported",
                            "not_measured",
                            "inventory_only",
                        )
                    },
                    q25=quantile(values, 0.25),
                    median=quantile(values, 0.5),
                    q75=quantile(values, 0.75),
                    minimum=min(values) if values else None,
                    maximum=max(values) if values else None,
                    zero=sum(v == 0 for v in values),
                    prevalence=(
                        sum(v > 0 for v in values) / len(values) if values else None
                    ),
                )
            )
    return result


def paired_sensitivity(rows):
    groups = defaultdict(dict)
    for row in rows:
        if row["status"] == "complete" and row["value"] is not None:
            key = (row["language"], row["metric"])
            groups[key].setdefault(row["dataset_version_uid"], {})[row["variant"]] = (
                row["value"]
            )
    result = []
    for (language, metric), deposits in sorted(groups.items()):
        paired = [
            v for v in deposits.values() if set(v) == {"primary", "exclude_uncertain"}
        ]
        result.append(
            dict(
                language=language,
                metric=metric,
                paired_deposits=len(paired),
                primary_median=median(v["primary"] for v in paired) if paired else None,
                exclude_uncertain_median=(
                    median(v["exclude_uncertain"] for v in paired) if paired else None
                ),
                median_change=(
                    median(v["exclude_uncertain"] - v["primary"] for v in paired)
                    if paired
                    else None
                ),
            )
        )
    return result


def write_csv(path, rows):
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]) if rows else [])
        writer.writeheader()
        writer.writerows(rows)


def report(output, readme=None):
    manifest = json.loads((output / "manifest.json").read_text())
    if not manifest.get("completed"):
        raise ValueError("Assessment is incomplete")
    if (
        digest(output / "dictionary.json")
        != manifest["instrument_hashes"]["metrics.json"]
    ):
        raise ValueError("Metric dictionary differs from assessment instrument")
    for filename, expected in manifest["output_hashes"].items():
        if digest(output / filename) != expected:
            raise ValueError(f"Output hash mismatch: {filename}")
    for name, count in manifest["output_rows"].items():
        if pq.read_metadata(output / f"{name}.parquet").num_rows != count:
            raise ValueError(f"Row count mismatch: {name}")
    registry = json.loads((output / "dictionary.json").read_text())
    metrics = pq.read_table(output / "metrics.parquet").to_pylist()
    keys = [
        (r["dataset_version_uid"], r["language"], r["variant"], r["metric"])
        for r in metrics
    ]
    if len(keys) != len(set(keys)):
        raise ValueError("Duplicate deposit metrics")
    for row in metrics:
        if row["metric"] not in registry:
            raise ValueError("Unknown metric")
        if row["measured_units"] > row["eligible_units"]:
            raise ValueError("Invalid coverage denominator")
        if (
            registry[row["metric"]]["unit"] in {"proportion", "binary"}
            and row["value"] is not None
            and not 0 <= row["value"] <= 1
        ):
            raise ValueError("Invalid bounded measurement")
    metadata = json.loads((output / "metadata.json").read_text())
    enriched = [dict(r, **metadata[r["dataset_version_uid"]]) for r in metrics]
    summary = summarize(enriched)
    write_csv(output / "summary.csv", summary)
    pq.write_table(
        pa.Table.from_pylist(summary), output / "summary.parquet", compression="zstd"
    )
    write_csv(output / "measurements.csv", enriched)
    for group in ("collection", "discipline", "deposit_year", "period"):
        write_csv(output / f"by-{group}.csv", summarize(enriched, group))
    sensitivity = paired_sensitivity(metrics)
    write_csv(output / "paired-sensitivity.csv", sensitivity)
    counts = Counter()
    for batch in pq.ParquetFile(output / "ledger.parquet").iter_batches(
        columns=["language", "eligibility", "read_status"]
    ):
        counts.update(
            (r["language"], r["eligibility"], r["read_status"])
            for r in batch.to_pylist()
        )
    write_json(
        output / "coverage.json",
        [
            dict(language=k[0], eligibility=k[1], read_status=k[2], files=n)
            for k, n in sorted(counts.items())
        ],
    )
    from .quality_report import render

    render(output, enriched, summary, sensitivity, registry, manifest)
    selected = [
        r
        for r in summary
        if r["variant"] == "primary"
        and r["population"] == "complete"
        and r["metric"] in {"clone_exact_union_50", "largest_file_share", "max_nesting"}
    ]
    markdown = (
        f"Run `{manifest['fingerprint'][:12]}`; {manifest['deposits']:,} deposits"
    )
    markdown += (
        " (selected subset)"
        if manifest["deposit_limit"] is not None or manifest["deposit_list_hash"]
        else ""
    )
    markdown += (
        ". Equal-deposit medians among complete measurements.\n\n| "
        "Language | Property | Median | Complete / eligible deposits |\n"
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
    write_json(
        output / "report-manifest.json",
        {
            "assessment_fingerprint": manifest["fingerprint"],
            "renderer_hashes": {
                p.name: digest(p)
                for p in (Path(__file__), Path(__file__).with_name("quality_report.py"))
            },
            "outputs": {
                p.name: digest(p)
                for p in output.iterdir()
                if p.suffix in {".html", ".csv", ".svg", ".pdf", ".md"}
            },
        },
    )
    return summary
