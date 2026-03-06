import time

import psycopg

conn = psycopg.connect("postgresql://unoc:unocpw@localhost:5432/unocdb")
print("[MONITOR] Watching DB for new links...")

for i in range(20):
    time.sleep(0.3)
    cur = conn.cursor()
    cur.execute("SELECT id, status FROM link ORDER BY id DESC LIMIT 1")
    row = cur.fetchone()
    if row:
        print(f"[DB] Link found: id={row[0]}, status={row[1]}")
        break
    print(f"[MONITOR] Check {i+1}/20: No links yet")

conn.close()
