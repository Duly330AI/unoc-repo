"""Centralized error codes and helpers.

Avoid magic string literals scattered across endpoints/services.
Extend cautiously; codes are stable API surface for clients & tests.
"""

from __future__ import annotations

from enum import Enum

from fastapi import HTTPException


class ErrorCode(str, Enum):
    INVALID_PROVISION_PATH = "INVALID_PROVISION_PATH"
    ALREADY_PROVISIONED = "ALREADY_PROVISIONED"
    POOL_EXHAUSTED = "POOL_EXHAUSTED"
    DUPLICATE_MGMT_INTERFACE = "DUPLICATE_MGMT_INTERFACE"
    INVALID_LINK_TYPE = "INVALID_LINK_TYPE"
    POP_LINK_DISALLOWED = "POP_LINK_DISALLOWED"
    CONTAINER_REQUIRED = "CONTAINER_REQUIRED"
    # GPON Phase 1: ODF-as-Aggregator specific validations
    LINK_INVALID_PAIRING = "LINK_INVALID_PAIRING"
    LINK_INVALID_UPSTREAM = "LINK_INVALID_UPSTREAM"
    LINK_MULTIPLE_UPSTREAMS = "LINK_MULTIPLE_UPSTREAMS"


_DEFAULT_STATUS: dict[ErrorCode, int] = {
    ErrorCode.INVALID_PROVISION_PATH: 400,
    ErrorCode.ALREADY_PROVISIONED: 409,
    ErrorCode.POOL_EXHAUSTED: 409,
    ErrorCode.DUPLICATE_MGMT_INTERFACE: 400,
    ErrorCode.INVALID_LINK_TYPE: 400,
    ErrorCode.POP_LINK_DISALLOWED: 400,
    # Missing / invalid required container (e.g., OLT without POP)
    ErrorCode.CONTAINER_REQUIRED: 422,
    # GPON Phase 1
    ErrorCode.LINK_INVALID_PAIRING: 400,
    ErrorCode.LINK_INVALID_UPSTREAM: 400,
    ErrorCode.LINK_MULTIPLE_UPSTREAMS: 400,
}


def raise_error(
    code: ErrorCode, *, detail_suffix: str | None = None, status_code: int | None = None
):
    sc = status_code or _DEFAULT_STATUS.get(code, 400)
    detail = code.value if detail_suffix is None else f"{code.value} {detail_suffix}".strip()
    raise HTTPException(status_code=sc, detail=detail)


__all__ = ["ErrorCode", "raise_error"]
