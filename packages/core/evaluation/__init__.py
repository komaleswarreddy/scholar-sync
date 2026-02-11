"""
Evaluation Package

Continuous evaluation loop for regression detection and quality monitoring.
"""

from packages.core.evaluation.evaluator import (
    Evaluator,
    EvaluationResult,
    EvaluationReport,
    EvaluationMetric
)
from packages.core.evaluation.scheduler import (
    EvaluationScheduler,
    ScheduledEval
)
from packages.core.evaluation.confidence_scorer import (
    ConfidenceScorer,
    ConfidenceLevel
)
from packages.core.evaluation.cold_start_handler import (
    ColdStartHandler,
    ColdStartReason
)

__all__ = [
    "Evaluator",
    "EvaluationResult",
    "EvaluationReport",
    "EvaluationMetric",
    "EvaluationScheduler",
    "ScheduledEval",
    "ConfidenceScorer",
    "ConfidenceLevel",
    "ColdStartHandler",
    "ColdStartReason",
]
