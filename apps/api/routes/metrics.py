"""
Metrics Dashboard API

Provides endpoints for viewing metrics and dashboard data.
"""

from fastapi import APIRouter, Request, HTTPException, Depends, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from sqlalchemy.exc import DBAPIError, OperationalError
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from collections import defaultdict
import uuid
import csv
import io

from packages.core.database.connection import get_db
from packages.core.monitoring.metrics import get_metrics_collector
from packages.core.monitoring.alerts import get_alert_manager
from packages.core.guardrails.cost_manager import get_cost_manager
from packages.core.database.models.chat import Message, Chat

router = APIRouter()

_AGENT_CATALOG: Dict[str, Dict[str, str]] = {
    # Generation agents: use llm_client.generate() to produce user-facing or intermediate text.
    "generate": {
        "label": "Generate",
        "description": "Primary answer generation agent.",
        "category": "generation",
    },
    "direct_chat": {
        "label": "Direct Chat",
        "description": "Non-RAG direct chat generation.",
        "category": "generation",
    },
    "intent_classify": {
        "label": "Intent Classify",
        "description": "Classifies user intent before retrieval.",
        "category": "generation",
    },
    "query_rewrite": {
        "label": "Query Rewriter",
        "description": "Rewrites user query to improve retrieval quality.",
        "category": "generation",
    },
    "chat_summarizer": {
        "label": "Chat Summarizer",
        "description": "Summarizes conversation history.",
        "category": "generation",
    },
    "whole_file_map": {
        "label": "Whole File Map",
        "description": "Map phase for full-document summarization.",
        "category": "generation",
    },
    "whole_file_reduce": {
        "label": "Whole File Reduce",
        "description": "Reduce phase that builds final full-document summary.",
        "category": "generation",
    },
    "studio_generate": {
        "label": "Studio Generate",
        "description": "Studio generation flows (quiz, flashcards, report, etc.).",
        "category": "generation",
    },
    # Utility model calls: model APIs used as support stages, not final response generation.
    "embedding": {
        "label": "Embedding",
        "description": "Vector embedding model calls used for retrieval.",
        "category": "utility",
    },
    "cohere_rerank": {
        "label": "Cohere Rerank",
        "description": "Cohere rerank model calls for result ordering.",
        "category": "utility",
    },
    "moderation": {
        "label": "Moderation",
        "description": "OpenAI moderation model calls for safety checks.",
        "category": "utility",
    },
    "other": {
        "label": "Other",
        "description": "Unmapped model calls.",
        "category": "utility",
    },
}


def _normalize_agent_id(feature_tag: Optional[str]) -> str:
    ft = str(feature_tag or "").strip().lower()
    if not ft:
        return "other"
    # Strict mappings for known LLM-calling feature tags.
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
    if ft.startswith("studio_"):
        return "studio_generate"
    if "studio" in ft:
        return "studio_generate"
    return "other"


def _iso_to_dt(ts: Optional[str]) -> Optional[datetime]:
    if not ts:
        return None
    try:
        return datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
    except Exception:
        return None


def _pct_delta(current: float, previous: float) -> Optional[float]:
    if previous == 0:
        return None
    return ((current - previous) / previous) * 100.0


async def _is_admin_request(request: Request, db: AsyncSession) -> bool:
    try:
        from apps.api.routes.admin import check_admin_role
        return await check_admin_role(request, db)
    except Exception:
        return False


def _collect_agent_stats(
    llm_calls: List[Dict[str, Any]],
    trace_errors_by_agent: Optional[Dict[str, int]] = None,
) -> Dict[str, Dict[str, Any]]:
    stats: Dict[str, Dict[str, Any]] = {}
    errors = trace_errors_by_agent or {}
    for call in llm_calls:
        agent_id = _normalize_agent_id(call.get("feature_tag"))
        if agent_id not in stats:
            meta = _AGENT_CATALOG.get(agent_id, _AGENT_CATALOG["other"])
            stats[agent_id] = {
                "agent_id": agent_id,
                "agent_label": meta["label"],
                "description": meta["description"],
                "category": meta.get("category", "utility"),
                "calls": 0,
                "tokens_in": 0,
                "tokens_out": 0,
                "tokens_total": 0,
                "cost_total": 0.0,
                "latencies": [],
                "providers": defaultdict(int),
                "models": defaultdict(int),
                "feature_tags": defaultdict(int),
                "last_seen_at": None,
            }
        row = stats[agent_id]
        row["calls"] += 1
        row["tokens_in"] += int(call.get("prompt_tokens") or 0)
        row["tokens_out"] += int(call.get("completion_tokens") or 0)
        row["tokens_total"] += int(call.get("total_tokens") or 0)
        row["cost_total"] += float(call.get("cost") or 0.0)
        lat = call.get("latency_ms")
        if isinstance(lat, (int, float)):
            row["latencies"].append(float(lat))
        provider = str(call.get("provider") or "unknown")
        model = str(call.get("model") or "unknown")
        feature_tag = str(call.get("feature_tag") or "unknown")
        row["providers"][provider] += 1
        row["models"][model] += 1
        row["feature_tags"][feature_tag] += 1
        ts = _iso_to_dt(call.get("timestamp"))
        if ts:
            if row["last_seen_at"] is None or ts > row["last_seen_at"]:
                row["last_seen_at"] = ts

    for agent_id, row in stats.items():
        lats = sorted(row["latencies"])
        n = len(lats)
        avg = (sum(lats) / n) if n else 0.0
        p95 = lats[min(int(n * 0.95), n - 1)] if n else 0.0
        err_count = int(errors.get(agent_id, 0))
        row["latency_avg_ms"] = round(avg, 2)
        row["latency_p95_ms"] = round(p95, 2)
        row["error_count"] = err_count
        row["error_rate"] = round((err_count / row["calls"]) if row["calls"] > 0 else 0.0, 4)
        row["cost_total"] = round(row["cost_total"], 6)
        row["providers"] = dict(sorted(row["providers"].items(), key=lambda x: x[1], reverse=True))
        row["models"] = dict(sorted(row["models"].items(), key=lambda x: x[1], reverse=True))
        row["feature_tags"] = dict(sorted(row["feature_tags"].items(), key=lambda x: x[1], reverse=True))
        row["last_seen_at"] = row["last_seen_at"].isoformat() if row["last_seen_at"] else None
        row.pop("latencies", None)
    return stats


def _is_db_unavailable_error(exc: Exception) -> bool:
    if isinstance(exc, (OperationalError, DBAPIError, OSError, TimeoutError)):
        return True
    msg = str(exc).lower()
    return (
        "connect call failed" in msg
        or "database connection error" in msg
        or "could not connect" in msg
        or "connection refused" in msg
        or "maxclientsinsessionmode" in msg
        or "max clients reached" in msg
        or "too many connections" in msg
        or "timeout" in msg
    )


@router.get("/summary")
async def get_metrics_summary(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Get metrics summary for the current tenant and user.
    
    Returns aggregated metrics including:
    - LLM call statistics (tokens, costs)
    - Cache hit/miss rates
    - Feature usage counts
    - Document costs
    - Regenerate attempts
    """
    tenant_id = request.state.tenant_id
    user_id = getattr(request.state, "user_id", None)
    
    # Debug logging
    print(f"[METRICS API] /summary endpoint: tenant_id={tenant_id}, user_id={user_id}")
    
    metrics = get_metrics_collector()
    summary = metrics.get_metrics_summary(tenant_id=tenant_id, user_id=user_id)
    
    return {
        "tenant_id": tenant_id,
        "user_id": user_id,
        "metrics": summary,
    }


@router.get("/alerts")
async def get_alerts(
    request: Request,
    alert_type: Optional[str] = None,
    severity: Optional[str] = None,
    limit: int = 100,
):
    """
    Get recent alerts.
    
    Args:
        alert_type: Optional filter by alert type
        severity: Optional filter by severity
        limit: Maximum number of alerts to return
    """
    tenant_id = request.state.tenant_id
    user_id = getattr(request.state, "user_id", None)
    
    alert_manager = get_alert_manager()
    alerts = alert_manager.get_recent_alerts(
        alert_type=alert_type,
        severity=severity,
        limit=limit
    )
    
    # Filter by tenant if needed
    if tenant_id:
        alerts = [a for a in alerts if a.get("tenant_id") == tenant_id or a.get("tenant_id") is None]
    
    # Filter by user if needed
    if user_id:
        alerts = [a for a in alerts if not a.get("user_id") or a.get("user_id") == user_id]
    
    return {
        "tenant_id": tenant_id,
        "user_id": user_id,
        "alerts": alerts,
        "count": len(alerts),
    }


@router.get("/dashboard")
async def get_dashboard_data(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Get comprehensive dashboard data.
    
    Returns all metrics, alerts, and summary statistics for dashboard visualization.
    """
    tenant_id = request.state.tenant_id
    user_id = getattr(request.state, "user_id", None)
    
    # Debug logging
    print(f"[METRICS API] /dashboard endpoint: tenant_id={tenant_id}, user_id={user_id}")
    
    metrics = get_metrics_collector()
    alert_manager = get_alert_manager()
    cost_manager = get_cost_manager()
    
    # Get metrics summary
    summary = metrics.get_metrics_summary(tenant_id=tenant_id, user_id=user_id)
    
    # Get cache hit rate
    cache_hit_rate = metrics.get_cache_hit_rate(tenant_id=tenant_id, user_id=user_id)
    
    # Get recent alerts
    alerts = alert_manager.get_recent_alerts(limit=50)
    if tenant_id:
        alerts = [a for a in alerts if a.get("tenant_id") == tenant_id or a.get("tenant_id") is None]
    if user_id:
        alerts = [a for a in alerts if not a.get("user_id") or a.get("user_id") == user_id]
    
    # Get usage summary from cost manager
    usage_summary = await cost_manager.get_usage_summary(tenant_id=tenant_id, user_id=user_id)
    
    return {
        "tenant_id": tenant_id,
        "user_id": user_id,
        "metrics": {
            **summary,
            "cache": {
                **summary.get("cache", {}),
                "hit_rate": cache_hit_rate,
            }
        },
        "alerts": alerts,
        "usage": usage_summary,
    }


@router.get("/rag-quality/debug")
async def debug_rag_quality(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Debug endpoint to check if feedback is being saved correctly."""
    tenant_id = request.state.tenant_id
    
    if not tenant_id:
        return {"error": "Tenant ID not found", "tenant_id": None}
    
    tenant_uuid = uuid.UUID(tenant_id)
    
    # Get all messages with feedback (no date filter)
    result = await db.execute(
        select(
            Message.id,
            Message.feedback,
            Message.role,
            Message.created_at,
            Chat.tenant_id,
        )
        .join(Chat)
        .where(
            and_(
                Chat.tenant_id == tenant_uuid,
                Message.feedback.isnot(None),
            )
        )
        .order_by(Message.created_at.desc())
        .limit(20)
    )
    
    messages = result.all()
    
    # Count by feedback type
    feedback_counts = {}
    for msg in messages:
        feedback = msg.feedback
        feedback_counts[feedback] = feedback_counts.get(feedback, 0) + 1
    
    return {
        "tenant_id": tenant_id,
        "total_messages_with_feedback": len(messages),
        "feedback_counts": feedback_counts,
        "recent_messages": [
            {
                "id": str(msg.id),
                "feedback": msg.feedback,
                "role": msg.role,
                "created_at": msg.created_at.isoformat() if msg.created_at else None,
            }
            for msg in messages
        ]
    }


@router.get("/rag-quality")
async def get_rag_quality_dashboard(
    request: Request,
    db: AsyncSession = Depends(get_db),
    days: int = Query(7, description="Number of days to analyze"),
):
    """
    RAG Quality Dashboard - Shows hallucination rate and quality metrics.
    
    Calculates:
    - Hallucination rate (thumbs_down / total feedback)
    - Positive feedback rate (thumbs_up / total feedback)
    - Total messages with feedback
    - Quality trends over time
    """
    tenant_id = request.state.tenant_id
    user_id = getattr(request.state, "user_id", None)
    
    if not tenant_id:
        return {
            "tenant_id": None,
            "user_id": user_id,
            "period_days": days,
            "summary": {
                "total_feedback": 0,
                "thumbs_up": 0,
                "thumbs_down": 0,
                "hallucination_rate": 0.0,
                "positive_rate": 0.0,
            },
            "daily_breakdown": [],
            "error": "Tenant ID not found"
        }
    
    tenant_uuid = uuid.UUID(tenant_id)
    
    # Calculate date range - use timezone-aware datetime
    # Add a small buffer to ensure we catch messages created "today"
    end_date = datetime.utcnow() + timedelta(hours=1)  # Add 1 hour buffer
    start_date = end_date - timedelta(days=days)
    
    # Query messages with feedback
    # First, let's also get a count of all messages to debug
    query_conditions = [
        Chat.tenant_id == tenant_uuid,
        Message.role == 'assistant',
    ]
    if user_id:
        query_conditions.append(Chat.user_id == user_id)
    
    try:
        debug_result = await db.execute(
            select(func.count(Message.id))
            .join(Chat)
            .where(and_(*query_conditions))
        )
        total_assistant_messages = debug_result.scalar() or 0
        
        feedback_count_result = await db.execute(
            select(func.count(Message.id))
            .join(Chat)
            .where(
                and_(
                    *query_conditions,
                    Message.feedback.isnot(None),
                )
            )
        )
        total_with_feedback = feedback_count_result.scalar() or 0
    except Exception as e:
        if _is_db_unavailable_error(e):
            print(f"[RAG_QUALITY] DB unavailable; returning empty fallback: {e}")
            return {
                "tenant_id": tenant_id,
                "user_id": user_id,
                "period_days": days,
                "summary": {
                    "total_feedback": 0,
                    "thumbs_up": 0,
                    "thumbs_down": 0,
                    "hallucination_rate": 0.0,
                    "positive_rate": 0.0,
                },
                "daily_breakdown": [],
            }
        raise
    
    print(f"[RAG_QUALITY] Tenant: {tenant_id}, User: {user_id}, Total assistant messages: {total_assistant_messages}, Messages with feedback: {total_with_feedback}")
    
    # Query with date filter - use CAST to date for timezone-safe date extraction
    date_query_conditions = [
        Chat.tenant_id == tenant_uuid,
        Message.role == 'assistant',
        Message.feedback.isnot(None),
        Message.created_at >= start_date,
        Message.created_at <= end_date
    ]
    if user_id:
        date_query_conditions.append(Chat.user_id == user_id)
    
    try:
        result = await db.execute(
            select(
                Message.feedback,
                func.count(Message.id).label('count'),
                func.date(Message.created_at).label('date')
            )
            .join(Chat)
            .where(and_(*date_query_conditions))
            .group_by(Message.feedback, func.date(Message.created_at))
        )
        
        feedback_data = result.all()
    except Exception as e:
        if _is_db_unavailable_error(e):
            print(f"[RAG_QUALITY] DB unavailable during date-range query; returning empty fallback: {e}")
            return {
                "tenant_id": tenant_id,
                "user_id": user_id,
                "period_days": days,
                "summary": {
                    "total_feedback": 0,
                    "thumbs_up": 0,
                    "thumbs_down": 0,
                    "hallucination_rate": 0.0,
                    "positive_rate": 0.0,
                },
                "daily_breakdown": [],
            }
        raise
    print(f"[RAG_QUALITY] Found {len(feedback_data)} feedback rows in date range ({start_date} to {end_date})")
    
    # If no data in date range, try without date filter to see if there's any feedback at all
    if len(feedback_data) == 0 and total_with_feedback > 0:
        print(f"[RAG_QUALITY] WARNING: No feedback in date range, but {total_with_feedback} messages have feedback. Date range might be too restrictive.")
        # Try querying without date filter to get all feedback
        no_date_query_conditions = [
            Chat.tenant_id == tenant_uuid,
            Message.role == 'assistant',
            Message.feedback.isnot(None),
        ]
        if user_id:
            no_date_query_conditions.append(Chat.user_id == user_id)
        
        result_all = await db.execute(
            select(
                Message.feedback,
                func.count(Message.id).label('count'),
                func.date(Message.created_at).label('date')
            )
            .join(Chat)
            .where(and_(*no_date_query_conditions))
            .group_by(Message.feedback, func.date(Message.created_at))
        )
        feedback_data = result_all.all()
        print(f"[RAG_QUALITY] Found {len(feedback_data)} feedback rows without date filter")
    
    # Calculate totals
    total_feedback = 0
    thumbs_up = 0
    thumbs_down = 0
    
    # Daily breakdown
    daily_stats = {}
    
    for row in feedback_data:
        feedback_type = row.feedback
        count = row.count
        date = row.date.isoformat() if row.date else None
        
        total_feedback += count
        
        if feedback_type == 'thumbs_up':
            thumbs_up += count
        elif feedback_type == 'thumbs_down':
            thumbs_down += count
        
        # Daily stats
        if date:
            if date not in daily_stats:
                daily_stats[date] = {'thumbs_up': 0, 'thumbs_down': 0, 'total': 0}
            daily_stats[date][feedback_type] = count
            daily_stats[date]['total'] += count
    
    # Calculate rates
    hallucination_rate = thumbs_down / total_feedback if total_feedback > 0 else 0.0
    positive_rate = thumbs_up / total_feedback if total_feedback > 0 else 0.0
    
    # Convert daily stats to list
    daily_breakdown = [
        {
            'date': date,
            'thumbs_up': stats['thumbs_up'],
            'thumbs_down': stats['thumbs_down'],
            'total': stats['total'],
            'hallucination_rate': stats['thumbs_down'] / stats['total'] if stats['total'] > 0 else 0.0
        }
        for date, stats in sorted(daily_stats.items())
    ]
    
    return {
        "tenant_id": tenant_id,
        "user_id": user_id,
        "period_days": days,
        "summary": {
            "total_feedback": total_feedback,
            "thumbs_up": thumbs_up,
            "thumbs_down": thumbs_down,
            "hallucination_rate": round(hallucination_rate, 4),
            "positive_rate": round(positive_rate, 4),
        },
        "daily_breakdown": daily_breakdown,
    }


@router.get("/token-consumption")
async def get_token_consumption_dashboard(
    request: Request,
    db: AsyncSession = Depends(get_db),
    days: int = Query(7, description="Number of days to analyze"),
    group_by: str = Query("feature", description="Group by: 'feature', 'model', 'user'"),
):
    """
    Token Consumption Dashboard - Shows tokens by feature, model, or user.
    
    Returns:
    - Total tokens consumed
    - Breakdown by feature/model/user
    - Daily consumption trends
    - Average tokens per call
    """
    tenant_id = request.state.tenant_id
    user_id = getattr(request.state, "user_id", None)
    
    # Check if user is admin - if admin, don't filter by user_id to get aggregate data
    is_admin = False
    try:
        from apps.api.routes.admin import check_admin_role
        is_admin = await check_admin_role(request, db)
    except Exception as e:
        # If admin check fails, assume not admin
        print(f"[METRICS] Could not check admin role: {e}")
        is_admin = False
    
    # If admin, set user_id to None to get aggregate data across all users
    if is_admin:
        user_id = None
        print(f"[METRICS] Admin user detected, returning aggregate data for tenant {tenant_id}")
    
    metrics = get_metrics_collector()
    
    # Get all LLM calls from in-memory storage
    with metrics._lock:
        llm_calls = []
        for m in metrics._llm_calls:
            # Check tenant match
            if str(m.get("tenant_id")) != str(tenant_id):
                continue
            
            # Check user match - if user_id is provided (and not admin), metric MUST have matching user_id
            if user_id:
                metric_user_id = m.get("user_id")
                if not metric_user_id or str(metric_user_id) != str(user_id):
                    continue
            
            llm_calls.append(m)
    
    # Filter by date range
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    filtered_calls = []
    for call in llm_calls:
        try:
            call_time = datetime.fromisoformat(call.get("timestamp", ""))
            if call_time >= cutoff_date:
                filtered_calls.append(call)
        except:
            continue
    
    # Group by requested dimension
    grouped = {}
    daily_totals = {}
    daily_calls = {}
    total_tokens = 0
    total_prompt_tokens = 0
    total_completion_tokens = 0
    total_calls = len(filtered_calls)
    
    for call in filtered_calls:
        tokens = call.get("total_tokens", 0)
        prompt_tokens = call.get("prompt_tokens", 0)
        completion_tokens = call.get("completion_tokens", 0)
        total_tokens += tokens
        total_prompt_tokens += prompt_tokens
        total_completion_tokens += completion_tokens
        
        # Group key
        if group_by == "feature":
            key = call.get("feature_tag", "unknown")
        elif group_by == "model":
            key = call.get("model", "unknown")
        elif group_by == "user":
            key = call.get("user_id", "unknown")
        else:
            key = "all"
        
        if key not in grouped:
            grouped[key] = {
                "total_tokens": 0,
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_calls": 0,
                "avg_tokens": 0,
                "cost": 0.0,
            }
        
        grouped[key]["total_tokens"] += tokens
        grouped[key]["prompt_tokens"] += prompt_tokens
        grouped[key]["completion_tokens"] += completion_tokens
        grouped[key]["total_calls"] += 1
        grouped[key]["cost"] += call.get("cost", 0.0)
        
        # Daily totals (tokens and calls)
        try:
            call_time = datetime.fromisoformat(call.get("timestamp", ""))
            date_key = call_time.date().isoformat()
            if date_key not in daily_totals:
                daily_totals[date_key] = 0
                daily_calls[date_key] = 0
            daily_totals[date_key] += tokens
            daily_calls[date_key] += 1
        except:
            pass
    
    # Calculate averages
    for key in grouped:
        if grouped[key]["total_calls"] > 0:
            grouped[key]["avg_tokens"] = grouped[key]["total_tokens"] / grouped[key]["total_calls"]
    
    # Convert to list sorted by tokens
    breakdown = [
        {
            "key": key,
            "total_tokens": stats["total_tokens"],
            "prompt_tokens": stats["prompt_tokens"],
            "completion_tokens": stats["completion_tokens"],
            "total_calls": stats["total_calls"],
            "avg_tokens": round(stats["avg_tokens"], 2),
            "cost": round(stats["cost"], 4),
            "percentage": round((stats["total_tokens"] / total_tokens * 100) if total_tokens > 0 else 0, 2),
        }
        for key, stats in sorted(grouped.items(), key=lambda x: x[1]["total_tokens"], reverse=True)
    ]
    
    # Daily breakdown (include both tokens and calls)
    daily_breakdown = [
        {
            "date": date, 
            "tokens": tokens,
            "calls": daily_calls.get(date, 0)
        }
        for date, tokens in sorted(daily_totals.items())
    ]
    
    return {
        "tenant_id": tenant_id,
        "user_id": None if is_admin else user_id,  # Return None for admin to indicate aggregate data
        "period_days": days,
        "group_by": group_by,
        "summary": {
            "total_tokens": total_tokens,
            "prompt_tokens": total_prompt_tokens,
            "completion_tokens": total_completion_tokens,
            "input_tokens": total_prompt_tokens,  # Alias for compatibility
            "output_tokens": total_completion_tokens,  # Alias for compatibility
            "total_calls": total_calls,
            "avg_tokens_per_call": round(total_tokens / total_calls if total_calls > 0 else 0, 2),
        },
        "breakdown": breakdown,
        "daily_breakdown": daily_breakdown,
    }


@router.get("/cost-tracking")
async def get_cost_tracking_dashboard(
    request: Request,
    db: AsyncSession = Depends(get_db),
    days: int = Query(30, description="Number of days to analyze"),
    group_by_user: bool = Query(False, description="Include per-user breakdown"),
):
    """
    Cost Tracking Dashboard - Shows daily and per-user costs.
    
    Returns:
    - Total cost
    - Daily cost breakdown
    - Per-user cost breakdown (if requested)
    - Cost by model/provider
    """
    tenant_id = request.state.tenant_id
    user_id = getattr(request.state, "user_id", None)
    
    # Check if user is admin - if admin, don't filter by user_id to get aggregate data
    is_admin = False
    try:
        from apps.api.routes.admin import check_admin_role
        is_admin = await check_admin_role(request, db)
    except Exception as e:
        # If admin check fails, assume not admin
        print(f"[METRICS] Could not check admin role: {e}")
        is_admin = False
    
    # If admin, set user_id to None to get aggregate data across all users
    if is_admin:
        user_id = None
        print(f"[METRICS] Admin user detected for cost tracking, returning aggregate data for tenant {tenant_id}")
    
    metrics = get_metrics_collector()
    
    # Get all LLM calls
    with metrics._lock:
        llm_calls = []
        for m in metrics._llm_calls:
            # Check tenant match
            if str(m.get("tenant_id")) != str(tenant_id):
                continue
            
            # Check user match - if user_id is provided (and not admin), metric MUST have matching user_id
            if user_id:
                metric_user_id = m.get("user_id")
                if not metric_user_id or str(metric_user_id) != str(user_id):
                    continue
            
            llm_calls.append(m)
    
    # Filter by date range
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    filtered_calls = []
    for call in llm_calls:
        try:
            call_time = datetime.fromisoformat(call.get("timestamp", ""))
            if call_time >= cutoff_date:
                filtered_calls.append(call)
        except:
            continue
    
    # Calculate totals
    total_cost = sum(call.get("cost", 0.0) for call in filtered_calls)
    total_calls = len(filtered_calls)
    
    # Daily breakdown
    daily_costs = {}
    user_costs = {}
    model_costs = {}
    
    for call in filtered_calls:
        cost = call.get("cost", 0.0)
        
        # Daily
        try:
            call_time = datetime.fromisoformat(call.get("timestamp", ""))
            date_key = call_time.date().isoformat()
            daily_costs[date_key] = daily_costs.get(date_key, 0.0) + cost
        except:
            pass
        
        # Per user
        if group_by_user:
            user_id = call.get("user_id", "unknown")
            user_costs[user_id] = user_costs.get(user_id, 0.0) + cost
        
        # Per model
        model = call.get("model", "unknown")
        model_costs[model] = model_costs.get(model, 0.0) + cost
    
    # Convert to lists
    daily_breakdown = [
        {"date": date, "cost": round(cost, 4)}
        for date, cost in sorted(daily_costs.items())
    ]
    
    user_breakdown = None
    if group_by_user:
        user_breakdown = [
            {"user_id": user_id, "cost": round(cost, 4), "percentage": round((cost / total_cost * 100) if total_cost > 0 else 0, 2)}
            for user_id, cost in sorted(user_costs.items(), key=lambda x: x[1], reverse=True)
        ]
    
    model_breakdown = [
        {"model": model, "cost": round(cost, 4), "percentage": round((cost / total_cost * 100) if total_cost > 0 else 0, 2)}
        for model, cost in sorted(model_costs.items(), key=lambda x: x[1], reverse=True)
    ]
    
    return {
        "tenant_id": tenant_id,
        "user_id": None if is_admin else user_id,  # Return None for admin to indicate aggregate data
        "period_days": days,
        "summary": {
            "total_cost": round(total_cost, 4),
            "total_calls": total_calls,
            "avg_cost_per_call": round(total_cost / total_calls if total_calls > 0 else 0, 6),
            "daily_avg_cost": round(total_cost / days, 4),
        },
        "daily_breakdown": daily_breakdown,
        "user_breakdown": user_breakdown,
        "model_breakdown": model_breakdown,
    }


@router.get("/cache-efficiency")
async def get_cache_efficiency_dashboard(
    request: Request,
    days: int = Query(7, description="Number of days to analyze"),
):
    """
    Cache Efficiency Dashboard - Shows cache ROI and efficiency metrics.
    
    Returns:
    - Cache hit rate
    - Cache miss rate
    - Estimated cost savings from cache
    - Cache performance by type
    - Latency improvements
    """
    tenant_id = request.state.tenant_id
    user_id = getattr(request.state, "user_id", None)
    metrics = get_metrics_collector()
    
    # Get cache operations
    with metrics._lock:
        cache_ops = []
        for m in metrics._cache_operations:
            # Check tenant match
            if str(m.get("tenant_id")) != str(tenant_id):
                continue
            
            # Check user match - if user_id is provided, metric MUST have matching user_id
            if user_id:
                metric_user_id = m.get("user_id")
                if not metric_user_id or str(metric_user_id) != str(user_id):
                    continue
            
            cache_ops.append(m)
    
    # Filter by date range
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    filtered_ops = []
    for op in cache_ops:
        try:
            op_time = datetime.fromisoformat(op.get("timestamp", ""))
            if op_time >= cutoff_date:
                filtered_ops.append(op)
        except:
            continue
    
    # Calculate stats
    hits = sum(1 for op in filtered_ops if op.get("operation") == "hit")
    misses = sum(1 for op in filtered_ops if op.get("operation") == "miss")
    total = hits + misses
    
    hit_rate = hits / total if total > 0 else 0.0
    miss_rate = misses / total if total > 0 else 0.0
    
    # Calculate average latencies
    hit_latencies = [op.get("latency_ms", 0) for op in filtered_ops if op.get("operation") == "hit" and op.get("latency_ms")]
    miss_latencies = [op.get("latency_ms", 0) for op in filtered_ops if op.get("operation") == "miss" and op.get("latency_ms")]
    
    avg_hit_latency = sum(hit_latencies) / len(hit_latencies) if hit_latencies else 0.0
    avg_miss_latency = sum(miss_latencies) / len(miss_latencies) if miss_latencies else 0.0
    
    # Estimate cost savings (assuming cache hits save LLM calls)
    # Rough estimate: each cache miss would have cost ~$0.001 (very rough)
    estimated_savings = hits * 0.001  # Very rough estimate
    
    # Breakdown by cache type
    cache_type_stats = {}
    for op in filtered_ops:
        cache_type = op.get("cache_type", "unknown")
        operation = op.get("operation")
        
        if cache_type not in cache_type_stats:
            cache_type_stats[cache_type] = {"hits": 0, "misses": 0}
        
        if operation == "hit":
            cache_type_stats[cache_type]["hits"] += 1
        elif operation == "miss":
            cache_type_stats[cache_type]["misses"] += 1
    
    cache_type_breakdown = [
        {
            "cache_type": cache_type,
            "hits": stats["hits"],
            "misses": stats["misses"],
            "total": stats["hits"] + stats["misses"],
            "hit_rate": round(stats["hits"] / (stats["hits"] + stats["misses"]) if (stats["hits"] + stats["misses"]) > 0 else 0, 4),
        }
        for cache_type, stats in cache_type_stats.items()
    ]
    
    return {
        "tenant_id": tenant_id,
        "user_id": user_id,
        "period_days": days,
        "summary": {
            "total_operations": total,
            "hits": hits,
            "misses": misses,
            "hit_rate": round(hit_rate, 4),
            "miss_rate": round(miss_rate, 4),
            "estimated_cost_savings": round(estimated_savings, 4),
        },
        "performance": {
            "avg_hit_latency_ms": round(avg_hit_latency, 2),
            "avg_miss_latency_ms": round(avg_miss_latency, 2),
            "latency_improvement_ms": round(avg_miss_latency - avg_hit_latency, 2) if avg_miss_latency > 0 else 0.0,
        },
        "cache_type_breakdown": cache_type_breakdown,
    }


@router.get("/latency")
async def get_latency_dashboard(
    request: Request,
    db: AsyncSession = Depends(get_db),
    days: int = Query(7, description="Number of days to analyze"),
):
    """
    Latency Dashboard - Shows latency metrics and identifies bottlenecks.
    
    Returns:
    - Average latency by operation type
    - P50, P95, P99 latencies
    - Latency trends over time
    - Bottleneck identification
    """
    tenant_id = request.state.tenant_id
    user_id = getattr(request.state, "user_id", None)
    
    # Check if user is admin - if admin, don't filter by user_id to get aggregate data
    is_admin = False
    try:
        from apps.api.routes.admin import check_admin_role
        is_admin = await check_admin_role(request, db)
    except Exception as e:
        # If admin check fails, assume not admin
        print(f"[METRICS] Could not check admin role: {e}")
        is_admin = False
    
    # If admin, set user_id to None to get aggregate data across all users
    if is_admin:
        user_id = None
        print(f"[METRICS] Admin user detected for latency, returning aggregate data for tenant {tenant_id}")
    
    metrics = get_metrics_collector()
    
    # Get LLM calls with latency data
    with metrics._lock:
        llm_calls = []
        for m in metrics._llm_calls:
            # Check tenant match
            if str(m.get("tenant_id")) != str(tenant_id):
                continue
            
            # Check latency exists
            if not m.get("latency_ms"):
                continue
            
            # Check user match - if user_id is provided (and not admin), metric MUST have matching user_id
            if user_id:
                metric_user_id = m.get("user_id")
                if not metric_user_id or str(metric_user_id) != str(user_id):
                    continue
            
            llm_calls.append(m)
    
    # Filter by date range
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    filtered_calls = []
    for call in llm_calls:
        try:
            call_time = datetime.fromisoformat(call.get("timestamp", ""))
            if call_time >= cutoff_date:
                filtered_calls.append(call)
        except:
            continue
    
    # Extract latencies
    latencies = [call.get("latency_ms", 0) for call in filtered_calls if call.get("latency_ms")]
    
    if not latencies:
        return {
            "tenant_id": tenant_id,
            "user_id": None if is_admin else user_id,  # Return None for admin to indicate aggregate data
            "period_days": days,
            "summary": {
                "total_calls": 0,
                "avg_latency_ms": 0,
                "p50_latency_ms": 0,
                "p95_latency_ms": 0,
                "p99_latency_ms": 0,
            },
            "by_model": [],
            "by_feature": [],
            "daily_breakdown": [],
        }
    
    # Calculate percentiles
    sorted_latencies = sorted(latencies)
    n = len(sorted_latencies)
    
    p50 = sorted_latencies[int(n * 0.50)] if n > 0 else 0
    p95 = sorted_latencies[int(n * 0.95)] if n > 0 else 0
    p99 = sorted_latencies[int(n * 0.99)] if n > 0 else 0
    avg_latency = sum(latencies) / len(latencies) if latencies else 0
    
    # Breakdown by model
    model_latencies = {}
    for call in filtered_calls:
        model = call.get("model", "unknown")
        latency = call.get("latency_ms", 0)
        if model not in model_latencies:
            model_latencies[model] = []
        model_latencies[model].append(latency)
    
    model_breakdown = [
        {
            "model": model,
            "avg_latency_ms": round(sum(lats) / len(lats), 2),
            "p95_latency_ms": round(sorted(lats)[int(len(lats) * 0.95)] if len(lats) > 0 else 0, 2),
            "call_count": len(lats),
        }
        for model, lats in model_latencies.items()
    ]
    
    # Breakdown by feature
    feature_latencies = {}
    for call in filtered_calls:
        feature = call.get("feature_tag", "unknown")
        latency = call.get("latency_ms", 0)
        if feature not in feature_latencies:
            feature_latencies[feature] = []
        feature_latencies[feature].append(latency)
    
    feature_breakdown = [
        {
            "feature": feature,
            "avg_latency_ms": round(sum(lats) / len(lats), 2),
            "p95_latency_ms": round(sorted(lats)[int(len(lats) * 0.95)] if len(lats) > 0 else 0, 2),
            "call_count": len(lats),
        }
        for feature, lats in feature_latencies.items()
    ]
    
    # Daily breakdown
    daily_latencies = {}
    for call in filtered_calls:
        try:
            call_time = datetime.fromisoformat(call.get("timestamp", ""))
            date_key = call_time.date().isoformat()
            if date_key not in daily_latencies:
                daily_latencies[date_key] = []
            daily_latencies[date_key].append(call.get("latency_ms", 0))
        except:
            pass
    
    daily_breakdown = [
        {
            "date": date,
            "avg_latency_ms": round(sum(lats) / len(lats), 2),
            "p95_latency_ms": round(sorted(lats)[int(len(lats) * 0.95)] if len(lats) > 0 else 0, 2),
            "call_count": len(lats),
        }
        for date, lats in sorted(daily_latencies.items())
    ]
    
    # Identify bottlenecks (operations with P95 > 5 seconds)
    bottlenecks = []
    for model, lats in model_latencies.items():
        if lats:
            p95 = sorted(lats)[int(len(lats) * 0.95)]
            if p95 > 5000:  # 5 seconds
                bottlenecks.append({
                    "type": "model",
                    "name": model,
                    "p95_latency_ms": round(p95, 2),
                    "severity": "high" if p95 > 10000 else "medium",
                })
    
    for feature, lats in feature_latencies.items():
        if lats:
            p95 = sorted(lats)[int(len(lats) * 0.95)]
            if p95 > 5000:  # 5 seconds
                bottlenecks.append({
                    "type": "feature",
                    "name": feature,
                    "p95_latency_ms": round(p95, 2),
                    "severity": "high" if p95 > 10000 else "medium",
                })
    
    return {
        "tenant_id": tenant_id,
        "user_id": None if is_admin else user_id,  # Return None for admin to indicate aggregate data
        "period_days": days,
        "summary": {
            "total_calls": len(filtered_calls),
            "avg_latency_ms": round(avg_latency, 2),
            "p50_latency_ms": round(p50, 2),
            "p95_latency_ms": round(p95, 2),
            "p99_latency_ms": round(p99, 2),
        },
        "by_model": sorted(model_breakdown, key=lambda x: x["avg_latency_ms"], reverse=True),
        "by_feature": sorted(feature_breakdown, key=lambda x: x["avg_latency_ms"], reverse=True),
        "daily_breakdown": daily_breakdown,
        "bottlenecks": bottlenecks,
    }


@router.get("/logs")
async def get_logs(
    request: Request,
    db: AsyncSession = Depends(get_db),
    days: int = Query(7, description="Number of days to retrieve logs"),
    limit: int = Query(1000, description="Maximum number of log entries to return"),
    event_type: Optional[str] = Query(None, description="Filter by event type"),
):
    """
    Get system logs from metrics data.
    
    Returns log entries from:
    - LLM calls (queries, errors, successes)
    - Cache operations
    - Feature usage
    - Document processing
    
    Args:
        days: Number of days to retrieve logs for
        limit: Maximum number of entries to return
        event_type: Optional filter by event type (query, error, success, warning, info, cache)
    """
    tenant_id = request.state.tenant_id
    user_id = getattr(request.state, "user_id", None)
    
    # Check if user is admin - if admin, don't filter by user_id to get all logs
    is_admin = False
    try:
        from apps.api.routes.admin import check_admin_role
        is_admin = await check_admin_role(request, db)
    except Exception:
        pass
    
    metrics = get_metrics_collector()
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    logs = []
    
    with metrics._lock:
        # Get LLM calls as log entries
        llm_calls = list(metrics._llm_calls)
        if tenant_id:
            llm_calls = [m for m in llm_calls if str(m.get("tenant_id")) == str(tenant_id)]
        if user_id and not is_admin:
            llm_calls = [m for m in llm_calls if str(m.get("user_id")) == str(user_id)]
        
        for call in llm_calls:
            try:
                call_time = datetime.fromisoformat(call.get("timestamp", ""))
                if call_time >= cutoff_date:
                    # Determine event type based on latency and errors
                    event_type_log = "query"
                    message = f"LLM call: {call.get('model', 'unknown')} - {call.get('total_tokens', 0)} tokens"
                    
                    if call.get("latency_ms", 0) > 10000:
                        event_type_log = "warning"
                        message = f"Slow LLM call: {call.get('model', 'unknown')} - {call.get('latency_ms', 0):.0f}ms latency"
                    
                    logs.append({
                        "timestamp": call.get("timestamp"),
                        "event_type": event_type_log,
                        "user": call.get("user_id", "unknown"),
                        "message": message,
                        "level": "info",
                        "metadata": {
                            "model": call.get("model"),
                            "tokens": call.get("total_tokens"),
                            "cost": call.get("cost"),
                            "latency_ms": call.get("latency_ms"),
                            "feature": call.get("feature_tag"),
                        }
                    })
            except:
                continue
        
        # Get cache operations as log entries
        cache_ops = list(metrics._cache_operations)
        if tenant_id:
            cache_ops = [m for m in cache_ops if str(m.get("tenant_id")) == str(tenant_id)]
        if user_id and not is_admin:
            cache_ops = [m for m in cache_ops if m.get("user_id") and str(m.get("user_id")) == str(user_id)]
        
        for op in cache_ops:
            try:
                op_time = datetime.fromisoformat(op.get("timestamp", ""))
                if op_time >= cutoff_date:
                    operation = op.get("operation", "unknown")
                    cache_type = op.get("cache_type", "unknown")
                    logs.append({
                        "timestamp": op.get("timestamp"),
                        "event_type": "cache",
                        "user": op.get("user_id", "system"),
                        "message": f"Cache {operation}: {cache_type}",
                        "level": "info" if operation == "hit" else "warning",
                        "metadata": {
                            "operation": operation,
                            "cache_type": cache_type,
                            "latency_ms": op.get("latency_ms"),
                        }
                    })
            except:
                continue
        
        # Get feature usage as log entries
        feature_usage = list(metrics._feature_usage)
        if tenant_id:
            feature_usage = [m for m in feature_usage if str(m.get("tenant_id")) == str(tenant_id)]
        if user_id and not is_admin:
            feature_usage = [m for m in feature_usage if m.get("user_id") and str(m.get("user_id")) == str(user_id)]
        
        for usage in feature_usage:
            try:
                usage_time = datetime.fromisoformat(usage.get("timestamp", ""))
                if usage_time >= cutoff_date:
                    logs.append({
                        "timestamp": usage.get("timestamp"),
                        "event_type": "info",
                        "user": usage.get("user_id", "unknown"),
                        "message": f"Feature used: {usage.get('feature', 'unknown')}",
                        "level": "info",
                        "metadata": {
                            "feature": usage.get("feature"),
                        }
                    })
            except:
                continue
    
    # Filter by event type if specified
    if event_type:
        logs = [log for log in logs if log.get("event_type") == event_type]
    
    # Sort by timestamp descending
    logs.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    
    # Limit results
    logs = logs[:limit]
    
    return {
        "tenant_id": tenant_id,
        "user_id": None if is_admin else user_id,
        "period_days": days,
        "logs": logs,
        "total": len(logs),
    }


@router.get("/agents/summary")
async def get_agents_summary(
    request: Request,
    db: AsyncSession = Depends(get_db),
    days: int = Query(30, description="Current window in days"),
    compare_days: int = Query(30, description="Previous comparison window in days"),
):
    tenant_id = request.state.tenant_id
    user_id = getattr(request.state, "user_id", None)
    is_admin = await _is_admin_request(request, db)
    if is_admin:
        user_id = None

    metrics = get_metrics_collector()
    now = datetime.utcnow()
    cur_start = now - timedelta(days=days)
    prev_start = cur_start - timedelta(days=compare_days)

    with metrics._lock:
        all_calls = list(metrics._llm_calls)
    scoped = [m for m in all_calls if str(m.get("tenant_id")) == str(tenant_id)]
    if user_id:
        scoped = [m for m in scoped if str(m.get("user_id")) == str(user_id)]

    cur_calls = [m for m in scoped if (_iso_to_dt(m.get("timestamp")) or datetime.min) >= cur_start]
    prev_calls = [
        m for m in scoped
        if prev_start <= (_iso_to_dt(m.get("timestamp")) or datetime.min) < cur_start
    ]

    try:
        from packages.core.monitoring.pipeline_trace import get_pipeline_trace_store
        store = get_pipeline_trace_store()
        traces = store.list_recent_traces_filtered(user_id=user_id, limit=200)
        trace_errors_by_agent: Dict[str, int] = defaultdict(int)
        for tr in traces:
            if str(tr.tenant_id) != str(tenant_id):
                continue
            for sp in tr.spans:
                if str(sp.status) == "error":
                    aid = _normalize_agent_id(sp.feature_tag or sp.name)
                    trace_errors_by_agent[aid] += 1
    except Exception:
        trace_errors_by_agent = defaultdict(int)

    cur_stats = _collect_agent_stats(cur_calls, trace_errors_by_agent)
    prev_stats = _collect_agent_stats(prev_calls, {})

    totals = {
        "total_calls": sum(v["calls"] for v in cur_stats.values()),
        "total_cost": round(sum(v["cost_total"] for v in cur_stats.values()), 6),
        "total_tokens": sum(v["tokens_total"] for v in cur_stats.values()),
        "active_agents": len([v for v in cur_stats.values() if v["calls"] > 0]),
        "avg_latency_ms": round(
            (sum(v["latency_avg_ms"] * v["calls"] for v in cur_stats.values()) / max(sum(v["calls"] for v in cur_stats.values()), 1)),
            2,
        ),
        "p95_latency_ms": round(max([v["latency_p95_ms"] for v in cur_stats.values()] or [0.0]), 2),
        "error_rate": round(
            (sum(v["error_count"] for v in cur_stats.values()) / max(sum(v["calls"] for v in cur_stats.values()), 1)),
            4,
        ),
    }

    prev_totals = {
        "total_calls": sum(v["calls"] for v in prev_stats.values()),
        "total_cost": round(sum(v["cost_total"] for v in prev_stats.values()), 6),
        "total_tokens": sum(v["tokens_total"] for v in prev_stats.values()),
        "avg_latency_ms": round(
            (sum(v["latency_avg_ms"] * v["calls"] for v in prev_stats.values()) / max(sum(v["calls"] for v in prev_stats.values()), 1)),
            2,
        ),
    }

    top_agents = sorted(cur_stats.values(), key=lambda x: x["calls"], reverse=True)[:10]
    return {
        "tenant_id": tenant_id,
        "user_id": user_id,
        "period_days": days,
        "compare_days": compare_days,
        "totals": totals,
        "deltas": {
            "calls_pct": _pct_delta(float(totals["total_calls"]), float(prev_totals["total_calls"])),
            "cost_pct": _pct_delta(float(totals["total_cost"]), float(prev_totals["total_cost"])),
            "tokens_pct": _pct_delta(float(totals["total_tokens"]), float(prev_totals["total_tokens"])),
            "latency_pct": _pct_delta(float(totals["avg_latency_ms"]), float(prev_totals["avg_latency_ms"])),
        },
        "top_agents": top_agents,
    }


@router.get("/agents/details")
async def get_agents_details(
    request: Request,
    db: AsyncSession = Depends(get_db),
    days: int = Query(30),
):
    tenant_id = request.state.tenant_id
    user_id = getattr(request.state, "user_id", None)
    is_admin = await _is_admin_request(request, db)
    if is_admin:
        user_id = None
    metrics = get_metrics_collector()
    cutoff = datetime.utcnow() - timedelta(days=days)

    with metrics._lock:
        calls = list(metrics._llm_calls)
    calls = [m for m in calls if str(m.get("tenant_id")) == str(tenant_id)]
    if user_id:
        calls = [m for m in calls if str(m.get("user_id")) == str(user_id)]
    calls = [m for m in calls if (_iso_to_dt(m.get("timestamp")) or datetime.min) >= cutoff]

    try:
        from packages.core.monitoring.pipeline_trace import get_pipeline_trace_store
        store = get_pipeline_trace_store()
        traces = store.list_recent_traces_filtered(user_id=user_id, limit=200)
        err_counts: Dict[str, int] = defaultdict(int)
        for tr in traces:
            if str(tr.tenant_id) != str(tenant_id):
                continue
            for sp in tr.spans:
                if str(sp.status) == "error":
                    err_counts[_normalize_agent_id(sp.feature_tag or sp.name)] += 1
    except Exception:
        err_counts = defaultdict(int)

    rows = list(_collect_agent_stats(calls, err_counts).values())
    # Always include the known LLM agent catalog so admins can see missing/idle agents too.
    existing_ids = {r["agent_id"] for r in rows}
    for agent_id, meta in _AGENT_CATALOG.items():
        if agent_id == "other":
            continue
        if agent_id in existing_ids:
            continue
        rows.append(
            {
                "agent_id": agent_id,
                "agent_label": meta["label"],
                "description": meta["description"],
                "category": meta.get("category", "utility"),
                "calls": 0,
                "tokens_in": 0,
                "tokens_out": 0,
                "tokens_total": 0,
                "cost_total": 0.0,
                "latency_avg_ms": 0.0,
                "latency_p95_ms": 0.0,
                "error_count": 0,
                "error_rate": 0.0,
                "providers": {},
                "models": {},
                "feature_tags": {},
                "last_seen_at": None,
            }
        )
    rows.sort(key=lambda x: (x["calls"], x["tokens_total"]), reverse=True)
    return {"tenant_id": tenant_id, "user_id": user_id, "period_days": days, "rows": rows}


@router.get("/agents/timeseries")
async def get_agents_timeseries(
    request: Request,
    db: AsyncSession = Depends(get_db),
    days: int = Query(30),
):
    tenant_id = request.state.tenant_id
    user_id = getattr(request.state, "user_id", None)
    is_admin = await _is_admin_request(request, db)
    if is_admin:
        user_id = None
    metrics = get_metrics_collector()
    cutoff = datetime.utcnow() - timedelta(days=days)

    with metrics._lock:
        calls = list(metrics._llm_calls)
    calls = [m for m in calls if str(m.get("tenant_id")) == str(tenant_id)]
    if user_id:
        calls = [m for m in calls if str(m.get("user_id")) == str(user_id)]
    calls = [m for m in calls if (_iso_to_dt(m.get("timestamp")) or datetime.min) >= cutoff]

    buckets: Dict[str, Dict[str, Any]] = {}
    for c in calls:
        ts = _iso_to_dt(c.get("timestamp"))
        if not ts:
            continue
        day = ts.date().isoformat()
        if day not in buckets:
            buckets[day] = {"date": day, "calls": 0, "tokens": 0, "cost": 0.0, "latencies": []}
        b = buckets[day]
        b["calls"] += 1
        b["tokens"] += int(c.get("total_tokens") or 0)
        b["cost"] += float(c.get("cost") or 0.0)
        lat = c.get("latency_ms")
        if isinstance(lat, (float, int)):
            b["latencies"].append(float(lat))

    series = []
    for day in sorted(buckets.keys()):
        b = buckets[day]
        latencies = sorted(b["latencies"])
        n = len(latencies)
        avg = (sum(latencies) / n) if n else 0.0
        p95 = latencies[min(int(n * 0.95), n - 1)] if n else 0.0
        series.append(
            {
                "date": day,
                "calls": b["calls"],
                "tokens": b["tokens"],
                "cost": round(b["cost"], 6),
                "avg_latency_ms": round(avg, 2),
                "p95_latency_ms": round(p95, 2),
            }
        )

    return {"tenant_id": tenant_id, "user_id": user_id, "period_days": days, "series": series}


@router.get("/agents/recent")
async def get_agents_recent(
    request: Request,
    db: AsyncSession = Depends(get_db),
    limit: int = Query(50),
):
    tenant_id = request.state.tenant_id
    user_id = getattr(request.state, "user_id", None)
    is_admin = await _is_admin_request(request, db)
    if is_admin:
        user_id = None
    limit = max(1, min(int(limit), 200))

    out: List[Dict[str, Any]] = []
    try:
        from packages.core.monitoring.pipeline_trace import get_pipeline_trace_store
        store = get_pipeline_trace_store()
        traces = store.list_recent_traces_filtered(user_id=user_id, limit=limit)
        for tr in traces:
            if str(tr.tenant_id) != str(tenant_id):
                continue
            for sp in tr.spans:
                out.append(
                    {
                        "trace_id": tr.trace_id,
                        "timestamp": datetime.utcfromtimestamp((sp.end_ms or tr.started_at_ms) / 1000.0).isoformat(),
                        "agent_id": _normalize_agent_id(sp.feature_tag or sp.name),
                        "agent_name": sp.name,
                        "status": sp.status,
                        "duration_ms": round(float(sp.duration_ms or 0.0), 2),
                        "error_message": sp.error_message,
                        "feature_tag": sp.feature_tag,
                    }
                )
        out.sort(key=lambda x: x["timestamp"], reverse=True)
        out = out[:limit]
    except Exception:
        out = []

    return {"tenant_id": tenant_id, "user_id": user_id, "limit": limit, "rows": out}


@router.get("/agents/export.csv")
async def export_agents_csv(
    request: Request,
    db: AsyncSession = Depends(get_db),
    days: int = Query(30),
):
    details = await get_agents_details(request, db, days)
    rows = details.get("rows", [])
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(
        [
            "agent_id",
            "agent_label",
            "calls",
            "tokens_in",
            "tokens_out",
            "tokens_total",
            "cost_total",
            "latency_avg_ms",
            "latency_p95_ms",
            "error_count",
            "error_rate",
            "last_seen_at",
        ]
    )
    for r in rows:
        writer.writerow(
            [
                r.get("agent_id"),
                r.get("agent_label"),
                r.get("calls"),
                r.get("tokens_in"),
                r.get("tokens_out"),
                r.get("tokens_total"),
                r.get("cost_total"),
                r.get("latency_avg_ms"),
                r.get("latency_p95_ms"),
                r.get("error_count"),
                r.get("error_rate"),
                r.get("last_seen_at"),
            ]
        )
    csv_body = buf.getvalue()
    return Response(
        content=csv_body,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename=\"agents_{days}d.csv\"'},
    )


@router.delete("/reset")
async def reset_all_metrics(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Reset all metrics data.
    
    This will permanently delete:
    - All in-memory metrics
    - All persisted metrics log files
    - All alerts
    
    Use with caution - this action cannot be undone.
    """
    tenant_id = request.state.tenant_id
    user_id = getattr(request.state, "user_id", None)
    
    metrics = get_metrics_collector()
    alert_manager = get_alert_manager()
    
    # Reset metrics
    metrics_result = metrics.reset_all_metrics()
    
    # Reset alerts
    alerts_result = alert_manager.reset_all_alerts()
    
    return {
        "tenant_id": tenant_id,
        "user_id": user_id,
        "status": "success",
        "metrics": metrics_result,
        "alerts": alerts_result,
        "message": "All metrics and alerts have been reset"
    }
