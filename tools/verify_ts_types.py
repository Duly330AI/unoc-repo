"""Verify generated TypeScript domain types are in sync (TASK-004).

Steps:
1. Read committed domain.ts
2. Re-run in-memory generation (reuse gen_ts_types logic without overwriting)
3. Compare content (ignoring hash line). Exit code 0 if match, 1 if drift.

Usage:
  python tools/verify_ts_types.py  (non-destructive)
"""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import tools.gen_ts_types as gen_ts_types  # type: ignore

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

OUT_FILE = gen_ts_types.OUT_FILE


def normalize(content: str) -> str:
    lines = content.splitlines()
    # Drop hash line for comparison (starts with // Hash: )
    return "\n".join(line for line in lines if not line.startswith("// Hash:"))


def regenerate() -> str:
    # Re-run generation to temp string instead of writing file.
    parts: list[str] = []
    for e in gen_ts_types.ENUM_EXPORTS:
        parts.append(gen_ts_types.enum_to_ts(e))
    for m in gen_ts_types.MODEL_EXPORTS:
        parts.append(gen_ts_types.model_to_interface(m))
    body = "\n".join(parts)
    h = hashlib.sha256(body.encode()).hexdigest()[:12]
    header = (
        "// AUTO-GENERATED FILE – DO NOT EDIT\n"
        f"// Hash: {h}\n"
        "// Source: tools/gen_ts_types.py\n\n"
        "/* eslint-disable */\n"
    )
    return header + body + ("\n" if not body.endswith("\n") else "")


def main() -> int:
    if not OUT_FILE.exists():
        print(f"ERROR: {OUT_FILE} missing. Run generation script.")
        return 1
    committed = OUT_FILE.read_text(encoding="utf-8")
    regenerated = regenerate()
    if normalize(committed) == normalize(regenerated):
        print("Type generation verification PASSED (no drift).")
        return 0
    else:
        print("Type generation verification FAILED: drift detected.")
        print("--- Committed (truncated) ---")
        print("\n".join(committed.splitlines()[:20]))
        print("--- Regenerated (truncated) ---")
        print("\n".join(regenerated.splitlines()[:20]))
        print("Run: python tools/gen_ts_types.py to update.")
        return 1


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
