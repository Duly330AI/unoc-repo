"""Compatibility shim for legacy imports.

This package used to contain seeding helpers. The real implementations now live
under ``backend.services.seed_helpers`` and orchestrator helpers remain in the
module file ``backend/services/seed_service.py``. Because this package name
shadows the module name, we dynamically load the sibling module to re-export
its public API without circular imports.
"""

from __future__ import annotations

import importlib.util
import os
import sys
from types import ModuleType

# Re-export helper functions from the new helpers package
from backend.services.seed_helpers import (
    ensure_default_hardware_models,
    ensure_default_tariffs,
    ensure_ipam_defaults,
)

_SIBLING_PATH = os.path.normpath(
    os.path.join(os.path.dirname(__file__), os.pardir, "seed_service.py")
)
_IMPL_NAME = "backend.services._seed_service_impl"
_IMPL: ModuleType | None = None


def _load_impl() -> ModuleType:
    global _IMPL
    if _IMPL is not None:
        return _IMPL
    spec = importlib.util.spec_from_file_location(_IMPL_NAME, _SIBLING_PATH)
    if not spec or not spec.loader:  # pragma: no cover - defensive
        raise ImportError("Failed to locate seed_service implementation module")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[_IMPL_NAME] = mod
    spec.loader.exec_module(mod)  # type: ignore[assignment]
    _IMPL = mod
    return mod


# Wrapper exports so names exist at import-time; implementations are loaded lazily
def allocate_backbone_mgmt(session, device):  # pragma: no cover - thin wrapper
    return _load_impl().allocate_backbone_mgmt(session, device)


def ensure_backbone_gateway(session):  # pragma: no cover - thin wrapper
    return _load_impl().ensure_backbone_gateway(session)


def ensure_physical_media(session):  # pragma: no cover - thin wrapper
    return _load_impl().ensure_physical_media(session)


# Expose constant via module attribute from implementation
try:  # pragma: no cover - simple constant fetch
    BACKBONE_GATEWAY_ID = _load_impl().BACKBONE_GATEWAY_ID  # type: ignore[attr-defined]
except Exception as _e:  # Fallback to literal to avoid import-time crashes
    BACKBONE_GATEWAY_ID = "backbone_gateway"

__all__ = [
    # helpers
    "ensure_default_hardware_models",
    "ensure_default_tariffs",
    "ensure_ipam_defaults",
    # orchestrator re-exports
    "allocate_backbone_mgmt",
    "ensure_backbone_gateway",
    "ensure_physical_media",
    "BACKBONE_GATEWAY_ID",
]
