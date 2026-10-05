import random

from not_to_code.duplicates import coverage
from not_to_code.model import Analysis, Token, Unit


def test_clone_coverage_matches_brute_force():
    rng = random.Random(483)
    for trial in range(400):
        analyses = []
        for i in range(rng.randrange(1, 6)):
            analysis = Analysis(Unit(str(i), str(rng.randrange(3)), "python", ""))
            analysis.tokens = [
                Token(str(rng.randrange(3)), "", 1, 1, 1, "other")
                for _ in range(rng.randrange(25))
            ]
            analyses.append(analysis)
        size = rng.randrange(1, 8)
        actual = coverage(analyses, size)
        expected = {
            kind: [bytearray(len(a.tokens)) for a in analyses]
            for kind in ("within", "between")
        }
        for i, a in enumerate(analyses):
            for j, b in enumerate(analyses):
                for p in range(len(a.tokens) - size + 1):
                    for q in range(len(b.tokens) - size + 1):
                        if i == j and abs(p - q) < size:
                            continue
                        left = [t.value for t in a.tokens[p : p + size]]
                        right = [t.value for t in b.tokens[q : q + size]]
                        if left == right:
                            kind = (
                                "within"
                                if a.unit.file_uid == b.unit.file_uid
                                else "between"
                            )
                            expected[kind][i][p : p + size] = b"\1" * size
        for kind, masks in expected.items():
            assert actual[kind] == masks, (trial, kind)
        expected_union = [
            bytearray(x | y for x, y in zip(a, b))
            for a, b in zip(expected["within"], expected["between"])
        ]
        assert actual["union"] == expected_union, (trial, "union")
