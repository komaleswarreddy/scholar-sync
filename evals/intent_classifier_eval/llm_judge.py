"""Additive LLM-as-judge for intent classifier routing (never overrides deterministic scores)."""

from __future__ import annotations

import json
import logging
import os
import re
from typing import Any

from evals.intent_classifier_eval.config import JUDGE_MODEL, get_langsmith_project
from evals.intent_classifier_eval.providers import call_model

logger = logging.getLogger(__name__)


def _tracing_on() -> bool:
    return (
        os.environ.get("LANGSMITH_TRACING_ENABLED", "").lower() in ("1", "true", "yes")
        or os.environ.get("LANGCHAIN_TRACING_V2", "").lower() in ("1", "true", "yes")
    )


def _judge_llm_call(system: str, user: str) -> str:
    """Call the judge model and post its full prompt+response as a viewable LLM run.

    Unlike a @traceable child (which LangSmith drops when run inside an
    evaluator context), this creates an explicit RunTree posted to the project,
    so the judge's system/user prompt and raw JSON reply are inspectable in the
    LangSmith UI (Tracing -> project -> 'llm_routing_judge/<model>').
    """
    if not _tracing_on():
        return call_model(
            provider="openai", model=JUDGE_MODEL, system=system, user=user,
            temperature=0.0, max_tokens=200,
        )

    run_tree = None
    try:
        from langsmith.run_trees import RunTree

        run_tree = RunTree(
            name=f"llm_routing_judge/{JUDGE_MODEL}",
            run_type="llm",
            inputs={
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ]
            },
            project_name=get_langsmith_project(),
            extra={"metadata": {"ls_provider": "openai", "ls_model_name": JUDGE_MODEL}},
        )
        run_tree.post()
    except Exception as exc:  # tracing is best-effort, never break scoring
        logger.debug("judge RunTree.post failed: %s", exc)
        run_tree = None

    result = call_model(
        provider="openai", model=JUDGE_MODEL, system=system, user=user,
        temperature=0.0, max_tokens=200, return_usage=True,
    )
    raw = result.get("text", "") if isinstance(result, dict) else str(result or "")
    usage = result.get("usage", {}) if isinstance(result, dict) else {}

    if run_tree is not None:
        try:
            pt = int(usage.get("prompt_tokens") or 0)
            ct = int(usage.get("completion_tokens") or 0)
            run_tree.end(outputs={"output": raw, "usage": usage})
            try:
                run_tree.set(
                    usage_metadata={
                        "input_tokens": pt,
                        "output_tokens": ct,
                        "total_tokens": pt + ct,
                    }
                )
            except Exception:
                pass
            run_tree.patch()
        except Exception as exc:
            logger.debug("judge RunTree.patch failed: %s", exc)

    return raw

_JUDGE_SYSTEM = """You are an expert evaluator for an educational intent-routing agent.
Score the model's routing JSON holistically on a 0.0–1.0 scale.

Dimensions (weight equally):
1. Routing correctness — intent, scope, requires_retrieval, requires_attachment vs gold reference
2. Contract adherence — valid 6-field JSON (intent, scope, requires_retrieval, requires_attachment, confidence, reasoning)
3. Reasoning quality — short, accurate justification (≤40 words)

Return ONLY JSON:
{"score": 0.0-1.0, "comment": "one sentence"}
Be strict on security_block false negatives and curriculum-collision false positives.
"""

_JUDGE_USER = """User query: {query}

Gold reference:
{reference}

Model output:
{prediction}

Score the model output vs gold reference.
"""


def routing_judge(run: Any, example: Any) -> dict:
    """
    LangSmith per-example evaluator. Additive only — does not gate shipping.
    Never raises.
    """
    try:
        outputs = getattr(run, "outputs", None) or {}
        reference = getattr(example, "outputs", None) or {}
        inputs = getattr(example, "inputs", None) or {}
        query = inputs.get("query", "")

        raw = _judge_llm_call(
            system=_JUDGE_SYSTEM,
            user=_JUDGE_USER.format(
                query=query,
                reference=json.dumps(reference, ensure_ascii=False),
                prediction=json.dumps(outputs, ensure_ascii=False),
            ),
        )
        if not raw:
            return {
                "key": "llm_routing_judge",
                "score": 0.0,
                "comment": "judge unavailable (empty response)",
            }

        parsed = _parse_judge_json(raw)
        score = float(parsed.get("score", 0.0))
        score = max(0.0, min(1.0, score))
        return {
            "key": "llm_routing_judge",
            "score": round(score, 3),
            "comment": str(parsed.get("comment", ""))[:500],
        }
    except Exception as exc:
        logger.warning("routing_judge failed: %s", exc)
        return {
            "key": "llm_routing_judge",
            "score": 0.0,
            "comment": f"judge error: {type(exc).__name__}",
        }


def _parse_judge_json(raw: str) -> dict:
    text = raw.strip()
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fence:
        text = fence.group(1)
    else:
        brace = re.search(r"\{.*\}", text, re.DOTALL)
        if brace:
            text = brace.group(0)
    try:
        obj = json.loads(text)
        return obj if isinstance(obj, dict) else {}
    except json.JSONDecodeError:
        return {}
