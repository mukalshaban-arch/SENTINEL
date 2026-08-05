"""Handler-level unit tests for server.py with the database mocked out.

The security-critical part here is the role guard: every handler that writes
data must reject a VIEWER *server-side*. That guard was originally missing on
almost every mutating endpoint (enforcement was frontend-only, so a direct
API call bypassed it entirely). The parametrized tests below assert the guard
on each handler individually, so re-introducing the bug on any single one
fails CI rather than shipping silently.
"""
from contextlib import contextmanager
from unittest.mock import MagicMock

import pytest

import server


@pytest.fixture
def handler(monkeypatch):
    """A fake SentinelHandler with DB access and response-writing stubbed.
    Handler methods are invoked unbound (server.SentinelHandler.<m>(handler,...))
    so no socket/HTTP machinery is ever constructed."""
    h = MagicMock()
    # Real guard, so tests exercise the actual authorization logic rather than
    # a mock that always returns True.
    h._require_edit_role.side_effect = lambda user: \
        server.SentinelHandler._require_edit_role(h, user)

    cursor = MagicMock()
    cursor.fetchone.return_value = {"id": 123}
    cursor.fetchall.return_value = []

    @contextmanager
    def _fake_db_cursor(commit: bool = False):
        yield cursor

    monkeypatch.setattr(server, "db_cursor", _fake_db_cursor)
    h._cursor = cursor
    return h


VIEWER = {"role": "VIEWER", "usr": "viewer", "sub": 3}
ANALYST = {"role": "ANALYST", "usr": "analyst", "sub": 2}
ADMIN = {"role": "ADMIN", "usr": "admin", "sub": 1}


# Each entry: (handler_name, args_before_user) — `user` is always passed last,
# matching the convention across every mutating handler in server.py.
MUTATING_HANDLERS = [
    ("_create_person", ()),
    ("_update_person", (1,)),
    ("_create_group", ()),
    ("_update_group", (1,)),
    ("_create_location", ()),
    ("_create_activity", ()),
    ("_update_activity", (1,)),
    ("_create_hotspot", ()),
    ("_update_hotspot", (1,)),
    ("_create_intel", ()),
    ("_update_intel", (1,)),
    ("_add_gallery", (1,)),
    ("_delete_gallery", (1, 2)),
    ("_nlp_submit", ()),
    ("_nlp_commit", (1,)),
    ("_nlp_reject", (1,)),
    ("_create_link_chart", ()),
    ("_update_link_chart", (1,)),
    ("_delete_link_chart", (1,)),
    ("_add_link_chart_node", (1,)),
    ("_update_link_chart_node", (1, 2)),
    ("_delete_link_chart_node", (1, 2)),
]


@pytest.mark.parametrize("handler_name,args", MUTATING_HANDLERS)
def test_viewer_is_blocked_from_every_mutating_handler(handler, handler_name, args):
    """Regression guard for the VIEWER write-access bypass."""
    method = getattr(server.SentinelHandler, handler_name)
    method(handler, *args, VIEWER)

    handler._error.assert_called_once_with(403, "Analyst or Administrator role required.")
    # Must reject before doing any work.
    handler._parse_json_body.assert_not_called()


@pytest.mark.parametrize("handler_name,args", MUTATING_HANDLERS)
def test_analyst_passes_the_role_guard(handler, handler_name, args):
    """The guard must not over-block: ANALYST reaches past it. We only assert
    no 403 was raised — what each handler does next varies and is covered by
    the integration suite."""
    handler._parse_json_body.return_value = {}
    method = getattr(server.SentinelHandler, handler_name)
    try:
        method(handler, *args, ANALYST)
    except Exception:
        pass  # handler-specific work may fail against mocks; the guard is what matters

    forbidden = [c for c in handler._error.call_args_list if c[0][0] == 403]
    assert not forbidden, f"{handler_name} wrongly returned 403 for ANALYST"


# ── _delete_entity (its own inline guard, predates _require_edit_role) ────
def test_delete_entity_blocks_viewer(handler):
    server.SentinelHandler._delete_entity(handler, "poi", 1, VIEWER)
    handler._error.assert_called_once_with(403, "Insufficient privileges.")


def test_delete_entity_rejects_table_not_on_whitelist(handler):
    """SQL-injection guard: the table name is interpolated into the DELETE, so
    it must come from a fixed whitelist."""
    server.SentinelHandler._delete_entity(handler, "users; DROP TABLE poi;--", 1, ADMIN)
    handler._error.assert_called_once_with(400, "Invalid entity type.")


@pytest.mark.parametrize("table", [
    "poi", "groups_of_interest", "locations", "activities", "hotspots", "intel_reports",
])
def test_delete_entity_accepts_whitelisted_tables(handler, table):
    server.SentinelHandler._delete_entity(handler, table, 1, ADMIN)
    errors = [c for c in handler._error.call_args_list]
    assert not errors
    handler._json.assert_called_once_with(200, {"ok": True})


# ── Input validation on create handlers ──────────────────────────────────
def test_create_person_requires_alias(handler):
    handler._parse_json_body.return_value = {"nationality": "Kenyan"}
    server.SentinelHandler._create_person(handler, ANALYST)
    handler._error.assert_called_once_with(400, "Alias is required.")


def test_create_person_succeeds_with_alias(handler):
    handler._parse_json_body.return_value = {"alias": "Test Subject"}
    server.SentinelHandler._create_person(handler, ANALYST)
    handler._json.assert_called_once_with(201, {"id": 123})


def test_create_person_aborts_on_invalid_json(handler):
    handler._parse_json_body.return_value = None  # _parse_json_body already sent 400
    server.SentinelHandler._create_person(handler, ANALYST)
    handler._json.assert_not_called()


def test_create_intel_requires_title(handler):
    handler._parse_json_body.return_value = {"body": "no title"}
    server.SentinelHandler._create_intel(handler, ANALYST)
    handler._error.assert_called_once_with(400, "Title is required.")


# ── Link-chart node validation (country names must be real) ──────────────
def test_add_link_chart_node_rejects_unknown_node_type(handler):
    handler._parse_json_body.return_value = {"nodeType": "alien", "nodeRef": "x"}
    server.SentinelHandler._add_link_chart_node(handler, 1, ANALYST)
    handler._error.assert_called_once_with(400, "nodeType must be person, group, or country.")


def test_add_link_chart_node_rejects_unrecognised_country(handler):
    handler._parse_json_body.return_value = {"nodeType": "country", "nodeRef": "Nowhereistan"}
    server.SentinelHandler._add_link_chart_node(handler, 1, ANALYST)
    handler._error.assert_called_once_with(400, "Not a recognised country.")


def test_add_link_chart_node_canonicalises_country_name(handler):
    handler._parse_json_body.return_value = {"nodeType": "country", "nodeRef": "kenya", "x": 0, "y": 0}
    server.SentinelHandler._add_link_chart_node(handler, 1, ANALYST)
    # The INSERT must receive the canonical "Kenya", not the lowercase input.
    insert_params = handler._cursor.execute.call_args_list[0][0][1]
    assert "Kenya" in insert_params


def test_add_link_chart_node_requires_node_ref_for_person(handler):
    handler._parse_json_body.return_value = {"nodeType": "person", "nodeRef": ""}
    server.SentinelHandler._add_link_chart_node(handler, 1, ANALYST)
    handler._error.assert_called_once_with(400, "nodeRef is required.")


def test_add_link_chart_node_reports_duplicate(handler):
    handler._parse_json_body.return_value = {"nodeType": "country", "nodeRef": "Kenya"}
    handler._cursor.fetchone.return_value = None  # ON CONFLICT DO NOTHING -> no row
    server.SentinelHandler._add_link_chart_node(handler, 1, ANALYST)
    handler._error.assert_called_once_with(409, "That node is already on this chart.")


# ── _resolve_link_node ────────────────────────────────────────────────────
def test_resolve_link_node_country_needs_no_db_lookup():
    result = server.SentinelHandler._resolve_link_node("country", "Kenya")
    assert result["label"] == "Kenya"


def test_resolve_link_node_returns_none_for_non_numeric_person_ref():
    assert server.SentinelHandler._resolve_link_node("person", "not-a-number") is None
