-- SENTINEL – schema.sql
-- Run once against a fresh PostgreSQL database:
--   psql -U sentinel_user -d sentinel -f schema.sql
--
-- Re-running is safe: all statements use IF NOT EXISTS / DO NOTHING.
--
-- v2.1 — expanded to match the frontend's actual data contract (persons,
-- groups, activities, hotspots, intel reports, generic entity extras,
-- audit log, backups). Enum-like text columns store the frontend's exact
-- uppercase string values (e.g. 'CRITICAL', 'ACTIVE') so the API layer
-- never needs to translate casing.

-- ─────────────────────────────────────────────
-- Extensions
-- ─────────────────────────────────────────────
CREATE EXTENSION IF NOT EXISTS "pgcrypto";   -- gen_random_uuid()
CREATE EXTENSION IF NOT EXISTS "unaccent";   -- accent-insensitive search

-- ─────────────────────────────────────────────
-- Users / Auth
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS users (
    id          SERIAL PRIMARY KEY,
    username    TEXT NOT NULL UNIQUE,
    password    TEXT NOT NULL,          -- bcrypt hash
    name        TEXT NOT NULL DEFAULT '',
    role        TEXT NOT NULL DEFAULT 'VIEWER'
                    CHECK (role IN ('ADMIN', 'ANALYST', 'VIEWER')),
    unit        TEXT,
    active      BOOLEAN NOT NULL DEFAULT TRUE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_login  TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS login_attempts (
    id          SERIAL PRIMARY KEY,
    username    TEXT NOT NULL,
    ip          TEXT NOT NULL,
    success     BOOLEAN NOT NULL,
    attempted_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_login_attempts_lookup
    ON login_attempts (username, ip, attempted_at DESC);

-- ─────────────────────────────────────────────
-- Persons of Interest
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS poi (
    id            SERIAL PRIMARY KEY,
    alias         TEXT NOT NULL,
    first_name    TEXT,
    last_name     TEXT,
    dob           DATE,
    nationality   TEXT,
    risk_level    TEXT NOT NULL DEFAULT 'MEDIUM'
                      CHECK (risk_level IN ('CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'INACTIVE')),
    status        TEXT NOT NULL DEFAULT 'ACTIVE'
                      CHECK (status IN ('ACTIVE', 'INACTIVE', 'DECEASED', 'UNKNOWN')),
    last_seen     DATE,
    last_location TEXT,
    last_lat      DOUBLE PRECISION,   -- coordinates for last_location, if known/plotted
    last_lng      DOUBLE PRECISION,
    description   TEXT,
    notes         TEXT,
    photo         TEXT,           -- base64 data URI, primary profile photo
    likeness      TEXT,           -- base64 data URI, sketch/composite image
    contacts      INTEGER[] NOT NULL DEFAULT '{}',   -- associate POI ids
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_poi_nationality ON poi (nationality);
-- Migration: existing databases created before last_lat/last_lng existed.
ALTER TABLE poi ADD COLUMN IF NOT EXISTS last_lat DOUBLE PRECISION;
ALTER TABLE poi ADD COLUMN IF NOT EXISTS last_lng DOUBLE PRECISION;

-- Evidence photo gallery — POI-specific (distinct from the generic
-- polymorphic `images` table below, which backs the "Profile Photographs" panel).
CREATE TABLE IF NOT EXISTS poi_gallery (
    id          SERIAL PRIMARY KEY,
    poi_id      INTEGER NOT NULL REFERENCES poi(id) ON DELETE CASCADE,
    src         TEXT NOT NULL,     -- base64 data URI
    caption     TEXT,
    occurred_on DATE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Offline face recognition (face_match.py: InsightFace buffalo_l + onnxruntime).
-- One row per detected face across a POI's photos (profile photo, likeness,
-- gallery, generic images) — answers "who does this new photo most resemble?"
-- via cosine similarity against every stored embedding.
CREATE TABLE IF NOT EXISTS face_embeddings (
    id          SERIAL PRIMARY KEY,
    poi_id      INTEGER NOT NULL REFERENCES poi(id) ON DELETE CASCADE,
    source      TEXT NOT NULL CHECK (source IN ('profile_photo', 'likeness', 'gallery', 'images')),
    source_id   INTEGER,        -- poi_gallery.id or images.id; NULL for the single-valued profile_photo/likeness fields
    embedding   BYTEA NOT NULL, -- 512-d float32 vector, L2-normalised (dot product == cosine similarity)
    det_score   DOUBLE PRECISION,
    bbox        JSONB,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_face_embeddings_poi ON face_embeddings (poi_id);

-- ─────────────────────────────────────────────
-- Groups of Interest
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS groups_of_interest (
    id           SERIAL PRIMARY KEY,
    name         TEXT NOT NULL,
    type         TEXT,
    threat_level TEXT NOT NULL DEFAULT 'MEDIUM'
                     CHECK (threat_level IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')),
    status       TEXT NOT NULL DEFAULT 'ACTIVE'
                     CHECK (status IN ('ACTIVE', 'INACTIVE', 'DORMANT')),
    founded      TEXT,
    base         TEXT,
    base_lat     DOUBLE PRECISION,   -- coordinates for base, if known/plotted
    base_lng     DOUBLE PRECISION,
    leader_id    INTEGER REFERENCES poi(id) ON DELETE SET NULL,
    description  TEXT,
    objectives   TEXT,
    notes        TEXT,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
-- Migration: existing databases created before base_lat/base_lng existed.
ALTER TABLE groups_of_interest ADD COLUMN IF NOT EXISTS base_lat DOUBLE PRECISION;
ALTER TABLE groups_of_interest ADD COLUMN IF NOT EXISTS base_lng DOUBLE PRECISION;

CREATE TABLE IF NOT EXISTS group_members (
    group_id    INTEGER NOT NULL REFERENCES groups_of_interest(id) ON DELETE CASCADE,
    poi_id      INTEGER NOT NULL REFERENCES poi(id) ON DELETE CASCADE,
    role        TEXT,
    joined_at   DATE,
    PRIMARY KEY (group_id, poi_id)
);

-- ─────────────────────────────────────────────
-- Locations (standing Location entity — feeds the dashboard's location
-- count and country aggregation; distinct from the generic per-entity
-- `entity_coordinates` table used for POI/group/activity "known locations").
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS locations (
    id          SERIAL PRIMARY KEY,
    name        TEXT NOT NULL,
    description TEXT,
    address     TEXT,
    country     TEXT,
    notes       TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS location_coords (
    id          SERIAL PRIMARY KEY,
    location_id INTEGER NOT NULL REFERENCES locations(id) ON DELETE CASCADE,
    lat         DOUBLE PRECISION NOT NULL,
    lng         DOUBLE PRECISION NOT NULL,
    label       TEXT
);

-- ─────────────────────────────────────────────
-- Gazetteer — offline place-name → coordinate lookup table. Populated from
-- GeoNames data via scripts/load_gazetteer.py. Powers geocode.py, which
-- auto-pins extracted locations on ingest (see nlp.commit_job). `search_key`
-- is the accent-folded lower-case name used for matching.
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS gazetteer (
    id           SERIAL PRIMARY KEY,
    geonameid    BIGINT,
    name         TEXT NOT NULL,
    asciiname    TEXT,
    search_key   TEXT NOT NULL,
    country      TEXT,           -- full country name when countryInfo.txt is loaded, else ISO2 code
    admin1       TEXT,
    lat          DOUBLE PRECISION NOT NULL,
    lng          DOUBLE PRECISION NOT NULL,
    population   BIGINT DEFAULT 0,
    feature_code TEXT
);
CREATE INDEX IF NOT EXISTS idx_gazetteer_search_key ON gazetteer (search_key);
CREATE INDEX IF NOT EXISTS idx_gazetteer_key_country ON gazetteer (search_key, country);

-- ─────────────────────────────────────────────
-- Activities — flat lat/lng + free-text location, matching how the
-- frontend actually models an activity (a single primary POI/group link,
-- not a many-to-many join).
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS activities (
    id          SERIAL PRIMARY KEY,
    poi_id      INTEGER REFERENCES poi(id) ON DELETE SET NULL,
    group_id    INTEGER REFERENCES groups_of_interest(id) ON DELETE SET NULL,
    type        TEXT NOT NULL DEFAULT 'OTHER'
                    CHECK (type IN ('MEETING', 'MOVEMENT', 'COMMUNICATION', 'FINANCIAL', 'SURVEILLANCE', 'OTHER')),
    occurred_on DATE,
    location    TEXT,
    lat         DOUBLE PRECISION,
    lng         DOUBLE PRECISION,
    description TEXT,
    severity    TEXT NOT NULL DEFAULT 'LOW'
                    CHECK (severity IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')),
    reported_by TEXT,
    notes       TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_activities_poi   ON activities (poi_id);
CREATE INDEX IF NOT EXISTS idx_activities_group ON activities (group_id);

-- ─────────────────────────────────────────────
-- Hotspots — map points with no underlying activity/location record.
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS hotspots (
    id          SERIAL PRIMARY KEY,
    name        TEXT NOT NULL,
    type        TEXT NOT NULL DEFAULT 'GENERAL'
                    CHECK (type IN ('MEETING_POINT', 'LOGISTICS', 'FINANCIAL', 'COMMAND', 'SURVEILLANCE', 'GENERAL')),
    risk        TEXT NOT NULL DEFAULT 'MEDIUM'
                    CHECK (risk IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')),
    lat         DOUBLE PRECISION NOT NULL,
    lng         DOUBLE PRECISION NOT NULL,
    note        TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ─────────────────────────────────────────────
-- Intel reports (analysis.html "New Report" / NLP commit target)
-- poi_refs/group_refs/locations/victims are stored as JSON-encoded text
-- (not native arrays) because the frontend does `JSON.parse(i.poi_refs)`.
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS intel_reports (
    id              SERIAL PRIMARY KEY,
    title           TEXT NOT NULL,
    occurred_on     DATE,
    body            TEXT,
    poi_refs        TEXT NOT NULL DEFAULT '[]',
    group_refs      TEXT NOT NULL DEFAULT '[]',
    locations       TEXT NOT NULL DEFAULT '[]',
    victims         TEXT NOT NULL DEFAULT '[]',
    analysis_result TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ─────────────────────────────────────────────
-- Generic entity extras — shared across entity_type IN
-- ('person', 'group', 'activity', 'location'), keyed by entity_id.
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS tags (
    id          SERIAL PRIMARY KEY,
    entity_type TEXT NOT NULL,
    entity_id   INTEGER NOT NULL,
    tag         TEXT NOT NULL,
    color       TEXT,
    UNIQUE (entity_type, entity_id, tag)
);
CREATE INDEX IF NOT EXISTS idx_tags_lookup ON tags (entity_type, entity_id);

CREATE TABLE IF NOT EXISTS notes (
    id          SERIAL PRIMARY KEY,
    entity_type TEXT NOT NULL,
    entity_id   INTEGER NOT NULL,
    title       TEXT,
    body        TEXT,
    note_type   TEXT NOT NULL DEFAULT 'GENERAL'
                    CHECK (note_type IN ('GENERAL', 'FIELD_REPORT', 'ASSESSMENT', 'OBSERVATION', 'WARNING')),
    is_pinned   BOOLEAN NOT NULL DEFAULT FALSE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_notes_lookup ON notes (entity_type, entity_id);

CREATE TABLE IF NOT EXISTS custom_fields (
    id          SERIAL PRIMARY KEY,
    entity_type TEXT NOT NULL,
    entity_id   INTEGER NOT NULL,
    field_key   TEXT NOT NULL,
    field_value TEXT,
    field_type  TEXT NOT NULL DEFAULT 'TEXT'
                    CHECK (field_type IN ('TEXT', 'NUMBER', 'DATE', 'URL', 'JSON')),
    UNIQUE (entity_type, entity_id, field_key)
);
CREATE INDEX IF NOT EXISTS idx_fields_lookup ON custom_fields (entity_type, entity_id);

CREATE TABLE IF NOT EXISTS attachments (
    id          SERIAL PRIMARY KEY,
    entity_type TEXT NOT NULL,
    entity_id   INTEGER NOT NULL,
    attach_type TEXT NOT NULL DEFAULT 'TEXT'
                    CHECK (attach_type IN ('TEXT', 'IMAGE', 'URL', 'DATA', 'DOCUMENT')),
    name        TEXT NOT NULL,
    content     TEXT,          -- base64 or plain-text body
    url         TEXT,
    mime_type   TEXT,
    description TEXT,
    size_bytes  INTEGER,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_attachments_lookup ON attachments (entity_type, entity_id);

CREATE TABLE IF NOT EXISTS images (
    id          SERIAL PRIMARY KEY,
    entity_type TEXT NOT NULL,
    entity_id   INTEGER NOT NULL,
    content     TEXT NOT NULL,   -- base64 data URI
    name        TEXT,
    description TEXT,
    mime_type   TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_images_lookup ON images (entity_type, entity_id);

CREATE TABLE IF NOT EXISTS entity_coordinates (
    id          SERIAL PRIMARY KEY,
    entity_type TEXT NOT NULL,
    entity_id   INTEGER NOT NULL,
    lat         DOUBLE PRECISION NOT NULL,
    lng         DOUBLE PRECISION NOT NULL,
    label       TEXT,
    note        TEXT,
    observed_on DATE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_entity_coordinates_lookup ON entity_coordinates (entity_type, entity_id);

-- entity_id/related_id are nullable + paired with an optional *_name column
-- so a relationship endpoint can be a "virtual" node with no numeric row of
-- its own — currently: a country (identified by name; see nationalities.py),
-- used by the Link Analysis diagram to connect persons/groups to countries.
CREATE TABLE IF NOT EXISTS relationships (
    id           SERIAL PRIMARY KEY,
    entity_type  TEXT NOT NULL,
    entity_id    INTEGER,
    entity_name  TEXT,
    related_type TEXT NOT NULL,
    related_id   INTEGER,
    related_name TEXT,
    rel_type     TEXT,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_relationships_lookup ON relationships (entity_type, entity_id);
-- Migration: existing databases created before entity_id/related_id were nullable.
ALTER TABLE relationships ALTER COLUMN entity_id DROP NOT NULL;
ALTER TABLE relationships ALTER COLUMN related_id DROP NOT NULL;
ALTER TABLE relationships ADD COLUMN IF NOT EXISTS entity_name TEXT;
ALTER TABLE relationships ADD COLUMN IF NOT EXISTS related_name TEXT;

-- Link Analysis — saved, named i2-style link charts. Nodes reference a
-- person/group (by numeric id) or a country (by name, no numeric row
-- exists for countries); edges are resolved live from `relationships`
-- (+ group_members / poi.contacts) rather than duplicated per chart.
CREATE TABLE IF NOT EXISTS link_charts (
    id          SERIAL PRIMARY KEY,
    name        TEXT NOT NULL,
    description TEXT,
    created_by  TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS link_chart_nodes (
    id          SERIAL PRIMARY KEY,
    chart_id    INTEGER NOT NULL REFERENCES link_charts(id) ON DELETE CASCADE,
    node_type   TEXT NOT NULL CHECK (node_type IN ('person', 'group', 'country')),
    node_ref    TEXT NOT NULL,   -- poi.id / groups_of_interest.id as text, or the country name
    x           DOUBLE PRECISION,
    y           DOUBLE PRECISION,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (chart_id, node_type, node_ref)
);
CREATE INDEX IF NOT EXISTS idx_link_chart_nodes_chart ON link_chart_nodes (chart_id);

CREATE TABLE IF NOT EXISTS timeline_events (
    id          SERIAL PRIMARY KEY,
    entity_type TEXT NOT NULL,
    entity_id   INTEGER NOT NULL,
    event_date  TIMESTAMPTZ NOT NULL,
    title       TEXT NOT NULL,
    detail      TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_timeline_lookup ON timeline_events (entity_type, entity_id, event_date DESC);

-- ─────────────────────────────────────────────
-- NLP / Intel extraction module
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS nlp_jobs (
    id           SERIAL PRIMARY KEY,
    raw_text     TEXT NOT NULL,
    claude_output JSONB,           -- raw Claude API response
    status       TEXT NOT NULL DEFAULT 'pending'
                     CHECK (status IN ('pending', 'reviewed', 'committed', 'rejected', 'failed')),
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    reviewed_at  TIMESTAMPTZ,
    committed_at TIMESTAMPTZ
);

-- ─────────────────────────────────────────────
-- Audit log
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS audit_log (
    id          SERIAL PRIMARY KEY,
    ts          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    user_id     INTEGER REFERENCES users(id) ON DELETE SET NULL,
    username    TEXT NOT NULL,
    action      TEXT NOT NULL,
    resource    TEXT,
    resource_id TEXT,
    detail      TEXT,
    ip          TEXT
);
CREATE INDEX IF NOT EXISTS idx_audit_log_user ON audit_log (user_id, ts DESC);
CREATE INDEX IF NOT EXISTS idx_audit_log_ts   ON audit_log (ts DESC);

-- ─────────────────────────────────────────────
-- Backups (metadata for files written to ./backups by pg_dump)
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS backups (
    id          SERIAL PRIMARY KEY,
    name        TEXT NOT NULL,
    created     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    size        BIGINT NOT NULL DEFAULT 0,
    verified    BOOLEAN NOT NULL DEFAULT FALSE,
    counts      JSONB,
    detail      TEXT
);

-- ─────────────────────────────────────────────
-- Narrative AI summaries (Phase 2) — the latest generated intelligence
-- assessment for a subject, stored so it persists, loads instantly, and prints.
-- Generic (entity_type/entity_id) to match tags/notes/images/entity_coordinates.
-- One current summary per subject (UNIQUE); regenerated on demand via
-- POST /api/persons|groups/<id>/summary.
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS entity_summaries (
    id           SERIAL PRIMARY KEY,
    entity_type  TEXT NOT NULL,          -- 'person' | 'group'
    entity_id    INTEGER NOT NULL,
    summary      TEXT NOT NULL,
    model        TEXT,
    generated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (entity_type, entity_id)
);

-- ─────────────────────────────────────────────
-- Updated-at trigger (apply to all main tables)
-- ─────────────────────────────────────────────
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;

DO $$
DECLARE
    tbl TEXT;
BEGIN
    FOREACH tbl IN ARRAY ARRAY['poi','groups_of_interest','locations','activities']
    LOOP
        IF NOT EXISTS (
            SELECT 1 FROM pg_trigger
            WHERE tgname = 'trg_' || tbl || '_updated_at'
        ) THEN
            EXECUTE format(
                'CREATE TRIGGER trg_%I_updated_at
                 BEFORE UPDATE ON %I
                 FOR EACH ROW EXECUTE FUNCTION set_updated_at()',
                tbl, tbl
            );
        END IF;
    END LOOP;
END;
$$;
