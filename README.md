# SENTINEL

[![CI Tests](https://github.com/mukalshaban-arch/SENTINEL/actions/workflows/tests.yml/badge.svg)](https://github.com/mukalshaban-arch/SENTINEL/actions/workflows/tests.yml)
[![codecov](https://codecov.io/gh/mukalshaban-arch/SENTINEL/branch/master/graph/badge.svg)](https://codecov.io/gh/mukalshaban-arch/SENTINEL)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**An offline-first intelligence tracking and link-analysis dashboard.**

SENTINEL lets a small analyst team track Persons of Interest, Groups of
Interest, activities, hotspots, and country profiles; ingest raw documents
and photos into structured records using local AI (no cloud API required for
any of it); and chart connections between people, groups, and countries in
an interactive link-analysis diagram similar to i2 Analyst's Notebook.

It's built to run on a single Windows machine or small intranet, with
PostgreSQL as its only hard external dependency. Everything else —
entity extraction, OCR, face matching, map tiles — runs locally once its
one-time model downloads are cached.

---

## Contents

- [What it does](#what-it-does)
- [Tech stack](#tech-stack)
- [Project structure](#project-structure)
- [Quick start](#quick-start)
- [Default logins](#default-logins)
- [Roles & access](#roles--access)
- [API surface](#api-surface)
- [Offline-by-design, honestly](#offline-by-design-honestly)
- [Known limitations](#known-limitations)

---

## What it does

### Core records
- **Persons of Interest** — full profile, risk level, nationality, photos,
  tags, notes, custom fields, timeline, known locations, relationships.
- **Groups of Interest** — profile, threat level, members, leader, base of
  operations, same extras as persons.
- **Activities & Hotspots** — logged events with type/severity/date, plotted
  on a GIS map; named hotspot locations with a risk rating.
- **Country Profiles** — automatically aggregated from person nationalities
  and group bases; validated against a real ~180-country list so typos or
  extraction noise never show up as a fake "country."
- **Intel Reports** — a searchable report library.

### Intel/Analysis module (fully offline)
Upload a document (PDF, Word, scanned image, plain text) or a batch of them.
The server:
1. Extracts text (native for PDF/DOCX; **PaddleOCR primary, EasyOCR
   fallback** for images/scanned pages)
2. Runs entity extraction (**spaCy NER + rule-based enrichment** — nationality,
   aliases, activity type/date, hotspot type) with a relevance filter so it
   surfaces people/groups/places actually *doing something*, not every name
   dropped in a byline or a citation
3. Auto-geocodes extracted locations against an offline gazetteer and creates
   map hotspots (with proximity de-duplication via geopandas/shapely)
4. Presents everything on a review screen with **per-item checkboxes** — the
   analyst picks exactly what gets written to the system, nothing is
   committed sight-unseen

### Face Search (fully offline)
Every photo uploaded to a Person of Interest is automatically face-detected
and embedded (**InsightFace buffalo_l + onnxruntime**, CPU). Upload a new
photo of a suspect — even one who's changed appearance over the years — and
get back every Person of Interest ranked by facial resemblance, with a
percentage and a "likely match" flag. A similarity-ranking tool to guide
investigation, not a forensic identification system — always verify a match
manually.

### Link Analysis (i2-style)
A dedicated interactive diagramming workspace. Create named, saved charts;
add persons, groups, or countries as nodes; draw and label relationships
between them. Existing group memberships and person-to-person contacts are
**auto-discovered** and shown as edges without re-entering anything. Drag to
arrange, double-click a node to jump to its record, right-click to remove a
node or delete an analyst-drawn link.

### Maps
GIS maps throughout the app run on **MapLibre GL** against OpenFreeMap's free
public vector-tile endpoint (no self-hosting, no API key) — the one feature
that needs live internet; every pin/marker is fully local data regardless.
Printed reports embed a static map snapshot (rendered offscreen, captured to
an image) rather than a live map, since a print window can't run WebGL.
For a genuinely offline deployment, point `SENTINEL_MBTILES_PATH` at a
downloaded `.mbtiles` package instead — see `DEPLOYMENT.md`.

### AI narrative assessment (the one online-only feature)
A short AI-written intelligence summary on person/group pages, clearly
marked "⚠ Requires internet" in the UI. Uses the Anthropic API. Everything
else in SENTINEL works without any API key.

---

## Tech stack

| Layer | Choice |
|---|---|
| Backend | Python 3.11, stdlib `http.server` (no framework) |
| Database | PostgreSQL |
| Auth | JWT (HMAC-SHA256, stdlib `hmac`), bcrypt password hashing |
| OCR | PaddleOCR (primary) + EasyOCR (fallback), CPU |
| NLP | spaCy (NER) + custom rule-based enrichment |
| Face recognition | InsightFace (buffalo_l) + onnxruntime, CPU |
| Geospatial | geopandas, shapely, offline gazetteer (GeoNames-based) |
| Maps | MapLibre GL JS (vector tiles) — OpenFreeMap public endpoint, or a local `.mbtiles` package |
| Link diagrams | vis-network |
| Frontend | Plain HTML/CSS/JS, no build step, no framework |

All heavier ML dependencies (PaddleOCR/PaddlePaddle, EasyOCR/torch, spaCy,
InsightFace/onnxruntime, geopandas) download their model weights once, on
first use, while online, then run fully offline. See `DEPLOYMENT.md` for the
exact commands and expected download sizes.

---

## Project structure

```
SENTINEL/
├── server.py              HTTP server — every /api/* route
├── db.py                  PostgreSQL connection pool
├── auth.py                JWT issue/verify, password hashing, lockout
├── nationalities.py       Demonym ↔ country resolution + validation
├── geocode.py             Offline place-name → coordinates (gazetteer)
├── tiles.py                Map tile provider (disk cache / .mbtiles / live upstream)
├── nlp.py                 NLP job orchestration, DB commit logic
├── nlp_extract.py         spaCy entity extraction + relevance filtering
├── ocr_offline.py         PaddleOCR/EasyOCR wrapper
├── face_match.py          InsightFace embedding + similarity search
├── summarize.py           Optional online AI narrative assessments
├── schema.sql             Full database schema (idempotent, safe to re-run)
├── sample_data.sql        Seed data for a fresh install
├── requirements.txt       Python dependencies
├── .env                   Config (DB creds, JWT secret, feature flags)
├── DEPLOYMENT.md          Full install/setup guide
├── scripts/
│   ├── load_gazetteer.py          Load GeoNames data for offline geocoding
│   ├── prefetch_tiles.py          Warm the map tile cache (policy-compliant sources only)
│   └── backfill_face_embeddings.py  Embed photos already in the DB
└── static/                All frontend pages (no build step)
    ├── dashboard.html, persons.html, person.html, groups.html, group.html
    ├── activities_hotspots.html, activity.html, countries.html
    ├── analysis.html          NLP Analyser + Face Search + Intel Reports
    ├── linkanalysis.html      Link Analysis diagrams
    ├── admin.html, viewer.html, login.html, index.html
    ├── sentinel.js            Shared API client, UI components, map/link helpers
    ├── sentinel.css           Shared styling
    └── vendor/                Self-hosted MapLibre GL, vis-network, fonts
```

---

## Quick start

Full instructions (PostgreSQL setup, all dependency installs, model
downloads, troubleshooting) are in **`DEPLOYMENT.md`**. Short version:

```bat
:: 1. PostgreSQL running, database + role created, schema + sample data loaded
psql -U postgres -c "CREATE ROLE sentinel_user WITH LOGIN PASSWORD '...';"
psql -U postgres -c "CREATE DATABASE sentinel OWNER sentinel_user;"
psql -U postgres -d sentinel -f schema.sql
psql -U postgres -d sentinel -f sample_data.sql

:: 2. Python environment
python -m venv venv
venv\Scripts\python.exe -m pip install -r requirements.txt

:: 3. Configure
:: Edit .env — set SENTINEL_DB_PASS to match, generate SENTINEL_JWT_SECRET:
python -c "import secrets; print(secrets.token_hex(32))"

:: 4. Run
venv\Scripts\python.exe server.py
```

Open `http://localhost:8090`.

---

## Default logins

| Username | Password | Role |
|---|---|---|
| `admin` | `Sentinel@2024!` | Administrator |
| `analyst` | `Sentinel@2024!` | Intelligence Analyst |
| `viewer` | `Sentinel@2024!` | Read-only Viewer |

Change these immediately in a real deployment.

---

## Roles & access

| Feature | ADMIN | ANALYST | VIEWER |
|---|---|---|---|
| Sidebar shows | Admin Panel only | Dashboard + full Intelligence section | Dashboard + full Intelligence section |
| View records, search, maps, reports | — | ✅ | ✅ |
| Create/edit persons, groups, activities, hotspots | — | ✅ | ❌ |
| Run NLP extraction, face search, link analysis edits | — | ✅ | ❌ |
| Delete any record | — | ❌ | ❌ |
| User management, audit log, backups | ✅ | ❌ | ❌ |

ADMIN is scoped to system administration only (user management, audit log,
backups) and doesn't see intelligence data in its own sidebar — a
separation-of-duties design, not an oversight.

---

## API surface

Everything is under `/api/`, JWT bearer auth (`Authorization: Bearer <token>`)
after `POST /api/auth/login`. Highlights:

| Area | Endpoints |
|---|---|
| Core entities | `/api/persons`, `/api/groups`, `/api/activities`, `/api/hotspots`, `/api/intel` (+ `/:id`) |
| Country profiles | `/api/countries`, `/api/countries/:name`, `/api/countries/known-list` |
| Generic extras | `/api/{person\|group\|activity\|location}/:id/{tags\|notes\|fields\|attachments\|images\|locations\|relationships}` |
| NLP pipeline | `/api/nlp/submit`, `/api/nlp/jobs`, `/api/nlp/jobs/:id`, `/api/nlp/jobs/:id/commit`, `/api/nlp/jobs/:id/reject` |
| Face search | `/api/face/search` |
| Link analysis | `/api/link-charts` (+ `/:id`, `/:id/nodes`, `/:id/nodes/:id`) |
| Admin | `/api/users`, `/api/audit`, `/api/backups` |

---

## Offline-by-design, honestly

SENTINEL was built to minimize external dependencies, but two things
genuinely need the internet:

1. **Map basemap imagery** (MapLibre + OpenFreeMap) — your data stays local;
   only the tile images are fetched live. Configure `SENTINEL_MBTILES_PATH`
   for a fully offline alternative.
2. **AI narrative assessments** (`summarize.py`) — clearly marked in the UI,
   skippable entirely.

Everything else — OCR, entity extraction, face recognition, geocoding,
hotspot de-duplication — runs on-box once its models are cached, with no
runtime network calls.

---

## Known limitations

- **spaCy's small model** (`en_core_web_sm`, the default) has real accuracy
  limits on unusual/non-Western names — a documented, honest trade-off of
  offline NER vs. an LLM. The analyst review step exists specifically to
  catch what it misses. Set `SENTINEL_SPACY_MODEL` to a larger model for
  better accuracy.
- **Face search is a similarity ranking, not forensic identification.**
  Appearance changes, image quality, and pose can all lower a true-match
  score. Treat results as investigative leads.
- **Country/nationality resolution** covers ~180 countries with common
  demonyms — obscure or historical nationality terms may not resolve and
  will be treated as unrecognized rather than guessed at.
- **Gazetteer (offline geocoding)** must be loaded separately
  (`scripts/load_gazetteer.py` with a GeoNames export) — without it,
  extracted locations won't auto-plot on the map, though everything else in
  the NLP pipeline still works.
