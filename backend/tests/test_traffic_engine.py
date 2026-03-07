from __future__ import annotations

from backend.services.traffic_engine import deterministic_rand01


def test_prng_determinism_basic():
    s = 42
    a = deterministic_rand01(s, 0, "dev1")
    b = deterministic_rand01(s, 0, "dev1")
    c = deterministic_rand01(s, 1, "dev1")
    d = deterministic_rand01(s, 0, "dev2")
    assert 0.0 <= a < 1.0
    assert a == b
    assert a != c
    assert a != d
