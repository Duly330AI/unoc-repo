#!/usr/bin/env python3
"""Quick DB query script to check link status values."""
import psycopg

try:
    conn = psycopg.connect("postgresql://unoc:unocpw@localhost:5432/unocdb")
    cur = conn.cursor()

    # Check recent links
    cur.execute(
        """
        SELECT id, status, kind, a_interface_id, b_interface_id 
        FROM link 
        ORDER BY id DESC 
        LIMIT 10
    """
    )

    rows = cur.fetchall()

    if not rows:
        print("✓ No links in database")
    else:
        print(f"Found {len(rows)} recent links:")
        print("-" * 80)
        for row in rows:
            link_id, status, kind, a_if, b_if = row
            print(f"  {link_id[:40]:40s} | status={status:10s} | kind={kind:6s}")
        print("-" * 80)

        # Check for any 'active' status links
        cur.execute("SELECT COUNT(*) FROM link WHERE status = 'active'")
        active_count = cur.fetchone()[0]
        if active_count > 0:
            print(f"⚠ WARNING: Found {active_count} links with status='active' (should be 'UP')")

    conn.close()

except Exception as e:
    print(f"✗ Error: {e}")
