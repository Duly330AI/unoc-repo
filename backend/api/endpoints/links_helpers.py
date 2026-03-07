"""Helper implementations hub for links endpoints.

This module re-exports query, common, and mutation helpers from
smaller focused modules to keep the file-length budget under control
while preserving public APIs and monkeypatch surfaces.
"""

from __future__ import annotations

from .links_helpers_common import normalize_status_str
from .links_helpers_create import create_link_impl as _create_link_impl
from .links_helpers_delete import delete_link_impl as _delete_link_impl
from .links_helpers_override import set_link_override_impl as _set_link_override_impl
from .links_helpers_query import get_link_impl as _get_link_impl
from .links_helpers_query import list_links_impl as _list_links_impl
from .links_helpers_update import update_link_impl as _update_link_impl

__all__ = [
    # query helpers re-exported for compatibility
    "list_links_impl",
    "get_link_impl",
    # shared helpers re-exported for compatibility
    "normalize_status_str",
    # mutation helpers re-exported for compatibility
    "create_link_impl",
    "delete_link_impl",
    "set_link_override_impl",
    "update_link_impl",
]


list_links_impl = _list_links_impl

get_link_impl = _get_link_impl

create_link_impl = _create_link_impl

delete_link_impl = _delete_link_impl

set_link_override_impl = _set_link_override_impl

update_link_impl = _update_link_impl
