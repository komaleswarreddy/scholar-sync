"""
Smoke test for Contextual Retrieval (before vs after).

Runs ingestion for a single document under a given source_id, then runs retrieval
for a set of queries and prints top matches + whether contextual metadata exists.

Usage:
  python scripts/smoke_contextual_retrieval.py ingest --path docs/contextual_retrieval_guide_markdown_conversion.md --tenant 00000000-0000-0000-0000-000000000001 --source baseline --contextual false
  python scripts/smoke_contextual_retrieval.py ingest --path docs/contextual_retrieval_guide_markdown_conversion.md --tenant 00000000-0000-0000-0000-000000000001 --source contextual --contextual true
  python scripts/smoke_contextual_retrieval.py query  --tenant 00000000-0000-0000-0000-000000000001 --source baseline
  python scripts/smoke_contextual_retrieval.py query  --tenant 00000000-0000-0000-0000-000000000001 --source contextual

Notes:
- This script does not depend on LlamaIndex ingestion adapters; it uses your
  `PineconeVectorStore` + `Embedder` compatible embedding model and writes the
  same metadata shape your retriever expects.

Canary (retrieval hardening):
- Staging: run `query` with `--classified-intent comparison --rag-debug` and confirm
  `retrieval_strategy.initial_retrieval_k_multiplier` is 4.0 when intent confidence is high.
- Enable `--context-aware-weighting` only after spot-checking ordering on definition/hint queries.
- For decomposition shadow mode, set `ENABLE_QUERY_DECOMPOSITION_SHADOW=true` in env (no query mutation).
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from contextlib import nullcontext
from pathlib import Path
from typing import Dict, Any, List, Optional
from unittest.mock import patch

from dotenv import load_dotenv

load_dotenv()

# Ensure project root is on sys.path (for `packages.*` imports).
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def _read_text(path: str) -> str:
    p = Path(path)
    return p.read_text(encoding="utf-8", errors="ignore")


def _print_match(m: Dict[str, Any], i: int) -> None:
    md = (m or {}).get("metadata", {}) or {}
    raw = str(md.get("text", "") or "")
    ctx = str(md.get("chunk_context", "") or "")
    summ = str(md.get("chunk_summary", "") or "")
    hint = str(md.get("concept_hint", "") or "")
    ctype = str(md.get("chunk_type", "") or "")
    sec = str(md.get("section_title", "") or "")
    cv = md.get("contextual_version", 0)
    def _safe(s: str) -> str:
        # Windows consoles often default to cp1252; keep output printable.
        try:
            return str(s)
        except Exception:
            return ""

    def _clip(s: str, n: int = 180) -> str:
        ss = _safe(s)
        return ss[:n]

    def _print_line(label: str, val: str) -> None:
        try:
            print(f"      {label}={val!r}")
        except UnicodeEncodeError:
            fallback = str(val).encode("cp1252", errors="backslashreplace").decode("cp1252", errors="ignore")
            print(f"      {label}={fallback!r}")

    print(f"  {i:02d}. id={m.get('id')} score={float(m.get('score', 0.0) or 0.0):.4f} cv={cv}")
    if sec or ctype:
        _print_line("section_title", _safe(sec))
        _print_line("chunk_type", _safe(ctype))
    if hint:
        _print_line("concept_hint", _safe(hint))
    if ctx:
        _print_line("chunk_context", _clip(ctx))
    if summ:
        _print_line("chunk_summary", _clip(summ))
    _print_line("raw_text_preview", _clip(raw))


async def _ingest(*, tenant: str, source: str, path: str) -> None:
    from config.settings import settings
    from packages.core.processing.semantic_chunker import SemanticChunker
    from packages.core.rag.vectorstores.pinecone_store import PineconeVectorStore
    from packages.core.rag.contextual_retrieval import ChunkContextualizer

    text = _read_text(path)
    # Chunk using the same chunk_size defaults as the app.
    chunker = SemanticChunker()
    chunks_with_md = chunker.chunk_text(
        text=text,
        chunk_size=int(getattr(settings, "CHUNK_SIZE", 1000)),
        overlap=int(int(getattr(settings, "CHUNK_SIZE", 1000)) * float(getattr(settings, "CHUNK_OVERLAP_PERCENT", 0.12))),
        pages=None,
    )

    # Contextual enrichment (optional)
    contextual = _INGEST_CONTEXTUAL
    contextualizer = ChunkContextualizer(tenant_id=tenant, user_id="smoke_test")

    # Build per-chunk embed text + metadata
    embed_texts = []
    vectors = []

    sem = asyncio.Semaphore(6)

    async def _enrich_one(i: int, chunk_text: str, chunk_md: dict) -> dict:
        if not contextual:
            return {}
        async with sem:
            enr = await contextualizer.enrich_chunk(
                whole_document=text,
                chunk_content=chunk_text,
                feature_tag="chunk_contextualization",
            )
            return enr.to_metadata() if enr else {}

    enrich_tasks = [asyncio.create_task(_enrich_one(i, ct, md)) for i, (ct, md) in enumerate(chunks_with_md)]
    enrich_results = await asyncio.gather(*enrich_tasks)

    for i, ((chunk_text, chunk_md), enr_md) in enumerate(zip(chunks_with_md, enrich_results)):
        vector_id = f"{source}_chunk_{i}"
        metadata = {
            "source_id": source,
            "tenant_id": tenant,
            "chunk_index": i,
            "text": chunk_text,  # raw for citations
        }
        # propagate semantic chunker metadata (page_start/end if present)
        for k in ("page_start", "page_end", "char_start", "char_end"):
            if k in (chunk_md or {}):
                metadata[k] = (chunk_md or {}).get(k)
        if "page_start" in metadata:
            metadata["page_number"] = metadata["page_start"]

        embed_text = chunk_text
        if contextual and enr_md:
            metadata.update(enr_md)
            metadata["contextual_version"] = 1
            embed_text = (
                str(metadata.get("chunk_context") or "")
                + "\n"
                + str(metadata.get("chunk_summary") or "")
                + "\n"
                + str(metadata.get("concept_hint") or "")
                + "\n\n"
                + chunk_text
            ).strip()

        embed_texts.append(embed_text)
        vectors.append({"id": vector_id, "metadata": metadata})

    store = PineconeVectorStore(tenant_id=tenant)
    embeddings = await store.batch_generate_embeddings(embed_texts)
    upserts = []
    for v, emb in zip(vectors, embeddings):
        upserts.append({"id": v["id"], "values": emb, "metadata": v["metadata"]})
    await store.batch_upsert_vectors(upserts)

    print(f"[INGEST] source_id={source} chunks_indexed={len(upserts)} contextual={contextual}")


async def _query(
    *,
    tenant: str,
    source: str,
    queries: List[str],
    classified_intent: Optional[str] = None,
    intent_confidence: Optional[float] = None,
    context_aware_weighting: bool = False,
    rag_debug: bool = False,
) -> None:
    from config.settings import settings
    from packages.core.rag.retriever import Retriever

    r = Retriever(tenant_id=tenant, user_id="smoke_test")
    flt = {"source_id": {"$in": [source]}}

    ca_ctx = (
        patch.object(settings, "ENABLE_CONTEXT_AWARE_RETRIEVAL_WEIGHTING", True)
        if context_aware_weighting
        else nullcontext()
    )
    dbg_ctx = patch.object(settings, "RAG_DEBUG", True) if rag_debug else nullcontext()

    with ca_ctx, dbg_ctx:
        for q in queries:
            print()
            print(f"== Query: {q!r} (source_id={source}) ==")
            if classified_intent:
                print(f"    classified_intent={classified_intent!r}")
            if intent_confidence is not None:
                print(f"    intent_confidence={intent_confidence!r}")
            out = await r.retrieve(
                query=q,
                filter=flt,
                conversation_history=None,
                classified_intent=classified_intent,
                classified_intent_confidence=intent_confidence,
            )
            matches = (out or {}).get("matches") or []
            print(f"Returned matches: {len(matches)}")
            dt = (out or {}).get("debug_trace") or {}
            if dt:
                rs = dt.get("retrieval_strategy")
                if rs:
                    print(f"    retrieval_strategy={rs!r}")
                if "context_aware_weighting_post_rerank" in (dt.get("guardrails_applied") or []):
                    print("    guardrail: context_aware_weighting_post_rerank")
                if dt.get("query_decomposition", {}).get("shadow_only"):
                    print("    query_decomposition: shadow_only")
            for i, m in enumerate(matches[:8], start=1):
                _print_match(m, i)


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)

    ap_i = sub.add_parser("ingest")
    ap_i.add_argument("--path", required=True)
    ap_i.add_argument("--tenant", required=True)
    ap_i.add_argument("--source", required=True)
    ap_i.add_argument("--contextual", required=True, choices=["true", "false"])

    ap_q = sub.add_parser("query")
    ap_q.add_argument("--tenant", required=True)
    ap_q.add_argument("--source", required=True)
    ap_q.add_argument(
        "--classified-intent",
        default=None,
        help="Optional intent slug passed to Retriever (e.g. comparison, explanation).",
    )
    ap_q.add_argument(
        "--intent-confidence",
        type=float,
        default=None,
        help="Optional confidence for classified intent (tests RETRIEVAL_INTENT_ROUTING_MIN_CONFIDENCE gating).",
    )
    ap_q.add_argument(
        "--context-aware-weighting",
        action="store_true",
        help="Temporarily enable ENABLE_CONTEXT_AWARE_RETRIEVAL_WEIGHTING for this run.",
    )
    ap_q.add_argument(
        "--rag-debug",
        action="store_true",
        help="Temporarily enable RAG_DEBUG to print retrieval_strategy / guardrails from debug_trace.",
    )

    args = ap.parse_args()
    if args.cmd == "ingest":
        global _INGEST_CONTEXTUAL
        _INGEST_CONTEXTUAL = args.contextual.lower() == "true"
        asyncio.run(_ingest(tenant=args.tenant, source=args.source, path=args.path))
        return

    if args.cmd == "query":
        queries = [
            "What is contextual embeddings in contextual retrieval?",
            "How does contextual BM25 help compared to embeddings?",
            "What is the full pipeline with reranking?",
            "Find the part about Rank Fusion Top 150 and reranker Top 20.",
            "Exact match query: TS-999",
        ]
        asyncio.run(
            _query(
                tenant=args.tenant,
                source=args.source,
                queries=queries,
                classified_intent=args.classified_intent,
                intent_confidence=args.intent_confidence,
                context_aware_weighting=args.context_aware_weighting,
                rag_debug=args.rag_debug,
            )
        )
        return


if __name__ == "__main__":
    _INGEST_CONTEXTUAL = False
    main()

