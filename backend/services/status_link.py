from __future__ import annotations

from backend.models import Device, Interface, Link, Status


def evaluate_link_status(link: Link) -> Status:
    """Return the effective link status based on admin overrides and endpoints.

    Rules (in order):
    - Admin override on the link wins if set (UP/DOWN/BLOCKING as forced).
    - Otherwise, check only ADMIN OVERRIDE of the endpoint devices; if either endpoint
      device is explicitly overridden DOWN, the link is DOWN.
    - If neither endpoint is forced DOWN, return the stored logical status of the link.
    """
    try:
        from sqlmodel import select as _select

        from backend.db import get_session

        with get_session() as s:
            raw = getattr(link, "__dict__", {}) or {}
            link_id = raw.get("id")
            a_if_id = raw.get("a_interface_id")
            b_if_id = raw.get("b_interface_id")

            ln = s.get(Link, link_id) if link_id else None
            if ln is None and a_if_id and b_if_id:
                ln = s.exec(
                    _select(Link).where(
                        (Link.a_interface_id == a_if_id) & (Link.b_interface_id == b_if_id)
                    )
                ).first()
                if ln is None:
                    ln = s.exec(
                        _select(Link).where(
                            (Link.a_interface_id == b_if_id) & (Link.b_interface_id == a_if_id)
                        )
                    ).first()
            if ln is None:
                rows = s.exec(_select(Link)).all()
                if len(rows) == 1:
                    ln = rows[0]
            if ln is None:
                return Status.UP

            result: Status = ln.status
            if getattr(ln, "admin_override_status", None) is not None:
                return ln.admin_override_status or result  # type: ignore[return-value]
            a_if = s.get(Interface, ln.a_interface_id)
            b_if = s.get(Interface, ln.b_interface_id)
            if not a_if or not b_if:
                return result
            a_dev = s.get(Device, a_if.device_id)
            b_dev = s.get(Device, b_if.device_id)
            if not a_dev or not b_dev:
                return result
            a_val = getattr(a_dev, "admin_override_status", None)
            b_val = getattr(b_dev, "admin_override_status", None)
            a_forced_down = (a_val is not None and str(a_val) == "DOWN") or (
                a_val is not None and hasattr(a_val, "value") and a_val.value == "DOWN"
            )
            b_forced_down = (b_val is not None and str(b_val) == "DOWN") or (
                b_val is not None and hasattr(b_val, "value") and b_val.value == "DOWN"
            )
            if a_forced_down or b_forced_down:
                result = Status.DOWN
            return result
    except Exception:
        return Status.UP


def is_link_passable(link: Link) -> bool:
    """Return True if traversal across link is allowed now (override + liveness)."""
    try:
        # If link has admin override -> only UP is passable
        if getattr(link, "admin_override_status", None) is None:
            try:
                from backend.db import get_session

                raw = getattr(link, "__dict__", {}) or {}
                link_id = raw.get("id")
                if link_id:
                    with get_session() as _s:
                        _ln = _s.get(Link, link_id)
                        if (
                            _ln is not None
                            and getattr(_ln, "admin_override_status", None) is not None
                        ):
                            _lov = getattr(_ln, "admin_override_status", None)
                            _lov_down = (_lov is not None and str(_lov) == "DOWN") or (
                                _lov is not None and hasattr(_lov, "value") and _lov.value == "DOWN"
                            )
                            if _lov_down:
                                return False
                            _lov_up = (_lov is not None and str(_lov) == "UP") or (
                                _lov is not None and hasattr(_lov, "value") and _lov.value == "UP"
                            )
                            if _lov_up:
                                return True
            except Exception:
                pass
        if getattr(link, "admin_override_status", None) is not None:
            lov = getattr(link, "admin_override_status", None)
            lov_up = (lov is not None and str(lov) == "UP") or (
                lov is not None and hasattr(lov, "value") and lov.value == "UP"
            )
            return bool(lov_up)

        stv = getattr(link, "status", None)
        if not (
            (stv is not None and str(stv) == "UP")
            or (stv is not None and hasattr(stv, "value") and stv.value == "UP")
        ):
            return False

        from backend.db import get_session

        with get_session() as s:
            raw = getattr(link, "__dict__", {}) or {}
            link_id = raw.get("id")
            ln = s.get(Link, link_id) if link_id else None
            if ln is None:
                ln = link
            a_if = s.get(Interface, ln.a_interface_id)
            b_if = s.get(Interface, ln.b_interface_id)
            if not a_if or not b_if:
                return False
            a_dev = s.get(Device, a_if.device_id)
            b_dev = s.get(Device, b_if.device_id)
            if not a_dev or not b_dev:
                return False
            aov = getattr(a_dev, "admin_override_status", None)
            if (aov is not None and str(aov) == "DOWN") or (
                aov is not None and hasattr(aov, "value") and aov.value == "DOWN"
            ):
                return False
            bov = getattr(b_dev, "admin_override_status", None)
            if (bov is not None and str(bov) == "DOWN") or (
                bov is not None and hasattr(bov, "value") and bov.value == "DOWN"
            ):
                return False
            return True
    except Exception:
        return False


__all__ = ["evaluate_link_status", "is_link_passable"]
