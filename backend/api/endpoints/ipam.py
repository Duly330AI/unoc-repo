import ipaddress
import os
from typing import Any, cast

from fastapi import APIRouter, HTTPException
from sqlmodel import select

from backend.db import get_session, init_db
from backend.models import VRF, InterfaceAddress, Prefix
from backend.services.seed_service import ensure_ipam_defaults

router = APIRouter(tags=["ipam"], prefix="/ipam")


def _prefix_pool_stats(prefix: Prefix, allocated_count: int, next_index: int = 1) -> dict[str, Any]:
    """Build pool row for a management Prefix.

    - pool_key: derived from Prefix.description if present, else prefix string
    - cidr: Prefix.prefix
    - next_index: kept for UI compatibility (legacy), default 1
    - allocated_count: live DB count of InterfaceAddress bound to this Prefix
    - capacity/utilization derived from CIDR host count
    """
    try:
        net = ipaddress.ip_network(prefix.prefix)
        hosts = list(net.hosts())
        cap = len(hosts)
        alloc = min(allocated_count, cap)
        return {
            "pool_key": prefix.description or prefix.prefix,
            "cidr": prefix.prefix,
            "next_index": next_index,
            "allocated_count": alloc,
            "capacity": cap,
            "utilization": round(alloc / cap, 4) if cap else 0.0,
        }
    except Exception as e:  # pragma: no cover - defensive
        raise HTTPException(status_code=500, detail=f"Invalid prefix {prefix.prefix}: {e}") from e


@router.get("/pools", response_model=list[dict])
def list_pools():  # simple dict shape for now
    """Return live IPAM pool stats derived from management Prefixes.

    This replaces legacy IPPool.next_index estimation. Management pools are
    represented by Prefix rows in VRF "mgmt" with description in:
        {core_mgmt, olt_mgmt, aon_mgmt, ont_mgmt, cpe_mgmt, noc_tools}
    """
    init_db()
    with get_session() as s:
        try:
            # Ensure base mgmt VRF and management prefixes exist for dev/demo convenience
            if os.getenv("UNOC_DEV_FEATURES"):
                try:
                    ensure_ipam_defaults(s)
                except Exception:
                    # Non-fatal: continue without seeding
                    pass

            # Locate mgmt VRF
            mgmt = s.exec(select(VRF).where(VRF.name == "mgmt")).first()
            if not mgmt:
                return []

            roles = {"core_mgmt", "olt_mgmt", "aon_mgmt", "ont_mgmt", "cpe_mgmt", "noc_tools"}
            # Cast for type-checker to allow SQLAlchemy in_ on column
            desc_in_roles = cast(Any, Prefix.description).in_(roles)
            prefixes = s.exec(
                select(Prefix).where((Prefix.vrf_id == mgmt.id) & desc_in_roles)
            ).all()
            if not prefixes:
                return []

            # Count InterfaceAddress by prefix_id in a single pass
            ids = [cast(int, p.id) for p in prefixes if p.id is not None]
            alloc_map: dict[int, int] = {pid: 0 for pid in ids}
            if ids:
                pid_in_ids = cast(Any, InterfaceAddress.prefix_id).in_(ids)
                addr_rows = s.exec(select(InterfaceAddress.prefix_id).where(pid_in_ids)).all()
                # Selecting a single column yields a list of values
                for pid in addr_rows:
                    if pid is not None:
                        alloc_map[int(pid)] = alloc_map.get(int(pid), 0) + 1

            out: list[dict[str, Any]] = []
            for p in prefixes:
                pid = cast(int, p.id)
                out.append(
                    _prefix_pool_stats(p, allocated_count=alloc_map.get(pid, 0), next_index=1)
                )
            # Sort by pool_key for stable UI
            out.sort(key=lambda r: str(r.get("pool_key")))
            return out
        except HTTPException:
            # bubble up intentional errors
            raise
        except Exception as e:
            # Defensive: return structured 500 instead of crashing
            raise HTTPException(status_code=500, detail=f"IPAM_ERROR: {e}") from e
