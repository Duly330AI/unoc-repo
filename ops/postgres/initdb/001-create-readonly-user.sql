-- Create read-only user for diagnostics in VS Code
-- This script runs once on first cluster init by the postgres image
-- Idempotency: CREATE USER IF NOT EXISTS is not available in vanilla Postgres; guard with DO block

DO
$$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_roles WHERE rolname = 'unoc_ro'
  ) THEN
    CREATE USER unoc_ro WITH PASSWORD 'unocpw_ro';
  END IF;
END
$$;

-- Ensure the user can connect to the database and read objects
GRANT CONNECT ON DATABASE unocdb TO unoc_ro;

-- Apply privileges after switching to target DB context
\connect unocdb

-- Grant USAGE on all non-system schemas (here public, extend if you create more schemas)
GRANT USAGE ON SCHEMA public TO unoc_ro;

-- Grant SELECT on existing tables and sequences
GRANT SELECT ON ALL TABLES IN SCHEMA public TO unoc_ro;
GRANT SELECT ON ALL SEQUENCES IN SCHEMA public TO unoc_ro;

-- Ensure future tables/sequences are also readable
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO unoc_ro;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON SEQUENCES TO unoc_ro;
