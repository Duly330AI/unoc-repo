"""Generate TypeScript types from backend models & schemas (TASK-004).

Outputs to: unoc-frontend-v2/src/types/domain.ts

Rules:
- Enums -> string union type
- Pydantic 'Out' models -> TS interface
- Deterministic sort ordering
"""

from __future__ import annotations

import hashlib
import inspect
import sys
from pathlib import Path
from typing import Any, get_type_hints

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend import models as domain_models  # type: ignore  # noqa: E402
from backend.api import schemas as api_schemas  # type: ignore  # noqa: E402

OUT_DIR = Path(__file__).resolve().parent.parent / "unoc-frontend-v2" / "src" / "types"
OUT_FILE = OUT_DIR / "domain.ts"


ENUM_EXPORTS = [
    domain_models.DeviceType,
    domain_models.LinkType,
    domain_models.Status,
    domain_models.DeviceRole,
    domain_models.InterfaceRole,
    domain_models.AdminStatus,
]

MODEL_EXPORTS = [
    api_schemas.DeviceOut,
    api_schemas.InterfaceOut,
    api_schemas.LinkOut,
    api_schemas.LinkResolvedOut,
    api_schemas.TariffOut,
]


def enum_to_ts(e: type) -> str:
    values = [f'"{m.value}"' for m in e]  # type: ignore[attr-defined]
    values.sort()
    return f"export type {e.__name__} = " + " | ".join(values) + ";\n"


PY_TO_TS = {
    str: "string",
    int: "number",
    float: "number",
    bool: "boolean",
}


def py_type_to_ts(t: Any) -> str:
    origin = getattr(t, "__origin__", None)
    if origin is list or origin is list:
        args = getattr(t, "__args__", [Any])
        return f"{py_type_to_ts(args[0])}[]"
    if origin is None:
        if t in PY_TO_TS:
            return PY_TO_TS[t]
        if inspect.isclass(t) and issubclass(t, tuple(ENUM_EXPORTS)):
            return t.__name__
    # fallback
    return "any"


def model_to_interface(m: type) -> str:
    hints = get_type_hints(m, include_extras=True)
    lines: list[str] = []
    for field_name, field_type in sorted(hints.items(), key=lambda kv: kv[0]):
        optional = " | None" in str(field_type) or "NoneType" in str(field_type)
        ts_type = py_type_to_ts(field_type)
        opt = "?" if optional else ""
        lines.append(f"  {field_name}{opt}: {ts_type};")
    return "export interface " + m.__name__ + " {\n" + "\n".join(lines) + "\n}\n"


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    parts: list[str] = []
    for e in ENUM_EXPORTS:
        parts.append(enum_to_ts(e))
    for m in MODEL_EXPORTS:
        parts.append(model_to_interface(m))
    body = "\n".join(parts)
    h = hashlib.sha256(body.encode()).hexdigest()[:12]
    header = (
        "// AUTO-GENERATED FILE – DO NOT EDIT\n"
        f"// Hash: {h}\n"
        "// Source: tools/gen_ts_types.py\n\n"
        "/* eslint-disable */\n"
    )
    OUT_FILE.write_text(header + body, encoding="utf-8")
    print(f"Wrote {OUT_FILE} ({len(body.splitlines())} lines)")


if __name__ == "__main__":  # pragma: no cover
    main()
