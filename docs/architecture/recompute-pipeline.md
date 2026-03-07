# Recompute Pipeline

1. API writes mutation -> enqueue event (coalesce window 50–200 ms)
2. Worker aggregates events -> builds dirty set
3. Incremental recompute (status/optics)
4. Persist diffs -> bump version
5. Invalidate snapshot cache -> emit WS deltas
