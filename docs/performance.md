# Performance: L3 status-recompute O(N^2) -> O(N)

## Method

The measured path is the L3 status-recompute specifically: `has_upstream_l3_or_anchor()` over N leaf devices in one session.

The benchmark is [backend/tests/perf/bench_l3_recompute.py](../backend/tests/perf/bench_l3_recompute.py). It creates an isolated throwaway sqlite database, builds a small routed topology with N leaf devices, and times the L3 reachability/status recompute path. `py-spy` sampling of the live stack was used to locate the hotspots before and after the code changes.

## Result

N = 200 leaf devices:

| State | Time | Per leaf |
| --- | ---: | ---: |
| Before, graph cache only | ~24,600 ms | ~123 ms/leaf |
| After, router-chain cache | ~285 ms | ~1.4 ms/leaf |

That is about an 85x reduction for the isolated L3 status-recompute benchmark.

## What changed

- Reuse a version-keyed logical-graph snapshot instead of rebuilding it per device.
- Memoize router L3 chains per recompute pass, scoped to the SQLModel session used for that pass.
- Dropped an O(N) admin-override fingerprint and a redundant provisioning recompute.

## Honest scope caveat

This measures the isolated L3 recompute, not end-to-end provisioning throughput. Single-device provisioning is still per-device; a bulk-provision path that performs one recompute for all devices is future work for large batches.

## Reproduce

Run from the repository root in Git Bash:

```bash
export PYTHONPATH=.
DATABASE_URL="sqlite:///bench_l3.db" BENCH_N=200 .venv-audit/Scripts/python.exe backend/tests/perf/bench_l3_recompute.py
rm -f bench_l3.db
```
