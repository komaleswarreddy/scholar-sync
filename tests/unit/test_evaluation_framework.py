"""Unit tests for evaluation framework."""

from packages.core.evaluation.evaluators.registry import get_evaluator
from packages.core.evaluation.datasets.loader import load_agent_dataset
from packages.core.config.model_registry import get_model, get_prompt_version


def test_router_evaluator_passes_golden_intent():
    ev = get_evaluator("router")
    records = load_agent_dataset("intent_classifier", limit=1)
    rec = records[0]
    result = ev.evaluate(
        inputs=rec.input,
        output=rec.expected_output,
        expected=rec.expected_output,
    )
    assert result.score >= 95
    assert result.passed


def test_model_registry_defaults():
    assert get_prompt_version("intent_classifier") == "v1"
    assert get_model("intent_classifier") == "gpt-4o-mini"
