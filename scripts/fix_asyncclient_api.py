#!/usr/bin/env python3
"""
Fix AsyncClient API for httpx 0.28+
Changes: AsyncClient(app=app) → AsyncClient(transport=ASGITransport(app=app))
"""
import re
from pathlib import Path

# Files to fix (from grep_search results)
FILES_TO_FIX = [
    "backend/tests/test_gpon_phase1_rules.py",
    "backend/tests/test_overrides_and_propagation.py",
    "backend/tests/test_provision_status_event.py",
    "backend/tests/test_status_propagation_phase2.py",
    "backend/tests/test_optical_status_gating.py",
    "backend/tests/test_l3_route_delete_propagation.py",
]


def fix_file(filepath: Path):
    """Fix AsyncClient(app=app) → AsyncClient(transport=ASGITransport(app=app))"""
    content = filepath.read_text(encoding="utf-8")
    original = content

    # Pattern: AsyncClient(app=app, base_url="http://test")
    # Replace with: AsyncClient(transport=ASGITransport(app=app), base_url="http://test")
    pattern = r"AsyncClient\(app=app,"
    replacement = r"AsyncClient(transport=ASGITransport(app=app),"

    content = re.sub(pattern, replacement, content)

    # Ensure ASGITransport import exists
    if "ASGITransport" in content and "from httpx import ASGITransport" not in content:
        # Find httpx imports
        if match := re.search(r"^from httpx import (.+)$", content, re.MULTILINE):
            old_imports = match.group(1)
            if "ASGITransport" not in old_imports:
                new_imports = old_imports.rstrip() + ", ASGITransport"
                content = content.replace(
                    f"from httpx import {old_imports}", f"from httpx import {new_imports}"
                )
        else:
            # Add new import after first import block
            lines = content.split("\n")
            for i, line in enumerate(lines):
                if line.startswith("from httpx import"):
                    lines.insert(i + 1, "from httpx import ASGITransport")
                    break
            else:
                # No httpx import found, add at top
                lines.insert(0, "from httpx import ASGITransport")
            content = "\n".join(lines)

    if content != original:
        filepath.write_text(content, encoding="utf-8")
        print(f"✅ Fixed: {filepath}")
        return True
    else:
        print(f"⏭️  Skipped (no changes): {filepath}")
        return False


def main():
    root = Path(__file__).parent.parent
    fixed = 0

    for file_rel in FILES_TO_FIX:
        filepath = root / file_rel
        if filepath.exists():
            if fix_file(filepath):
                fixed += 1
        else:
            print(f"⚠️  Not found: {filepath}")

    print(f"\n✅ Fixed {fixed}/{len(FILES_TO_FIX)} files")


if __name__ == "__main__":
    main()
