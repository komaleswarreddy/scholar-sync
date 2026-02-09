# Phase 4: Session Memory & Caching

## Overview

Phase 4 implements session memory management and caching to optimize token usage and prevent unnecessary LLM calls.

## Features Implemented

### 1. ✅ Debounce & Rate Limiting

**File**: `packages/core/memory/rate_limiter.py`

Prevents accidental multi-calls and abuse:
- **Debounce**: Minimum time between identical queries (default: 2 seconds)
- **Rate Limiting**: Maximum requests per minute (default: 30) and per hour (default: 500)
- **User-based**: Tracks requests per user
- **Automatic cleanup**: Removes old entries to prevent memory growth

**Configuration**:
```python
ENABLE_RATE_LIMITING: bool = True
RATE_LIMIT_REQUESTS_PER_MINUTE: int = 30
RATE_LIMIT_DEBOUNCE_SECONDS: float = 2.0
```

**Integration**: 
- Applied in `apps/api/routes/chat.py` before processing requests
- Returns `429 Too Many Requests` if rate limit exceeded

### 2. ✅ Answer Caching for Repeated Queries

**File**: `packages/core/memory/answer_cache.py`

Caches answers to skip LLM calls for repeated queries:
- **Query Normalization**: Case-insensitive, whitespace handling
- **Context-Aware**: Considers active source IDs in cache key
- **TTL-based Expiration**: Default 1 hour
- **Persistent Storage**: Saves to disk for persistence across restarts
- **Cache Statistics**: Tracks hits, misses, hit rate

**Configuration**:
```python
ENABLE_ANSWER_CACHE: bool = True
ANSWER_CACHE_TTL_SECONDS: int = 3600  # 1 hour
```

**Integration**:
- Checks cache before retrieval in `packages/core/services/rag_service.py`
- Caches answers after generation
- Returns cached answer immediately if found

**Cache Key**: Hash of (normalized_query + sorted_source_ids)

### 3. ✅ Periodic Chat Summarization

**File**: `packages/core/memory/chat_summarizer.py`

Summarizes chat history to reduce tokens:
- **Trigger**: When history exceeds threshold (default: 10 messages)
- **Recent Window**: Keeps last N messages unsummarized (default: 5)
- **Two Modes**:
  - Simple summarization (fast, no LLM cost)
  - LLM-based summarization (more accurate, costs tokens)
- **Preserves Context**: Maintains key information in summary

**Configuration**:
```python
ENABLE_CHAT_SUMMARIZATION: bool = True
CHAT_SUMMARIZE_AFTER: int = 10
CHAT_KEEP_RECENT: int = 5
```

**Integration**:
- Applied in `packages/core/services/rag_service.py` before retrieval
- Summarizes old messages, keeps recent messages intact

### 4. ✅ Session Memory Pruning

**File**: `packages/core/memory/memory_manager.py`

Prunes chat history to avoid full chat replay:
- **Max History**: Limits messages (default: 20) and tokens (default: 2000)
- **Pruning Strategies**:
  - `recent`: Keep only recent messages
  - `relevance`: Keep recent + relevant to current query
  - `summary`: Summarize old messages, keep recent
- **Always Keeps Recent**: Last N messages always preserved (default: 5)

**Configuration**:
```python
ENABLE_MEMORY_PRUNING: bool = True
MAX_HISTORY_MESSAGES: int = 20
MAX_HISTORY_TOKENS: int = 2000
MEMORY_PRUNING_STRATEGY: str = "recent"  # "recent", "relevance", "summary"
```

**Integration**:
- Applied in `packages/core/services/rag_service.py` before retrieval
- Prunes history based on configured strategy

## Settings

All Phase 4 settings in `config/settings.py`:

```python
# Phase 4: Session Memory & Caching
USE_SESSION_MEMORY: bool = True  # Master switch
ENABLE_RATE_LIMITING: bool = True
ENABLE_ANSWER_CACHE: bool = True
ENABLE_CHAT_SUMMARIZATION: bool = True
ENABLE_MEMORY_PRUNING: bool = True

# Rate Limiting
RATE_LIMIT_REQUESTS_PER_MINUTE: int = 30
RATE_LIMIT_DEBOUNCE_SECONDS: float = 2.0

# Answer Cache
ANSWER_CACHE_TTL_SECONDS: int = 3600  # 1 hour

# Chat Summarization
CHAT_SUMMARIZE_AFTER: int = 10
CHAT_KEEP_RECENT: int = 5

# Memory Pruning
MAX_HISTORY_MESSAGES: int = 20
MAX_HISTORY_TOKENS: int = 2000
MEMORY_PRUNING_STRATEGY: str = "recent"  # "recent", "relevance", "summary"
```

## Integration Flow

**Request Flow**:
1. **Rate Limiting** (in `apps/api/routes/chat.py`)
   - Check rate limits and debounce
   - Return 429 if exceeded

2. **Answer Cache** (in `packages/core/services/rag_service.py`)
   - Check cache for repeated query
   - Return cached answer if found

3. **Memory Pruning** (in `packages/core/services/rag_service.py`)
   - Prune history if exceeds limits
   - Apply pruning strategy

4. **Chat Summarization** (in `packages/core/services/rag_service.py`)
   - Summarize old messages if history too long
   - Keep recent messages intact

5. **RAG Retrieval** (normal flow)
   - Retrieve context with pruned/summarized history
   - Generate answer

6. **Cache Answer** (after generation)
   - Cache generated answer for future queries

## Benefits

1. **Token Reduction**:
   - Answer caching: 0 tokens for repeated queries
   - Memory pruning: Reduces history tokens
   - Chat summarization: Compresses old messages

2. **Performance**:
   - Faster responses for cached queries
   - Reduced LLM API calls
   - Lower latency

3. **Cost Savings**:
   - Fewer LLM calls (caching)
   - Fewer input tokens (pruning/summarization)
   - Reduced API costs

4. **User Experience**:
   - Prevents accidental duplicate requests (debounce)
   - Protects against abuse (rate limiting)
   - Maintains context while reducing tokens

## File Structure

```
packages/core/memory/
├── __init__.py              # Package exports
├── rate_limiter.py          # Rate limiting & debounce
├── answer_cache.py          # Answer caching
├── chat_summarizer.py       # Chat summarization
├── memory_manager.py        # Memory pruning
└── context_compressor.py    # Context compression (existing)
```

## Usage Examples

### Rate Limiting
```python
from packages.core.memory import RateLimiter

rate_limiter = RateLimiter(
    max_requests_per_minute=30,
    debounce_seconds=2.0
)

result = rate_limiter.check_rate_limit(user_id, query, tenant_id)
if not result["allowed"]:
    # Handle rate limit
    pass
```

### Answer Caching
```python
from packages.core.memory import AnswerCache

cache = AnswerCache(default_ttl_seconds=3600)

# Check cache
cached = cache.get(query, source_ids, tenant_id)
if cached:
    return cached["answer"]

# Cache answer
cache.set(query, source_ids, answer, citations, tenant_id)
```

### Chat Summarization
```python
from packages.core.memory import ChatSummarizer

summarizer = ChatSummarizer(
    recent_window=5,
    summarize_after=10
)

if summarizer.should_summarize(history):
    result = summarizer.summarize_history(history, query)
    history = result["summarized_history"]
```

### Memory Pruning
```python
from packages.core.memory import MemoryManager

manager = MemoryManager(
    max_history_messages=20,
    max_history_tokens=2000,
    prune_strategy="recent"
)

result = manager.prune_history(history, current_query)
history = result["pruned_history"]
```

## Testing

1. **Rate Limiting**:
   - Send same query twice quickly → second should be debounced
   - Send 30+ requests in a minute → should hit rate limit

2. **Answer Caching**:
   - Send same query twice → second should return cached answer
   - Check cache stats → should show hits

3. **Chat Summarization**:
   - Send 10+ messages → should trigger summarization
   - Check history → should have summary + recent messages

4. **Memory Pruning**:
   - Send 20+ messages → should trigger pruning
   - Check history → should be reduced to max_history_messages

## Notes

- All features are optional and can be disabled via settings
- Rate limiter uses in-memory storage (resets on restart)
- Answer cache persists to disk (survives restarts)
- Memory pruning and summarization are applied per-request
- Cache keys include source IDs for context-aware caching
