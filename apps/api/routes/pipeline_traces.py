"""
Pipeline trace API (LangGraph + RAG debugger).

Traces are in-memory per process. GET /recent is available to any authenticated user
(their traces only); admins see global recent.
"""

from collections import defaultdict
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Request, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from config.settings import settings
from packages.core.database.connection import get_db
from packages.core.monitoring.metrics import get_metrics_collector
from packages.core.monitoring.pipeline_trace import get_pipeline_trace_store
from apps.api.routes.admin import check_admin_role

router = APIRouter()


_AGENT_LABELS: Dict[str, str] = {
    "generate": "Generate",
    "direct_chat": "Direct Chat",
    "intent_classify": "Intent Classify",
    "query_rewrite": "Query Rewriter",
    "chat_summarizer": "Chat Summarizer",
    "whole_file_map": "Whole File Map",
    "whole_file_reduce": "Whole File Reduce",
    "studio_generate": "Studio Generate",
    "embedding": "Embedding",
    "cohere_rerank": "Cohere Rerank",
    "moderation": "Moderation",
    "other": "Other",
}


def _normalize_agent_id(feature_tag: Optional[str]) -> str:
    ft = str(feature_tag or "").strip().lower()
    if not ft:
        return "other"
    if ft in {"chat_langgraph", "chat_langgraph_retry_not_found", "chat_langgraph_retry_incomplete", "chat"}:
        return "generate"
    if ft == "chat_langgraph_direct":
        return "direct_chat"
    if ft == "query_rewriter":
        return "query_rewrite"
    if ft == "intent_classifier":
        return "intent_classify"
    if ft == "embedding":
        return "embedding"
    if ft == "cohere_rerank":
        return "cohere_rerank"
    if ft == "chat_summarizer":
        return "chat_summarizer"
    if ft == "whole_file_map":
        return "whole_file_map"
    if ft == "whole_file_reduce":
        return "whole_file_reduce"
    if ft.startswith("studio_") or "studio" in ft:
        return "studio_generate"
    return "other"


def _extract_trace_text(tr: Any, kind: str) -> str:
    spans = sorted(list(getattr(tr, "spans", []) or []), key=lambda s: ((s.start_ms or 0.0), (s.order or 0)))
    if kind == "query":
        keys = ("message", "query", "raw_query", "query_preview", "raw_focus_snippet")
        for sp in spans:
            data = getattr(sp, "input_summary", {}) or {}
            for key in keys:
                value = data.get(key)
                if isinstance(value, str) and value.strip():
                    return value.strip()
        return ""

    output_keys = ("output_preview", "answer_preview")
    for preferred_name in ("ModerationOutput", "Generate", "DirectChat", "WholeFileMapReduce"):
        for sp in reversed(spans):
            if str(getattr(sp, "name", "")) != preferred_name:
                continue
            data = getattr(sp, "output_summary", {}) or {}
            for key in output_keys:
                value = data.get(key)
                if isinstance(value, str) and value.strip():
                    return value.strip()
    return ""


def _collect_trace_usage(trace_id: str, tenant_id: str) -> Dict[str, Any]:
    metrics = get_metrics_collector()
    with metrics._lock:
        calls = list(metrics._llm_calls)

    trace_calls = [
        c
        for c in calls
        if str(c.get("tenant_id")) == str(tenant_id) and str(c.get("request_id") or "") == str(trace_id)
    ]
    trace_calls.sort(key=lambda c: str(c.get("timestamp") or ""))

    grouped: Dict[str, Dict[str, Any]] = {}
    rows: List[Dict[str, Any]] = []
    total_in = total_out = total_tokens = 0
    total_cost = 0.0

    for idx, call in enumerate(trace_calls, start=1):
        feature_tag = str(call.get("feature_tag") or "unknown")
        agent_id = _normalize_agent_id(feature_tag)
        agent_label = _AGENT_LABELS.get(agent_id, "Other")
        prompt_tokens = int(call.get("prompt_tokens") or 0)
        completion_tokens = int(call.get("completion_tokens") or 0)
        tokens_total = int(call.get("total_tokens") or 0)
        cost = float(call.get("cost") or 0.0)
        latency_ms = float(call.get("latency_ms") or 0.0)
        model = str(call.get("model") or "unknown")
        provider = str(call.get("provider") or "unknown")

        rows.append(
            {
                "call_index": idx,
                "timestamp": call.get("timestamp"),
                "agent_id": agent_id,
                "agent_label": agent_label,
                "feature_tag": feature_tag,
                "model": model,
                "provider": provider,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": tokens_total,
                "cost_usd": round(cost, 6),
                "latency_ms": round(latency_ms, 2),
            }
        )

        total_in += prompt_tokens
        total_out += completion_tokens
        total_tokens += tokens_total
        total_cost += cost

        if feature_tag not in grouped:
            grouped[feature_tag] = {
                "agent_id": agent_id,
                "agent_label": agent_label,
                "feature_tag": feature_tag,
                "calls": 0,
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
                "cost_usd": 0.0,
                "latency_ms_total": 0.0,
                "models": defaultdict(int),
                "providers": defaultdict(int),
            }
        row = grouped[feature_tag]
        row["calls"] += 1
        row["prompt_tokens"] += prompt_tokens
        row["completion_tokens"] += completion_tokens
        row["total_tokens"] += tokens_total
        row["cost_usd"] += cost
        row["latency_ms_total"] += latency_ms
        row["models"][model] += 1
        row["providers"][provider] += 1

    usage_by_agent: List[Dict[str, Any]] = []
    for feature_tag, row in grouped.items():
        calls_n = max(int(row["calls"]), 1)
        usage_by_agent.append(
            {
                "agent_id": row["agent_id"],
                "agent_label": row["agent_label"],
                "feature_tag": feature_tag,
                "calls": row["calls"],
                "prompt_tokens": row["prompt_tokens"],
                "completion_tokens": row["completion_tokens"],
                "total_tokens": row["total_tokens"],
                "cost_usd": round(float(row["cost_usd"]), 6),
                "latency_ms_avg": round(float(row["latency_ms_total"]) / calls_n, 2),
                "models": dict(sorted(row["models"].items(), key=lambda x: x[1], reverse=True)),
                "providers": dict(sorted(row["providers"].items(), key=lambda x: x[1], reverse=True)),
            }
        )
    usage_by_agent.sort(key=lambda x: (x["total_tokens"], x["cost_usd"], x["calls"]), reverse=True)

    return {
        "summary": {
            "llm_calls": len(trace_calls),
            "prompt_tokens": total_in,
            "completion_tokens": total_out,
            "total_tokens": total_tokens,
            "cost_usd": round(total_cost, 6),
        },
        "by_agent": usage_by_agent,
        "calls": rows,
    }


def _build_trace_payload(tr: Any) -> Dict[str, Any]:
    payload = get_pipeline_trace_store().to_jsonable(tr)
    payload["trace_summary"] = {
        "query_preview": _extract_trace_text(tr, "query"),
        "response_preview": _extract_trace_text(tr, "response"),
    }
    payload["usage"] = _collect_trace_usage(tr.trace_id, tr.tenant_id)
    return payload


def _safe_basename(path: Optional[str]) -> str:
    import os

    p = str(path or "").strip()
    if not p:
        return ""
    return os.path.basename(p.replace("\\", "/"))


def _chunk_kind(md: Dict[str, Any], *, ncert_ns: str) -> str:
    st = str(md.get("source_type") or "").strip().lower()
    if st == "ncert_global":
        return "global"
    kns = str(md.get("knowledge_namespace") or "").strip()
    if kns and kns == ncert_ns:
        return "global"
    # Default: tenant-selected sources
    return "selected"


async def _load_sources_for_ids(
    db: AsyncSession,
    *,
    tenant_id: str,
    source_ids: List[str],
    caller_user_id: str,
    is_admin: bool,
) -> Dict[str, Dict[str, Any]]:
    """
    Return mapping source_id -> {title, file_name, namespace, source_kind}.
    Includes tenant sources (sources table) + NCERT global docs (ncert_global_documents table).
    """
    out: Dict[str, Dict[str, Any]] = {}
    if not source_ids:
        return out
    # Best-effort UUID coercion.
    import uuid as uuid_lib

    uuids = []
    for sid in source_ids:
        try:
            uuids.append(uuid_lib.UUID(str(sid)))
        except Exception:
            continue
    if not uuids:
        return out

    # Tenant sources
    try:
        from packages.core.database.models.source import Source

        q = select(Source.id, Source.title, Source.s3_key).where(
            Source.id.in_(uuids),
            Source.tenant_id == uuid_lib.UUID(str(tenant_id)),
        )
        if not is_admin:
            q = q.where(Source.user_id == str(caller_user_id))
        res = await db.execute(q)
        for row in res.all():
            if not row:
                continue
            sid = str(row.id)
            out[sid] = {
                "source_id": sid,
                "source_title": row.title,
                "file_name": _safe_basename(row.s3_key),
                "namespace": str(tenant_id),
                "source_kind": "selected",
            }
    except Exception:
        pass

    # NCERT global docs
    try:
        from packages.core.database.models.ncert_global import NcertGlobalDocument

        gres = await db.execute(
            select(
                NcertGlobalDocument.id,
                NcertGlobalDocument.title,
                NcertGlobalDocument.original_filename,
                NcertGlobalDocument.pinecone_namespace,
            ).where(NcertGlobalDocument.id.in_(uuids))
        )
        for row in gres.all():
            if not row:
                continue
            sid = str(row.id)
            out[sid] = {
                "source_id": sid,
                "source_title": row.title,
                "file_name": str(row.original_filename or ""),
                "namespace": str(row.pinecone_namespace or getattr(settings, "NCERT_GLOBAL_PINECONE_NAMESPACE", "NcertDataGlobal")),
                "source_kind": "global",
            }
    except Exception:
        pass

    return out


def _format_context_lines(chunks: List[Dict[str, Any]]) -> str:
    lines: List[str] = []
    for i, c in enumerate(chunks or [], 1):
        title = str(c.get("source_title") or c.get("source_id") or "unknown")
        page = c.get("page_number")
        page_str = f"p{page}" if page else f"chunk{i}"
        text = str(c.get("preview") or "")
        lines.append(f"[{i}] {title} ({page_str}): {text}")
    return "\n\n".join(lines).strip()


def _decision_log(
    *,
    similarity_threshold: float,
    active_source_ids: List[str],
    include_global_effective: bool,
    retrieved_selected: List[Dict[str, Any]],
    selected_selected: List[Dict[str, Any]],
    selected_global: List[Dict[str, Any]],
    final_answer_preview: str,
) -> List[Dict[str, Any]]:
    max_selected_score = 0.0
    if retrieved_selected:
        try:
            max_selected_score = max(float(c.get("score") or 0.0) for c in retrieved_selected)
        except Exception:
            max_selected_score = 0.0

    not_found = final_answer_preview.strip() == "Not found in provided sources."
    final_has_selected_ctx = len(selected_selected) > 0
    retrieval_had_selected = len(retrieved_selected) > 0
    crossed_threshold = bool(retrieval_had_selected and max_selected_score >= float(similarity_threshold))

    reasons: List[Dict[str, Any]] = []
    reasons.append(
        {
            "key": "selected_source_threshold_check",
            "selected_sources_count": len(active_source_ids),
            "retrieved_selected_chunks": len(retrieved_selected),
            "max_selected_score": round(float(max_selected_score), 4),
            "similarity_threshold": float(similarity_threshold),
            "passed": crossed_threshold,
        }
    )
    reasons.append(
        {
            "key": "final_context_contains_selected_sources",
            "selected_chunks_in_prompt": len(selected_selected),
            "passed": final_has_selected_ctx,
        }
    )
    reasons.append(
        {
            "key": "global_fallback_enabled",
            "enabled": bool(include_global_effective),
            "global_chunks_in_prompt": len(selected_global),
        }
    )
    reasons.append(
        {
            "key": "not_found_in_sources",
            "is_not_found": not_found,
        }
    )
    # Explicit conditions requested for “Not found in provided sources.” visibility.
    reasons.append(
        {
            "key": "not_found_conditions",
            "condition_1_no_selected_chunk_crosses_threshold": bool(not crossed_threshold),
            "condition_2_chunks_weak_or_filtered_out": bool(retrieval_had_selected and not final_has_selected_ctx),
            "condition_3_final_prompt_has_no_selected_source_context": bool(not final_has_selected_ctx),
            "expected_not_found": bool(
                (not crossed_threshold)
                or (retrieval_had_selected and not final_has_selected_ctx)
                or (not final_has_selected_ctx)
            ),
        }
    )
    # When global is used despite selected sources: explain why selected-source path failed.
    reasons.append(
        {
            "key": "global_fallback_reason",
            "global_fallback_enabled": bool(include_global_effective),
            "used_global_chunks_in_prompt": bool(len(selected_global) > 0),
            "selected_sources_failed_threshold": bool(len(active_source_ids) > 0 and not crossed_threshold),
            "selected_sources_filtered_out": bool(len(active_source_ids) > 0 and retrieval_had_selected and not final_has_selected_ctx),
            "selected_sources_missing_in_prompt": bool(len(active_source_ids) > 0 and not final_has_selected_ctx),
        }
    )
    return reasons


@router.get("/recent")
async def list_recent_traces(
    request: Request,
    db: AsyncSession = Depends(get_db),
    limit: int = 30,
) -> Dict[str, Any]:
    """
    Recent pipeline traces for the authenticated user.
    Admins see global recent traces (all users); regular users only their own.
    """
    if not getattr(settings, "ENABLE_PIPELINE_TRACE", True):
        raise HTTPException(status_code=404, detail="Pipeline tracing disabled")
    uid = getattr(request.state, "user_id", None)
    if not uid:
        raise HTTPException(status_code=401, detail="Authentication required")

    try:
        is_admin = await check_admin_role(request, db)
    except HTTPException as exc:
        print(
            f"[PIPELINE_TRACE] recent admin-role check failed for user={uid}: "
            f"{exc.status_code} {exc.detail}"
        )
        is_admin = False
    except Exception as exc:
        print(
            f"[PIPELINE_TRACE] recent admin-role check exception for user={uid}: "
            f"{type(exc).__name__}: {exc}"
        )
        is_admin = False

    try:
        store = get_pipeline_trace_store()
        filter_user: str | None = None if is_admin else uid
        traces = store.list_recent_traces_filtered(user_id=filter_user, limit=min(limit, 100))
        out: List[Dict[str, Any]] = [
            {
                "trace_id": tr.trace_id,
                "user_id": tr.user_id,
                "tenant_id": tr.tenant_id,
                "total_duration_ms": tr.total_duration_ms,
                "success": tr.success,
                "span_count": len(tr.spans),
            }
            for tr in traces
        ]
        return {"traces": out, "scope": "all" if is_admin else "mine"}
    except Exception as exc:
        print(f"[PIPELINE_TRACE] recent traces fallback for user={uid}: {type(exc).__name__}: {exc}")
        return {"traces": [], "scope": "mine", "warning": "recent_traces_unavailable"}


@router.get("/{trace_id}")
async def get_pipeline_trace(
    trace_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Return a single trace (owner or admin)."""
    if not getattr(settings, "ENABLE_PIPELINE_TRACE", True):
        raise HTTPException(status_code=404, detail="Pipeline tracing disabled")
    uid = getattr(request.state, "user_id", None)
    if not uid:
        raise HTTPException(status_code=401, detail="Authentication required")
    store = get_pipeline_trace_store()
    tr = store.get_trace(trace_id)
    if not tr:
        raise HTTPException(status_code=404, detail="Trace not found or expired")
    # Owner can always load their trace without hitting the DB for admin role.
    if uid == tr.user_id:
        return _build_trace_payload(tr)
    # Cross-tenant / other-user trace: require admin. If DB is down, return 503 — not a
    # misleading 403 (check_admin_role otherwise returns False when DB errors).
    is_admin = await check_admin_role(request, db, raise_on_db_unavailable=True)
    if not is_admin:
        raise HTTPException(status_code=403, detail="Not allowed to view this trace")
    return _build_trace_payload(tr)


@router.get("/{trace_id}/explain")
async def get_pipeline_trace_explain(
    trace_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Admin-friendly structured explain view for a trace.

    Does not expose the full rendered prompt; provides a structured breakdown:
    - sources searched
    - retrieved vs selected chunks
    - selected vs global context separation
    - deterministic decision log for Not found / fallback
    """
    if not getattr(settings, "ENABLE_PIPELINE_TRACE", True):
        raise HTTPException(status_code=404, detail="Pipeline tracing disabled")
    uid = getattr(request.state, "user_id", None)
    if not uid:
        raise HTTPException(status_code=401, detail="Authentication required")

    store = get_pipeline_trace_store()
    tr = store.get_trace(trace_id)
    if not tr:
        raise HTTPException(status_code=404, detail="Trace not found or expired")

    # Authorization: owner or admin.
    is_admin = False
    if str(uid) != str(tr.user_id):
        is_admin = await check_admin_role(request, db, raise_on_db_unavailable=True)
        if not is_admin:
            raise HTTPException(status_code=403, detail="Not allowed to view this trace")

    payload = _build_trace_payload(tr)
    artifacts = (payload.get("artifacts") or {}) if isinstance(payload, dict) else {}
    chat_req = artifacts.get("chat_request") or {}
    retrieval = artifacts.get("retrieval") or {}
    ctxsel = artifacts.get("context_selector") or {}
    guardrails_art = artifacts.get("guardrails") if isinstance(artifacts.get("guardrails"), dict) else {}
    if not guardrails_art:
        for sp in sorted(list(getattr(tr, "spans", []) or []), key=lambda s: (s.start_ms or 0, s.order or 0)):
            if str(getattr(sp, "name", "")) != "ModerationInput":
                continue
            out = getattr(sp, "output_summary", {}) or {}
            if out.get("prompt_injection_detected") is not None or out.get("injection_pattern_matched"):
                guardrails_art = {
                    "prompt_injection_detected": bool(out.get("prompt_injection_detected", False)),
                    "injection_pattern_matched": out.get("injection_pattern_matched"),
                    "generation_blocked_reason": out.get("generation_blocked_reason"),
                }
                break

    active_source_ids = list(chat_req.get("active_source_ids") or [])
    include_global_effective = bool(chat_req.get("include_ncert_global_effective"))
    tenant_ns = str(chat_req.get("tenant_namespace") or tr.tenant_id or "")
    ncert_ns = str(chat_req.get("ncert_global_namespace") or getattr(settings, "NCERT_GLOBAL_PINECONE_NAMESPACE", "NcertDataGlobal"))

    retrieved_chunks = list(retrieval.get("retrieved_chunks") or [])
    selected_chunks = list(ctxsel.get("selected_chunks") or [])

    # Normalize chunk rows
    def _norm_chunks(items: List[Dict[str, Any]], *, included: bool) -> List[Dict[str, Any]]:
        out_rows: List[Dict[str, Any]] = []
        for m in items or []:
            if not isinstance(m, dict):
                continue
            md = m.get("metadata") or {}
            if not isinstance(md, dict):
                md = {}
            source_id = md.get("source_id")
            kind = _chunk_kind(md, ncert_ns=ncert_ns)
            out_rows.append(
                {
                    "chunk_id": m.get("chunk_id"),
                    "source_id": source_id,
                    "source_kind": kind,
                    "namespace": ncert_ns if kind == "global" else tenant_ns,
                    "score": float(m.get("score") or 0.0),
                    "preview": str(md.get("text_preview") or ""),
                    "page_number": md.get("page_number"),
                    "included_in_prompt": bool(included),
                }
            )
        return out_rows

    retrieved_rows = _norm_chunks(retrieved_chunks, included=False)
    selected_rows = _norm_chunks(selected_chunks, included=True)

    selected_ids = {r.get("chunk_id") for r in selected_rows if r.get("chunk_id")}
    # Mark retrieved items that ended up included.
    for r in retrieved_rows:
        if r.get("chunk_id") in selected_ids:
            r["included_in_prompt"] = True

    all_chunk_rows = retrieved_rows + [r for r in selected_rows if r.get("chunk_id") not in {x.get("chunk_id") for x in retrieved_rows}]

    # Source lookup map
    source_ids_from_chunks = {str(r.get("source_id")) for r in all_chunk_rows if r.get("source_id")}
    source_ids_from_active = {str(sid) for sid in active_source_ids if sid}
    source_ids_all = sorted(list(source_ids_from_chunks | source_ids_from_active))
    source_meta = await _load_sources_for_ids(
        db,
        tenant_id=str(tr.tenant_id),
        source_ids=source_ids_all,
        caller_user_id=str(uid),
        is_admin=bool(is_admin),
    )

    # Attach titles + filenames to chunk rows
    for r in all_chunk_rows:
        sid = str(r.get("source_id") or "")
        meta = source_meta.get(sid) or {}
        r["source_title"] = meta.get("source_title") or r.get("source_id")
        r["file_name"] = meta.get("file_name") or ""

    # Sources searched list
    sources_searched: List[Dict[str, Any]] = []
    for sid in active_source_ids:
        s = str(sid or "").strip()
        if not s:
            continue
        meta = source_meta.get(s) or {}
        sources_searched.append(
            {
                "source_id": s,
                "source_title": meta.get("source_title") or s,
                "file_name": meta.get("file_name") or "",
                "namespace": tenant_ns,
                "source_kind": "selected",
              }
        )
    if include_global_effective:
        # Show global namespace participation (documents appear from chunks).
        sources_searched.append(
            {
                "source_id": "ncert_global_library",
                "source_title": "NCERT Global Library",
                "file_name": "",
                "namespace": ncert_ns,
                "source_kind": "global",
            }
        )

    # Answer origin classification from selected chunks
    selected_selected = [r for r in selected_rows if r.get("source_kind") == "selected"]
    selected_global = [r for r in selected_rows if r.get("source_kind") == "global"]
    if selected_selected and selected_global:
        origin = "combined"
    elif selected_global and not selected_selected:
        origin = "global_only"
    elif selected_selected and not selected_global:
        origin = "selected_only"
    else:
        origin = "none"

    # Prompt breakdown (structured only; no full rendered prompt).
    prompt_breakdown = {
        "user_query": (payload.get("trace_summary") or {}).get("query_preview") or "",
        "selected_sources_context": _format_context_lines(selected_selected),
        "global_context": _format_context_lines(selected_global),
        # The exact packed context string (already numbered + truncated in ContextSelector), if captured.
        "final_context_sent_to_llm": str((ctxsel.get("final_context_sent_to_llm") or "")).strip(),
    }
    if not prompt_breakdown["final_context_sent_to_llm"]:
        prompt_breakdown["final_context_sent_to_llm"] = "\n\n".join(
            [x for x in [prompt_breakdown["selected_sources_context"], prompt_breakdown["global_context"]] if x.strip()]
        ).strip()

    thr = float(getattr(settings, "SIMILARITY_THRESHOLD", 0.54))
    retrieved_selected = [r for r in retrieved_rows if r.get("source_kind") == "selected"]
    decision = _decision_log(
        similarity_threshold=thr,
        active_source_ids=active_source_ids,
        include_global_effective=include_global_effective,
        retrieved_selected=retrieved_selected,
        selected_selected=selected_selected,
        selected_global=selected_global,
        final_answer_preview=(payload.get("trace_summary") or {}).get("response_preview") or "",
    )

    payload["explain"] = {
        "prompt_injection_detected": bool(guardrails_art.get("prompt_injection_detected", False)),
        "injection_pattern_matched": guardrails_art.get("injection_pattern_matched"),
        "generation_blocked_reason": guardrails_art.get("generation_blocked_reason"),
        "answer_origin": origin,
        "namespaces": {
            "tenant_namespace": tenant_ns,
            "global_namespace": ncert_ns if include_global_effective else None,
        },
        "pipelines": {
            "use_retrieval_agents": bool(getattr(settings, "USE_RETRIEVAL_AGENTS", False)),
            "include_ncert_global_effective": include_global_effective,
        },
        "sources_searched": sources_searched,
        "chunks": all_chunk_rows,
        "prompt_breakdown": {
            "user_query": prompt_breakdown["user_query"],
            "selected_sources_context": prompt_breakdown["selected_sources_context"],
            "global_context": prompt_breakdown["global_context"],
            "final_context_sent_to_llm": prompt_breakdown["final_context_sent_to_llm"],
        },
        "decision_log": decision,
    }
    return payload
