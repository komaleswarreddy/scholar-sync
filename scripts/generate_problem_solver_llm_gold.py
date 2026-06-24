#!/usr/bin/env python3
"""
Generate production-level LLM gold outputs for Agents 17-22 eval pool.

Uses the same prompts and models as ProblemSolverService:
  - problem_solver/dna.j2  -> task problem_solver_dna
  - coach templates      -> task problem_solver_mode
  - follow_up.j2         -> task problem_solver_mode

Results cached to problem_solver_llm_gold_cache.json (resumable).
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env")

from config.settings import settings  # noqa: E402
from packages.core.llm import get_llm_client, get_model_for_task  # noqa: E402
from packages.core.prompts import load_prompt  # noqa: E402
from packages.core.processing.help_me_solve_cumulative import enrich_help_me_solve_response
from packages.core.security.answer_leak_guard import answer_leak_guard  # noqa: E402
from packages.core.services.problem_solver_service import (  # noqa: E402
    MODE_TEMPLATES,
    _parse_json_object,
    normalize_mode_response,
)
from packages.core.services.problem_subject_inference import (  # noqa: E402
    infer_problem_subject,
    normalize_dna_subject,
)
from problem_solver_gold_authors import ncert_context as build_ncert_context, infer_chapter  # noqa: E402

POOL_PATH = SCRIPTS / "problem_solver_eval_pool.json"
CACHE_PATH = SCRIPTS / "problem_solver_llm_gold_cache.json"
DNA_CACHE_KEY = "_dna_by_problem_id"

AGENT_TEMPLATE = {
    "problem_dna_analyzer": None,
    "explain_from_basics": MODE_TEMPLATES["EXPLAIN_FROM_BASICS"],
    "show_best_approach": MODE_TEMPLATES["SHOW_BEST_APPROACH"],
    "show_missing_idea": MODE_TEMPLATES["SHOW_MISSING_IDEA"],
    "help_me_solve_it": MODE_TEMPLATES["HELP_ME_SOLVE_IT"],
    "problem_solver_followup": "problem_solver/follow_up.j2",
}

AGENT_TO_MODE = {
    "explain_from_basics": "EXPLAIN_FROM_BASICS",
    "show_best_approach": "SHOW_BEST_APPROACH",
    "show_missing_idea": "SHOW_MISSING_IDEA",
    "help_me_solve_it": "HELP_ME_SOLVE_IT",
}


def _scope_for_item(item: dict[str, Any]) -> dict[str, Any]:
    subj = item.get("subject", "physics")
    inference = infer_problem_subject(item["problem_text_normalized"], [subj, "science", "mathematics"])
    keys = list({subj, inference.get("subject_key", subj)})
    labels = [subj.title()]
    return {
        "subject_keys": keys,
        "subject_labels": labels,
        "class_num": int(item.get("class_num") or 12),
    }


def _ncert_for_item(item: dict[str, Any]) -> str:
    ch = infer_chapter(item["problem_text_normalized"], item.get("subject", "physics"))
    return build_ncert_context(ch, item.get("subject", "physics"))


async def _llm_json(prompt: str, task: str, retries: int = 3) -> dict[str, Any]:
    provider, model = get_model_for_task(task)
    llm = get_llm_client(provider=provider, model=model, temperature=0.3)
    last_err: Exception | None = None
    for attempt in range(retries):
        try:
            resp = await llm.generate(
                prompt,
                response_format={"type": "json_object"},
                feature_tag=f"eval_gold_{task}",
            )
            parsed = _parse_json_object(resp.content or "")
            if parsed:
                return parsed
            last_err = ValueError("empty or invalid JSON")
        except Exception as exc:
            last_err = exc
        await asyncio.sleep(2 ** attempt)
    raise RuntimeError(f"LLM failed after {retries} tries: {last_err}")


async def _fetch_dna(item: dict[str, Any], cache: dict[str, Any]) -> dict[str, Any]:
    pid = item["id"]
    dna_store = cache.setdefault(DNA_CACHE_KEY, {})
    if pid in dna_store:
        return dna_store[pid]

    scope = _scope_for_item(item)
    ncert = _ncert_for_item(item)
    inference = infer_problem_subject(item["problem_text_normalized"], scope["subject_keys"])
    hint = (
        f"{inference['subject']} (NCERT key: {inference['subject_key']}, "
        f"confidence: {inference['confidence']})"
    )
    prompt = load_prompt(
        "problem_solver/dna.j2",
        problem_text_normalized=item["problem_text_normalized"],
        ncert_context=ncert,
        subject_keys=scope["subject_keys"],
        subject_labels=scope["subject_labels"],
        class_num=scope["class_num"],
        inferred_subject_hint=hint,
    )
    dna = await _llm_json(prompt, task="problem_solver_dna")
    dna = normalize_dna_subject(dna, item["problem_text_normalized"], scope)
    expert = dna.get("expert_solution_internal")
    dna_store[pid] = {"dna_json": dna, "expert_solution_internal": expert}
    return dna_store[pid]


def _help_me_prior_example_id(
    item: dict[str, Any],
    lookup: dict[tuple[str, int], str],
) -> str | None:
    ic = int(item.get("interaction_count") or 0)
    if ic <= 0:
        return None
    return lookup.get((item["id"], ic - 1))


def _format_prior_response(prior: dict[str, Any] | None) -> str | None:
    if not prior:
        return None
    return json.dumps(prior, ensure_ascii=False, indent=2)


async def _fetch_coach_gold(
    item: dict[str, Any],
    cache: dict[str, Any],
    *,
    pool_by_ex_id: dict[str, dict[str, Any]],
    help_me_lookup: dict[tuple[str, int], str],
) -> dict[str, Any]:
    agent_id = item["agent_id"]
    ncert = _ncert_for_item(item)
    dna_bundle = await _fetch_dna(item, cache)
    expert = dna_bundle.get("expert_solution_internal")

    if agent_id == "problem_dna_analyzer":
        return {"dna_json": dna_bundle["dna_json"]}

    if agent_id == "problem_solver_followup":
        action = item.get("action", "GIVE_SIMILAR_PROBLEM")
        mode = item.get("solving_mode", "HELP_ME_SOLVE_IT")
        prompt = load_prompt(
            "problem_solver/follow_up.j2",
            action=action,
            user_follow_up=f"Student clicked {action}",
            problem_text_normalized=item["problem_text_normalized"],
            solving_mode=mode,
            ncert_context=ncert,
        )
        response = await _llm_json(prompt, task="problem_solver_mode")
        allow = action in ("REVEAL_SOLUTION", "SHOW_BEST_APPROACH", "SHOW_SHORTER_VERSION")
        response = answer_leak_guard(response, expert_solution=expert, allow_reveal=allow)
        response = normalize_mode_response(response, solving_mode=mode, interaction_count=0)
        return {"coach_json": response}

    template = AGENT_TEMPLATE[agent_id]
    mode = AGENT_TO_MODE[agent_id]
    ic = int(item.get("interaction_count") or 0)
    sc = item.get("student_choice") or None
    if ic in (1, 2) and not sc:
        sc = "A"

    prompt_kwargs: dict[str, Any] = {
        "problem_text_normalized": item["problem_text_normalized"],
        "ncert_context": ncert,
        "interaction_count": ic,
        "checkpoint_number": ic + 1 if agent_id == "help_me_solve_it" else None,
        "student_choice": sc,
    }
    if agent_id == "help_me_solve_it" and ic >= 1:
        prior_ex_id = _help_me_prior_example_id(item, help_me_lookup)
        prior_gold: dict[str, Any] | None = None
        if prior_ex_id:
            cached = cache.get("examples", {}).get(prior_ex_id)
            if cached and cached.get("coach_json"):
                prior_gold = cached["coach_json"]
            elif prior_ex_id in pool_by_ex_id:
                prior_bundle = await _fetch_coach_gold(
                    pool_by_ex_id[prior_ex_id],
                    cache,
                    pool_by_ex_id=pool_by_ex_id,
                    help_me_lookup=help_me_lookup,
                )
                prior_gold = prior_bundle.get("coach_json")
        prompt_kwargs["prior_response"] = _format_prior_response(prior_gold)

    prompt = load_prompt(template, **prompt_kwargs)
    response = await _llm_json(prompt, task="problem_solver_mode")
    allow_reveal = mode in ("EXPLAIN_FROM_BASICS", "SHOW_BEST_APPROACH")
    if agent_id == "help_me_solve_it" and ic >= 2:
        allow_reveal = True
    response = answer_leak_guard(response, expert_solution=expert, allow_reveal=allow_reveal)
    response = normalize_mode_response(response, solving_mode=mode, interaction_count=ic)
    if agent_id == "help_me_solve_it":
        prior_dict: dict[str, Any] | None = None
        if ic >= 1:
            prior_ex_id = _help_me_prior_example_id(item, help_me_lookup)
            if prior_ex_id:
                cached = cache.get("examples", {}).get(prior_ex_id)
                if cached and cached.get("llm_gold", {}).get("coach_json"):
                    prior_dict = cached["llm_gold"]["coach_json"]
        response = enrich_help_me_solve_response(
            response,
            interaction_count=ic,
            student_choice=sc,
            prior_response=prior_dict,
        )
    return {"coach_json": response}


def _load_cache() -> dict[str, Any]:
    if CACHE_PATH.exists():
        return json.loads(CACHE_PATH.read_text(encoding="utf-8"))
    return {"version": "1.0.0", "examples": {}, DNA_CACHE_KEY: {}}


def _save_cache(cache: dict[str, Any]) -> None:
    CACHE_PATH.write_text(json.dumps(cache, indent=2, ensure_ascii=False), encoding="utf-8")


async def run(args: argparse.Namespace) -> int:
    if not (settings.OPENAI_API_KEY or "").strip():
        print("ERROR: OPENAI_API_KEY required for production LLM gold generation.", file=sys.stderr)
        return 1
    if not POOL_PATH.exists():
        print(f"Missing {POOL_PATH}. Run select_problem_solver_eval_pool.py first.", file=sys.stderr)
        return 1

    pool = json.loads(POOL_PATH.read_text(encoding="utf-8"))
    pool_items = pool["items"]
    pool_by_ex_id = {it["example_id"]: it for it in pool_items}
    help_me_lookup: dict[tuple[str, int], str] = {}
    for it in pool_items:
        if it.get("agent_id") == "help_me_solve_it":
            help_me_lookup[(it["id"], int(it.get("interaction_count") or 0))] = it["example_id"]

    items = pool_items
    problem_ids_for_dna_clear: set[str] = set()
    if args.agent:
        items = [i for i in items if i["agent_id"] == args.agent]
    if args.has_image:
        items = [i for i in items if i.get("has_image")]
    if args.ids_file:
        ids_path = Path(args.ids_file)
        if not ids_path.is_absolute():
            ids_path = SCRIPTS / ids_path
        id_data = json.loads(ids_path.read_text(encoding="utf-8"))
        problem_ids = set(id_data.get("patched_problem_ids") or id_data.get("ids") or [])
        example_ids = set(id_data.get("patched_example_ids") or [])
        problem_ids_for_dna_clear = problem_ids
        if example_ids:
            items = [i for i in items if i["example_id"] in example_ids]
        elif problem_ids:
            items = [i for i in items if i["id"] in problem_ids]
    if args.limit:
        items = items[: args.limit]

    def _sort_key(it: dict[str, Any]) -> tuple[int, int, str]:
        ic = int(it.get("interaction_count") or 0) if it.get("agent_id") == "help_me_solve_it" else 0
        return (0 if it.get("agent_id") != "help_me_solve_it" else 1, ic, it["example_id"])

    items = sorted(items, key=_sort_key)

    cache = _load_cache()
    examples = cache.setdefault("examples", {})
    done = 0
    skipped = 0
    failed: list[str] = []

    for i, item in enumerate(items):
        ex_id = item["example_id"]
        if ex_id in examples and not args.force:
            skipped += 1
            continue
        if args.force and (problem_ids_for_dna_clear or args.has_image):
            if not problem_ids_for_dna_clear or item["id"] in problem_ids_for_dna_clear:
                dna_store = cache.setdefault(DNA_CACHE_KEY, {})
                dna_store.pop(item["id"], None)
        if args.dry_run:
            print(f"[dry-run] would generate {ex_id} ({item['agent_id']})")
            continue
        print(f"[{i+1}/{len(items)}] {ex_id} ({item['agent_id']})...", flush=True)
        try:
            gold = await _fetch_coach_gold(
                item,
                cache,
                pool_by_ex_id=pool_by_ex_id,
                help_me_lookup=help_me_lookup,
            )
            examples[ex_id] = {
                "example_id": ex_id,
                "agent_id": item["agent_id"],
                "problem_id": item["id"],
                "llm_gold": gold,
                "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            }
            _save_cache(cache)
            done += 1
        except Exception as exc:
            print(f"  FAIL: {exc}", flush=True)
            failed.append(ex_id)
        await asyncio.sleep(args.delay)

    # Merge llm_gold into pool
    if not args.dry_run and done > 0:
        full_pool = json.loads(POOL_PATH.read_text(encoding="utf-8"))
        cache = _load_cache()
        for item in full_pool["items"]:
            ex = cache["examples"].get(item["example_id"])
            if ex and "llm_gold" in ex:
                item["llm_gold"] = ex["llm_gold"]
                item["gold_source"] = "production_llm"
        POOL_PATH.write_text(json.dumps(full_pool, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"Merged llm_gold into {POOL_PATH}")

    print(f"Done: {done} generated, {skipped} skipped, {len(failed)} failed")
    if failed:
        print("Failed:", ", ".join(failed[:20]))
        return 1
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate LLM gold for problem solver eval pool")
    parser.add_argument("--agent", type=str, default="", help="Filter by agent_id (e.g. show_missing_idea)")
    parser.add_argument("--limit", type=int, default=0, help="Max examples to process (0=all)")
    parser.add_argument("--delay", type=float, default=1.0, help="Seconds between API calls")
    parser.add_argument("--force", action="store_true", help="Regenerate even if cached")
    parser.add_argument("--has-image", action="store_true", help="Only has_image eval items")
    parser.add_argument(
        "--ids-file",
        type=str,
        default="",
        help="JSON file with patched_problem_ids or ids to regenerate",
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    return asyncio.run(run(args))


if __name__ == "__main__":
    sys.exit(main())
