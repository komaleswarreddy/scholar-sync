#!/usr/bin/env python3
"""Generate production vision LLM gold for Agents 32–33 eval pool."""

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
sys.path.insert(0, str(SCRIPTS))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env")

from config.settings import settings  # noqa: E402
from ocr_eval_catalog import extract_page_embedded_images  # noqa: E402
from packages.core.processing.image_ocr import (  # noqa: E402
    describe_diagram_image_bytes,
    ocr_diagram_image_bytes,
    ocr_problem_page_bytes,
)
from packages.core.processing.problem_solver_extraction import (  # noqa: E402
    finalize_problem_text,
    split_diagram_blocks,
)

_QUESTION_SPLIT_RE = re.compile(r"(?=Q\.\s*\d+)", re.I)

POOL_PATH = SCRIPTS / "agents_32_34_eval_pool.json"
CACHE_PATH = SCRIPTS / "agents_32_34_vision_gold_cache.json"


def _strip_fences(text: str) -> str:
    t = (text or "").strip()
    m = re.match(r"^```(?:\w+)?\s*\n?(.*?)\n?```\s*$", t, re.S | re.I)
    return m.group(1).strip() if m else t


def _validate_image_ocr(text: str, item: dict[str, Any]) -> dict[str, Any]:
    ans = _strip_fences(text).strip()
    if len(ans) < 40:
        raise ValueError(f"extracted_text too short ({len(ans)} chars)")
    if re.search(r"can't process images|unable to (read|process)", ans, re.I):
        raise ValueError("vision refusal in OCR output")
    if not re.search(r"Q\.?\s*\d+|Section|SECTION|\(\d\)|\([A-D]\)", ans, re.I):
        if len(ans) < 80:
            raise ValueError("missing question-number signal in OCR output")
    if item.get("variation") == "diagram" and "[diagram:" not in ans.lower():
        raise ValueError("diagram variation missing [Diagram: ...] block")
    return {"extracted_text": ans}


async def _collect_page_diagram_desc(item: dict[str, Any], page_png: bytes) -> str:
    """Mirror problem_solver_source_text hybrid diagram collection."""
    parts: list[str] = []
    seen: set[str] = set()

    def _add_desc(raw_desc: str) -> None:
        for block in split_diagram_blocks(raw_desc):
            key = block[:100].lower()
            if key not in seen:
                seen.add(key)
                parts.append(block)

    for img_bytes in extract_page_embedded_images(item["source_key"], int(item["page_number"])):
        try:
            desc = await describe_diagram_image_bytes(img_bytes)
            if desc.strip():
                _add_desc(desc.strip())
        except Exception:
            continue
    if page_png:
        try:
            desc = await describe_diagram_image_bytes(page_png, mime_type="image/png")
            if desc.strip():
                _add_desc(desc.strip())
        except Exception:
            pass
    return "; ".join(f"[Diagram: {part}]" for part in parts) if parts else ""


def _merge_page_ocr_with_diagrams(
    page_text: str,
    diagram_desc: str,
    *,
    page_has_images: bool = True,
) -> str:
    """Per-question stem → [Diagram] → options merge (production finalize_problem_text)."""
    body = (page_text or "").strip()
    if not body or not diagram_desc:
        return body
    chunks = [chunk.strip() for chunk in _QUESTION_SPLIT_RE.split(body) if chunk.strip()]
    if not chunks:
        return finalize_problem_text(body, diagram_desc, page_has_images=page_has_images)
    return "\n\n".join(
        finalize_problem_text(chunk, diagram_desc, page_has_images=page_has_images)
        for chunk in chunks
    )


def _validate_diagram_labels(text: str, item: dict[str, Any]) -> dict[str, Any]:
    ans = _strip_fences(text).strip()
    if not ans or ans.upper() == "NO_DIAGRAM":
        raise ValueError("NO_DIAGRAM or empty labels")
    if len(ans) < 15:
        raise ValueError("labels_text too short")
    if len(ans) > 900:
        raise ValueError("labels_text too long (full page OCR leak)")
    noise = ("no image", "unable to extract", "please upload", "no diagram", "can't process")
    if any(n in ans.lower() for n in noise):
        raise ValueError("noise marker in diagram labels")
    # Expect label-like tokens (letters, digits, arrows, units) — not prose paragraphs
    if len(ans.split()) > 120 and "," not in ans and ";" not in ans:
        raise ValueError("labels_text looks like prose OCR not labels")
    return {"labels_text": ans}


async def gold_image_ocr(item: dict[str, Any]) -> dict[str, Any]:
    path = ROOT / item["fixture_path"]
    if not path.exists():
        raise FileNotFoundError(f"missing fixture {path}")
    png = path.read_bytes()
    text = await ocr_problem_page_bytes(png, mime_type="image/png")
    if item.get("variation") == "diagram":
        diagram_desc = await _collect_page_diagram_desc(item, png)
        if not diagram_desc:
            raise ValueError("diagram variation produced no diagram description")
        text = _merge_page_ocr_with_diagrams(text, diagram_desc, page_has_images=True)
    return _validate_image_ocr(text, item)


async def gold_diagram_ocr(item: dict[str, Any]) -> dict[str, Any]:
    path = ROOT / item["fixture_path"]
    if not path.exists():
        raise FileNotFoundError(f"missing fixture {path}")
    png = path.read_bytes()
    text = await ocr_diagram_image_bytes(png, mime_type="image/png")
    return _validate_diagram_labels(text, item)


FETCHERS = {
    "image_ocr": gold_image_ocr,
    "diagram_label_ocr": gold_diagram_ocr,
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
        print(f"Run select_agents_32_34_eval_pool.py first. Missing {POOL_PATH}", file=sys.stderr)
        return 1

    pool = json.loads(POOL_PATH.read_text(encoding="utf-8"))
    items = [i for i in pool["items"] if i["agent_id"] in FETCHERS]
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
            if row["agent_id"] not in FETCHERS:
                continue
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
