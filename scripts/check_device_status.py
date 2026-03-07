import psycopg

conn = psycopg.connect("postgresql://unoc:unocpw@localhost:5432/unocdb")
cur = conn.cursor()
cur.execute("SELECT id, status, admin_override_status FROM device ORDER BY id")
print("Devices in DB (RAW):")
for row in cur.fetchall():
    print(f"  {row[0]}: status={repr(row[1])}, override={repr(row[2])}")
conn.close()
