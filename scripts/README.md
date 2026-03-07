# Scripts

Mixed utility & legacy scripts. Actively used items are documented; purely historical ones remain in `legacy/`.

## Active (Phase B)

- `reset_dev_db.py` – Dev convenience: drop/recreate SQLite file DB, optional seed (`--seed`).
- `verify_ts_types.py` – Detect drift between backend Pydantic models & generated TS types.

## Legacy Folder

`scripts/legacy/` holds deprecated or experimental utilities. Before reviving one, create/ reference a TASK ID and modernize paths & imports.

## Contribution Rules

1. Add a header comment with TASK ID & purpose.
2. Prefer idempotent, side-effect explicit scripts.
3. Avoid embedding secrets / environment-specific constants.

## Cleanup Roadmap

Stale scripts will be evaluated each milestone; removals noted in `COMPLETED_TASKS.md` if impactful.

## Profiling backend with py-spy (optional)

To capture a short CPU profile of the running backend using py-spy:

1. Install py-spy in your active environment:

```
pip install py-spy
```

2. Find the backend process ID (PID). If you use the VS Code task "backend: run", check the terminal output or your OS process list.

3. Record a 15s profile and open it:

```
py-spy record -o profile.svg --pid <PID> --duration 15 --rate 100
start profile.svg
```

Notes:

- Trigger the specific endpoints/flows during the capture window to focus samples.
- In containers, you may need extra privileges (ptrace) to attach.
