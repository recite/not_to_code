import sys

from not_to_code.native import invoke, substantive


def test_failed_process_cannot_claim_processed():
    result = invoke(
        [sys.executable, "-c", 'print(\'{"status":"processed"}\'); exit(1)'], ""
    )
    assert result["status"] == "analysis_failed"


def test_timing_is_not_substantive():
    a = {"timing": 1, "result": [{"elapsed_seconds": 2, "value": 3}]}
    assert substantive(a) == {"result": [{"value": 3}]}
