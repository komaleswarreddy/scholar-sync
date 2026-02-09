# Input Token Optimization

## Overview
This document describes the optimizations implemented to reduce input token usage in the RAG pipeline.

## Problem
Input tokens were consuming too much of the token budget, leading to high costs and potential context window limits.

## Solutions Implemented

### 1. ✅ Reduced Context Budget
**Settings**: `CONTEXT_TOKEN_BUDGET = 2500` (reduced from 4000)
- **Savings**: ~37.5% reduction in context token budget
- **Impact**: Lower input token usage while maintaining quality

### 2. ✅ Reduced Chunk Counts
**Settings**:
- `MAX_CONTEXT_CHUNKS = 8` (reduced from 10)
- `MIN_CONTEXT_CHUNKS = 4` (reduced from 6)
- **Savings**: 20-40% fewer chunks sent to LLM
- **Impact**: Lower input tokens while maintaining minimum quality

### 3. ✅ Chunk Text Truncation
**Setting**: `MAX_CHUNK_LENGTH = 500` characters per chunk
- **Implementation**: Truncates chunks at sentence boundaries
- **Savings**: 30-50% reduction per chunk if chunks are long
- **Impact**: Preserves important information while reducing tokens

### 4. ✅ Chunk Compression for Lower-Scoring Chunks
**Setting**: `USE_CHUNK_COMPRESSION = true`
- **Strategy**: 
  - Top 4 chunks: Full text (up to MAX_CHUNK_LENGTH)
  - Chunks 5+: Compressed to 300 chars + first sentence if score < 0.7
- **Savings**: 40-60% reduction for lower-scoring chunks
- **Impact**: Prioritizes high-relevance chunks while reducing overall tokens

### 5. ✅ Optimized Prompt Template
**Changes**:
- Removed verbose instructions
- Condensed format requirements
- Shorter context header
- **Savings**: ~100-200 tokens per request
- **Impact**: More tokens available for actual context

### 6. ✅ Context Compression
**Implementation**: Automatic compression if context exceeds budget
- Truncates lower-priority chunks (chunks 4+)
- Preserves top 3 chunks fully
- Respects token budget strictly
- **Savings**: 20-30% additional reduction when needed

## Configuration

Add to `.env`:
```env
CONTEXT_TOKEN_BUDGET=2500          # Reduced from 4000 (37.5% reduction)
MAX_CONTEXT_CHUNKS=8               # Reduced from 10 (20% reduction)
MIN_CONTEXT_CHUNKS=4               # Reduced from 6 (33% reduction)
MAX_CHUNK_LENGTH=500                # Max characters per chunk (truncate if longer)
USE_CHUNK_COMPRESSION=true         # Compress lower-scoring chunks
```

## Expected Token Savings

### Per Request:
- **Context Budget**: 4000 → 2500 tokens = **-37.5%**
- **Chunk Count**: 10 → 8 chunks = **-20%**
- **Chunk Truncation**: 30-50% per long chunk
- **Compression**: 40-60% for lower-scoring chunks
- **Prompt**: ~100-200 tokens saved

### Total Estimated Savings:
- **Conservative**: 30-40% reduction in input tokens
- **Aggressive** (with compression): 40-50% reduction

## Token Usage Breakdown

**Before Optimization:**
- Context: ~4000 tokens (10 chunks × ~400 tokens each)
- Prompt: ~300 tokens
- **Total**: ~4300 tokens

**After Optimization:**
- Context: ~2000-2500 tokens (8 chunks × ~250-300 tokens each, with truncation)
- Prompt: ~200 tokens
- **Total**: ~2200-2700 tokens
- **Savings**: ~35-45%

## Quality Preservation

Optimizations preserve quality by:
1. **Top chunks remain full**: First 3-4 chunks keep full text (up to limit)
2. **Sentence boundary truncation**: Preserves complete thoughts
3. **Minimum chunks enforced**: Always provides at least 4 chunks
4. **High-scoring chunks prioritized**: Better chunks get more tokens

## Monitoring

Check logs for:
- `[RAG] Truncated chunk X: Y → Z chars` - Chunk truncation
- `[RAG] Compressed chunk X` - Chunk compression
- `[RAG] Final context size: X chars (~Y tokens)` - Total context size
- `[RAG] WARNING: Context exceeds budget` - Budget exceeded (compression triggered

## Tuning

Adjust based on your needs:

**More Aggressive (Lower Tokens):**
```env
CONTEXT_TOKEN_BUDGET=2000
MAX_CONTEXT_CHUNKS=6
MAX_CHUNK_LENGTH=400
```

**More Conservative (Higher Quality):**
```env
CONTEXT_TOKEN_BUDGET=3000
MAX_CONTEXT_CHUNKS=10
MAX_CHUNK_LENGTH=600
```

## Files Modified

1. `config/settings.py` - Added optimization settings
2. `packages/core/services/rag_service.py` - Implemented truncation and compression
3. `packages/core/rag/retriever.py` - Updated minimum chunks logic
4. `packages/core/prompts/templates/chat/rag_prompt.j2` - Optimized prompt template

## Next Steps

1. Monitor token usage in production
2. Adjust `MAX_CHUNK_LENGTH` based on chunk size distribution
3. Fine-tune compression thresholds
4. Consider semantic summarization for very long chunks
