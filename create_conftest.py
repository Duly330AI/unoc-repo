# Script to create conftest.py for backend tests

content = """# Pytest configuration for backend tests
import os

# Override DATABASE_URL for Go integration tests
os.environ["DATABASE_URL"] = "postgresql://unoc:unocpw@localhost:5432/unocdb"
"""

target = r"c:\noc_project\UNOC\unoc\backend\tests\conftest.py"

with open(target, "w", encoding="utf-8") as f:
    f.write(content)

print(f"Created {target}")
