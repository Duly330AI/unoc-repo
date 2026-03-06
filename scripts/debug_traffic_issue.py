"""
Debug script for traffic generation issue.
Outputs all results to a file to avoid terminal conflicts.
"""

import httpx
import psycopg

OUTPUT_FILE = "debug_output.txt"


def write_output(msg: str):
    """Append message to output file and print."""
    with open(OUTPUT_FILE, "a", encoding="utf-8") as f:
        f.write(msg + "\n")
    print(msg)


def main():
    # Clear output file
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("=== TRAFFIC GENERATION DEBUG ===\n\n")

    write_output("1. Checking devices...")
    try:
        devices = httpx.get("http://localhost:5001/api/devices", timeout=5.0).json()
        write_output(f"   Found {len(devices)} devices:")
        for d in devices:
            write_output(
                f"   - {d['id']}: type=\"{d['type']}\" (repr={repr(d['type'])}), status={d['status']}, provisioned={d.get('provisioned', False)}, tariff={d.get('tariff_id', 'None')}"
            )

        # Check if core_router or backbone are anchor types
        write_output("\n   Anchor check:")
        anchor_types = ["BACKBONE_GATEWAY", "POP", "CORE_SITE", "CORE_ROUTER"]
        for d in devices:
            is_anchor = d["type"] in anchor_types
            write_output(
                f"   - {d['id']} ({d['type']}): {'✓ IS ANCHOR' if is_anchor else '✗ not anchor'}"
            )
    except Exception as e:
        write_output(f"   ERROR: {e}")

    write_output("\n2. Checking links...")
    try:
        links = httpx.get("http://localhost:5001/api/links", timeout=5.0).json()
        write_output(f"   Found {len(links)} links:")
        for link in links:
            write_output(
                f"   - {link['id']}: a={link['a_interface_id']}, b={link['b_interface_id']}, status={link['status']}"
            )
    except Exception as e:
        write_output(f"   ERROR: {e}")

    write_output("\n3. Checking if link interfaces exist in database...")
    try:
        conn = psycopg.connect("postgresql://unoc:unocpw@localhost:5432/unocdb")
        cur = conn.cursor()

        # Get all link interface IDs
        links = httpx.get("http://localhost:5001/api/links", timeout=5.0).json()
        interface_ids = set()
        for link in links:
            interface_ids.add(link["a_interface_id"])
            interface_ids.add(link["b_interface_id"])

        write_output(f"   Link interfaces needed: {sorted(interface_ids)}")

        # Check which ones exist in DB
        if interface_ids:
            placeholders = ",".join(["%s"] * len(interface_ids))
            cur.execute(
                f"SELECT id, device_id FROM interface WHERE id IN ({placeholders})",
                tuple(interface_ids),
            )
            results = cur.fetchall()

            write_output(f"   Interfaces found in DB: {len(results)}/{len(interface_ids)}")
            for iface_id, dev_id in results:
                write_output(f"   ✓ {iface_id} -> {dev_id}")

            # Find missing interfaces
            found_ids = {r[0] for r in results}
            missing_ids = interface_ids - found_ids
            if missing_ids:
                write_output("\n   MISSING INTERFACES (THIS IS THE PROBLEM!):")
                for missing in sorted(missing_ids):
                    write_output(f"   ✗ {missing}")

        conn.close()
    except Exception as e:
        write_output(f"   ERROR: {e}")

    write_output("\n4. Checking Go Traffic Engine snapshot...")
    try:
        go_snap = httpx.get("http://localhost:8080/api/v1/snapshot", timeout=5.0).json()
        write_output(f"   Tick: {go_snap['tick']}")
        write_output(f"   Leaves count: {go_snap['leaves_count']}")
        write_output(f"   Devices with traffic: {len(go_snap.get('device_metrics', {}))}")
        write_output(f"   Links with traffic: {len(go_snap.get('link_metrics', {}))}")
    except Exception as e:
        write_output(f"   ERROR: {e}")

    write_output("\n5. Total interface count in database...")
    try:
        conn = psycopg.connect("postgresql://unoc:unocpw@localhost:5432/unocdb")
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM interface")
        total = cur.fetchone()[0]
        write_output(f"   Total interfaces in DB: {total}")

        # Show first 10
        cur.execute("SELECT id, device_id, name FROM interface LIMIT 10")
        write_output("   Sample interfaces:")
        for iface_id, dev_id, name in cur.fetchall():
            write_output(f"   - {iface_id} (device={dev_id}, name={name})")

        conn.close()
    except Exception as e:
        write_output(f"   ERROR: {e}")

    write_output("\n=== DEBUG COMPLETE ===")
    write_output(f"Full output saved to: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
