# Integration tests (manual / not run in CI)

This suite exercises the real HTTP API end-to-end against a **live server**
backed by a **live PostgreSQL database**, with real writes cleaned up
afterward. It's the right tool for verifying the whole system actually works
together, but it isn't a CI unit-test suite: it needs Postgres reachable,
`server.py` running, and the full ML stack installed (spaCy model, PaddleOCR/
EasyOCR, InsightFace) for the NLP/Face Search checks to pass.

For CI, see `tests/unit/` instead — fast, no external services.

## Running locally

```bat
:: 1. Postgres running, schema loaded, server started
venv\Scripts\python.exe server.py

:: 2. In another terminal
venv\Scripts\python.exe tests\integration\run_all.py
```

Exits 0 on all-pass, 1 if anything fails, 2 if it can't reach the server.
