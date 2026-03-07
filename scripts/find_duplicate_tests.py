import re

content = open("backend/tests/test_batch_operations_integration.py", encoding="utf-8").read()
matches = [
    (m.start(), m.group(1)) for m in re.finditer(r"^\s*def (test_\w+)", content, re.MULTILINE)
]
funcs = {}
duplicates = []

for pos, name in matches:
    line_num = content[:pos].count("\n") + 1
    if name in funcs:
        duplicates.append((name, line_num, funcs[name]))
        print(f"{name}: line {line_num} (duplicate of line {funcs[name]})")
    else:
        funcs[name] = line_num

print(f"\nTotal duplicate functions: {len(duplicates)}")
