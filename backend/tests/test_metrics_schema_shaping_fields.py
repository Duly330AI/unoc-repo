from backend.api.schemas import MetricsSnapshotResponse


def test_metrics_snapshot_response_retains_shaping_fields():
    response = MetricsSnapshotResponse.model_validate(
        {
            "lastTick": 9,
            "devices": {
                "ont1": {
                    "bps": 396_000_000.0,
                    "utilization": 0.33,
                    "upstream_bps": 66_000_000.0,
                    "downstream_bps": 330_000_000.0,
                    "capacity_mbps": 1000.0,
                    "congested": True,
                    "demand_up_bps": 100_000_000.0,
                    "demand_down_bps": 500_000_000.0,
                    "scale_up": 0.66,
                    "scale_down": 0.66,
                    "throttled": True,
                }
            },
            "links": {
                "uplink1": {
                    "bps": 1_200_000_000.0,
                    "utilization": 1.0,
                    "capacity_mbps": 1000.0,
                    "congested": True,
                    "demand_up_bps": 300_000_000.0,
                    "demand_down_bps": 1_500_000_000.0,
                }
            },
        }
    )

    dumped = response.model_dump()

    device = dumped["devices"]["ont1"]
    assert device["demand_up_bps"] == 100_000_000.0
    assert device["demand_down_bps"] == 500_000_000.0
    assert device["scale_up"] == 0.66
    assert device["scale_down"] == 0.66
    assert device["throttled"] is True
    # B1 fields still intact
    assert device["congested"] is True
    assert device["capacity_mbps"] == 1000.0

    link = dumped["links"]["uplink1"]
    assert link["demand_up_bps"] == 300_000_000.0
    assert link["demand_down_bps"] == 1_500_000_000.0


def test_metrics_snapshot_response_shaping_fields_default_to_none():
    response = MetricsSnapshotResponse.model_validate(
        {
            "lastTick": 1,
            "devices": {"ont1": {"bps": 1.0, "utilization": 0.0}},
        }
    )

    device = response.devices["ont1"]
    assert device.demand_up_bps is None
    assert device.scale_up is None
    assert device.throttled is None
