"""
Usage Aggregation Task

⚠️ READ-ONLY: Only reads UsageRecord, never writes.

Aggregates usage data for reporting and analytics.
"""

# TODO: Implement usage aggregation
# - Read UsageRecord data
# - Aggregate by tenant, user, time period
# - Generate reports
# - NEVER write to UsageRecord (only CostManager can write)


# @celery_app.task
# async def aggregate_usage(tenant_id: str, start_date: datetime, end_date: datetime):
#     """Aggregate usage data (read-only)."""
#     # TODO: Implement aggregation (read-only)
#     pass


