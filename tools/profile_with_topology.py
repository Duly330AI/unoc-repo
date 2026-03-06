"""Profile traffic tick and status recompute with realistic topology.

Creates topology, then profiles operations to find CPU hotspots.

Usage:
    python tools/profile_with_topology.py --devices 200 --ticks 5
"""

import argparse
import cProfile
import pstats
import sys
from io import StringIO

sys.path.insert(0, ".")

from backend.db import get_session, init_db
from backend.models import Device, Interface, Link
from backend.services.status_service import recompute_dirty
from backend.services.traffic.v2_engine import TrafficEngine


def create_topology(device_count: int):
    """Create realistic network topology."""
    print(f"Creating topology: {device_count} devices...")

    s = get_session()

    # Calculate device distribution
    backbone_count = 1
    core_count = 2
    edge_count = max(10, device_count // 20)
    aon_count = max(50, device_count // 4)
    endpoint_count = device_count - backbone_count - core_count - edge_count - aon_count
    ont_count = endpoint_count // 2
    cpe_count = endpoint_count - ont_count

    print(
        f"  Distribution: {backbone_count} backbone, {core_count} cores, {edge_count} edges, {aon_count} switches, {ont_count} ONTs, {cpe_count} CPE"
    )

    from backend.catalog import CATALOG_SINGLETON

    cat = CATALOG_SINGLETON

    # Get hardware models
    backbone_hw = next(hw for hw in cat.hardware_models if hw.purpose == "BACKBONE_GATEWAY")
    core_hw = next(hw for hw in cat.hardware_models if hw.purpose == "CORE_ROUTER")
    edge_hw = next(hw for hw in cat.hardware_models if hw.purpose == "EDGE_ROUTER")
    aon_hw = next(hw for hw in cat.hardware_models if hw.purpose == "AON_SWITCH")
    ont_hw = next(hw for hw in cat.hardware_models if hw.purpose == "ONT")
    cpe_hw = next(hw for hw in cat.hardware_models if hw.purpose == "CPE")

    # Get default tariff
    default_tariff = next(t for t in cat.tariffs if t.name == "default")

    all_devices = []

    # Create devices
    dev_id = 1

    # Backbone
    for i in range(backbone_count):
        dev = Device(
            id=f"dev{dev_id:04d}",
            name=f"Backbone-GW-{i+1}",
            hardware_model_id=backbone_hw.id,
            tariff_id=default_tariff.id,
        )
        all_devices.append(dev)
        s.add(dev)
        dev_id += 1

    # Cores
    core_devices = []
    for i in range(core_count):
        dev = Device(
            id=f"dev{dev_id:04d}",
            name=f"Core-Router-{i+1}",
            hardware_model_id=core_hw.id,
            tariff_id=default_tariff.id,
        )
        core_devices.append(dev)
        all_devices.append(dev)
        s.add(dev)
        dev_id += 1

    # Edges
    edge_devices = []
    for i in range(edge_count):
        dev = Device(
            id=f"dev{dev_id:04d}",
            name=f"Edge-Router-{i+1}",
            hardware_model_id=edge_hw.id,
            tariff_id=default_tariff.id,
        )
        edge_devices.append(dev)
        all_devices.append(dev)
        s.add(dev)
        dev_id += 1

    # AON Switches
    aon_devices = []
    for i in range(aon_count):
        dev = Device(
            id=f"dev{dev_id:04d}",
            name=f"AON-Switch-{i+1}",
            hardware_model_id=aon_hw.id,
            tariff_id=default_tariff.id,
        )
        aon_devices.append(dev)
        all_devices.append(dev)
        s.add(dev)
        dev_id += 1

    # ONTs
    ont_devices = []
    for i in range(ont_count):
        dev = Device(
            id=f"dev{dev_id:04d}",
            name=f"ONT-{i+1}",
            hardware_model_id=ont_hw.id,
            tariff_id=default_tariff.id,
        )
        ont_devices.append(dev)
        all_devices.append(dev)
        s.add(dev)
        dev_id += 1

    # CPE
    for i in range(cpe_count):
        dev = Device(
            id=f"dev{dev_id:04d}",
            name=f"CPE-{i+1}",
            hardware_model_id=cpe_hw.id,
            tariff_id=default_tariff.id,
        )
        all_devices.append(dev)
        s.add(dev)
        dev_id += 1

    s.commit()

    # Create interfaces (2 per device)
    interfaces = []
    for dev in all_devices:
        for port_num in range(2):
            iface = Interface(
                id=f"{dev.id}-p{port_num}",
                device_id=dev.id,
                name=f"port{port_num}",
                port_number=port_num,
            )
            interfaces.append(iface)

    s.bulk_save_objects(interfaces)
    s.commit()

    # Create links (hierarchical)
    links = []
    link_id = 1

    # Backbone to cores
    backbone = all_devices[0]
    for core in core_devices:
        links.append(
            Link(
                id=f"link{link_id:04d}",
                a_interface_id=f"{backbone.id}-p0",
                b_interface_id=f"{core.id}-p0",
            )
        )
        link_id += 1

    # Cores to edges
    edges_per_core = len(edge_devices) // len(core_devices)
    for i, core in enumerate(core_devices):
        start_idx = i * edges_per_core
        end_idx = start_idx + edges_per_core if i < len(core_devices) - 1 else len(edge_devices)
        for edge in edge_devices[start_idx:end_idx]:
            links.append(
                Link(
                    id=f"link{link_id:04d}",
                    a_interface_id=f"{core.id}-p1",
                    b_interface_id=f"{edge.id}-p0",
                )
            )
            link_id += 1

    # Edges to AON switches
    switches_per_edge = len(aon_devices) // len(edge_devices)
    for i, edge in enumerate(edge_devices):
        start_idx = i * switches_per_edge
        end_idx = start_idx + switches_per_edge if i < len(edge_devices) - 1 else len(aon_devices)
        for aon in aon_devices[start_idx:end_idx]:
            links.append(
                Link(
                    id=f"link{link_id:04d}",
                    a_interface_id=f"{edge.id}-p1",
                    b_interface_id=f"{aon.id}-p0",
                )
            )
            link_id += 1

    # AON switches to ONTs
    onts_per_switch = len(ont_devices) // len(aon_devices)
    for i, aon in enumerate(aon_devices):
        start_idx = i * onts_per_switch
        end_idx = start_idx + onts_per_switch if i < len(aon_devices) - 1 else len(ont_devices)
        for ont in ont_devices[start_idx:end_idx]:
            links.append(
                Link(
                    id=f"link{link_id:04d}",
                    a_interface_id=f"{aon.id}-p1",
                    b_interface_id=f"{ont.id}-p0",
                )
            )
            link_id += 1

    s.bulk_save_objects(links)
    s.commit()
    s.close()

    print(f"✅ Topology created: {len(all_devices)} devices, {len(links)} links")


def profile_traffic_tick(ticks: int, output_file: str):
    """Profile traffic engine tick."""
    print(f"\nProfiling {ticks} traffic ticks...")

    engine = TrafficEngine()

    profiler = cProfile.Profile()
    profiler.enable()

    for _ in range(ticks):
        engine.run_tick()

    profiler.disable()

    # Save binary stats
    profiler.dump_stats(output_file)
    print(f"✅ Binary stats saved to: {output_file}")

    # Generate human-readable report
    s = StringIO()
    ps = pstats.Stats(profiler, stream=s)
    ps.strip_dirs()
    ps.sort_stats("cumulative")
    ps.print_stats(50)  # Top 50 functions

    txt_file = output_file.replace(".stats", ".txt")
    with open(txt_file, "w") as f:
        f.write(s.getvalue())
    print(f"✅ Human-readable report saved to: {txt_file}")

    # Print top 20 to console
    print("\n" + "=" * 80)
    print("TOP 20 CPU HOTSPOTS (by cumulative time)")
    print("=" * 80)
    ps.print_stats(20)


def profile_status_recompute(output_file: str):
    """Profile status recompute."""
    print("\nProfiling status recompute (50 devices)...")

    s = get_session()
    from sqlmodel import select

    # Get 50 random devices
    devices = s.exec(select(Device).limit(50)).all()
    device_ids = [d.id for d in devices]
    s.close()

    profiler = cProfile.Profile()
    profiler.enable()

    s = get_session()
    recompute_dirty(s, device_ids)
    s.close()

    profiler.disable()

    # Save binary stats
    profiler.dump_stats(output_file)
    print(f"✅ Binary stats saved to: {output_file}")

    # Generate human-readable report
    s = StringIO()
    ps = pstats.Stats(profiler, stream=s)
    ps.strip_dirs()
    ps.sort_stats("cumulative")
    ps.print_stats(50)  # Top 50 functions

    txt_file = output_file.replace(".stats", ".txt")
    with open(txt_file, "w") as f:
        f.write(s.getvalue())
    print(f"✅ Human-readable report saved to: {txt_file}")

    # Print top 20 to console
    print("\n" + "=" * 80)
    print("TOP 20 CPU HOTSPOTS (by cumulative time)")
    print("=" * 80)
    ps.print_stats(20)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--devices", type=int, default=200, help="Number of devices")
    parser.add_argument("--ticks", type=int, default=5, help="Number of traffic ticks to profile")
    parser.add_argument(
        "--profile-status", action="store_true", help="Also profile status recompute"
    )
    args = parser.parse_args()

    init_db()

    # Create topology
    create_topology(args.devices)

    # Profile traffic tick
    profile_traffic_tick(args.ticks, f"traffic_profile_{args.devices}dev.stats")

    # Optionally profile status
    if args.profile_status:
        profile_status_recompute(f"status_profile_{args.devices}dev.stats")

    print("\n" + "=" * 80)
    print("✅ PROFILING COMPLETE")
    print("=" * 80)
    print(f"Topology: {args.devices} devices")
    print(f"Traffic ticks profiled: {args.ticks}")
    if args.profile_status:
        print("Status recompute profiled: 50 devices")


if __name__ == "__main__":
    main()
