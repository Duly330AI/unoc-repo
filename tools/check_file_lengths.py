"""Utility to report files exceeding a configured max line length.

Usage (from repo root):
    python tools/check_file_lengths.py --max 400 --ext .py .ts --format table

Deterministic output: stable sorting by descending line count then path.
Excludes typical build / virtual env / coverage / node directories.
Collects markers for broad exemptions: ruff: noqa, noqa, pragma: no cover, type: ignore
"""

from __future__ import annotations

import argparse
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

EXCLUDE_DIR_NAMES = {".venv", "node_modules", "htmlcov", "dist", "build", "__pycache__"}
MARKER_SUBSTRINGS = ["ruff: noqa", "noqa", "pragma: no cover", "type: ignore"]


@dataclass(frozen=True)
class FileReport:
    path: Path
    lines: int
    markers: list[str]

    def marker_str(self) -> str:
        return ",".join(sorted(set(self.markers))) if self.markers else ""


def iter_files(root: Path, exts: Iterable[str]) -> Iterable[Path]:
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        if p.suffix in exts:
            # skip excluded dirs quickly
            if any(part in EXCLUDE_DIR_NAMES for part in p.parts):
                continue
            yield p


def count_lines(path: Path) -> int:
    # Read in binary then count newlines for speed & determinism
    data = path.read_bytes()
    # ensure final line counted even if no trailing newline
    return data.count(b"\n") + (0 if data.endswith(b"\n") else 1)


def collect_markers(path: Path) -> list[str]:
    text = path.read_text(errors="ignore")  # ignore encoding edge cases
    found: list[str] = []
    for m in MARKER_SUBSTRINGS:
        if m in text:
            found.append(m)
    return found


def build_report(root: Path, max_lines: int, exts: Iterable[str]) -> list[FileReport]:
    reports: list[FileReport] = []
    for f in iter_files(root, exts):
        line_count = count_lines(f)
        if line_count > max_lines:
            markers = collect_markers(f)
            reports.append(FileReport(f, line_count, markers))
    reports.sort(key=lambda r: (-r.lines, str(r.path)))
    return reports


def format_table(reports: list[FileReport]) -> str:
    if not reports:
        return "No files exceed limit."
    # columns: Lines | Markers | Path
    line_w = max(len(str(r.lines)) for r in reports)
    rows = [
        f"{'LINES'.ljust(line_w)}  MARKERS                 PATH",
        f"{'-'*line_w}  ----------------------  ----",
    ]
    for r in reports:
        rows.append(f"{str(r.lines).ljust(line_w)}  {r.marker_str():<22}  {r.path}")
    return "\n".join(rows)


def format_json(reports: list[FileReport]) -> str:
    import json

    payload = [
        {"path": str(r.path), "lines": r.lines, "markers": sorted(set(r.markers))} for r in reports
    ]
    return json.dumps(payload, indent=2)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--max", type=int, default=400, help="Max allowed lines")
    parser.add_argument("--ext", nargs="+", default=[".py", ".ts"], help="Extensions to include")
    parser.add_argument("--format", choices=["table", "json"], default="table")
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    reports = build_report(root, args.max, args.ext)

    if args.format == "table":
        print(format_table(reports))
    else:
        print(format_json(reports))

    # Exit non-zero if violations found to integrate into CI later
    return 1 if reports else 0


if __name__ == "__main__":  # pragma: no cover - convenience script
    raise SystemExit(main())
