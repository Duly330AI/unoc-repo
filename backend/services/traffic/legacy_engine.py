"""Legacy traffic engine module has been removed.

This file remains as a tombstone to clearly fail if imported.
Use backend.services.traffic.v2_runner.TariffTrafficRunner instead.
"""

raise ImportError(
    "backend.services.traffic.legacy_engine was removed; use TariffTrafficRunner (v2)."
)
