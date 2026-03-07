"""Compatibility shim for devices mutation helpers.

This file re-exports the public API (exceptions and functions) from
smaller modules to keep file sizes below the 400-line policy, while
preserving import paths used by the router.
"""

from .devices_helpers_delete import delete_device_impl  # re-export
from .devices_helpers_mutation_core import (  # re-export
    ConflictError,
    UnprocessableError,
    create_device_impl,
    update_device_impl,
)

__all__ = [
    "ConflictError",
    "UnprocessableError",
    "create_device_impl",
    "update_device_impl",
    "delete_device_impl",
]
