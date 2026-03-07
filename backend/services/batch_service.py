"""
Batch Operations Service - Python Fallback Implementation

Week 3 Day 14: Stub fallback implementation for batch operations.
Used when Go batch service is unavailable.

NOTE: This is a STUB implementation for Week 3 Day 14. Real implementation will delegate
to existing link CRUD functions in subsequent tasks.
"""

import uuid
from typing import Any


def batch_create_links_python(
    links: list[dict[str, Any]],
    dry_run: bool = False,
    request_id: str | None = None,
    db: Any = None,
) -> dict[str, Any]:
    """
    Python stub fallback for batch link creation.

    Returns empty results with a warning that Python fallback is not fully implemented.
    Week 3 Day 14: Stub only - real implementation in Day 15.
    """
    request_id = request_id or str(uuid.uuid4())

    return {
        "created_link_ids": [],
        "failed_links": [
            {
                "index": idx,
                "a_interface_id": link["a_interface_id"],
                "b_interface_id": link["b_interface_id"],
                "error_code": "FALLBACK_NOT_IMPLEMENTED",
                "error_message": "Python fallback stub - use Go service (Day 14)",
            }
            for idx, link in enumerate(links)
        ],
        "total_requested": len(links),
        "total_created": 0,
    }


def batch_delete_links_python(
    link_ids: list[int],
    request_id: str | None = None,
    db: Any = None,
) -> dict[str, Any]:
    """
    Python stub fallback for batch link deletion.

    Returns empty results with a warning that Python fallback is not fully implemented.
    Week 3 Day 14: Stub only - real implementation in Day 15.
    """
    request_id = request_id or str(uuid.uuid4())

    return {
        "deleted_link_ids": [],
        "failed_links": [
            {
                "index": idx,
                "link_id": link_id,
                "error_code": "FALLBACK_NOT_IMPLEMENTED",
                "error_message": "Python fallback stub - use Go service (Day 14)",
            }
            for idx, link_id in enumerate(link_ids)
        ],
        "total_requested": len(link_ids),
        "total_deleted": 0,
    }
