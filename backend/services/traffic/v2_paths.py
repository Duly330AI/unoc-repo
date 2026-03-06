from __future__ import annotations

from collections.abc import Sequence

from sqlmodel import Session

from backend.models import Interface, Link
from backend.services.pathfinding import DeviceRecord, LinkRecord, build_optical_graph


def infer_paths_for_leaf(
    leaf_id: str,
    g,  # networkx Graph/MultiGraph
    link_rows_all: Sequence[Link],
    iface_to_device: dict[str, str],
    s: Session,
    d_recs: Sequence[DeviceRecord],
    l_recs: Sequence[LinkRecord],
) -> tuple[Interface | None, set[str], set[str]]:
    union_devices: set[str] = {leaf_id}
    union_links: set[str] = set()
    peer_iface: Interface | None = None

    try:
        import networkx as _nx  # local import

        def _edge_attr_dicts(u: str, v: str) -> list[dict]:
            ed = g.get_edge_data(u, v) or {}
            if isinstance(ed, dict) and ("id" in ed or "synthetic" in ed):
                return [ed]
            if isinstance(ed, dict):
                return [val for val in ed.values() if isinstance(val, dict)]
            return []

        added_links_for_leaf: set[str] = set()
        if g.has_node(leaf_id):
            for nbr in g.neighbors(leaf_id):
                attrs = _edge_attr_dicts(leaf_id, nbr)
                for edata in attrs:
                    if edata.get("synthetic") is True:
                        continue
                    lid = edata.get("id")
                    if isinstance(lid, str):
                        union_links.add(lid)
                        added_links_for_leaf.add(lid)
                        for _row in link_rows_all:
                            if _row.id == lid:
                                if (_row.a_interface_id in iface_to_device) and (
                                    iface_to_device[_row.a_interface_id] == leaf_id
                                ):
                                    peer_iface = s.get(Interface, _row.b_interface_id)
                                elif (_row.b_interface_id in iface_to_device) and (
                                    iface_to_device[_row.b_interface_id] == leaf_id
                                ):
                                    peer_iface = s.get(Interface, _row.a_interface_id)
                                break
                        break
                if added_links_for_leaf:
                    break
    except Exception:
        pass

    try:
        import networkx as _nx  # local import

        if g is not None and g.has_node(leaf_id):
            anchors = [
                n
                for n, data in g.nodes(data=True)
                if data.get("type") in {"BACKBONE_GATEWAY", "CORE_ROUTER"}
            ]
            if not anchors:
                anchors = [
                    n
                    for n, data in g.nodes(data=True)
                    if data.get("type") not in {"ONT", "BUSINESS_ONT", "AON_CPE"} and n != leaf_id
                ]

            def _path_real_only(source: str, target: str) -> list[str] | None:
                real_edges = [
                    (u, v) for u, v, ed in g.edges(data=True) if not bool(ed.get("synthetic"))
                ]
                if not real_edges:
                    return None
                g_real = _nx.Graph()
                g_real.add_nodes_from(g.nodes(data=True))
                g_real.add_edges_from(real_edges)
                try:
                    path = _nx.shortest_path(g_real, source=source, target=target)
                    return list(path)
                except (_nx.NetworkXNoPath, _nx.NodeNotFound):
                    return None

            def _path_weighted(source: str, target: str) -> list[str] | None:
                def _w(__u: str, __v: str, _edge_attr: dict) -> float:
                    return 10.0 if bool(_edge_attr.get("synthetic")) else 1.0

                def _weight(__a: str, __b: str, _edge_attr: dict) -> float:
                    return _w(__a, __b, _edge_attr)

                try:
                    path = _nx.shortest_path(g, source=source, target=target, weight=_weight)
                    return list(path)
                except (_nx.NetworkXNoPath, _nx.NodeNotFound):
                    return None

            best_path: list[str] | None = None
            best_cost: tuple[int, int] | None = None
            for a in anchors:
                p = _path_real_only(leaf_id, a)
                if p is None:
                    p = _path_weighted(leaf_id, a)
                if p is None:
                    continue
                syn_count = 0
                for u, v in zip(p[:-1], p[1:], strict=True):
                    ed = g.get_edge_data(u, v) or {}
                    if bool(ed.get("synthetic")):
                        syn_count += 1
                cost = (syn_count, len(p))
                if best_cost is None or cost < best_cost:
                    best_cost = cost
                    best_path = p

            if not best_path:
                try:
                    g_opt = build_optical_graph(list(d_recs), list(l_recs))
                except Exception:
                    g_opt = None
                origin_id = None
                if g_opt is not None and g_opt.has_node(leaf_id):
                    try:
                        candidates = [
                            n for n, data in g_opt.nodes(data=True) if data.get("type") == "OLT"
                        ]
                        best_o: str | None = None
                        best_len2: int | None = None
                        for o in candidates:
                            try:
                                p2 = _nx.shortest_path(g_opt, source=leaf_id, target=o)
                            except (_nx.NetworkXNoPath, _nx.NodeNotFound):
                                continue
                            plen2 = len(p2)
                            if best_len2 is None or plen2 < best_len2:
                                best_len2 = plen2
                                best_o = o
                        origin_id = best_o
                    except Exception:
                        origin_id = None
                if origin_id:
                    best_cost = None
                    best_path = None
                    for a in anchors:
                        p = _path_real_only(origin_id, a)
                        if p is None:
                            p = _path_weighted(origin_id, a)
                        if p is None:
                            continue
                        syn_count = 0
                        for u, v in zip(p[:-1], p[1:], strict=True):
                            ed = g.get_edge_data(u, v) or {}
                            if bool(ed.get("synthetic")):
                                syn_count += 1
                        cost = (syn_count, len(p))
                        if best_cost is None or cost < best_cost:
                            best_cost = cost
                            best_path = p

            if best_path and len(best_path) >= 2:
                for node in best_path:
                    union_devices.add(node)

                def _edge_attr_dicts(u: str, v: str) -> list[dict]:
                    ed = g.get_edge_data(u, v) or {}
                    if isinstance(ed, dict) and ("id" in ed or "synthetic" in ed):
                        return [ed]
                    if isinstance(ed, dict):
                        return [val for val in ed.values() if isinstance(val, dict)]
                    return []

                for u, v in zip(best_path[:-1], best_path[1:], strict=True):
                    attrs = _edge_attr_dicts(u, v)
                    for edata in attrs:
                        if edata.get("synthetic") is True:
                            continue
                        lid = edata.get("id")
                        if isinstance(lid, str):
                            union_links.add(lid)
                            break
    except Exception:
        pass

    return peer_iface, union_devices, union_links
