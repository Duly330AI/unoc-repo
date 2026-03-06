"""Dependency Resolver – re-export shim.

This module preserves the original public API while delegating implementation to
split modules for maintainability and line-budget compliance. Behavior unchanged.
"""

from .dependency_resolver_core import (
    DependencyCheckResult,
    UpstreamL3Result,
    evaluate_upstream_dependencies,
    has_upstream_l3_or_anchor,
)
from .dependency_resolver_trace import has_l3_reachability_to_anchor, trace_l3_path_to_anchor

__all__ = [
    "DependencyCheckResult",
    "UpstreamL3Result",
    "evaluate_upstream_dependencies",
    "trace_l3_path_to_anchor",
    "has_l3_reachability_to_anchor",
    "has_upstream_l3_or_anchor",
]
