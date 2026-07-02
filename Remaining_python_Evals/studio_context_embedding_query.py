"""
studio_context_embedding_query_evaluators.py

LangSmith custom evaluators for Agent 16: Studio Context Embedding Query Legacy.

Agent role:
- Legacy fallback retrieval-query builder for Studio RAG.
- Builds ONE embedding search query string for Pinecone retrieval.
- Live Studio bypasses this agent: fixed STUDIO_BROAD_RETRIEVAL_QUERIES when
  retrieval_focus is empty, and Query Rewriter (#2) when retrieval_focus is set.

Production dependencies:
- Inputs: studio_task, source_title, topic
- Output: embedding_query

Design choice:
- Code-first, not LLM/hybrid.
- Tier 3 regression subset. Output is a short query, so key contract, one-line
  format, concision, task-awareness, topic/source relevance, topic expansion,
  and legacy no-leak behavior are deterministic enough.
"""

from __future__ import annotations

import json
import re
from typing import Any, Optional

REQUIRED_INPUT_KEYS = {"studio_task", "source_title", "topic"}
REQUIRED_OUTPUT_KEYS = {"embedding_query"}
ALLOWED_OUTPUT_KEYS = {"embedding_query"}
VALID_STUDIO_TASKS = {"quiz", "flashcards", "mind_map", "slide_deck"}

MIN_QUERY_TOKENS = 12
MAX_QUERY_TOKENS = 28

TASK_CUES = {
    "quiz": {"quiz", "mcq", "questions", "practice", "application", "conceptual", "test", "answer", "options"},
    "flashcards": {"flashcards", "definitions", "terms", "formulas", "recall", "key terms", "memory", "cards"},
    "mind_map": {"mind map", "hierarchy", "relationships", "connections", "structure", "classification", "branches", "concept map"},
    "slide_deck": {"slide deck", "lesson", "overview", "sequence", "process", "explain", "presentation", "flow"},
}

BROAD_DEFAULT_QUERY = "educational source material overview and key concepts"

BANNED_PATTERNS = {
    "as an ai language model", "i cannot", "i can't", "not enough context",
    "json", "markdown", "```", "pinecone", "embedding model", "studioservice",
    "retrieval_focus", "studio_broad_retrieval_queries", "query rewriter",
    "fallback prompt", "j2", "system prompt",
}

GENERIC_WORDS = {
    "chapter", "source", "title", "topic", "concept", "concepts", "overview",
    "key", "important", "study", "material", "educational", "class",
    "student", "students", "ncert", "cbse", "quiz", "flashcards", "mind",
    "map", "slide", "deck", "lesson", "practice", "questions", "definition",
    "definitions", "formula", "formulas", "terms", "relationships",
    "hierarchy", "process", "flow", "explain", "overview",
}

TITLE_STOPWORDS = {"chapter", "class", "ncert", "cbse", "part", "unit", "pdf"}

SUBJECT_EXPANSION_HINTS = {
    "current": {"ohm", "resistance", "resistivity", "kirchhoff", "drift", "mobility", "series", "parallel", "cell", "emf", "power", "temperature"},
    "electricity": {"ohm", "resistance", "resistivity", "kirchhoff", "drift", "mobility", "series", "parallel", "cell", "emf", "power", "temperature"},
    "ray": {"reflection", "refraction", "lens", "mirror", "prism", "focus", "image", "magnification", "power", "optical", "instrument"},
    "optics": {"reflection", "refraction", "lens", "mirror", "prism", "focus", "image", "magnification", "power", "optical", "instrument"},
    "work": {"energy", "kinetic", "potential", "power", "conservative", "work-energy", "collision", "spring", "force"},
    "rotation": {"torque", "angular", "momentum", "inertia", "rolling", "equilibrium", "centre", "mass", "rigid"},
    "equilibrium": {"kc", "kp", "reaction", "quotient", "le", "chatelier", "ionic", "acid", "base", "buffer", "solubility"},
    "electrochemistry": {"cell", "electrode", "nernst", "emf", "conductance", "faraday", "galvanic", "electrolysis", "potential"},
    "bonding": {"ionic", "covalent", "hybridisation", "vsepr", "bond", "molecular", "orbital", "dipole", "geometry"},
    "hydrocarbons": {"alkane", "alkene", "alkyne", "aromatic", "isomerism", "reaction", "addition", "substitution", "benzene"},
    "coordination": {"ligand", "coordination", "isomerism", "crystal", "field", "nomenclature", "complex", "oxidation"},
    "molecular": {"dna", "rna", "replication", "transcription", "translation", "codon", "gene", "mutation", "operon", "genetic"},
    "inheritance": {"dna", "rna", "replication", "transcription", "translation", "codon", "gene", "mutation", "operon", "genetic"},
    "cell": {"mitosis", "meiosis", "cycle", "phase", "chromosome", "division", "checkpoint", "cytokinesis"},
    "anatomy": {"tissue", "xylem", "phloem", "root", "stem", "leaf", "dicot", "monocot", "vascular"},
    "conic": {"parabola", "ellipse", "hyperbola", "focus", "directrix", "eccentricity", "latus", "rectum", "circle"},
    "probability": {"event", "conditional", "bayes", "independent", "random", "variable", "distribution", "mean", "variance"},
    "binomial": {"expansion", "general", "term", "coefficient", "pascal", "middle", "positive", "integer"},
    "inequalities": {"linear", "solution", "interval", "graph", "half-plane", "system", "number", "line"},
}


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


def _query_tokens(text: str) -> list[str]:
    return re.findall(r"[a-zA-Z0-9ΩμρΔθ/^²³+-]+", _norm(text))


def _content_tokens(text: str) -> set[str]:
    stop = {"the", "a", "an", "and", "or", "to", "of", "in", "on", "for", "with", "is", "are", "from", "using", "before", "after", "into", "based", "source", "title", "topic", "chapter", "class"}
    return {t for t in _query_tokens(text) if len(t) > 2 and t not in stop}


def _contains_any(text: str, needles) -> bool:
    t = _norm(text)
    return any(_norm(n) in t for n in needles)


def _jaccard(a: str, b: str) -> float:
    ta, tb = _content_tokens(a), _content_tokens(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def _get_task(inputs: dict) -> str:
    return _norm(inputs.get("studio_task", ""))


def _get_query(out: Optional[dict]) -> Optional[str]:
    if not isinstance(out, dict):
        return None
    val = out.get("embedding_query")
    return val if isinstance(val, str) else None


def _get_gold_query(ref: Optional[dict]) -> str:
    if not isinstance(ref, dict):
        return ""
    val = ref.get("embedding_query", "")
    return val if isinstance(val, str) else str(val)


def _title_terms(source_title: str) -> set[str]:
    return {t for t in _content_tokens(source_title) if t not in TITLE_STOPWORDS and t not in GENERIC_WORDS}


def _topic_terms(topic: str) -> set[str]:
    return {t for t in _content_tokens(topic) if t not in GENERIC_WORDS}


def _expected_expansion_terms(source_title: str, topic: str) -> set[str]:
    text = _norm(source_title + " " + topic)
    expected = set()
    for key, terms in SUBJECT_EXPANSION_HINTS.items():
        if key in text:
            expected |= terms
    return expected


def _is_plain_one_line(text: str) -> bool:
    return "\n" not in text.strip() and "\r" not in text.strip()


def _has_sentence_preamble(query: str) -> bool:
    q = _norm(query)
    bad_starts = ("here is", "sure", "this query", "use this", "embedding query:", "search query:", "query:", "i would search")
    return q.startswith(bad_starts)


def _task_cue_present(task: str, query: str) -> bool:
    return any(cue in _norm(query) for cue in TASK_CUES.get(task, set()))


def parse_model_response_to_outputs(raw_text: str) -> dict:
    if not isinstance(raw_text, str):
        return {}
    text = raw_text.strip()
    if not text:
        return {"embedding_query": ""}
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, flags=re.DOTALL)
    candidate = fence.group(1) if fence else text
    try:
        parsed = json.loads(candidate)
        if isinstance(parsed, dict) and isinstance(parsed.get("embedding_query"), str):
            return {"embedding_query": parsed["embedding_query"].strip()}
    except Exception:
        pass
    label = re.match(r"^(?:embedding query|search query|query)\s*:\s*(.+)$", text, flags=re.IGNORECASE | re.DOTALL)
    if label:
        return {"embedding_query": label.group(1).strip()}
    return {"embedding_query": text}


def key_contract(run, example) -> dict:
    inputs = _safe_get_inputs(example)
    out = _safe_get_outputs(run)

    missing_inputs = REQUIRED_INPUT_KEYS - set(inputs.keys())
    if missing_inputs:
        return {"key": "key_contract", "score": 0.0, "comment": f"missing required input key(s): {sorted(missing_inputs)}"}

    task = _get_task(inputs)
    if task not in VALID_STUDIO_TASKS:
        return {"key": "key_contract", "score": 0.0, "comment": f"invalid studio_task={task!r}; expected one of {sorted(VALID_STUDIO_TASKS)}"}

    if out is None:
        return {"key": "key_contract", "score": 0.0, "comment": "outputs missing or not a JSON object"}

    present = set(out.keys())
    missing = REQUIRED_OUTPUT_KEYS - present
    extra = present - ALLOWED_OUTPUT_KEYS
    if missing or extra:
        return {"key": "key_contract", "score": 0.0, "comment": f"output key mismatch -- missing={sorted(missing)} extra={sorted(extra)}"}

    query = out.get("embedding_query")
    if not isinstance(query, str):
        return {"key": "key_contract", "score": 0.0, "comment": f"embedding_query must be string, got {type(query).__name__}"}

    if not query.strip():
        return {"key": "key_contract", "score": 0.0, "comment": "embedding_query is empty"}

    return {"key": "key_contract", "score": 1.0, "comment": "input/output key contract valid"}


def concise_plain_query(run, example) -> dict:
    query = _get_query(_safe_get_outputs(run))
    if query is None:
        return {"key": "concise_plain_query", "score": 0.0, "comment": "embedding_query missing/non-string", "hard_rule_violated": False}

    issues = []
    hard = False
    if not _is_plain_one_line(query):
        issues.append("query_not_one_line")
        hard = True
    if _contains_any(query, BANNED_PATTERNS):
        issues.append("banned_or_internal_term_detected")
        hard = True
    if _has_sentence_preamble(query):
        issues.append("query_has_preamble_or_label")
        hard = True
    if query.strip().endswith("."):
        issues.append("query_ends_like_sentence")

    token_count = len(_query_tokens(query))
    if token_count < MIN_QUERY_TOKENS:
        issues.append(f"too_short:{token_count}_tokens")
    if token_count > MAX_QUERY_TOKENS:
        issues.append(f"too_long:{token_count}_tokens")
    if len(re.findall(r"[.!?;:]", query)) > 2:
        issues.append("too_much_sentence_punctuation")

    if hard:
        return {"key": "concise_plain_query", "score": 0.0, "comment": "; ".join(issues), "hard_rule_violated": True}
    if issues:
        extreme = token_count < 8 or token_count > 34
        return {"key": "concise_plain_query", "score": 0.0 if extreme else 0.5, "comment": "; ".join(issues), "hard_rule_violated": extreme}
    return {"key": "concise_plain_query", "score": 1.0, "comment": f"plain one-line query with {token_count} tokens", "hard_rule_violated": False}


def query_relevance(run, example) -> dict:
    out = _safe_get_outputs(run)
    ref = _safe_get_reference(example)
    inputs = _safe_get_inputs(example)
    query = _get_query(out)
    if query is None:
        return {"key": "query_relevance", "score": 0.0, "comment": "embedding_query missing/non-string"}

    source_title = str(inputs.get("source_title", ""))
    topic = str(inputs.get("topic", ""))
    gold = _get_gold_query(ref)
    q_tokens = _content_tokens(query)
    title_terms = _title_terms(source_title)
    topic_terms = _topic_terms(topic)

    title_overlap = len(title_terms & q_tokens) / max(1, len(title_terms))
    topic_overlap = len(topic_terms & q_tokens) / max(1, len(topic_terms))
    gold_overlap = _jaccard(query, gold) if gold else 0.0

    issues = []
    if title_terms and title_overlap < 0.25:
        issues.append(f"low_source_title_overlap={title_overlap:.2f}")
    if topic_terms and topic_overlap < 0.50:
        issues.append(f"low_topic_overlap={topic_overlap:.2f}")
    if gold and gold_overlap < 0.18:
        issues.append(f"low_gold_overlap={gold_overlap:.2f}")

    if not issues:
        return {"key": "query_relevance", "score": 1.0, "comment": f"relevant; title_overlap={title_overlap:.2f} topic_overlap={topic_overlap:.2f} gold_overlap={gold_overlap:.2f}"}

    hard = any(x.startswith("low_topic_overlap") for x in issues)
    return {"key": "query_relevance", "score": 0.0 if hard else 0.5, "comment": "; ".join(issues)}


def task_aware(run, example) -> dict:
    query = _get_query(_safe_get_outputs(run))
    inputs = _safe_get_inputs(example)
    if query is None:
        return {"key": "task_aware", "score": 0.0, "comment": "embedding_query missing/non-string"}
    task = _get_task(inputs)
    if task not in VALID_STUDIO_TASKS:
        return {"key": "task_aware", "score": 0.0, "comment": f"invalid studio_task={task!r}"}
    if _task_cue_present(task, query):
        return {"key": "task_aware", "score": 1.0, "comment": f"query includes task-aware cue for {task}"}
    return {"key": "task_aware", "score": 0.0, "comment": f"query lacks task-aware cue for studio_task={task}"}


def topic_coverage(run, example) -> dict:
    out = _safe_get_outputs(run)
    ref = _safe_get_reference(example)
    inputs = _safe_get_inputs(example)
    query = _get_query(out)
    if query is None:
        return {"key": "topic_coverage", "score": 0.0, "comment": "embedding_query missing/non-string"}

    source_title = str(inputs.get("source_title", ""))
    topic = str(inputs.get("topic", ""))
    gold = _get_gold_query(ref)
    q_tokens = _content_tokens(query)
    title_topic_terms = _title_terms(source_title) | _topic_terms(topic)
    task_terms = set().union(*TASK_CUES.values())
    expansion_terms = {t for t in q_tokens if t not in title_topic_terms and t not in GENERIC_WORDS and t not in task_terms}
    expected = _expected_expansion_terms(source_title, topic)
    expected_hit_count = len(expected & q_tokens)

    if expected:
        if expected_hit_count >= 4:
            return {"key": "topic_coverage", "score": 1.0, "comment": f"subject expansion sufficient; expected_hits={expected_hit_count}, expansion_terms={len(expansion_terms)}"}
        if expected_hit_count >= 2:
            return {"key": "topic_coverage", "score": 0.5, "comment": f"partial subject expansion; expected_hits={expected_hit_count}, expansion_terms={len(expansion_terms)}"}
        return {"key": "topic_coverage", "score": 0.0, "comment": f"weak subject expansion; expected_hits={expected_hit_count}, expansion_terms={sorted(expansion_terms)[:8]}"}

    if 4 <= len(expansion_terms) <= 14:
        return {"key": "topic_coverage", "score": 1.0, "comment": f"topic expansion acceptable; expansion_terms={len(expansion_terms)}"}
    if 2 <= len(expansion_terms) <= 18:
        return {"key": "topic_coverage", "score": 0.5, "comment": f"topic expansion partial; expansion_terms={len(expansion_terms)}"}
    gold_overlap = _jaccard(query, gold) if gold else 0.0
    if gold_overlap >= 0.25:
        return {"key": "topic_coverage", "score": 1.0, "comment": f"coverage acceptable via gold overlap={gold_overlap:.2f}"}
    return {"key": "topic_coverage", "score": 0.0, "comment": f"query appears too narrow/broad; expansion_terms={len(expansion_terms)} gold_overlap={gold_overlap:.2f}"}


def legacy_regression(run, example) -> dict:
    out = _safe_get_outputs(run)
    ref = _safe_get_reference(example)
    inputs = _safe_get_inputs(example)
    query = _get_query(out)
    if query is None:
        return {"key": "legacy_regression", "score": 0.0, "comment": "embedding_query missing/non-string", "hard_rule_violated": False}

    source_title = str(inputs.get("source_title", ""))
    topic = str(inputs.get("topic", ""))
    gold = _get_gold_query(ref)
    issues = []
    hard = False

    if source_title.strip() and topic.strip() and _jaccard(query, BROAD_DEFAULT_QUERY) > 0.75:
        issues.append("used_broad_default_despite_present_inputs")
        hard = True

    if _contains_any(query, {"studio_broad_retrieval_queries", "query rewriter", "retrieval_focus", "fallback prompt", "live studio", "dynamic embedding path"}):
        issues.append("leaks_implementation_or_live_path_details")
        hard = True

    if gold:
        gold_overlap = _jaccard(query, gold)
        if gold_overlap < 0.15:
            issues.append(f"low_gold_regression_overlap={gold_overlap:.2f}")

    if hard:
        return {"key": "legacy_regression", "score": 0.0, "comment": "; ".join(issues), "hard_rule_violated": True}
    if issues:
        return {"key": "legacy_regression", "score": 0.5, "comment": "; ".join(issues), "hard_rule_violated": False}
    return {"key": "legacy_regression", "score": 1.0, "comment": "legacy regression checks passed", "hard_rule_violated": False}


def studio_context_embedding_query_severity_summary(runs: list, examples: list) -> dict:
    if len(runs) != len(examples):
        return {"key": "studio_context_embedding_query_severity_summary", "score": 0.0, "comment": f"runs/examples length mismatch ({len(runs)} vs {len(examples)})", "ship_recommendation": "BLOCK"}

    tier_0 = []
    tier_1 = 0
    tier_1_applicable = 0
    variation_totals: dict[str, int] = {}
    variation_passes: dict[str, int] = {}

    for run, example in zip(runs, examples):
        variation = _safe_get_variation(example)
        variation_totals[variation] = variation_totals.get(variation, 0) + 1
        key_res = key_contract(run, example)
        if key_res["score"] == 0.0:
            tier_0.append({"example_id": getattr(example, "id", None), "reason": f"key_contract failed: {key_res['comment']}"})
            continue

        concise = concise_plain_query(run, example)
        relevance = query_relevance(run, example)
        aware = task_aware(run, example)
        coverage = topic_coverage(run, example)
        regression = legacy_regression(run, example)

        if concise.get("hard_rule_violated"):
            tier_0.append({"example_id": getattr(example, "id", None), "reason": f"concise_plain_query hard failure: {concise['comment']}"})
        if aware["score"] == 0.0:
            tier_0.append({"example_id": getattr(example, "id", None), "reason": f"task_aware failed: {aware['comment']}"})
        if relevance["score"] == 0.0 and "low_topic_overlap" in relevance["comment"]:
            tier_0.append({"example_id": getattr(example, "id", None), "reason": f"query_relevance hard failure: {relevance['comment']}"})
        if coverage["score"] == 0.0:
            tier_0.append({"example_id": getattr(example, "id", None), "reason": f"topic_coverage failed: {coverage['comment']}"})
        if regression.get("hard_rule_violated"):
            tier_0.append({"example_id": getattr(example, "id", None), "reason": f"legacy_regression hard failure: {regression['comment']}"})

        tier_1_applicable += 5
        for result in (concise, relevance, aware, coverage, regression):
            if result["score"] < 1.0:
                tier_1 += 1
        if all(r["score"] == 1.0 for r in (concise, relevance, aware, coverage, regression)):
            variation_passes[variation] = variation_passes.get(variation, 0) + 1

    tier_1_rate = (tier_1 / tier_1_applicable) if tier_1_applicable else 0.0
    per_variation_pass_rate = {v: round(variation_passes.get(v, 0) / total, 3) for v, total in variation_totals.items()}
    recommendation = "BLOCK" if tier_0 else ("REVIEW" if tier_1_rate > 0.18 else "OK")

    return {
        "key": "studio_context_embedding_query_severity_summary",
        "score": 0.0 if tier_0 else round(1.0 - tier_1_rate, 3),
        "comment": f"ship_recommendation={recommendation} | tier_0_blocking_count={len(tier_0)} | tier_1_review_rate={tier_1_rate:.3f}",
        "tier_0_blocking_count": len(tier_0),
        "tier_0_blocking_examples": tier_0,
        "tier_1_review_rate": round(tier_1_rate, 3),
        "per_variation_pass_rate": per_variation_pass_rate,
        "ship_recommendation": recommendation,
    }


PER_EXAMPLE_EVALUATORS = [
    key_contract,
    concise_plain_query,
    query_relevance,
    task_aware,
    topic_coverage,
    legacy_regression,
]

SUMMARY_EVALUATORS = [studio_context_embedding_query_severity_summary]
