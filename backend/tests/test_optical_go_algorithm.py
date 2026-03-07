"""Integration tests for Go Optical PathFinder Algorithm (Day 17 Week 3).

Tests the Go Dijkstra implementation against real topology:
- Happy path: ONT → SPLITTER → OLT with proper attenuation
- No path: Disconnected ONT (no route to OLT)
- Multiple paths: Shortest path selection
- Attenuation accuracy: Fiber loss + insertion loss calculations

Performance Target: Single ONT path < 50ms (Python baseline: 40s = 800× speedup)
"""

import time
from contextlib import contextmanager

import pytest
from sqlalchemy import create_engine, text
from sqlmodel import Session

# CRITICAL: Import backend.models FIRST at module level
# Required for SQLAlchemy FK resolution and seed_service catalog operations
import backend.models  # noqa: F401
from backend.clients.go_services.optical_client import OpticalClient

# Create PostgreSQL session factory (bypassing root conftest SQLite setup)
POSTGRES_URL = "postgresql://unoc:unocpw@localhost:5432/unocdb"
_engine = create_engine(POSTGRES_URL)


def _init_schema_if_needed():
    """Initialize PostgreSQL schema if tables don't exist.

    Auto-creates all SQLModel tables and seeds catalog data.
    """
    try:
        with _engine.connect() as conn:
            conn.execute(text("SELECT 1 FROM device LIMIT 1"))
    except Exception:
        # Schema doesn't exist, create it directly with test engine
        from sqlmodel import SQLModel

        # Create all tables in test engine
        SQLModel.metadata.create_all(_engine)

        # Seed catalog data
        with Session(_engine) as session:
            from backend.services.seed_service import (
                ensure_default_hardware_models,
                ensure_physical_media,
            )

            ensure_physical_media(session)
            ensure_default_hardware_models(session)
            session.commit()


@contextmanager
def get_postgres_session():
    """Provide PostgreSQL session for integration tests."""
    _init_schema_if_needed()  # Ensure schema exists
    session = Session(_engine)
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@pytest.fixture
def optical_client():
    """Provide OpticalClient instance for tests."""
    return OpticalClient()


@pytest.fixture
def setup_optical_topology():
    """Create test topology: OLT → SPLITTER → ONT with known attenuation.

    Uses SQLModel for type-safe fixture creation. Auto-initializes schema if needed.
    """
    from sqlmodel import select

    from backend.models_pkg.device import Device, DeviceType, Status
    from backend.models_pkg.interface import AdminStatus, Interface
    from backend.models_pkg.link import Link, LinkType
    from backend.models_pkg.physical import PhysicalMedium

    with get_postgres_session() as session:
        # Clean up any existing test data
        for link in session.exec(select(Link).where(Link.id.like("test-go-%"))).all():  # type: ignore
            session.delete(link)
        for interface in session.exec(
            select(Interface).where(Interface.id.like("test-go-%"))  # type: ignore
        ).all():
            session.delete(interface)
        for device in session.exec(select(Device).where(Device.id.like("test-go-%"))).all():  # type: ignore
            session.delete(device)
        session.commit()

        # Get fiber type from catalog (SM_G652D: 0.35 dB/km)
        fiber = session.exec(
            select(PhysicalMedium).where(PhysicalMedium.code == "SMF_G652D")
        ).first()
        if not fiber:
            pytest.skip("SMF_G652D fiber not found in catalog")

        # Create devices using SQLModel (type-safe!)
        olt = Device(
            id="test-go-olt-1",
            name="Test OLT 1",
            type=DeviceType.OLT,
            status=Status.UP,
            provisioned=False,
        )
        session.add(olt)

        splitter = Device(
            id="test-go-splitter-1",
            name="Test Splitter 1:8",
            type=DeviceType.SPLITTER,
            status=Status.UP,
            insertion_loss_db=10.5,  # 1:8 splitter typical loss
            provisioned=False,
        )
        session.add(splitter)

        ont = Device(
            id="test-go-ont-1",
            name="Test ONT 1",
            type=DeviceType.ONT,
            status=Status.UP,
            provisioned=False,
        )
        session.add(ont)
        session.commit()

        # Create interfaces using SQLModel
        olt_port = Interface(
            id="test-go-olt-1-port-1",
            device_id="test-go-olt-1",
            name="1/1/1",
            admin_status=AdminStatus.UP,
        )
        session.add(olt_port)

        splitter_uplink = Interface(
            id="test-go-splitter-1-uplink",
            device_id="test-go-splitter-1",
            name="uplink",
            admin_status=AdminStatus.UP,
        )
        session.add(splitter_uplink)

        splitter_downlink = Interface(
            id="test-go-splitter-1-port-1",
            device_id="test-go-splitter-1",
            name="port-1",
            admin_status=AdminStatus.UP,
        )
        session.add(splitter_downlink)

        ont_port = Interface(
            id="test-go-ont-1-optical",
            device_id="test-go-ont-1",
            name="optical",
            admin_status=AdminStatus.UP,
        )
        session.add(ont_port)
        session.commit()

        # Create links using SQLModel
        # Link 1: OLT → SPLITTER (2 km = 0.7 dB fiber loss @ 0.35 dB/km)
        link1 = Link(
            id="test-go-link-1",
            a_interface_id="test-go-olt-1-port-1",
            b_interface_id="test-go-splitter-1-uplink",
            kind=LinkType.FIBER,
            length_km=2.0,
            physical_medium_id=fiber.id,
            status=Status.UP,
        )
        session.add(link1)

        # Link 2: SPLITTER → ONT (1 km = 0.35 dB fiber loss)
        link2 = Link(
            id="test-go-link-2",
            a_interface_id="test-go-splitter-1-port-1",
            b_interface_id="test-go-ont-1-optical",
            kind=LinkType.FIBER,
            length_km=1.0,
            physical_medium_id=fiber.id,
            status=Status.UP,
        )
        session.add(link2)

        session.commit()

        # Calculate expected attenuation:
        # - Link 1 fiber loss: 2.0 km × 0.35 dB/km = 0.7 dB
        # - Splitter insertion loss: 10.5 dB
        # - Link 2 fiber loss: 1.0 km × 0.35 dB/km = 0.35 dB
        # - Total: 0.7 + 10.5 + 0.35 = 11.55 dB
        expected_attenuation = 11.55

    yield {
        "ont_id": "test-go-ont-1",
        "olt_id": "test-go-olt-1",
        "splitter_id": "test-go-splitter-1",
        "expected_attenuation_db": expected_attenuation,
        "expected_segments": 2,  # ONT → SPLITTER → OLT
    }

    # Cleanup using SQLModel
    with get_postgres_session() as session:
        for link in session.exec(select(Link).where(Link.id.like("test-go-%"))).all():  # type: ignore
            session.delete(link)
        for interface in session.exec(
            select(Interface).where(Interface.id.like("test-go-%"))  # type: ignore
        ).all():
            session.delete(interface)
        for device in session.exec(select(Device).where(Device.id.like("test-go-%"))).all():  # type: ignore
            session.delete(device)
        session.commit()


@pytest.fixture
def setup_isolated_ont():
    """Create ONT with no path to OLT (disconnected topology)."""
    from sqlmodel import select

    from backend.models_pkg.device import Device, DeviceType, Status

    with get_postgres_session() as session:
        # Clean up existing
        for device in session.exec(select(Device).where(Device.id == "test-go-isolated-ont")).all():
            session.delete(device)
        session.commit()

        # Create ONT with no links
        isolated_ont = Device(
            id="test-go-isolated-ont",
            name="Isolated ONT",
            type=DeviceType.ONT,
            status=Status.UP,
            provisioned=False,
        )
        session.add(isolated_ont)
        session.commit()

    yield "test-go-isolated-ont"

    # Cleanup
    with get_postgres_session() as session:
        for device in session.exec(select(Device).where(Device.id == "test-go-isolated-ont")).all():
            session.delete(device)
        session.commit()


@pytest.fixture
def setup_multiple_paths():
    """Create topology with multiple paths to test shortest path selection.

    Topology:
                  ┌─ SPLITTER-A (8dB) ─┐
        OLT-1 ───┤                      ├─ ONT-1
                  └─ SPLITTER-B (12dB) ─┘

    Path A: 2km + 8dB + 1km = 0.7 + 8.0 + 0.35 = 9.05 dB (SHORTEST)
    Path B: 2km + 12dB + 1km = 0.7 + 12.0 + 0.35 = 13.05 dB
    """
    from sqlmodel import select

    from backend.models_pkg.device import Device, DeviceType, Status
    from backend.models_pkg.interface import AdminStatus, Interface
    from backend.models_pkg.link import Link, LinkType
    from backend.models_pkg.physical import PhysicalMedium

    with get_postgres_session() as session:
        # Clean up
        for link in session.exec(select(Link).where(Link.id.like("test-go-multi-%"))).all():  # type: ignore
            session.delete(link)
        for interface in session.exec(
            select(Interface).where(Interface.id.like("test-go-multi-%"))  # type: ignore
        ).all():
            session.delete(interface)
        for device in session.exec(select(Device).where(Device.id.like("test-go-multi-%"))).all():  # type: ignore
            session.delete(device)
        session.commit()

        # Get fiber type
        fiber = session.exec(
            select(PhysicalMedium).where(PhysicalMedium.code == "SMF_G652D")
        ).first()
        if not fiber:
            pytest.skip("SMF_G652D fiber not found")

        # Create devices using SQLModel
        olt = Device(
            id="test-go-multi-olt-1",
            name="Multi OLT",
            type=DeviceType.OLT,
            status=Status.UP,
            provisioned=False,
        )
        session.add(olt)

        splitter_a = Device(
            id="test-go-multi-splitter-a",
            name="Splitter A (8dB)",
            type=DeviceType.SPLITTER,
            status=Status.UP,
            insertion_loss_db=8.0,
            provisioned=False,
        )
        session.add(splitter_a)

        splitter_b = Device(
            id="test-go-multi-splitter-b",
            name="Splitter B (12dB)",
            type=DeviceType.SPLITTER,
            status=Status.UP,
            insertion_loss_db=12.0,
            provisioned=False,
        )
        session.add(splitter_b)

        ont = Device(
            id="test-go-multi-ont-1",
            name="Multi ONT",
            type=DeviceType.ONT,
            status=Status.UP,
            provisioned=False,
        )
        session.add(ont)
        session.commit()

        # Create interfaces (OLT: 2 ports, Splitters: uplink+downlink each, ONT: 1 port)
        interfaces_to_create = [
            Interface(
                id="test-go-multi-olt-port-1",
                device_id="test-go-multi-olt-1",
                name="1/1/1",
                admin_status=AdminStatus.UP,
            ),
            Interface(
                id="test-go-multi-olt-port-2",
                device_id="test-go-multi-olt-1",
                name="1/1/2",
                admin_status=AdminStatus.UP,
            ),
            Interface(
                id="test-go-multi-splitter-a-uplink",
                device_id="test-go-multi-splitter-a",
                name="uplink",
                admin_status=AdminStatus.UP,
            ),
            Interface(
                id="test-go-multi-splitter-a-downlink",
                device_id="test-go-multi-splitter-a",
                name="port-1",
                admin_status=AdminStatus.UP,
            ),
            Interface(
                id="test-go-multi-splitter-b-uplink",
                device_id="test-go-multi-splitter-b",
                name="uplink",
                admin_status=AdminStatus.UP,
            ),
            Interface(
                id="test-go-multi-splitter-b-downlink",
                device_id="test-go-multi-splitter-b",
                name="port-1",
                admin_status=AdminStatus.UP,
            ),
            Interface(
                id="test-go-multi-ont-optical",
                device_id="test-go-multi-ont-1",
                name="optical",
                admin_status=AdminStatus.UP,
            ),
        ]
        for iface in interfaces_to_create:
            session.add(iface)
        session.commit()

        # Create links (Path A and Path B)
        links_to_create = [
            # Path A: OLT → SPLITTER-A → ONT
            Link(
                id="test-go-multi-link-1a",
                a_interface_id="test-go-multi-olt-port-1",
                b_interface_id="test-go-multi-splitter-a-uplink",
                kind=LinkType.FIBER,
                length_km=2.0,
                physical_medium_id=fiber.id,
                status=Status.UP,
            ),
            Link(
                id="test-go-multi-link-2a",
                a_interface_id="test-go-multi-splitter-a-downlink",
                b_interface_id="test-go-multi-ont-optical",
                kind=LinkType.FIBER,
                length_km=1.0,
                physical_medium_id=fiber.id,
                status=Status.UP,
            ),
            # Path B: OLT → SPLITTER-B → ONT
            Link(
                id="test-go-multi-link-1b",
                a_interface_id="test-go-multi-olt-port-2",
                b_interface_id="test-go-multi-splitter-b-uplink",
                kind=LinkType.FIBER,
                length_km=2.0,
                physical_medium_id=fiber.id,
                status=Status.UP,
            ),
            Link(
                id="test-go-multi-link-2b",
                a_interface_id="test-go-multi-splitter-b-downlink",
                b_interface_id="test-go-multi-ont-optical",
                kind=LinkType.FIBER,
                length_km=1.0,
                physical_medium_id=fiber.id,
                status=Status.UP,
            ),
        ]
        for link in links_to_create:
            session.add(link)
        session.commit()

    yield {
        "ont_id": "test-go-multi-ont-1",
        "olt_id": "test-go-multi-olt-1",
        "expected_attenuation_db": 9.05,  # Path A (shorter)
        "expected_via": "test-go-multi-splitter-a",  # Should choose splitter A
    }

    # Cleanup using SQLModel
    with get_postgres_session() as session:
        for link in session.exec(select(Link).where(Link.id.like("test-go-multi-%"))).all():  # type: ignore
            session.delete(link)
        for interface in session.exec(
            select(Interface).where(Interface.id.like("test-go-multi-%"))  # type: ignore
        ).all():
            session.delete(interface)
        for device in session.exec(select(Device).where(Device.id.like("test-go-multi-%"))).all():  # type: ignore
            session.delete(device)
        session.commit()


def test_go_algorithm_happy_path(optical_client, setup_optical_topology):
    """Test Go PathFinder with happy path: ONT → SPLITTER → OLT."""
    topo = setup_optical_topology

    # Measure performance
    start_time = time.perf_counter()
    result = optical_client.get_path(ont_id=topo["ont_id"])
    elapsed_ms = (time.perf_counter() - start_time) * 1000

    print(f"\n📊 Go PathFinder Performance: {elapsed_ms:.2f} ms (target: <50ms)")

    # Validate response structure
    assert isinstance(result, dict), "Result must be dict"
    assert result.get("backend") == "go", "Should use Go implementation"
    assert result.get("path_exists") is True, "Path should exist"
    assert result.get("ont_id") == topo["ont_id"], "ONT ID must match"
    assert result.get("olt_id") == topo["olt_id"], f"OLT ID must be {topo['olt_id']}"

    # Validate path segments
    segments = result.get("segments", [])
    assert (
        len(segments) == topo["expected_segments"]
    ), f"Expected {topo['expected_segments']} segments"

    # Validate attenuation accuracy (±0.1 dB tolerance for floating point)
    total_attenuation = result.get("total_attenuation_db", 0.0)
    expected = topo["expected_attenuation_db"]
    tolerance = 0.1
    assert (
        abs(total_attenuation - expected) <= tolerance
    ), f"Attenuation mismatch: got {total_attenuation:.2f} dB, expected {expected:.2f} dB (±{tolerance} dB)"

    # Validate segment structure
    for segment in segments:
        assert "from_device_id" in segment, "Segment must have from_device_id"
        assert "to_device_id" in segment, "Segment must have to_device_id"
        assert "attenuation_db" in segment, "Segment must have attenuation_db"
        assert segment["attenuation_db"] >= 0, "Attenuation must be non-negative"

    # Performance target check
    assert elapsed_ms < 50, f"Performance target missed: {elapsed_ms:.2f} ms > 50 ms"

    print(
        f"✅ Path resolved: {len(segments)} segments, {total_attenuation:.2f} dB total attenuation"
    )


def test_go_algorithm_no_path(optical_client, setup_isolated_ont):
    """Test Go PathFinder with isolated ONT (no path to OLT)."""
    isolated_ont_id = setup_isolated_ont

    result = optical_client.get_path(ont_id=isolated_ont_id)

    # Should return path_exists=False for isolated ONT
    assert isinstance(result, dict), "Result must be dict"
    assert result.get("backend") == "go", "Should use Go implementation"
    assert result.get("path_exists") is False, "Isolated ONT should have no path"
    assert result.get("ont_id") == isolated_ont_id, "ONT ID must match"
    assert result.get("segments", []) == [], "No segments for isolated ONT"

    print(f"✅ Correctly detected no path for isolated ONT: {isolated_ont_id}")


def test_go_algorithm_multiple_paths(optical_client, setup_multiple_paths):
    """Test Go PathFinder selects shortest path when multiple paths exist."""
    topo = setup_multiple_paths

    result = optical_client.get_path(ont_id=topo["ont_id"])

    # Validate response
    assert isinstance(result, dict), "Result must be dict"
    assert result.get("backend") == "go", "Should use Go implementation"
    assert result.get("path_exists") is True, "Path should exist"
    assert result.get("olt_id") == topo["olt_id"], f"OLT ID must be {topo['olt_id']}"

    # Validate shortest path was selected (attenuation-based)
    total_attenuation = result.get("total_attenuation_db", 999.0)
    expected = topo["expected_attenuation_db"]
    tolerance = 0.1
    assert (
        abs(total_attenuation - expected) <= tolerance
    ), f"Should select shortest path: got {total_attenuation:.2f} dB, expected {expected:.2f} dB"

    # Validate path goes through correct splitter (lower insertion loss)
    segments = result.get("segments", [])
    assert len(segments) > 0, "Must have segments"

    # Check if path goes through splitter A (8dB, lower loss)
    devices_in_path = set()
    for segment in segments:
        devices_in_path.add(segment["from_device_id"])
        devices_in_path.add(segment["to_device_id"])

    assert (
        topo["expected_via"] in devices_in_path
    ), f"Path should go through {topo['expected_via']} (lower insertion loss)"

    print(
        f"✅ Correctly selected shortest path: {total_attenuation:.2f} dB via {topo['expected_via']}"
    )


def test_go_algorithm_nonexistent_ont(optical_client):
    """Test Go PathFinder with nonexistent ONT ID."""
    result = optical_client.get_path(ont_id="nonexistent_ont_999999")

    # Should return path_exists=False for nonexistent ONT
    assert isinstance(result, dict), "Result must be dict"
    assert result.get("path_exists") is False, "Nonexistent ONT should have no path"
    assert result.get("ont_id") == "nonexistent_ont_999999", "ONT ID must match"


def test_go_algorithm_performance_baseline(optical_client, setup_optical_topology):
    """Benchmark Go PathFinder performance over 10 iterations.

    Target: <50ms per ONT (Python baseline: 40s = 800× speedup)
    """
    topo = setup_optical_topology
    iterations = 10

    elapsed_times = []
    for i in range(iterations):
        start_time = time.perf_counter()
        result = optical_client.get_path(ont_id=topo["ont_id"])
        elapsed_ms = (time.perf_counter() - start_time) * 1000
        elapsed_times.append(elapsed_ms)

        # Sanity check each iteration
        assert result.get("path_exists") is True, f"Iteration {i+1}: Path should exist"

    # Calculate statistics
    avg_time = sum(elapsed_times) / len(elapsed_times)
    min_time = min(elapsed_times)
    max_time = max(elapsed_times)

    print(f"\n📊 Go PathFinder Performance ({iterations} iterations):")
    print(f"  Average: {avg_time:.2f} ms")
    print(f"  Min:     {min_time:.2f} ms")
    print(f"  Max:     {max_time:.2f} ms")
    print("  Target:  <50 ms")

    # Performance assertions
    assert avg_time < 50, f"Average performance target missed: {avg_time:.2f} ms > 50 ms"
    assert max_time < 100, f"Worst case too slow: {max_time:.2f} ms > 100 ms"

    print(f"✅ Performance target met: {avg_time:.2f} ms average (target: <50ms)")
