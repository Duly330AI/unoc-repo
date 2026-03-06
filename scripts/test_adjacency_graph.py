"""
Test adjacency graph building logic - mimic exactly what Go does.
"""

from collections import defaultdict, deque

import psycopg


def main():
    print("=== ADJACENCY GRAPH DEBUG ===\n")

    conn = psycopg.connect("postgresql://unoc:unocpw@localhost:5432/unocdb")
    cur = conn.cursor()

    # Step 1: Build interface-to-device mapping (like Go does)
    print("1. Building interface-to-device mapping...")
    cur.execute("SELECT id, device_id FROM interface")
    iface_to_device = {}
    for iface_id, dev_id in cur.fetchall():
        iface_to_device[iface_id] = dev_id
    print(f"   Total interfaces: {len(iface_to_device)}")

    # Step 2: Build adjacency graph from links
    print("\n2. Building adjacency graph from links...")
    cur.execute("SELECT id, a_interface_id, b_interface_id, status FROM link")
    neighbors = defaultdict(set)
    link_count = 0
    skipped_count = 0

    for link_id, a_iface, b_iface, status in cur.fetchall():
        # Only process UP links
        if status != "UP":
            print(f"   SKIP {link_id}: status={status}")
            skipped_count += 1
            continue

        # Get endpoint devices
        a_dev = iface_to_device.get(a_iface)
        b_dev = iface_to_device.get(b_iface)

        if not a_dev or not b_dev:
            print(f"   SKIP {link_id}: a_dev={a_dev}, b_dev={b_dev} (missing device mapping!)")
            skipped_count += 1
            continue

        # Add bidirectional edges
        neighbors[a_dev].add(b_dev)
        neighbors[b_dev].add(a_dev)
        link_count += 1
        print(f"   ADD {link_id}: {a_dev} <-> {b_dev}")

    print(f"\n   Links processed: {link_count}, skipped: {skipped_count}")

    # Step 3: Print adjacency list
    print("\n3. Final adjacency graph:")
    for dev, neighs in sorted(neighbors.items()):
        print(f"   {dev} -> {sorted(neighs)}")

    # Step 4: BFS from aon_cpe to find anchor
    print("\n4. Running BFS from aon_cpe to find anchor...")
    anchor_types = {"BACKBONE_GATEWAY", "CORE_ROUTER", "POP", "CORE_SITE"}

    # Get device types
    cur.execute("SELECT id, type, status FROM device")
    device_info = {row[0]: {"type": row[1], "status": row[2]} for row in cur.fetchall()}

    start_id = "aon_cpe"
    queue = deque([start_id])
    visited = {start_id}
    parents = {start_id: None}

    anchor_found = None
    iterations = 0

    while queue:
        current_id = queue.popleft()
        iterations += 1
        current_info = device_info.get(current_id, {})
        current_type = current_info.get("type")
        current_status = current_info.get("status")

        print(
            f"   Iteration {iterations}: visiting {current_id} (type={current_type}, status={current_status})"
        )

        # Check if current is anchor
        if current_type in anchor_types and current_id != start_id:
            print(f"   ✓ FOUND ANCHOR: {current_id} (type={current_type})")
            anchor_found = current_id
            break

        # Explore neighbors
        neighs = neighbors.get(current_id, set())
        print(f"      Neighbors: {sorted(neighs) if neighs else 'NONE!'}")

        for neighbor_id in neighs:
            if neighbor_id in visited:
                print(f"      - {neighbor_id}: already visited")
                continue

            neighbor_info = device_info.get(neighbor_id, {})
            neighbor_status = neighbor_info.get("status")

            # Only traverse UP devices
            if neighbor_status != "UP":
                print(f"      - {neighbor_id}: SKIP (status={neighbor_status})")
                continue

            visited.add(neighbor_id)
            parents[neighbor_id] = current_id
            queue.append(neighbor_id)
            print(f"      - {neighbor_id}: added to queue")

    if anchor_found:
        # Reconstruct path
        path = []
        current = anchor_found
        while current:
            path.insert(0, current)
            current = parents[current]
        print(f"\n   ✓ Path found: {' -> '.join(path)}")
    else:
        print(f"\n   ✗ NO ANCHOR FOUND! BFS visited: {visited}")
        print("   This means the adjacency graph is disconnected or all neighbors were skipped!")

    conn.close()
    print("\n=== DEBUG COMPLETE ===")


if __name__ == "__main__":
    main()
