"""
SENTINEL – nlp_extract.py
Fully offline intelligence-entity extraction: spaCy NER + rule-based
enrichment. Replaces the previous Claude-API-based extraction.

Produces the exact same JSON shape the rest of the pipeline (nlp.commit_job,
the /api/nlp/* routes, the analysis.html review screen) already expects:
    {
      "persons":    [{"name","aliases","nationality","notes"}],
      "groups":     [{"name","category","description","notes"}],
      "locations":  [{"name","address","country","type","notes"}],
      "activities": [{"title","type","date","notes","poi_names","group_names","location_name"}],
      "image_links":[]
    }

Honest limitation: spaCy's statistical NER + these heuristics are noticeably
lower recall/precision than an LLM, especially with the small "sm" model
(no vector-based disambiguation, weaker on unusual names). This is mitigated
by the analyst review step in the UI — every extracted item is a suggestion,
never auto-committed without review — and can be improved by installing a
larger model (see SENTINEL_SPACY_MODEL below).
"""

import os
import re
import logging
from datetime import datetime

from dateutil import parser as dateparser

logger = logging.getLogger("sentinel.nlp_extract")

SPACY_MODEL = os.environ.get("SENTINEL_SPACY_MODEL", "en_core_web_sm")

_nlp = None
_load_failed = False


def _get_spacy():
    """Lazy-load the spaCy pipeline so server startup never blocks on it."""
    global _nlp, _load_failed
    if _nlp is not None or _load_failed:
        return _nlp
    try:
        import spacy
        _nlp = spacy.load(SPACY_MODEL)
        logger.info("spaCy model '%s' loaded.", SPACY_MODEL)
    except Exception as e:
        logger.error(
            "Could not load spaCy model '%s' (%s). Install it with: "
            "python -m pip install <wheel for %s> — see SENTINEL_SETUP_GUIDE.md. "
            "Entity extraction is disabled until a model is available.",
            SPACY_MODEL, e, SPACY_MODEL,
        )
        _load_failed = True
    return _nlp


ACTIVITY_TYPES = {"MEETING", "MOVEMENT", "COMMUNICATION", "FINANCIAL", "SURVEILLANCE", "OTHER"}
_ACTIVITY_KEYWORDS = [
    ("MEETING",       ("met", "meeting", "gathered", "convened", "rendezvous")),
    ("MOVEMENT",      ("travelled", "traveled", "moved", "arrived", "departed", "crossed",
                        "transported", "flew", "drove", "convoy")),
    ("COMMUNICATION", ("called", "phoned", "messaged", "emailed", "texted", "contacted",
                        "communicated", "radioed")),
    ("FINANCIAL",     ("paid", "transferred", "wired", "funded", "financed", "deposited",
                        "laundered", "payment")),
    ("SURVEILLANCE",  ("watched", "monitored", "tracked", "surveilled", "observed",
                        "photographed", "followed")),
]

HOTSPOT_TYPES = {"MEETING_POINT", "LOGISTICS", "FINANCIAL", "COMMAND", "SURVEILLANCE", "GENERAL"}
_LOCATION_KEYWORDS = [
    ("MEETING_POINT", ("hotel", "cafe", "café", "restaurant", "meeting", "rendezvous", "bar")),
    ("LOGISTICS",      ("warehouse", "depot", "port", "airport", "border", "crossing",
                         "storage", "yard", "dock")),
    ("FINANCIAL",      ("bank", "exchange", "wire", "money transfer", "hawala")),
    ("COMMAND",        ("headquarters", "hq", "command", "base", "compound", "safehouse",
                         "safe house")),
    ("SURVEILLANCE",   ("checkpoint", "lookout", "watch post", "observation")),
]

_GROUP_CATEGORY_KEYWORDS = [
    ("Terror Cell",           ("cell", "terror", "extremist", "militant")),
    ("Criminal Organisation", ("cartel", "syndicate", "gang", "mafia", "trafficking",
                                "smuggling", "organised crime", "organized crime")),
    ("Militia",               ("militia", "insurgent", "rebel", "front")),
    ("Front Organisation",    ("front organisation", "front organization", "shell company",
                                "charity front")),
]

_ALIAS_PATTERN = re.compile(
    r"""(?:alias|a\.k\.a\.?|aka|also\s+known\s+as)\s*[:\-]?\s*["“]?([A-Z][\w'\- ]{1,40}?)["”]?(?:[.,;)]|$)""",
    re.IGNORECASE,
)

# Report metadata/header lines ("Analyst: Jane Doe", "Source: HUMINT") name-drop
# real people/orgs that are about the REPORT, not intelligence subjects — skip
# these sentences entirely rather than let the byline become a "person of interest".
_METADATA_LINE = re.compile(
    r"""^(analyst|reported\s+by|report(ed)?\s+by|source|classification|prepared\s+by|
        compiled\s+by|author|distribution|date|reference|case\s*(no|number)?)\s*:""",
    re.IGNORECASE | re.VERBOSE,
)

# Generic institutions spaCy's ORG label frequently catches that are essentially
# never a SENTINEL "Group of Interest" (a tracked criminal/threat network) —
# background references to the UN, the police, a news wire, etc. Matched after
# stripping a leading "the " and lowercasing.
_ORG_STOPLIST = {
    "un", "united nations", "nato", "interpol", "europol", "who",
    "world health organization", "world health organisation",
    "red cross", "red crescent", "eu", "european union", "au", "african union",
    "police", "the police", "military", "government", "parliament", "congress",
    "senate", "court", "supreme court", "embassy", "ministry", "reuters",
    "ap", "associated press", "bbc", "cnn", "al jazeera", "unhcr", "unicef",
    "world bank", "imf", "international monetary fund",
}

# spaCy's small model frequently mislabels 2-3 word Title-Case personal names
# (especially non-Western ones) as GPE/LOC/ORG/PRODUCT. When such a span is
# immediately preceded by a strong "this is a person" cue (a nationality
# word, "national", or a title), reclassify it as PERSON rather than trust
# the model's label. This is a targeted fix for a demonstrated failure mode,
# not a general-purpose name detector.
_PERSON_NAME_SHAPE = re.compile(r"^[A-Z][a-z]+(?:[\s'\-][A-Z][a-z]+){1,2}$")
_PERSON_CUE_WORDS = {
    "national", "citizen", "resident", "mr", "mr.", "mrs", "mrs.", "ms", "ms.",
    "dr", "dr.", "sheikh", "colonel", "general", "commander", "captain",
}


def _reclassify_person_like_spans(doc):
    """Yield (text, label) for every entity, upgrading mislabeled personal
    names (see module note above) from GPE/LOC/ORG/FAC/PRODUCT to PERSON."""
    for ent in doc.ents:
        label = ent.label_
        if label in ("GPE", "LOC", "ORG", "FAC", "PRODUCT") and _PERSON_NAME_SHAPE.match(ent.text.strip()):
            prev_tok = doc[ent.start - 1] if ent.start > 0 else None
            prev2_tok = doc[ent.start - 2] if ent.start > 1 else None
            cue = (
                (prev_tok and prev_tok.text.lower() in _PERSON_CUE_WORDS) or
                (prev2_tok and prev2_tok.text.lower() in _PERSON_CUE_WORDS) or
                (prev_tok and prev_tok.ent_type_ == "NORP")
            )
            if cue:
                label = "PERSON"
        yield ent, label


def _norm(s: str) -> str:
    return " ".join((s or "").strip().split())


def _pick_type(text_lower: str, keyword_table, default):
    for label, keywords in keyword_table:
        if any(kw in text_lower for kw in keywords):
            return label
    return default


def _parse_date(text: str) -> str | None:
    """Best-effort natural-language date -> ISO 8601. Returns None if unparseable."""
    try:
        dt = dateparser.parse(text, fuzzy=True, default=datetime(1900, 1, 1))
        # If the parser silently fell back to the default year, treat it as
        # "no real date found" rather than fabricating 1900-01-01.
        if dt.year == 1900 and "1900" not in text:
            return None
        return dt.date().isoformat()
    except Exception:
        return None


def extract_entities(text: str) -> dict:
    """
    Run offline NER + heuristics over `text` and return the entities dict
    described in the module docstring. Never raises — on any internal error,
    or if no spaCy model is available, returns an all-empty result so the
    calling job is marked 'reviewed' with nothing to commit, rather than
    'failed'.
    """
    empty = {"persons": [], "groups": [], "locations": [], "activities": [], "image_links": []}
    nlp = _get_spacy()
    if nlp is None:
        return empty

    try:
        return _extract(nlp, text)
    except Exception:
        logger.exception("Offline extraction failed; returning empty result.")
        return empty


def _strip_metadata_lines(text: str) -> str:
    """Drop report header/byline LINES ("Analyst: Jane Doe") before spaCy ever
    sees them. Must happen at the line level, not the sentence level: these
    lines have no sentence-ending punctuation, so spaCy's segmenter merges
    them with the real content that follows into one giant "sentence" —
    filtering post-hoc would then discard the real content along with it."""
    kept = [ln for ln in text.split("\n") if not _METADATA_LINE.match(ln.strip())]
    return "\n".join(kept)


def _extract(nlp, text: str) -> dict:
    max_chars = 200_000   # generous local-CPU-friendly cap
    if len(text) > max_chars:
        text = text[:max_chars]
    text = _strip_metadata_lines(text)
    doc = nlp(text)

    # Effective label per entity (start_char, end_char), after upgrading
    # mislabeled personal names — see _reclassify_person_like_spans.
    effective_label = {
        (ent.start_char, ent.end_char): label
        for ent, label in _reclassify_person_like_spans(doc)
    }

    # ---- Global entity roll-up (case-insensitive de-dupe, first-seen casing kept) ----
    # Generic institutions (UN, police, a news wire, ...) are dropped outright —
    # they're essentially never a tracked "Group of Interest", just background noise.
    persons_seen, groups_seen, locations_seen = {}, {}, {}
    for ent in doc.ents:
        name = _norm(ent.text)
        if not name or len(name) < 2:
            continue
        key = name.lower()
        label = effective_label.get((ent.start_char, ent.end_char), ent.label_)
        if label == "PERSON" and key not in persons_seen:
            persons_seen[key] = name
        elif label == "ORG" and key not in groups_seen:
            if re.sub(r"^the\s+", "", key) in _ORG_STOPLIST:
                continue
            groups_seen[key] = name
        elif label in ("GPE", "LOC", "FAC") and key not in locations_seen:
            locations_seen[key] = name

    # ---- Per-sentence pass: nationality/alias for persons, category for groups,
    #      type for locations, and activity construction ----
    person_notes, person_nat, person_alias = {}, {}, {}
    group_notes, group_cat = {}, {}
    location_notes, location_type = {}, {}
    activities = []

    for sent in doc.sents:
        s_text = _norm(sent.text)
        if not s_text:
            continue
        # Skip report metadata/header lines ("Analyst: Jane Doe") — the named
        # person/org there is about the report itself, not an intel subject.
        if _METADATA_LINE.match(s_text):
            continue
        s_lower = s_text.lower()

        sent_labels = {(e.start_char, e.end_char): effective_label.get((e.start_char, e.end_char), e.label_)
                       for e in sent.ents}
        sent_persons = [e for e in sent.ents if sent_labels[(e.start_char, e.end_char)] == "PERSON"]
        sent_orgs    = [e for e in sent.ents if sent_labels[(e.start_char, e.end_char)] == "ORG"
                        and e.text.lower().strip() in groups_seen]
        sent_locs    = [e for e in sent.ents if sent_labels[(e.start_char, e.end_char)] in ("GPE", "LOC", "FAC")]
        sent_norps   = [e for e in sent.ents if e.label_ == "NORP"]
        sent_dates   = [e for e in sent.ents if e.label_ == "DATE"]

        alias_match = _ALIAS_PATTERN.search(s_text)

        for p in sent_persons:
            key = p.text.lower().strip()
            if key not in persons_seen:
                continue
            person_notes.setdefault(key, s_text)
            if sent_norps and key not in person_nat:
                person_nat[key] = _norm(sent_norps[0].text)
            if alias_match and key not in person_alias:
                candidate = _norm(alias_match.group(1))
                if candidate.lower() != key:
                    person_alias[key] = candidate

        for g in sent_orgs:
            key = g.text.lower().strip()
            group_notes.setdefault(key, s_text)
            if key not in group_cat:
                group_cat[key] = _pick_type(s_lower, _GROUP_CATEGORY_KEYWORDS, None)

        for l in sent_locs:
            key = l.text.lower().strip()
            if key not in locations_seen:
                continue
            location_notes.setdefault(key, s_text)
            if key not in location_type:
                location_type[key] = _pick_type(s_lower, _LOCATION_KEYWORDS, "GENERAL")

        # An "activity" needs at least one actor (person/org) AND at least one
        # anchor (a date or a place) — otherwise it's too weak a signal to log
        # as a discrete event rather than just background entity mentions.
        if (sent_persons or sent_orgs) and (sent_dates or sent_locs):
            title = s_text if len(s_text) <= 90 else s_text[:87].rstrip() + "…"
            activities.append({
                "title": title,
                "type": _pick_type(s_lower, _ACTIVITY_KEYWORDS, "OTHER"),
                "date": _parse_date(sent_dates[0].text) if sent_dates else None,
                "notes": s_text,
                "poi_names": [_norm(e.text) for e in sent_persons],
                "group_names": [_norm(e.text) for e in sent_orgs],
                "location_name": _norm(sent_locs[0].text) if sent_locs else None,
            })

    # ---- Relevance gate ----------------------------------------------------
    # Only surface a person/group/location if it's either doing something
    # (appears in a detected activity) or carries its own strong standalone
    # signal (a resolved alias/nationality, a threat category, a specific
    # place type). A bare name mention with none of that is exactly the kind
    # of noise ("every name, every location") this filter exists to drop.
    activity_persons   = {n.lower() for a in activities for n in a["poi_names"]}
    activity_groups    = {n.lower() for a in activities for n in a["group_names"]}
    activity_locations = {a["location_name"].lower() for a in activities if a["location_name"]}

    persons = [{
        "name": name,
        "aliases": person_alias.get(key),
        "nationality": person_nat.get(key),
        "notes": person_notes.get(key, ""),
    } for key, name in persons_seen.items()
      if key in activity_persons or person_alias.get(key) or person_nat.get(key)]

    groups = [{
        "name": name,
        "category": group_cat.get(key),
        "description": None,
        "notes": group_notes.get(key, ""),
    } for key, name in groups_seen.items()
      if key in activity_groups or group_cat.get(key)]

    locations = [{
        "name": name,
        "address": None,
        "country": None,
        "type": location_type.get(key, "GENERAL"),
        "notes": location_notes.get(key, ""),
    } for key, name in locations_seen.items()
      if key in activity_locations or location_type.get(key, "GENERAL") != "GENERAL"]

    return {
        "persons": persons,
        "groups": groups,
        "locations": locations,
        "activities": activities,
        "image_links": [],
    }


def match_images_to_entities(image_files: list[dict], entities: dict) -> list[dict]:
    """
    Offline substitute for Claude-vision image linking: OCRs each image and
    looks for an extracted entity's name in that text. No visual understanding
    — purely text-in-image matching — so this only catches labelled/captioned
    photos (e.g. an ID card, a name plate, a captioned surveillance still),
    not "a photo that looks like this person". Anything it misses is still
    available to attach manually from the entity's own photo panel.
    """
    if not image_files:
        return []
    from ocr_offline import ocr_image

    candidates = (
        [(p["name"], "poi") for p in entities.get("persons", [])] +
        [(g["name"], "group") for g in entities.get("groups", [])] +
        [(l["name"], "location") for l in entities.get("locations", [])]
    )
    if not candidates:
        return []

    links = []
    for f in image_files:
        try:
            text = ocr_image(f["path"])
        except Exception as e:
            logger.warning("Image OCR failed for %s: %s", f["filename"], e)
            continue
        if not text or text.startswith("["):
            continue
        text_lower = text.lower()
        for name, etype in candidates:
            if name.lower() in text_lower:
                links.append({
                    "filename": f["filename"],
                    "entity_type": etype,
                    "entity_name": name,
                    "reason": "Name found in image text (OCR match).",
                    "confidence": "medium",
                })
    return links
