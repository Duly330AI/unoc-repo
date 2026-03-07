"""Check device table schema."""

from sqlalchemy import create_engine, text

engine = create_engine("postgresql://unoc:unocpw@localhost:5432/unocdb")

with engine.connect() as conn:
    result = conn.execute(
        text(
            """
        SELECT column_name, data_type 
        FROM information_schema.columns 
        WHERE table_name='device' 
        ORDER BY ordinal_position
    """
        )
    )

    print("Device table columns:")
    for row in result:
        print(f"  - {row[0]}: {row[1]}")
