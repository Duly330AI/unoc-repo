# Definition of Done (DoD)

A change is considered Done when it satisfies ALL of the following:

1. Code quality

- Lints clean (ruff) and formatted (black/isort where applicable)
- No TODO/FIXME left in changed lines unless tracked with an issue ID
- Public API changes documented and typed

2. Tests

- Unit tests cover happy path + at least one edge case
- Integration tests updated when behavior changes
- Full backend test suite passes locally
- New functionality measurable via assertions (no sleep-based flakiness)

3. Performance & Observability

- SQL query count/time checked on hot paths (perf.log shows reasonable bounds)
- No N+1 added; add cache/indexes where necessary
- Meaningful logs at INFO/ERROR; no noisy debug logs committed
- Metrics counters/timers added for new critical paths

4. Security & Reliability

- Inputs validated; no direct SQL string concatenation
- Exceptions handled; user-facing errors mapped to proper HTTP status codes
- Background tasks idempotent and coalesced when applicable

5. Documentation

- docs updated: API, architecture, or ops sections as relevant
- README or setup docs updated if setup changes
- Migration notes added when data shape changes

6. Release hygiene

- Feature flag or config gate for risky behavior
- Backwards compatibility noted; deprecation schedule documented if needed
- Acceptance criteria ticked off in issue/PR description
