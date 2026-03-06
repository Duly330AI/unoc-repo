"""Link classification service.

Consumes LINK_TYPE_RULES constants and provides a stable classify() helper.
"""

from __future__ import annotations

from dataclasses import dataclass

from backend.constants import LINK_TYPE_RULES
from backend.models import Device


@dataclass(slots=True)
class LinkClassification:
    rule_id: str
    allowed: bool
    link_class: str


def classify(a: Device, b: Device) -> LinkClassification:
    for r in LINK_TYPE_RULES:
        if r.matcher(a, b):  # type: ignore[attr-defined]
            return LinkClassification(r.rule_id, r.allowed, r.link_class)
    # default L9 reverse_invalid (see spec)
    return LinkClassification("L9", False, "reverse_invalid")
