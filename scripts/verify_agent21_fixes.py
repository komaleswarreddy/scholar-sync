#!/usr/bin/env python3
"""Pre-flight audit for agent 21 (help_me_solve_it)."""
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
from packages.core.evaluation.datasets.loader import load_agent_dataset

AGENT_ID = "help_me_solve_it"
INTENDED_GEMINI = "gemini-3.1-pro"


def audit() -> list[str]:
    errors: list[str] = []
    records = load_agent_dataset(AGENT_ID)
    if len(records) != 30:
        errors.append(f"expected 30 examples, got {len(records)}")

    ex = records[0]
    inputs = ex.input
    problem = inputs.get("problem_text_normalized", "")
    if not problem:
        errors.append("dataset missing problem_text_normalized")

    for ver in ("v1", "v2", "v3"):
        sys_s, _user = render_prompts(AGENT_ID, ver, inputs)
        if problem[:40] not in sys_s:
            errors.append(f"{ver}: problem not in system prompt")
        if "interaction_count" not in sys_s.lower() and "interactionCount" not in sys_s:
            errors.append(f"{ver}: interaction branch instructions missing")

    tok = MAX_TOKENS_BY_AGENT.get(AGENT_ID, 600)
    if tok < 8000:
        errors.append(f"max_tokens={tok} too low for full reveal JSON (recommend 16000)")

    if AGENT_ID not in STRUCTURED_JSON_AGENT_IDS:
        errors.append("not in STRUCTURED_JSON_AGENT_IDS (OpenAI json_mode off)")

    gold = ex.expected_output.get("coach_json")
    if isinstance(gold, dict):
        sample = json.dumps(gold, ensure_ascii=False)
        out = parse_model_response(AGENT_ID, sample)
        if not out.get("coach_json"):
            errors.append("parser failed on gold coach_json")

    active = get_agent_models(AGENT_ID)
    models = [m.model for m in active]
    if not models:
        errors.append("no active runtime models")
    if INTENDED_GEMINI not in models:
        errors.append(f"gemini model must stay {INTENDED_GEMINI!r}, got {models}")

    return errors


def main() -> int:
    errors = audit()
    models = [m.model for m in get_agent_models(AGENT_ID)]
    status = "PASS" if not errors else "FAIL"
    print(
        f"{status} {AGENT_ID} | examples={len(load_agent_dataset(AGENT_ID))} | "
        f"models={models} | max_tokens={MAX_TOKENS_BY_AGENT.get(AGENT_ID, 600)} | "
        f"gemini_intended={INTENDED_GEMINI}"
    )
    for e in errors:
        print(f"  - {e}")
    if errors:
        return 1
    print("\nAll pre-flight checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
