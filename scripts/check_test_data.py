from sqlalchemy import create_engine, text

engine = create_engine("postgresql://unoc:unocpw@localhost:5432/unocdb")
with engine.connect() as conn:
    # Check test-go-% devices
    result = conn.execute(
        text("SELECT id, type FROM device WHERE id LIKE 'test-go-%' OR id LIKE 'test-commit-%'")
    )
    rows = list(result)
    print(f"Found {len(rows)} test devices:")
    for row in rows:
        print(f"  {row[0]} ({row[1]})")
