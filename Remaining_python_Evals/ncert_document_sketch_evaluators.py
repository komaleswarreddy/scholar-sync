"""
ncert_document_sketch_evaluators.py

LangSmith custom evaluators for Agent 27: NCERT Document Sketch.

Agent role:
- Optional NCERT-ingestion helper.
- Produces a compact chapter-level sketch from NCERT document text.
- The sketch helps Agent 28 Chunk Contextualization add NCERT chapter context
  to each indexed chunk when contextual retrieval is enabled.

Production dependencies:
- Inputs:
    header: str
    document_text: str
- Output:
    sketch_json: dict

Recommended sketch_json contract used by this evaluator:
    {
      "title": str,                  # short NCERT chapter/source title
      "document_type": str,          # textbook_excerpt | notes | mixed | unknown
      "summary": str,                # compact grounded chapter/source summary
      "key_topics": list[str],       # 3-10 NCERT-grounded topics
      "keywords": list[str],         # 5-18 retrieval-friendly NCERT terms
      "structure_notes": str         # compact notes about NCERT organization
    }

Why code-first:
- Agent 27 is Tier 3 and optional.
- It is a retrieval-ingestion helper, not a student-facing answer generator.
- The failure modes are mostly deterministic:
  wrong schema, non-NCERT/exam-paper style sketch, unsupported terms, bloated
  summary, generic keywords, footer/answer-key leakage, and poor downstream
  utility for Agent 28.

Dependency note:
- Agent 27 is parallel to Agent 26, not dependent on Agent 26.
- Agent 27 is bypassed when NCERT/document-sketch flags are off.
- Agent 28 may consume this sketch during contextual retrieval indexing.

LangSmith usage:
    from ncert_document_sketch_evaluators import (
        PER_EXAMPLE_EVALUATORS,
        SUMMARY_EVALUATORS,
    )

    client.evaluate(
        target_fn,
        data="nbm-prompt-ncert_document_sketch",
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
    "textbook_excerpt",
    "notes",
    "mixed",
    "unknown",
}

SUMMARY_MIN_WORDS = 28
SUMMARY_MAX_WORDS = 150

KEY_TOPICS_MIN = 3
KEY_TOPICS_MAX = 10

KEYWORDS_MIN = 5
KEYWORDS_MAX = 18

TITLE_MAX_WORDS = 18
STRUCTURE_NOTES_MAX_WORDS = 90

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

NCERT_CUES = {
    "ncert",
    "chapter",
    "exercise",
    "example",
    "activity",
    "figure",
    "table",
    "summary",
    "intext question",
    "textbook",
    "class 11",
    "class 12",
    "class xi",
    "class xii",
    "cbse",
}

TEXTBOOK_STRUCTURE_CUES = {
    "definition",
    "example",
    "activity",
    "figure",
    "table",
    "exercise",
    "derivation",
    "concept",
    "formula",
    "diagram",
    "summary",
    "paragraph",
}

EXAM_PAPER_CUES = {
    "section a",
    "section b",
    "marks",
    "choose the correct",
    "mcq",
    "assertion",
    "reason",
    "case study",
    "q.",
    "question paper",
    "answer the following",
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
    "solution manual",
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
    "ncert chapter",
}

GENERIC_WORDS = {
    "the", "and", "with", "from", "this", "that", "document", "chapter",
    "notes", "question", "questions", "answer", "answers", "summary",
    "topic", "topics", "concept", "concepts", "important", "student",
    "students", "study", "material", "section", "page", "class",
    "source", "text", "contains", "covers", "includes", "ncert",
    "textbook", "exercise", "examples", "example", "activity",
}

SUBJECT_HINTS = {
    "physics": {
        "current", "electric", "resistance", "potential", "charge", "field",
        "ray", "optics", "lens", "mirror", "motion", "force", "energy",
        "work", "power", "wave", "magnetic", "capacitance", "induction",
    },
    "chemistry": {
        "mole", "equilibrium", "bond", "coordination", "compound", "reaction",
        "oxidation", "reduction", "electrochemistry", "hydrocarbon", "acid",
        "base", "enthalpy", "orbital", "hybridisation", "ligand",
    },
    "biology": {
        "cell", "dna", "rna", "gene", "organism", "plant", "animal",
        "photosynthesis", "respiration", "tissue", "enzyme", "protein",
        "evolution", "ecology", "reproduction", "inheritance",
    },
    "mathematics": {
        "function", "limit", "derivative", "integral", "matrix", "determinant",
        "vector", "probability", "binomial", "conic", "parabola", "equation",
        "inequality", "theorem", "line", "plane",
    },
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
        "contains", "covers", "includes", "summary", "ncert", "class",
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


def _infer_subject_text(header: str, document_text: str) -> str:
    text = _norm(header + " " + document_text)
    scores = {subj: sum(1 for h in hints if h in text) for subj, hints in SUBJECT_HINTS.items()}
    best, score = max(scores.items(), key=lambda kv: kv[1])
    return best if score >= 2 else "unknown"


def _is_exam_paper_like(text: str) -> bool:
    t = _norm(text)
    return sum(1 for cue in EXAM_PAPER_CUES if cue in t) >= 3


def _is_ncert_like(text: str) -> bool:
    t = _norm(text)
    return sum(1 for cue in NCERT_CUES if cue in t) >= 2


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

    extra = set(sketch.keys()) - CORE_SKETCH_KEYS
    if extra:
        # Allow no extras for stable downstream Agent 28 consumption.
        return {
            "key": "schema_validity",
            "score": 0.5,
            "comment": f"unexpected optional key(s): {sorted(extra)}",
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
# Evaluator 2: ncert_source_contract
# ---------------------------------------------------------------------------

def ncert_source_contract(run, example) -> dict:
    sketch = _get_sketch(_safe_get_outputs(run))
    inputs = _safe_get_inputs(example)

    if sketch is None:
        return {
            "key": "ncert_source_contract",
            "score": 0.0,
            "comment": "sketch_json missing/malformed",
            "hard_rule_violated": False,
        }

    header = str(inputs.get("header", ""))
    doc = str(inputs.get("document_text", ""))
    source_text = header + " " + doc
    sketch_text = _flatten_sketch_text(sketch)
    issues = []
    hard = False

    # NCERT sketch should look like a textbook/chapter sketch, not an exam-paper sketch.
    if _is_exam_paper_like(source_text) and sketch.get("document_type") == "textbook_excerpt":
        issues.append("exam-paper-like source incorrectly labeled textbook_excerpt")
        hard = True

    if _is_ncert_like(source_text) and sketch.get("document_type") not in {"textbook_excerpt", "notes", "mixed"}:
        issues.append(f"NCERT-like source has weak document_type={sketch.get('document_type')!r}")

    # Sketch should preserve NCERT/chapter identity when visible.
    if _contains_any(source_text, {"ncert", "class 11", "class 12", "class xi", "class xii", "cbse"}):
        if not _contains_any(sketch_text, {"ncert", "class", "chapter", "textbook", "cbse"}):
            issues.append("NCERT/class/chapter identity not reflected")

    # Title should not be generic.
    title = str(sketch.get("title", ""))
    if _norm(title) in GENERIC_TOPICS or _word_count(title) <= 1:
        issues.append(f"generic_title:{title!r}")

    if hard:
        return {
            "key": "ncert_source_contract",
            "score": 0.0,
            "comment": "; ".join(issues),
            "hard_rule_violated": True,
        }

    if issues:
        return {
            "key": "ncert_source_contract",
            "score": 0.5,
            "comment": "; ".join(issues),
            "hard_rule_violated": False,
        }

    return {
        "key": "ncert_source_contract",
        "score": 1.0,
        "comment": "NCERT source identity and document_type checks passed",
        "hard_rule_violated": False,
    }


# ---------------------------------------------------------------------------
# Evaluator 3: grounded_ncert_sketch
# ---------------------------------------------------------------------------

def grounded_ncert_sketch(run, example) -> dict:
    sketch = _get_sketch(_safe_get_outputs(run))
    inputs = _safe_get_inputs(example)
    gold = _get_gold_sketch(_safe_get_reference(example))

    if sketch is None:
        return {
            "key": "grounded_ncert_sketch",
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

    # For NCERT sketches, invented named laws/chapters are serious.
    named_unsupported = [t for t in unsupported if " " in t and len(t) > 8]
    if named_unsupported:
        issues.append(f"unsupported_named_terms:{named_unsupported[:5]}")
        hard = True

    if len(unsupported) >= 8:
        issues.append(f"many_unsupported_terms:{unsupported[:8]}")
        hard = True
    elif unsupported:
        issues.append(f"possible_unsupported_terms:{unsupported[:6]}")

    if hard:
        return {
            "key": "grounded_ncert_sketch",
            "score": 0.0,
            "comment": "; ".join(issues[:10]),
            "hard_rule_violated": True,
        }

    if issues:
        return {
            "key": "grounded_ncert_sketch",
            "score": 0.5,
            "comment": "; ".join(issues[:10]),
            "hard_rule_violated": False,
        }

    return {
        "key": "grounded_ncert_sketch",
        "score": 1.0,
        "comment": f"NCERT sketch grounded; overlap={overlap:.2f}",
        "hard_rule_violated": False,
    }


# ---------------------------------------------------------------------------
# Evaluator 4: syllabus_retrieval_utility
# ---------------------------------------------------------------------------

def syllabus_retrieval_utility(run, example) -> dict:
    sketch = _get_sketch(_safe_get_outputs(run))
    inputs = _safe_get_inputs(example)

    if sketch is None:
        return {
            "key": "syllabus_retrieval_utility",
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
            "key": "syllabus_retrieval_utility",
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

    if topic_hits < max(2, min(4, len(topics) // 2)):
        issues.append(f"few_key_topics_trace_to_source:{topic_hits}/{len(topics)}")

    if keyword_hits < max(3, min(7, len(keywords) // 2)):
        issues.append(f"few_keywords_trace_to_source:{keyword_hits}/{len(keywords)}")

    inferred_subject = _infer_subject_text(header, doc)
    if inferred_subject != "unknown":
        subject_term_hits = sum(1 for term in keywords + topics if _contains_any(term, SUBJECT_HINTS[inferred_subject]))
        if subject_term_hits < 2:
            issues.append(f"retrieval_metadata_not_subject_specific:{inferred_subject}")

    # Sketch should be compact enough to prepend/contextualize chunks.
    total_words = _word_count(summary) + _word_count(structure_notes) + sum(_word_count(x) for x in topics + keywords)
    if total_words > 260:
        issues.append(f"sketch_too_verbose_for_contextualization:{total_words}_words")

    if hard:
        return {
            "key": "syllabus_retrieval_utility",
            "score": 0.0,
            "comment": "; ".join(issues[:10]),
            "hard_rule_violated": True,
        }

    if issues:
        return {
            "key": "syllabus_retrieval_utility",
            "score": 0.5,
            "comment": "; ".join(issues[:10]),
            "hard_rule_violated": False,
        }

    return {
        "key": "syllabus_retrieval_utility",
        "score": 1.0,
        "comment": "NCERT topics/keywords are compact and retrieval-useful",
        "hard_rule_violated": False,
    }


# ---------------------------------------------------------------------------
# Evaluator 5: textbook_structure_alignment
# ---------------------------------------------------------------------------

def textbook_structure_alignment(run, example) -> dict:
    sketch = _get_sketch(_safe_get_outputs(run))
    inputs = _safe_get_inputs(example)

    if sketch is None:
        return {"key": "textbook_structure_alignment", "score": 0.0, "comment": "sketch_json missing/malformed"}

    doc = str(inputs.get("document_text", ""))
    sketch_text = _flatten_sketch_text(sketch)
    structure = str(sketch.get("structure_notes", ""))

    issues = []

    if _contains_any(doc, {"example", "exercise", "activity", "figure", "table", "derivation"}):
        if not _contains_any(structure, TEXTBOOK_STRUCTURE_CUES):
            issues.append("source_has_textbook_structure_but_structure_notes_do_not_reflect_it")

    if _contains_any(doc, {"definition", "formula", "theorem", "law", "principle"}):
        if not _contains_any(sketch_text, {"definition", "formula", "theorem", "law", "principle", "relation"}):
            issues.append("conceptual/formula structure missing from sketch")

    if _is_exam_paper_like(doc):
        if sketch.get("document_type") == "textbook_excerpt":
            issues.append("exam-like source should not be labeled textbook_excerpt")
        if _contains_any(structure, {"example", "activity", "textbook", "chapter"}):
            issues.append("exam-like source structure is described as textbook content")

    if issues:
        hard = any("should not be labeled" in x for x in issues)
        return {
            "key": "textbook_structure_alignment",
            "score": 0.0 if hard else 0.5,
            "comment": "; ".join(issues),
        }

    return {
        "key": "textbook_structure_alignment",
        "score": 1.0,
        "comment": "textbook/chapter structure alignment passed",
    }


# ---------------------------------------------------------------------------
# Evaluator 6: no_noise_or_exam_leakage
# ---------------------------------------------------------------------------

def no_noise_or_exam_leakage(run, example) -> dict:
    sketch = _get_sketch(_safe_get_outputs(run))
    inputs = _safe_get_inputs(example)

    if sketch is None:
        return {
            "key": "no_noise_or_exam_leakage",
            "score": 0.0,
            "comment": "sketch_json missing/malformed",
            "hard_rule_violated": False,
        }

    sketch_text = _flatten_sketch_text(sketch)
    doc = str(inputs.get("document_text", ""))

    issues = []
    hard = False

    keyword_topic_text = " ".join(sketch.get("keywords", []) + sketch.get("key_topics", [])) if isinstance(sketch.get("keywords"), list) and isinstance(sketch.get("key_topics"), list) else sketch_text

    if _contains_any(keyword_topic_text, FOOTER_NOISE):
        issues.append("footer/web/noise token included in retrieval metadata")
        hard = True

    doc_is_key = _contains_any(doc, ANSWER_KEY_NOISE)
    if not doc_is_key and _contains_any(keyword_topic_text, ANSWER_KEY_NOISE):
        issues.append("answer-key wording leaked into NCERT retrieval metadata")
        hard = True

    # NCERT sketch should not become a generated exam paper sketch unless source is exam-like.
    if not _is_exam_paper_like(doc) and _contains_any(keyword_topic_text, EXAM_PAPER_CUES):
        issues.append("exam-paper cues leaked into NCERT textbook metadata")

    longest_topic_or_keyword = max([_word_count(x) for x in (sketch.get("key_topics", []) + sketch.get("keywords", []))], default=0)
    if longest_topic_or_keyword > 12:
        issues.append(f"topic_or_keyword_too_sentence_like:{longest_topic_or_keyword}_words")

    if hard:
        return {
            "key": "no_noise_or_exam_leakage",
            "score": 0.0,
            "comment": "; ".join(issues),
            "hard_rule_violated": True,
        }

    if issues:
        return {
            "key": "no_noise_or_exam_leakage",
            "score": 0.5,
            "comment": "; ".join(issues),
            "hard_rule_violated": False,
        }

    return {
        "key": "no_noise_or_exam_leakage",
        "score": 1.0,
        "comment": "no footer/answer-key/exam-noise leakage detected",
        "hard_rule_violated": False,
    }


# ---------------------------------------------------------------------------
# Evaluator 7: thin_or_noisy_ncert_behavior
# ---------------------------------------------------------------------------

def thin_or_noisy_ncert_behavior(run, example) -> dict:
    sketch = _get_sketch(_safe_get_outputs(run))
    inputs = _safe_get_inputs(example)

    if sketch is None:
        return {"key": "thin_or_noisy_ncert_behavior", "score": 0.0, "comment": "sketch_json missing/malformed"}

    doc = str(inputs.get("document_text", ""))
    summary = str(sketch.get("summary", ""))
    topics = sketch.get("key_topics", [])
    keywords = sketch.get("keywords", [])

    issues = []

    if _word_count(doc) < 45:
        if _word_count(summary) > 75:
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
            "key": "thin_or_noisy_ncert_behavior",
            "score": 0.0 if hard else 0.5,
            "comment": "; ".join(issues),
        }

    return {"key": "thin_or_noisy_ncert_behavior", "score": 1.0, "comment": "thin/noisy NCERT source behavior passed"}


# ---------------------------------------------------------------------------
# Summary evaluator
# ---------------------------------------------------------------------------

def ncert_document_sketch_severity_summary(runs: list, examples: list) -> dict:
    """
    BLOCK:
    - invalid schema / wrong keys
    - exam-paper source labeled as NCERT textbook
    - ungrounded sketch / invented named terms
    - footer/answer-key/noise in retrieval metadata
    - subject/topic metadata too generic to help Agent 28

    REVIEW:
    - length/count outside preferred range
    - possible unsupported terms
    - thin-source over-expansion
    - structure notes weak
    """
    if len(runs) != len(examples):
        return {
            "key": "ncert_document_sketch_severity_summary",
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

        ncert = ncert_source_contract(run, example)
        grounded = grounded_ncert_sketch(run, example)
        retrieval = syllabus_retrieval_utility(run, example)
        structure = textbook_structure_alignment(run, example)
        noise = no_noise_or_exam_leakage(run, example)
        thin = thin_or_noisy_ncert_behavior(run, example)

        for result in (ncert, grounded, retrieval, noise):
            if result.get("hard_rule_violated"):
                tier_0.append({"example_id": getattr(example, "id", None), "reason": f"{result['key']} hard failure: {result['comment']}"})

        if structure["score"] == 0.0:
            tier_0.append({"example_id": getattr(example, "id", None), "reason": f"textbook_structure_alignment failed: {structure['comment']}"})

        tier_1_applicable += 7
        for result in (schema, ncert, grounded, retrieval, structure, noise, thin):
            if result["score"] < 1.0:
                tier_1 += 1

        if (
            schema["score"] == 1.0
            and ncert["score"] == 1.0
            and grounded["score"] == 1.0
            and retrieval["score"] == 1.0
            and structure["score"] == 1.0
            and noise["score"] == 1.0
            and thin["score"] == 1.0
        ):
            variation_passes[variation] = variation_passes.get(variation, 0) + 1

    tier_1_rate = tier_1 / tier_1_applicable if tier_1_applicable else 0.0
    per_variation = {v: round(variation_passes.get(v, 0) / total, 3) for v, total in variation_totals.items()}

    recommendation = "BLOCK" if tier_0 else ("REVIEW" if tier_1_rate > 0.20 else "OK")

    return {
        "key": "ncert_document_sketch_severity_summary",
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
    ncert_source_contract,
    grounded_ncert_sketch,
    syllabus_retrieval_utility,
    textbook_structure_alignment,
    no_noise_or_exam_leakage,
    thin_or_noisy_ncert_behavior,
]

SUMMARY_EVALUATORS = [ncert_document_sketch_severity_summary]
