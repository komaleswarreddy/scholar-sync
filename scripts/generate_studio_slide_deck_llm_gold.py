#!/usr/bin/env python3
"""
Generate production-level LLM gold for Agent 14 (studio_slide_deck).

Uses the same prompts and model routing as StudioService._generate_structured_task().
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
from studio_slide_deck_quality import assess_deck_quality  # noqa: E402

POOL_PATH = SCRIPTS / "studio_slide_deck_eval_pool.json"
CACHE_PATH = SCRIPTS / "studio_slide_deck_llm_gold_cache.json"


def _clean_markdown_code_blocks(content: str) -> str:
    if content.strip().startswith("```"):
        lines = content.strip().split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        return "\n".join(lines)
    return content


async def _generate_deck(item: dict[str, Any], retries: int = 4) -> str:
    context = item.get("context") or ""
    custom = item.get("custom_instructions") or ""
    system_prompt = load_prompt("studio/system_educational_json_markdown.j2")
    count_hint = ""
    m = re.search(r"(\d+)\s*slides?", custom, re.I)
    if m:
        count_hint = f"\n\nCRITICAL: Output exactly {m.group(1)} slides (# Slide 1 through # Slide {m.group(1)}). Final slide must be a conclusion with 3–6 takeaway bullets. Vary bullet counts (1–7) across slides — do not use the same number on every slide."
    user_prompt = load_prompt(
        "studio/slide_deck_prompt.j2",
        context=context,
        custom_instructions=custom + count_hint,
        retrieval_queries_note="",
    )
    provider, model = get_model_for_task("slide_deck")
    llm = get_llm_client(provider=provider, model=model, temperature=0.7)
    last_err: Exception | None = None
    for attempt in range(retries):
        try:
            resp = await llm.generate(
                user_prompt,
                system_prompt=system_prompt,
                max_tokens=4096,
                feature_tag="eval_studio_slide_deck",
            )
            content = _clean_markdown_code_blocks(resp.content or "").strip()
            if not content or not re.search(r"^#\s*Slide\s+\d+:", content, re.M | re.I):
                last_err = ValueError("missing # Slide N: headings")
                await asyncio.sleep(2 ** attempt)
                continue
            qc = assess_deck_quality(content, custom, context, production_llm=True)
            if not all(qc.values()):
                failed = [k for k, v in qc.items() if not v]
                last_err = ValueError(f"quality failed: {failed}")
                await asyncio.sleep(2 ** attempt)
                continue
            return content
        except Exception as exc:
            last_err = exc
            await asyncio.sleep(2 ** attempt)
    raise RuntimeError(f"LLM failed: {last_err}")


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
        print(f"Run build_studio_slide_deck_pool.py first. Missing {POOL_PATH}", file=sys.stderr)
        return 1

    pool = json.loads(POOL_PATH.read_text(encoding="utf-8"))
    items = pool["items"]
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
            md = await _generate_deck(item)
            examples[ex_id] = {
                "example_id": ex_id,
                "slide_deck_markdown": md,
                "gold_source": "production_llm",
                "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "quality": assess_deck_quality(
                    md, item["custom_instructions"], item.get("context", ""), production_llm=True
                ),
            }
            _save_cache(cache)
            done += 1
        except Exception as exc:
            print(f"  FAIL: {exc}", flush=True)
            failed.append(ex_id)
        await asyncio.sleep(args.delay)

    # Merge into pool
    if done and not args.dry_run:
        full = json.loads(POOL_PATH.read_text(encoding="utf-8"))
        for item in full["items"]:
            ex = examples.get(item["example_id"])
            if ex:
                item["llm_gold"] = {"slide_deck_markdown": ex["slide_deck_markdown"]}
                item["gold_source"] = "production_llm"
        full["version"] = "1.2.0"
        POOL_PATH.write_text(json.dumps(full, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"Merged llm_gold into {POOL_PATH}")

    print(f"Done: {done} generated, {skipped} skipped, {len(failed)} failed")
    if failed:
        print("Failed:", ", ".join(failed))
        return 1
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--delay", type=float, default=1.0)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    return asyncio.run(run(args))


if __name__ == "__main__":
    sys.exit(main())
