# SQL Tools Playbook (VS Code)

This playbook documents how we use the VS Code PostgreSQL extension in development for safe and consistent diagnostics.

## Prerequisites

- VS Code extension installed: `ckolkman.vscode-postgres` (PostgreSQL Management Tool)
- Local dev DB via docker-compose listening on localhost:5432

Two connections are preconfigured in `.vscode/settings.json`:

- UNOC (Read-Only) — default. User: `unoc_ro`
- UNOC (Admin) — escalation only. User: `unoc`

The connections point to:

- Host: `localhost`
- Port: `5432`
- Database: `unocdb`

## Usage

1. Open the PostgreSQL explorer (VS Code activity bar → PostgreSQL icon).
2. Select the default connection "UNOC (Read-Only)" and connect.
3. Use the built-in query editor for SELECT-only diagnostics. Save queries in your workspace when useful.

### Common tasks

- Inspect tables: Right-click schema → "Show Table" or run `SELECT * FROM <table> LIMIT 50;`.
- Check counts and status: `SELECT COUNT(*) FROM <table>;`
- Verify recent changes via API: filter by timestamps or IDs returned from the REST calls.

## Rules and Workflow

- Always use the Read-Only connection for diagnostics.
- Any write (INSERT/UPDATE/DELETE) requires explicit approval by the project lead and must be executed using the "UNOC (Admin)" connection.
- Prefer API endpoints for creating test data or modifying objects. Direct DB writes are exceptions and must be tracked in an incident or task with exact SQL attached.

## Read-Only Role

The `unoc_ro` user is intended to have SELECT-only privileges. If you cannot connect or see objects:

- Confirm the user exists and has `CONNECT` on the database and `USAGE` on required schemas.
- Ensure `GRANT SELECT` is applied to tables and views that you need to inspect.

## Troubleshooting

- Connection refused: make sure docker-compose is up and Postgres is listening on 5432 locally.
- Authentication failed: check credentials in `.vscode/settings.json` or environment overrides.
- Missing tables: verify current schema (`search_path`) and privileges for `unoc_ro`.

## Security notes

- Do not commit real credentials in public repositories. For local dev, credentials are placeholders and may be overridden by environment variables.
- Use the Admin connection only when approved and for the shortest time necessary. Switch back to Read-Only after completing the task.
