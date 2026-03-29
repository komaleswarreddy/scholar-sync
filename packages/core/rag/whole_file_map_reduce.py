"""
Whole-document map-reduce summarization.

1) List + fetch ALL vectors for selected source(s) from Pinecone (ordered by chunk index).
2) MAP: batch chunks → LLM produces one short summary line per chunk (batched to save calls).
3) REDUCE: LLM synthesizes the final user-facing summary from the per-chunk / per-batch summaries.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

from config.settings import settings
from packages.core.rag.vectorstores.pinecone_store import get_pinecone_index
from packages.core.rag.vectorstores.namespace import normalize_pinecone_namespace
from packages.core.llm import get_llm_client, get_model_for_task
from packages.core.prompts import load_prompt


def should_whole_file_map_reduce(
    message: str,
    active_source_ids: List[str],
    intent: Any,
) -> bool:
    """
    True when we should list/fetch all chunks and run map→reduce (single source only).
    """
    from packages.core.rag.agents.intent_classifier import UserIntent

    if not getattr(settings, "USE_WHOLE_FILE_MAP_REDUCE", True):
        return False
    if len(active_source_ids) != 1:
        return False
    if intent == UserIntent.WHOLE_DOCUMENT_SUMMARY:
        return True
    if intent == UserIntent.SUMMARY:
        q = (message or "").lower()
        if any(x in q for x in ("whole", "entire", "full", "complete", "all", "everything")):
            return True
        if any(x in q for x in ("document", "pdf", "file", "book", "chapter")):
            return True
    return False


def _chunk_sort_key(match: Dict[str, Any]) -> Tuple[int, str]:
    md = match.get("metadata") or {}
    idx = md.get("chunk_index")
    if idx is not None:
        try:
            return (int(idx), match.get("id") or "")
        except (TypeError, ValueError):
            pass
    vid = match.get("id") or ""
    m = re.search(r"_chunk_(\d+)$", str(vid))
    if m:
        return (int(m.group(1)), vid)
    return (10**9, vid)


def _list_vector_ids_for_source(namespace: str, source_id: str) -> List[str]:
    """List all vector IDs for a source using id prefix {source_id}_chunk_."""
    index = get_pinecone_index()
    prefix = f"{source_id}_chunk_"
    ids: List[str] = []
    try:
        # Pinecone: index.list() yields batches of vector id strings per page
        for batch in index.list(namespace=namespace, prefix=prefix):
            if isinstance(batch, (list, tuple)):
                ids.extend(str(x) for x in batch)
            elif isinstance(batch, str):
                ids.append(batch)
    except Exception as e:
        print(f"[WHOLE_FILE] index.list failed for prefix={prefix!r}: {e}")
    return list(dict.fromkeys(ids))


def _fetch_vectors_by_ids(namespace: str, vector_ids: List[str]) -> List[Dict[str, Any]]:
    """Fetch metadata for vectors in batches (Pinecone fetch limit ~1000 IDs per call)."""
    if not vector_ids:
        return []
    index = get_pinecone_index()
    matches: List[Dict[str, Any]] = []
    batch_size = 900
    for i in range(0, len(vector_ids), batch_size):
        batch = vector_ids[i : i + batch_size]
        try:
            res = index.fetch(ids=batch, namespace=namespace)
            vecs = getattr(res, "vectors", None) or {}
            if isinstance(vecs, dict):
                for vid, rec in vecs.items():
                    md = {}
                    if hasattr(rec, "metadata") and rec.metadata:
                        md = dict(rec.metadata)
                    elif isinstance(rec, dict):
                        md = dict(rec.get("metadata") or {})
                    matches.append({"id": vid, "metadata": md, "score": 1.0})
        except Exception as e:
            print(f"[WHOLE_FILE] fetch batch failed: {e}")
    return matches


async def _fallback_query_chunks(
    tenant_id: str,
    source_id: str,
    cap: int,
    user_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """If list() is empty, retrieve up to `cap` chunks by similarity (best-effort, not guaranteed full coverage)."""
    from packages.core.rag.embedder import Embedder
    from packages.core.rag.vectorstores.pinecone_store import PineconeVectorStore

    embedder = Embedder(tenant_id, user_id=user_id)
    emb = await embedder.generate_embedding("full document summary of the entire text content")
    store = PineconeVectorStore(tenant_id)
    raw = await store.query_vectors(
        query_embedding=emb,
        top_k=min(cap, 10000),
        filter={"source_id": source_id},
    )
    matches = raw.get("matches", []) if isinstance(raw, dict) else getattr(raw, "matches", []) or []
    norm: List[Dict[str, Any]] = []
    for m in matches:
        if isinstance(m, dict):
            norm.append(m)
        else:
            md = getattr(m, "metadata", None) or {}
            norm.append(
                {
                    "id": getattr(m, "id", None),
                    "metadata": dict(md) if md else {},
                    "score": float(getattr(m, "score", 0) or 0),
                }
            )
    return norm


async def fetch_all_chunks_for_sources(
    tenant_id: str,
    source_ids: List[str],
    user_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Return all chunk records for the given sources, sorted in reading order."""
    ns = normalize_pinecone_namespace(tenant_id)
    cap = getattr(settings, "WHOLE_FILE_MAX_CHUNKS", 500)
    out: List[Dict[str, Any]] = []
    for sid in source_ids:
        ids = _list_vector_ids_for_source(ns, sid)
        if not ids:
            print(f"[WHOLE_FILE] list() empty for {sid}; using similarity query fallback.")
            rows = await _fallback_query_chunks(tenant_id, sid, cap, user_id=user_id)
        else:
            rows = _fetch_vectors_by_ids(ns, ids)
        for row in rows:
            md = row.get("metadata") or {}
            if "source_id" not in md and sid:
                md = {**md, "source_id": sid}
            row["metadata"] = md
        out.extend(rows)
    out.sort(key=_chunk_sort_key)
    if len(out) > cap:
        print(f"[WHOLE_FILE] Truncating chunks {len(out)} → {cap}")
        out = out[:cap]
    return out


def _chunk_text(m: Dict[str, Any]) -> str:
    md = m.get("metadata") or {}
    return (md.get("text") or "").strip()


async def _map_batch_summarize(
    tenant_id: str,
    user_id: str,
    batch_index: int,
    chunk_texts: List[str],
) -> str:
    """One LLM call: produce a short bullet list summarizing each excerpt in order."""
    excerpts = "\n\n".join(
        f"--- Part {batch_index}.{i + 1} ---\n{t[:8000]}" for i, t in enumerate(chunk_texts) if t
    )
    prompt = (
        "You are summarizing parts of a document for a later full-document summary.\n"
        "For each Part below, write EXACTLY ONE concise sentence capturing its main idea.\n"
        "Number your lines Part 1, Part 2, ... matching the order below.\n"
        "Do not add an introduction or conclusion.\n\n"
        f"{excerpts}"
    )
    provider, model = get_model_for_task("chat")
    llm = get_llm_client(provider=provider, model=model, temperature=0.2)
    resp = await llm.generate(
        prompt=prompt,
        temperature=0.2,
        max_tokens=min(1024, 200 * len(chunk_texts)),
        tenant_id=tenant_id,
        user_id=user_id,
        feature_tag="whole_file_map",
    )
    return (resp.content or "").strip()


async def _reduce_summaries(
    tenant_id: str,
    user_id: str,
    user_message: str,
    section_summaries: str,
) -> str:
    """Final answer from all map outputs."""
    prompt = load_prompt(
        "rag/whole_file_reduce_prompt.j2",
        user_message=user_message,
        section_summaries=section_summaries,
    )
    provider, model = get_model_for_task("chat")
    llm = get_llm_client(provider=provider, model=model, temperature=0.5)
    max_tok = getattr(settings, "DOCUMENT_SUMMARY_CHAT_MAX_TOKENS", settings.CHAT_MAX_TOKENS)
    resp = await llm.generate(
        prompt=prompt,
        temperature=0.5,
        max_tokens=max_tok,
        tenant_id=tenant_id,
        user_id=user_id,
        feature_tag="whole_file_reduce",
    )
    return (resp.content or "").strip()


async def run_whole_file_map_reduce(
    *,
    tenant_id: str,
    user_id: str,
    message: str,
    active_source_ids: List[str],
) -> Dict[str, Any]:
    """
    Map: batch-summarize all chunk texts. Reduce: one final answer from those summaries.

    Returns:
        precomputed_answer: final user-facing text (or None if map-reduce did not run)
        section_summaries: concatenated map-stage text (for optional context / debugging)
        used_map_reduce: True when map+reduce completed successfully
    """
    if not getattr(settings, "USE_WHOLE_FILE_MAP_REDUCE", True):
        return {"precomputed_answer": None, "section_summaries": "", "used_map_reduce": False}

    if not active_source_ids:
        return {"precomputed_answer": None, "section_summaries": "", "used_map_reduce": False}

    chunks = await fetch_all_chunks_for_sources(tenant_id, active_source_ids, user_id=user_id)
    if not chunks:
        return {
            "precomputed_answer": None,
            "section_summaries": "",
            "used_map_reduce": False,
            "error": "no_chunks",
        }

    texts = [_chunk_text(c) for c in chunks]
    texts = [t for t in texts if t]
    if not texts:
        return {
            "precomputed_answer": None,
            "section_summaries": "",
            "used_map_reduce": False,
            "error": "empty_text",
        }

    batch_size = max(1, int(getattr(settings, "WHOLE_FILE_MAP_BATCH_SIZE", 6)))
    map_outputs: List[str] = []
    batch_num = 0
    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        batch_num += 1
        part = await _map_batch_summarize(tenant_id, user_id, batch_num, batch)
        if part:
            map_outputs.append(part)

    section_summaries = "\n\n".join(map_outputs)
    final = await _reduce_summaries(tenant_id, user_id, message, section_summaries)

    return {
        "precomputed_answer": (final or "").strip() or None,
        "section_summaries": section_summaries,
        "used_map_reduce": bool((final or "").strip()),
    }
