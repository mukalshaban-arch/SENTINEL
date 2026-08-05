# SENTINEL — Full Deployment Guide
## Fresh install with sample data + NLP module

---

## Step 1 — Install PostgreSQL

Download from https://www.postgresql.org/download/windows/
During install, note the `postgres` superuser password you set.

Add to your system PATH:
```
C:\Program Files\PostgreSQL\17\bin
```
(adjust version number as needed)

Verify:
```bat
psql --version
```

---

## Step 2 — Create database and user

```bat
psql -U postgres
```

```sql
CREATE USER sentinel_user WITH PASSWORD 'YourStrongPassword123!';
CREATE DATABASE sentinel OWNER sentinel_user;
GRANT ALL PRIVILEGES ON DATABASE sentinel TO sentinel_user;
\q
```

---

## Step 3 — Apply schema and sample data

```bat
cd C:\Users\User\SENTINEL
psql -U sentinel_user -d sentinel -f schema.sql
psql -U sentinel_user -d sentinel -f sample_data.sql
```

Expected output for sample_data.sql:
```
INSERT 0 3    ← users
INSERT 0 6    ← locations
INSERT 0 10   ← POIs
INSERT 0 5    ← groups
...
```

---

## Step 4 — Install Python dependencies

SENTINEL's NLP/OCR/mapping pipeline is **fully offline** — no external API
calls, no internet needed at runtime. It's built on PaddleOCR + EasyOCR
(OCR), spaCy (entity extraction), and geopandas/shapely/folium (geospatial).
The only feature that still calls out to the internet is the optional
Claude-based "AI narrative assessment" panel on person/group pages — see the
note at the end of this step.

### Core (required):
```bat
pip install psycopg2-binary bcrypt pdfminer.six python-docx --trusted-host pypi.org --trusted-host files.pythonhosted.org
```

### Offline OCR (image / scanned-PDF text extraction):

| Package | Purpose |
|---|---|
| `paddleocr` + `paddlepaddle` | Primary OCR engine |
| `easyocr` | Fallback OCR engine if PaddleOCR fails on a given image |
| `Pillow` | Image handling |

```bat
pip install paddleocr paddlepaddle easyocr Pillow --trusted-host pypi.org --trusted-host files.pythonhosted.org
```

> **Known issue:** recent `paddlepaddle` + oneDNN can crash on some CPUs with
> `NotImplementedError (...onednn_instruction.cc)`. SENTINEL already runs
> PaddleOCR with `enable_mkldnn=False` to avoid this — no action needed, but
> if you call PaddleOCR directly elsewhere, do the same.

Both engines download their model weights **once**, the first time OCR
actually runs (a few hundred MB total, cached under `%USERPROFILE%\.paddlex`
and `%USERPROFILE%\.EasyOCR`). After that first run, OCR works fully offline.
If neither engine's weights are cached and there's no internet, OCR calls
return a placeholder message instead of crashing.

### Offline NLP entity extraction:

```bat
pip install spacy python-dateutil --trusted-host pypi.org --trusted-host files.pythonhosted.org
```

spaCy also needs a language **model**, which is not a normal pip package.
Download it (needs internet, once):
```bat
python -c "import urllib.request; urllib.request.urlretrieve('https://huggingface.co/spacy/en_core_web_sm/resolve/main/en_core_web_sm-any-py3-none-any.whl', 'en_core_web_sm-3.8.0-py3-none-any.whl')"
pip install en_core_web_sm-3.8.0-py3-none-any.whl
```
The small model (`en_core_web_sm`) works but has noticeably lower accuracy on
unusual/non-Western names than a larger model. For better results, replace
`en_core_web_sm` above with `en_core_web_lg` or `en_core_web_trf` (larger
downloads), and set `SENTINEL_SPACY_MODEL` in `.env` to match.

### Offline geospatial (hotspot de-duplication, map data):
```bat
pip install geopandas shapely folium pandas --trusted-host pypi.org --trusted-host files.pythonhosted.org
```

### Offline face recognition (Analysis → Face Search):
```bat
pip install insightface onnxruntime --trusted-host pypi.org --trusted-host files.pythonhosted.org
```
Downloads the `buffalo_l` model pack (~280MB) automatically the first time
it's used, while online — fully offline after that (cached under
`%USERPROFILE%\.insightface`). Every photo uploaded to a Person of Interest
(profile photo, likeness, gallery, or the images panel) is automatically
embedded for matching. To backfill embeddings for photos that were already
in the database before this feature was added:
```bat
python scripts\backfill_face_embeddings.py
```
This is a similarity ranking to guide investigation, not a forensic
identification tool — always verify a match manually.

> If you skip any of the above, the server still runs — those specific
> features just log a warning and return a clear placeholder instead of
> extracted data.

### Optional: the online narrative-assessment feature
The "Generate Assessment" button on person/group pages (a short AI-written
narrative summary, not entity extraction) still uses the Anthropic API and
needs `ANTHROPIC_API_KEY` + internet. Everything else does not.
```bat
pip install anthropic --trusted-host pypi.org --trusted-host files.pythonhosted.org
```
Skip this if you don't need that one panel — it's clearly marked
"Requires internet" in the UI and every other feature works without it.

---

## Step 5 — Configure .env

```bat
copy .env.example .env
notepad C:\Users\User\SENTINEL\.env
```

Fill in:
```env
SENTINEL_DB_PASS=YourStrongPassword123!
SENTINEL_JWT_SECRET=<generate below>
SENTINEL_SPACY_MODEL=en_core_web_sm
```

Generate JWT secret:
```bat
python -c "import secrets; print(secrets.token_hex(32))"
```

`ANTHROPIC_API_KEY` is optional — only needed for the "AI narrative
assessment" panel on person/group pages (get one from
https://console.anthropic.com/). The NLP document-extraction module does not
use it.

---

## Step 6 — Place files

Your SENTINEL folder should look like this:
```
C:\Users\User\SENTINEL\
├── server.py          ← new
├── db.py              ← new
├── auth.py            ← new
├── nlp.py             ← new
├── nlp_extract.py     ← new (offline spaCy entity extraction)
├── ocr_offline.py     ← new (PaddleOCR + EasyOCR)
├── geocode.py         ← new (offline gazetteer lookup)
├── summarize.py       ← new (optional, online-only narrative assessments)
├── schema.sql         ← new (already run)
├── sample_data.sql    ← new (already run)
├── .env               ← new (filled in)
├── .env.example       ← new (template, keep for reference)
└── static\
    ├── index.html
    ├── login.html
    ├── sentinel.js
    ├── sentinel.css
    └── ... (other pages)
```

---

## Step 7 — Start the server

```bat
cd C:\Users\User\SENTINEL
python server.py
```

Expected output:
```
INFO  sentinel.server – SENTINEL listening on http://0.0.0.0:8080
```

Open: http://localhost:8080

---

## Step 8 — Login credentials

All sample users share password: **Sentinel@2024!**

| Username | Role | Access |
|---|---|---|
| `admin` | Admin | Full access including user management and backups |
| `analyst` | Analyst | Create/edit/delete all entities, run NLP |
| `viewer` | Viewer | Read-only access |

---

## Step 9 — Test the NLP module

### Quick text test (no files needed):
Using curl or any REST client:
```bat
curl -X POST http://localhost:8080/api/nlp/submit ^
  -H "Authorization: Bearer <your-token>" ^
  -H "Content-Type: application/json" ^
  -d "{\"text\": \"Intelligence report: Viktor Sorokin met with Chen Wei at Mombasa port on 14 December. The Haraka Network is believed to be involved.\"}"
```

Response:
```json
{ "job_id": 1, "status": "pending", "message": "Job queued. Poll GET /api/nlp/jobs/1 for status." }
```

Poll for results:
```bat
curl http://localhost:8080/api/nlp/jobs/1 -H "Authorization: Bearer <token>"
```

Wait for `"status": "reviewed"`, then review the extracted entities (returned
in the `claude_output` field — the name is historical; it now holds output
from the offline spaCy pipeline, not Claude) and commit:
```bat
curl -X POST http://localhost:8080/api/nlp/jobs/1/commit -H "Authorization: Bearer <token>"
```

### File upload test:
```bat
curl -X POST http://localhost:8080/api/nlp/submit ^
  -H "Authorization: Bearer <token>" ^
  -F "files[]=@C:\path\to\report.pdf" ^
  -F "files[]=@C:\path\to\suspect_photo.jpg"
```

Supported file types: `.txt`, `.csv`, `.pdf`, `.doc`, `.docx`, `.jpg`, `.jpeg`, `.png`, `.tiff`, `.bmp`, `.webp`

---

## Step 10 — Offline map tiles

Without any setup, GIS maps show a neutral placeholder grid — pins, popups,
and all data work fine, there's just no photographic basemap underneath.

**Recommended for a real offline deployment:** download a pre-made `.mbtiles`
package (a standard SQLite tile package) for your area of operations from a
provider whose terms permit offline redistribution (e.g. MapTiler's
downloadable regional exports, or protomaps.com). This is a normal one-time
download through their site, not a scripted API call. Then in `.env`:
```env
SENTINEL_MBTILES_PATH=D:\SENTINEL\tiles\region.mbtiles
```
Restart the server — tiles are read straight from the package, no network
call at runtime, ever.

**Do not** point `scripts/prefetch_tiles.py` at a public "for browsers" tile
server like `tile.openstreetmap.org` and run it at any real volume — their
usage policy prohibits scripted bulk access, and the server responds to
violations by silently serving a "blocked" notice *image* (HTTP 200, looks
like a normal tile) instead of an error, which used to get cached as if it
were real map data. `tiles.py` now detects and rejects that, but the
underlying access is still against that provider's policy — use `--upstream`
only against a provider/plan that actually allows it, at a light `--delay`.

---

## Backup

```bat
curl -X POST http://localhost:8080/api/admin/backup -H "Authorization: Bearer <admin-token>"
```

Backup file saved to: `C:\Users\User\SENTINEL\backups\sentinel_YYYYMMDD_HHMMSS.sql.gz`

Restore:
```bat
pg_restore -U sentinel_user -d sentinel C:\Users\User\SENTINEL\backups\sentinel_20241201_120000.sql.gz
```

---

## Troubleshooting

| Error | Fix |
|---|---|
| `SENTINEL_JWT_SECRET` error on start | Generate and set in .env |
| `psycopg2.OperationalError` password | Check .env DB pass matches PostgreSQL |
| `OSError: Can't find model 'en_core_web_sm'` | The spaCy language model isn't installed — see Step 4 |
| NLP extraction returns nothing / everything empty | Same as above — extraction silently returns empty results (not a failure) when no spaCy model is loaded |
| Images/scanned PDFs return `[OCR unavailable...]` | Neither PaddleOCR nor EasyOCR has cached model weights yet — run any OCR once while online (Step 4) to cache them |
| PaddleOCR crashes with `onednn_instruction.cc` error | Known paddlepaddle/oneDNN bug — SENTINEL already sets `enable_mkldnn=False` in `ocr_offline.py`; if you see this elsewhere, apply the same flag |
| NLP job stuck in `pending` | Check sentinel.log for errors |
| NLP job shows `failed` | Check sentinel.log — a genuine crash (e.g. DB error), not a missing-model case (those return empty results, not `failed`) |
| "Generate Assessment" button fails | That one feature needs `ANTHROPIC_API_KEY` + internet — see Step 4's optional section |
| Maps show a dark grid, no imagery | Expected until you set `SENTINEL_MBTILES_PATH` — see Step 10 |
| sentinel.log: "byte-identical to the previous tile" | The configured tile upstream is rate-limiting/blocking you — stop the prefetch job, see Step 10 |
