"""Evaluator registry."""

from __future__ import annotations

from typing import Dict

from packages.core.evaluation.evaluators.agent_evaluators import (
  AnswerGeneratorEvaluator,
  FormatterEvaluator,
  HintAgentEvaluator,
  QueryRewriterEvaluator,
  RetrieverEvaluator,
  RouterEvaluator,
  VerifierEvaluator,
)
from packages.core.evaluation.evaluators.base import BaseEvaluator

_REGISTRY: Dict[str, BaseEvaluator] = {
  "router": RouterEvaluator(),
  "query_rewriter": QueryRewriterEvaluator(),
  "retriever": RetrieverEvaluator(),
  "answer_generator": AnswerGeneratorEvaluator(),
  "verifier": VerifierEvaluator(),
  "formatter": FormatterEvaluator(),
  "hint_agent": HintAgentEvaluator(),
}


def get_evaluator(name: str) -> BaseEvaluator:
  if name not in _REGISTRY:
    return _REGISTRY["formatter"]
  return _REGISTRY[name]
