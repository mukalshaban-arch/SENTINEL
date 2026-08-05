"""Shared HTTP helper for the test suite. Stdlib only (urllib), matching the
project's no-framework, no-build-step philosophy.

The single-threaded dev server (http.server.HTTPServer, not Threading) will
occasionally reset a connection under back-to-back requests — retry once or
twice rather than treat it as a real failure.
"""
import json
import urllib.request
import urllib.error

BASE = "http://localhost:8090"


def call(method, path, token=None, body=None, is_json=True):
    url = BASE + path
    headers = {}
    data = None
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if body is not None:
        if is_json:
            data = json.dumps(body).encode()
            headers["Content-Type"] = "application/json"
        else:
            data = body
    req = urllib.request.Request(url, data=data, headers=headers, method=method)

    code, raw = None, b""
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                code, raw = r.status, r.read()
            break
        except urllib.error.HTTPError as e:
            code = e.code
            try:
                raw = e.read()
            except (ConnectionResetError, OSError):
                raw = b""
            break
        except (ConnectionResetError, OSError):
            if attempt == 2:
                raise
            continue

    try:
        parsed = json.loads(raw)
    except Exception:
        parsed = raw
    return code, parsed


def login(username, password):
    code, r = call("POST", "/api/auth/login", body={"username": username, "password": password})
    return r.get("token") if code == 200 else None


def server_reachable():
    try:
        call("GET", "/")
        return True
    except Exception:
        return False
