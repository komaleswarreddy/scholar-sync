"""Base evaluator types."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class EvalResult:
  score: float
  passed: bool
  metrics: Dict[str, float] = field(default_factory=dict)
  details: Optional[str] = None

  def to_dict(self) -> Dict[str, Any]:
    return {
      "score": round(self.score, 2),
      "passed": self.passed,
      "metrics": {k: round(v, 4) if isinstance(v, float) else v for k, v in self.metrics.items()},
      "details": self.details,
    }


class BaseEvaluator(ABC):
  name: str = "base"
  passing_threshold: float = 90.0

  @abstractmethod
  def evaluate(
    self,
    *,
    inputs: Dict[str, Any],
    output: Any,
    expected: Dict[str, Any],
    metadata: Optional[Dict[str, Any]] = None,
  ) -> EvalResult:
    ...

  def _weighted_score(self, metrics: Dict[str, float], weights: Dict[str, float]) -> float:
    total_w = sum(weights.values()) or 1.0
    return sum(metrics.get(k, 0.0) * w for k, w in weights.items()) / total_w * 100.0
