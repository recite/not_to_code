"""The single, versioned measurement dictionary for all producers and reports."""

import json
from pathlib import Path

REGISTRY = json.loads(Path(__file__).with_name("metrics.json").read_text())


def measures(language, source=None):
    return {
        name: spec
        for name, spec in REGISTRY.items()
        if language in spec["languages"]
        and (source is None or spec["source"] == source)
    }
