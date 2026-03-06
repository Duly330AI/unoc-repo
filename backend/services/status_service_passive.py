from __future__ import annotations

from sqlmodel import select

from backend.db import get_session
from backend.models import Device, DeviceType, Interface, Link, Status
from backend.services.dependency_resolver import has_upstream_l3_or_anchor


def eval_passive_status(device: Device) -> Status:
    """Evaluate PASSIVE device effective status using local topology context.

    Rules:
    - Isolation (<2 neighbors) -> DOWN
    - Require at least one upstream ACTIVE candidate with L3 reachability (directly or via passive chain)
    - Require at least one downstream terminator (ONT/BUSINESS_ONT/AON_CPE) reachable via passive chain
    """
    try:
        with get_session() as s:
            if_rows = s.exec(select(Interface).where(Interface.device_id == device.id)).all()
            if_ids = {i.id for i in if_rows}
            link_rows = s.exec(select(Link)).all()
            neighbors: set[str] = set()
            for ln in link_rows:
                involved = (ln.a_interface_id in if_ids) or (ln.b_interface_id in if_ids)
                if not involved:
                    continue
                other_if_id = (
                    ln.b_interface_id if ln.a_interface_id in if_ids else ln.a_interface_id
                )
                other_if = s.get(Interface, other_if_id)
                if other_if:
                    neighbors.add(other_if.device_id)
            if len(neighbors) < 2:
                return Status.DOWN
            upstream_candidates: list[Device] = []
            downstream_terms: list[Device] = []
            passive_neighbors: list[Device] = []
            for nd in neighbors:
                drow = s.get(Device, nd)
                if not drow:
                    continue
                if drow.type in {
                    DeviceType.OLT,
                    DeviceType.AON_SWITCH,
                    DeviceType.CORE_ROUTER,
                    DeviceType.EDGE_ROUTER,
                }:
                    upstream_candidates.append(drow)
                elif drow.type in {DeviceType.ONT, DeviceType.BUSINESS_ONT, DeviceType.AON_CPE}:
                    downstream_terms.append(drow)
                elif drow.type in {
                    DeviceType.ODF,
                    DeviceType.NVT,
                    DeviceType.SPLITTER,
                    DeviceType.HOP,
                }:
                    passive_neighbors.append(drow)
            chain_has_upstream = False
            checked: set[str] = set()
            stack: list[Device] = list(upstream_candidates) + passive_neighbors
            while stack and not chain_has_upstream:
                cur = stack.pop()
                if cur.id in checked:
                    continue
                checked.add(cur.id)
                if cur in upstream_candidates:
                    res = has_upstream_l3_or_anchor(s, cur)
                    if res.ok:
                        chain_has_upstream = True
                        break
                cur_if_rows = s.exec(select(Interface).where(Interface.device_id == cur.id)).all()
                cur_if_ids = {i.id for i in cur_if_rows}
                for ln in link_rows:
                    if not (ln.a_interface_id in cur_if_ids or ln.b_interface_id in cur_if_ids):
                        continue
                    other_if_id = (
                        ln.b_interface_id if ln.a_interface_id in cur_if_ids else ln.a_interface_id
                    )
                    other_if = s.get(Interface, other_if_id)
                    if not other_if:
                        continue
                    other_dev = s.get(Device, other_if.device_id)
                    if not other_dev or other_dev.id in checked:
                        continue
                    if other_dev.type in {
                        DeviceType.ODF,
                        DeviceType.NVT,
                        DeviceType.SPLITTER,
                        DeviceType.HOP,
                    }:
                        stack.append(other_dev)
                    elif other_dev.type in {
                        DeviceType.OLT,
                        DeviceType.AON_SWITCH,
                        DeviceType.CORE_ROUTER,
                        DeviceType.EDGE_ROUTER,
                    }:
                        res2 = has_upstream_l3_or_anchor(s, other_dev)
                        if res2.ok:
                            chain_has_upstream = True
                            break
            if not chain_has_upstream:
                return Status.DOWN
            has_terminator = bool(downstream_terms)
            if not has_terminator:
                visited_passive: set[str] = set()
                queue: list[Device] = list(passive_neighbors)
                while queue and not has_terminator:
                    cur = queue.pop(0)
                    if cur.id in visited_passive:
                        continue
                    visited_passive.add(cur.id)
                    cur_if_rows = s.exec(
                        select(Interface).where(Interface.device_id == cur.id)
                    ).all()
                    cur_if_ids = {i.id for i in cur_if_rows}
                    for ln in link_rows:
                        if not (ln.a_interface_id in cur_if_ids or ln.b_interface_id in cur_if_ids):
                            continue
                        other_if_id = (
                            ln.b_interface_id
                            if ln.a_interface_id in cur_if_ids
                            else ln.a_interface_id
                        )
                        other_if = s.get(Interface, other_if_id)
                        if not other_if:
                            continue
                        other_dev = s.get(Device, other_if.device_id)
                        if not other_dev:
                            continue
                        if other_dev.type in {
                            DeviceType.ONT,
                            DeviceType.BUSINESS_ONT,
                            DeviceType.AON_CPE,
                        }:
                            has_terminator = True
                            break
                        if (
                            other_dev.type
                            in {DeviceType.ODF, DeviceType.NVT, DeviceType.SPLITTER, DeviceType.HOP}
                            and other_dev.id not in visited_passive
                        ):
                            queue.append(other_dev)
            if not has_terminator:
                return Status.DOWN
            return Status.UP
    except Exception:
        return Status.DEGRADED
