"""Devices API endpoints.

This module intentionally stays thin: all business logic lives in helpers.
"""

from fastapi import APIRouter, Header, HTTPException, Query, Response

from backend.api.schemas import DeviceCreate, DeviceOut, DeviceUpdate
from backend.db import get_session, init_db

from .devices_helpers_ip_trace import get_device_ip_trace_impl
from .devices_helpers_mac_table import get_device_mac_table_impl
from .devices_helpers_mutation import (
    ConflictError,
    UnprocessableError,
    create_device_impl,
    delete_device_impl,
    update_device_impl,
)
from .devices_helpers_override import set_device_override_impl
from .devices_helpers_query import get_device_impl, get_devices_json_cached
from .devices_helpers_transiting_ips import get_device_transiting_ips_impl

router = APIRouter(tags=["devices"], prefix="/devices")


@router.post("", response_model=DeviceOut, status_code=201)
def create_device(payload: DeviceCreate):
    init_db()
    with get_session() as s:
        try:
            return create_device_impl(s, payload)
        except ConflictError as e:
            raise HTTPException(status_code=409, detail=str(e)) from None
        except UnprocessableError as e:
            # 400 for parent validation, 422 for semantic problems
            msg = str(e)
            # Treat any parent/parenting rule violations as 400 (bad request)
            lower = msg.lower()
            code = (
                400
                if ("parent" in lower or "parented" in lower or msg == "INVALID_PARENT")
                else 422
            )
            raise HTTPException(status_code=code, detail=msg) from None


@router.get(
    "",
    response_model=list[DeviceOut],
    response_model_exclude_none=True,
)
def list_devices(
    include_interfaces: bool = Query(
        False,
        description="Include interface list (adds 'interfaces' array to each device)",
    ),
    if_none_match: str | None = Header(default=None, alias="If-None-Match"),
):
    init_db()
    with get_session() as s:
        # If-None-Match handling
        json_bytes, etag = get_devices_json_cached(s, include_interfaces)
        inm = if_none_match
        if inm and inm == etag:
            return Response(status_code=304)
        return Response(content=json_bytes, media_type="application/json", headers={"ETag": etag})


@router.get("/{device_id}", response_model=DeviceOut)
def get_device(device_id: str):
    init_db()
    with get_session() as s:
        try:
            return get_device_impl(s, device_id)
        except LookupError:
            raise HTTPException(status_code=404, detail="Not found") from None


@router.put("/{device_id}", response_model=DeviceOut)
def update_device(device_id: str, payload: DeviceUpdate):
    init_db()
    with get_session() as s:
        try:
            return update_device_impl(s, device_id, payload)
        except LookupError:
            raise HTTPException(status_code=404, detail="Not found") from None
        except UnprocessableError as e:
            msg = str(e)
            lower = msg.lower()
            code = (
                400
                if ("parent" in lower or "parented" in lower or msg == "INVALID_PARENT")
                else 422
            )
            raise HTTPException(status_code=code, detail=msg) from None


@router.get("/{device_id}/mac-table", response_model=list[dict])
def get_device_mac_table(device_id: str):
    """Return the MAC address entries for the device's bridge domains.

    Minimal shape: [{ mac_address, interface_id, bridge_domain_id, type }]
    """
    init_db()
    with get_session() as s:
        try:
            return get_device_mac_table_impl(s, device_id)
        except LookupError:
            raise HTTPException(status_code=404, detail="Not found") from None


@router.patch("/{device_id}/override", response_model=DeviceOut)
def set_device_override(device_id: str, body: dict):  # type: ignore[no-untyped-def]
    """Set or clear admin override status for a device.

    Body: { admin_override_status: "DOWN" | null }
    """
    init_db()
    with get_session() as s:
        try:
            return set_device_override_impl(s, device_id, body)
        except LookupError:
            raise HTTPException(status_code=404, detail="Not found") from None
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e)) from None


@router.delete("/{device_id}", status_code=204)
def delete_device(device_id: str):
    init_db()
    with get_session() as s:
        try:
            delete_device_impl(s, device_id)
            return None
        except LookupError:
            raise HTTPException(status_code=404, detail="Not found") from None


@router.get("/{device_id}/ip-trace", response_model=dict)
def get_device_ip_trace(device_id: str):
    """Compute L3 communication path from device to backbone_gateway.

    Returns IP addresses, hops, and reachability status.
    """
    init_db()
    with get_session() as s:
        try:
            return get_device_ip_trace_impl(s, device_id)
        except LookupError:
            raise HTTPException(status_code=404, detail="Not found") from None


@router.get("/{device_id}/transiting-ips", response_model=dict)
def get_device_transiting_ips(device_id: str):
    """Get all IPs transiting through a passive device (e.g., optical splitter).

    Passive devices don't have L3 routing but traffic flows through them.
    Returns aggregated IPs from downstream devices and IP pool statistics.
    """
    init_db()
    with get_session() as s:
        try:
            return get_device_transiting_ips_impl(s, device_id)
        except LookupError:
            raise HTTPException(status_code=404, detail="Not found") from None
