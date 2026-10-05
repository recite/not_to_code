import os
from pathlib import Path

import pytest

from not_to_code.adapter import Softverse
from not_to_code.findings import measure_findings
from not_to_code.lexical import tokenize_unit
from not_to_code.model import Analysis, Unit
from not_to_code.structure import measure_structure


@pytest.fixture(scope="session")
def adapter():
    root = Path(
        os.environ.get(
            "SOFTVERSE_ROOT", str(Path(__file__).resolve().parents[2] / "softverse")
        )
    )
    return Softverse(root)


@pytest.fixture
def analyze(adapter):
    def run(language, source, uid="a", file_uid=None):
        a = Analysis(Unit(uid, file_uid or uid, language, source))
        tokenize_unit(a, adapter)
        measure_structure(a, adapter)
        measure_findings(a)
        return a

    return run
