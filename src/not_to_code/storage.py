"""Stable, explicit output schemas, including empty tables."""

import pyarrow as pa
import pyarrow.parquet as pq

BASE = [
    ("dataset_version_uid", pa.string()),
    ("dataset_doi", pa.string()),
    ("collection_id", pa.string()),
]
S, I, F = pa.string(), pa.int64(), pa.float64()
FIELDS = {
    "ledger": [
        ("file_uid", S),
        ("relative_path", S),
        ("language", S),
        ("eligibility", S),
        ("eligibility_reason", S),
        ("read_status", S),
        ("sha256", S),
        ("encoding", S),
        ("detail", S),
    ],
    "units": [
        ("file_uid", S),
        ("unit_uid", S),
        ("language", S),
        ("token_status", S),
        ("structure_status", S),
        ("detail", S),
        ("code_lines", I),
        ("tokens", I),
        ("routine_count", I),
        ("branch_count", I),
        ("max_nesting", I),
        ("first_line", I),
        ("cell_index", I),
        ("chunk_label", S),
    ],
    "findings": [
        ("file_uid", S),
        ("unit_uid", S),
        ("language", S),
        ("rule", S),
        ("line", I),
        ("col", I),
        ("cell_index", I),
        ("chunk_label", S),
        ("evidence", S),
    ],
    "clones": [
        ("file_uid", S),
        ("unit_uid", S),
        ("language", S),
        ("variant", S),
        ("mode", S),
        ("threshold", I),
        ("start_token", I),
        ("end_token", I),
        ("start_line", I),
        ("end_line", I),
        ("cell_index", I),
        ("chunk_label", S),
    ],
    "metrics": [
        ("language", S),
        ("variant", S),
        ("metric", S),
        ("numerator", F),
        ("denominator", F),
        ("value", F),
        ("status", S),
        ("eligible_units", I),
        ("measured_units", I),
    ],
}
SCHEMAS = {name: pa.schema(BASE + fields) for name, fields in FIELDS.items()}


class Tables:
    def __init__(self, output):
        self.output = output
        self.writers = {
            name: pq.ParquetWriter(
                output / f"{name}.parquet.tmp", schema, compression="zstd"
            )
            for name, schema in SCHEMAS.items()
        }
        self.counts = dict.fromkeys(SCHEMAS, 0)

    def write(self, result):
        for name, writer in self.writers.items():
            rows = result[name]
            if rows:
                writer.write_table(pa.Table.from_pylist(rows, schema=SCHEMAS[name]))
            self.counts[name] += len(rows)

    def close(self, success):
        for name, writer in self.writers.items():
            writer.close()
            if success:
                (self.output / f"{name}.parquet.tmp").replace(
                    self.output / f"{name}.parquet"
                )
