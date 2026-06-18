#!/usr/bin/env python3
"""
RET-01 through RET-11 retrieval evaluation runner.

Usage:
  INTEGRATION_TESTS=1 python evals/runners/retrieval_eval.py
  INTEGRATION_TESTS=1 python evals/runners/retrieval_eval.py --report evals/reports/retrieval_latest.json
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

import httpx
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

from config.settings import settings  # noqa: E402
from packages.core.rag.retriever import Retriever  # noqa: E402
from tests.helpers.auth import make_dev_jwt  # noqa: E402
from tests.helpers.chat_client import stream_chat  # noqa: E402
from tests.helpers.ingest_client import upload_file, wait_for_source_status  # noqa: E402

GOLDEN_PATH = ROOT / "evals" / "datasets" / "retrieval_golden.json"
FIXTURES = ROOT / "tests" / "fixtures" / "ingestion"
TENANT_ID = os.getenv("NOTEBOOKLM_TENANT_ID", "eeff7c1c-fe22-4573-ad93-a36f19ad4dc5")


REFUSAL_MARKERS = (
    "not found in provided sources",
    "not found in the selected sources",
    "not found in the provided sources",
    "not found in your sources",
    "not in the provided sources",
    "cannot find",
    "no information",
    "don't have information",
    "do not have information",
)


@dataclass
class EvalResult:
    item_id: str
    passed: bool
    metrics: Dict[str, Any] = field(default_factory=dict)
    notes: str = ""


def _phrase_hit(text: str, phrases: List[str]) -> bool:
    lower = text.lower()
    return any(p.lower() in lower for p in phrases)


def _recall_at_k(ranks: List[Optional[int]], k: int) -> float:
    if not ranks:
        return 0.0
    hits = sum(1 for r in ranks if r is not None and r <= k)
    return hits / len(ranks)


def _mrr(ranks: List[Optional[int]]) -> float:
    if not ranks:
        return 0.0
    scores = [1.0 / r for r in ranks if r is not None]
    return sum(scores) / len(ranks) if scores else 0.0


def _jaccard(a: Set[str], b: Set[str]) -> float:
    if not a and not b:
        return 1.0
    union = a | b
    if not union:
        return 0.0
    return len(a & b) / len(union)


SKIP_FIXTURES = {
    "blank_scanned.pdf",
    "truncated.pdf",
    "jpg_renamed.pdf",
    "encrypted_sample.pdf",
}


def _golden_fixture_names(items: List[Dict[str, Any]]) -> List[str]:
    names: List[str] = []
    seen: set[str] = set()
    for item in items:
        for name in item.get("fixture_files") or []:
            if name not in seen and name not in SKIP_FIXTURES:
                seen.add(name)
                names.append(name)
    return names


async def ensure_fixture_sources(
    client: httpx.Client,
    base_url: str,
    token: str,
    items: List[Dict[str, Any]],
) -> Dict[str, str]:
    """Upload golden-set fixtures once; map filename -> source_id."""
    mapping: Dict[str, str] = {}
    for name in _golden_fixture_names(items):
        path = FIXTURES / name
        if not path.exists():
            raise FileNotFoundError(f"Missing fixture for golden set: {path}")
        response = upload_file(client, base_url=base_url, token=token, file_path=path)
        if response.status_code != 200:
            raise RuntimeError(
                f"Upload failed for {name}: {response.status_code} {response.text[:300]}"
            )
        source_id = response.json()["id"]
        wait_for_source_status(client, base_url=base_url, token=token, source_id=source_id)
        mapping[name] = source_id
    return mapping


async def retrieve_chunks(
    query: str,
    source_ids: List[str],
    user_id: str,
) -> List[Dict[str, Any]]:
    retriever = Retriever(TENANT_ID, user_id=user_id)
    filt = {"source_id": {"$in": source_ids}} if source_ids else None
    result = await retriever.retrieve(query=query, filter=filt, include_ncert_global=False)
    return list(result.get("chunks") or result.get("matches") or [])


def chunk_ids(chunks: List[Dict[str, Any]]) -> List[str]:
    ids: List[str] = []
    for ch in chunks:
        cid = ch.get("chunk_id") or ch.get("id") or ""
        if cid:
            ids.append(str(cid))
    return ids


def _chunk_text_blob(ch: Dict[str, Any]) -> str:
    meta = ch.get("metadata") or {}
    parts = [
        ch.get("text") or "",
        meta.get("text") or "",
        meta.get("_node_content") or "",
    ]
    return " ".join(str(p) for p in parts if p)


def rank_of_first_hit(chunks: List[Dict[str, Any]], phrases: List[str]) -> Optional[int]:
    for idx, ch in enumerate(chunks, start=1):
        if _phrase_hit(_chunk_text_blob(ch), phrases):
            return idx
    return None


async def run_eval(base_url: str, user_id: str) -> Dict[str, Any]:
    token = make_dev_jwt(user_id)
    golden = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))
    thresholds = golden["thresholds"]
    items: List[Dict[str, Any]] = golden["items"]

    with httpx.Client(timeout=120.0) as client:
        fixture_map = await ensure_fixture_sources(client, base_url, token, items)

    factual_ranks: List[Optional[int]] = []
    formula_ranks: List[Optional[int]] = []
    long_ranks: List[Optional[int]] = []
    type_ranks: Dict[str, List[Optional[int]]] = defaultdict(list)
    paraphrase_sets: Dict[str, List[Set[str]]] = defaultdict(list)
    negative_results: List[bool] = []
    multi_doc_hits = 0
    multi_doc_total = 0
    precision_scores: List[float] = []

    results: List[EvalResult] = []

    for item in items:
        source_ids = [fixture_map[name] for name in item.get("fixture_files", []) if name in fixture_map]
        chunks = await retrieve_chunks(item["question"], source_ids, user_id)
        ids_top10 = chunk_ids(chunks)[:10]
        ids_top5 = set(ids_top10[:5])

        if item.get("negative"):
            chat = None
            with httpx.Client(timeout=180.0) as client:
                for attempt in range(3):
                    try:
                        chat = stream_chat(
                            client,
                            base_url=base_url,
                            token=token,
                            message=item["question"],
                            active_source_ids=source_ids,
                        )
                        break
                    except httpx.HTTPStatusError as exc:
                        if exc.response.status_code in {500, 502, 503, 429} and attempt < 2:
                            import time

                            time.sleep(2 ** attempt)
                            continue
                        raise
            text = (chat.text or "").lower() if chat else ""
            refused = any(m in text for m in REFUSAL_MARKERS) or "not found" in text
            negative_results.append(refused)
            results.append(EvalResult(item["id"], refused, {"refused": refused}))
            continue

        phrases = item.get("expected_phrases") or []
        rank = rank_of_first_hit(chunks, phrases)
        if item.get("bucket") == "factual":
            factual_ranks.append(rank)
        if item.get("bucket") == "formula":
            formula_ranks.append(rank)
        if item.get("bucket") == "long_question":
            long_ranks.append(rank)
        qtype = item.get("question_type") or "GENERAL"
        type_ranks[qtype].append(rank)

        if item.get("paraphrase_group"):
            paraphrase_sets[item["paraphrase_group"]].append(ids_top5)

        if item.get("bucket") == "multi_doc" or item.get("allowed_sources_min"):
            min_sources = item.get("allowed_sources_min") or 2
            multi_doc_total += 1
            sources_in_top5 = {
                (ch.get("source_id") or (ch.get("metadata") or {}).get("source_id"))
                for ch in chunks[:5]
            }
            hit_count = len([s for s in source_ids if s in sources_in_top5])
            if hit_count >= min_sources:
                multi_doc_hits += 1

        relevant = 0
        for ch in chunks[:10]:
            if phrases and _phrase_hit(_chunk_text_blob(ch), phrases):
                relevant += 1
        precision_scores.append(relevant / max(len(chunks[:10]), 1))

        passed = rank is not None and rank <= 3
        results.append(EvalResult(item["id"], passed, {"rank": rank, "top10": len(ids_top10)}))

    paraphrase_jaccards: List[float] = []
    for group, sets in paraphrase_sets.items():
        if len(sets) < 2:
            continue
        base = sets[0]
        for other in sets[1:]:
            paraphrase_jaccards.append(_jaccard(base, other))

    id_to_type = {it["id"]: it.get("question_type", "GENERAL") for it in items}
    ret10_failures: Dict[str, List[str]] = {}
    for qtype, ranks in type_ranks.items():
        failed_for_type = [
            r.item_id
            for r in results
            if id_to_type.get(r.item_id) == qtype
            and (r.metrics.get("rank") is None or r.metrics.get("rank", 99) > 3)
        ]
        if failed_for_type and _recall_at_k(ranks, 3) < thresholds["question_type_recall_at_3_min"]:
            ret10_failures[qtype] = failed_for_type

    summary = {
        "recall_at_1": _recall_at_k(factual_ranks, 1),
        "recall_at_3": _recall_at_k(factual_ranks, 3),
        "recall_at_5": _recall_at_k(factual_ranks, 5),
        "recall_at_10": _recall_at_k(factual_ranks, 10),
        "mrr": _mrr(factual_ranks),
        "context_precision": sum(precision_scores) / max(len(precision_scores), 1),
        "formula_recall_at_3": _recall_at_k(formula_ranks, 3),
        "long_question_recall_at_3": _recall_at_k(long_ranks, 3),
        "negative_refusal_rate": sum(negative_results) / max(len(negative_results), 1),
        "multi_doc_rate": (multi_doc_hits / multi_doc_total) if multi_doc_total else None,
        "paraphrase_jaccard_mean": sum(paraphrase_jaccards) / max(len(paraphrase_jaccards), 1),
        "question_type_recall_at_3": {
            k: _recall_at_k(v, 3) for k, v in type_ranks.items()
        },
        "ret10_failed_item_ids": ret10_failures,
        "thresholds": thresholds,
        "pass": {
            "RET-01": _recall_at_k(factual_ranks, 3) >= thresholds["recall_at_3"],
            "RET-02": _mrr(factual_ranks) >= thresholds["mrr"],
            "RET-03": (sum(precision_scores) / max(len(precision_scores), 1)) >= thresholds["context_precision"],
            "RET-05": ((multi_doc_hits / multi_doc_total) if multi_doc_total else 1.0)
            >= thresholds["multi_doc_top5_min_sources"],
            "RET-06": (sum(negative_results) / max(len(negative_results), 1)) >= thresholds["negative_refusal_rate"],
            "RET-08": (sum(paraphrase_jaccards) / max(len(paraphrase_jaccards), 1))
            >= thresholds["paraphrase_jaccard_top5"],
            "RET-09": _recall_at_k(formula_ranks, 3) >= thresholds["formula_recall_at_3"],
            "RET-10": all(
                _recall_at_k(v, 3) >= thresholds["question_type_recall_at_3_min"] for v in type_ranks.values()
            ),
            "RET-11": _recall_at_k(long_ranks, 3) >= thresholds["long_question_recall_at_3"],
        },
        "items": [{"id": r.item_id, "passed": r.passed, "metrics": r.metrics, "notes": r.notes} for r in results],
    }
    return summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default=os.getenv("NOTEBOOKLM_API_URL", "http://127.0.0.1:8000"))
    parser.add_argument("--user-id", default="ret_eval_user")
    parser.add_argument("--report", default=str(ROOT / "evals" / "reports" / "retrieval_latest.json"))
    args = parser.parse_args()

    if os.getenv("INTEGRATION_TESTS", "").strip() not in {"1", "true", "yes"}:
        print("Set INTEGRATION_TESTS=1 to run live retrieval eval")
        return 2

    summary = asyncio.run(run_eval(args.base_url, args.user_id))
    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary["pass"], indent=2))
    print(f"Report written to {report_path}")
    return 0 if all(summary["pass"].values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
