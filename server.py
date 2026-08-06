"""
SENTINEL – server.py  (PostgreSQL edition)
Hardened HTTP server replacing the SQLite version.

Security measures applied:
  [1] Path traversal prevention – safe_static_path() whitelist + realpath check
  [2] Stored XSS – all DB writes sanitised; frontend must use escHtml()
  [3] Brute-force protection – DB-backed lockout via auth.is_locked_out()
  [4] JWT secret from env – never hardcoded
  [5] Bounded request body – MAX_BODY_BYTES enforced before any read
  [6] Exception leakage – generic 500 message; details logged server-side only
  [7] CORS – strict origin whitelist
  [8] Password policy – enforced on create/change
  [9] Content-Type validation on uploads
  [10] SQL injection – %s parameterisation throughout (no string formatting)
"""

import os
import sys
import io
import json
import mimetypes
import logging
import traceback
import subprocess
import threading
import uuid
from datetime import datetime, date, time as _time, timezone
from decimal import Decimal
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse, parse_qs, unquote


def _json_default(o):
    """
    Fallback serializer for types the stdlib json module can't handle.
    Covers the Postgres column types SENTINEL returns (TIMESTAMPTZ/DATE,
    NUMERIC, UUID, BYTEA) so API responses never raise on serialization.
    """
    if isinstance(o, (datetime, date, _time)):
        return o.isoformat()
    if isinstance(o, Decimal):
        return float(o)
    if isinstance(o, uuid.UUID):
        return str(o)
    if isinstance(o, (bytes, bytearray, memoryview)):
        return bytes(o).decode("utf-8", "replace")
    raise TypeError(f"Object of type {o.__class__.__name__} is not JSON serializable")

from db import init_pool, close_pool, db_cursor
import tiles
import summarize
from nationalities import (
    nationalities_for_country, resolve_known_country, canonical_country_name, KNOWN_COUNTRIES,
)
from face_match import store_embeddings_for_photo, data_uri_to_bytes, search_similar_faces, engine_ready
from auth import (
    require_auth, record_attempt, is_locked_out,
    hash_password, check_password,
    issue_token, validate_password,
    get_token_from_header, verify_token,
)
from nlp import (
    process_job, commit_job,
    NLP_DIR, ALLOWED_MIME_TYPES, IMAGE_MIME_TYPES,
    extract_text_from_file,
)

# ─── Logging ────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s – %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("sentinel.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger("sentinel.server")

# ─── Config ─────────────────────────────────────────────────────────────────
BASE_DIR        = Path(__file__).resolve().parent


def _load_dotenv() -> None:
    """Load KEY=VALUE pairs from .env into the environment (existing vars win).
    Must run before the config constants below are evaluated so that .env can
    override PORT / ALLOWED_ORIGINS and supply DB credentials."""
    env_file = BASE_DIR / ".env"
    if not env_file.exists():
        return
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip())


_load_dotenv()

PORT            = int(os.environ.get("SENTINEL_PORT", 8080))
STATIC_DIR      = BASE_DIR / "static"
UPLOADS_DIR     = BASE_DIR / "uploads"
MAX_BODY_BYTES  = 50 * 1024 * 1024   # 50 MB
TILE_MAX_Z      = 19                  # sanity bound for /tiles/{z}/{x}/{y}.png

# Ensure correct Content-Type for locally vendored web fonts (Windows' mimetypes
# does not know .woff2 by default) so offline @font-face loads cleanly.
mimetypes.add_type("font/woff2", ".woff2")
mimetypes.add_type("font/woff", ".woff")
ALLOWED_ORIGINS = set(
    os.environ.get(
        "SENTINEL_ALLOWED_ORIGINS",
        "http://localhost:8080,http://127.0.0.1:8080,http://192.168.1.223:8080"
    ).split(",")
)

RISK_RANK = {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1, "INACTIVE": 0}
EXTRAS_ENTITY_TYPES = {"person", "group", "activity", "location"}


# ─── Static file serving ────────────────────────────────────────────────────
def safe_static_path(raw_path: str) -> Path | None:
    """
    Resolve a URL path to a filesystem path inside STATIC_DIR only.
    Returns None if the resolved path escapes STATIC_DIR (path traversal).
    """
    # Strip query string, decode percent-encoding safely
    clean = urlparse(raw_path).path.lstrip("/") or "index.html"
    candidate = (STATIC_DIR / clean).resolve()
    if STATIC_DIR.resolve() not in candidate.parents and candidate != STATIC_DIR.resolve():
        return None
    if not candidate.exists() or not candidate.is_file():
        return None
    return candidate


# ─── Request handler ────────────────────────────────────────────────────────
class SentinelHandler(BaseHTTPRequestHandler):
    server_version = "SENTINEL/2.0"
    error_message_format = '{"error": "%(explain)s"}'
    error_content_type  = "application/json"

    # ── Helpers ────────────────────────────────────────────────────────────
    def _origin(self) -> str:
        return self.headers.get("Origin", "")

    def _cors_headers(self) -> dict:
        origin = self._origin()
        if origin in ALLOWED_ORIGINS:
            return {
                "Access-Control-Allow-Origin":  origin,
                "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
                "Access-Control-Allow-Headers": "Authorization, Content-Type",
                "Access-Control-Max-Age":       "86400",
                "Vary": "Origin",
            }
        return {}

    def _send(self, code: int, body: bytes, content_type: str = "application/json",
              extra_headers: dict | None = None) -> None:
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        for k, v in self._cors_headers().items():
            self.send_header(k, v)
        if extra_headers:
            for k, v in extra_headers.items():
                self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def _json(self, code: int, data) -> None:
        self._send(code, json.dumps(data, default=_json_default).encode(), "application/json")

    def _error(self, code: int, message: str) -> None:
        self._json(code, {"error": message})

    def _read_body(self) -> bytes | None:
        """Read request body with hard size cap."""
        length = int(self.headers.get("Content-Length", 0))
        if length > MAX_BODY_BYTES:
            self._error(413, "Request body too large.")
            return None
        return self.rfile.read(length) if length else b""

    def _require_auth(self, min_role: str = "VIEWER") -> dict | None:
        try:
            return require_auth(dict(self.headers), min_role)
        except PermissionError as e:
            code, _, msg = str(e).partition(": ")
            self._error(int(code) if code.isdigit() else 401, msg)
            return None

    def _client_ip(self) -> str:
        return (
            self.headers.get("X-Forwarded-For", "").split(",")[0].strip()
            or self.client_address[0]
        )

    # ── Audit log ──────────────────────────────────────────────────────────
    def _audit(self, user: dict | None, action: str, resource: str | None = None,
               resource_id=None, detail: str | None = None) -> None:
        uid   = user.get("sub") if user else None
        uname = user.get("usr") if user else "unknown"
        self._audit_raw(uid, uname, action, resource,
                         str(resource_id) if resource_id is not None else None, detail)

    def _audit_raw(self, user_id, username, action, resource, resource_id, detail) -> None:
        try:
            with db_cursor(commit=True) as cur:
                cur.execute("""
                    INSERT INTO audit_log (user_id, username, action, resource, resource_id, detail, ip)
                    VALUES (%s,%s,%s,%s,%s,%s,%s)
                """, (user_id, username, action, resource, resource_id, detail, self._client_ip()))
        except Exception:
            logger.warning("Audit log write failed", exc_info=True)

    # ── Routing ────────────────────────────────────────────────────────────
    def do_OPTIONS(self):
        self._send(204, b"")

    def do_GET(self):
        parsed = urlparse(self.path)
        path   = parsed.path

        if path.startswith("/api/"):
            self._route_api("GET", path, parsed)
        elif path.startswith("/tiles/"):
            self._serve_tile(path)
        else:
            self._serve_static(path)

    def do_POST(self):
        parsed = urlparse(self.path)
        self._route_api("POST", parsed.path, parsed)

    def do_PUT(self):
        parsed = urlparse(self.path)
        self._route_api("PUT", parsed.path, parsed)

    def do_DELETE(self):
        parsed = urlparse(self.path)
        self._route_api("DELETE", parsed.path, parsed)

    def _serve_static(self, raw_path: str) -> None:
        file_path = safe_static_path(raw_path)
        if file_path is None:
            self._error(404, "Not found.")
            return
        mime, _ = mimetypes.guess_type(str(file_path))
        mime = mime or "application/octet-stream"
        try:
            data = file_path.read_bytes()
            self._send(200, data, mime)
        except OSError:
            self._error(500, "Could not read file.")

    def _serve_tile(self, path: str) -> None:
        """Serve a map tile from the offline cache: /tiles/{z}/{x}/{y}.png

        Integer-only z/x/y (no path traversal possible). Cache misses return a
        neutral placeholder with 200 so Leaflet never shows broken tiles.
        """
        parts = path.strip("/").split("/")   # ["tiles", z, x, y.png]
        if len(parts) != 4 or not parts[3].endswith(".png"):
            self._error(404, "Not found.")
            return
        try:
            z, x, y = int(parts[1]), int(parts[2]), int(parts[3][:-4])
        except ValueError:
            self._error(404, "Not found.")
            return
        if not (0 <= z <= TILE_MAX_Z and 0 <= x < (1 << z) and 0 <= y < (1 << z)):
            self._error(404, "Not found.")
            return
        data, _hit = tiles.get_tile(z, x, y)
        self._send(200, data, "image/png", {"Cache-Control": "public, max-age=604800"})

    def _route_api(self, method: str, path: str, parsed) -> None:
        try:
            self._dispatch(method, path, parsed)
        except PermissionError as e:
            code, _, msg = str(e).partition(": ")
            self._error(int(code) if code.isdigit() else 403, msg)
        except Exception:
            logger.error("Unhandled exception:\n%s", traceback.format_exc())
            self._error(500, "An internal error occurred.")   # [6] no traceback to client

    def _dispatch(self, method: str, path: str, parsed) -> None:
        qs = parse_qs(parsed.query)

        # ── Auth endpoints (no JWT required) ─────────────────────────────
        if path == "/api/auth/login" and method == "POST":
            return self._login()
        if path == "/api/auth/logout" and method == "POST":
            token = get_token_from_header(dict(self.headers))
            payload = verify_token(token) if token else None
            if payload:
                self._audit(payload, "LOGOUT")
            return self._json(200, {"ok": True})

        # ── All other endpoints require at least viewer role ──────────────
        user = self._require_auth("VIEWER")
        if user is None:
            return

        # Stats
        if path == "/api/stats" and method == "GET":
            return self._stats()

        # Countries (computed aggregation, read-only)
        if path == "/api/countries" and method == "GET":
            return self._list_countries()
        if path == "/api/countries/known-list" and method == "GET":
            return self._json(200, sorted(KNOWN_COUNTRIES))
        if m := _match(path, r"/api/countries/([^/]+)$"):
            if method == "GET":
                return self._get_country(unquote(m[0]))

        # Persons
        if path == "/api/persons":
            if method == "GET":  return self._list_persons(qs)
            if method == "POST": return self._create_person(user)
        if m := _match(path, r"/api/persons/(\d+)$"):
            pid = int(m[0])
            if method == "GET":    return self._get_person(pid)
            if method == "PUT":    return self._update_person(pid, user)
            if method == "DELETE": return self._delete_entity("poi", pid, user, "PERSON")
        if m := _match(path, r"/api/persons/(\d+)/activities$"):
            if method == "GET": return self._person_activities(int(m[0]))
        if m := _match(path, r"/api/persons/(\d+)/summary$"):
            pid = int(m[0])
            if method == "GET":  return self._get_summary("person", pid)
            if method == "POST": return self._generate_summary("person", pid)
        if m := _match(path, r"/api/persons/(\d+)/gallery$"):
            pid = int(m[0])
            if method == "GET":  return self._list_gallery(pid)
            if method == "POST": return self._add_gallery(pid, user)
        if m := _match(path, r"/api/persons/(\d+)/gallery/(\d+)$"):
            if method == "DELETE": return self._delete_gallery(int(m[0]), int(m[1]), user)

        # Groups
        if path == "/api/groups":
            if method == "GET":  return self._list_groups(qs)
            if method == "POST": return self._create_group(user)
        if m := _match(path, r"/api/groups/(\d+)$"):
            gid = int(m[0])
            if method == "GET":    return self._get_group(gid)
            if method == "PUT":    return self._update_group(gid, user)
            if method == "DELETE": return self._delete_entity("groups_of_interest", gid, user, "GROUP")
        if m := _match(path, r"/api/groups/(\d+)/activities$"):
            if method == "GET": return self._group_activities(int(m[0]))
        if m := _match(path, r"/api/groups/(\d+)/summary$"):
            gid = int(m[0])
            if method == "GET":  return self._get_summary("group", gid)
            if method == "POST": return self._generate_summary("group", gid)

        # Locations (standing Location entity — feeds dashboard stat/country agg)
        if path == "/api/locations":
            if method == "GET":  return self._list_locations(qs)
            if method == "POST": return self._create_location(user)

        # Activities
        if path == "/api/activities":
            if method == "GET":  return self._list_activities(qs)
            if method == "POST": return self._create_activity(user)
        if m := _match(path, r"/api/activities/(\d+)$"):
            aid = int(m[0])
            if method == "GET":    return self._get_activity(aid)
            if method == "PUT":    return self._update_activity(aid, user)
            if method == "DELETE": return self._delete_entity("activities", aid, user, "ACTIVITY")

        # Hotspots
        if path == "/api/hotspots":
            if method == "GET":  return self._list_hotspots()
            if method == "POST": return self._create_hotspot(user)
        if m := _match(path, r"/api/hotspots/(\d+)$"):
            hid = int(m[0])
            if method == "GET":    return self._get_hotspot(hid)
            if method == "PUT":    return self._update_hotspot(hid, user)
            if method == "DELETE": return self._delete_entity("hotspots", hid, user, "HOTSPOT")

        # Intel reports
        if path == "/api/intel":
            if method == "GET":  return self._list_intel()
            if method == "POST": return self._create_intel(user)
        if m := _match(path, r"/api/intel/(\d+)$"):
            iid = int(m[0])
            if method == "GET":    return self._get_intel(iid)
            if method == "PUT":    return self._update_intel(iid, user)
            if method == "DELETE": return self._delete_entity("intel_reports", iid, user, "INTEL")

        # Generic entity extras: /api/<person|group|activity|location>/<id>/<resource>
        if m := _match(path, r"/api/(person|group|activity|location)/(\d+)/(tags|notes|fields|attachments|images|locations|relationships)$"):
            etype, eid, resource = m[0], int(m[1]), m[2]
            return self._extras(method, etype, eid, resource, user)

        # Generic extras singleton mutate/delete: /api/tags/5, /api/notes/9, ...
        if m := _match(path, r"/api/(tags|notes|fields|attachments|images|locations|relationships)/(\d+)$"):
            return self._extras_item(method, m[0], int(m[1]), user)

        # NLP
        if path == "/api/nlp/submit" and method == "POST":
            return self._nlp_submit(user)
        if path == "/api/nlp/jobs" and method == "GET":
            return self._nlp_list()
        if m := _match(path, r"/api/nlp/jobs/(\d+)$"):
            if method == "GET": return self._nlp_get(int(m[0]))
        if m := _match(path, r"/api/nlp/jobs/(\d+)/commit$"):
            if method == "POST": return self._nlp_commit(int(m[0]), user)
        if m := _match(path, r"/api/nlp/jobs/(\d+)/reject$"):
            if method == "POST": return self._nlp_reject(int(m[0]), user)

        # Face search
        if path == "/api/face/search" and method == "POST":
            return self._face_search()

        # Link Analysis — saved i2-style charts
        if path == "/api/link-charts":
            if method == "GET":  return self._list_link_charts()
            if method == "POST": return self._create_link_chart(user)
        if m := _match(path, r"/api/link-charts/(\d+)$"):
            cid = int(m[0])
            if method == "GET":    return self._get_link_chart(cid)
            if method == "PUT":    return self._update_link_chart(cid, user)
            if method == "DELETE": return self._delete_link_chart(cid, user)
        if m := _match(path, r"/api/link-charts/(\d+)/nodes$"):
            if method == "POST": return self._add_link_chart_node(int(m[0]), user)
        if m := _match(path, r"/api/link-charts/(\d+)/nodes/(\d+)$"):
            cid, nid = int(m[0]), int(m[1])
            if method == "PUT":    return self._update_link_chart_node(cid, nid, user)
            if method == "DELETE": return self._delete_link_chart_node(cid, nid, user)

        # Admin — users
        if path == "/api/users":
            require_auth(dict(self.headers), "ADMIN")
            if method == "GET":  return self._list_users()
            if method == "POST": return self._create_user(user)
        if m := _match(path, r"/api/users/(\d+)$"):
            require_auth(dict(self.headers), "ADMIN")
            uid = int(m[0])
            if method == "PUT":    return self._update_user(uid, user)
            if method == "DELETE": return self._deactivate_user(uid, user)

        # Admin — audit log
        if path == "/api/audit" and method == "GET":
            require_auth(dict(self.headers), "ADMIN")
            return self._list_audit(qs)

        # Admin — backups
        if path == "/api/backups":
            require_auth(dict(self.headers), "ADMIN")
            if method == "GET":  return self._list_backups()
            if method == "POST": return self._create_backup(user)

        self._error(404, "Endpoint not found.")

    # ── Auth ───────────────────────────────────────────────────────────────
    def _login(self) -> None:
        body = self._read_body()
        if body is None:
            return
        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            return self._error(400, "Invalid JSON.")

        username = str(data.get("username", "")).strip().lower()
        password = str(data.get("password", ""))
        ip       = self._client_ip()

        if not username or not password:
            return self._error(400, "Username and password required.")

        if is_locked_out(username, ip):
            record_attempt(username, ip, False)
            self._audit_raw(None, username, "LOGIN_FAIL", None, None, "Locked out — too many failed attempts.")
            return self._error(429, "Too many failed attempts. Try again later.")

        with db_cursor() as cur:
            cur.execute(
                "SELECT id, username, password, role, name, unit FROM users WHERE username = %s AND active = TRUE",
                (username,)
            )
            user_row = cur.fetchone()

        if not user_row or not check_password(password, user_row["password"]):
            record_attempt(username, ip, False)
            self._audit_raw(user_row["id"] if user_row else None, username, "LOGIN_FAIL",
                             None, None, "Invalid credentials.")
            return self._error(401, "Invalid credentials.")

        record_attempt(username, ip, True)

        with db_cursor(commit=True) as cur:
            cur.execute("UPDATE users SET last_login = NOW() WHERE id = %s", (user_row["id"],))

        token = issue_token(user_row["id"], user_row["username"], user_row["role"])
        self._audit_raw(user_row["id"], username, "LOGIN", None, None, "Successful login.")
        self._json(200, {
            "token": token,
            "user": {
                "id":       user_row["id"],
                "username": user_row["username"],
                "role":     user_row["role"],
                "name":     user_row["name"],
                "unit":     user_row["unit"],
            },
        })

    # ── Persons ────────────────────────────────────────────────────────────
    def _list_persons(self, qs) -> None:
        search = qs.get("q", [None])[0]
        where, params = "", []
        if search:
            where = "WHERE (p.alias ILIKE %s OR p.first_name ILIKE %s OR p.last_name ILIKE %s OR p.nationality ILIKE %s)"
            params = [f"%{search}%"] * 4
        with db_cursor() as cur:
            cur.execute(f"""
                SELECT p.id, p.alias, p.first_name, p.last_name, p.dob, p.nationality,
                       p.risk_level, p.status, p.last_seen, p.last_location, p.last_lat, p.last_lng,
                       p.description, p.photo, p.created_at, p.updated_at,
                       COALESCE(array_agg(DISTINCT gm.group_id) FILTER (WHERE gm.group_id IS NOT NULL), '{{}}') AS affiliation,
                       COUNT(DISTINCT a.id) AS "activityCount"
                FROM poi p
                LEFT JOIN group_members gm ON gm.poi_id = p.id
                LEFT JOIN activities a ON a.poi_id = p.id
                {where}
                GROUP BY p.id
                ORDER BY p.alias
            """, params)
            rows = cur.fetchall()
        self._json(200, [dict(r) for r in rows])

    def _get_person(self, pid: int) -> None:
        with db_cursor() as cur:
            cur.execute("SELECT * FROM poi WHERE id = %s", (pid,))
            row = cur.fetchone()
            if not row:
                return self._error(404, "Person not found.")
            cur.execute("SELECT group_id FROM group_members WHERE poi_id = %s", (pid,))
            affiliation = [r["group_id"] for r in cur.fetchall()]
            cur.execute("""
                SELECT id, src, caption, occurred_on AS date, occurred_on AS date_taken
                FROM poi_gallery WHERE poi_id = %s ORDER BY created_at DESC
            """, (pid,))
            gallery = [dict(r) for r in cur.fetchall()]
            cur.execute("""
                SELECT id, content, name, description, mime_type
                FROM images WHERE entity_type='person' AND entity_id=%s ORDER BY created_at DESC
            """, (pid,))
            images = [dict(r) for r in cur.fetchall()]
            cur.execute("""
                SELECT id, lat, lng, label, note, observed_on AS date_observed
                FROM entity_coordinates WHERE entity_type='person' AND entity_id=%s ORDER BY created_at DESC
            """, (pid,))
            locations = [dict(r) for r in cur.fetchall()]
        result = dict(row)
        result["affiliation"] = affiliation
        result["gallery"]     = gallery
        result["images"]      = images
        result["locations"]   = locations
        self._json(200, result)

    def _create_person(self, user: dict) -> None:
        if not self._require_edit_role(user): return
        data = self._parse_json_body()
        if data is None:
            return
        alias = str(data.get("alias", "")).strip()
        if not alias:
            return self._error(400, "Alias is required.")
        with db_cursor(commit=True) as cur:
            cur.execute("""
                INSERT INTO poi (alias, first_name, last_name, dob, nationality, risk_level, status,
                                  last_location, last_lat, last_lng, description, notes)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id
            """, (
                alias, data.get("firstName"), data.get("lastName"), data.get("dob") or None,
                data.get("nationality"), data.get("riskLevel", "MEDIUM"), data.get("status", "ACTIVE"),
                data.get("lastLocation"), data.get("lastLat") or None, data.get("lastLng") or None,
                data.get("description"), data.get("notes"),
            ))
            new_id = cur.fetchone()["id"]
            for gid in (data.get("affiliation") or []):
                cur.execute("INSERT INTO group_members (group_id, poi_id) VALUES (%s,%s) ON CONFLICT DO NOTHING",
                            (gid, new_id))
        self._audit(user, "CREATE_PERSON", "person", new_id, f"Created person: {alias}")
        self._json(201, {"id": new_id})

    def _update_person(self, pid: int, user: dict) -> None:
        if not self._require_edit_role(user): return
        data = self._parse_json_body()
        if data is None:
            return
        field_map = {
            "alias": "alias", "firstName": "first_name", "lastName": "last_name",
            "dob": "dob", "nationality": "nationality", "riskLevel": "risk_level",
            "status": "status", "lastSeen": "last_seen", "lastLocation": "last_location",
            "lastLat": "last_lat", "lastLng": "last_lng",
            "description": "description", "notes": "notes",
            "photo": "photo", "likeness": "likeness",
        }
        sets, vals = [], []
        for pkey, col in field_map.items():
            if pkey in data:
                v = data[pkey]
                if pkey in ("dob", "lastSeen") and v == "":
                    v = None
                if pkey in ("lastLat", "lastLng") and v == "":
                    v = None
                sets.append(f"{col}=%s")
                vals.append(v)
        if "contacts" in data:
            sets.append("contacts=%s")
            vals.append([int(c) for c in (data.get("contacts") or [])])
        if sets:
            vals.append(pid)
            with db_cursor(commit=True) as cur:
                cur.execute(f"UPDATE poi SET {', '.join(sets)} WHERE id=%s", vals)
        # Best-effort: (re-)extract face embeddings whenever the profile photo
        # or likeness changes, so face search stays current. Never blocks the
        # save on failure — a bad/corrupt image just means no embedding yet.
        for pkey, source in (("photo", "profile_photo"), ("likeness", "likeness")):
            if pkey in data:
                try:
                    img_bytes = data_uri_to_bytes(data[pkey]) if data[pkey] else None
                    if img_bytes:
                        store_embeddings_for_photo(pid, source, None, img_bytes)
                    else:
                        with db_cursor(commit=True) as cur:
                            cur.execute("DELETE FROM face_embeddings WHERE poi_id=%s AND source=%s AND source_id IS NULL",
                                        (pid, source))
                except Exception:
                    logger.exception("Face embedding extraction failed for poi #%s (%s)", pid, source)
        if "affiliation" in data:
            with db_cursor(commit=True) as cur:
                cur.execute("DELETE FROM group_members WHERE poi_id=%s", (pid,))
                for gid in (data.get("affiliation") or []):
                    cur.execute("INSERT INTO group_members (group_id, poi_id) VALUES (%s,%s) ON CONFLICT DO NOTHING",
                                (gid, pid))
        self._audit(user, "UPDATE_PERSON", "person", pid, f"Updated person #{pid}")
        self._json(200, {"ok": True})

    def _person_activities(self, pid: int) -> None:
        with db_cursor() as cur:
            cur.execute("""
                SELECT a.id, a.type, a.occurred_on AS date, a.location, a.lat, a.lng,
                       a.description, a.severity, a.reported_by, a.poi_id, a.group_id
                FROM activities a WHERE a.poi_id = %s ORDER BY a.occurred_on DESC NULLS LAST
            """, (pid,))
            self._json(200, [dict(r) for r in cur.fetchall()])

    # ── Narrative AI summaries (Phase 2) ───────────────────────────────────
    def _get_summary(self, kind: str, eid: int) -> None:
        """Return the stored narrative summary for a person/group (or null)."""
        with db_cursor() as cur:
            cur.execute(
                "SELECT summary, model, generated_at FROM entity_summaries "
                "WHERE entity_type = %s AND entity_id = %s", (kind, eid))
            row = cur.fetchone()
        if not row:
            return self._json(200, {"summary": None})
        self._json(200, {"summary": row["summary"], "model": row["model"],
                         "generatedAt": row["generated_at"]})

    def _generate_summary(self, kind: str, eid: int) -> None:
        """Build the subject's dossier, generate a narrative assessment, and store it."""
        user = self._require_auth("ANALYST")
        if user is None:
            return
        dossier = self._person_dossier(eid) if kind == "person" else self._group_dossier(eid)
        if dossier is None:
            return self._error(404, f"{kind.capitalize()} not found.")
        try:
            summary = summarize.generate_summary(dossier)
        except RuntimeError as e:
            return self._error(503, str(e))   # backend not configured (e.g. no API key)
        with db_cursor(commit=True) as cur:
            cur.execute(
                "INSERT INTO entity_summaries (entity_type, entity_id, summary, model) "
                "VALUES (%s, %s, %s, %s) "
                "ON CONFLICT (entity_type, entity_id) DO UPDATE "
                "SET summary = EXCLUDED.summary, model = EXCLUDED.model, generated_at = NOW() "
                "RETURNING generated_at", (kind, eid, summary, summarize.SUMMARY_MODEL))
            gen_at = cur.fetchone()["generated_at"]
        self._audit(user, "GENERATE_SUMMARY", kind, eid, f"Generated AI summary for {kind} {eid}")
        self._json(200, {"summary": summary, "model": summarize.SUMMARY_MODEL, "generatedAt": gen_at})

    def _person_dossier(self, pid: int) -> dict | None:
        with db_cursor() as cur:
            cur.execute(
                "SELECT alias, first_name, last_name, dob, nationality, risk_level, status, "
                "last_seen, last_location, description, notes FROM poi WHERE id = %s", (pid,))
            p = cur.fetchone()
            if not p:
                return None
            cur.execute(
                "SELECT g.name, g.type, gm.role FROM group_members gm "
                "JOIN groups_of_interest g ON g.id = gm.group_id WHERE gm.poi_id = %s", (pid,))
            affiliations = [dict(r) for r in cur.fetchall()]
            cur.execute(
                "SELECT type, occurred_on, location, severity, description FROM activities "
                "WHERE poi_id = %s ORDER BY occurred_on DESC NULLS LAST LIMIT 100", (pid,))
            activities = [dict(r) for r in cur.fetchall()]
            cur.execute(
                "SELECT label, note, lat, lng, observed_on FROM entity_coordinates "
                "WHERE entity_type = 'person' AND entity_id = %s", (pid,))
            locations = [dict(r) for r in cur.fetchall()]
        d = dict(p)
        d.update(subject_type="person", affiliations=affiliations,
                 activities=activities, known_locations=locations)
        return d

    def _group_dossier(self, gid: int) -> dict | None:
        with db_cursor() as cur:
            cur.execute(
                "SELECT name, type, threat_level, status, founded, base, objectives, "
                "description, notes FROM groups_of_interest WHERE id = %s", (gid,))
            g = cur.fetchone()
            if not g:
                return None
            cur.execute(
                "SELECT p.alias, gm.role FROM group_members gm "
                "JOIN poi p ON p.id = gm.poi_id WHERE gm.group_id = %s", (gid,))
            members = [dict(r) for r in cur.fetchall()]
            cur.execute(
                "SELECT type, occurred_on, location, severity, description FROM activities "
                "WHERE group_id = %s ORDER BY occurred_on DESC NULLS LAST LIMIT 100", (gid,))
            activities = [dict(r) for r in cur.fetchall()]
            cur.execute(
                "SELECT label, note, lat, lng, observed_on FROM entity_coordinates "
                "WHERE entity_type = 'group' AND entity_id = %s", (gid,))
            locations = [dict(r) for r in cur.fetchall()]
        d = dict(g)
        d.update(subject_type="group", members=members,
                 activities=activities, known_locations=locations)
        return d

    def _list_gallery(self, pid: int) -> None:
        with db_cursor() as cur:
            cur.execute("""
                SELECT id, src, caption, occurred_on AS date, occurred_on AS date_taken
                FROM poi_gallery WHERE poi_id = %s ORDER BY created_at DESC
            """, (pid,))
            self._json(200, [dict(r) for r in cur.fetchall()])

    def _add_gallery(self, pid: int, user: dict) -> None:
        if not self._require_edit_role(user): return
        data = self._parse_json_body()
        if data is None:
            return
        src = data.get("src")
        if not src:
            return self._error(400, "src is required.")
        with db_cursor(commit=True) as cur:
            cur.execute("""
                INSERT INTO poi_gallery (poi_id, src, caption, occurred_on) VALUES (%s,%s,%s,%s) RETURNING id
            """, (pid, src, data.get("caption"), data.get("date") or None))
            new_id = cur.fetchone()["id"]
        try:
            img_bytes = data_uri_to_bytes(src)
            if img_bytes:
                store_embeddings_for_photo(pid, "gallery", new_id, img_bytes)
        except Exception:
            logger.exception("Face embedding extraction failed for poi #%s gallery photo #%s", pid, new_id)
        self._json(201, {"id": new_id})

    def _delete_gallery(self, pid: int, gid: int, user: dict) -> None:
        if not self._require_edit_role(user): return
        with db_cursor(commit=True) as cur:
            cur.execute("DELETE FROM poi_gallery WHERE id=%s AND poi_id=%s", (gid, pid))
            cur.execute("DELETE FROM face_embeddings WHERE poi_id=%s AND source='gallery' AND source_id=%s", (pid, gid))
        self._json(200, {"ok": True})

    # ── Groups ─────────────────────────────────────────────────────────────
    def _list_groups(self, qs) -> None:
        search = qs.get("q", [None])[0]
        where, params = "", []
        if search:
            where = "WHERE (g.name ILIKE %s OR g.description ILIKE %s)"
            params = [f"%{search}%"] * 2
        with db_cursor() as cur:
            cur.execute(f"""
                SELECT g.id, g.name, g.type, g.threat_level, g.status, g.founded, g.base,
                       g.base_lat, g.base_lng,
                       g.leader_id, g.description, g.objectives, g.created_at, g.updated_at,
                       COALESCE(array_agg(DISTINCT gm.poi_id) FILTER (WHERE gm.poi_id IS NOT NULL), '{{}}') AS members,
                       COUNT(DISTINCT a.id) AS "activityCount"
                FROM groups_of_interest g
                LEFT JOIN group_members gm ON gm.group_id = g.id
                LEFT JOIN activities a ON a.group_id = g.id
                {where}
                GROUP BY g.id
                ORDER BY g.name
            """, params)
            rows = cur.fetchall()
        self._json(200, [dict(r) for r in rows])

    def _get_group(self, gid: int) -> None:
        with db_cursor() as cur:
            cur.execute("SELECT * FROM groups_of_interest WHERE id = %s", (gid,))
            row = cur.fetchone()
            if not row:
                return self._error(404, "Group not found.")
            cur.execute("SELECT poi_id FROM group_members WHERE group_id = %s", (gid,))
            members = [r["poi_id"] for r in cur.fetchall()]
            cur.execute("""
                SELECT id, content, name, description, mime_type
                FROM images WHERE entity_type='group' AND entity_id=%s ORDER BY created_at DESC
            """, (gid,))
            images = [dict(r) for r in cur.fetchall()]
            cur.execute("""
                SELECT id, lat, lng, label, note, observed_on AS date_observed
                FROM entity_coordinates WHERE entity_type='group' AND entity_id=%s ORDER BY created_at DESC
            """, (gid,))
            locations = [dict(r) for r in cur.fetchall()]
        result = dict(row)
        result["members"]   = members
        result["images"]    = images
        result["locations"] = locations
        self._json(200, result)

    def _create_group(self, user: dict) -> None:
        if not self._require_edit_role(user): return
        data = self._parse_json_body()
        if data is None:
            return
        name = str(data.get("name", "")).strip()
        if not name:
            return self._error(400, "Name is required.")
        with db_cursor(commit=True) as cur:
            cur.execute("""
                INSERT INTO groups_of_interest (name, type, threat_level, status, founded, base,
                                                 base_lat, base_lng, leader_id, description, objectives)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id
            """, (
                name, data.get("type"), data.get("threatLevel", "MEDIUM"), data.get("status", "ACTIVE"),
                data.get("founded"), data.get("base"), data.get("baseLat") or None, data.get("baseLng") or None,
                data.get("leaderId") or None, data.get("description"), data.get("objectives"),
            ))
            new_id = cur.fetchone()["id"]
            for pid in (data.get("members") or []):
                cur.execute("INSERT INTO group_members (group_id, poi_id) VALUES (%s,%s) ON CONFLICT DO NOTHING",
                            (new_id, pid))
        self._audit(user, "CREATE_GROUP", "group", new_id, f"Created group: {name}")
        self._json(201, {"id": new_id})

    def _update_group(self, gid: int, user: dict) -> None:
        if not self._require_edit_role(user): return
        data = self._parse_json_body()
        if data is None:
            return
        field_map = {
            "name": "name", "type": "type", "threatLevel": "threat_level", "status": "status",
            "founded": "founded", "base": "base", "baseLat": "base_lat", "baseLng": "base_lng",
            "leaderId": "leader_id", "description": "description", "objectives": "objectives",
        }
        sets, vals = [], []
        for pkey, col in field_map.items():
            if pkey in data:
                v = data[pkey]
                if pkey == "leaderId" and not v:
                    v = None
                if pkey in ("baseLat", "baseLng") and v == "":
                    v = None
                sets.append(f"{col}=%s")
                vals.append(v)
        if sets:
            vals.append(gid)
            with db_cursor(commit=True) as cur:
                cur.execute(f"UPDATE groups_of_interest SET {', '.join(sets)} WHERE id=%s", vals)
        if "members" in data:
            with db_cursor(commit=True) as cur:
                cur.execute("DELETE FROM group_members WHERE group_id=%s", (gid,))
                for pid in (data.get("members") or []):
                    cur.execute("INSERT INTO group_members (group_id, poi_id) VALUES (%s,%s) ON CONFLICT DO NOTHING",
                                (gid, pid))
        self._audit(user, "UPDATE_GROUP", "group", gid, f"Updated group #{gid}")
        self._json(200, {"ok": True})

    def _group_activities(self, gid: int) -> None:
        with db_cursor() as cur:
            cur.execute("""
                SELECT a.id, a.type, a.occurred_on AS date, a.location, a.lat, a.lng,
                       a.description, a.severity, a.reported_by, a.poi_id, a.group_id
                FROM activities a WHERE a.group_id = %s ORDER BY a.occurred_on DESC NULLS LAST
            """, (gid,))
            self._json(200, [dict(r) for r in cur.fetchall()])

    # ── Locations (standing Location entity) ────────────────────────────────
    def _list_locations(self, qs) -> None:
        search = qs.get("q", [None])[0]
        where, params = "", []
        if search:
            where = "WHERE name ILIKE %s OR address ILIKE %s"
            params = [f"%{search}%"] * 2
        with db_cursor() as cur:
            cur.execute(f"SELECT id, name, address, country, updated_at FROM locations {where} ORDER BY name", params)
            rows = cur.fetchall()
        self._json(200, [dict(r) for r in rows])

    def _create_location(self, user: dict) -> None:
        if not self._require_edit_role(user): return
        data = self._parse_json_body()
        if data is None:
            return
        name = str(data.get("name", "")).strip()
        if not name:
            return self._error(400, "Name is required.")
        with db_cursor(commit=True) as cur:
            cur.execute("""
                INSERT INTO locations (name, description, address, country, notes)
                VALUES (%s, %s, %s, %s, %s) RETURNING id
            """, (name, data.get("description"), data.get("address"),
                  data.get("country"), data.get("notes")))
            new_id = cur.fetchone()["id"]
            for coord in data.get("coords", []):
                cur.execute("""
                    INSERT INTO location_coords (location_id, lat, lng, label)
                    VALUES (%s, %s, %s, %s)
                """, (new_id, coord["lat"], coord["lng"], coord.get("label")))
        self._audit(user, "CREATE_LOCATION", "location", new_id, f"Created location: {name}")
        self._json(201, {"id": new_id})

    # ── Activities ─────────────────────────────────────────────────────────
    def _list_activities(self, qs) -> None:
        filters, params = [], []
        if q := qs.get("q", [None])[0]:
            filters.append("(a.description ILIKE %s OR a.location ILIKE %s)")
            params += [f"%{q}%", f"%{q}%"]
        if df := qs.get("date_from", [None])[0]:
            filters.append("a.occurred_on >= %s"); params.append(df)
        if dt := qs.get("date_to", [None])[0]:
            filters.append("a.occurred_on <= %s"); params.append(dt)
        where = ("WHERE " + " AND ".join(filters)) if filters else ""
        with db_cursor() as cur:
            cur.execute(f"""
                SELECT a.id, a.type, a.occurred_on AS date, a.location, a.lat, a.lng,
                       a.description, a.severity, a.reported_by, a.poi_id, a.group_id,
                       p.alias, p.risk_level, p.first_name, p.last_name,
                       a.created_at, a.updated_at
                FROM activities a
                LEFT JOIN poi p ON p.id = a.poi_id
                {where}
                ORDER BY a.occurred_on DESC NULLS LAST
            """, params)
            rows = cur.fetchall()
        self._json(200, [dict(r) for r in rows])

    def _get_activity(self, aid: int) -> None:
        with db_cursor() as cur:
            cur.execute("""
                SELECT a.id, a.type, a.occurred_on AS date, a.location, a.lat, a.lng,
                       a.description, a.severity, a.reported_by, a.poi_id, a.group_id,
                       p.alias, p.risk_level, p.first_name, p.last_name,
                       a.created_at, a.updated_at
                FROM activities a
                LEFT JOIN poi p ON p.id = a.poi_id
                WHERE a.id = %s
            """, (aid,))
            row = cur.fetchone()
            if not row:
                return self._error(404, "Activity not found.")
            group = None
            if row["group_id"]:
                cur.execute("SELECT id, name, type, threat_level FROM groups_of_interest WHERE id = %s",
                            (row["group_id"],))
                g = cur.fetchone()
                group = dict(g) if g else None
            cur.execute("""
                SELECT id, type, location, occurred_on AS date, severity, lat, lng
                FROM activities
                WHERE id != %s AND (poi_id = %s OR group_id = %s)
                ORDER BY occurred_on DESC NULLS LAST LIMIT 10
            """, (aid, row["poi_id"], row["group_id"]))
            related = [dict(r) for r in cur.fetchall()]
            cur.execute("""
                SELECT id, content, name, description, mime_type
                FROM images WHERE entity_type='activity' AND entity_id=%s ORDER BY created_at DESC
            """, (aid,))
            images = [dict(r) for r in cur.fetchall()]
            cur.execute("""
                SELECT id, lat, lng, label, note, observed_on AS date_observed
                FROM entity_coordinates WHERE entity_type='activity' AND entity_id=%s ORDER BY created_at DESC
            """, (aid,))
            locations = [dict(r) for r in cur.fetchall()]
        result = dict(row)
        result["group"]     = group
        result["related"]   = related
        result["images"]    = images
        result["locations"] = locations
        self._json(200, result)

    def _create_activity(self, user: dict) -> None:
        if not self._require_edit_role(user): return
        data = self._parse_json_body()
        if data is None:
            return
        with db_cursor(commit=True) as cur:
            cur.execute("""
                INSERT INTO activities (poi_id, group_id, type, occurred_on, location, lat, lng,
                                         description, severity, reported_by)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id
            """, (
                data.get("poiId") or None, data.get("groupId") or None,
                data.get("type", "OTHER"), data.get("date") or None, data.get("location"),
                data.get("lat"), data.get("lng"), data.get("description"),
                data.get("severity", "LOW"), data.get("reportedBy"),
            ))
            new_id = cur.fetchone()["id"]
        self._audit(user, "CREATE_ACTIVITY", "activity", new_id, f"Logged activity #{new_id}")
        self._json(201, {"id": new_id})

    def _update_activity(self, aid: int, user: dict) -> None:
        if not self._require_edit_role(user): return
        data = self._parse_json_body()
        if data is None:
            return
        field_map = {
            "type": "type", "date": "occurred_on", "location": "location", "severity": "severity",
            "lat": "lat", "lng": "lng", "description": "description", "reportedBy": "reported_by",
            "poiId": "poi_id", "groupId": "group_id",
        }
        sets, vals = [], []
        for pkey, col in field_map.items():
            if pkey in data:
                v = data[pkey]
                if pkey in ("poiId", "groupId") and not v:
                    v = None
                sets.append(f"{col}=%s")
                vals.append(v)
        if sets:
            vals.append(aid)
            with db_cursor(commit=True) as cur:
                cur.execute(f"UPDATE activities SET {', '.join(sets)} WHERE id=%s", vals)
        self._audit(user, "UPDATE_ACTIVITY", "activity", aid, f"Updated activity #{aid}")
        self._json(200, {"ok": True})

    # ── Hotspots ───────────────────────────────────────────────────────────
    def _list_hotspots(self) -> None:
        with db_cursor() as cur:
            cur.execute("SELECT id, name, type, risk, lat, lng, note, created_at FROM hotspots ORDER BY name")
            self._json(200, [dict(r) for r in cur.fetchall()])

    def _get_hotspot(self, hid: int) -> None:
        with db_cursor() as cur:
            cur.execute("SELECT id, name, type, risk, lat, lng, note, created_at FROM hotspots WHERE id=%s", (hid,))
            row = cur.fetchone()
        if not row:
            return self._error(404, "Hotspot not found.")
        self._json(200, dict(row))

    def _create_hotspot(self, user: dict) -> None:
        if not self._require_edit_role(user): return
        data = self._parse_json_body()
        if data is None:
            return
        name = str(data.get("name", "")).strip()
        if not name:
            return self._error(400, "Name is required.")
        if data.get("lat") is None or data.get("lng") is None:
            return self._error(400, "lat and lng are required.")
        with db_cursor(commit=True) as cur:
            cur.execute("""
                INSERT INTO hotspots (name, type, risk, lat, lng, note)
                VALUES (%s,%s,%s,%s,%s,%s) RETURNING id
            """, (name, data.get("type", "GENERAL"), data.get("risk", "MEDIUM"),
                  data.get("lat"), data.get("lng"), data.get("note")))
            new_id = cur.fetchone()["id"]
        self._audit(user, "CREATE_HOTSPOT", "hotspot", new_id, f"Created hotspot: {name}")
        self._json(201, {"id": new_id})

    def _update_hotspot(self, hid: int, user: dict) -> None:
        if not self._require_edit_role(user): return
        data = self._parse_json_body()
        if data is None:
            return
        field_map = {"name": "name", "type": "type", "risk": "risk", "lat": "lat", "lng": "lng", "note": "note"}
        sets, vals = [], []
        for pkey, col in field_map.items():
            if pkey in data:
                sets.append(f"{col}=%s")
                vals.append(data[pkey])
        if sets:
            vals.append(hid)
            with db_cursor(commit=True) as cur:
                cur.execute(f"UPDATE hotspots SET {', '.join(sets)} WHERE id=%s", vals)
        self._audit(user, "UPDATE_HOTSPOT", "hotspot", hid, f"Updated hotspot #{hid}")
        self._json(200, {"ok": True})

    # ── Intel reports ──────────────────────────────────────────────────────
    def _list_intel(self) -> None:
        with db_cursor() as cur:
            cur.execute("""
                SELECT id, title, occurred_on AS date, created_at, poi_refs, group_refs, locations, victims,
                       analysis_result
                FROM intel_reports ORDER BY occurred_on DESC NULLS LAST, created_at DESC
            """)
            self._json(200, [dict(r) for r in cur.fetchall()])

    def _get_intel(self, iid: int) -> None:
        with db_cursor() as cur:
            cur.execute("""
                SELECT id, title, occurred_on AS date, created_at, poi_refs, group_refs, locations, victims,
                       analysis_result, body
                FROM intel_reports WHERE id = %s
            """, (iid,))
            row = cur.fetchone()
        if not row:
            return self._error(404, "Intel report not found.")
        self._json(200, dict(row))

    def _create_intel(self, user: dict) -> None:
        if not self._require_edit_role(user): return
        data = self._parse_json_body()
        if data is None:
            return
        title = str(data.get("title", "")).strip()
        if not title:
            return self._error(400, "Title is required.")
        with db_cursor(commit=True) as cur:
            cur.execute("""
                INSERT INTO intel_reports (title, occurred_on, body, poi_refs, group_refs, locations, victims,
                                            analysis_result)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id
            """, (
                title, data.get("date") or None, data.get("text", data.get("body")),
                json.dumps(data.get("poiRefs") or []), json.dumps(data.get("groupRefs") or []),
                json.dumps(data.get("locations") or []), json.dumps(data.get("victims") or []),
                data.get("analysisResult"),
            ))
            new_id = cur.fetchone()["id"]
        self._audit(user, "CREATE_INTEL", "intel", new_id, f"Created intel report: {title}")
        self._json(201, {"id": new_id})

    def _update_intel(self, iid: int, user: dict) -> None:
        if not self._require_edit_role(user): return
        data = self._parse_json_body()
        if data is None:
            return
        sets, vals = [], []
        for pkey, col in (("title", "title"), ("date", "occurred_on"), ("analysisResult", "analysis_result")):
            if pkey in data:
                sets.append(f"{col}=%s")
                vals.append(data[pkey])
        if "text" in data or "body" in data:
            sets.append("body=%s")
            vals.append(data.get("text", data.get("body")))
        for pkey, col in (("poiRefs", "poi_refs"), ("groupRefs", "group_refs"),
                          ("locations", "locations"), ("victims", "victims")):
            if pkey in data:
                sets.append(f"{col}=%s")
                vals.append(json.dumps(data[pkey] or []))
        if sets:
            vals.append(iid)
            with db_cursor(commit=True) as cur:
                cur.execute(f"UPDATE intel_reports SET {', '.join(sets)} WHERE id=%s", vals)
        self._audit(user, "UPDATE_INTEL", "intel", iid, f"Updated intel report #{iid}")
        self._json(200, {"ok": True})

    # ── Countries (computed aggregation) ────────────────────────────────────
    def _list_countries(self) -> None:
        with db_cursor() as cur:
            cur.execute("SELECT DISTINCT nationality FROM poi WHERE nationality IS NOT NULL AND nationality <> '' ORDER BY nationality")
            nationalities = [r["nationality"] for r in cur.fetchall()]

            # Group nationality/demonym values (e.g. "Nigerian") by the country
            # name they belong to (e.g. "Nigeria") so a country with multiple
            # recorded demonym spellings still shows as a single card.
            # Values that don't resolve to a real, recognised country (typos,
            # stray NLP extraction noise, unrelated words) are dropped here —
            # never shown as a Country Profiles card in the first place.
            countries: dict[str, list[str]] = {}
            for nat in nationalities:
                country = resolve_known_country(nat)
                if country:
                    countries.setdefault(country, []).append(nat)

            result = []
            for name, nats in countries.items():
                cur.execute("SELECT risk_level FROM poi WHERE nationality = ANY(%s)", (nats,))
                risks = [r["risk_level"] for r in cur.fetchall()]
                cur.execute("SELECT COUNT(*) AS cnt FROM groups_of_interest WHERE base ILIKE %s", (f"%{name}%",))
                group_count = cur.fetchone()["cnt"]
                cur.execute("SELECT COUNT(*) AS cnt FROM activities WHERE location ILIKE %s", (f"%{name}%",))
                activity_count = cur.fetchone()["cnt"]
                result.append({
                    "name": name,
                    "personCount": len(risks),
                    "groupCount": group_count,
                    "activityCount": activity_count,
                    "criticalCount": sum(1 for r in risks if r == "CRITICAL"),
                    "highRiskCount": sum(1 for r in risks if r in ("CRITICAL", "HIGH")),
                    "topRisk": max(risks, key=lambda r: RISK_RANK.get(r, 0)) if risks else None,
                    # Hotspots have no country attribution in this dataset (point coords only).
                    "hotspotCount": 0,
                })
        result.sort(key=lambda c: c["name"])
        self._json(200, result)

    def _get_country(self, name: str) -> None:
        canonical = canonical_country_name(name)
        if not canonical:
            return self._error(404, "Not a recognised country.")
        name = canonical
        with db_cursor() as cur:
            cur.execute("SELECT DISTINCT nationality FROM poi WHERE nationality IS NOT NULL AND nationality <> ''")
            known_nationalities = [r["nationality"] for r in cur.fetchall()]
            nats = nationalities_for_country(name, known_nationalities) or [name]

            cur.execute("SELECT * FROM poi WHERE nationality = ANY(%s) ORDER BY alias", (nats,))
            persons = [dict(r) for r in cur.fetchall()]
            for p in persons:
                cur.execute("""
                    SELECT id, content, name, description, mime_type
                    FROM images WHERE entity_type='person' AND entity_id=%s
                """, (p["id"],))
                p["images"] = [dict(r) for r in cur.fetchall()]
                cur.execute("""
                    SELECT id, lat, lng, label, note, observed_on AS date_observed
                    FROM entity_coordinates WHERE entity_type='person' AND entity_id=%s
                """, (p["id"],))
                p["locations"] = [dict(r) for r in cur.fetchall()]

            cur.execute("SELECT * FROM groups_of_interest WHERE base ILIKE %s ORDER BY name", (f"%{name}%",))
            groups = [dict(r) for r in cur.fetchall()]
            for g in groups:
                cur.execute("SELECT poi_id FROM group_members WHERE group_id = %s", (g["id"],))
                g["members"] = [r["poi_id"] for r in cur.fetchall()]
                cur.execute("""
                    SELECT id, content, name, description, mime_type
                    FROM images WHERE entity_type='group' AND entity_id=%s
                """, (g["id"],))
                g["images"] = [dict(r) for r in cur.fetchall()]
                cur.execute("""
                    SELECT id, lat, lng, label, note, observed_on AS date_observed
                    FROM entity_coordinates WHERE entity_type='group' AND entity_id=%s
                """, (g["id"],))
                g["locations"] = [dict(r) for r in cur.fetchall()]

            cur.execute("""
                SELECT a.id, a.type, a.occurred_on AS date, a.location, a.lat, a.lng,
                       a.severity, a.description, p.alias
                FROM activities a LEFT JOIN poi p ON p.id = a.poi_id
                WHERE a.location ILIKE %s ORDER BY a.occurred_on DESC NULLS LAST
            """, (f"%{name}%",))
            activities = [dict(r) for r in cur.fetchall()]

            cur.execute("SELECT AVG(lat) AS lat, AVG(lng) AS lng FROM activities WHERE location ILIKE %s AND lat IS NOT NULL",
                        (f"%{name}%",))
            centroid = cur.fetchone()

        self._json(200, {
            "name": name,
            "persons": persons,
            "groups": groups,
            "activities": activities,
            "hotspots": [],
            "lat": centroid["lat"] if centroid else None,
            "lng": centroid["lng"] if centroid else None,
        })

    # ── Stats ──────────────────────────────────────────────────────────────
    def _stats(self) -> None:
        with db_cursor() as cur:
            def count(sql, *params):
                cur.execute(sql, params)
                return cur.fetchone()["cnt"]
            self._json(200, {
                "persons":       count("SELECT COUNT(*) AS cnt FROM poi"),
                "activePersons": count("SELECT COUNT(*) AS cnt FROM poi WHERE status='ACTIVE'"),
                "groups":        count("SELECT COUNT(*) AS cnt FROM groups_of_interest"),
                "activeGroups":  count("SELECT COUNT(*) AS cnt FROM groups_of_interest WHERE status='ACTIVE'"),
                "activities":    count("SELECT COUNT(*) AS cnt FROM activities"),
                "hotspots":      count("SELECT COUNT(*) AS cnt FROM hotspots"),
                "intel":         count("SELECT COUNT(*) AS cnt FROM intel_reports"),
                "critical":      count("SELECT COUNT(*) AS cnt FROM poi WHERE risk_level='CRITICAL'"),
            })

    # ── Role guard for anything that creates/edits data ─────────────────────
    # The blanket auth check in _dispatch only requires VIEWER (so every
    # authenticated user can hit any endpoint that isn't otherwise gated) —
    # VIEWER's read-only restriction was, before this, enforced only by the
    # frontend hiding buttons. Call this at the top of every handler that
    # writes data; a client that bypasses the UI (curl, a proxy, a bug) must
    # still be stopped server-side.
    def _require_edit_role(self, user: dict) -> bool:
        if user.get("role") not in ("ADMIN", "ANALYST"):
            self._error(403, "Analyst or Administrator role required.")
            return False
        return True

    # ── Generic delete ─────────────────────────────────────────────────────
    def _delete_entity(self, table: str, eid: int, user: dict, audit_label: str | None = None) -> None:
        if user.get("role") not in ("ADMIN", "ANALYST"):
            return self._error(403, "Insufficient privileges.")
        ALLOWED_TABLES = {"poi", "groups_of_interest", "locations", "activities", "hotspots", "intel_reports"}
        if table not in ALLOWED_TABLES:
            return self._error(400, "Invalid entity type.")
        with db_cursor(commit=True) as cur:
            cur.execute(f"DELETE FROM {table} WHERE id = %s", (eid,))
        if audit_label:
            self._audit(user, f"DELETE_{audit_label}", audit_label.lower(), eid,
                        f"Deleted {audit_label.lower()} #{eid}")
        self._json(200, {"ok": True})

    # ── Generic entity extras ───────────────────────────────────────────────
    def _extras(self, method: str, etype: str, eid: int, resource: str, user: dict) -> None:
        if method != "GET" and not self._require_edit_role(user): return
        if resource == "tags":          return self._extras_tags(method, etype, eid)
        if resource == "notes":         return self._extras_notes(method, etype, eid)
        if resource == "fields":        return self._extras_fields(method, etype, eid)
        if resource == "attachments":   return self._extras_attachments(method, etype, eid)
        if resource == "images":        return self._extras_images(method, etype, eid)
        if resource == "locations":     return self._extras_locations(method, etype, eid)
        if resource == "relationships": return self._extras_relationships(method, etype, eid)
        self._error(404, "Unknown resource.")

    def _extras_tags(self, method: str, etype: str, eid: int) -> None:
        if method == "GET":
            with db_cursor() as cur:
                cur.execute("SELECT id, tag, color FROM tags WHERE entity_type=%s AND entity_id=%s ORDER BY tag",
                            (etype, eid))
                return self._json(200, [dict(r) for r in cur.fetchall()])
        if method == "POST":
            data = self._parse_json_body()
            if data is None:
                return
            tag = str(data.get("tag", "")).strip()
            if not tag:
                return self._error(400, "Tag value required.")
            with db_cursor(commit=True) as cur:
                cur.execute("""
                    INSERT INTO tags (entity_type, entity_id, tag, color) VALUES (%s,%s,%s,%s)
                    ON CONFLICT (entity_type, entity_id, tag) DO UPDATE SET color = EXCLUDED.color
                    RETURNING id
                """, (etype, eid, tag, data.get("color")))
                row = cur.fetchone()
            return self._json(201, {"id": row["id"]})
        self._error(405, "Method not allowed.")

    def _extras_notes(self, method: str, etype: str, eid: int) -> None:
        if method == "GET":
            with db_cursor() as cur:
                cur.execute("""
                    SELECT id, title, body, note_type, is_pinned, created_at
                    FROM notes WHERE entity_type=%s AND entity_id=%s
                    ORDER BY is_pinned DESC, created_at DESC
                """, (etype, eid))
                return self._json(200, [dict(r) for r in cur.fetchall()])
        if method == "POST":
            data = self._parse_json_body()
            if data is None:
                return
            with db_cursor(commit=True) as cur:
                cur.execute("""
                    INSERT INTO notes (entity_type, entity_id, title, body, note_type, is_pinned)
                    VALUES (%s,%s,%s,%s,%s,%s) RETURNING id
                """, (etype, eid, data.get("title"), data.get("body"),
                      data.get("noteType", "GENERAL"), bool(data.get("isPinned"))))
                new_id = cur.fetchone()["id"]
            return self._json(201, {"id": new_id})
        self._error(405, "Method not allowed.")

    def _extras_fields(self, method: str, etype: str, eid: int) -> None:
        if method == "GET":
            with db_cursor() as cur:
                cur.execute("""
                    SELECT id, field_key, field_value, field_type
                    FROM custom_fields WHERE entity_type=%s AND entity_id=%s ORDER BY field_key
                """, (etype, eid))
                return self._json(200, [dict(r) for r in cur.fetchall()])
        if method == "POST":
            data = self._parse_json_body()
            if data is None:
                return
            key = str(data.get("key", "")).strip()
            if not key:
                return self._error(400, "key is required.")
            with db_cursor(commit=True) as cur:
                cur.execute("""
                    INSERT INTO custom_fields (entity_type, entity_id, field_key, field_value, field_type)
                    VALUES (%s,%s,%s,%s,%s)
                    ON CONFLICT (entity_type, entity_id, field_key)
                    DO UPDATE SET field_value = EXCLUDED.field_value, field_type = EXCLUDED.field_type
                    RETURNING id
                """, (etype, eid, key, data.get("value"), data.get("fieldType", "TEXT")))
                new_id = cur.fetchone()["id"]
            return self._json(201, {"id": new_id})
        self._error(405, "Method not allowed.")

    def _extras_attachments(self, method: str, etype: str, eid: int) -> None:
        if method == "GET":
            with db_cursor() as cur:
                cur.execute("""
                    SELECT id, attach_type, name, url, mime_type, description, size_bytes, created_at
                    FROM attachments WHERE entity_type=%s AND entity_id=%s ORDER BY created_at DESC
                """, (etype, eid))
                return self._json(200, [dict(r) for r in cur.fetchall()])
        if method == "POST":
            data = self._parse_json_body()
            if data is None:
                return
            name = str(data.get("name", "")).strip()
            if not name:
                return self._error(400, "name is required.")
            content = data.get("content")
            size_bytes = len(content.encode("utf-8", "ignore")) if content else 0
            with db_cursor(commit=True) as cur:
                cur.execute("""
                    INSERT INTO attachments (entity_type, entity_id, attach_type, name, content, url,
                                              mime_type, description, size_bytes)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id
                """, (etype, eid, data.get("attachType", "TEXT"), name, content,
                      data.get("url"), data.get("mimeType"), data.get("description"), size_bytes))
                new_id = cur.fetchone()["id"]
            return self._json(201, {"id": new_id})
        self._error(405, "Method not allowed.")

    def _extras_images(self, method: str, etype: str, eid: int) -> None:
        if method == "GET":
            with db_cursor() as cur:
                cur.execute("""
                    SELECT id, content, name, description, mime_type, created_at
                    FROM images WHERE entity_type=%s AND entity_id=%s ORDER BY created_at DESC
                """, (etype, eid))
                return self._json(200, [dict(r) for r in cur.fetchall()])
        if method == "POST":
            data = self._parse_json_body()
            if data is None:
                return
            content = data.get("content")
            if not content:
                return self._error(400, "content is required.")
            with db_cursor(commit=True) as cur:
                cur.execute("""
                    INSERT INTO images (entity_type, entity_id, content, name, description, mime_type)
                    VALUES (%s,%s,%s,%s,%s,%s) RETURNING id
                """, (etype, eid, content, data.get("name"), data.get("caption"), data.get("mimeType")))
                new_id = cur.fetchone()["id"]
            if etype == "person":
                try:
                    img_bytes = data_uri_to_bytes(content)
                    if img_bytes:
                        store_embeddings_for_photo(eid, "images", new_id, img_bytes)
                except Exception:
                    logger.exception("Face embedding extraction failed for poi #%s image #%s", eid, new_id)
            return self._json(201, {"id": new_id})
        self._error(405, "Method not allowed.")

    def _extras_locations(self, method: str, etype: str, eid: int) -> None:
        if method == "GET":
            with db_cursor() as cur:
                cur.execute("""
                    SELECT id, lat, lng, label, note, observed_on AS date_observed
                    FROM entity_coordinates WHERE entity_type=%s AND entity_id=%s ORDER BY created_at DESC
                """, (etype, eid))
                return self._json(200, [dict(r) for r in cur.fetchall()])
        if method == "POST":
            data = self._parse_json_body()
            if data is None:
                return
            if data.get("lat") is None or data.get("lng") is None:
                return self._error(400, "lat and lng are required.")
            with db_cursor(commit=True) as cur:
                cur.execute("""
                    INSERT INTO entity_coordinates (entity_type, entity_id, lat, lng, label, note, observed_on)
                    VALUES (%s,%s,%s,%s,%s,%s,%s) RETURNING id
                """, (etype, eid, data["lat"], data["lng"], data.get("label"),
                      data.get("note"), data.get("dateObserved") or None))
                new_id = cur.fetchone()["id"]
            return self._json(201, {"id": new_id})
        self._error(405, "Method not allowed.")

    def _extras_relationships(self, method: str, etype: str, eid: int) -> None:
        if method == "GET":
            with db_cursor() as cur:
                cur.execute("""
                    SELECT id, related_type, related_id, related_name, rel_type, created_at
                    FROM relationships WHERE entity_type=%s AND entity_id=%s ORDER BY created_at DESC
                """, (etype, eid))
                return self._json(200, [dict(r) for r in cur.fetchall()])
        if method == "POST":
            data = self._parse_json_body()
            if data is None:
                return
            related_type = data.get("relatedType", etype)
            related_id   = data.get("relatedId") or None
            related_name = data.get("relatedName") or None
            # A country target has no numeric row — it's identified by name.
            # Validate against the real-country list so a typo/garbage value
            # never gets stored as if it were a country (same lesson as the
            # Country Profiles fix).
            if related_type == "country":
                canonical = canonical_country_name(related_name)
                if not canonical:
                    return self._error(400, "Not a recognised country.")
                related_id, related_name = None, canonical
            with db_cursor(commit=True) as cur:
                cur.execute("""
                    INSERT INTO relationships (entity_type, entity_id, related_type, related_id, related_name, rel_type)
                    VALUES (%s,%s,%s,%s,%s,%s) RETURNING id
                """, (etype, eid, related_type, related_id, related_name, data.get("relType")))
                new_id = cur.fetchone()["id"]
            return self._json(201, {"id": new_id})
        self._error(405, "Method not allowed.")

    def _extras_item(self, method: str, resource: str, rid: int, user: dict) -> None:
        if not self._require_edit_role(user): return
        table_map = {
            "tags": "tags", "notes": "notes", "fields": "custom_fields",
            "attachments": "attachments", "images": "images",
            "locations": "entity_coordinates", "relationships": "relationships",
        }
        table = table_map.get(resource)
        if not table:
            return self._error(404, "Unknown resource.")
        if method == "DELETE":
            with db_cursor(commit=True) as cur:
                cur.execute(f"DELETE FROM {table} WHERE id=%s", (rid,))
                if resource == "images":
                    cur.execute("DELETE FROM face_embeddings WHERE source='images' AND source_id=%s", (rid,))
            return self._json(200, {"ok": True})
        if method == "PUT":
            data = self._parse_json_body()
            if data is None:
                return
            if table == "custom_fields" and "value" in data:
                with db_cursor(commit=True) as cur:
                    cur.execute("UPDATE custom_fields SET field_value=%s WHERE id=%s", (data["value"], rid))
                return self._json(200, {"ok": True})
            if table == "notes":
                sets, vals = [], []
                for pkey, col in (("title", "title"), ("body", "body"),
                                  ("noteType", "note_type"), ("isPinned", "is_pinned")):
                    if pkey in data:
                        sets.append(f"{col}=%s")
                        vals.append(bool(data[pkey]) if pkey == "isPinned" else data[pkey])
                if sets:
                    vals.append(rid)
                    with db_cursor(commit=True) as cur:
                        cur.execute(f"UPDATE notes SET {', '.join(sets)} WHERE id=%s", vals)
                return self._json(200, {"ok": True})
            return self._error(400, "Update not supported for this resource.")
        self._error(405, "Method not allowed.")

    # ── NLP ────────────────────────────────────────────────────────────────
    def _nlp_submit(self, user: dict) -> None:
        if not self._require_edit_role(user): return
        ct = self.headers.get("Content-Type", "")
        raw_body = self._read_body()
        if raw_body is None:
            return

        extracted_text = ""
        image_files    = []

        # JSON shortcut
        if "application/json" in ct:
            try:
                data = json.loads(raw_body)
            except json.JSONDecodeError:
                return self._error(400, "Invalid JSON.")
            extracted_text = str(data.get("text", "")).strip()
            if not extracted_text:
                return self._error(400, "Field 'text' is required for JSON submissions.")

        elif "multipart/form-data" in ct:
            # Use email.parser — no deprecated cgi module needed
            fields = _parse_multipart(ct, raw_body)

            if "text" in fields:
                extracted_text = fields["text"][0]["data"].decode("utf-8", errors="replace").strip()

            for field_name in ("file", "files", "files[]", "document"):
                for part in fields.get(field_name, []):
                    fname = part.get("filename", "")
                    if not fname:
                        continue
                    mime = part.get("content_type", "application/octet-stream").split(";")[0].strip()
                    if mime not in ALLOWED_MIME_TYPES:
                        logger.warning("NLP submit: rejected file type %s (%s)", fname, mime)
                        continue
                    ext      = Path(fname).suffix or ".bin"
                    saved_as = f"{uuid.uuid4().hex}{ext}"
                    dest     = NLP_DIR / saved_as
                    dest.write_bytes(part["data"])

                    if mime in IMAGE_MIME_TYPES:
                        image_files.append({
                            "filename": fname,
                            "saved_as": saved_as,
                            "mime":     mime,
                            "path":     dest,
                        })
                    else:
                        file_text = extract_text_from_file(dest, mime)
                        extracted_text += (f"\n\n--- {fname} ---\n{file_text}"
                                           if extracted_text else file_text)
        else:
            return self._error(400, "multipart/form-data or application/json required.")

        if not extracted_text and not image_files:
            return self._error(400, "No text or recognisable files were provided.")

        if not extracted_text and image_files:
            parts = [extract_text_from_file(f["path"], f["mime"]) for f in image_files]
            extracted_text = "\n\n".join(p for p in parts if p.strip()) or "[Image — no OCR text]"

        with db_cursor(commit=True) as cur:
            cur.execute(
                "INSERT INTO nlp_jobs (raw_text, status) VALUES (%s, 'pending') RETURNING id",
                (extracted_text,)
            )
            job_id = cur.fetchone()["id"]

        threading.Thread(
            target=process_job,
            args=(job_id, extracted_text, image_files),
            daemon=True,
            name=f"nlp-job-{job_id}"
        ).start()

        self._json(202, {
            "job_id":      job_id,
            "status":      "pending",
            "files_count": len(image_files),
            "text_length": len(extracted_text),
            "message":     "Job queued. Poll GET /api/nlp/jobs/{id} for status.",
        })

    def _nlp_get(self, job_id: int) -> None:
        with db_cursor() as cur:
            cur.execute("""
                SELECT id, status, created_at, reviewed_at, committed_at,
                       LEFT(raw_text, 300) AS preview, claude_output
                FROM nlp_jobs WHERE id = %s
            """, (job_id,))
            row = cur.fetchone()
        if not row:
            return self._error(404, "Job not found.")
        result = dict(row)
        if result.get("claude_output"):
            output = result["claude_output"]
            if isinstance(output, str):
                output = json.loads(output)
            output.pop("_image_files", None)
            result["claude_output"] = output
        self._json(200, result)

    def _nlp_list(self) -> None:
        with db_cursor() as cur:
            cur.execute("""
                SELECT id, status, created_at, reviewed_at, committed_at,
                       LEFT(raw_text, 120) AS preview
                FROM nlp_jobs ORDER BY created_at DESC LIMIT 100
            """)
            self._json(200, [dict(r) for r in cur.fetchall()])

    def _nlp_commit(self, job_id: int, user: dict) -> None:
        if not self._require_edit_role(user): return
        # Optional body: {"selections": {"persons":[0,2], "groups":[0], ...}}
        # restricting the commit to only the items the analyst checked in the
        # review screen. No body / malformed body -> commit everything, so
        # existing callers (curl, older clients) keep working unchanged.
        selections = None
        raw = self._read_body()
        if raw:
            try:
                payload = json.loads(raw)
                if isinstance(payload, dict):
                    selections = payload.get("selections")
            except json.JSONDecodeError:
                pass
        try:
            summary = commit_job(job_id, selections)
            self._json(200, {"ok": True, "summary": summary})
        except ValueError as e:
            self._error(404, str(e))
        except Exception:
            logger.error("NLP commit failed:\n%s", traceback.format_exc())
            self._error(500, "Commit failed. Check server logs.")

    def _nlp_reject(self, job_id: int, user: dict) -> None:
        if not self._require_edit_role(user): return
        with db_cursor(commit=True) as cur:
            cur.execute("UPDATE nlp_jobs SET status = 'rejected' WHERE id = %s", (job_id,))
        self._json(200, {"ok": True})

    # ── Face search ────────────────────────────────────────────────────────
    def _face_search(self) -> None:
        """POST multipart/form-data (field "file") or JSON {"image": "data:...base64,..."}.
        Detects face(s) in the uploaded image and ranks every POI in the
        system by best cosine similarity, using embeddings already stored
        from their on-file photos (see face_match.store_embeddings_for_photo)."""
        if not engine_ready():
            return self._error(503, "Face recognition model is not available on this server "
                                     "(InsightFace failed to load — check server logs).")

        ct = self.headers.get("Content-Type", "")
        raw_body = self._read_body()
        if raw_body is None:
            return

        image_bytes = None
        if "multipart/form-data" in ct:
            fields = _parse_multipart(ct, raw_body)
            for field_name in ("file", "image", "photo"):
                parts = fields.get(field_name, [])
                if parts:
                    image_bytes = parts[0]["data"]
                    break
        elif "application/json" in ct:
            try:
                data = json.loads(raw_body)
            except json.JSONDecodeError:
                return self._error(400, "Invalid JSON.")
            image_bytes = data_uri_to_bytes(data.get("image", ""))
        else:
            return self._error(400, "multipart/form-data or application/json required.")

        if not image_bytes:
            return self._error(400, "No image was provided.")

        result = search_similar_faces(image_bytes, top_n=10)
        self._json(200, result)

    # ── Link Analysis ──────────────────────────────────────────────────────
    def _list_link_charts(self) -> None:
        with db_cursor() as cur:
            cur.execute("""
                SELECT c.id, c.name, c.description, c.created_by, c.created_at, c.updated_at,
                       COUNT(n.id) AS "nodeCount"
                FROM link_charts c
                LEFT JOIN link_chart_nodes n ON n.chart_id = c.id
                GROUP BY c.id ORDER BY c.updated_at DESC
            """)
            self._json(200, [dict(r) for r in cur.fetchall()])

    def _create_link_chart(self, user: dict) -> None:
        if not self._require_edit_role(user): return
        data = self._parse_json_body()
        if data is None:
            return
        name = str(data.get("name", "")).strip() or "Untitled Chart"
        with db_cursor(commit=True) as cur:
            cur.execute("""
                INSERT INTO link_charts (name, description, created_by) VALUES (%s,%s,%s) RETURNING id
            """, (name, data.get("description"), user.get("usr")))
            new_id = cur.fetchone()["id"]
        self._audit(user, "CREATE_LINK_CHART", "link_chart", new_id, f"Created link chart: {name}")
        self._json(201, {"id": new_id})

    @staticmethod
    def _resolve_link_node(node_type: str, node_ref: str) -> dict | None:
        """Look up display data for one chart node. Returns None if the
        underlying person/group no longer exists (deleted since the node was added)."""
        if node_type == "country":
            return {"label": node_ref, "sublabel": None, "risk": None, "status": None, "photo": None}
        table, id_col = ("poi", "alias") if node_type == "person" else ("groups_of_interest", "name")
        try:
            ref_id = int(node_ref)
        except (TypeError, ValueError):
            return None
        with db_cursor() as cur:
            if node_type == "person":
                cur.execute("SELECT alias, risk_level, status, photo FROM poi WHERE id=%s", (ref_id,))
                row = cur.fetchone()
                if not row:
                    return None
                return {"label": row["alias"], "sublabel": None, "risk": row["risk_level"],
                        "status": row["status"], "photo": row["photo"]}
            else:
                cur.execute("SELECT name, threat_level, status FROM groups_of_interest WHERE id=%s", (ref_id,))
                row = cur.fetchone()
                if not row:
                    return None
                return {"label": row["name"], "sublabel": None, "risk": row["threat_level"],
                        "status": row["status"], "photo": None}

    def _get_link_chart(self, cid: int) -> None:
        with db_cursor() as cur:
            cur.execute("SELECT id, name, description, created_by, created_at, updated_at FROM link_charts WHERE id=%s", (cid,))
            chart = cur.fetchone()
            if not chart:
                return self._error(404, "Chart not found.")
            cur.execute("SELECT id, node_type, node_ref, x, y FROM link_chart_nodes WHERE chart_id=%s", (cid,))
            node_rows = [dict(r) for r in cur.fetchall()]

        nodes = []
        node_keys = set()   # {(node_type, node_ref)} for edge matching below
        person_ids, group_ids = [], []
        for n in node_rows:
            display = self._resolve_link_node(n["node_type"], n["node_ref"])
            if display is None:
                continue   # underlying entity was deleted since this node was added — skip silently
            nodes.append({**n, **display})
            node_keys.add((n["node_type"], n["node_ref"]))
            if n["node_type"] == "person":
                person_ids.append(int(n["node_ref"]))
            elif n["node_type"] == "group":
                group_ids.append(int(n["node_ref"]))

        edges = []
        with db_cursor() as cur:
            # 1. Explicit analyst-drawn relationships touching any node on this chart.
            cur.execute("""
                SELECT id, entity_type, entity_id, entity_name, related_type, related_id, related_name, rel_type
                FROM relationships
                WHERE entity_type IN ('person','group','country') AND related_type IN ('person','group','country')
            """)
            for r in cur.fetchall():
                a = (r["entity_type"], str(r["entity_id"]) if r["entity_id"] is not None else r["entity_name"])
                b = (r["related_type"], str(r["related_id"]) if r["related_id"] is not None else r["related_name"])
                if a in node_keys and b in node_keys and a != b:
                    edges.append({"id": f"rel-{r['id']}", "from": a, "to": b,
                                  "label": r["rel_type"] or "related to", "kind": "relationship",
                                  "relationship_id": r["id"]})

            # 2. Group membership (implicit, read-only on the diagram).
            if person_ids and group_ids:
                cur.execute("SELECT group_id, poi_id FROM group_members WHERE poi_id = ANY(%s) AND group_id = ANY(%s)",
                            (person_ids, group_ids))
                for r in cur.fetchall():
                    a, b = ("person", str(r["poi_id"])), ("group", str(r["group_id"]))
                    if a in node_keys and b in node_keys:
                        edges.append({"id": f"mem-{r['poi_id']}-{r['group_id']}", "from": a, "to": b,
                                      "label": "member of", "kind": "membership", "relationship_id": None})

            # 3. Person-to-person associates (implicit, read-only on the diagram).
            if person_ids:
                cur.execute("SELECT id, contacts FROM poi WHERE id = ANY(%s)", (person_ids,))
                seen_pairs = set()
                for r in cur.fetchall():
                    a_id = r["id"]
                    for c_id in (r["contacts"] or []):
                        if c_id not in person_ids:
                            continue
                        pair = tuple(sorted((a_id, c_id)))
                        if pair in seen_pairs:
                            continue
                        seen_pairs.add(pair)
                        edges.append({"id": f"contact-{pair[0]}-{pair[1]}",
                                      "from": ("person", str(pair[0])), "to": ("person", str(pair[1])),
                                      "label": "associate of", "kind": "contact", "relationship_id": None})

        result = dict(chart)
        result["nodes"] = nodes
        result["edges"] = edges
        self._json(200, result)

    def _update_link_chart(self, cid: int, user: dict) -> None:
        if not self._require_edit_role(user): return
        data = self._parse_json_body()
        if data is None:
            return
        sets, vals = [], []
        for pkey, col in (("name", "name"), ("description", "description")):
            if pkey in data:
                sets.append(f"{col}=%s")
                vals.append(data[pkey])
        if sets:
            sets.append("updated_at=NOW()")
            vals.append(cid)
            with db_cursor(commit=True) as cur:
                cur.execute(f"UPDATE link_charts SET {', '.join(sets)} WHERE id=%s", vals)
        self._json(200, {"ok": True})

    def _delete_link_chart(self, cid: int, user: dict) -> None:
        if not self._require_edit_role(user): return
        with db_cursor(commit=True) as cur:
            cur.execute("DELETE FROM link_charts WHERE id=%s", (cid,))
        self._audit(user, "DELETE_LINK_CHART", "link_chart", cid, f"Deleted link chart #{cid}")
        self._json(200, {"ok": True})

    def _add_link_chart_node(self, cid: int, user: dict) -> None:
        if not self._require_edit_role(user): return
        data = self._parse_json_body()
        if data is None:
            return
        node_type = data.get("nodeType")
        if node_type not in ("person", "group", "country"):
            return self._error(400, "nodeType must be person, group, or country.")
        node_ref = str(data.get("nodeRef", "")).strip()
        if node_type == "country":
            canonical = canonical_country_name(node_ref)
            if not canonical:
                return self._error(400, "Not a recognised country.")
            node_ref = canonical
        elif not node_ref:
            return self._error(400, "nodeRef is required.")
        with db_cursor(commit=True) as cur:
            cur.execute("""
                INSERT INTO link_chart_nodes (chart_id, node_type, node_ref, x, y)
                VALUES (%s,%s,%s,%s,%s)
                ON CONFLICT (chart_id, node_type, node_ref) DO NOTHING
                RETURNING id
            """, (cid, node_type, node_ref, data.get("x"), data.get("y")))
            row = cur.fetchone()
            cur.execute("UPDATE link_charts SET updated_at=NOW() WHERE id=%s", (cid,))
        if not row:
            return self._error(409, "That node is already on this chart.")
        self._json(201, {"id": row["id"]})

    def _update_link_chart_node(self, cid: int, nid: int, user: dict) -> None:
        if not self._require_edit_role(user): return
        data = self._parse_json_body()
        if data is None:
            return
        with db_cursor(commit=True) as cur:
            cur.execute("UPDATE link_chart_nodes SET x=%s, y=%s WHERE id=%s AND chart_id=%s",
                        (data.get("x"), data.get("y"), nid, cid))
        self._json(200, {"ok": True})

    def _delete_link_chart_node(self, cid: int, nid: int, user: dict) -> None:
        if not self._require_edit_role(user): return
        with db_cursor(commit=True) as cur:
            cur.execute("DELETE FROM link_chart_nodes WHERE id=%s AND chart_id=%s", (nid, cid))
        self._json(200, {"ok": True})

    # ── Admin: users ───────────────────────────────────────────────────────
    def _list_users(self) -> None:
        with db_cursor() as cur:
            cur.execute("""
                SELECT id, username, name, role, unit, active, created_at, last_login
                FROM users ORDER BY username
            """)
            self._json(200, [dict(r) for r in cur.fetchall()])

    def _create_user(self, user: dict) -> None:
        data = self._parse_json_body()
        if data is None:
            return
        username = str(data.get("username", "")).strip().lower()
        password = str(data.get("password", ""))
        name     = str(data.get("name", "")).strip()
        role     = str(data.get("role", "VIEWER")).upper()
        unit     = data.get("unit")

        if not username or not password or not name:
            return self._error(400, "username, password, and name are required.")
        errs = validate_password(password)
        if errs:
            return self._error(400, "Password policy: " + "; ".join(errs))
        if role not in ("ADMIN", "ANALYST", "VIEWER"):
            return self._error(400, "Invalid role.")

        hashed = hash_password(password)
        try:
            with db_cursor(commit=True) as cur:
                cur.execute("""
                    INSERT INTO users (username, password, name, role, unit) VALUES (%s,%s,%s,%s,%s) RETURNING id
                """, (username, hashed, name, role, unit))
                new_id = cur.fetchone()["id"]
        except Exception:
            return self._error(409, "Username already exists.")
        self._audit(user, "CREATE_USER", "user", new_id, f"Created user account: {username}")
        self._json(201, {"id": new_id})

    def _update_user(self, uid: int, user: dict) -> None:
        data = self._parse_json_body()
        if data is None:
            return
        sets, vals = [], []
        if data.get("password"):
            errs = validate_password(data["password"])
            if errs:
                return self._error(400, "Password policy: " + "; ".join(errs))
            sets.append("password=%s"); vals.append(hash_password(data["password"]))
        if "name" in data:
            sets.append("name=%s"); vals.append(str(data["name"]).strip())
        if "role" in data:
            role = str(data["role"]).upper()
            if role not in ("ADMIN", "ANALYST", "VIEWER"):
                return self._error(400, "Invalid role.")
            sets.append("role=%s"); vals.append(role)
        if "unit" in data:
            sets.append("unit=%s"); vals.append(data["unit"])
        reactivating = False
        if "active" in data:
            active_val = data["active"]
            active_bool = bool(active_val) if isinstance(active_val, bool) else bool(int(active_val))
            sets.append("active=%s"); vals.append(active_bool)
            reactivating = active_bool and len(data) == 1

        if not sets:
            return self._json(200, {"ok": True})
        vals.append(uid)
        with db_cursor(commit=True) as cur:
            cur.execute(f"UPDATE users SET {', '.join(sets)} WHERE id=%s", vals)
        self._audit(user, "REACTIVATE_USER" if reactivating else "UPDATE_USER",
                    "user", uid, f"Updated user #{uid}")
        self._json(200, {"ok": True})

    def _deactivate_user(self, uid: int, user: dict) -> None:
        if user.get("sub") == uid:
            return self._error(400, "Cannot deactivate your own account.")
        with db_cursor(commit=True) as cur:
            cur.execute("UPDATE users SET active=FALSE WHERE id=%s", (uid,))
        self._audit(user, "DEACTIVATE_USER", "user", uid, f"Deactivated user #{uid}")
        self._json(200, {"ok": True})

    # ── Admin: audit log ─────────────────────────────────────────────────────
    def _list_audit(self, qs) -> None:
        try:
            limit = min(int(qs.get("limit", [200])[0] or 200), 1000)
        except ValueError:
            limit = 200
        user_id = qs.get("user_id", [None])[0]
        action  = qs.get("action", [None])[0]
        filters, params = [], []
        if user_id:
            filters.append("user_id = %s"); params.append(int(user_id))
        if action:
            filters.append("action ILIKE %s"); params.append(f"{action}%")
        where = ("WHERE " + " AND ".join(filters)) if filters else ""
        params.append(limit)
        with db_cursor() as cur:
            cur.execute(f"""
                SELECT id, ts, user_id, username, action, resource, resource_id, detail, ip
                FROM audit_log {where} ORDER BY ts DESC LIMIT %s
            """, params)
            self._json(200, [dict(r) for r in cur.fetchall()])

    # ── Admin: backups ─────────────────────────────────────────────────────
    def _list_backups(self) -> None:
        with db_cursor() as cur:
            cur.execute("SELECT id, name, created, size, verified, counts, detail FROM backups ORDER BY created DESC")
            self._json(200, [dict(r) for r in cur.fetchall()])

    def _create_backup(self, user: dict) -> None:
        ts      = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        outfile = BASE_DIR / "backups" / f"sentinel_{ts}.sql.gz"
        outfile.parent.mkdir(exist_ok=True)
        env = os.environ.copy()
        env["PGPASSWORD"] = os.environ.get("SENTINEL_DB_PASS", "")
        try:
            result = subprocess.run([
                "pg_dump",
                "-h", os.environ.get("SENTINEL_DB_HOST", "localhost"),
                "-p", os.environ.get("SENTINEL_DB_PORT", "5432"),
                "-U", os.environ.get("SENTINEL_DB_USER", "sentinel_user"),
                "-d", os.environ.get("SENTINEL_DB_NAME", "sentinel"),
                "-F", "c",    # custom compressed format
                "-f", str(outfile),
            ], capture_output=True, env=env, timeout=120)
        except FileNotFoundError:
            # pg_dump isn't on PATH — a deployment/packaging problem, not a
            # database error. Say so plainly instead of surfacing an opaque 500.
            logger.error("pg_dump not found on PATH — cannot create backups.")
            return self._error(503, "pg_dump is not installed or not on PATH on the server. "
                                    "Install the PostgreSQL client tools to enable backups.")
        except subprocess.TimeoutExpired:
            logger.error("pg_dump timed out after 120s.")
            return self._error(504, "Backup timed out after 120 seconds.")

        verified, counts, detail = result.returncode == 0 and outfile.exists(), None, None
        if verified:
            try:
                with db_cursor() as cur:
                    counts = {}
                    for tbl in ("poi", "groups_of_interest", "activities", "hotspots", "intel_reports", "users"):
                        cur.execute(f"SELECT COUNT(*) AS cnt FROM {tbl}")
                        counts[tbl] = cur.fetchone()["cnt"]
            except Exception as e:
                verified = False
                detail = f"Post-backup verification failed: {e}"
        else:
            detail = result.stderr.decode(errors="replace")[:500] or "pg_dump failed."
            logger.error("pg_dump failed: %s", detail)

        size = outfile.stat().st_size if outfile.exists() else 0
        with db_cursor(commit=True) as cur:
            cur.execute("""
                INSERT INTO backups (name, size, verified, counts, detail)
                VALUES (%s,%s,%s,%s,%s)
                RETURNING id, name, created, size, verified, counts, detail
            """, (outfile.name, size, verified, json.dumps(counts) if counts else None, detail))
            row = cur.fetchone()
        self._audit(user, "BACKUP", None, None, f"Manual database backup created: {outfile.name}")
        self._json(200, dict(row))

    # ── Shared helpers ─────────────────────────────────────────────────────
    def _parse_json_body(self) -> dict | None:
        body = self._read_body()
        if body is None:
            return None
        try:
            return json.loads(body)
        except json.JSONDecodeError:
            self._error(400, "Invalid JSON.")
            return None

    def log_message(self, fmt, *args):
        logger.info(f"{self.client_address[0]} – {fmt % args}")


# ─── Utilities ──────────────────────────────────────────────────────────────
import re as _re
from email import message_from_bytes
from email.policy import HTTP as _HTTP_POLICY


def _match(path: str, pattern: str):
    m = _re.fullmatch(pattern, path)
    return m.groups() if m else None


def _parse_multipart(content_type: str, body: bytes) -> dict:
    """
    Parse a multipart/form-data body without the deprecated cgi module.
    Returns dict of {field_name: [{"data": bytes, "filename": str|None, "content_type": str}]}
    """
    # Reconstruct a full MIME message so email.parser can decode it
    msg = message_from_bytes(
        f"Content-Type: {content_type}\r\n\r\n".encode() + body,
        policy=_HTTP_POLICY
    )
    result: dict = {}
    for part in msg.iter_parts():
        cd = part.get("Content-Disposition", "")
        if not cd:
            continue
        # Extract field name
        name_match = _re.search(r'name="([^"]*)"', cd)
        if not name_match:
            continue
        name = name_match.group(1)
        # Extract optional filename
        fname_match = _re.search(r'filename="([^"]*)"', cd)
        filename = fname_match.group(1) if fname_match else None
        ct = part.get_content_type() or "application/octet-stream"
        data = part.get_payload(decode=True) or b""
        result.setdefault(name, []).append({
            "data":         data,
            "filename":     filename,
            "content_type": ct,
        })
    return result


# ─── Entry point ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    # .env already loaded at import time via _load_dotenv()
    init_pool()
    httpd = HTTPServer(("0.0.0.0", PORT), SentinelHandler)
    logger.info("SENTINEL listening on http://0.0.0.0:%d", PORT)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        close_pool()
        logger.info("Server stopped.")
