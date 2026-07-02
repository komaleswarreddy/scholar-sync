#!/usr/bin/env python3
"""Generate production LLM gold for Agents 26–30 (RAG source-upload pipeline)."""

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
from packages.core.services.tutor_notebook_bootstrap_service import _parse_json_object  # noqa: E402

POOL_PATH = SCRIPTS / "agents_26_30_eval_pool.json"
CACHE_PATH = SCRIPTS / "agents_26_30_llm_gold_cache.json"

CHUNK_TYPES = {
    "definition", "procedure", "example", "table", "figure",
    "argument", "formula", "qa", "other",
}

ELECTRICITY_TERMS = ("ohm", "electricity", "resistance", "voltage", "current", "kirchhoff")


def _parse_json(raw: str) -> dict[str, Any] | None:
    return _parse_json_object(raw)


def _strip_fences(text: str) -> str:
    t = (text or "").strip()
    m = re.match(r"^```(?:json|markdown)?\s*\n?(.*?)\n?```\s*$", t, re.S | re.I)
    return m.group(1).strip() if m else t


def _validate_sketch(data: dict[str, Any], item: dict[str, Any]) -> dict[str, Any]:
    required = ("chapter_title", "main_sections", "key_definitions", "concepts")
    for k in required:
        if k not in data:
            raise ValueError(f"sketch missing key {k}")
    concepts = data.get("concepts") or []
    if not isinstance(concepts, list) or len(concepts) < 10:
        raise ValueError(f"concepts count {len(concepts) if isinstance(concepts, list) else 0} < 10")
    defs = data.get("key_definitions") or {}
    doc = (item.get("document_text") or "").lower()
    subj = (item.get("subject") or "").lower()
    for term in defs:
        tl = str(term).lower()
        if "ohm" in tl and not any(x in doc for x in ELECTRICITY_TERMS):
            if "electric" not in subj and "physics" not in subj:
                raise ValueError(f"cross-topic definition leak: {term}")
    sketch = {
        "chapter_title": str(data.get("chapter_title", "") or ""),
        "main_sections": [str(x) for x in (data.get("main_sections") or [])][:20],
        "key_definitions": {str(k): str(v)[:200] for k, v in (defs or {}).items()},
        "concepts": [str(c) for c in concepts][:30],
    }
    if len(json.dumps(sketch, ensure_ascii=False)) > 4000:
        raise ValueError("sketch too large")
    return {"sketch_json": sketch}


def _validate_contextualization(data: dict[str, Any], item: dict[str, Any]) -> dict[str, Any]:
    keys = ("chunk_context", "chunk_summary", "chunk_type", "section_title", "concept_hint")
    for k in keys:
        if k not in data:
            raise ValueError(f"contextualization missing {k}")
    ctype = str(data.get("chunk_type", "")).strip().lower()
    if ctype not in CHUNK_TYPES:
        raise ValueError(f"invalid chunk_type {ctype}")
    ctx = str(data.get("chunk_context", "")).strip()
    summ = str(data.get("chunk_summary", "")).strip()
    if not ctx and not summ:
        raise ValueError("empty chunk_context and chunk_summary")
    if len(ctx) > 800 or len(summ) > 600:
        raise ValueError("context/summary too long")
    return {
        "contextualization_json": {
            "chunk_context": ctx,
            "chunk_summary": summ,
            "chunk_type": ctype,
            "section_title": str(data.get("section_title", "") or ""),
            "concept_hint": str(data.get("concept_hint", "") or ""),
        }
    }


def _parse_map_lines(text: str, n_parts: int) -> str:
    raw = _strip_fences(text)
    lines = [ln.strip() for ln in raw.splitlines() if ln.strip()]
    part_lines: list[str] = []

    for ln in lines:
        m = re.match(r"^Part\s+(\d+)\s*[:\-–]\s*(.+)$", ln, re.I)
        if m:
            part_lines.append(f"Part {m.group(1)}: {m.group(2).strip()}")
            continue
        m = re.match(r"^\*\*Part\s+(\d+)\*\*\s*[:\-–]?\s*(.+)$", ln, re.I)
        if m:
            part_lines.append(f"Part {m.group(1)}: {m.group(2).strip()}")
            continue
        m = re.match(r"^(\d+)\.\s+(.+)$", ln)
        if m:
            part_lines.append(f"Part {m.group(1)}: {m.group(2).strip()}")

    if len(part_lines) < n_parts:
        # one-line-per-nonempty fallback when model ignores Part prefix
        candidates = [ln for ln in lines if len(ln) > 20 and not ln.lower().startswith(("here", "below", "summary"))]
        if len(candidates) >= n_parts:
            part_lines = [f"Part {i + 1}: {candidates[i]}" for i in range(n_parts)]

    part_lines = part_lines[:n_parts]
    if len(part_lines) != n_parts:
        raise ValueError(f"map line count {len(part_lines)} != {n_parts}; raw={raw[:200]!r}")
    for pl in part_lines:
        body = pl.split(":", 1)[-1].strip()
        if len(body) < 12:
            raise ValueError(f"map line too short: {pl[:60]}")
        if re.search(r"main idea of section", body, re.I):
            raise ValueError("placeholder map line")
    return "\n".join(part_lines)


def _validate_reduce(text: str, item: dict[str, Any], map_summaries: str) -> dict[str, Any]:
    ans = _strip_fences(text).strip()
    if len(ans) < 120:
        raise ValueError(f"reduce answer too short ({len(ans)} chars)")
    themes: list[str] = []
    for ln in (map_summaries or "").splitlines():
        if ":" in ln:
            themes.append(ln.split(":", 1)[-1].strip().lower())
    if themes:
        stop = {"about", "their", "these", "those", "which", "where", "there", "other", "using", "based"}
        hits = 0
        for theme in themes:
            words = [w for w in re.findall(r"[a-z]{4,}", theme) if w not in stop]
            if words and any(w in ans.lower() for w in words[:6]):
                hits += 1
        if hits < max(1, len(themes) // 3):
            raise ValueError("reduce answer may ignore map themes")
    return {"final_answer": ans}


async def _llm_text(prompt: str, task: str, *, max_tokens: int = 2000, temperature: float = 0.35) -> str:
    provider, model = get_model_for_task(task)
    llm = get_llm_client(provider=provider, model=model, temperature=temperature)
    kwargs: dict[str, Any] = {
        "feature_tag": f"eval_gold_{task}",
        "max_tokens": max_tokens,
    }
    resp = await llm.generate(
        prompt,
        system_prompt="Follow instructions precisely.",
        temperature=temperature,
        **kwargs,
    )
    content = (resp.content or "").strip()
    if not content:
        raise ValueError("empty LLM response")
    return content


async def _llm_json(prompt: str, task: str, *, max_tokens: int = 1200) -> dict[str, Any]:
    provider, model = get_model_for_task(task)
    llm = get_llm_client(provider=provider, model=model, temperature=0.2)
    kwargs: dict[str, Any] = {
        "feature_tag": f"eval_gold_{task}",
        "max_tokens": max_tokens,
    }
    if provider == LLMProvider.OPENAI:
        kwargs["response_format"] = {"type": "json_object"}
    resp = await llm.generate(
        prompt,
        system_prompt="Return valid JSON only. No markdown fences.",
        temperature=0.2,
        **kwargs,
    )
    parsed = _parse_json(resp.content or "")
    if not parsed:
        raise ValueError("empty or invalid JSON")
    return parsed


async def gold_document_sketch(item: dict[str, Any]) -> dict[str, Any]:
    prompt = load_prompt(
        "rag/document_sketch.j2",
        header=item["header"],
        document_text=item["document_text"],
    )
    data = await _llm_json(prompt, task="chunk_contextualization")
    return _validate_sketch(data, item)


async def gold_ncert_document_sketch(item: dict[str, Any]) -> dict[str, Any]:
    prompt = load_prompt(
        "rag/ncert_document_sketch.j2",
        header=item["header"],
        document_text=item["document_text"],
    )
    data = await _llm_json(prompt, task="chunk_contextualization")
    return _validate_sketch(data, item)


async def gold_chunk_contextualization(item: dict[str, Any]) -> dict[str, Any]:
    prompt = load_prompt(
        "rag/chunk_contextualization.j2",
        whole_document=item["whole_document"],
        chunk_content=item["chunk_content"],
        target_context_tokens=item["target_context_tokens"],
        target_summary_tokens=item["target_summary_tokens"],
        target_concept_terms=item["target_concept_terms"],
    )
    data = await _llm_json(prompt, task="chunk_contextualization", max_tokens=400)
    return _validate_contextualization(data, item)


async def gold_whole_file_map(item: dict[str, Any]) -> dict[str, Any]:
    parts = item["parts"]
    excerpts = "\n\n".join(
        f"--- Part {i + 1} ---\n{p[:8000]}" for i, p in enumerate(parts) if p
    )
    prompt = load_prompt("rag/whole_file_map_prompt.j2", excerpts=excerpts)
    text = await _llm_text(prompt, task="chat", max_tokens=min(1024, 200 * len(parts)), temperature=0.2)
    map_summaries = _parse_map_lines(text, len(parts))
    return {"map_summaries": map_summaries}


async def gold_whole_file_reduce(item: dict[str, Any], cache_examples: dict[str, Any]) -> dict[str, Any]:
    map_id = item.get("map_example_id") or item["example_id"].replace("whole_file_reduce", "whole_file_map_summarizer")
    map_ex = cache_examples.get(map_id, {})
    map_gold = map_ex.get("llm_gold") or {}
    section_summaries = map_gold.get("map_summaries") or item.get("section_summaries") or ""
    if not section_summaries.strip():
        raise ValueError(f"missing map gold for {map_id}")
    prompt = load_prompt(
        "rag/whole_file_reduce_prompt.j2",
        user_message=item["user_message"],
        section_summaries=section_summaries,
    )
    text = await _llm_text(prompt, task="chat", max_tokens=2500, temperature=0.5)
    gold = _validate_reduce(text, item, section_summaries)
    gold["section_summaries"] = section_summaries
    return gold


FETCHERS = {
    "document_sketch": gold_document_sketch,
    "ncert_document_sketch": gold_ncert_document_sketch,
    "chunk_contextualization": gold_chunk_contextualization,
    "whole_file_map_summarizer": gold_whole_file_map,
}


def _load_cache() -> dict[str, Any]:
    if CACHE_PATH.exists():
        return json.loads(CACHE_PATH.read_text(encoding="utf-8"))
    return {"version": "1.0.0", "examples": {}}


def _save_cache(cache: dict[str, Any]) -> None:
    CACHE_PATH.write_text(json.dumps(cache, indent=2, ensure_ascii=False), encoding="utf-8")


def _sort_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    order = {
        "document_sketch": 0,
        "ncert_document_sketch": 1,
        "chunk_contextualization": 2,
        "whole_file_map_summarizer": 3,
        "whole_file_reduce": 4,
    }
    return sorted(items, key=lambda x: (order.get(x["agent_id"], 9), x.get("example_id", "")))


async def run(args: argparse.Namespace) -> int:
    if not (settings.OPENAI_API_KEY or "").strip():
        print("ERROR: OPENAI_API_KEY required.", file=sys.stderr)
        return 1
    if not POOL_PATH.exists():
        print(f"Run select_agents_26_30_eval_pool.py first. Missing {POOL_PATH}", file=sys.stderr)
        return 1

    pool = json.loads(POOL_PATH.read_text(encoding="utf-8"))
    items = _sort_items(pool["items"])
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
            if item["agent_id"] == "whole_file_reduce":
                gold = await gold_whole_file_reduce(item, examples)
            else:
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
                if row["agent_id"] == "whole_file_reduce":
                    row["section_summaries"] = ex["llm_gold"].get("section_summaries", "")
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
