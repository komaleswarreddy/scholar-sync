"""Structured context packing grouped by source."""

from __future__ import annotations

from typing import Any, Dict, List, Tuple


def _display_title(meta: Dict[str, Any]) -> str:
    for key in ("display_source", "source_title", "title", "filename"):
        val = meta.get(key)
        if val:
            return str(val)
    sid = meta.get("source_id")
    return str(sid) if sid else "Source"


def _page_label(meta: Dict[str, Any]) -> str:
    page = meta.get("page_number") or meta.get("page_start")
    return f"p{page}" if page is not None else "p?"


def pack_context_by_source(
    matches: List[Dict[str, Any]],
    *,
    max_chunk_chars: int = 0,
) -> Tuple[str, List[Dict[str, Any]]]:
    """
    Group chunks by source_id and return (context_string, citations list).
    Global citation indices are preserved in order.
    """
    if not matches:
        return "", []

    by_source: Dict[str, List[Dict[str, Any]]] = {}
    source_order: List[str] = []
    for m in matches:
        md = m.get("metadata") or {}
        sid = str(md.get("source_id") or md.get("knowledge_namespace") or "_unknown")
        if sid not in by_source:
            by_source[sid] = []
            source_order.append(sid)
        by_source[sid].append(m)

    context_parts: List[str] = []
    citations: List[Dict[str, Any]] = []
    idx = 0

    for sid in source_order:
        group = by_source[sid]
        title = _display_title((group[0].get("metadata") or {}))
        context_parts.append(f"## Source: {title}")
        for m in group:
            idx += 1
            md = m.get("metadata") or {}
            chunk_text = str(md.get("text", "") or "")
            if max_chunk_chars and len(chunk_text) > max_chunk_chars:
                chunk_text = chunk_text[:max_chunk_chars] + "..."
            page_str = _page_label(md)
            context_parts.append(f"[{idx}] ({page_str}): {chunk_text}")
            citations.append(
                {
                    "index": idx,
                    "source_id": md.get("source_id"),
                    "chunk_id": m.get("id"),
                    "text": chunk_text,
                    "page_number": md.get("page_number") or md.get("page_start"),
                    "score": m.get("score", 0.0),
                    "source_title": title,
                }
            )

    return "\n\n".join(context_parts), citations
