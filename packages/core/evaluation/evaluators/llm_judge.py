"""LLM-as-judge for answer quality."""

from __future__ import annotations

import json
import re
from typing import Any, Dict

from config.settings import settings
from packages.core.llm import get_llm_client, get_model_for_task

_JUDGE_PROMPT = """You are an expert evaluator for Indian NCERT/CBSE tutoring answers.

Score each dimension 1-5 (integers only).

Question: {question}
Context excerpts: {context}
Student-facing answer: {answer}
Reference notes (may be empty): {expected_notes}

Return ONLY JSON:
{{
  "accuracy": 1-5,
  "completeness": 1-5,
  "source_grounding": 1-5,
  "exam_worthiness": 1-5,
  "reasoning": "one short sentence"
}}
"""


def judge_answer_quality(
  *,
  question: str,
  answer: str,
  context: str = "",
  expected_notes: str = "",
) -> Dict[str, Any]:
  """Heuristic fallback when LLM unavailable; otherwise LLM judge."""
  if not (settings.OPENAI_API_KEY or "").strip():
    return _heuristic_judge(answer, context)
  try:
    provider, model = get_model_for_task("intent_classifier")
    client = get_llm_client(provider=provider, model=model, temperature=0.0, max_tokens=256)
    prompt = _JUDGE_PROMPT.format(
      question=question[:800],
      context=context[:3000],
      answer=answer[:3000],
      expected_notes=expected_notes[:500],
    )
    import asyncio

    async def _run():
      r = await client.generate(prompt=prompt, feature_tag="eval_llm_judge")
      return r.content or ""

    if _in_async_context():
      return _heuristic_judge(answer, context)
    raw = asyncio.run(_run())
  except Exception:
    return _heuristic_judge(answer, context)

  if not raw:
    return _heuristic_judge(answer, context)

  try:
    m = re.search(r"\{.*\}", raw, re.DOTALL)
    if m:
      obj = json.loads(m.group())
      for k in ("accuracy", "completeness", "source_grounding", "exam_worthiness"):
        obj[k] = max(1, min(5, int(obj.get(k, 3))))
      return obj
  except Exception:
    pass
  return _heuristic_judge(answer, context)


def _heuristic_judge(answer: str, context: str) -> Dict[str, Any]:
  a = (answer or "").lower()
  c = (context or "").lower()
  grounding = 0.6
  if c and a:
    words = [w for w in a.split() if len(w) > 4][:20]
    hits = sum(1 for w in words if w in c)
    grounding = min(1.0, hits / max(len(words), 1) + 0.3)
  score = int(3 + grounding * 2)
  return {
    "accuracy": score,
    "completeness": score,
    "source_grounding": score,
    "exam_worthiness": 3,
    "reasoning": "Heuristic judge (no API key or parse failure).",
  }


def _in_async_context() -> bool:
  try:
    import asyncio
    asyncio.get_running_loop()
    return True
  except RuntimeError:
    return False
