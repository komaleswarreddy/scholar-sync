"""Generic LLM-as-judge for agents that require it (e.g. rag_chat_response_generator)."""

from __future__ import annotations

import logging
import os
from typing import Callable

from evals.agent_eval.config import JUDGE_MODEL, get_langsmith_project, infer_provider
from evals.intent_classifier_eval.providers import call_model

logger = logging.getLogger(__name__)


def _tracing_on() -> bool:
    return (
        os.environ.get("LANGSMITH_TRACING_ENABLED", "").lower() in ("1", "true", "yes")
        or os.environ.get("LANGCHAIN_TRACING_V2", "").lower() in ("1", "true", "yes")
    )


def make_judge_llm(agent_id: str) -> Callable[[str], str]:
    """Return judge_llm(prompt) -> raw JSON string for build_per_example_evaluators."""

    def judge_llm(prompt: str) -> str:
        system = (
            "You are an expert evaluator for educational AI outputs. "
            "Follow the user message exactly and respond with JSON only."
        )
        return _judge_call(agent_id=agent_id, system=system, user=prompt)

    return judge_llm


def _judge_call(*, agent_id: str, system: str, user: str) -> str:
    judge_provider = infer_provider(JUDGE_MODEL)
    if not _tracing_on():
        return call_model(
            provider=judge_provider,
            model=JUDGE_MODEL,
            system=system,
            user=user,
            temperature=0.0,
            max_tokens=800,
        )

    run_tree = None
    try:
        from langsmith.run_trees import RunTree

        run_tree = RunTree(
            name=f"llm_judge/{agent_id}/{JUDGE_MODEL}",
            run_type="llm",
            inputs={
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ]
            },
            project_name=get_langsmith_project(),
            extra={
                "metadata": {
                    "ls_provider": judge_provider,
                    "ls_model_name": JUDGE_MODEL,
                    "agent_id": agent_id,
                }
            },
        )
        run_tree.post()
    except Exception as exc:
        logger.debug("judge RunTree.post failed: %s", exc)
        run_tree = None

    result = call_model(
        provider=judge_provider,
        model=JUDGE_MODEL,
        system=system,
        user=user,
        temperature=0.0,
        max_tokens=800,
        return_usage=True,
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
