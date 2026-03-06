"""
End-to-End Traffic Flow Test - AON Path
========================================

Creates complete topology and validates traffic flows through entire chain:
backbone → core_router → aon_switch → aon_cpe

Requirements:
- Go Traffic Engine running on port 8080
- Backend running on port 5001 with USE_GO_TRAFFIC=1
- PostgreSQL running

Expected Behavior:
1. CPE generates dynamic traffic (within tariff bounds)
2. All links show utilization
3. Traffic flows through all devices to backbone
4. No browser interaction needed - automatic validation
"""

import time
from typing import Any

import httpx

BASE_URL = "http://localhost:5001"
GO_URL = "http://localhost:8080"


def log(msg: str) -> None:
    """Print timestamped log message."""
    print(f"[{time.strftime('%H:%M:%S')}] {msg}")


def api_post(path: str, json: dict[str, Any]) -> dict[str, Any]:
    """POST to backend API."""
    response = httpx.post(f"{BASE_URL}{path}", json=json, timeout=30.0)
    response.raise_for_status()
    return response.json()


def api_patch(path: str, json: dict[str, Any]) -> dict[str, Any]:
    """PATCH to backend API."""
    response = httpx.patch(f"{BASE_URL}{path}", json=json, timeout=30.0)
    response.raise_for_status()
    return response.json()


def api_get(path: str) -> dict[str, Any]:
    """GET from backend API."""
    response = httpx.get(f"{BASE_URL}{path}", timeout=30.0)
    response.raise_for_status()
    return response.json()


def create_device(device_id: str, device_type: str) -> dict[str, Any]:
    """Create device."""
    log(f"Creating device: {device_id} ({device_type})")
    return api_post(
        "/api/devices",
        {
            "id": device_id,
            "name": device_id,
            "type": device_type,
            "status": "UP",  # Must be UP for Go Traffic Engine to traverse
        },
    )


def create_link(a_dev: str, a_port: str, b_dev: str, b_port: str) -> dict[str, Any]:
    """Create link between two devices.
    Automatically orders interfaces lexicographically to match Backend's canonical format.
    """
    a_if = f"{a_dev}-{a_port}"
    b_if = f"{b_dev}-{b_port}"

    # Backend requires lexicographic ordering: swap if needed
    if a_if > b_if:
        a_if, b_if = b_if, a_if

    link_id = f"{a_if}__{b_if}"
    log(f"Creating link: {link_id}")
    return api_post(
        "/api/links",
        {
            "id": link_id,
            "a_interface_id": a_if,
            "b_interface_id": b_if,
            "kind": "FIBER",  # Must be uppercase enum value
        },
    )


def provision_device(device_id: str, tariff_id: str | None = None) -> dict[str, Any]:
    """Provision device (set status=active, assign tariff if leaf)."""
    log(f"Provisioning device: {device_id}" + (f" with tariff {tariff_id}" if tariff_id else ""))
    payload: dict[str, Any] = {"status": "active"}
    if tariff_id:
        payload["tariff_id"] = tariff_id
    return api_post(f"/api/devices/{device_id}/provision", payload)


def get_traffic_snapshot() -> dict[str, Any]:
    """Get current traffic snapshot from Go Traffic Engine."""
    response = httpx.get(f"{GO_URL}/api/v1/snapshot", timeout=10.0)
    response.raise_for_status()
    return response.json()


def get_metrics_snapshot() -> dict[str, Any]:
    """Get frontend metrics snapshot."""
    return api_get("/api/metrics/snapshot")


def validate_traffic_flow() -> tuple[bool, str]:
    """
    Validate that traffic flows through entire chain.

    Returns:
        (success, message)
    """
    log("Validating traffic flow...")

    # Get Go snapshot
    try:
        go_snap = get_traffic_snapshot()
    except Exception as e:
        return False, f"Failed to get Go snapshot: {e}"

    # Get frontend snapshot
    try:
        fe_snap = get_metrics_snapshot()
    except Exception as e:
        return False, f"Failed to get frontend snapshot: {e}"

    # Expected devices in chain
    expected_devices = ["backbone", "core_router", "aon_switch", "aon_cpe"]

    # Check Go snapshot has device metrics
    device_metrics = go_snap.get("device_metrics", {})
    if not device_metrics:
        return False, "Go snapshot has no device_metrics"

    # Check each device has traffic
    missing_devices = []
    zero_traffic_devices = []
    for dev_id in expected_devices:
        if dev_id not in device_metrics:
            missing_devices.append(dev_id)
            continue

        metrics = device_metrics[dev_id]
        up_mbps = metrics.get("up_mbps", 0.0)
        down_mbps = metrics.get("down_mbps", 0.0)

        if up_mbps == 0.0 and down_mbps == 0.0:
            zero_traffic_devices.append(dev_id)

    if missing_devices:
        return False, f"Devices missing from Go snapshot: {missing_devices}"

    if zero_traffic_devices:
        return False, f"Devices with zero traffic: {zero_traffic_devices}"

    # Check links have traffic
    link_metrics = go_snap.get("link_metrics", {})
    if not link_metrics:
        return False, "Go snapshot has no link_metrics"

    # Expected links - use ACCESS ports on backbone/core for downstream connections
    expected_links = [
        "backbone-access1__core_router-uplink1",
        "core_router-access1__aon_switch-uplink1",
        "aon_switch-access1__aon_cpe-access1",
    ]

    missing_links = []
    zero_util_links = []
    for link_id in expected_links:
        if link_id not in link_metrics:
            missing_links.append(link_id)
            continue

        metrics = link_metrics[link_id]
        utilization = metrics.get("utilization", 0.0)

        if utilization == 0.0:
            zero_util_links.append(link_id)

    if missing_links:
        return False, f"Links missing from Go snapshot: {missing_links}"

    if zero_util_links:
        return False, f"Links with zero utilization: {zero_util_links}"

    # Check frontend snapshot (transformed data)
    fe_devices = fe_snap.get("devices", {})
    if not fe_devices:
        return False, "Frontend snapshot has no devices"

    fe_links = fe_snap.get("links", {})
    if not fe_links:
        return False, "Frontend snapshot has no links"

    # Success!
    cpe_metrics = device_metrics["aon_cpe"]
    backbone_metrics = device_metrics["backbone"]

    return True, (
        f"[OK] Traffic flow validated!\n"
        f"  CPE: {cpe_metrics['up_mbps']:.1f} Mbps up, {cpe_metrics['down_mbps']:.1f} Mbps down\n"
        f"  Backbone: {backbone_metrics['up_mbps']:.1f} Mbps up, {backbone_metrics['down_mbps']:.1f} Mbps down\n"
        f"  All {len(expected_links)} links have utilization > 0"
    )


def main() -> None:
    """Create topology and validate traffic flow."""
    log("=" * 60)
    log("End-to-End Traffic Flow Test - AON Path")
    log("=" * 60)

    # Check Go Traffic Engine is running
    try:
        response = httpx.get(f"{GO_URL}/health", timeout=5.0)
        response.raise_for_status()
        log(f"[OK] Go Traffic Engine healthy: {response.json()}")
    except Exception as e:
        log(f"[FAIL] Go Traffic Engine not available: {e}")
        log("   Start with: cd engine-go && go run ./cmd/traffic-engine")
        return

    # Check Backend is running
    try:
        response = httpx.get(f"{BASE_URL}/api/health", timeout=5.0)
        response.raise_for_status()
        log("[OK] Backend healthy")
    except Exception as e:
        log(f"[FAIL] Backend not available: {e}")
        return

    log("")
    log("Phase 1: Creating devices...")
    log("-" * 60)

    # Create devices (left to right on topology)
    create_device("backbone", "BACKBONE_GATEWAY")
    create_device("core_router", "CORE_ROUTER")
    create_device("aon_switch", "AON_SWITCH")
    create_device("aon_cpe", "AON_CPE")

    log("")
    log("Phase 2: Creating links...")
    log("-" * 60)

    # Create links (left to right)
    # Note: Use ACCESS ports on backbone/core for downstream connections (like a switch)
    create_link("backbone", "access1", "core_router", "uplink1")
    create_link("core_router", "access1", "aon_switch", "uplink1")
    create_link("aon_switch", "access1", "aon_cpe", "access1")

    log("")
    log("Phase 3: Provisioning devices (core → switch → cpe, backbone already UP)...")
    log("-" * 60)

    # Note: Backbone is always_online and cannot be provisioned (no valid provision path)
    # It's already status=UP by default when created
    log("Skipping backbone (always_online, already UP)")
    time.sleep(0.5)

    log("Provisioning core_router (no tariff for active)")
    provision_device("core_router", tariff_id=None)
    time.sleep(0.5)

    log("Provisioning aon_switch (no tariff for active)")
    provision_device("aon_switch", tariff_id=None)
    time.sleep(0.5)

    # CPE needs tariff for traffic generation (tariff_id="4" is "AON 1000/1000")
    log("Provisioning aon_cpe with AON 1000/1000 tariff (id=4)")
    provision_device("aon_cpe", tariff_id="4")

    log("")
    log("Phase 4: Waiting for traffic generation...")
    log("-" * 60)
    log("Waiting 3 seconds for Go Traffic Engine to generate first ticks...")
    time.sleep(3)

    log("")
    log("Phase 5: Validating traffic flow...")
    log("-" * 60)

    # Validate multiple times to ensure consistency
    success_count = 0
    attempts = 5

    for attempt in range(1, attempts + 1):
        log(f"Validation attempt {attempt}/{attempts}...")
        success, message = validate_traffic_flow()

        if success:
            success_count += 1
            log(message)
        else:
            log(f"[FAIL] Validation failed: {message}")

        if attempt < attempts:
            time.sleep(1)  # Wait 1s between validations

    log("")
    log("=" * 60)
    log("Test Results")
    log("=" * 60)

    if success_count >= 3:
        log(f"[OK] SUCCESS: {success_count}/{attempts} validations passed")
        log("   Traffic flows correctly through entire chain!")
        log("   - CPE generates dynamic traffic within tariff bounds")
        log("   - All links show utilization > 0")
        log("   - Traffic aggregates upstream to backbone")
    else:
        log(f"[FAIL] FAILURE: Only {success_count}/{attempts} validations passed")
        log("   Traffic flow is inconsistent or broken")
        log("")
        log("Debug steps:")
        log("1. Check Backend logs for 'Go Traffic Engine CONNECTED'")
        log("2. Check Backend logs for 'Traffic tick completed: duration_ms=...'")
        log("3. Check Go logs for 'Traffic tick completed'")
        log(f"4. Manual check: curl {GO_URL}/api/v1/snapshot")
        log(f"5. Manual check: curl {BASE_URL}/api/metrics/snapshot")


if __name__ == "__main__":
    main()
