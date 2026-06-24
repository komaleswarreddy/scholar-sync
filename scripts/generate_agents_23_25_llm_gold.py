#!/usr/bin/env python3
"""Generate production LLM gold for Agents 23–25 eval pool."""

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
from packages.core.llm import LLMProvider, get_llm_client, get_model_for_task  # noqa: E402
from packages.core.prompts import load_prompt  # noqa: E402
from packages.core.services.source_question_extraction_service import _normalize_sections  # noqa: E402
from packages.core.services.tutor_notebook_bootstrap_service import (  # noqa: E402
    TutorNotebookBootstrapService,
    _parse_json_object,
)

POOL_PATH = SCRIPTS / "agents_23_25_eval_pool.json"
CACHE_PATH = SCRIPTS / "agents_23_25_llm_gold_cache.json"


def _parse_json(raw: str) -> dict[str, Any] | None:
    return _parse_json_object(raw)


async def _llm_json(prompt: str, task: str, *, system: str = "Return valid JSON only.") -> dict[str, Any]:
    provider, model = get_model_for_task(task)
    llm = get_llm_client(provider=provider, model=model, temperature=0.35)
    kwargs: dict[str, Any] = {
        "feature_tag": f"eval_gold_{task}",
        "max_tokens": 2000,
    }
    if provider == LLMProvider.OPENAI:
        kwargs["response_format"] = {"type": "json_object"}
    resp = await llm.generate(prompt, system_prompt=system, temperature=0.35, **kwargs)
    parsed = _parse_json(resp.content or "")
    if not parsed:
        raise ValueError("empty or invalid JSON")
    return parsed


async def gold_bootstrap(item: dict[str, Any]) -> dict[str, Any]:
    prompt = load_prompt(
        "tutor/notebook_bootstrap.j2",
        class_num=item["class_num"],
        subject_label=item["subject_label"],
        chapter_no=item["chapter_no"],
        chapter_title=item["chapter_title"],
        concept=item.get("concept"),
        ncert_context=item["ncert_context"],
    )
    data = await _llm_json(prompt, task="chat")
    scope = {
        "class_num": item["class_num"],
        "subject_label": item["subject_label"],
        "subject_key": item.get("subject_key", "science"),
        "subject_slug": item.get("subject_key", "science"),
        "chapter_no": item["chapter_no"],
        "chapter_title": item["chapter_title"],
        "concept": item.get("concept"),
    }
    sanitized = TutorNotebookBootstrapService.__new__(TutorNotebookBootstrapService)._sanitize_payload(data, scope)
    return {"bootstrap_json": sanitized}


async def gold_followup(item: dict[str, Any]) -> dict[str, Any]:
    prompt = load_prompt(
        "tutor/follow_up_questions.j2",
        class_num=item["class_num"],
        subject_label=item["subject_label"],
        chapter_no=item["chapter_no"],
        chapter_title=item["chapter_title"],
        concept=item.get("concept"),
        user_message=item["user_message"],
        assistant_message=item["assistant_message"],
    )
    data = await _llm_json(prompt, task="tutor_follow_ups")
    follow_ups = data.get("follow_ups")
    if not isinstance(follow_ups, list) or len(follow_ups) != 3:
        raise ValueError("follow_ups must be list of 3")
    cleaned = [str(x).strip()[:90] for x in follow_ups]
    if any(len(x) < 8 for x in cleaned):
        raise ValueError("follow_ups too short")
    return {"follow_ups": cleaned}


async def gold_source_extract(item: dict[str, Any]) -> dict[str, Any]:
    prompt = load_prompt(
        "source_questions/extract.j2",
        document_text=item["document_text"],
    )
    data = await _llm_json(prompt, task="source_question_extract", system="Return valid JSON only.")
    rows = _normalize_sections(data)
    if not rows:
        raise ValueError("no questions extracted")
    # Rebuild sections_json shape for eval
    sections_map: dict[str | None, list[dict[str, Any]]] = {}
    for row in rows:
        label = row.get("section_label")
        sections_map.setdefault(label, []).append({
            "number": row["question_number"],
            "preview": row["preview"],
            "fullText": row["full_text"],
            "pageHint": row.get("page_hint"),
            "confidence": row.get("confidence", "high"),
        })
    sections = [{"label": k, "questions": v} for k, v in sections_map.items()]
    return {"sections_json": {"sections": sections}}


FETCHERS = {
    "tutor_notebook_bootstrap": gold_bootstrap,
    "tutor_follow_up_questions": gold_followup,
    "source_question_extraction": gold_source_extract,
}


def _load_cache() -> dict[str, Any]:
    if CACHE_PATH.exists():
        return json.loads(CACHE_PATH.read_text(encoding="utf-8"))
    return {"version": "1.0.0", "examples": {}}


def _save_cache(cache: dict[str, Any]) -> None:
    CACHE_PATH.write_text(json.dumps(cache, indent=2, ensure_ascii=False), encoding="utf-8")


async def run(args: argparse.Namespace) -> int:
    if not (settings.OPENAI_API_KEY or "").strip():
        print("ERROR: OPENAI_API_KEY required.", file=sys.stderr)
        return 1
    if not POOL_PATH.exists():
        print(f"Run select_agents_23_25_eval_pool.py first. Missing {POOL_PATH}", file=sys.stderr)
        return 1

    pool = json.loads(POOL_PATH.read_text(encoding="utf-8"))
    items = pool["items"]
    if args.agent:
        items = [i for i in items if i["agent_id"] == args.agent]
    if args.limit:
        items = items[: args.limit]

    cache = _load_cache()
    examples = cache.setdefault("examples", {})
    done = skipped = 0
    failed: list[str] = []

    for i, item in enumerate(items):
        ex_id = item["example_id"]
        if ex_id in examples and not args.force:
            skipped += 1
            continue
        if args.dry_run:
            print(f"[dry-run] {ex_id}")
            continue
        print(f"[{i+1}/{len(items)}] {ex_id}...", flush=True)
        try:
            fn = FETCHERS[item["agent_id"]]
            gold = await fn(item)
            examples[ex_id] = {
                "example_id": ex_id,
                "agent_id": item["agent_id"],
                "llm_gold": gold,
                "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            }
            _save_cache(cache)
            done += 1
        except Exception as exc:
            print(f"  FAIL: {exc}", flush=True)
            failed.append(ex_id)
        await asyncio.sleep(args.delay)

    if not args.dry_run and done > 0:
        full = json.loads(POOL_PATH.read_text(encoding="utf-8"))
        cache = _load_cache()
        for row in full["items"]:
            ex = cache["examples"].get(row["example_id"])
            if ex and "llm_gold" in ex:
                row["llm_gold"] = ex["llm_gold"]
                row["gold_source"] = "production_llm"
        POOL_PATH.write_text(json.dumps(full, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"Merged gold into {POOL_PATH}")

    print(f"Done: {done}, skipped: {skipped}, failed: {len(failed)}")
    return 1 if failed else 0


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--agent", default="")
    p.add_argument("--limit", type=int, default=0)
    p.add_argument("--delay", type=float, default=0.75)
    p.add_argument("--force", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    return asyncio.run(run(p.parse_args()))


if __name__ == "__main__":
    sys.exit(main())
