"""Pinned inputs, source verification, resumable per-deposit assessment."""

import csv
import gzip
import hashlib
import importlib.metadata
import json
import platform
import warnings
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
from functools import partial
from pathlib import Path

import pyarrow.parquet as pq

from .adapter import LANGUAGES, Softverse, eligibility
from .assessment import assess_language
from .findings import measure_findings
from .lexical import tokenize_unit
from .model import Analysis, Unit
from .storage import SCHEMAS, Tables
from .structure import measure_structure


def digest(path):
    with Path(path).open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def write_json(path, value):
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n")
    temporary.replace(path)


def read_source(row):
    path = Path(row.get("local_path") or "/nonexistent")
    try:
        raw = path.read_bytes()
    except OSError as exc:
        return None, "unavailable", None, None, str(exc)
    sha = hashlib.sha256(raw).hexdigest()
    if not row.get("sha256_local"):
        return None, "unverified", sha, None, "No inventoried source hash"
    if sha != row["sha256_local"]:
        return None, "hash_mismatch", sha, None, "Content differs from inventory"
    encodings = ["utf-8-sig"]
    if raw.startswith((b"\xff\xfe", b"\xfe\xff")):
        encodings.insert(0, "utf-16")
    if row.get("encoding") and (row.get("encoding_confidence") or 0) >= 0.7:
        encodings.append(row["encoding"])
    for encoding in encodings:
        try:
            return raw.decode(encoding), "complete", sha, encoding, ""
        except (UnicodeError, LookupError):
            continue
    return None, "decode_failed", sha, None, "No confident strict decoding"


def environment_index(root, file_dois):
    result = defaultdict(lambda: defaultdict(set))

    def verify(row):
        if file_dois.get(row["source_file_uid"]) != row["dataset_doi"]:
            raise ValueError("Environment evidence does not join to its source deposit")

    for row in pq.read_table(
        root / "build/tally/declared_dependencies.parquet"
    ).to_pylist():
        verify(row)
        language = {"cran": "r", "bioconductor": "r", "pypi": "python"}.get(
            row["ecosystem"]
        )
        if not language:
            continue
        flags = result[row["dataset_doi"]][language]
        role = row["dependency_role"]
        if role == "direct":
            flags.add("dependency_declaration")
        if row["version_constraint"] and role in {"direct", "locked"}:
            flags.add("version_constraint")
        if role == "locked":
            flags.add("locked_dependency")
        if role == "installed":
            flags.add("bundled_dependency")
    for row in pq.read_table(
        root / "build/tally/environment_signals.parquet"
    ).to_pylist():
        verify(row)
        language = {
            "r_version": "r",
            "python_version": "python",
            "stata_version": "stata",
        }.get(row["signal"])
        if language and row["value"]:
            result[row["dataset_doi"]][language].add("interpreter_version")
    return result


def instrument(root, limit):
    package = Path(__file__).parent
    specification = package / "measurement.md"
    if not specification.exists():
        specification = package.parents[1] / "measurement.md"
    inputs = [
        "build/tally/files.parquet",
        "build/tally/declared_dependencies.parquet",
        "build/tally/environment_signals.parquet",
        "data/frame/frame.csv",
    ]
    upstream = [
        "softverse/__init__.py",
        "softverse/stata/lexer.py",
        "softverse/detect/notebooks.py",
        "softverse/detect/dispatch.py",
    ]
    versions = {
        n: importlib.metadata.version(n)
        for n in [
            "not-to-code",
            "pyarrow",
            "tree-sitter",
            "tree-sitter-language-pack",
            "charset-normalizer",
        ]
    }
    versions["python"] = platform.python_version()
    contract = dict(
        schema_version=1,
        specification_hash=digest(specification),
        softverse_root=str(root),
        deposit_limit=limit,
        input_hashes={p: digest(root / p) for p in inputs},
        upstream_hashes={p: digest(root / p) for p in upstream},
        instrument_hashes={
            p.name: digest(p)
            for p in sorted(package.iterdir())
            if p.suffix in {".py", ".json"}
        },
        versions=versions,
    )
    contract["fingerprint"] = hashlib.sha256(
        json.dumps(contract, sort_keys=True).encode()
    ).hexdigest()
    return contract


def process_deposit(rows, adapter, environment):
    result = {name: [] for name in SCHEMAS}
    analyses = []
    included = {}
    base = {
        key: rows[0][key]
        for key in ("dataset_version_uid", "dataset_doi", "collection_id")
    }
    for row in rows:
        state, reason = eligibility(row)
        entry = dict(
            base,
            file_uid=row["file_uid"],
            relative_path=row["relative_path"],
            language=row["language"],
            eligibility=state,
            eligibility_reason=reason,
            read_status="not_requested",
            sha256=None,
            encoding=None,
            detail="",
        )
        result["ledger"].append(entry)
        if state == "excluded" or row["language"] not in LANGUAGES | {
            "notebook",
            "rmarkdown",
        }:
            continue
        included[row["file_uid"]] = state
        source, status, sha, encoding, detail = read_source(row)
        entry.update(read_status=status, sha256=sha, encoding=encoding, detail=detail)
        if source is None:
            language = row["language"]
            units = [Unit(row["file_uid"], row["file_uid"], language, "")]
        else:
            try:
                units = adapter.units(row, source)
            except (ValueError, TypeError, KeyError, AttributeError) as exc:
                entry.update(read_status="container_failed", detail=str(exc))
                units = [Unit(row["file_uid"], row["file_uid"], row["language"], "")]
        for unit in units:
            a = Analysis(unit)
            if entry["read_status"] != "complete":
                a.token_status = a.structure_status = "failed"
                a.detail = entry["detail"]
            else:
                try:
                    tokenize_unit(a, adapter)
                    measure_structure(a, adapter)
                    measure_findings(a)
                except (RecursionError, ValueError, SyntaxError) as exc:
                    a.token_status = a.structure_status = "failed"
                    a.tokens.clear()
                    a.code_lines.clear()
                    a.findings.clear()
                    a.detail = f"Instrument could not analyze: {exc}"
            analyses.append(a)
            result["units"].append(
                dict(
                    base,
                    file_uid=unit.file_uid,
                    unit_uid=unit.uid,
                    language=unit.language,
                    token_status=a.token_status,
                    structure_status=a.structure_status,
                    detail=a.detail,
                    code_lines=(
                        len(a.code_lines) if a.token_status == "complete" else None
                    ),
                    tokens=len(a.tokens) if a.token_status == "complete" else None,
                    routine_count=(
                        len(a.routines) if a.structure_status == "complete" else None
                    ),
                    branch_count=(
                        a.branch_count if a.structure_status == "complete" else None
                    ),
                    max_nesting=(
                        a.max_nesting if a.structure_status == "complete" else None
                    ),
                    first_line=unit.first_line,
                    cell_index=unit.cell_index,
                    chunk_label=unit.chunk_label,
                )
            )
            result["findings"].extend(dict(base, **finding) for finding in a.findings)
    for language in sorted(LANGUAGES):
        previous = None
        for variant in ("primary", "exclude_uncertain"):
            if previous is not None and "uncertain" not in included.values():
                metrics, clones = (
                    [dict(r, variant=variant) for r in rows] for rows in previous
                )
            else:
                metrics, clones = assess_language(
                    analyses,
                    language,
                    included,
                    environment.get(language, set()),
                    variant,
                )
            previous = metrics, clones
            result["metrics"].extend(dict(base, **m) for m in metrics)
            result["clones"].extend(dict(base, **m) for m in clones)
    return result


def cached_deposit(root, cache, group, environment, return_path=False):
    adapter = Softverse(root)
    warnings.filterwarnings("ignore", category=SyntaxWarning)
    key = group[0]["dataset_version_uid"]
    filename = cache / (hashlib.sha256(key.encode()).hexdigest() + ".json.gz")
    if filename.exists():
        with gzip.open(filename, "rt") as handle:
            result = json.load(handle)
        by_uid = {r["file_uid"]: r for r in group}
        for entry in result["ledger"]:
            if entry["read_status"] == "not_requested":
                continue
            _, status, sha, _, _ = read_source(by_uid[entry["file_uid"]])
            if sha != entry["sha256"] or (
                status != entry["read_status"]
                and entry["read_status"] != "container_failed"
            ):
                raise ValueError("Cached source changed; choose a new output directory")
    else:
        result = process_deposit(group, adapter, environment)
        temp = filename.with_suffix(".tmp")
        with gzip.open(temp, "wt") as handle:
            json.dump(result, handle, sort_keys=True)
        temp.replace(filename)
    return filename if return_path else result


def ordered_results(root, cache, jobs, workers):
    if workers == 1:
        for group, environment in jobs:
            yield cached_deposit(root, cache, group, environment)
        return
    with ProcessPoolExecutor(max_workers=workers) as executor:
        completed = executor.map(
            partial(cached_deposit, root, cache, return_path=True),
            (job[0] for job in jobs),
            (job[1] for job in jobs),
        )
        for filename in completed:
            with gzip.open(filename, "rt") as handle:
                yield json.load(handle)


def assess(root, output, limit=None, workers=1):
    root, output = root.resolve(), output.resolve()
    Softverse(root)
    manifest = instrument(root, limit)
    output.mkdir(parents=True, exist_ok=True)
    manifest_path = output / "manifest.json"
    if (
        manifest_path.exists()
        and json.loads(manifest_path.read_text())["fingerprint"]
        != manifest["fingerprint"]
    ):
        raise ValueError(
            "Run inputs or instrument changed; choose a new output directory"
        )
    write_json(manifest_path, manifest)
    cache = output / "cache"
    cache.mkdir(exist_ok=True)
    frame = {
        r["collection_id"]
        for r in csv.DictReader((root / "data/frame/frame.csv").open())
    }
    rows = pq.read_table(root / "build/tally/files.parquet").to_pylist()
    uids, dois, groups = set(), {}, defaultdict(list)
    for row in rows:
        if row["file_uid"] in uids:
            raise ValueError("Duplicate file_uid in inventory")
        uids.add(row["file_uid"])
        doi, version = row["dataset_doi"], row["dataset_version_uid"]
        if not doi or not version:
            raise ValueError("Missing deposit identity")
        if doi in dois and dois[doi] != version:
            raise ValueError("DOI maps to multiple versions")
        dois[doi] = version
        if row["collection_id"] in frame:
            groups[version].append(row)
    env = environment_index(root, {r["file_uid"]: r["dataset_doi"] for r in rows})
    keys = sorted(groups, key=lambda k: hashlib.sha256(k.encode()).hexdigest())
    if limit is not None:
        keys = keys[:limit]
    writers = Tables(output)
    success = False
    try:
        jobs = []
        for key in keys:
            group = sorted(groups[key], key=lambda r: r["file_uid"])
            if len({r["collection_id"] for r in group}) != 1:
                raise ValueError("Deposit maps to multiple collections")
            jobs.append((group, dict(env[group[0]["dataset_doi"]])))
        for i, result in enumerate(ordered_results(root, cache, jobs, workers), 1):
            writers.write(result)
            if i % 25 == 0 or i == len(keys):
                print(f"Assessed {i}/{len(keys)} deposits", flush=True)
        success = True
    finally:
        writers.close(success)
    manifest.update(
        completed=True,
        deposits=len(keys),
        inventory_rows=len(rows),
        frame_inventory_rows=sum(len(g) for g in groups.values()),
        output_rows=writers.counts,
    )
    manifest["output_hashes"] = {
        f"{name}.parquet": digest(output / f"{name}.parquet") for name in SCHEMAS
    }
    write_json(manifest_path, manifest)
    return manifest
