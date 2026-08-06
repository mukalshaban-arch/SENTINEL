"""Unit tests for summarize.py — the optional, online-only AI narrative
assessment. The Anthropic SDK is stubbed throughout: no API key is used and
no network call is ever made.

What matters here is that every unavailable/misconfigured/failed state
raises RuntimeError with an actionable message, because server.py turns that
into a clean 503 rather than a generic 500.
"""
import sys
import types

import pytest

import summarize


class _FakeAuthError(Exception):
    pass


class _FakeConnError(Exception):
    pass


class _FakeAPIError(Exception):
    def __init__(self, message="boom"):
        super().__init__(message)
        self.message = message


def _install_fake_sdk(monkeypatch, *, create=None):
    """Install a stand-in `anthropic` module with the exception types
    summarize.py catches, plus a client whose messages.create is `create`."""
    fake = types.ModuleType("anthropic")
    fake.AuthenticationError = _FakeAuthError
    fake.APIConnectionError = _FakeConnError
    fake.APIError = _FakeAPIError

    class _Messages:
        def create(self, **kwargs):
            return create(**kwargs)

    class _Client:
        def __init__(self, api_key=None):
            self.api_key = api_key
            self.messages = _Messages()

    fake.Anthropic = _Client
    monkeypatch.setitem(sys.modules, "anthropic", fake)
    monkeypatch.setattr(summarize, "anthropic", fake, raising=False)
    monkeypatch.setattr(summarize, "ANTHROPIC_AVAILABLE", True)
    return fake


def _ok_response(text="## Summary\nA neutral assessment."):
    block = types.SimpleNamespace(text=text)
    return types.SimpleNamespace(content=[block])


DOSSIER = {"alias": "Test Subject", "nationality": "Kenya", "activities": []}


# ── Unavailable / unconfigured backends ──────────────────────────────────
def test_raises_when_sdk_not_installed(monkeypatch):
    monkeypatch.setattr(summarize, "ANTHROPIC_AVAILABLE", False)
    with pytest.raises(RuntimeError, match="anthropic SDK not installed"):
        summarize.generate_summary(DOSSIER)


def test_raises_when_api_key_missing(monkeypatch):
    _install_fake_sdk(monkeypatch, create=lambda **kw: _ok_response())
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
        summarize.generate_summary(DOSSIER)


def test_raises_when_api_key_is_blank(monkeypatch):
    _install_fake_sdk(monkeypatch, create=lambda **kw: _ok_response())
    monkeypatch.setenv("ANTHROPIC_API_KEY", "")
    with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
        summarize.generate_summary(DOSSIER)


# ── Success path ─────────────────────────────────────────────────────────
def test_returns_stripped_assessment_text(monkeypatch):
    _install_fake_sdk(monkeypatch, create=lambda **kw: _ok_response("  ## Summary\nBody.  "))
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    assert summarize.generate_summary(DOSSIER) == "## Summary\nBody."


def test_sends_configured_model_and_system_prompt(monkeypatch):
    captured = {}

    def create(**kwargs):
        captured.update(kwargs)
        return _ok_response()

    _install_fake_sdk(monkeypatch, create=create)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    summarize.generate_summary(DOSSIER)

    assert captured["model"] == summarize.SUMMARY_MODEL
    assert captured["system"] == summarize.SUMMARY_SYSTEM_PROMPT
    assert captured["max_tokens"] == 1500


def test_dossier_is_serialised_into_the_user_message(monkeypatch):
    captured = {}

    def create(**kwargs):
        captured.update(kwargs)
        return _ok_response()

    _install_fake_sdk(monkeypatch, create=create)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    summarize.generate_summary(DOSSIER)

    content = captured["messages"][0]["content"]
    assert "Test Subject" in content


def test_oversized_dossier_is_truncated(monkeypatch):
    captured = {}

    def create(**kwargs):
        captured.update(kwargs)
        return _ok_response()

    _install_fake_sdk(monkeypatch, create=create)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    summarize.generate_summary({"notes": "x" * 100_000})

    content = captured["messages"][0]["content"]
    assert "dossier truncated for length" in content


def test_non_serialisable_dossier_values_do_not_raise(monkeypatch):
    from datetime import date

    _install_fake_sdk(monkeypatch, create=lambda **kw: _ok_response())
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    # default=str in the json.dumps call must absorb date/Decimal/etc.
    assert summarize.generate_summary({"seen": date(2024, 1, 1)})


# ── API failure translation ──────────────────────────────────────────────
def test_auth_error_becomes_actionable_runtime_error(monkeypatch):
    def create(**kwargs):
        raise _FakeAuthError()

    _install_fake_sdk(monkeypatch, create=create)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "bad-key")
    with pytest.raises(RuntimeError, match="invalid or expired"):
        summarize.generate_summary(DOSSIER)


def test_connection_error_mentions_connectivity(monkeypatch):
    def create(**kwargs):
        raise _FakeConnError()

    _install_fake_sdk(monkeypatch, create=create)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    with pytest.raises(RuntimeError, match="Could not reach"):
        summarize.generate_summary(DOSSIER)


def test_generic_api_error_is_wrapped(monkeypatch):
    def create(**kwargs):
        raise _FakeAPIError("rate limited")

    _install_fake_sdk(monkeypatch, create=create)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    with pytest.raises(RuntimeError, match="rate limited"):
        summarize.generate_summary(DOSSIER)
