#!/usr/bin/env python3
"""
Fail if any backend Python module exceeds 400 non-blank, non-comment lines.

Counts logical lines (skips empty lines and pure comment lines).
Excludes backend/tests/ and special-cased files listed in EXCLUDES.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
MAX_LINES = 400

# Add explicit exclusions here if needed (keep list small and temporary).
EXCLUDES = {
    # Example: "backend/provisioning.py",
}


def logical_line_count(path: Path) -> int:
    count = 0
    try:
        for raw in path.read_text(encoding="utf-8").splitlines():
            s = raw.strip()
            if not s:
                continue
            if s.startswith("#"):
                continue
            count += 1
    except UnicodeDecodeError:
        # If a file cannot be decoded as utf-8, treat as 0 to avoid false positives
        return 0
    return count


def main() -> int:
    violations: list[tuple[int, Path]] = []
    for path in BACKEND.rglob("*.py"):
        rel = path.relative_to(ROOT)
        # Skip tests and explicit excludes
        if rel.parts[:2] == ("backend", "tests"):
            continue
        if str(rel).replace("\\", "/") in EXCLUDES:
            continue
        lines = logical_line_count(path)
        if lines > MAX_LINES:
            violations.append((lines, rel))

    if violations:
        violations.sort(reverse=True)
        print(f"ERROR: Backend modules exceeding {MAX_LINES} logical lines:")
        for count, rel in violations:
            print(f"  {count:4d}  {rel}")
        print(
            "\nPlease split large modules into focused helpers or components to satisfy the policy."
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
