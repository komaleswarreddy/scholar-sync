"""
studio_flashcards_evaluators.py

LangSmith custom evaluators for Agent 12: Studio Flashcards Generator.

Agent role:
- Generates a JSON flashcard deck from retrieved source excerpts.
- Production pairs the shared Studio system prompt (#10) with the flashcards task prompt.
- Custom instructions may override count, difficulty, focus, or style.

Production dependencies:
- Inputs:
    context: str
    custom_instructions: str
- Output:
    flashcards_json: {
        "title": str,
        "cards": [
            {
                "front": str,
                "back": str,
                "type": optional str,
                "source_hint": optional str
            }
        ]
    }

- Depends on retrieved Studio context.
- Studio retrieval may use Query Rewriter (#2) upstream.
- Agent 12 is wrapped by Studio System JSON (#10), but this evaluator should only
  require context + custom_instructions.

Design choice:
- Code-first, not LLM/hybrid.
- Criticality: Tier 2, student-facing Studio output.
- Main failures are deterministic:
  invalid JSON, wrong card count, missing front/back, duplicated cards,
  front/back leakage, too verbose cards, no-source fabrication, weak source grounding,
  custom instruction misses, and poor spaced-review card design.
- Avoid an LLM judge here to prevent overfitting/cost. Agent 7 already carries
  semantic RAG judgment; flashcard quality is mostly structure + grounding + usability.

LangSmith usage:
    from studio_flashcards_evaluators import PER_EXAMPLE_EVALUATORS, SUMMARY_EVALUATORS

    client.evaluate(
        target_fn,
        data="nbm-prompt-studio_flashcards",
        evaluators=PER_EXAMPLE_EVALUATORS,
        summary_evaluators=SUMMARY_EVALUATORS,
    )
"""

from __future__ import annotations

import json
import re
from typing import Any, Optional


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

REQUIRED_KEYS = {"flashcards_json"}
ALLOWED_KEYS = {"flashcards_json"}

DECK_REQUIRED_KEYS = {"title", "cards"}
CARD_REQUIRED_KEYS = {"front", "back"}

DEFAULT_MIN_CARDS = 8
DEFAULT_MAX_CARDS = 15

NO_SOURCE_VARIATIONS = {"no_source", "empty_context"}
MULTI_SOURCE_VARIATIONS = {"multi_source"}

EMPTY_CONTEXT_MARKERS = {
    "", "none", "n/a", "no context", "empty", "not provided",
}

BANNED_PATTERNS = {
    "as an ai language model",
    "i cannot access",
    "i don't have access",
}

PLACEHOLDER_PATTERNS = {
    "front", "back", "card front", "card back", "term here", "definition here",
    "placeholder", "sample card", "question here", "answer here",
}

GENERIC_WORDS = {
    "flashcard", "flashcards", "cards", "card", "front", "back", "answer",
    "question", "definition", "term", "concept", "explain", "context",
    "source", "sources", "chapter", "student", "students", "review",
    "remember", "recall", "practice", "deck", "title", "type", "hint",
    "using", "based", "following", "given", "excerpt", "important",
}

FORMULA_HINTS = {"formula", "equation", "numerical", "derive", "expression"}
DEFINITION_HINTS = {"definition", "define", "term", "meaning", "vocabulary"}
CONCEPT_HINTS = {"concept", "understand", "explain", "why", "how"}

MAX_FRONT_WORDS = 24
MAX_BACK_WORDS = 60
MIN_BACK_WORDS = 2


# ---------------------------------------------------------------------------
# Safe helpers
# ---------------------------------------------------------------------------

def _safe_get_outputs(run) -> Optional[dict]:
    try:
        out = run.outputs
        return out if isinstance(out, dict) else None
    except Exception:
        return None


def _safe_get_inputs(example) -> dict:
    try:
        inputs = example.inputs
        return inputs if isinstance(inputs, dict) else {}
    except Exception:
        return {}


def _safe_get_reference(example) -> Optional[dict]:
    try:
        ref = example.outputs
        return ref if isinstance(ref, dict) else None
    except Exception:
        return None


def _safe_get_metadata(example) -> dict:
    try:
        meta = example.metadata or {}
        return meta if isinstance(meta, dict) else {}
    except Exception:
        return {}


def _safe_get_variation(example) -> str:
    return str(_safe_get_metadata(example).get("variation", "unknown"))


def _norm(text: Any) -> str:
    if text is None:
        return ""
    return re.sub(r"\s+", " ", str(text).strip().lower())


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-zA-Z0-9Ωμ°/+=∩∪^²³().-]+", _norm(text)))


def _content_tokens(text: str) -> set[str]:
    stop = {
        "the", "a", "an", "and", "or", "to", "of", "in", "on", "for", "with",
        "is", "are", "was", "were", "be", "been", "being", "this", "that",
        "it", "as", "by", "from", "source", "context", "excerpt", "card",
        "front", "back", "answer", "question", "definition", "term",
    }
    return {t for t in _tokens(text) if len(t) > 2 and t not in stop}


def _jaccard(a: str, b: str) -> float:
    ta, tb = _content_tokens(a), _content_tokens(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def _contains_any(text: str, needles) -> bool:
    t = _norm(text)
    return any(_norm(n) in t for n in needles)


def _word_count(text: str) -> int:
    return len(re.findall(r"\S+", text or ""))


def _is_empty_context(context: str) -> bool:
    return _norm(context) in EMPTY_CONTEXT_MARKERS or _word_count(context) < 3


def _parse_deck(value: Any) -> tuple[bool, Optional[dict], str]:
    """
    Accepts already parsed dict or JSON string.
    Rejects markdown fences and trailing prose.
    """
    if isinstance(value, dict):
        return True, value, json.dumps(value, ensure_ascii=False)

    if not isinstance(value, str):
        return False, None, str(value)

    raw = value.strip()
    if not raw:
        return False, None, raw

    if "```" in raw:
        return False, None, raw

    try:
        parsed = json.loads(raw)
    except Exception:
        return False, None, raw

    return (True, parsed, raw) if isinstance(parsed, dict) else (False, None, raw)


def _get_deck(out: Optional[dict]) -> Optional[dict]:
    if not isinstance(out, dict):
        return None
    ok, parsed, _ = _parse_deck(out.get("flashcards_json"))
    return parsed if ok else None


def _get_gold_deck(ref: Optional[dict]) -> Optional[dict]:
    if not isinstance(ref, dict):
        return None
    ok, parsed, _ = _parse_deck(ref.get("flashcards_json"))
    return parsed if ok else None


def _cards(deck: Optional[dict]) -> list[dict]:
    if not isinstance(deck, dict):
        return []
    cards = deck.get("cards")
    return cards if isinstance(cards, list) else []


def _flatten_deck_text(deck: Optional[dict]) -> str:
    if not isinstance(deck, dict):
        return ""
    try:
        return json.dumps(deck, ensure_ascii=False)
    except Exception:
        return str(deck)


def _extract_requested_count(custom: str) -> Optional[int]:
    text = _norm(custom)
    patterns = [
        r"\bexactly\s+(\d+)\b",
        r"\b(\d+)\s*cards?\b",
        r"\b(\d+)\s*flashcards?\b",
        r"\bmake\s+(\d+)\b",
        r"\bgenerate\s+(\d+)\b",
    ]
    for p in patterns:
        m = re.search(p, text)
        if m:
            return int(m.group(1))
    return None


def _extract_focus_terms(custom: str) -> set[str]:
    terms = set()
    for m in re.findall(r"(?:focus|only|on|about)\s+([a-zA-Z0-9Ωμ°/+=∩∪^²³(). -]{3,90})", custom, flags=re.IGNORECASE):
        segment = re.split(r"[,;—-]|difficulty|easy|medium|hard|\d+\s*(?:cards?|flashcards?)", m, flags=re.IGNORECASE)[0]
        for tok in _content_tokens(segment):
            if tok not in GENERIC_WORDS:
                terms.add(tok)
    return terms


def _specific_terms(text: str) -> set[str]:
    """
    Conservative factual-term extraction for grounding.
    """
    found = set()

    # formulas
    for m in re.findall(r"\b[A-Za-zρΔ][A-Za-z0-9_]*\s*=\s*[^.;,\n]+", text or ""):
        found.add(_norm(m))

    # numbers / values
    for m in re.findall(r"\b\d+(?:\.\d+)?\b", text or ""):
        found.add(_norm(m))

    # Greek/symbol tokens
    for m in re.findall(r"[ρΔθΩμ][A-Za-z0-9_/*+^²³·=-]*", text or ""):
        found.add(_norm(m))

    # multi-word capitalized terms
    for m in re.findall(r"\b[A-Z][a-z]+(?:'s)?(?:\s+[A-Z][a-z]+(?:'s)?)+\b", text or ""):
        found.add(_norm(m))

    # content tokens
    for tok in _content_tokens(text or ""):
        if tok not in GENERIC_WORDS and len(tok) > 3:
            found.add(tok)

    return found


def _detect_source_markers(context: str) -> set[str]:
    markers = set()
    for p in [
        r"\[source[:\s]+([^\]]+)\]",
        r"\bsource\s*(\d+)\b",
        r"\bfile[:\s]+([A-Za-z0-9_.-]+\.pdf)\b",
        r"\bsource_pdf[:\s]+([A-Za-z0-9_.-]+\.pdf)\b",
    ]:
        for m in re.findall(p, context or "", flags=re.IGNORECASE):
            markers.add(_norm(m))
    return markers


def _list_from_mapping(mapping: Optional[dict], key: str) -> list[str]:
    if not isinstance(mapping, dict):
        return []
    val = mapping.get(key)
    if isinstance(val, list):
        return [str(x) for x in val if str(x).strip()]
    return []


def _card_text(card: dict) -> str:
    return f"{card.get('front', '')} {card.get('back', '')}"


def parse_model_response_to_outputs(raw_text: str) -> dict:
    """
    Defensive parser for raw model text.
    Returns {"flashcards_json": parsed} when possible.
    """
    if not isinstance(raw_text, str) or not raw_text.strip():
        return {}

    raw = raw_text.strip()
    if "```" in raw:
        fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, re.DOTALL)
        if fence:
            raw = fence.group(1).strip()
        else:
            return {}

    try:
        parsed = json.loads(raw)
        if isinstance(parsed, dict):
            return {"flashcards_json": parsed}
    except Exception:
        m = re.search(r"\{.*\}", raw, re.DOTALL)
        if m:
            try:
                parsed = json.loads(m.group(0))
                if isinstance(parsed, dict):
                    return {"flashcards_json": parsed}
            except Exception:
                pass

    return {}


# ---------------------------------------------------------------------------
# Evaluator 1: schema_validity
# ---------------------------------------------------------------------------

def schema_validity(run, example) -> dict:
    out = _safe_get_outputs(run)
    if out is None:
        return {
            "key": "schema_validity",
            "score": 0.0,
            "comment": "outputs missing or not a JSON object",
        }

    present = set(out.keys())
    missing = REQUIRED_KEYS - present
    extra = present - ALLOWED_KEYS
    if missing or extra:
        return {
            "key": "schema_validity",
            "score": 0.0,
            "comment": f"key set mismatch -- missing={sorted(missing)} extra={sorted(extra)}",
        }

    ok, deck, raw = _parse_deck(out.get("flashcards_json"))
    if not ok:
        return {
            "key": "schema_validity",
            "score": 0.0,
            "comment": f"flashcards_json is not a valid clean JSON object; sample={raw[:120]!r}",
        }

    deck_keys = set(deck.keys())
    missing_deck = DECK_REQUIRED_KEYS - deck_keys
    if missing_deck:
        return {
            "key": "schema_validity",
            "score": 0.0,
            "comment": f"deck missing required key(s): {sorted(missing_deck)}",
        }

    if not isinstance(deck.get("title"), str) or not deck["title"].strip():
        return {
            "key": "schema_validity",
            "score": 0.0,
            "comment": "deck.title must be a non-empty string",
        }

    cards = deck.get("cards")
    if not isinstance(cards, list):
        return {
            "key": "schema_validity",
            "score": 0.0,
            "comment": "deck.cards must be a list",
        }

    for idx, card in enumerate(cards):
        if not isinstance(card, dict):
            return {
                "key": "schema_validity",
                "score": 0.0,
                "comment": f"card {idx} is not an object",
            }

        missing_card = CARD_REQUIRED_KEYS - set(card.keys())
        if missing_card:
            return {
                "key": "schema_validity",
                "score": 0.0,
                "comment": f"card {idx} missing key(s): {sorted(missing_card)}",
            }

        for field in CARD_REQUIRED_KEYS:
            if not isinstance(card.get(field), str) or not card[field].strip():
                return {
                    "key": "schema_validity",
                    "score": 0.0,
                    "comment": f"card {idx}.{field} must be a non-empty string",
                }

        for optional in ("type", "source_hint"):
            if optional in card and not isinstance(card[optional], str):
                return {
                    "key": "schema_validity",
                    "score": 0.0,
                    "comment": f"card {idx}.{optional} must be a string when present",
                }

    return {
        "key": "schema_validity",
        "score": 1.0,
        "comment": "schema valid",
    }


# ---------------------------------------------------------------------------
# Evaluator 2: card_count_match
# ---------------------------------------------------------------------------

def card_count_match(run, example) -> dict:
    out = _safe_get_outputs(run)
    ref = _safe_get_reference(example)
    inputs = _safe_get_inputs(example)
    variation = _safe_get_variation(example)

    deck = _get_deck(out)
    if deck is None:
        return {
            "key": "card_count_match",
            "score": 0.0,
            "comment": "flashcards_json missing/malformed",
            "hard_rule_violated": False,
        }

    cards = _cards(deck)
    context = str(inputs.get("context", ""))
    custom = str(inputs.get("custom_instructions", ""))
    requested = _extract_requested_count(custom)
    gold_deck = _get_gold_deck(ref)
    gold_count = len(_cards(gold_deck)) if gold_deck else None

    if variation in NO_SOURCE_VARIATIONS or _is_empty_context(context):
        if len(cards) == 0:
            return {
                "key": "card_count_match",
                "score": 1.0,
                "comment": "no-source case safely returned zero cards",
                "hard_rule_violated": False,
            }
        return {
            "key": "card_count_match",
            "score": 0.0,
            "comment": f"no-source/empty-context case produced {len(cards)} card(s)",
            "hard_rule_violated": True,
        }

    expected = requested if requested is not None else gold_count
    if expected is not None:
        if len(cards) == expected:
            return {
                "key": "card_count_match",
                "score": 1.0,
                "comment": f"card count matched expected={expected}",
                "hard_rule_violated": False,
            }
        return {
            "key": "card_count_match",
            "score": 0.0,
            "comment": f"card count mismatch: expected={expected}, got={len(cards)}",
            "hard_rule_violated": True,
        }

    if DEFAULT_MIN_CARDS <= len(cards) <= DEFAULT_MAX_CARDS:
        return {
            "key": "card_count_match",
            "score": 1.0,
            "comment": f"default card count acceptable: {len(cards)}",
            "hard_rule_violated": False,
        }

    return {
        "key": "card_count_match",
        "score": 0.5,
        "comment": f"card count outside default {DEFAULT_MIN_CARDS}-{DEFAULT_MAX_CARDS} range: {len(cards)}",
        "hard_rule_violated": False,
    }


# ---------------------------------------------------------------------------
# Evaluator 3: flashcard_design_quality
# ---------------------------------------------------------------------------

def flashcard_design_quality(run, example) -> dict:
    """
    Checks card usability:
    - concise front and back
    - front does not reveal the answer
    - no placeholders
    - one idea per card heuristic
    - no duplicate/near-duplicate cards
    """
    out = _safe_get_outputs(run)
    inputs = _safe_get_inputs(example)
    variation = _safe_get_variation(example)

    deck = _get_deck(out)
    if deck is None:
        return {
            "key": "flashcard_design_quality",
            "score": 0.0,
            "comment": "flashcards_json missing/malformed",
            "hard_rule_violated": False,
        }

    cards = _cards(deck)
    context = str(inputs.get("context", ""))

    if variation in NO_SOURCE_VARIATIONS or _is_empty_context(context):
        return {
            "key": "flashcard_design_quality",
            "score": 1.0 if len(cards) == 0 else 0.0,
            "comment": "no-source case",
            "hard_rule_violated": bool(len(cards) != 0),
        }

    issues = []

    for idx, card in enumerate(cards):
        front = str(card.get("front", ""))
        back = str(card.get("back", ""))

        if _contains_any(front + " " + back, BANNED_PATTERNS):
            issues.append(f"card_{idx}_banned_pattern")

        if _norm(front) in PLACEHOLDER_PATTERNS or _norm(back) in PLACEHOLDER_PATTERNS:
            issues.append(f"card_{idx}_placeholder_text")

        front_wc = _word_count(front)
        back_wc = _word_count(back)

        if front_wc > MAX_FRONT_WORDS:
            issues.append(f"card_{idx}_front_too_long_{front_wc}_words")

        if back_wc > MAX_BACK_WORDS:
            issues.append(f"card_{idx}_back_too_long_{back_wc}_words")

        if back_wc < MIN_BACK_WORDS:
            # Very short backs can be valid for formula/value/location cards, e.g. "(a,0)", "e=1", "x-axis".
            if not re.search(r"\d|=|[()ρΔθΩμ-]|axis|law|rule", back, flags=re.IGNORECASE):
                issues.append(f"card_{idx}_back_too_short_{back_wc}_words")

        # Front should not contain most of the answer.
        if _jaccard(front, back) > 0.65 and back_wc >= 4:
            issues.append(f"card_{idx}_front_leaks_back")

        # Avoid multi-question front.
        if front.count("?") > 1:
            issues.append(f"card_{idx}_front_has_multiple_questions")

        # One idea per card heuristic: avoid very long backs with multiple clauses.
        if back.count(";") + back.count(".") >= 4 and back_wc > 35:
            issues.append(f"card_{idx}_back_may_contain_multiple_ideas")

    # Duplicate card check.
    texts = [_card_text(c) for c in cards if isinstance(c, dict)]
    duplicate_pairs = []
    for i in range(len(texts)):
        for j in range(i + 1, len(texts)):
            if _jaccard(texts[i], texts[j]) >= 0.80:
                duplicate_pairs.append((i, j))

    if duplicate_pairs:
        issues.append(f"near_duplicate_cards:{duplicate_pairs[:5]}")

    if issues:
        hard = any(
            "placeholder" in x
            or "front_leaks_back" in x
            or "near_duplicate" in x
            or "banned_pattern" in x
            for x in issues
        )
        return {
            "key": "flashcard_design_quality",
            "score": 0.0 if hard else 0.5,
            "comment": "; ".join(issues[:10]),
            "hard_rule_violated": hard,
        }

    return {
        "key": "flashcard_design_quality",
        "score": 1.0,
        "comment": "flashcard design checks passed",
        "hard_rule_violated": False,
    }


# ---------------------------------------------------------------------------
# Evaluator 4: custom_instruction_compliance
# ---------------------------------------------------------------------------

def custom_instruction_compliance(run, example) -> dict:
    """
    Checks only concrete custom instructions:
    - requested count
    - focus terms
    - formula/definition/concept style
    - language cue
    """
    out = _safe_get_outputs(run)
    inputs = _safe_get_inputs(example)

    deck = _get_deck(out)
    if deck is None:
        return {
            "key": "custom_instruction_compliance",
            "score": 0.0,
            "comment": "flashcards_json missing/malformed",
        }

    cards = _cards(deck)
    custom = str(inputs.get("custom_instructions", ""))
    deck_text = _flatten_deck_text(deck)
    custom_norm = _norm(custom)
    issues = []

    requested_count = _extract_requested_count(custom)
    if requested_count is not None and len(cards) != requested_count:
        issues.append(f"requested_count_{requested_count}_got_{len(cards)}")

    focus_terms = _extract_focus_terms(custom)
    if focus_terms:
        missing_focus = [t for t in focus_terms if t not in _tokens(deck_text)]
        if len(missing_focus) >= max(1, len(focus_terms) // 2 + 1):
            issues.append(f"focus_terms_not_reflected:{missing_focus[:5]}")

    # Style cues
    if any(h in custom_norm for h in FORMULA_HINTS):
        # At least some backs/fronts should contain formula-like or symbolic content.
        if not re.search(r"=|[ρΔθΩμ]|[A-Za-z]\^?\d+|\d+/\d+", deck_text):
            issues.append("formula_cards_requested_but_no_formula_like_content")

    if any(h in custom_norm for h in DEFINITION_HINTS):
        # Definition decks usually front asks term/meaning and back defines.
        if not any(
            _contains_any(c.get("front", ""), {"what is", "define", "meaning", "term"})
            or _contains_any(c.get("back", ""), {"is", "refers to", "means"})
            for c in cards
            if isinstance(c, dict)
        ):
            issues.append("definition_style_requested_but_not_detected")

    if re.search(r"\bin\s+hindi\b|हिंदी|हिन्दी", custom, flags=re.IGNORECASE):
        if not re.search(r"[\u0900-\u097F]", deck_text):
            issues.append("hindi_requested_but_no_devanagari_detected")

    if issues:
        hard = any(x.startswith(("requested_count", "focus_terms", "hindi_requested")) for x in issues)
        return {
            "key": "custom_instruction_compliance",
            "score": 0.0 if hard else 0.5,
            "comment": "; ".join(issues),
        }

    return {
        "key": "custom_instruction_compliance",
        "score": 1.0,
        "comment": "custom instruction checks passed",
    }


# ---------------------------------------------------------------------------
# Evaluator 5: grounding
# ---------------------------------------------------------------------------

def grounding(run, example) -> dict:
    """
    Cards must be grounded in the provided context or gold deck.
    """
    out = _safe_get_outputs(run)
    ref = _safe_get_reference(example)
    inputs = _safe_get_inputs(example)
    variation = _safe_get_variation(example)

    deck = _get_deck(out)
    if deck is None:
        return {
            "key": "grounding",
            "score": 0.0,
            "comment": "flashcards_json missing/malformed",
            "hard_rule_violated": False,
        }

    context = str(inputs.get("context", ""))
    cards = _cards(deck)

    if variation in NO_SOURCE_VARIATIONS or _is_empty_context(context):
        return {
            "key": "grounding",
            "score": 1.0 if len(cards) == 0 else 0.0,
            "comment": "no-source grounding case",
            "hard_rule_violated": bool(len(cards) != 0),
        }

    gold_deck = _get_gold_deck(ref)
    deck_text = _flatten_deck_text(deck)
    gold_text = _flatten_deck_text(gold_deck)

    allowed_terms = (
        _specific_terms(context)
        | _specific_terms(gold_text)
        | _specific_terms(str(inputs.get("custom_instructions", "")))
    )
    output_terms = _specific_terms(deck_text)

    unsupported = sorted([
        t for t in output_terms
        if t not in allowed_terms
        and t not in GENERIC_WORDS
        and not any(t in a or a in t for a in allowed_terms if len(a) >= 4)
    ])

    numeric_or_formula_bad = [t for t in unsupported if re.search(r"\d|=|[ρΔθΩμ]", t)]
    if numeric_or_formula_bad:
        return {
            "key": "grounding",
            "score": 0.0,
            "comment": f"unsupported numeric/formula/symbol content: {numeric_or_formula_bad[:5]}",
            "hard_rule_violated": True,
        }

    if len(unsupported) >= 8:
        return {
            "key": "grounding",
            "score": 0.0,
            "comment": f"many unsupported terms/facts: {unsupported[:10]}",
            "hard_rule_violated": True,
        }

    overlap_context = _jaccard(deck_text, context)
    overlap_gold = _jaccard(deck_text, gold_text) if gold_text else 0.0

    if overlap_context >= 0.16 or overlap_gold >= 0.24:
        return {
            "key": "grounding",
            "score": 1.0,
            "comment": f"grounded; context_overlap={overlap_context:.2f} gold_overlap={overlap_gold:.2f}",
            "hard_rule_violated": False,
        }

    if unsupported:
        return {
            "key": "grounding",
            "score": 0.5,
            "comment": f"possible unsupported terms: {unsupported[:6]}",
            "hard_rule_violated": False,
        }

    return {
        "key": "grounding",
        "score": 1.0,
        "comment": f"grounding acceptable; context_overlap={overlap_context:.2f} gold_overlap={overlap_gold:.2f}",
        "hard_rule_violated": False,
    }


# ---------------------------------------------------------------------------
# Evaluator 6: coverage_and_source_balance
# ---------------------------------------------------------------------------

def coverage_and_source_balance(run, example) -> dict:
    """
    Ensures deck is not repetitive and, for multi-source contexts, is not one-source heavy.
    """
    out = _safe_get_outputs(run)
    inputs = _safe_get_inputs(example)
    variation = _safe_get_variation(example)

    deck = _get_deck(out)
    if deck is None:
        return {
            "key": "coverage_and_source_balance",
            "score": 0.0,
            "comment": "flashcards_json missing/malformed",
        }

    cards = _cards(deck)
    context = str(inputs.get("context", ""))

    if variation in NO_SOURCE_VARIATIONS or _is_empty_context(context):
        return {
            "key": "coverage_and_source_balance",
            "score": 1.0 if len(cards) == 0 else 0.0,
            "comment": "no-source case",
        }

    if len(cards) <= 2:
        return {
            "key": "coverage_and_source_balance",
            "score": 1.0,
            "comment": "small deck; coverage balance minimally applicable",
        }

    # Avoid all cards being about the same phrase.
    fronts = [str(c.get("front", "")) for c in cards if isinstance(c, dict)]
    repeated_pairs = []
    for i in range(len(fronts)):
        for j in range(i + 1, len(fronts)):
            if _jaccard(fronts[i], fronts[j]) >= 0.75:
                repeated_pairs.append((i, j))

    if repeated_pairs:
        return {
            "key": "coverage_and_source_balance",
            "score": 0.0,
            "comment": f"near-duplicate card fronts detected: {repeated_pairs[:5]}",
        }

    if variation in MULTI_SOURCE_VARIATIONS:
        source_markers = _detect_source_markers(context)
        if len(source_markers) >= 2:
            chunks = re.split(
                r"\[source[:\s]+[^\]]+\]|\bsource\s*\d+\b|\bfile[:\s]+[A-Za-z0-9_.-]+\.pdf",
                context,
                flags=re.IGNORECASE,
            )
            covered = 0
            deck_text = _flatten_deck_text(deck)
            for ch in chunks:
                if _word_count(ch) >= 5 and _jaccard(deck_text, ch) >= 0.08:
                    covered += 1
            if covered < 2:
                return {
                    "key": "coverage_and_source_balance",
                    "score": 0.5,
                    "comment": "multi-source context detected but deck appears concentrated in one source",
                }

    return {
        "key": "coverage_and_source_balance",
        "score": 1.0,
        "comment": "coverage/source balance checks passed",
    }


# ---------------------------------------------------------------------------
# Summary evaluator
# ---------------------------------------------------------------------------

def studio_flashcards_severity_summary(runs: list, examples: list) -> dict:
    """
    BLOCK:
    - invalid schema
    - wrong card count when requested/gold count exists
    - no-source fabrication
    - placeholder cards
    - front leaks answer
    - duplicate cards
    - unsupported numeric/formula facts

    REVIEW:
    - verbosity/usability issues
    - weak custom compliance
    - possible grounding weakness
    - source balance weakness
    """
    if len(runs) != len(examples):
        return {
            "key": "studio_flashcards_severity_summary",
            "score": 0.0,
            "comment": f"runs/examples length mismatch ({len(runs)} vs {len(examples)})",
            "ship_recommendation": "BLOCK",
        }

    tier_0 = []
    tier_1 = 0
    tier_1_applicable = 0
    variation_totals: dict[str, int] = {}
    variation_passes: dict[str, int] = {}

    for run, example in zip(runs, examples):
        variation = _safe_get_variation(example)
        variation_totals[variation] = variation_totals.get(variation, 0) + 1

        schema = schema_validity(run, example)
        if schema["score"] == 0.0:
            tier_0.append({
                "example_id": getattr(example, "id", None),
                "reason": f"schema_validity failed: {schema['comment']}",
            })
            continue

        count = card_count_match(run, example)
        design = flashcard_design_quality(run, example)
        custom = custom_instruction_compliance(run, example)
        ground = grounding(run, example)
        coverage = coverage_and_source_balance(run, example)

        for result in (count, design, ground):
            if result.get("hard_rule_violated"):
                tier_0.append({
                    "example_id": getattr(example, "id", None),
                    "reason": f"{result['key']} hard failure: {result['comment']}",
                })

        if custom["score"] == 0.0 and any(x in custom["comment"] for x in ["requested_count", "focus_terms", "hindi_requested"]):
            tier_0.append({
                "example_id": getattr(example, "id", None),
                "reason": f"custom instruction hard failure: {custom['comment']}",
            })

        tier_1_applicable += 5
        if count["score"] < 1.0:
            tier_1 += 1
        if design["score"] < 1.0:
            tier_1 += 1
        if custom["score"] < 1.0:
            tier_1 += 1
        if ground["score"] < 1.0:
            tier_1 += 1
        if coverage["score"] < 1.0:
            tier_1 += 1

        if (
            count["score"] == 1.0
            and design["score"] == 1.0
            and custom["score"] == 1.0
            and ground["score"] == 1.0
            and coverage["score"] == 1.0
        ):
            variation_passes[variation] = variation_passes.get(variation, 0) + 1

    tier_1_rate = (tier_1 / tier_1_applicable) if tier_1_applicable else 0.0

    per_variation_pass_rate = {
        v: round(variation_passes.get(v, 0) / total, 3)
        for v, total in variation_totals.items()
    }

    if tier_0:
        recommendation = "BLOCK"
    elif tier_1_rate > 0.18:
        recommendation = "REVIEW"
    else:
        recommendation = "OK"

    return {
        "key": "studio_flashcards_severity_summary",
        "score": 0.0 if tier_0 else round(1.0 - tier_1_rate, 3),
        "comment": (
            f"ship_recommendation={recommendation} | "
            f"tier_0_blocking_count={len(tier_0)} | "
            f"tier_1_review_rate={tier_1_rate:.3f}"
        ),
        "tier_0_blocking_count": len(tier_0),
        "tier_0_blocking_examples": tier_0,
        "tier_1_review_rate": round(tier_1_rate, 3),
        "per_variation_pass_rate": per_variation_pass_rate,
        "ship_recommendation": recommendation,
    }


# ---------------------------------------------------------------------------
# Public registries
# ---------------------------------------------------------------------------

PER_EXAMPLE_EVALUATORS = [
    schema_validity,
    card_count_match,
    flashcard_design_quality,
    custom_instruction_compliance,
    grounding,
    coverage_and_source_balance,
]

SUMMARY_EVALUATORS = [
    studio_flashcards_severity_summary,
]
