"""
orchestration_flow_evaluators.py

LangSmith custom evaluators for ScholarSync production orchestration / agent-flow
regression tests.

Purpose
-------
Individual agent evaluators answer: "When this agent runs, did it produce the
right local output?"

This orchestration evaluator answers: "Did production route the request through
the right agent path, invoke the required agents, bypass the forbidden agents,
and preserve critical handoffs between agents?"

This is intentionally CODE-FIRST, not LLM/hybrid. The orchestration layer is a
routing/dependency problem, so the highest-value checks are deterministic:
route match, required/forbidden agent invocation, ordering, mutual exclusion,
bypass behavior, and handoff integrity.

Expected target function output
-------------------------------
Your LangSmith target_fn should return a dict containing either the trace fields
directly, or nested under `flow_trace` / `trace` / `orchestration_trace`.

Recommended minimal shape:

    {
        "final_route": "rag",  # or direct_chat, security_block,
                              # whole_file_map_reduce_success,
                              # whole_file_map_reduce_fallback,
                              # problem_solver, studio, ingestion, source_extraction
        "agents_invoked": ["intent_classifier", "scope_narrower", "query_rewriter"],
        "agents_bypassed": ["direct_chat", "whole_file_map_summarizer"],
        "route_events": ["intent_classified", "retrieval_started", "context_packed"],
        "flags": {"ENABLE_QUERY_DECOMPOSITION": true},
        "agent_inputs": {
            "query_rewriter": {"query": "..."},
            "query_decomposer": {"query": "..."}
        },
        "agent_outputs": {
            "scope_narrower": {"focused_query": "..."},
            "query_rewriter": {"queries": ["primary rewritten query", "variant"]}
        },
        "map_reduce_ok": false,
        "template_missing": false,
        "error": null
    }

Recommended example.outputs shape
---------------------------------
Keep gold outputs small and explicit. Only include what matters for that flow
case.

    {
        "expected_route": "direct_chat",
        "required_agents": ["direct_chat"],
        "forbidden_agents": ["scope_narrower", "query_rewriter",
                             "query_decomposer", "hallucination_guard_retry",
                             "whole_file_map_summarizer", "whole_file_reduce"],
        "expected_order": [["intent_classifier", "direct_chat"]],
        "expected_handoffs": {
            "rewriter_uses_scope_focused_query": false,
            "decomposer_uses_rewritten_queries_0": false
        }
    }

Evaluator registry
------------------
    from orchestration_flow_evaluators import PER_EXAMPLE_EVALUATORS, SUMMARY_EVALUATORS

    client.evaluate(
        target_fn,
        data="nbm-prompt-orchestration-flow",
        evaluators=PER_EXAMPLE_EVALUATORS,
        summary_evaluators=SUMMARY_EVALUATORS,
    )

Notes
-----
- This file has no external dependencies and performs no LLM calls.
- It does not evaluate answer quality. Agent #7 RAG answer quality should remain
  in retrieval/RAG golden-set evals.
- It is defensive: malformed traces score cleanly as failures instead of
  crashing the experiment.
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

# ---------------------------------------------------------------------------
# Canonical agent names and aliases
# ---------------------------------------------------------------------------

CANONICAL_AGENTS = {
    "intent_classifier",
    "query_rewriter",
    "query_decomposer",
    "scope_narrower",
    "chat_policy_block",
    "direct_chat",
    "chat_summarizer",
    "hallucination_guard_retry",
    "studio_system_json",
    "studio_quiz",
    "studio_flashcards",
    "studio_mind_map",
    "studio_slide_deck",
    "studio_fallback_legacy",
    "studio_context_embedding_query",
    "problem_dna_analyzer",
    "explain_from_basics",
    "show_best_approach",
    "show_missing_idea",
    "help_me_solve_it",
    "problem_solver_followup",
    "tutor_notebook_bootstrap",
    "tutor_follow_up_questions",
    "source_question_extraction",
    "document_sketch",
    "ncert_document_sketch",
    "chunk_contextualization",
    "whole_file_map_summarizer",
    "whole_file_reduce",
    "image_ocr",
    "diagram_label_ocr",
    "refusal_templates",
    # Production #7 is excluded from the 33-agent eval set, but a production
    # trace may still include it. We allow it here for orchestration checks.
    "rag_chat_response_generator",
    "generate",
    "retrieval",
    "embedding_search",
    "hybrid_search",
    "rerank",
    "context_pack",
    "moderation_input",
    "moderation_output",
    "dialog_route",
    "cache_check",
    "memory",
}

AGENT_ALIASES = {
    # numbers / labels
    "1": "intent_classifier",
    "#1": "intent_classifier",
    "intent": "intent_classifier",
    "intentclassify": "intent_classifier",
    "intent_classifier_agent": "intent_classifier",
    "2": "query_rewriter",
    "#2": "query_rewriter",
    "rewriter": "query_rewriter",
    "queryrewriter": "query_rewriter",
    "3": "query_decomposer",
    "#3": "query_decomposer",
    "decomposer": "query_decomposer",
    "querydecomposer": "query_decomposer",
    "4": "scope_narrower",
    "#4": "scope_narrower",
    "scope": "scope_narrower",
    "scopenarrower": "scope_narrower",
    "5": "chat_policy_block",
    "#5": "chat_policy_block",
    "policy": "chat_policy_block",
    "6": "direct_chat",
    "#6": "direct_chat",
    "directchat": "direct_chat",
    "7": "rag_chat_response_generator",
    "#7": "rag_chat_response_generator",
    "rag": "rag_chat_response_generator",
    "rag_generator": "rag_chat_response_generator",
    "rag_chat": "rag_chat_response_generator",
    "8": "chat_summarizer",
    "#8": "chat_summarizer",
    "summarizer": "chat_summarizer",
    "9": "hallucination_guard_retry",
    "#9": "hallucination_guard_retry",
    "hallucination_guard": "hallucination_guard_retry",
    "10": "studio_system_json",
    "#10": "studio_system_json",
    "11": "studio_quiz",
    "#11": "studio_quiz",
    "quiz": "studio_quiz",
    "12": "studio_flashcards",
    "#12": "studio_flashcards",
    "flashcards": "studio_flashcards",
    "13": "studio_mind_map",
    "#13": "studio_mind_map",
    "mind_map": "studio_mind_map",
    "14": "studio_slide_deck",
    "#14": "studio_slide_deck",
    "slide_deck": "studio_slide_deck",
    "15": "studio_fallback_legacy",
    "#15": "studio_fallback_legacy",
    "16": "studio_context_embedding_query",
    "#16": "studio_context_embedding_query",
    "17": "problem_dna_analyzer",
    "#17": "problem_dna_analyzer",
    "dna": "problem_dna_analyzer",
    "problem_dna": "problem_dna_analyzer",
    "18": "explain_from_basics",
    "#18": "explain_from_basics",
    "19": "show_best_approach",
    "#19": "show_best_approach",
    "20": "show_missing_idea",
    "#20": "show_missing_idea",
    "21": "help_me_solve_it",
    "#21": "help_me_solve_it",
    "22": "problem_solver_followup",
    "#22": "problem_solver_followup",
    "23": "tutor_notebook_bootstrap",
    "#23": "tutor_notebook_bootstrap",
    "24": "tutor_follow_up_questions",
    "#24": "tutor_follow_up_questions",
    "25": "source_question_extraction",
    "#25": "source_question_extraction",
    "26": "document_sketch",
    "#26": "document_sketch",
    "27": "ncert_document_sketch",
    "#27": "ncert_document_sketch",
    "28": "chunk_contextualization",
    "#28": "chunk_contextualization",
    "29": "whole_file_map_summarizer",
    "#29": "whole_file_map_summarizer",
    "map": "whole_file_map_summarizer",
    "whole_file_map": "whole_file_map_summarizer",
    "30": "whole_file_reduce",
    "#30": "whole_file_reduce",
    "reduce": "whole_file_reduce",
    "whole_file_reduce_agent": "whole_file_reduce",
    "32": "image_ocr",
    "#32": "image_ocr",
    "33": "diagram_label_ocr",
    "#33": "diagram_label_ocr",
    "34": "refusal_templates",
    "#34": "refusal_templates",
    "refusal": "refusal_templates",
}

VALID_ROUTES = {
    "cache_hit",
    "moderation_block",
    "security_block",
    "direct_chat",
    "standard_rag",
    "rag",
    "whole_file_map_reduce_success",
    "whole_file_map_reduce_fallback",
    "studio",
    "problem_solver",
    "problem_solver_followup",
    "tutor_bootstrap",
    "tutor_followup",
    "source_question_extraction",
    "ingestion",
    "ocr",
    "refusal",
}

RETRIEVAL_STACK = {
    "scope_narrower",
    "query_rewriter",
    "query_decomposer",
    "retrieval",
    "embedding_search",
    "hybrid_search",
    "rerank",
    "context_pack",
}

RAG_STACK = RETRIEVAL_STACK | {"rag_chat_response_generator", "generate", "hallucination_guard_retry"}
MAP_REDUCE_STACK = {"whole_file_map_summarizer", "whole_file_reduce"}
STUDIO_GENERATORS = {"studio_quiz", "studio_flashcards", "studio_mind_map", "studio_slide_deck"}
PROBLEM_COACHES = {"explain_from_basics", "show_best_approach", "show_missing_idea", "help_me_solve_it"}

# ---------------------------------------------------------------------------
# Safe extraction helpers
# ---------------------------------------------------------------------------

def _get_attr_or_item(obj: Any, key: str, default: Any = None) -> Any:
    try:
        if isinstance(obj, dict):
            return obj.get(key, default)
        return getattr(obj, key, default)
    except Exception:
        return default


def _safe_get_outputs(run: Any) -> Optional[dict]:
    try:
        out = _get_attr_or_item(run, "outputs")
        if isinstance(out, dict):
            return out
        return None
    except Exception:
        return None


def _safe_get_inputs(run_or_example: Any) -> dict:
    try:
        inputs = _get_attr_or_item(run_or_example, "inputs", {})
        return inputs if isinstance(inputs, dict) else {}
    except Exception:
        return {}


def _safe_get_reference(example: Any) -> dict:
    try:
        ref = _get_attr_or_item(example, "outputs", {})
        return ref if isinstance(ref, dict) else {}
    except Exception:
        return {}


def _safe_get_metadata(example: Any) -> dict:
    try:
        meta = _get_attr_or_item(example, "metadata", {})
        return meta if isinstance(meta, dict) else {}
    except Exception:
        return {}


def _example_id(example: Any) -> Optional[str]:
    return _get_attr_or_item(example, "id", None) or _get_attr_or_item(example, "name", None)


def parse_model_response_to_outputs(raw_text: str) -> dict:
    """Parse raw model/orchestrator JSON text into a dict for LangSmith outputs.

    This is optional helper code for your target_fn. LangSmith run.outputs should
    ultimately be a dict. On parse failure, returns {} so schema evaluators fail
    cleanly rather than crashing.
    """
    if not isinstance(raw_text, str) or not raw_text.strip():
        return {}
    text = raw_text.strip()
    fence_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fence_match:
        text = fence_match.group(1)
    else:
        brace_match = re.search(r"\{.*\}", text, re.DOTALL)
        if brace_match:
            text = brace_match.group(0)
    try:
        parsed = json.loads(text)
    except Exception:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _extract_trace(outputs: Optional[dict]) -> Optional[dict]:
    if not isinstance(outputs, dict):
        return None
    for key in ("flow_trace", "trace", "orchestration_trace", "route_trace"):
        nested = outputs.get(key)
        if isinstance(nested, dict):
            return nested
    return outputs


def _normalize_token(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip().lower()
    text = text.replace("-", "_").replace(" ", "_").replace(".", "_")
    text = re.sub(r"[^a-z0-9_#]+", "", text)
    text = re.sub(r"_+", "_", text).strip("_")
    return AGENT_ALIASES.get(text, text)


def _normalize_agent(value: Any) -> str:
    token = _normalize_token(value)
    return AGENT_ALIASES.get(token, token)


def _as_list(value: Any) -> list:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    if isinstance(value, set):
        return list(value)
    return [value]


def _agent_name_from_event(event: Any) -> Optional[str]:
    if isinstance(event, str):
        return _normalize_agent(event)
    if isinstance(event, dict):
        for key in ("agent", "agent_id", "name", "node", "step", "run_name", "dataset_id"):
            if key in event:
                return _normalize_agent(event[key])
    return None


def _extract_invoked_agents(trace: dict, run: Any = None) -> List[str]:
    raw: list = []
    for key in ("agents_invoked", "invoked_agents", "agent_sequence", "nodes_visited", "steps"):
        raw.extend(_as_list(trace.get(key)))

    # route_events may contain explicit agent entries; include only recognized agents.
    for event in _as_list(trace.get("route_events")):
        name = _agent_name_from_event(event)
        if name:
            raw.append(name)

    # Optional: LangSmith child runs can also reveal agent/node names.
    child_runs = _get_attr_or_item(run, "child_runs", []) if run is not None else []
    for child in _as_list(child_runs):
        for key in ("name", "run_name", "serialized"):
            val = _get_attr_or_item(child, key, None)
            if isinstance(val, dict):
                val = val.get("name") or val.get("id")
            if val:
                raw.append(val)
                break

    normalized: List[str] = []
    seen = set()
    for item in raw:
        name = _agent_name_from_event(item)
        if not name:
            continue
        if name in CANONICAL_AGENTS or name in AGENT_ALIASES.values():
            name = _normalize_agent(name)
            if name and name not in seen:
                normalized.append(name)
                seen.add(name)
    return normalized


def _extract_bypassed_agents(trace: dict) -> List[str]:
    raw = []
    for key in ("agents_bypassed", "bypassed_agents", "skipped_agents", "agents_skipped"):
        raw.extend(_as_list(trace.get(key)))
    normalized = []
    seen = set()
    for item in raw:
        name = _normalize_agent(item)
        if name and name not in seen:
            normalized.append(name)
            seen.add(name)
    return normalized


def _get_route(trace: dict) -> str:
    for key in ("final_route", "route", "selected_route", "path", "terminal_path"):
        val = trace.get(key)
        if isinstance(val, str) and val.strip():
            route = _normalize_token(val)
            # Normalize common route aliases.
            aliases = {
                "rag_chat": "standard_rag",
                "retrieval_rag": "standard_rag",
                "standard_retrieval": "standard_rag",
                "whole_file_map_reduce": "whole_file_map_reduce_success"
                if trace.get("map_reduce_ok") is True else "whole_file_map_reduce_fallback",
                "map_reduce_success": "whole_file_map_reduce_success",
                "map_reduce_fallback": "whole_file_map_reduce_fallback",
                "problem": "problem_solver",
                "ps": "problem_solver",
            }
            return aliases.get(route, route)
    return ""


def _word_set(text: Any) -> set[str]:
    if not isinstance(text, str):
        return set()
    return {t for t in re.findall(r"[a-z0-9]+", text.lower()) if len(t) > 1}


def _jaccard(a: Any, b: Any) -> float:
    sa, sb = _word_set(a), _word_set(b)
    if not sa and not sb:
        return 1.0
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / max(1, len(sa | sb))


def _get_agent_inputs(trace: dict, agent: str) -> dict:
    agent = _normalize_agent(agent)
    all_inputs = trace.get("agent_inputs") or trace.get("inputs_by_agent") or {}
    if isinstance(all_inputs, dict):
        for key, value in all_inputs.items():
            if _normalize_agent(key) == agent and isinstance(value, dict):
                return value
    # Also support flattened keys like query_decomposer_input.
    for key in (f"{agent}_input", f"{agent}_inputs"):
        value = trace.get(key)
        if isinstance(value, dict):
            return value
    return {}


def _get_agent_outputs(trace: dict, agent: str) -> dict:
    agent = _normalize_agent(agent)
    all_outputs = trace.get("agent_outputs") or trace.get("outputs_by_agent") or {}
    if isinstance(all_outputs, dict):
        for key, value in all_outputs.items():
            if _normalize_agent(key) == agent and isinstance(value, dict):
                return value
    for key in (f"{agent}_output", f"{agent}_outputs"):
        value = trace.get(key)
        if isinstance(value, dict):
            return value
    return {}


def _expected_list(ref: dict, key: str) -> List[str]:
    return [_normalize_agent(x) for x in _as_list(ref.get(key)) if _normalize_agent(x)]


def _order_index(invoked: Sequence[str], agent: str) -> Optional[int]:
    agent = _normalize_agent(agent)
    try:
        return list(invoked).index(agent)
    except ValueError:
        return None


def _check_order_pair(invoked: Sequence[str], before: str, after: str) -> Tuple[bool, str]:
    before_n = _normalize_agent(before)
    after_n = _normalize_agent(after)
    i = _order_index(invoked, before_n)
    j = _order_index(invoked, after_n)
    if i is None or j is None:
        return True, f"order pair skipped because one/both agents absent: {before_n}->{after_n}"
    if i < j:
        return True, f"order ok: {before_n} before {after_n}"
    return False, f"order violation: {before_n} index={i} should be before {after_n} index={j}"


def _expected_order_pairs(ref: dict) -> List[Tuple[str, str]]:
    raw = ref.get("expected_order") or ref.get("required_order") or []
    pairs: List[Tuple[str, str]] = []
    for item in _as_list(raw):
        if isinstance(item, (list, tuple)):
            if len(item) == 2:
                pairs.append((_normalize_agent(item[0]), _normalize_agent(item[1])))
            elif len(item) > 2:
                seq = [_normalize_agent(x) for x in item if _normalize_agent(x)]
                pairs.extend(list(zip(seq, seq[1:])))
        elif isinstance(item, str) and ">" in item:
            seq = [_normalize_agent(x) for x in item.split(">") if _normalize_agent(x)]
            pairs.extend(list(zip(seq, seq[1:])))
    return pairs

# ---------------------------------------------------------------------------
# Evaluator 1: trace_schema_validity
# ---------------------------------------------------------------------------

def trace_schema_validity(run: Any, example: Any) -> dict:
    """Basic structural gate for orchestration traces."""
    outputs = _safe_get_outputs(run)
    trace = _extract_trace(outputs)
    if trace is None:
        return {
            "key": "trace_schema_validity",
            "score": 0.0,
            "comment": "run.outputs missing or not a dict/trace dict",
        }

    route = _get_route(trace)
    invoked = _extract_invoked_agents(trace, run)
    bypassed = _extract_bypassed_agents(trace)

    if not route:
        return {
            "key": "trace_schema_validity",
            "score": 0.0,
            "comment": "missing final_route/route/path in trace",
        }

    if not isinstance(invoked, list):
        return {
            "key": "trace_schema_validity",
            "score": 0.0,
            "comment": "agents_invoked could not be parsed as list",
        }

    if not invoked and route not in {"cache_hit", "moderation_block"}:
        return {
            "key": "trace_schema_validity",
            "score": 0.0,
            "comment": "agents_invoked empty for non-terminal cached/moderation route",
        }

    unknown = [a for a in invoked + bypassed if a not in CANONICAL_AGENTS]
    if unknown:
        return {
            "key": "trace_schema_validity",
            "score": 0.5,
            "comment": f"trace parsed but contains unknown agent labels: {sorted(set(unknown))}",
        }

    return {
        "key": "trace_schema_validity",
        "score": 1.0,
        "comment": f"trace ok route={route!r} invoked={invoked}",
    }

# ---------------------------------------------------------------------------
# Evaluator 2: route_match
# ---------------------------------------------------------------------------

def route_match(run: Any, example: Any) -> dict:
    """Exact route/path match against example.outputs['expected_route'] when provided."""
    outputs = _safe_get_outputs(run)
    trace = _extract_trace(outputs)
    ref = _safe_get_reference(example)
    if trace is None:
        return {"key": "route_match", "score": 0.0, "comment": "missing trace"}

    expected = ref.get("expected_route") or ref.get("route") or ref.get("expected_path")
    if not expected:
        return {"key": "route_match", "score": 1.0, "comment": "no expected_route provided; neutral pass"}

    predicted = _get_route(trace)
    expected_norm = _normalize_token(expected)
    route_aliases = {
        "retrieval_rag": "standard_rag",
        "rag": "standard_rag",
        "rag_chat": "standard_rag",
        "map_reduce_success": "whole_file_map_reduce_success",
        "map_reduce_fallback": "whole_file_map_reduce_fallback",
    }
    predicted_norm = route_aliases.get(predicted, predicted)
    expected_norm = route_aliases.get(expected_norm, expected_norm)

    match = predicted_norm == expected_norm
    return {
        "key": "route_match",
        "score": 1.0 if match else 0.0,
        "comment": f"predicted_route={predicted_norm!r} expected_route={expected_norm!r}",
    }

# ---------------------------------------------------------------------------
# Evaluator 3: agent_invocation_contract
# ---------------------------------------------------------------------------

def agent_invocation_contract(run: Any, example: Any) -> dict:
    """Checks required/forbidden agents plus built-in bypass expectations."""
    outputs = _safe_get_outputs(run)
    trace = _extract_trace(outputs)
    ref = _safe_get_reference(example)
    if trace is None:
        return {"key": "agent_invocation_contract", "score": 0.0, "comment": "missing trace"}

    route = _get_route(trace)
    invoked = set(_extract_invoked_agents(trace, run))

    required = set(_expected_list(ref, "required_agents"))
    forbidden = set(_expected_list(ref, "forbidden_agents"))

    # Built-in route contracts. These are intentionally conservative and can
    # be overridden/augmented with explicit required_agents/forbidden_agents.
    if route in {"direct_chat"}:
        required.add("direct_chat")
        forbidden.update(RETRIEVAL_STACK | MAP_REDUCE_STACK | {"rag_chat_response_generator", "hallucination_guard_retry"})
    elif route in {"security_block", "refusal", "moderation_block"}:
        required.add("refusal_templates")
        forbidden.update(RETRIEVAL_STACK | MAP_REDUCE_STACK | {"rag_chat_response_generator", "hallucination_guard_retry", "direct_chat"})
    elif route == "whole_file_map_reduce_success":
        required.update({"whole_file_map_summarizer", "whole_file_reduce"})
        forbidden.update(RETRIEVAL_STACK | {"hallucination_guard_retry"})
    elif route == "whole_file_map_reduce_fallback":
        required.add("whole_file_map_summarizer")
        # Retrieval may proceed after fallback; do not forbid retrieval stack.
    elif route == "studio":
        required.add("studio_system_json")
        forbidden.add("studio_context_embedding_query")  # legacy always bypassed in production
        if not trace.get("template_missing"):
            forbidden.add("studio_fallback_legacy")
    elif route == "problem_solver":
        required.add("problem_dna_analyzer")
    elif route == "problem_solver_followup":
        required.update({"problem_dna_analyzer", "problem_solver_followup"})
    elif route == "tutor_bootstrap":
        required.add("tutor_notebook_bootstrap")
    elif route == "tutor_followup":
        required.add("tutor_follow_up_questions")
    elif route == "source_question_extraction":
        required.add("source_question_extraction")

    missing = sorted(a for a in required if a not in invoked)
    wrongly_invoked = sorted(a for a in forbidden if a in invoked)

    score = 1.0
    comments = []
    if missing:
        score = 0.0
        comments.append(f"missing_required={missing}")
    if wrongly_invoked:
        score = 0.0
        comments.append(f"forbidden_invoked={wrongly_invoked}")

    if not comments:
        comments.append("required/forbidden agent contract satisfied")

    return {
        "key": "agent_invocation_contract",
        "score": score,
        "comment": " | ".join(comments),
    }

# ---------------------------------------------------------------------------
# Evaluator 4: dependency_and_order_integrity
# ---------------------------------------------------------------------------

def dependency_and_order_integrity(run: Any, example: Any) -> dict:
    """Checks hard dependencies, ordering, and mutual exclusion constraints."""
    outputs = _safe_get_outputs(run)
    trace = _extract_trace(outputs)
    ref = _safe_get_reference(example)
    if trace is None:
        return {"key": "dependency_and_order_integrity", "score": 0.0, "comment": "missing trace"}

    invoked = _extract_invoked_agents(trace, run)
    invoked_set = set(invoked)
    failures: List[str] = []
    warnings: List[str] = []

    # Built-in production order checks when both agents appear.
    built_in_pairs = [
        ("scope_narrower", "query_rewriter"),
        ("query_rewriter", "query_decomposer"),
        ("whole_file_map_summarizer", "whole_file_reduce"),
        ("problem_dna_analyzer", "explain_from_basics"),
        ("problem_dna_analyzer", "show_best_approach"),
        ("problem_dna_analyzer", "show_missing_idea"),
        ("problem_dna_analyzer", "help_me_solve_it"),
        ("problem_dna_analyzer", "problem_solver_followup"),
        ("studio_system_json", "studio_quiz"),
        ("studio_system_json", "studio_flashcards"),
        ("studio_system_json", "studio_mind_map"),
        ("studio_system_json", "studio_slide_deck"),
    ]

    for before, after in built_in_pairs + _expected_order_pairs(ref):
        ok, comment = _check_order_pair(invoked, before, after)
        if not ok:
            failures.append(comment)

    # Hard dependency: reduce cannot run without map.
    if "whole_file_reduce" in invoked_set and "whole_file_map_summarizer" not in invoked_set:
        failures.append("whole_file_reduce ran without whole_file_map_summarizer")

    # Hard dependency: problem coach cannot run without DNA.
    active_coaches = sorted(PROBLEM_COACHES & invoked_set)
    if active_coaches and "problem_dna_analyzer" not in invoked_set:
        failures.append(f"problem coach ran without problem_dna_analyzer: {active_coaches}")

    # Mutual exclusion: only one coach mode per primary problem response.
    if len(active_coaches) > 1:
        failures.append(f"multiple mutually-exclusive problem coach modes ran: {active_coaches}")

    # Mutual exclusion: direct chat and RAG/map-reduce terminal paths should not both run.
    if "direct_chat" in invoked_set and (RAG_STACK & invoked_set or MAP_REDUCE_STACK & invoked_set):
        failures.append("direct_chat ran together with RAG/retrieval/map-reduce stack")

    # Studio: exactly one primary Studio generator when a Studio request runs.
    active_studio_generators = sorted(STUDIO_GENERATORS & invoked_set)
    if "studio_system_json" in invoked_set and len(active_studio_generators) == 0:
        warnings.append("studio_system_json ran but no primary studio generator recorded")
    if len(active_studio_generators) > 1:
        failures.append(f"multiple Studio generators ran in one request: {active_studio_generators}")

    if failures:
        return {
            "key": "dependency_and_order_integrity",
            "score": 0.0,
            "comment": " | ".join(failures),
            "warnings": warnings,
        }

    return {
        "key": "dependency_and_order_integrity",
        "score": 0.5 if warnings else 1.0,
        "comment": "dependencies/order ok" if not warnings else " | ".join(warnings),
        "warnings": warnings,
    }

# ---------------------------------------------------------------------------
# Evaluator 5: critical_handoff_integrity
# ---------------------------------------------------------------------------

def critical_handoff_integrity(run: Any, example: Any) -> dict:
    """Checks specific handoffs between agents when trace data is available.

    This is where we enforce production-sensitive transitions such as:
    - Query Rewriter should use Scope Narrower's focused_query when provided.
    - Query Decomposer should receive rewritten_queries[0], not all rewrites or
      the raw/original query, when decomposition is enabled and upstream rewrites exist.
    """
    outputs = _safe_get_outputs(run)
    trace = _extract_trace(outputs)
    ref = _safe_get_reference(example)
    if trace is None:
        return {"key": "critical_handoff_integrity", "score": 0.0, "comment": "missing trace"}

    invoked = set(_extract_invoked_agents(trace, run))
    flags = trace.get("flags") if isinstance(trace.get("flags"), dict) else {}
    expected_handoffs = ref.get("expected_handoffs") if isinstance(ref.get("expected_handoffs"), dict) else {}

    failures: List[str] = []
    warnings: List[str] = []

    # Handoff 4 -> 2: Scope focused_query may be fed to Rewriter.
    check_rewriter_scope = expected_handoffs.get("rewriter_uses_scope_focused_query")
    if check_rewriter_scope is True or ("scope_narrower" in invoked and "query_rewriter" in invoked):
        scope_out = _get_agent_outputs(trace, "scope_narrower")
        rewriter_in = _get_agent_inputs(trace, "query_rewriter")
        focused = scope_out.get("focused_query") or trace.get("focused_query")
        rewriter_query = rewriter_in.get("query") or rewriter_in.get("focused_query")
        if focused and rewriter_query:
            if _jaccard(focused, rewriter_query) < 0.35:
                failures.append("query_rewriter input does not match/overlap scope_narrower.focused_query")
        elif check_rewriter_scope is True:
            failures.append("missing trace fields for required rewriter_uses_scope_focused_query handoff")
        else:
            warnings.append("scope->rewriter handoff not fully traceable")

    # Handoff 2 -> 3: Decomposer must use rewritten_queries[0].
    decomposition_enabled = bool(
        flags.get("ENABLE_QUERY_DECOMPOSITION")
        or flags.get("enable_query_decomposition")
        or trace.get("ENABLE_QUERY_DECOMPOSITION")
        or trace.get("enable_query_decomposition")
        or expected_handoffs.get("decomposer_uses_rewritten_queries_0") is True
    )

    if "query_decomposer" in invoked and (decomposition_enabled or "query_rewriter" in invoked):
        rewriter_out = _get_agent_outputs(trace, "query_rewriter")
        rewritten_queries = (
            rewriter_out.get("queries")
            or trace.get("rewritten_queries")
            or trace.get("queries")
            or []
        )
        decomposer_in = _get_agent_inputs(trace, "query_decomposer")
        decomposer_query = decomposer_in.get("query") or trace.get("decomposer_input_query")

        if isinstance(rewritten_queries, list) and rewritten_queries and isinstance(rewritten_queries[0], str):
            primary_rewrite = rewritten_queries[0]
            if not decomposer_query:
                failures.append("query_decomposer input query missing; cannot verify rewritten_queries[0] handoff")
            elif _jaccard(decomposer_query, primary_rewrite) < 0.35:
                failures.append(
                    "query_decomposer did not use rewritten_queries[0] as input "
                    f"(low overlap: decomposer_query={decomposer_query!r}, primary_rewrite={primary_rewrite!r})"
                )
        elif expected_handoffs.get("decomposer_uses_rewritten_queries_0") is True:
            failures.append("missing query_rewriter.queries; cannot verify decomposer_uses_rewritten_queries_0")
        else:
            warnings.append("rewriter->decomposer handoff not fully traceable")

    # Map-reduce handoff #29 -> #30.
    if "whole_file_reduce" in invoked:
        map_out = _get_agent_outputs(trace, "whole_file_map_summarizer")
        reduce_in = _get_agent_inputs(trace, "whole_file_reduce")
        map_summaries = map_out.get("map_summaries") or trace.get("map_summaries")
        section_summaries = reduce_in.get("section_summaries") or reduce_in.get("map_summaries")
        if map_summaries is not None and section_summaries is not None:
            # Use len/text overlap loosely because summaries may be concatenated.
            if isinstance(map_summaries, list):
                map_text = " ".join(str(x) for x in map_summaries)
            else:
                map_text = str(map_summaries)
            section_text = " ".join(str(x) for x in section_summaries) if isinstance(section_summaries, list) else str(section_summaries)
            if _jaccard(map_text, section_text) < 0.10 and len(_word_set(map_text)) >= 5:
                failures.append("whole_file_reduce input does not appear to contain map summaries")
        else:
            warnings.append("map->reduce handoff not fully traceable")

    if failures:
        return {
            "key": "critical_handoff_integrity",
            "score": 0.0,
            "comment": " | ".join(failures),
            "warnings": warnings,
        }

    return {
        "key": "critical_handoff_integrity",
        "score": 0.5 if warnings else 1.0,
        "comment": "handoffs ok" if not warnings else " | ".join(warnings),
        "warnings": warnings,
    }

# ---------------------------------------------------------------------------
# Summary evaluator: severity rollup
# ---------------------------------------------------------------------------

def orchestration_severity_summary(runs: list, examples: list) -> dict:
    """Rolls the full experiment into a production-readiness recommendation."""
    if len(runs) != len(examples):
        return {
            "key": "orchestration_severity_summary",
            "score": 0.0,
            "comment": f"runs/examples length mismatch ({len(runs)} vs {len(examples)}) -- BLOCK",
            "ship_recommendation": "BLOCK",
        }

    tier_0_hits: List[dict] = []
    tier_1_hits: List[dict] = []
    scenario_totals: Dict[str, int] = {}
    scenario_passes: Dict[str, int] = {}

    for run, example in zip(runs, examples):
        meta = _safe_get_metadata(example)
        ref = _safe_get_reference(example)
        scenario = str(meta.get("scenario") or meta.get("variation") or ref.get("expected_route") or "unknown")
        scenario_totals[scenario] = scenario_totals.get(scenario, 0) + 1

        checks = [
            trace_schema_validity(run, example),
            route_match(run, example),
            agent_invocation_contract(run, example),
            dependency_and_order_integrity(run, example),
            critical_handoff_integrity(run, example),
        ]

        # Tier 0: any hard 0 on schema, route, invocation, dependencies.
        hard_fail_keys = {
            "trace_schema_validity",
            "route_match",
            "agent_invocation_contract",
            "dependency_and_order_integrity",
        }
        example_tier0 = []
        example_tier1 = []
        for result in checks:
            key = result.get("key")
            score = result.get("score")
            if key in hard_fail_keys and score == 0.0:
                example_tier0.append({"key": key, "comment": result.get("comment")})
            elif key == "critical_handoff_integrity" and score == 0.0:
                # Handoff failures are Tier 0 only when explicitly required by the gold example
                # or when they involve decomposer using the wrong primary rewrite.
                comment = str(result.get("comment", ""))
                expected_handoffs = ref.get("expected_handoffs") if isinstance(ref.get("expected_handoffs"), dict) else {}
                if expected_handoffs or "query_decomposer did not use rewritten_queries[0]" in comment:
                    example_tier0.append({"key": key, "comment": comment})
                else:
                    example_tier1.append({"key": key, "comment": comment})
            elif score == 0.5:
                example_tier1.append({"key": key, "comment": result.get("comment")})

        if example_tier0:
            tier_0_hits.append({
                "example_id": _example_id(example),
                "scenario": scenario,
                "failures": example_tier0,
            })
        elif example_tier1:
            tier_1_hits.append({
                "example_id": _example_id(example),
                "scenario": scenario,
                "warnings": example_tier1,
            })
        else:
            scenario_passes[scenario] = scenario_passes.get(scenario, 0) + 1

    total = max(1, len(examples))
    tier_1_rate = len(tier_1_hits) / total
    per_scenario_pass_rate = {
        scenario: round(scenario_passes.get(scenario, 0) / count, 3)
        for scenario, count in scenario_totals.items()
    }

    if tier_0_hits:
        recommendation = "BLOCK"
    elif tier_1_rate > 0.10:
        recommendation = "REVIEW"
    else:
        recommendation = "OK"

    return {
        "key": "orchestration_severity_summary",
        "score": 0.0 if tier_0_hits else round(1.0 - tier_1_rate, 3),
        "comment": (
            f"ship_recommendation={recommendation} | "
            f"tier_0_blocking_count={len(tier_0_hits)} | "
            f"tier_1_warning_rate={tier_1_rate:.3f}"
        ),
        "tier_0_blocking_count": len(tier_0_hits),
        "tier_0_blocking_examples": tier_0_hits,
        "tier_1_warning_count": len(tier_1_hits),
        "tier_1_warning_examples": tier_1_hits,
        "per_scenario_pass_rate": per_scenario_pass_rate,
        "ship_recommendation": recommendation,
    }

# ---------------------------------------------------------------------------
# Public registry
# ---------------------------------------------------------------------------

PER_EXAMPLE_EVALUATORS = [
    trace_schema_validity,
    route_match,
    agent_invocation_contract,
    dependency_and_order_integrity,
    critical_handoff_integrity,
]

SUMMARY_EVALUATORS = [
    orchestration_severity_summary,
]
