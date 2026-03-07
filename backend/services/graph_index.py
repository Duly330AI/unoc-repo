from __future__ import annotations

from dataclasses import dataclass, field

from sqlmodel import select

from backend.db import get_session, init_db
from backend.models import Device, Interface, Link


@dataclass(frozen=True)
class Change:
    devices_added: set[str] = field(default_factory=set)
    devices_updated: set[str] = field(default_factory=set)
    devices_moved: set[str] = field(default_factory=set)
    links_added: set[str] = field(default_factory=set)
    links_updated: set[str] = field(default_factory=set)
    links_deleted: set[str] = field(default_factory=set)
    overrides_changed: set[str] = field(default_factory=set)  # device or link ids


@dataclass
class DirtySet:
    devices: set[str] = field(default_factory=set)
    links: set[str] = field(default_factory=set)
    region_id: str | None = None


class RegionVersionMap:
    """Simple region version tracker.

    A region represents a connected component in the device adjacency graph.
    """

    def __init__(self) -> None:
        self._versions: dict[str, int] = {}

    def version(self, region_id: str) -> int:
        return self._versions.get(region_id, 0)

    def bump(self, region_id: str) -> int:
        cur = self._versions.get(region_id, 0) + 1
        self._versions[region_id] = cur
        return cur


class GraphIndex:
    """Adjacency/indexes for devices/interfaces/links with region detection."""

    def __init__(self) -> None:
        # Maps
        self.device_by_iface: dict[str, str] = {}
        self.link_endpoints: dict[str, tuple[str, str]] = {}
        self.links_by_device: dict[str, set[str]] = {}
        self.device_neighbors: dict[str, set[str]] = {}
        self._region_of_device: dict[str, str] = {}

    def build(self) -> None:
        """Rebuild the index from the database."""
        init_db()
        self.device_by_iface.clear()
        self.link_endpoints.clear()
        self.links_by_device.clear()
        self.device_neighbors.clear()
        self._region_of_device.clear()

        with get_session() as s:
            # Interfaces: map iface -> device
            for iface in s.exec(select(Interface)).all():
                self.device_by_iface[iface.id] = iface.device_id

            # Links: endpoints and per-device link sets
            for ln in s.exec(select(Link)).all():
                a_dev = self.device_by_iface.get(ln.a_interface_id)
                b_dev = self.device_by_iface.get(ln.b_interface_id)
                if not a_dev or not b_dev:
                    continue
                self.link_endpoints[ln.id] = (a_dev, b_dev)
                self.links_by_device.setdefault(a_dev, set()).add(ln.id)
                self.links_by_device.setdefault(b_dev, set()).add(ln.id)
                # undirected device adjacency
                self.device_neighbors.setdefault(a_dev, set()).add(b_dev)
                self.device_neighbors.setdefault(b_dev, set()).add(a_dev)

            # Ensure every device appears at least once in maps
            for dev in s.exec(select(Device)).all():
                self.links_by_device.setdefault(dev.id, set())
                self.device_neighbors.setdefault(dev.id, set())

        # Compute connected components for region ids
        self._compute_regions()

    def _compute_regions(self) -> None:
        visited: set[str] = set()
        for dev in sorted(self.device_neighbors.keys()):  # deterministic order
            if dev in visited:
                continue
            # BFS
            queue = [dev]
            component: list[str] = []
            visited.add(dev)
            while queue:
                d = queue.pop(0)
                component.append(d)
                for n in sorted(self.device_neighbors.get(d, set())):
                    if n not in visited:
                        visited.add(n)
                        queue.append(n)
            # Deterministic region id: join of sorted device ids hash-like
            region_id = f"r:{component[0]}:{len(component)}"
            for d in component:
                self._region_of_device[d] = region_id

    # ---- Public API ----

    def neighbors_device(self, device_id: str) -> set[str]:
        return set(self.device_neighbors.get(device_id, set()))

    def neighbors_link(self, link_id: str) -> set[str]:
        a_b = self.link_endpoints.get(link_id)
        return set(a_b) if a_b else set()

    def region_id_of_device(self, device_id: str) -> str:
        return self._region_of_device.get(device_id, f"r:{device_id}:1")

    def affected_region_for_devices(self, dev_ids: set[str]) -> str:
        # Pick the first device's region (assuming changes are local); if mixed, choose smallest id
        if not dev_ids:
            return "r:unknown:0"
        cand = sorted(dev_ids)[0]
        return self.region_id_of_device(cand)

    def dirty_set_for_change(self, change: Change) -> DirtySet:
        """Compute a conservative dirty set for a change.

        Strategy: include directly changed devices plus their neighbors; for links,
        include both endpoint devices and the link ids.
        """
        devices: set[str] = set()
        links: set[str] = set()

        # Device changes
        for did in (
            set(change.devices_added)
            | set(change.devices_updated)
            | set(change.devices_moved)
            | {i for i in change.overrides_changed if i in self.device_neighbors}
        ):
            devices.add(did)
            devices |= self.neighbors_device(did)

        # Link changes
        for lid in set(change.links_added) | set(change.links_updated) | set(change.links_deleted):
            links.add(lid)
            for d in self.neighbors_link(lid):
                devices.add(d)
                devices |= self.neighbors_device(d)

        region_id = self.affected_region_for_devices(devices)
        return DirtySet(devices=devices, links=links, region_id=region_id)
