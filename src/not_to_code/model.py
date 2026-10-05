"""Source units and lexical evidence, before deposit-level aggregation."""

from dataclasses import dataclass, field


@dataclass(slots=True)
class Token:
    value: str
    normalized: str
    line: int
    col: int
    end_line: int
    kind: str


@dataclass
class Unit:
    uid: str
    file_uid: str
    language: str
    source: str
    first_line: int = 1
    cell_index: int | None = None
    chunk_label: str | None = None
    incomplete: bool = False
    first_col: int = 1


@dataclass
class Analysis:
    unit: Unit
    tokens: list[Token] = field(default_factory=list)
    code_lines: set[int] = field(default_factory=set)
    token_status: str = "complete"
    structure_status: str = "complete"
    detail: str = ""
    branch_count: int = 0
    max_nesting: int = 0
    routines: list[tuple[int, int]] = field(default_factory=list)
    findings: list[dict] = field(default_factory=list)

    def finding(self, rule: str, line: int, col: int, evidence: str) -> None:
        self.findings.append(
            {
                "unit_uid": self.unit.uid,
                "file_uid": self.unit.file_uid,
                "language": self.unit.language,
                "rule": rule,
                "line": line + self.unit.first_line - 1,
                "col": col + (self.unit.first_col - 1 if line == 1 else 0),
                "cell_index": self.unit.cell_index,
                "chunk_label": self.unit.chunk_label,
                "evidence": evidence[:300],
            }
        )
