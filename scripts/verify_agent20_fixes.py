#!/usr/bin/env python3
"""Pre-flight audit for agent 20 (ncert_document_sketch)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from evals.agent_eval.config import STRUCTURED_JSON_AGENT_IDS, get_agent_models
from evals.agent_eval.evaluator_loader import parse_model_response
from evals.agent_eval.prompts import render_prompts
from evals.agent_eval.run_matrix import MAX_TOKENS_BY_AGENT
from evals.datasets.final_Evalutors.ncert_document_sketch_evaluators import (
    CORE_SKETCH_KEYS,
    PER_EXAMPLE_EVALUATORS,
    parse_model_response_to_outputs,
    schema_validity,
)
from packages.core.evaluation.datasets.loader import load_agent_dataset

AGENT_ID = "ncert_document_sketch"
PRODUCTION_KEYS = {"chapter_title", "main_sections", "key_definitions", "concepts"}


class _Run:
    def __init__(self, outputs: dict):
        self.outputs = outputs


class _Example:
    def __init__(self, inputs: dict, outputs: dict, metadata: dict | None = None):
        self.inputs = inputs
        self.outputs = outputs
        self.metadata = metadata or {}


def audit() -> list[str]:
    errors: list[str] = []
    records = load_agent_dataset(AGENT_ID)
    if len(records) != 13:
        errors.append(f"expected 13 examples, got {len(records)}")

    if CORE_SKETCH_KEYS != PRODUCTION_KEYS:
        errors.append(f"evaluator CORE_SKETCH_KEYS mismatch: {CORE_SKETCH_KEYS}")

    ex = records[0]
    inputs = ex.input
    doc = inputs.get("document_text", "")
    header = inputs.get("header", "")
    if not doc or not header:
        errors.append("dataset missing header or document_text")

    for ver in ("v1", "v2", "v3"):
        sys_s, user = render_prompts(AGENT_ID, ver, inputs)
        if doc[:40] not in sys_s:
            errors.append(f"{ver}: document_text not in system prompt")
        if header[:20] not in sys_s:
            errors.append(f"{ver}: header not in system prompt")
        if "chapter_title" not in sys_s:
            errors.append(f"{ver}: prompt missing chapter_title schema")

    tok = MAX_TOKENS_BY_AGENT.get(AGENT_ID, 600)
    if tok < 2500:
        errors.append(f"max_tokens={tok} too low for gpt-5-mini sketch JSON (recommend 3000)")

    if AGENT_ID not in STRUCTURED_JSON_AGENT_IDS:
        errors.append("not in STRUCTURED_JSON_AGENT_IDS (OpenAI json_mode off)")

    gold = ex.expected_output.get("sketch_json")
    if not isinstance(gold, dict):
        errors.append("gold sketch_json missing")
    else:
        missing_gold = PRODUCTION_KEYS - set(gold.keys())
        if missing_gold:
            errors.append(f"gold sketch_json missing keys: {sorted(missing_gold)}")

        sample = json.dumps(gold, ensure_ascii=False)
        out = parse_model_response(AGENT_ID, sample)
        if not out.get("sketch_json"):
            errors.append("parse_model_response failed on gold sketch_json")

        wrapped = json.dumps({"sketch_json": gold}, ensure_ascii=False)
        out2 = parse_model_response_to_outputs(wrapped)
        if not out2.get("sketch_json"):
            errors.append("parse_model_response_to_outputs failed on wrapped gold")

        run = _Run({"sketch_json": gold})
        example = _Example(inputs, ex.expected_output, {"variation": ex.metadata.get("variation", "unknown")})
        schema = schema_validity(run, example)
        if schema["score"] < 1.0:
            errors.append(f"gold fails schema_validity: {schema['comment']}")

    fence_sample = "```json\n" + json.dumps(gold, ensure_ascii=False) + "\n```"
    if not parse_model_response_to_outputs(fence_sample).get("sketch_json"):
        errors.append("parser failed on fenced JSON sample")

    active = get_agent_models(AGENT_ID)
    if len(active) != 3:
        errors.append(f"expected 3 runtime models, got {len(active)}")
    if not any(m.model == "gpt-5-mini" for m in active):
        errors.append("gpt-5-mini not in active models")

    if len(PER_EXAMPLE_EVALUATORS) < 7:
        errors.append("expected 7 per-example evaluators")

    return errors


def main() -> int:
    errors = audit()
    records = load_agent_dataset(AGENT_ID)
    models = [m.model for m in get_agent_models(AGENT_ID)]
    status = "PASS" if not errors else "FAIL"
    print(
        f"{status} {AGENT_ID} | examples={len(records)} | "
        f"models={models} | max_tokens={MAX_TOKENS_BY_AGENT.get(AGENT_ID, 600)}"
    )
    for e in errors:
        print(f"  - {e}")
    if errors:
        return 1
    print("\nAll pre-flight checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
