# Metrics Persistence Fix

## Problem
Metrics were resetting to 0 on server restart/refresh because they were only stored in memory.

## Solution
Implemented persistent metrics storage by loading metrics from log files on startup.

## Changes Made

### 1. ✅ Load Metrics on Startup
**File**: `packages/core/monitoring/metrics.py`

- Added `_load_persisted_metrics()` method that loads metrics from JSONL log files on initialization
- Loads last 10,000 LLM calls, cache operations, feature usage, and regenerate attempts
- Loads all document costs
- Updates aggregated counters (cache stats, feature counts, etc.)

### 2. ✅ Improved Error Handling
- Added try-catch blocks for each log file type
- Validates metric structure before loading
- Skips malformed lines gracefully
- Logs detailed information about what was loaded

### 3. ✅ Enhanced Debugging
- Added detailed logging when metrics are loaded
- Logs warnings when no metrics found
- Checks if log files exist and their sizes
- Shows breakdown of loaded metrics

### 4. ✅ Reload Method
- Added `reload_metrics_from_logs()` method to manually reload metrics
- Useful for refreshing metrics after they've been written

## How It Works

**On Server Startup:**
1. `MetricsCollector.__init__()` is called
2. `_load_persisted_metrics()` is called automatically
3. Metrics are loaded from `logs/metrics/*.jsonl` files
4. In-memory storage is populated with persisted metrics
5. Aggregated counters are updated

**On Metrics Retrieval:**
1. `get_metrics_summary()` reads from in-memory storage
2. Metrics are filtered by tenant_id if provided
3. Aggregated statistics are calculated
4. Returns summary with all metrics

**On Metrics Recording:**
1. Metrics are written to in-memory storage (deques)
2. Metrics are also written to log files (JSONL format)
3. Log files persist across server restarts

## Log Files Location

Metrics are stored in: `logs/metrics/`

Files:
- `llm_calls.jsonl` - LLM API call metrics
- `cache_operations.jsonl` - Cache hit/miss operations
- `document_costs.jsonl` - Document processing costs
- `feature_usage.jsonl` - Feature usage tracking
- `regenerate_attempts.jsonl` - Regenerate button attempts

## Expected Behavior

**Before Fix:**
- Server restart → Metrics reset to 0
- Page refresh → Metrics might reset if singleton recreated

**After Fix:**
- Server restart → Metrics loaded from log files
- Page refresh → Metrics persist (same singleton instance)
- Metrics accumulate over time

## Debugging

If metrics are still showing 0:

1. **Check log files exist:**
   ```bash
   ls -lh logs/metrics/
   ```

2. **Check log file contents:**
   ```bash
   tail -n 10 logs/metrics/llm_calls.jsonl
   ```

3. **Check server logs:**
   Look for:
   - `[METRICS] Loaded X LLM call metrics from log file`
   - `[METRICS] Metrics persistence: Loaded X total metrics`
   - `[METRICS] WARNING: No metrics found for tenant_id=...`

4. **Check tenant_id matching:**
   - Ensure metrics are recorded with the same tenant_id format
   - Check if tenant_id filtering is excluding metrics

5. **Verify metrics are being recorded:**
   - Check for `[METRICS] Recorded LLM call: ...` in logs
   - Verify log files are being written to

## Testing

1. **Record some metrics:**
   - Send a chat message
   - Upload a document
   - Use features

2. **Check metrics endpoint:**
   ```bash
   curl http://localhost:8000/api/v1/metrics/dashboard
   ```

3. **Restart server:**
   ```bash
   # Stop server
   # Start server
   ```

4. **Check metrics again:**
   - Metrics should persist (not reset to 0)
   - Check server logs for "Loaded X metrics from log file"

## Notes

- Metrics are loaded on startup, not on every request (for performance)
- Only last 10,000 entries are loaded (most recent)
- Log files grow over time - consider log rotation for production
- Metrics are filtered by tenant_id when retrieving
- If no tenant_id provided, returns metrics for all tenants
