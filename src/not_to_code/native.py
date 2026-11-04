"""Bounded, nonexecuting R analyzers and shared deposit-level aggregation."""

import hashlib
import json
import os
import subprocess
from pathlib import Path

from .registry import measures


def substantive(value):
    if isinstance(value, dict):
        return {
            k: substantive(v)
            for k, v in value.items()
            if k not in {"elapsed_seconds", "timing", "searchTimeMs", "processTimeMs"}
        }
    if isinstance(value, list):
        return [substantive(v) for v in value]
    return value


def invoke(command, source):
    try:
        run = subprocess.run(
            command, input=source, text=True, capture_output=True, timeout=35
        )
        try:
            result = json.loads(run.stdout)
            if not isinstance(result, dict) or "status" not in result:
                raise ValueError("Expected an analyzer status object")
        except ValueError:
            return {"status": "analysis_failed", "error": run.stderr[-2000:]}
        if run.returncode and result["status"] == "processed":
            return {"status": "analysis_failed", "error": "Nonzero tool exit"}
        return substantive(result)
    except subprocess.TimeoutExpired:
        return {"status": "timeout"}
    except OSError as exc:
        return {"status": "unavailable", "error": str(exc)}


def tool_contract(tools):
    if tools is None:
        return None
    tools = tools.resolve()
    paths = [
        tools / name
        for name in (
            "analyze.mjs",
            "randomness.mjs",
            "lint.R",
            "renv.lock",
            "package-lock.json",
        )
    ]
    record = {
        "root": str(tools),
        "hashes": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},
    }
    installed = json.loads(
        (tools / "node_modules/@eagleoutice/flowr/package.json").read_text()
    )
    locked = json.loads((tools / "package-lock.json").read_text())["packages"][
        "node_modules/@eagleoutice/flowr"
    ]["version"]
    if installed["version"] != locked:
        raise ValueError("Installed flowR differs from its lock; run npm ci")
    record["node"] = subprocess.run(
        ["node", "--version"], check=True, capture_output=True, text=True, timeout=10
    ).stdout.strip()
    check = invoke(
        ["Rscript", "--vanilla", str(tools / "lint.R"), str(tools / "renv.lock")], ""
    )
    if check["status"] != "processed":
        raise ValueError(f"Restore the locked R environment: {check}")
    record.update(flowR=locked, r=check["r_version"], lintr=check["version"])
    return record


def analyze_unit(unit, readable, contract, cache):
    tools = Path(contract["root"]) if contract else None
    records = {}
    for tool in ("flowR", "lintr"):
        if not tools:
            records[tool] = {"status": "not_measured"}
            continue
        if not readable or unit.language != "r" or unit.incomplete:
            records[tool] = {"status": "unavailable" if not readable else "unsupported"}
            continue
        key = hashlib.sha256(
            (unit.source + tool + json.dumps(contract, sort_keys=True)).encode()
        ).hexdigest()
        path = cache / f"{key}.json"
        if path.exists():
            records[tool] = json.loads(path.read_text())
            continue
        command = (
            ["node", "--max-old-space-size=512", str(tools / "analyze.mjs"), "--worker"]
            if tool == "flowR"
            else [
                "Rscript",
                "--vanilla",
                str(tools / "lint.R"),
                str(tools / "renv.lock"),
            ]
        )
        native = invoke(command, unit.source)
        temporary = path.with_suffix(f".{os.getpid()}.tmp")
        temporary.write_text(json.dumps(native, sort_keys=True))
        temporary.replace(path)
        records[tool] = native
    return records


def assess_native(analyses, eligibility, records, variant):
    selected = [
        a
        for a in analyses
        if a.unit.language in {"r", "unknown", "notebook", "rmarkdown"}
        and (variant == "primary" or eligibility[a.unit.file_uid] == "included")
    ]
    if not any(a.unit.language == "r" for a in selected):
        return []
    rows = []
    for name, spec in measures("r").items():
        if spec["source"] == "baseline":
            continue
        tool = "lintr" if spec["source"].startswith("lintr") else "flowR"
        entries = [records[a.unit.uid][tool] for a in selected]
        feature = "paths" if spec["source"] == "flowR" else "calls"

        def status_of(record):
            return record.get("feature_status", {}).get(feature, record["status"])

        measured = [
            a
            for a in selected
            if status_of(records[a.unit.uid][tool]) == "processed"
            and (spec["source"] != "lintr_rate" or a.token_status == "complete")
        ]
        good = [records[a.unit.uid][tool] for a in measured]
        status = (
            "not_measured"
            if all(e["status"] == "not_measured" for e in entries)
            else (
                "complete"
                if len(good) == len(entries)
                else "partial" if good else "missing"
            )
        )
        numerator, denominator, value = None, 1, None
        if good:
            calls = [c for e in good for c in e.get("calls", [])]
            if tool == "lintr":
                count = sum(f["linter"] == name for e in good for f in e["findings"])
                numerator = int(count > 0)
                if spec["source"] == "lintr_rate":
                    numerator = count
                    denominator = sum(len(a.code_lines) for a in measured)
            elif spec["source"] == "flowR":
                numerator = int(
                    any(
                        e["results"]["linter"]["results"]["absolute-file-paths"][
                            "results"
                        ]
                        for e in good
                    )
                )
            elif spec["source"] == "semantic":
                numerator = int(any(c["kind"] == "assertion" for c in calls))
            elif spec["source"] == "randomness":
                if status == "complete":
                    if not any(c["kind"] == "stochastic" for c in calls):
                        status = "inapplicable"
                    else:
                        numerator = int(
                            not any(
                                c["kind"] == "seed"
                                and c["seed_value"] not in {"null", "missing"}
                                for c in calls
                            )
                        )
            if numerator is not None and denominator:
                value = numerator / denominator * spec["scale"]
            elif status == "complete":
                status = "inapplicable"
        rows.append(
            dict(
                language="r",
                variant=variant,
                metric=name,
                numerator=numerator,
                denominator=denominator,
                value=value,
                status=status,
                eligible_units=len(entries),
                measured_units=len(good),
            )
        )
    return rows
