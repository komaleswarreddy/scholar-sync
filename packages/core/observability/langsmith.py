"""
LangSmith observability for agent runs and evaluations.

Wraps bootstrap + metadata normalization for agent-level and e2e traces.
"""

from __future__ import annotations

import functools
import time
from contextlib import contextmanager
from typing import Any, Callable, Dict, Generator, Optional

from packages.core.config.model_registry import get_model, get_prompt_version
from packages.core.monitoring.langsmith_bootstrap import configure_langsmith_tracing


def configure_eval_tracing(project: Optional[str] = None) -> Dict[str, Any]:
    """Enable LangSmith tracing; optionally override project for eval runs."""
    status = configure_langsmith_tracing()
    if project and status.get("enabled"):
        import os

        os.environ["LANGSMITH_PROJECT"] = project
        status = {**status, "project": project}
    return status


def agent_trace_metadata(
    agent_name: str,
    *,
    prompt_version: Optional[str] = None,
    model: Optional[str] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Standard metadata dict attached to every agent LangSmith run."""
    meta = {
        "agent_name": agent_name,
        "prompt_version": prompt_version or get_prompt_version(agent_name),
        "model": model or get_model(agent_name),
    }
    if extra:
        meta.update(extra)
    return meta


@contextmanager
def trace_agent_run(
    agent_name: str,
    *,
    inputs: Optional[Dict[str, Any]] = None,
    prompt_version: Optional[str] = None,
    model: Optional[str] = None,
    retrieved_context_chars: int = 0,
) -> Generator[Dict[str, Any], None, None]:
    """
    Context manager recording latency and attaching metadata.
    Yields a mutable record dict; set record['output'], record['error'], record['tokens'], record['cost'].
    """
    record: Dict[str, Any] = {
        "agent_name": agent_name,
        "inputs": inputs or {},
        "metadata": agent_trace_metadata(
            agent_name,
            prompt_version=prompt_version,
            model=model,
            extra={"retrieved_context_chars": retrieved_context_chars},
        ),
        "latency_ms": 0.0,
        "tokens": 0,
        "cost_usd": 0.0,
        "output": None,
        "error": None,
    }
    t0 = time.perf_counter()
    try:
        yield record
    except Exception as exc:
        record["error"] = str(exc)
        raise
    finally:
        record["latency_ms"] = (time.perf_counter() - t0) * 1000.0
        _emit_langsmith_run(record)


def _emit_langsmith_run(record: Dict[str, Any]) -> None:
    """Best-effort LangSmith run logging when SDK is available."""
    try:
        from langsmith import traceable  # noqa: F401
    except ImportError:
        return
    status = configure_langsmith_tracing()
    if not status.get("enabled"):
        return
    try:
        from langsmith.run_trees import RunTree

        meta = dict(record.get("metadata") or {})
        prompt_tok = int(record.get("prompt_tokens") or 0)
        completion_tok = int(record.get("completion_tokens") or 0)
        if not prompt_tok and record.get("tokens"):
            completion_tok = int(record.get("tokens") or 0)
            prompt_tok = completion_tok // 2
        if prompt_tok or completion_tok:
            from packages.core.observability.langsmith_publish import estimate_cost

            costs = estimate_cost(str(meta.get("model", "gpt-4o-mini")), prompt_tok, completion_tok)
            meta.update(costs)

        run = RunTree(
            name=record.get("agent_name", "agent"),
            run_type="llm" if meta.get("model") else "chain",
            inputs=record.get("inputs") or {},
            extra={"metadata": meta},
        )
        outputs = {
            "output": record.get("output"),
            "latency_ms": record.get("latency_ms"),
            "prompt_tokens": prompt_tok,
            "completion_tokens": completion_tok,
            "total_cost_usd": meta.get("total_cost_usd", record.get("cost_usd")),
        }
        if record.get("error"):
            run.end(error=record["error"])
        else:
            run.end(outputs=outputs)
        run.post()
    except Exception:
        pass


def trace_agent(agent_name: str, **meta_kwargs: Any) -> Callable:
    """Decorator wrapping async or sync agent functions with trace_agent_run."""

    def decorator(fn: Callable) -> Callable:
        @functools.wraps(fn)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            with trace_agent_run(agent_name, inputs={"args": str(args)[:500], "kwargs": str(kwargs)[:500]}, **meta_kwargs) as rec:
                result = await fn(*args, **kwargs)
                rec["output"] = result if isinstance(result, (str, dict, list)) else str(result)[:2000]
                return result

        @functools.wraps(fn)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            with trace_agent_run(agent_name, inputs={"kwargs": str(kwargs)[:500]}, **meta_kwargs) as rec:
                result = fn(*args, **kwargs)
                rec["output"] = result if isinstance(result, (str, dict, list)) else str(result)[:2000]
                return result

        import asyncio

        if asyncio.iscoroutinefunction(fn):
            return async_wrapper
        return sync_wrapper

    return decorator


def log_eval_feedback(
    run_id: str,
    score: float,
    *,
    key: str = "weighted_score",
    comment: Optional[str] = None,
) -> None:
    """Attach evaluator score to a LangSmith run."""
    try:
        from langsmith import Client

        client = Client()
        client.create_feedback(run_id, key=key, score=score / 100.0 if score > 1 else score, comment=comment)
    except Exception:
        pass
