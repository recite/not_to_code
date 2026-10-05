"""Read-only adapter to the explicitly supported Softverse source instrument."""

import importlib
import io
import json
import re
import sys
import tokenize
from pathlib import Path

from .model import Unit

SUPPORTED_EXTRACTOR = "2.4.0"
LANGUAGES = {"r", "python", "stata"}


class Softverse:
    def __init__(self, root: Path):
        root = root.resolve()
        sys.path.insert(0, str(root))
        package = importlib.import_module("softverse")
        if Path(package.__file__).resolve().parent != root / "softverse":
            raise ValueError("A different Softverse checkout is already imported")
        if package.EXTRACTOR_VERSION != SUPPORTED_EXTRACTOR:
            raise ValueError("Unsupported Softverse extractor; validate adapter first")
        self.notebooks = importlib.import_module("softverse.detect.notebooks")
        self.stata = importlib.import_module("softverse.stata.lexer")
        self.dispatch = importlib.import_module("softverse.detect.dispatch")

    def language_name(self, name) -> str:
        name = str(name or "").strip().lower()
        return str(self.notebooks._ENGINE_LANGUAGE.get(name, name or "unknown"))

    def literate_units(self, uid: str, source: str) -> list[Unit]:
        out = []
        current = None
        closer = None
        lines = []
        for number, line in enumerate(source.splitlines(), 1):
            if current is None:
                match = self.notebooks._CHUNK_OPEN.match(line)
                sweave = self.notebooks._RNW_OPEN.match(line)
                if not match and not sweave:
                    continue
                header = (match or sweave)[1]
                if match:
                    parts = header.strip().split(",", 1)[0].split()
                    language = self.language_name(parts[0] if parts else None)
                    label = parts[1] if len(parts) > 1 else None
                    fence = re.match(r"\s*(`{3,}|~{3,})", line)[1]
                    closer = re.compile(
                        r"^\s*"
                        + re.escape(fence[0])
                        + "{"
                        + str(len(fence))
                        + r",}\s*$"
                    )
                else:
                    language, label = "r", header.split(",")[0] or None
                    closer = self.notebooks._RNW_CLOSE
                if re.search(r"\bengine\s*=", header):
                    language = "unknown"
                current = Unit(
                    f"{uid}:chunk:{len(out)}",
                    uid,
                    language,
                    "",
                    number + 1,
                    chunk_label=label,
                )
                lines = []
            elif closer.match(line):
                current.source = "\n".join(lines)
                out.append(current)
                current = None
            else:
                lines.append(line)
        if current is not None:
            current.source = "\n".join(lines)
            current.incomplete = True
            out.append(current)
        return out

    def units(self, row: dict, source: str) -> list[Unit]:
        language = row["language"]
        uid = row["file_uid"]
        if language in LANGUAGES:
            return [Unit(uid, uid, language, source)]
        if language == "rmarkdown":
            out = self.literate_units(uid, source)
            # Inline expressions are units; they must not disappear from coverage.
            for line, text in enumerate(source.splitlines(), 1):
                for i, match in enumerate(self.notebooks._INLINE_R.finditer(text)):
                    if any(
                        u.uid.startswith(f"{uid}:chunk:")
                        and u.first_line
                        <= line
                        < u.first_line + len(u.source.splitlines())
                        for u in out
                    ):
                        continue
                    out.append(
                        Unit(
                            f"{uid}:inline:{line}:{i}",
                            uid,
                            "r",
                            match[1],
                            line,
                            chunk_label="inline",
                            first_col=match.start(1) + 1,
                        )
                    )
            if not out:
                return [Unit(uid, uid, "r", "")]
            return out
        if language == "notebook":
            payload = json.loads(source)
            metadata = payload.get("metadata") or {}
            lang = self.language_name(
                (metadata.get("kernelspec") or {}).get("language")
                or (metadata.get("language_info") or {}).get("name")
            )
            cells = payload.get("cells")
            if cells is None:
                cells = [
                    c for s in payload.get("worksheets", []) for c in s.get("cells", [])
                ]
            out = []
            for i, cell in enumerate(cells or []):
                if cell.get("cell_type") != "code":
                    continue
                code = self.notebooks._cell_source(cell)
                cell_lang = lang
                first = code.splitlines()[0].strip() if code.splitlines() else ""
                if first.startswith("%%"):
                    parts = first[2:].split()
                    engine = parts[0].lower() if parts else ""
                    cell_lang = {
                        "r": "r",
                        "python": "python",
                        "stata": "stata",
                        "bash": "shell",
                        "sh": "shell",
                        "html": "html",
                        "javascript": "javascript",
                        "sql": "sql",
                    }.get(engine, "unknown")
                    code = "\n" + "\n".join(code.splitlines()[1:])
                magic_lines = {
                    n
                    for n, text in enumerate(code.splitlines(), 1)
                    if text.lstrip().startswith(("%", "!"))
                }
                if cell_lang == "python" and magic_lines:
                    try:
                        for token in tokenize.generate_tokens(
                            io.StringIO(code).readline
                        ):
                            if token.type in {
                                tokenize.STRING,
                                tokenize.COMMENT,
                            } or tokenize.tok_name[token.type] in {
                                "FSTRING_MIDDLE",
                                "TSTRING_MIDDLE",
                            }:
                                magic_lines.difference_update(
                                    range(token.start[0], token.end[0] + 1)
                                )
                    except (tokenize.TokenError, IndentationError, SyntaxError):
                        pass
                magic = bool(magic_lines)
                out.append(
                    Unit(
                        f"{uid}:cell:{i}",
                        uid,
                        cell_lang,
                        code,
                        cell_index=i,
                        incomplete=magic,
                    )
                )
            return out or [Unit(uid, uid, lang, "")]
        return [Unit(uid, uid, language, source)]


def eligibility(row: dict) -> tuple[str, str]:
    """Conservative exclusions; broad upstream heuristics stay uncertain."""
    parts = [p.lower() for p in Path(row["relative_path"]).parts]
    installed = {
        "site-packages",
        "dist-packages",
        "site-library",
        "node_modules",
        ".venv",
        "venv",
    }
    mechanical = {".ipynb_checkpoints", "__pycache__", "__macosx", ".git"}
    if set(parts) & mechanical or any(p.startswith("._") for p in parts):
        return "excluded", "mechanical_artifact"
    if set(parts) & installed:
        return "excluded", "installed_dependency_tree"
    if any(
        a in {"renv", "packrat", ".checkpoint"} and b in {"library", "lib", "src"}
        for a, b in zip(parts, parts[1:])
    ):
        return "excluded", "installed_dependency_tree"
    if row.get("is_vendored") or set(parts) & {
        "vendor",
        "ado",
        "old",
        "backup",
        "backups",
        "generated",
    }:
        return "uncertain", row.get("vendor_rule") or "ambiguous_role"
    return "included", "candidate_analysis_code"
