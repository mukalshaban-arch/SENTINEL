"""Unit tests for server.py's pure request-handling helpers: route regex
matching, multipart body parsing, JSON serialization of DB-native types, and
the role guard that fixed the VIEWER write-access bypass. These don't need
an HTTP server, a socket, or a DB — server.py is imported directly and its
handler methods are called with a lightweight fake `self`.

Importing server.py pulls in nlp.py/face_match.py/ocr_offline.py, but all of
those lazy-load their actual ML dependencies inside functions, so this stays
fast and dependency-light (see tests/unit/conftest.py)."""
import json
import uuid
from datetime import datetime, date, timezone
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

import server


# ── _match (route regex) ──────────────────────────────────────────────────
def test_match_returns_none_when_no_match():
    assert server._match("/api/persons", r"/api/groups/(\d+)$") is None


def test_match_extracts_single_capture_group():
    assert server._match("/api/persons/42", r"/api/persons/(\d+)$") == ("42",)


def test_match_extracts_multiple_capture_groups():
    result = server._match("/api/link-charts/3/nodes/9", r"/api/link-charts/(\d+)/nodes/(\d+)$")
    assert result == ("3", "9")


def test_match_requires_full_match_not_prefix():
    # A route matcher using fullmatch must not match a longer path than the pattern.
    assert server._match("/api/persons/42/extra", r"/api/persons/(\d+)$") is None


def test_match_no_capture_groups_returns_empty_tuple():
    assert server._match("/api/groups", r"/api/groups") == ()


# ── _json_default (serializer for Postgres-native types) ─────────────────
def test_json_default_datetime():
    dt = datetime(2024, 5, 5, 12, 30, tzinfo=timezone.utc)
    assert server._json_default(dt) == dt.isoformat()


def test_json_default_date():
    d = date(2024, 5, 5)
    assert server._json_default(d) == "2024-05-05"


def test_json_default_decimal():
    assert server._json_default(Decimal("3.14")) == pytest.approx(3.14)
    assert isinstance(server._json_default(Decimal("3.14")), float)


def test_json_default_uuid():
    u = uuid.uuid4()
    assert server._json_default(u) == str(u)


def test_json_default_bytes():
    assert server._json_default(b"hello") == "hello"


def test_json_default_unsupported_type_raises():
    class Unsupported:
        pass
    with pytest.raises(TypeError):
        server._json_default(Unsupported())


def test_json_dumps_with_default_handles_mixed_payload():
    payload = {"created_at": date(2024, 1, 1), "amount": Decimal("9.5"), "id": uuid.uuid4()}
    dumped = json.dumps(payload, default=server._json_default)
    reloaded = json.loads(dumped)
    assert reloaded["created_at"] == "2024-01-01"
    assert reloaded["amount"] == 9.5


# ── _parse_multipart ───────────────────────────────────────────────────────
def _build_multipart_body(boundary: str, fields: list[tuple]) -> bytes:
    """fields: list of (name, value_bytes, filename_or_None, content_type)"""
    parts = []
    for name, value, filename, content_type in fields:
        header = f'Content-Disposition: form-data; name="{name}"'
        if filename:
            header += f'; filename="{filename}"'
        header += f"\r\nContent-Type: {content_type}\r\n\r\n"
        parts.append(f"--{boundary}\r\n".encode() + header.encode() + value)
    body = b"\r\n".join(parts) + f"\r\n--{boundary}--\r\n".encode()
    return body


def test_parse_multipart_extracts_text_field():
    boundary = "TESTBOUNDARY"
    body = _build_multipart_body(boundary, [
        ("text", b"hello world", None, "text/plain"),
    ])
    result = server._parse_multipart(f"multipart/form-data; boundary={boundary}", body)
    assert result["text"][0]["data"] == b"hello world"
    assert result["text"][0]["filename"] is None


def test_parse_multipart_extracts_file_field_with_filename():
    boundary = "TESTBOUNDARY"
    body = _build_multipart_body(boundary, [
        ("file", b"\x89PNG-fake-bytes", "photo.png", "image/png"),
    ])
    result = server._parse_multipart(f"multipart/form-data; boundary={boundary}", body)
    assert result["file"][0]["filename"] == "photo.png"
    assert result["file"][0]["content_type"] == "image/png"
    assert result["file"][0]["data"] == b"\x89PNG-fake-bytes"


def test_parse_multipart_multiple_fields():
    boundary = "TESTBOUNDARY"
    body = _build_multipart_body(boundary, [
        ("text", b"some text", None, "text/plain"),
        ("file", b"filedata", "doc.txt", "text/plain"),
    ])
    result = server._parse_multipart(f"multipart/form-data; boundary={boundary}", body)
    assert set(result.keys()) == {"text", "file"}


def test_parse_multipart_empty_body_returns_empty_dict():
    result = server._parse_multipart("multipart/form-data; boundary=X", b"")
    assert result == {}


# ── _require_edit_role (the VIEWER-write-bypass fix) ─────────────────────
@pytest.mark.parametrize("role", ["ADMIN", "ANALYST"])
def test_require_edit_role_allows_admin_and_analyst(role):
    fake_self = MagicMock()
    allowed = server.SentinelHandler._require_edit_role(fake_self, {"role": role})
    assert allowed is True
    fake_self._error.assert_not_called()


@pytest.mark.parametrize("role", ["VIEWER", "", None, "GARBAGE"])
def test_require_edit_role_blocks_everyone_else(role):
    fake_self = MagicMock()
    allowed = server.SentinelHandler._require_edit_role(fake_self, {"role": role})
    assert allowed is False
    fake_self._error.assert_called_once_with(403, "Analyst or Administrator role required.")


def test_require_edit_role_handles_missing_role_key():
    fake_self = MagicMock()
    allowed = server.SentinelHandler._require_edit_role(fake_self, {})
    assert allowed is False


# ── safe_static_path (path-traversal prevention) ─────────────────────────
def test_safe_static_path_resolves_existing_file():
    # login.html ships with the app — a real file inside static/.
    result = server.safe_static_path("/login.html")
    assert result is not None
    assert result.name == "login.html"


def test_safe_static_path_defaults_to_index_html():
    result = server.safe_static_path("/")
    assert result is not None
    assert result.name == "index.html"


def test_safe_static_path_strips_query_string():
    result = server.safe_static_path("/login.html?next=/dashboard")
    assert result is not None
    assert result.name == "login.html"


@pytest.mark.parametrize("attack", [
    "/../server.py",
    "/../../etc/passwd",
    "/../.env",
    "/subdir/../../server.py",
])
def test_safe_static_path_blocks_traversal(attack):
    assert server.safe_static_path(attack) is None


def test_safe_static_path_returns_none_for_missing_file():
    assert server.safe_static_path("/definitely-not-a-real-file.html") is None


def test_safe_static_path_returns_none_for_directory():
    # vendor/ exists inside static/ but is a directory, not a file.
    assert server.safe_static_path("/vendor") is None


# ── _cors_headers (strict origin whitelist) ──────────────────────────────
def test_cors_headers_allows_whitelisted_origin(monkeypatch):
    monkeypatch.setattr(server, "ALLOWED_ORIGINS", {"http://localhost:8090"})
    fake_self = MagicMock()
    fake_self.headers = {"Origin": "http://localhost:8090"}
    fake_self._origin = lambda: "http://localhost:8090"

    headers = server.SentinelHandler._cors_headers(fake_self)
    assert headers["Access-Control-Allow-Origin"] == "http://localhost:8090"
    assert headers["Vary"] == "Origin"


def test_cors_headers_rejects_unknown_origin(monkeypatch):
    monkeypatch.setattr(server, "ALLOWED_ORIGINS", {"http://localhost:8090"})
    fake_self = MagicMock()
    fake_self._origin = lambda: "http://evil.example.com"

    assert server.SentinelHandler._cors_headers(fake_self) == {}


def test_cors_headers_empty_when_no_origin(monkeypatch):
    monkeypatch.setattr(server, "ALLOWED_ORIGINS", {"http://localhost:8090"})
    fake_self = MagicMock()
    fake_self._origin = lambda: ""
    assert server.SentinelHandler._cors_headers(fake_self) == {}


# ── _read_body (size cap) ─────────────────────────────────────────────────
def test_read_body_reads_declared_length():
    fake_self = MagicMock()
    fake_self.headers = {"Content-Length": "5"}
    fake_self.rfile.read.return_value = b"hello"

    assert server.SentinelHandler._read_body(fake_self) == b"hello"


def test_read_body_returns_empty_for_zero_length():
    fake_self = MagicMock()
    fake_self.headers = {}
    assert server.SentinelHandler._read_body(fake_self) == b""


def test_read_body_rejects_oversized_body():
    fake_self = MagicMock()
    fake_self.headers = {"Content-Length": str(server.MAX_BODY_BYTES + 1)}

    assert server.SentinelHandler._read_body(fake_self) is None
    fake_self._error.assert_called_once_with(413, "Request body too large.")
    fake_self.rfile.read.assert_not_called()  # must reject *before* reading


# ── _parse_json_body ──────────────────────────────────────────────────────
def test_parse_json_body_valid_json():
    fake_self = MagicMock()
    fake_self._read_body.return_value = b'{"alias": "Test"}'
    assert server.SentinelHandler._parse_json_body(fake_self) == {"alias": "Test"}


def test_parse_json_body_invalid_json_returns_none_and_errors():
    fake_self = MagicMock()
    fake_self._read_body.return_value = b"{not valid json"

    assert server.SentinelHandler._parse_json_body(fake_self) is None
    fake_self._error.assert_called_once_with(400, "Invalid JSON.")


def test_parse_json_body_propagates_none_from_oversized_body():
    fake_self = MagicMock()
    fake_self._read_body.return_value = None  # _read_body already sent 413

    assert server.SentinelHandler._parse_json_body(fake_self) is None
    fake_self._error.assert_not_called()  # must not double-report


# ── _require_auth (error-code translation) ───────────────────────────────
def test_require_auth_returns_payload_on_success(monkeypatch):
    monkeypatch.setattr(server, "require_auth", lambda headers, role: {"role": "ADMIN", "usr": "a"})
    fake_self = MagicMock()
    fake_self.headers = {}

    assert server.SentinelHandler._require_auth(fake_self)["role"] == "ADMIN"


@pytest.mark.parametrize("raised,expected_code", [
    ("401: Invalid or expired token.", 401),
    ("403: Role 'ADMIN' or higher required.", 403),
])
def test_require_auth_translates_permission_error_to_status_code(monkeypatch, raised, expected_code):
    def _raise(headers, role):
        raise PermissionError(raised)
    monkeypatch.setattr(server, "require_auth", _raise)

    fake_self = MagicMock()
    fake_self.headers = {}

    assert server.SentinelHandler._require_auth(fake_self) is None
    assert fake_self._error.call_args[0][0] == expected_code
