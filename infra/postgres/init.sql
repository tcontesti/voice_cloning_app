-- Voice Cloning App — Postgres initialization
-- Runs once on first container start.

CREATE EXTENSION IF NOT EXISTS pgcrypto;   -- gen_random_uuid, digest, hmac
CREATE EXTENSION IF NOT EXISTS "uuid-ossp"; -- uuid_generate_v7 via helper in M2

-- Schemas for logical separation (populated by Alembic in M2)
CREATE SCHEMA IF NOT EXISTS app;     -- application data
CREATE SCHEMA IF NOT EXISTS audit;   -- append-only audit log

COMMENT ON SCHEMA app IS 'Application tables (users, recordings, syntheses, ...)';
COMMENT ON SCHEMA audit IS 'Append-only audit log with hash chain (RGPD / Ley IA 2024/1689)';
