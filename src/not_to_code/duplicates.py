"""Exact window matching with collision verification and union coverage."""

from array import array
from collections import defaultdict


def windows(values, size):
    packed = array("I", values)
    width = packed.itemsize
    raw = packed.tobytes()
    for start in range(len(values) - size + 1):
        yield start, raw[start * width : (start + size) * width]


def coverage(analyses, size, normalized=False):
    vocabulary = {}
    sequences = []
    index = {}
    for u, a in enumerate(analyses):
        seq = []
        for token in a.tokens:
            text = token.normalized if normalized else token.value
            seq.append(vocabulary.setdefault(text, len(vocabulary) + 1))
        sequences.append(seq)
        for start, key in windows(seq, size):
            occurrence = (u, start)
            if key not in index:
                index[key] = occurrence
            elif isinstance(index[key], tuple):
                index[key] = [index[key], occurrence]
            else:
                index[key].append(occurrence)
    masks = {
        kind: [bytearray(len(s)) for s in sequences] for kind in ("within", "between")
    }
    for occurrences in index.values():
        if isinstance(occurrences, tuple):
            continue
        by_file = defaultdict(list)
        for u, start in occurrences:
            by_file[analyses[u].unit.file_uid].append((u, start))
        for entries in by_file.values():
            first, last = entries[0], entries[-1]
            for u, start in entries:
                # Distinct units never overlap, including cells in one file.
                within = (
                    first[0] != u
                    or last[0] != u
                    or start - first[1] >= size
                    or last[1] - start >= size
                )
                if within:
                    masks["within"][u][start : start + size] = b"\1" * size
                if len(by_file) > 1:
                    masks["between"][u][start : start + size] = b"\1" * size
    masks["union"] = [
        bytearray(x | y for x, y in zip(a, b))
        for a, b in zip(masks["within"], masks["between"])
    ]
    return masks


def spans(mask):
    start = None
    for i, flag in enumerate(mask):
        if flag and start is None:
            start = i
        elif not flag and start is not None:
            yield start, i
            start = None
    if start is not None:
        yield start, len(mask)


def measure_duplicates(analyses, thresholds=(30, 50, 100)):
    metrics, occurrences = {}, []
    denominator = sum(len(a.tokens) for a in analyses)
    for size in thresholds:
        exact = coverage(analyses, size)
        normalized = coverage(analyses, size, normalized=True)["union"]
        for kind, masks in exact.items():
            metrics[f"clone_exact_{kind}_{size}"] = (sum(map(sum, masks)), denominator)
        incremental = sum(
            sum(n and not e for n, e in zip(norm, ex))
            for norm, ex in zip(normalized, exact["union"])
        )
        metrics[f"clone_normalized_increment_{size}"] = (incremental, denominator)
        for mode, masks in (("exact", exact["union"]), ("normalized", normalized)):
            for a, mask in zip(analyses, masks):
                for start, end in spans(mask):
                    occurrences.append(
                        {
                            "unit_uid": a.unit.uid,
                            "file_uid": a.unit.file_uid,
                            "language": a.unit.language,
                            "mode": mode,
                            "threshold": size,
                            "start_token": start,
                            "end_token": end,
                            "start_line": a.tokens[start].line + a.unit.first_line - 1,
                            "end_line": max(t.end_line for t in a.tokens[start:end])
                            + a.unit.first_line
                            - 1,
                            "cell_index": a.unit.cell_index,
                            "chunk_label": a.unit.chunk_label,
                        }
                    )
    return metrics, occurrences
