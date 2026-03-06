"""
Go gRPC Service Clients with Python Fallback

Week 1 Day 4: gRPC clients with protobuf stubs.
All clients gracefully fall back to Python if Go services unavailable.
"""

from .batch_client import BatchClient, get_batch_client
from .optical_client import OpticalClient, get_optical_client
from .status_client import StatusClient, get_status_client

__all__ = [
    "OpticalClient",
    "get_optical_client",
    "BatchClient",
    "get_batch_client",
    "StatusClient",
    "get_status_client",
]
