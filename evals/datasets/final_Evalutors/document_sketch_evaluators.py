"""
document_sketch_evaluators.py

LangSmith custom evaluators for Agent 26: Document Sketch.

Agent role:
- Optional upload-ingestion helper.
- Produces a compact whole-document sketch from uploaded document text.
- The sketch helps Agent 28 Chunk Contextualization add document-level context
  to each indexed chunk when contextual retrieval is enabled.

Production dependencies:
- Inputs:
    header: str
    document_text: str
- Output:
    sketch_json: dict

Recommended sketch_json contract used by this evaluator:
    {
      "title": str,                  # short title inferred from header/text
      "document_type": str,          # notes | exam_paper | worksheet | textbook_excerpt | unknown
      "summary": str,                # compact grounded document summary
      "key_topics": list[str],       # 3-8 grounded topics
      "keywords": list[str],         # 5-15 retrieval-friendly terms
      "structure_notes": str         # compact notes about sections / question patterns / organization
    }

Why this contract is intentionally modest:
- Agent 26 is Tier 3 and optional.
- It should not become a second summarizer or a student-facing answer.
- The output only needs enough high-signal metadata for Agent 28 contextualization.

Dependency note:
- Agent 26 is bypassed when doc-sketch flags are off.
- It is independent at call time, but downstream Agent 28 may consume its sketch.
- It must not depend on Agent 25 question extraction, because Agent 25 is a
  separate upload parsing API.

Evaluator design:
- Code-first, not LLM/hybrid.
- Criticality: Tier 3 optional ingestion.
- Main risks are deterministic enough:
  malformed JSON, bloated summary, unsupported/invented terms, generic sketch,
  poor retrieval utility, answer-key/footer leakage, and unsafe use of thin text.
- No required LLM judge. If you later see frequent semantic misses in production,
  add a small optional judge, but do not start there.

LangSmith usage:
    from document_sketch_evaluators import (
        PER_EXAMPLE_EVALUATORS,
        SUMMARY_EVALUATORS,
    )

    client.evaluate(
        target_fn,
        data="nbm-prompt-document_sketch",
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

REQUIRED_INPUT_KEYS = {"header", "document_text"}
REQUIRED_OUTPUT_KEYS = {"sketch_json"}

CORE_SKETCH_KEYS = {
    "title",
    "document_type",
    "summary",
    "key_topics",
    "keywords",
    "structure_notes",
}

VALID_DOCUMENT_TYPES = {
    "notes",
    "exam_paper",
    "worksheet",
    "textbook_excerpt",
    "question_paper",
    "solution_key",
    "mixed",
    "unknown",
}

SUMMARY_MIN_WORDS = 25
SUMMARY_MAX_WORDS = 140

KEY_TOPICS_MIN = 2
KEY_TOPICS_MAX = 10

KEYWORDS_MIN = 4
KEYWORDS_MAX = 18

TITLE_MAX_WORDS = 16
STRUCTURE_NOTES_MAX_WORDS = 80

BANNED_PATTERNS = {
    "as an ai language model",
    "i cannot access",
    "i don't have access",
    "not enough context",
    "placeholder",
    "todo",
    "lorem ipsum",
    "sketch_json",
    "valid json",
    "system prompt",
    ".j2",
    "jinja",
}

FOOTER_NOISE = {
    "downloaded from",
    "printed by",
    "copyright",
    "all rights reserved",
    "page footer",
    "turn over",
    "scanned by",
    "www.",
    "http://",
    "https://",
}

ANSWER_KEY_NOISE = {
    "answer key",
    "marking scheme",
    "solutions:",
    "correct option",
}

GENERIC_TOPICS = {
    "chapter",
    "document",
    "study material",
    "important topics",
    "questions",
    "answers",
    "notes",
    "summary",
    "concepts",
    "key points",
}

GENERIC_WORDS = {
    "the", "and", "with", "from", "this", "that", "document", "chapter",
    "notes", "question", "questions", "answer", "answers", "summary",
    "topic", "topics", "concept", "concepts", "important", "student",
    "students", "study", "material", "section", "page", "class",
    "source", "text", "contains", "covers", "includes",
}

QUESTION_CUES = {
    "q.", "question", "section a", "section b", "mcq", "assertion", "reason",
    "case study", "marks", "choose the correct", "(a)", "(b)", "(c)", "(d)",
}

NOTES_CUES = {
    "definition", "example", "formula", "theorem", "concept", "explain",
    "notes", "key points", "summary",
}

TEXTBOOK_CUES = {
    "chapter", "exercise", "figure", "table", "activity", "example",
    "introduction", "summary",
}


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


def _word_count(text: str) -> int:
    return len(re.findall(r"\S+", text or ""))


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-zA-Z0-9ΩμρΔθ°/+=∩∪^²³().-]+", _norm(text)))


def _content_tokens(text: str) -> set[str]:
    stop = {
        "the", "a", "an", "and", "or", "to", "of", "in", "on", "for", "with",
        "is", "are", "was", "were", "be", "been", "being", "this", "that",
        "it", "as", "by", "from", "document", "chapter", "source", "text",
        "contains", "covers", "includes", "summary",
    }
    return {t for t in _tokens(text) if len(t) > 2 and t not in stop}


def _specific_terms(text: str) -> set[str]:
    found = set()

    for tok in _content_tokens(text or ""):
        if tok not in GENERIC_WORDS and len(tok) > 3:
            found.add(tok)

    for m in re.findall(r"\b[A-Za-zρΔ][A-Za-z0-9_]*\s*=\s*[^.;,\n]+", text or ""):
        found.add(_norm(m))

    for m in re.findall(r"\b[A-Z][a-z]+(?:'s)?(?:\s+[A-Z][a-z]+(?:'s)?)+\b", text or ""):
        found.add(_norm(m))

    for m in re.findall(r"[ρΔθΩμ][A-Za-z0-9_/*+^²³·=-]*", text or ""):
        found.add(_norm(m))

    return found


def _jaccard(a: str, b: str) -> float:
    ta, tb = _content_tokens(a), _content_tokens(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def _contains_any(text: str, needles) -> bool:
    t = _norm(text)
    return any(_norm(n) in t for n in needles)


def _parse_sketch(value: Any) -> tuple[bool, Optional[dict], str]:
    if isinstance(value, dict):
        return True, value, json.dumps(value, ensure_ascii=False)

    if not isinstance(value, str):
        return False, None, str(value)

    raw = value.strip()
    if not raw or "```" in raw:
        return False, None, raw

    try:
        parsed = json.loads(raw)
    except Exception:
        return False, None, raw

    return (True, parsed, raw) if isinstance(parsed, dict) else (False, None, raw)


def _get_sketch(out: Optional[dict]) -> Optional[dict]:
    if not isinstance(out, dict):
        return None
    ok, parsed, _ = _parse_sketch(out.get("sketch_json"))
    return parsed if ok else None


def _get_gold_sketch(ref: Optional[dict]) -> Optional[dict]:
    if not isinstance(ref, dict):
        return None
    ok, parsed, _ = _parse_sketch(ref.get("sketch_json"))
    return parsed if ok else None


def _flatten_sketch_text(sketch: Optional[dict]) -> str:
    if not isinstance(sketch, dict):
        return ""
    try:
        return json.dumps(sketch, ensure_ascii=False)
    except Exception:
        return str(sketch)


def _list_of_strings(value: Any) -> bool:
    return isinstance(value, list) and all(isinstance(x, str) and x.strip() for x in value)


def _doc_type_from_text(header: str, document_text: str) -> str:
    text = _norm(header + " " + document_text)

    question_score = sum(1 for cue in QUESTION_CUES if cue in text)
    notes_score = sum(1 for cue in NOTES_CUES if cue in text)
    textbook_score = sum(1 for cue in TEXTBOOK_CUES if cue in text)

    if _contains_any(text, ANSWER_KEY_NOISE):
        return "solution_key"

    if question_score >= 3:
        return "question_paper"

    if notes_score >= 2 and question_score < 2:
        return "notes"

    if textbook_score >= 3:
        return "textbook_excerpt"

    if question_score and notes_score:
        return "mixed"

    return "unknown"


def _json_from_text(text: str) -> Optional[dict]:
    if not isinstance(text, str):
        return None
    raw = text.strip()
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, re.DOTALL)
    if fence:
        raw = fence.group(1)
    else:
        obj = re.search(r"\{.*\}", raw, re.DOTALL)
        if obj:
            raw = obj.group(0)
    try:
        parsed = json.loads(raw)
    except Exception:
        return None
    return parsed if isinstance(parsed, dict) else None


def parse_model_response_to_outputs(raw_text: str) -> dict:
    """
    Defensive parser for raw model response.
    Accepts either:
    - {"sketch_json": {...}}
    - {...} as the sketch object itself
    """
    if not isinstance(raw_text, str) or not raw_text.strip():
        return {}

    parsed = _json_from_text(raw_text)
    if not isinstance(parsed, dict):
        return {}

    if "sketch_json" in parsed:
        ok, sketch, _ = _parse_sketch(parsed["sketch_json"])
        return {"sketch_json": sketch if ok else parsed["sketch_json"]}

    return {"sketch_json": parsed}


# ---------------------------------------------------------------------------
# Evaluator 1: schema_validity
# ---------------------------------------------------------------------------

def schema_validity(run, example) -> dict:
    inputs = _safe_get_inputs(example)
    missing_inputs = REQUIRED_INPUT_KEYS - set(inputs.keys())
    if missing_inputs:
        return {
            "key": "schema_validity",
            "score": 0.0,
            "comment": f"missing input key(s): {sorted(missing_inputs)}",
        }

    out = _safe_get_outputs(run)
    if out is None:
        return {
            "key": "schema_validity",
            "score": 0.0,
            "comment": "outputs missing or not JSON object",
        }

    present = set(out.keys())
    if present != REQUIRED_OUTPUT_KEYS:
        return {
            "key": "schema_validity",
            "score": 0.0,
            "comment": f"output key mismatch -- missing={sorted(REQUIRED_OUTPUT_KEYS-present)} extra={sorted(present-REQUIRED_OUTPUT_KEYS)}",
        }

    ok, sketch, raw = _parse_sketch(out.get("sketch_json"))
    if not ok:
        return {
            "key": "schema_validity",
            "score": 0.0,
            "comment": f"sketch_json is not a clean JSON object; sample={raw[:120]!r}",
        }

    missing = CORE_SKETCH_KEYS - set(sketch.keys())
    if missing:
        return {
            "key": "schema_validity",
            "score": 0.0,
            "comment": f"sketch_json missing core key(s): {sorted(missing)}",
        }

    if not isinstance(sketch.get("title"), str) or not sketch["title"].strip():
        return {"key": "schema_validity", "score": 0.0, "comment": "title must be non-empty string"}
    if _word_count(sketch["title"]) > TITLE_MAX_WORDS:
        return {"key": "schema_validity", "score": 0.5, "comment": f"title too long: {_word_count(sketch['title'])} words"}

    if sketch.get("document_type") not in VALID_DOCUMENT_TYPES:
        return {
            "key": "schema_validity",
            "score": 0.0,
            "comment": f"invalid document_type={sketch.get('document_type')!r}",
        }

    summary = sketch.get("summary")
    if not isinstance(summary, str) or not summary.strip():
        return {"key": "schema_validity", "score": 0.0, "comment": "summary must be non-empty string"}

    summary_words = _word_count(summary)
    if summary_words < SUMMARY_MIN_WORDS or summary_words > SUMMARY_MAX_WORDS:
        return {
            "key": "schema_validity",
            "score": 0.5,
            "comment": f"summary length outside preferred band: {summary_words} words",
        }

    if not _list_of_strings(sketch.get("key_topics")):
        return {"key": "schema_validity", "score": 0.0, "comment": "key_topics must be non-empty list of strings"}

    if not (KEY_TOPICS_MIN <= len(sketch["key_topics"]) <= KEY_TOPICS_MAX):
        return {
            "key": "schema_validity",
            "score": 0.5,
            "comment": f"key_topics count outside preferred range: {len(sketch['key_topics'])}",
        }

    if not _list_of_strings(sketch.get("keywords")):
        return {"key": "schema_validity", "score": 0.0, "comment": "keywords must be non-empty list of strings"}

    if not (KEYWORDS_MIN <= len(sketch["keywords"]) <= KEYWORDS_MAX):
        return {
            "key": "schema_validity",
            "score": 0.5,
            "comment": f"keywords count outside preferred range: {len(sketch['keywords'])}",
        }

    structure_notes = sketch.get("structure_notes")
    if not isinstance(structure_notes, str) or not structure_notes.strip():
        return {"key": "schema_validity", "score": 0.0, "comment": "structure_notes must be non-empty string"}

    if _word_count(structure_notes) > STRUCTURE_NOTES_MAX_WORDS:
        return {
            "key": "schema_validity",
            "score": 0.5,
            "comment": f"structure_notes too long: {_word_count(structure_notes)} words",
        }

    text = _flatten_sketch_text(sketch)
    if _contains_any(text, BANNED_PATTERNS):
        return {"key": "schema_validity", "score": 0.0, "comment": "sketch_json contains banned/internal phrase"}

    return {"key": "schema_validity", "score": 1.0, "comment": "schema valid"}


# ---------------------------------------------------------------------------
# Evaluator 2: grounded_sketch
# ---------------------------------------------------------------------------

def grounded_sketch(run, example) -> dict:
    sketch = _get_sketch(_safe_get_outputs(run))
    inputs = _safe_get_inputs(example)
    gold = _get_gold_sketch(_safe_get_reference(example))

    if sketch is None:
        return {
            "key": "grounded_sketch",
            "score": 0.0,
            "comment": "sketch_json missing/malformed",
            "hard_rule_violated": False,
        }

    header = str(inputs.get("header", ""))
    doc = str(inputs.get("document_text", ""))
    gold_text = _flatten_sketch_text(gold)
    allowed = " ".join([header, doc, gold_text])
    sketch_text = _flatten_sketch_text(sketch)

    issues = []
    hard = False

    overlap = max(_jaccard(sketch_text, allowed), _jaccard(str(sketch.get("summary", "")), allowed))

    if _word_count(doc) >= 20 and overlap < 0.08:
        issues.append(f"weak_source_overlap={overlap:.2f}")
        hard = True

    allowed_terms = _specific_terms(allowed)
    produced_terms = _specific_terms(sketch_text)

    unsupported = sorted([
        t for t in produced_terms
        if t not in allowed_terms
        and not any(t in a or a in t for a in allowed_terms if len(a) >= 4)
        and t not in GENERIC_WORDS
    ])

    numeric_or_formula_bad = [t for t in unsupported if re.search(r"\d|=|[ρΔθΩμ]", t)]
    if numeric_or_formula_bad:
        issues.append(f"unsupported_numeric_or_formula_terms:{numeric_or_formula_bad[:5]}")
        hard = True

    if len(unsupported) >= 8:
        issues.append(f"many_unsupported_terms:{unsupported[:8]}")
        hard = True
    elif unsupported:
        issues.append(f"possible_unsupported_terms:{unsupported[:6]}")

    if hard:
        return {
            "key": "grounded_sketch",
            "score": 0.0,
            "comment": "; ".join(issues[:10]),
            "hard_rule_violated": True,
        }

    if issues:
        return {
            "key": "grounded_sketch",
            "score": 0.5,
            "comment": "; ".join(issues[:10]),
            "hard_rule_violated": False,
        }

    return {
        "key": "grounded_sketch",
        "score": 1.0,
        "comment": f"sketch grounded; overlap={overlap:.2f}",
        "hard_rule_violated": False,
    }


# ---------------------------------------------------------------------------
# Evaluator 3: retrieval_utility
# ---------------------------------------------------------------------------

def retrieval_utility(run, example) -> dict:
    sketch = _get_sketch(_safe_get_outputs(run))
    inputs = _safe_get_inputs(example)

    if sketch is None:
        return {
            "key": "retrieval_utility",
            "score": 0.0,
            "comment": "sketch_json missing/malformed",
            "hard_rule_violated": False,
        }

    doc = str(inputs.get("document_text", ""))
    header = str(inputs.get("header", ""))
    keywords = sketch.get("keywords", [])
    topics = sketch.get("key_topics", [])
    summary = str(sketch.get("summary", ""))
    structure_notes = str(sketch.get("structure_notes", ""))

    issues = []
    hard = False

    if not keywords or not topics:
        return {
            "key": "retrieval_utility",
            "score": 0.0,
            "comment": "keywords/key_topics missing",
            "hard_rule_violated": True,
        }

    generic_keywords = [kw for kw in keywords if _norm(kw) in GENERIC_TOPICS or _norm(kw) in GENERIC_WORDS]
    if len(generic_keywords) >= max(2, len(keywords) // 2):
        issues.append(f"too_many_generic_keywords:{generic_keywords[:6]}")
        hard = True

    unique_keyword_norms = {_norm(k) for k in keywords}
    if len(unique_keyword_norms) != len(keywords):
        issues.append("duplicate_keywords")

    unique_topic_norms = {_norm(t) for t in topics}
    if len(unique_topic_norms) != len(topics):
        issues.append("duplicate_key_topics")

    source_scope = header + " " + doc
    topic_hits = sum(1 for topic in topics if _jaccard(topic, source_scope) >= 0.05 or _norm(topic) in _norm(source_scope))
    keyword_hits = sum(1 for kw in keywords if _jaccard(kw, source_scope) >= 0.05 or _norm(kw) in _norm(source_scope))

    if topic_hits < max(1, min(3, len(topics) // 2)):
        issues.append(f"few_key_topics_trace_to_source:{topic_hits}/{len(topics)}")

    if keyword_hits < max(2, min(6, len(keywords) // 2)):
        issues.append(f"few_keywords_trace_to_source:{keyword_hits}/{len(keywords)}")

    # Sketch should be compact enough to prepend/contextualize chunks.
    total_words = _word_count(summary) + _word_count(structure_notes) + sum(_word_count(x) for x in topics + keywords)
    if total_words > 240:
        issues.append(f"sketch_too_verbose_for_contextualization:{total_words}_words")

    if hard:
        return {
            "key": "retrieval_utility",
            "score": 0.0,
            "comment": "; ".join(issues[:10]),
            "hard_rule_violated": True,
        }

    if issues:
        return {
            "key": "retrieval_utility",
            "score": 0.5,
            "comment": "; ".join(issues[:10]),
            "hard_rule_violated": False,
        }

    return {
        "key": "retrieval_utility",
        "score": 1.0,
        "comment": "topics/keywords compact and retrieval-useful",
        "hard_rule_violated": False,
    }


# ---------------------------------------------------------------------------
# Evaluator 4: document_type_and_structure
# ---------------------------------------------------------------------------

def document_type_and_structure(run, example) -> dict:
    sketch = _get_sketch(_safe_get_outputs(run))
    inputs = _safe_get_inputs(example)
    gold = _get_gold_sketch(_safe_get_reference(example))

    if sketch is None:
        return {"key": "document_type_and_structure", "score": 0.0, "comment": "sketch_json missing/malformed"}

    header = str(inputs.get("header", ""))
    doc = str(inputs.get("document_text", ""))
    pred_type = sketch.get("document_type")
    expected_type = None

    if isinstance(gold, dict) and gold.get("document_type") in VALID_DOCUMENT_TYPES:
        expected_type = gold["document_type"]
    else:
        expected_type = _doc_type_from_text(header, doc)

    issues = []

    # Treat exam_paper/question_paper as equivalent.
    equivalent = {pred_type, expected_type} <= {"exam_paper", "question_paper"}
    if expected_type != "unknown" and pred_type != expected_type and not equivalent:
        issues.append(f"document_type_mismatch:pred={pred_type},expected~={expected_type}")

    structure = str(sketch.get("structure_notes", ""))
    if expected_type in {"exam_paper", "question_paper"}:
        if not _contains_any(structure, {"section", "question", "marks", "mcq", "case study", "numbered"}):
            issues.append("question_paper_structure_notes_not_question_aware")
    elif expected_type == "notes":
        if not _contains_any(structure, {"notes", "definitions", "examples", "formulas", "concepts", "headings"}):
            issues.append("notes_structure_notes_not_notes_aware")
    elif expected_type == "textbook_excerpt":
        if not _contains_any(structure, {"chapter", "example", "exercise", "figure", "activity", "paragraph"}):
            issues.append("textbook_structure_notes_not_textbook_aware")

    if issues:
        hard = any("mismatch" in x for x in issues)
        return {
            "key": "document_type_and_structure",
            "score": 0.0 if hard else 0.5,
            "comment": "; ".join(issues),
        }

    return {
        "key": "document_type_and_structure",
        "score": 1.0,
        "comment": f"document_type/structure passed; type={pred_type}",
    }


# ---------------------------------------------------------------------------
# Evaluator 5: no_noise_or_answer_key_leakage
# ---------------------------------------------------------------------------

def no_noise_or_answer_key_leakage(run, example) -> dict:
    sketch = _get_sketch(_safe_get_outputs(run))
    inputs = _safe_get_inputs(example)

    if sketch is None:
        return {
            "key": "no_noise_or_answer_key_leakage",
            "score": 0.0,
            "comment": "sketch_json missing/malformed",
            "hard_rule_violated": False,
        }

    sketch_text = _flatten_sketch_text(sketch)
    doc = str(inputs.get("document_text", ""))

    issues = []
    hard = False

    # Footers can exist in the source, but should not dominate sketch keywords/topics.
    keyword_topic_text = " ".join(sketch.get("keywords", []) + sketch.get("key_topics", [])) if isinstance(sketch.get("keywords"), list) and isinstance(sketch.get("key_topics"), list) else sketch_text

    if _contains_any(keyword_topic_text, FOOTER_NOISE):
        issues.append("footer/web/noise token included in retrieval metadata")
        hard = True

    # Answer key documents are valid, but regular exam/worksheet sketches should
    # not turn answers into core keywords unless the document itself is clearly a key.
    doc_is_key = _contains_any(doc, ANSWER_KEY_NOISE)
    if not doc_is_key and _contains_any(keyword_topic_text, ANSWER_KEY_NOISE):
        issues.append("answer-key wording leaked into non-solution sketch metadata")
        hard = True

    # Prevent copying too much raw text into sketch.
    longest_topic_or_keyword = max([_word_count(x) for x in (sketch.get("key_topics", []) + sketch.get("keywords", []))], default=0)
    if longest_topic_or_keyword > 12:
        issues.append(f"topic_or_keyword_too_sentence_like:{longest_topic_or_keyword}_words")

    if hard:
        return {
            "key": "no_noise_or_answer_key_leakage",
            "score": 0.0,
            "comment": "; ".join(issues),
            "hard_rule_violated": True,
        }

    if issues:
        return {
            "key": "no_noise_or_answer_key_leakage",
            "score": 0.5,
            "comment": "; ".join(issues),
            "hard_rule_violated": False,
        }

    return {
        "key": "no_noise_or_answer_key_leakage",
        "score": 1.0,
        "comment": "no footer/answer-key/noise leakage detected",
        "hard_rule_violated": False,
    }


# ---------------------------------------------------------------------------
# Evaluator 6: thin_or_noisy_source_behavior
# ---------------------------------------------------------------------------

def thin_or_noisy_source_behavior(run, example) -> dict:
    sketch = _get_sketch(_safe_get_outputs(run))
    inputs = _safe_get_inputs(example)

    if sketch is None:
        return {"key": "thin_or_noisy_source_behavior", "score": 0.0, "comment": "sketch_json missing/malformed"}

    doc = str(inputs.get("document_text", ""))
    summary = str(sketch.get("summary", ""))
    topics = sketch.get("key_topics", [])
    keywords = sketch.get("keywords", [])

    issues = []

    if _word_count(doc) < 40:
        # Thin source should produce conservative sketch.
        if _word_count(summary) > 70:
            issues.append(f"thin_source_summary_too_expansive:{_word_count(summary)}_words")
        if len(topics) > 5:
            issues.append(f"thin_source_too_many_topics:{len(topics)}")
        if len(keywords) > 10:
            issues.append(f"thin_source_too_many_keywords:{len(keywords)}")
        if not _contains_any(summary, {"brief", "limited", "available text", "excerpt", "appears"}):
            issues.append("thin_source_not_marked_as_limited_or_excerpt")

    if _contains_any(doc, {"ocr", "unclear", "illegible", "garbled", "scan artifact"}):
        if not _contains_any(str(sketch.get("structure_notes", "")) + " " + summary, {"ocr", "unclear", "scan", "garbled", "limited"}):
            issues.append("noisy_ocr_source_not_acknowledged")

    if issues:
        hard = len(issues) >= 3
        return {
            "key": "thin_or_noisy_source_behavior",
            "score": 0.0 if hard else 0.5,
            "comment": "; ".join(issues),
        }

    return {"key": "thin_or_noisy_source_behavior", "score": 1.0, "comment": "thin/noisy source behavior passed"}


# ---------------------------------------------------------------------------
# Summary evaluator
# ---------------------------------------------------------------------------

def document_sketch_severity_summary(runs: list, examples: list) -> dict:
    """
    BLOCK:
    - invalid schema / wrong keys
    - ungrounded sketch
    - too many unsupported numeric/formula terms
    - footer/answer-key/noise leakage into retrieval metadata
    - document_type mismatch when source type is obvious

    REVIEW:
    - summary/title/keyword counts outside preferred range
    - possible unsupported terms
    - thin-source over-expansion
    - weak retrieval utility
    """
    if len(runs) != len(examples):
        return {
            "key": "document_sketch_severity_summary",
            "score": 0.0,
            "comment": f"runs/examples length mismatch ({len(runs)} vs {len(examples)})",
            "ship_recommendation": "BLOCK",
        }

    tier_0 = []
    tier_1 = 0
    tier_1_applicable = 0
    variation_totals = {}
    variation_passes = {}

    for run, example in zip(runs, examples):
        variation = _safe_get_variation(example)
        variation_totals[variation] = variation_totals.get(variation, 0) + 1

        schema = schema_validity(run, example)
        if schema["score"] == 0.0:
            tier_0.append({"example_id": getattr(example, "id", None), "reason": f"schema_validity failed: {schema['comment']}"})
            continue

        grounded = grounded_sketch(run, example)
        retrieval = retrieval_utility(run, example)
        doc_type = document_type_and_structure(run, example)
        noise = no_noise_or_answer_key_leakage(run, example)
        thin = thin_or_noisy_source_behavior(run, example)

        for result in (grounded, retrieval, noise):
            if result.get("hard_rule_violated"):
                tier_0.append({"example_id": getattr(example, "id", None), "reason": f"{result['key']} hard failure: {result['comment']}"})

        if doc_type["score"] == 0.0:
            tier_0.append({"example_id": getattr(example, "id", None), "reason": f"document_type_and_structure failed: {doc_type['comment']}"})

        tier_1_applicable += 6
        for result in (schema, grounded, retrieval, doc_type, noise, thin):
            if result["score"] < 1.0:
                tier_1 += 1

        if (
            schema["score"] == 1.0
            and grounded["score"] == 1.0
            and retrieval["score"] == 1.0
            and doc_type["score"] == 1.0
            and noise["score"] == 1.0
            and thin["score"] == 1.0
        ):
            variation_passes[variation] = variation_passes.get(variation, 0) + 1

    tier_1_rate = tier_1 / tier_1_applicable if tier_1_applicable else 0.0
    per_variation = {v: round(variation_passes.get(v, 0) / total, 3) for v, total in variation_totals.items()}

    recommendation = "BLOCK" if tier_0 else ("REVIEW" if tier_1_rate > 0.20 else "OK")

    return {
        "key": "document_sketch_severity_summary",
        "score": 0.0 if tier_0 else round(1.0 - tier_1_rate, 3),
        "comment": (
            f"ship_recommendation={recommendation} | "
            f"tier_0_blocking_count={len(tier_0)} | "
            f"tier_1_review_rate={tier_1_rate:.3f} | "
            f"evaluator_type=code_first_tier3"
        ),
        "tier_0_blocking_count": len(tier_0),
        "tier_0_blocking_examples": tier_0,
        "tier_1_review_rate": round(tier_1_rate, 3),
        "per_variation_pass_rate": per_variation,
        "ship_recommendation": recommendation,
    }


# ---------------------------------------------------------------------------
# Public registries
# ---------------------------------------------------------------------------

PER_EXAMPLE_EVALUATORS = [
    schema_validity,
    grounded_sketch,
    retrieval_utility,
    document_type_and_structure,
    no_noise_or_answer_key_leakage,
    thin_or_noisy_source_behavior,
]

SUMMARY_EVALUATORS = [document_sketch_severity_summary]
