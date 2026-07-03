from backend.services.traffic.v2_runner import (
    build_device_metric_changes,
    build_link_metric_changes,
    transform_go_snapshot_to_frontend,
)

GO_SNAPSHOT = {
    "tick": 21,
    "device_metrics": {
        "ont1": {
            "up_bps": 66_000_000.0,
            "down_bps": 330_000_000.0,
            "up_mbps": 66.0,
            "down_mbps": 330.0,
            "demand_up_bps": 100_000_000.0,
            "demand_down_bps": 500_000_000.0,
            "demand_up_mbps": 100.0,
            "demand_down_mbps": 500.0,
            "scale_up": 0.66,
            "scale_down": 0.66,
            "throttled": True,
            "utilization": 0.33,
            "capacity_mbps": 1000.0,
            "congested": True,
        }
    },
    "link_metrics": {
        "uplink1": {
            "up_bps": 200_000_000.0,
            "down_bps": 1_000_000_000.0,
            "traffic_mbps": 1200.0,
            "demand_up_bps": 300_000_000.0,
            "demand_down_bps": 1_500_000_000.0,
            "demand_mbps": 1800.0,
            "utilization": 1.0,
            "capacity_mbps": 1000.0,
            "congested": True,
        }
    },
}


def test_transform_go_snapshot_preserves_shaping_fields():
    frontend = transform_go_snapshot_to_frontend(GO_SNAPSHOT)

    device = frontend["devices"]["ont1"]
    # Delivered traffic stays the primary value ...
    assert device["bps"] == (66.0 + 330.0) * 1_000_000.0
    assert device["upstream_bps"] == 66_000_000.0
    assert device["downstream_bps"] == 330_000_000.0
    # ... and the B2 requested/scale/throttled fields survive.
    assert device["demand_up_bps"] == 100_000_000.0
    assert device["demand_down_bps"] == 500_000_000.0
    assert device["scale_up"] == 0.66
    assert device["scale_down"] == 0.66
    assert device["throttled"] is True
    # B1 fields are untouched.
    assert device["congested"] is True
    assert device["capacity_mbps"] == 1000.0

    link = frontend["links"]["uplink1"]
    assert link["demand_up_bps"] == 300_000_000.0
    assert link["demand_down_bps"] == 1_500_000_000.0
    assert link["congested"] is True
    assert link["capacity_mbps"] == 1000.0


def test_ws_change_helpers_preserve_shaping_fields():
    device_changes = build_device_metric_changes(GO_SNAPSHOT)
    link_changes = build_link_metric_changes(GO_SNAPSHOT)

    assert len(device_changes) == 1
    device = device_changes[0]
    assert device["id"] == "ont1"
    assert device["demand_up_bps"] == 100_000_000.0
    assert device["demand_down_bps"] == 500_000_000.0
    assert device["scale_up"] == 0.66
    assert device["scale_down"] == 0.66
    assert device["throttled"] is True
    assert device["congested"] is True
    assert device["capacity_mbps"] == 1000.0

    assert len(link_changes) == 1
    link = link_changes[0]
    assert link["id"] == "uplink1"
    assert link["demand_up_bps"] == 300_000_000.0
    assert link["demand_down_bps"] == 1_500_000_000.0
    assert link["congested"] is True
    assert link["capacity_mbps"] == 1000.0


def test_shaping_fields_are_optional_for_older_snapshots():
    legacy_snapshot = {
        "tick": 5,
        "device_metrics": {
            "ont1": {"up_bps": 1.0, "down_bps": 2.0, "up_mbps": 0.0, "down_mbps": 0.0}
        },
        "link_metrics": {"l1": {"up_bps": 1.0, "down_bps": 2.0, "traffic_mbps": 0.0}},
    }

    frontend = transform_go_snapshot_to_frontend(legacy_snapshot)
    device_changes = build_device_metric_changes(legacy_snapshot)

    assert "demand_up_bps" not in frontend["devices"]["ont1"]
    assert "throttled" not in frontend["devices"]["ont1"]
    assert "demand_up_bps" not in device_changes[0]
