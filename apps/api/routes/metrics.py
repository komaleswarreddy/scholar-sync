"""
Metrics Dashboard API

Provides endpoints for viewing metrics and dashboard data.
"""

from fastapi import APIRouter, Request, HTTPException, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import uuid

from packages.core.database.connection import get_db
from packages.core.monitoring.metrics import get_metrics_collector
from packages.core.monitoring.alerts import get_alert_manager
from packages.core.guardrails.cost_manager import get_cost_manager
from packages.core.database.models.chat import Message, Chat

router = APIRouter()


@router.get("/summary")
async def get_metrics_summary(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Get metrics summary for the current tenant.
    
    Returns aggregated metrics including:
    - LLM call statistics (tokens, costs)
    - Cache hit/miss rates
    - Feature usage counts
    - Document costs
    - Regenerate attempts
    """
    tenant_id = request.state.tenant_id
    
    metrics = get_metrics_collector()
    summary = metrics.get_metrics_summary(tenant_id=tenant_id)
    
    return {
        "tenant_id": tenant_id,
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
    
    alert_manager = get_alert_manager()
    alerts = alert_manager.get_recent_alerts(
        alert_type=alert_type,
        severity=severity,
        limit=limit
    )
    
    # Filter by tenant if needed
    if tenant_id:
        alerts = [a for a in alerts if a.get("tenant_id") == tenant_id or a.get("tenant_id") is None]
    
    return {
        "tenant_id": tenant_id,
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
    
    metrics = get_metrics_collector()
    alert_manager = get_alert_manager()
    cost_manager = get_cost_manager()
    
    # Get metrics summary
    summary = metrics.get_metrics_summary(tenant_id=tenant_id)
    
    # Get cache hit rate
    cache_hit_rate = metrics.get_cache_hit_rate(tenant_id=tenant_id)
    
    # Get recent alerts
    alerts = alert_manager.get_recent_alerts(limit=50)
    if tenant_id:
        alerts = [a for a in alerts if a.get("tenant_id") == tenant_id or a.get("tenant_id") is None]
    
    # Get usage summary from cost manager
    usage_summary = await cost_manager.get_usage_summary(tenant_id=tenant_id)
    
    return {
        "tenant_id": tenant_id,
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
    
    if not tenant_id:
        return {
            "tenant_id": None,
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
    debug_result = await db.execute(
        select(func.count(Message.id))
        .join(Chat)
        .where(
            and_(
                Chat.tenant_id == tenant_uuid,
                Message.role == 'assistant',
            )
        )
    )
    total_assistant_messages = debug_result.scalar() or 0
    
    feedback_count_result = await db.execute(
        select(func.count(Message.id))
        .join(Chat)
        .where(
            and_(
                Chat.tenant_id == tenant_uuid,
                Message.role == 'assistant',
                Message.feedback.isnot(None),
            )
        )
    )
    total_with_feedback = feedback_count_result.scalar() or 0
    
    print(f"[RAG_QUALITY] Tenant: {tenant_id}, Total assistant messages: {total_assistant_messages}, Messages with feedback: {total_with_feedback}")
    
    # Query with date filter - use CAST to date for timezone-safe date extraction
    result = await db.execute(
        select(
            Message.feedback,
            func.count(Message.id).label('count'),
            func.date(Message.created_at).label('date')
        )
        .join(Chat)
        .where(
            and_(
                Chat.tenant_id == tenant_uuid,
                Message.role == 'assistant',
                Message.feedback.isnot(None),
                Message.created_at >= start_date,
                Message.created_at <= end_date
            )
        )
        .group_by(Message.feedback, func.date(Message.created_at))
    )
    
    feedback_data = result.all()
    print(f"[RAG_QUALITY] Found {len(feedback_data)} feedback rows in date range ({start_date} to {end_date})")
    
    # If no data in date range, try without date filter to see if there's any feedback at all
    if len(feedback_data) == 0 and total_with_feedback > 0:
        print(f"[RAG_QUALITY] WARNING: No feedback in date range, but {total_with_feedback} messages have feedback. Date range might be too restrictive.")
        # Try querying without date filter to get all feedback
        result_all = await db.execute(
            select(
                Message.feedback,
                func.count(Message.id).label('count'),
                func.date(Message.created_at).label('date')
            )
            .join(Chat)
            .where(
                and_(
                    Chat.tenant_id == tenant_uuid,
                    Message.role == 'assistant',
                    Message.feedback.isnot(None),
                )
            )
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
    metrics = get_metrics_collector()
    
    # Get all LLM calls from in-memory storage
    with metrics._lock:
        llm_calls = [
            m for m in metrics._llm_calls
            if m.get("tenant_id") == tenant_id
        ]
    
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
    total_tokens = 0
    total_calls = len(filtered_calls)
    
    for call in filtered_calls:
        tokens = call.get("total_tokens", 0)
        total_tokens += tokens
        
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
                "total_calls": 0,
                "avg_tokens": 0,
                "cost": 0.0,
            }
        
        grouped[key]["total_tokens"] += tokens
        grouped[key]["total_calls"] += 1
        grouped[key]["cost"] += call.get("cost", 0.0)
        
        # Daily totals
        try:
            call_time = datetime.fromisoformat(call.get("timestamp", ""))
            date_key = call_time.date().isoformat()
            if date_key not in daily_totals:
                daily_totals[date_key] = 0
            daily_totals[date_key] += tokens
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
            "total_calls": stats["total_calls"],
            "avg_tokens": round(stats["avg_tokens"], 2),
            "cost": round(stats["cost"], 4),
            "percentage": round((stats["total_tokens"] / total_tokens * 100) if total_tokens > 0 else 0, 2),
        }
        for key, stats in sorted(grouped.items(), key=lambda x: x[1]["total_tokens"], reverse=True)
    ]
    
    # Daily breakdown
    daily_breakdown = [
        {"date": date, "tokens": tokens}
        for date, tokens in sorted(daily_totals.items())
    ]
    
    return {
        "tenant_id": tenant_id,
        "period_days": days,
        "group_by": group_by,
        "summary": {
            "total_tokens": total_tokens,
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
    metrics = get_metrics_collector()
    
    # Get all LLM calls
    with metrics._lock:
        llm_calls = [
            m for m in metrics._llm_calls
            if m.get("tenant_id") == tenant_id
        ]
    
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
    metrics = get_metrics_collector()
    
    # Get cache operations
    with metrics._lock:
        cache_ops = [
            m for m in metrics._cache_operations
            if m.get("tenant_id") == tenant_id
        ]
    
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
    metrics = get_metrics_collector()
    
    # Get LLM calls with latency data
    with metrics._lock:
        llm_calls = [
            m for m in metrics._llm_calls
            if m.get("tenant_id") == tenant_id and m.get("latency_ms")
        ]
    
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
