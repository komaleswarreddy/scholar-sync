#!/usr/bin/env python3
"""Pre-flight audit for agents 17 (explain_from_basics) and 18 (show_best_approach)."""
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

AGENTS = ("explain_from_basics", "show_best_approach")


def audit_agent(agent_id: str) -> list[str]:
    errors: list[str] = []
    records = load_agent_dataset(agent_id)
    if not records:
        errors.append("dataset empty")
        return errors

    ex = records[0]
    inputs = ex.input
    problem = inputs.get("problem_text_normalized", "")
    if not problem:
        errors.append("dataset missing problem_text_normalized")

    for ver in ("v1", "v2", "v3"):
        sys_s, user = render_prompts(agent_id, ver, inputs)
        if problem and problem[:40] not in sys_s:
            errors.append(f"{ver}: problem not in system prompt")
        if len(sys_s) < 400:
            errors.append(f"{ver}: system prompt too short ({len(sys_s)})")

    tok = MAX_TOKENS_BY_AGENT.get(agent_id, 600)
    if tok < 6000:
        errors.append(f"max_tokens={tok} may truncate coach JSON (recommend 8000)")

    if agent_id not in STRUCTURED_JSON_AGENT_IDS:
        errors.append("not in STRUCTURED_JSON_AGENT_IDS (OpenAI json_mode off)")

    gold = ex.expected_output.get("coach_json")
    if isinstance(gold, dict):
        sample = json.dumps(gold, ensure_ascii=False)
        out = parse_model_response(agent_id, sample)
        if not out.get("coach_json"):
            errors.append("parser failed on gold coach_json")

    active = get_agent_models(agent_id)
    if not active:
        errors.append("no active runtime models")

    return errors


def main() -> int:
    all_errors: dict[str, list[str]] = {}
    for agent_id in AGENTS:
        errs = audit_agent(agent_id)
        all_errors[agent_id] = errs
        status = "PASS" if not errs else "FAIL"
        models = [m.model for m in get_agent_models(agent_id)]
        print(f"{status} {agent_id} | examples={len(load_agent_dataset(agent_id))} | models={models} | max_tokens={MAX_TOKENS_BY_AGENT.get(agent_id, 600)}")
        for e in errs:
            print(f"  - {e}")

    failed = {k: v for k, v in all_errors.items() if v}
    if failed:
        return 1
    print("\nAll pre-flight checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
