# ADR 0001: Use PostgreSQL (not SQLite) in Production

## Context
Initial development used SQLite for simplicity. SQLite cannot handle concurrent writes safely and has limited features (no JSON aggregation, no row-level locking).

## Decision
Use PostgreSQL 16 for production. SQLite is acceptable for local development only.

## Consequences
- Need Docker Compose with Postgres service
- Need DATABASE_URL env var set correctly
- All migrations must be tested against PostgreSQL
- Local dev can still use SQLite via DATABASE_URL env var
