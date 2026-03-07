"""Aggregate API router assembling modular endpoint groups.

This file intentionally kept tiny; individual endpoint groups live under
`backend.api.endpoints.*` to satisfy the 400 line policy and aid navigation.
"""

from fastapi import APIRouter

from .endpoints import (
    catalog,
    config,
    debug,
    devices,
    health,
    interfaces,
    ipam,
    layout,
    links,
    links_batch,
    metrics,
    optical,
    physical,
    ports,
    provisioning,
    routing,
    status,
    tariffs,
    tools,
    topology,
    vrf_prefix,
    ws,
)

api_router = APIRouter()

# Include sub-routers (prefixes defined in each module for clarity)
api_router.include_router(health.router)
api_router.include_router(layout.router)
# Legacy: include layout router again without prefix for backwards compatibility
api_router.include_router(layout.router, prefix="", include_in_schema=False)
api_router.include_router(devices.router)
api_router.include_router(provisioning.router)
api_router.include_router(interfaces.router)
api_router.include_router(interfaces.addr_router)
api_router.include_router(links.router)
api_router.include_router(links_batch.router)
api_router.include_router(physical.router)
api_router.include_router(optical.router)
api_router.include_router(topology.router)
api_router.include_router(metrics.router)
api_router.include_router(ws.router)
api_router.include_router(ipam.router)
api_router.include_router(vrf_prefix.router)
api_router.include_router(routing.router)
api_router.include_router(config.router)
api_router.include_router(tariffs.router)
api_router.include_router(catalog.router)
api_router.include_router(debug.router)
api_router.include_router(ports.router)
api_router.include_router(tools.router)
api_router.include_router(status.router, prefix="/status", tags=["status"])

__all__ = ["api_router"]
