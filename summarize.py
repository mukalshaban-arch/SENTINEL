"""
SENTINEL – summarize.py
Generates a narrative intelligence assessment for a subject (person or group)
from its aggregated dossier.

The model call sits behind generate_summary(dossier) so it can be swapped for a
local model later (Phase 3 — offline) without touching any caller. Cloud
(Anthropic) for now, mirroring nlp.py's setup. Model is configurable via
SENTINEL_SUMMARY_MODEL (defaults to the same model used for extraction).
"""

import os
import json
import logging

logger = logging.getLogger("sentinel.summarize")

try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False
    logger.warning("anthropic SDK not installed — narrative summaries disabled.")

SUMMARY_MODEL = os.environ.get("SENTINEL_SUMMARY_MODEL", "claude-opus-4-8")

SUMMARY_SYSTEM_PROMPT = """You are an intelligence analyst assistant for SENTINEL, a \
restricted intelligence tracking system. Given a structured dossier on a subject (a \
person or a group of interest), write a concise, professional intelligence assessment \
in British English.

Rules:
- Base EVERY statement only on the dossier provided. Never invent names, dates, \
locations, affiliations, or events. If something is not in the dossier, do not assert it.
- Where information is missing, say so plainly (e.g. "No known associates on record") \
rather than speculating or filling gaps.
- Neutral, factual, analytic tone — no sensational or emotive language.
- Use these markdown section headings, and OMIT any section that has no supporting data:
  ## Summary  — 2–4 sentence overview: who/what the subject is, status, headline risk.
  ## Profile  — key identifying details and background from the dossier.
  ## Affiliations & Network  — known groups, members, or associates and their roles.
  ## Activity Pattern  — what the recorded activities indicate (types, cadence, recency).
  ## Geographic Footprint  — locations of note and any movement pattern.
  ## Assessment  — the analytic bottom line and the recorded risk/threat level, with an \
explicit caveat about how complete or sparse the underlying data is.
Keep the whole assessment under roughly 400 words."""


def generate_summary(dossier: dict) -> str:
    """Return a narrative intelligence assessment (markdown) for a dossier.

    Swappable seam: today this delegates to the Anthropic API; a local model can
    replace _call_model without changing callers. Raises RuntimeError with an
    actionable message when the backend is unavailable/unconfigured, so the API
    layer can surface a clear error instead of a generic 500.
    """
    return _call_model(dossier)


def _call_model(dossier: dict) -> str:
    if not ANTHROPIC_AVAILABLE:
        raise RuntimeError("anthropic SDK not installed. Run: pip install anthropic")
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not set in .env")

    client = anthropic.Anthropic(api_key=api_key)
    payload = json.dumps(dossier, indent=2, default=str, ensure_ascii=False)
    max_chars = 60000
    if len(payload) > max_chars:
        payload = payload[:max_chars] + "\n[... dossier truncated for length ...]"

    try:
        response = client.messages.create(
            model=SUMMARY_MODEL,
            max_tokens=1500,
            system=SUMMARY_SYSTEM_PROMPT,
            messages=[{
                "role": "user",
                "content": f"Subject dossier (JSON):\n\n{payload}\n\nWrite the intelligence assessment.",
            }],
        )
    except anthropic.AuthenticationError:
        raise RuntimeError("Anthropic API key is invalid or expired — update ANTHROPIC_API_KEY in .env.")
    except anthropic.APIConnectionError:
        raise RuntimeError("Could not reach the summarization service (no network?). "
                           "This step needs connectivity until the offline model (Phase 3) is in place.")
    except anthropic.APIError as e:
        raise RuntimeError(f"Summarization service error: {getattr(e, 'message', str(e))}")
    return response.content[0].text.strip()
