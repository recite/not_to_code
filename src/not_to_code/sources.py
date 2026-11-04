"""Verified source recovery and descriptive deposit/environment metadata."""

import csv
import hashlib
from pathlib import Path

import pyarrow.parquet as pq


def restore_sources(root, output, groups, keys):
    needed = {
        r["sha256_local"]
        for k in keys
        for r in groups[k]
        if r.get("sha256_local")
        and not Path(r.get("local_path") or "/nonexistent").exists()
    }
    directory = output / "restored"
    directory.mkdir(exist_ok=True)
    recovered = {}
    for sha in sorted(needed):
        path = directory / sha
        if path.exists() and hashlib.sha256(path.read_bytes()).hexdigest() == sha:
            recovered[sha] = str(path)
    pending = needed - recovered.keys()
    for shard in sorted((root / "build/release/corpus/contents").glob("*.parquet")):
        if not pending:
            break
        for batch in pq.ParquetFile(shard).iter_batches(batch_size=1000):
            for content in batch.to_pylist():
                sha = content["sha256"]
                if sha not in pending or not content.get("exact"):
                    continue
                try:
                    raw = content["content"].encode(content["src_encoding"] or "utf-8")
                except (UnicodeError, LookupError):
                    continue
                if hashlib.sha256(raw).hexdigest() == sha:
                    path = directory / sha
                    path.write_bytes(raw)
                    recovered[sha] = str(path)
                    pending.remove(sha)
    for key in keys:
        for row in groups[key]:
            if (
                row.get("sha256_local") in recovered
                and not Path(row.get("local_path") or "/nonexistent").exists()
            ):
                row["local_path"] = recovered[row["sha256_local"]]
    return sorted(recovered)


ARTIFACTS = {
    "renv.lock": "R lockfile",
    "packrat.lock": "R lockfile",
    "description": "R package metadata",
    "uv.lock": "Python lockfile",
    "poetry.lock": "Python lockfile",
    "pipfile.lock": "Python lockfile",
    "pyproject.toml": "Python project metadata",
    "environment.yml": "Conda environment",
    "environment.yaml": "Conda environment",
    "dockerfile": "Container recipe",
}


def metadata(root, baseline):
    frame = {
        r["collection_id"]: r
        for r in csv.DictReader((root / "data/frame/frame.csv").open())
    }
    deposits = {}
    path = root / "build/release/corpus/deposits.parquet"
    for row in (pq.read_table(path).to_pylist() if path.exists() else []):
        doi = row["dataset_doi"]
        if doi in deposits:
            raise ValueError(f"Ambiguous deposit metadata: {doi}")
        deposits[doi] = row
    result = {}
    for row in baseline:
        key = row["dataset_version_uid"]
        if key in result:
            continue
        collection = frame.get(row["collection_id"], {})
        deposit = deposits.get(row["dataset_doi"], {})
        year = deposit.get("deposit_year")
        result[key] = {
            "dataset_doi": row["dataset_doi"],
            "collection": row["collection_id"],
            "discipline": collection.get("discipline") or "Unknown",
            "deposit_year": year,
            "period": f"{year // 5 * 5}–{year // 5 * 5 + 4}" if year else "Unknown",
            "collection_state": deposit.get("collection_state", "unknown"),
        }
    return result


def environment_evidence(root, selected_rows):
    selected = {r["dataset_version_uid"] for r in selected_rows}
    files = {
        r["file_uid"]: r
        for r in pq.read_table(root / "build/tally/files.parquet").to_pylist()
        if r["dataset_version_uid"] in selected
    }
    rows = []
    for name in ("declared_dependencies", "environment_signals"):
        for record in pq.read_table(root / f"build/tally/{name}.parquet").to_pylist():
            source = files.get(record["source_file_uid"])
            if source is None:
                continue
            if record["dataset_doi"] != source["dataset_doi"]:
                raise ValueError("Environment evidence has a mismatched source deposit")
            rows.append(
                dict(
                    record,
                    dataset_version_uid=source["dataset_version_uid"],
                    evidence_type=name,
                    is_vendored=source["is_vendored"],
                )
            )
    for uid, source in files.items():
        name = (source.get("filename") or Path(source["relative_path"]).name).lower()
        kind = ARTIFACTS.get(name)
        if name.startswith("requirements") and name.endswith(".txt"):
            kind = "Python requirements"
        if kind and not source["is_vendored"]:
            rows.append(
                dict(
                    dataset_version_uid=source["dataset_version_uid"],
                    source_file_uid=uid,
                    evidence_type="inventory_filename",
                    artifact=kind,
                    filename=source["relative_path"],
                    interpretation="Filename observed; contents and use not validated",
                )
            )
    return rows
