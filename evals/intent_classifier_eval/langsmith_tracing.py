"""LangSmith observability helpers for intent classifier eval runs."""



from __future__ import annotations



import os

from pathlib import Path

from typing import Any, Dict, Optional



import yaml



ROOT = Path(__file__).resolve().parents[2]

PRICING_PATH = ROOT / "config" / "model_pricing.yaml"





def load_pricing() -> Dict[str, Dict[str, float]]:

    if not PRICING_PATH.is_file():

        return {

            "gpt-4o-mini": {"input_per_1m_usd": 0.15, "output_per_1m_usd": 0.60},

            "gpt-4o": {"input_per_1m_usd": 2.50, "output_per_1m_usd": 10.00},

        }

    doc = yaml.safe_load(PRICING_PATH.read_text(encoding="utf-8")) or {}

    return doc.get("pricing") or {}





def estimate_cost(model: str, prompt_tokens: int, completion_tokens: int) -> Dict[str, float]:

    rates = load_pricing().get(model) or load_pricing().get("gpt-4o-mini", {})

    in_rate = float(rates.get("input_per_1m_usd", 0.15)) / 1_000_000

    out_rate = float(rates.get("output_per_1m_usd", 0.60)) / 1_000_000

    input_cost = prompt_tokens * in_rate

    output_cost = completion_tokens * out_rate

    total = input_cost + output_cost

    return {

        "prompt_tokens": float(prompt_tokens),

        "completion_tokens": float(completion_tokens),

        "total_tokens": float(prompt_tokens + completion_tokens),

        "input_cost_usd": round(input_cost, 8),

        "output_cost_usd": round(output_cost, 8),

        "total_cost_usd": round(total, 8),

    }





def _tracing_enabled() -> bool:

    return os.environ.get("LANGSMITH_TRACING_ENABLED", "").lower() in ("1", "true", "yes") or bool(

        os.environ.get("LANGCHAIN_TRACING_V2", "").lower() in ("1", "true", "yes")

    )





def _coerce_llm_result(result: Any) -> Dict[str, Any]:

    if isinstance(result, dict):

        return {

            "text": str(result.get("text") or ""),

            "usage": result.get("usage") or {},

            "refusal": result.get("refusal"),

            "finish_reason": result.get("finish_reason"),

        }

    return {

        "text": str(result or ""),

        "usage": {},

        "refusal": None,

        "finish_reason": None,

    }





def traced_llm_call(

    *,

    name: str,

    provider: str,

    model: str,

    system: str,

    user: str,

    temperature: float,

    max_tokens: int,

    call_fn,

    on_first_token_extra=None,

    json_mode: bool = False,

) -> Dict[str, Any]:

    """

    Execute an LLM call and post a child run_type=llm trace with token/cost metadata.



    Returns a dict with keys: text, usage, refusal, finish_reason.

    """

    kwargs = dict(

        provider=provider,

        model=model,

        system=system,

        user=user,

        temperature=temperature,

        max_tokens=max_tokens,

        json_mode=json_mode,

    )



    if not _tracing_enabled():

        result = call_fn(**kwargs, return_usage=True)

        return _coerce_llm_result(result)



    try:

        from datetime import datetime, timezone



        from langsmith.run_helpers import get_current_run_tree, traceable



        @traceable(name=name, run_type="llm")

        def _inner() -> Dict[str, Any]:

            run_tree = get_current_run_tree()



            def _on_first_token() -> None:

                if run_tree is not None:

                    try:

                        run_tree.add_event(

                            {

                                "name": "new_token",

                                "time": datetime.now(timezone.utc).isoformat(),

                            }

                        )

                    except Exception:

                        pass

                if on_first_token_extra is not None:

                    try:

                        on_first_token_extra()

                    except Exception:

                        pass



            result = _coerce_llm_result(

                call_fn(

                    **kwargs,

                    return_usage=True,

                    on_first_token=_on_first_token,

                )

            )

            text = result["text"]

            usage = result["usage"]

            pt = int(usage.get("prompt_tokens") or usage.get("input_tokens") or 0)

            ct = int(usage.get("completion_tokens") or usage.get("output_tokens") or 0)

            costs = estimate_cost(model, pt, ct)



            if run_tree is not None:

                usage_metadata = {

                    "input_tokens": pt,

                    "output_tokens": ct,

                    "total_tokens": pt + ct,

                    "input_cost": costs["input_cost_usd"],

                    "output_cost": costs["output_cost_usd"],

                    "total_cost": costs["total_cost_usd"],

                }

                try:

                    run_tree.set(

                        metadata={"ls_provider": provider, "ls_model_name": model},

                        usage_metadata=usage_metadata,

                    )

                except Exception:

                    run_tree.add_metadata(

                        {"ls_provider": provider, "ls_model_name": model}

                    )

                run_tree.add_outputs(

                    {

                        "output": text,

                        "usage": usage,

                        "cost": costs,

                        "refusal": result.get("refusal"),

                        "finish_reason": result.get("finish_reason"),

                    }

                )

            return result



        return _inner()

    except Exception:

        result = call_fn(**kwargs, return_usage=True)

        return _coerce_llm_result(result)

