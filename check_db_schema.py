import psycopg

conn = psycopg.connect("postgresql://unoc:unocpw@localhost:5432/unocdb")
cur = conn.cursor()

# Check link data
cur.execute("SELECT id, a_interface_id, b_interface_id FROM link")
rows = cur.fetchall()
print("Links in database:")
for r in rows:
    print(f"  {r[0]}: a={r[1]}, b={r[2]}")

# Check which device each interface belongs to
cur.execute(
    "SELECT id, device_id FROM interface WHERE id IN ('backbone-access1', 'core_router-uplink1', 'core_router-access1', 'aon_switch-uplink1', 'aon_switch-access1', 'aon_cpe-access1')"
)
rows = cur.fetchall()
print("\nInterface-to-device mapping:")
for r in rows:
    print(f"  {r[0]} → {r[1]}")
