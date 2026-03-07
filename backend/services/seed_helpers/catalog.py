"""Catalog seeding helpers.

Includes seeding of default tariffs and default hardware catalog entries.
Split from seed_service.py to keep the orchestrator thin; public API preserved
via re-export in seed_service.py.
"""

from __future__ import annotations

from sqlmodel import Session, select

from backend.models import DeviceType, HardwareModel, PortProfile, PortRole, Tariff


def ensure_default_tariffs(session: Session) -> None:
    """Ensure a small set of default tariffs exist with technology classification.

    Idempotent per unique name.
    GPON: Basic 100/20, Pro 1000/300
    AON:  Sym 300/300, Sym 1000/1000
    """
    desired: list[dict] = [
        {
            "name": "Basic 100/20",
            "max_up_mbps": 20.0,
            "max_down_mbps": 100.0,
            "technology": Tariff.TariffTechnology.GPON,  # type: ignore[attr-defined]
        },
        {
            "name": "Pro 1000/300",
            "max_up_mbps": 300.0,
            "max_down_mbps": 1000.0,
            "technology": Tariff.TariffTechnology.GPON,  # type: ignore[attr-defined]
        },
        {
            "name": "AON 300/300",
            "max_up_mbps": 300.0,
            "max_down_mbps": 300.0,
            "technology": Tariff.TariffTechnology.AON,  # type: ignore[attr-defined]
        },
        {
            "name": "AON 1000/1000",
            "max_up_mbps": 1000.0,
            "max_down_mbps": 1000.0,
            "technology": Tariff.TariffTechnology.AON,  # type: ignore[attr-defined]
        },
    ]
    existing = {t.name for t in session.exec(select(Tariff)).all()}
    for d in desired:
        if d["name"] in existing:
            continue
        session.add(
            Tariff(
                name=d["name"],
                max_up_mbps=d["max_up_mbps"],
                max_down_mbps=d["max_down_mbps"],
                technology=d["technology"],
            )
        )
    session.flush()


def ensure_default_hardware_models(session: Session) -> None:
    """Seed a minimal default hardware catalog and port profiles (idempotent).

    Creates generic models for common device types with sensible PortProfiles.
    The entries are marked with meta_source="default" for deterministic selection.
    """

    # Helper to get-or-create hardware model by catalog_id
    def goc_model(**kwargs) -> HardwareModel:
        catalog_id = kwargs["catalog_id"]
        row = session.exec(
            select(HardwareModel).where(HardwareModel.catalog_id == catalog_id)
        ).first()
        if row:
            # Reconcile core identity fields if changed
            updated = False
            for k in ("vendor", "model", "version", "device_type", "ports_total", "capacity_gbps"):
                if getattr(row, k, None) != kwargs.get(k):
                    setattr(row, k, kwargs.get(k))
                    updated = True
            if getattr(row, "meta_source", None) != "default":
                row.meta_source = "default"
                updated = True
            if updated:
                session.add(row)
            session.flush()
            return row
        row = HardwareModel(meta_source="default", **kwargs)
        session.add(row)
        session.flush()
        return row

    # Helper to upsert PortProfile by (hardware_model_id, name)
    def upsert_profile(
        model: HardwareModel,
        name: str,
        count: int,
        speed_gbps: float | None,
        port_role: PortRole | None = None,
        legacy_role: str | None = None,
        media: str | None = None,
        max_subscribers: int | None = None,
    ) -> None:
        assert model.id is not None
        model_id = model.id
        existing = session.exec(
            select(PortProfile).where(
                (PortProfile.hardware_model_id == model_id) & (PortProfile.name == name)
            )
        ).first()
        if existing:
            changed = False
            for k, v in {
                "count": count,
                "speed_gbps": speed_gbps,
                "port_role": port_role,
                "role": legacy_role,
                "media": media,
                "max_subscribers": max_subscribers,
            }.items():
                if getattr(existing, k) != v:
                    setattr(existing, k, v)
                    changed = True
            if changed:
                session.add(existing)
            return
        session.add(
            PortProfile(
                hardware_model_id=model_id,
                name=name,
                count=count,
                speed_gbps=speed_gbps,
                port_role=port_role,
                role=legacy_role,
                media=media,
                max_subscribers=max_subscribers,
            )
        )

    # --- OLT ---
    olt = goc_model(
        catalog_id="DEFAULT_OLT",
        device_type=DeviceType.OLT,
        vendor="UNOC",
        model="Generic OLT",
        version="1.0",
        ports_total=21,  # 16 PON + 4 uplink + 1 mgmt
        capacity_gbps=80.0,
    )
    upsert_profile(
        olt,
        name="mgmt0",
        count=1,
        speed_gbps=1.0,
        legacy_role="management",
        port_role=None,
        media="rj45",
    )
    upsert_profile(
        olt, name="uplink", count=4, speed_gbps=10.0, port_role=PortRole.UPLINK, media="sfp+"
    )
    upsert_profile(
        olt,
        name="pon",
        count=16,
        speed_gbps=None,
        port_role=PortRole.PON,
        media="pon",
        max_subscribers=64,
    )

    # --- AON Switch ---
    aon_sw = goc_model(
        catalog_id="DEFAULT_AON_SWITCH",
        device_type=DeviceType.AON_SWITCH,
        vendor="UNOC",
        model="Generic AON Switch",
        version="1.0",
        ports_total=29,  # 24 access + 4 uplink + 1 mgmt
        capacity_gbps=64.0,
    )
    upsert_profile(
        aon_sw, name="mgmt0", count=1, speed_gbps=1.0, legacy_role="management", media="rj45"
    )
    upsert_profile(
        aon_sw, name="access", count=24, speed_gbps=1.0, port_role=PortRole.ACCESS, media="rj45"
    )
    upsert_profile(
        aon_sw, name="uplink", count=4, speed_gbps=10.0, port_role=PortRole.UPLINK, media="sfp+"
    )

    # --- CORE Router ---
    core = goc_model(
        catalog_id="DEFAULT_CORE_ROUTER",
        device_type=DeviceType.CORE_ROUTER,
        vendor="UNOC",
        model="Generic Core Router",
        version="1.0",
        ports_total=10,
        capacity_gbps=800.0,
    )
    upsert_profile(
        core, name="mgmt0", count=1, speed_gbps=1.0, legacy_role="management", media="rj45"
    )
    upsert_profile(
        core, name="uplink", count=8, speed_gbps=100.0, port_role=PortRole.UPLINK, media="qsfp28"
    )
    upsert_profile(
        core, name="access", count=1, speed_gbps=10.0, port_role=PortRole.ACCESS, media="sfp+"
    )

    # --- BACKBONE Gateway --- (clone of Generic Router uplink set)
    bb = goc_model(
        catalog_id="DEFAULT_BACKBONE_GATEWAY",
        device_type=DeviceType.BACKBONE_GATEWAY,
        vendor="UNOC",
        model="Generic Backbone Gateway",
        version="1.0",
        ports_total=10,
        capacity_gbps=800.0,
    )
    upsert_profile(
        bb, name="mgmt0", count=1, speed_gbps=1.0, legacy_role="management", media="rj45"
    )
    upsert_profile(
        bb, name="uplink", count=8, speed_gbps=100.0, port_role=PortRole.UPLINK, media="qsfp28"
    )
    upsert_profile(
        bb, name="access", count=1, speed_gbps=10.0, port_role=PortRole.ACCESS, media="sfp+"
    )

    # --- EDGE Router ---
    edge = goc_model(
        catalog_id="DEFAULT_EDGE_ROUTER",
        device_type=DeviceType.EDGE_ROUTER,
        vendor="UNOC",
        model="Generic Edge Router",
        version="1.0",
        ports_total=13,
        capacity_gbps=200.0,
    )
    upsert_profile(
        edge, name="mgmt0", count=1, speed_gbps=1.0, legacy_role="management", media="rj45"
    )
    upsert_profile(
        edge, name="uplink", count=4, speed_gbps=10.0, port_role=PortRole.UPLINK, media="sfp+"
    )
    upsert_profile(
        edge, name="access", count=8, speed_gbps=1.0, port_role=PortRole.ACCESS, media="rj45"
    )

    # --- AON CPE ---
    cpe = goc_model(
        catalog_id="DEFAULT_AON_CPE",
        device_type=DeviceType.AON_CPE,
        vendor="UNOC",
        model="Generic AON CPE",
        version="1.0",
        ports_total=5,
        capacity_gbps=1.0,
    )
    upsert_profile(
        cpe, name="mgmt0", count=1, speed_gbps=1.0, legacy_role="management", media="rj45"
    )
    upsert_profile(
        cpe, name="access", count=4, speed_gbps=1.0, port_role=PortRole.ACCESS, media="rj45"
    )

    # --- ONT ---
    ont = goc_model(
        catalog_id="DEFAULT_ONT",
        device_type=DeviceType.ONT,
        vendor="UNOC",
        model="Generic ONT",
        version="1.0",
        ports_total=2,
        capacity_gbps=1.0,
    )
    upsert_profile(
        ont, name="mgmt0", count=1, speed_gbps=1.0, legacy_role="management", media="rj45"
    )
    upsert_profile(ont, name="ge", count=1, speed_gbps=1.0, port_role=PortRole.ACCESS, media="rj45")

    # --- Passive inline devices (ODF/NVT/SPLITTER/HOP) ---
    odf = goc_model(
        catalog_id="DEFAULT_ODF",
        device_type=DeviceType.ODF,
        vendor="UNOC",
        model="Generic ODF",
        version="1.0",
        ports_total=1,
        capacity_gbps=None,
        insertion_loss_db=0.5,
    )
    upsert_profile(odf, name="if0", count=1, speed_gbps=None, port_role=None, media=None)

    splitter = goc_model(
        catalog_id="DEFAULT_SPLITTER",
        device_type=DeviceType.SPLITTER,
        vendor="UNOC",
        model="Generic Splitter",
        version="1.0",
        ports_total=1,
        capacity_gbps=None,
        insertion_loss_db=3.5,
    )
    upsert_profile(splitter, name="if0", count=1, speed_gbps=None, port_role=None, media=None)

    nvt = goc_model(
        catalog_id="DEFAULT_NVT",
        device_type=DeviceType.NVT,
        vendor="UNOC",
        model="Generic NVT",
        version="1.0",
        ports_total=1,
        capacity_gbps=None,
        insertion_loss_db=0.2,
    )
    upsert_profile(nvt, name="if0", count=1, speed_gbps=None, port_role=None, media=None)

    hop = goc_model(
        catalog_id="DEFAULT_HOP",
        device_type=DeviceType.HOP,
        vendor="UNOC",
        model="Generic Inline Hop",
        version="1.0",
        ports_total=1,
        capacity_gbps=None,
        insertion_loss_db=0.1,
    )
    upsert_profile(hop, name="if0", count=1, speed_gbps=None, port_role=None, media=None)

    # --- CORE SITE (Container) ---
    goc_model(
        catalog_id="DEFAULT_CORE_SITE",
        device_type=DeviceType.CORE_SITE,
        vendor="UNOC",
        model="Generic Core Site",
        version="1.0",
        ports_total=6,
        capacity_gbps=None,
    )

    session.flush()


__all__ = ["ensure_default_tariffs", "ensure_default_hardware_models"]
