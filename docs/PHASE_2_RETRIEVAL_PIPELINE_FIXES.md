# Phase 2 RAG Retrieval Pipeline Fixes

## Overview
This document describes the fixes applied to the Phase 2 RAG retrieval pipeline to improve answer quality while maintaining cost guardrails and preventing over-filtering of context.

## Problem
After implementing Phase 2 retrieval agents (query rewriting, hybrid retrieval, MMR diversity, reranking, context selection, intent classification), answer quality degraded due to over-aggressive filtering and context pruning.

## Solution
Implemented comprehensive guardrails and improvements across all retrieval stages to ensure:
1. Minimum context chunks are always provided (6 chunks minimum)
2. Query rewriting preserves semantic intent
3. Filtering stages are skipped for small document sets
4. Highly relevant chunks are preserved even if similar
5. Detailed debug logging for pipeline diagnostics

## Changes Made

### 1. Configuration Settings (`config/settings.py`)
- Added `RAG_DEBUG: bool = False` - Enable detailed debug logging
- Added `MIN_CONTEXT_CHUNKS: int = 6` - Minimum chunks to ensure quality
- Added `QUERY_REWRITE_CONFIDENCE_THRESHOLD: float = 0.7` - Confidence threshold for query rewrites
- Added `CONTEXT_TOKEN_BUDGET: int = 4000` - Target token budget for context
- Updated `MAX_CONTEXT_CHUNKS: int = 10` (increased from 5)

### 2. Query Rewriter (`packages/core/rag/agents/query_rewriter.py`)
**Changes:**
- Returns dict with `queries`, `confidence`, `used_rewrites`, `reasoning`
- Added confidence threshold check - only uses rewrites if confidence >= threshold
- Enhanced prompt to explicitly preserve semantic intent
- Prevents over-specialization of generic queries
- Falls back to original query if confidence is low

**Key Features:**
- Preserves exact semantic meaning
- Does not narrow scope unnecessarily
- Logs rewrite confidence and reasoning

### 3. Retriever (`packages/core/rag/retriever.py`)
**Major Overhaul:**
- Added comprehensive debug logging at every stage
- Implemented guardrails to prevent over-filtering:
  - Skip MMR if < 8 chunks retrieved
  - Skip scope narrowing if < 40 chunks available
  - Ensure minimum 6 chunks after reranking
  - Ensure minimum 6 chunks in final context
- Detailed debug trace tracking:
  - Original query
  - Rewritten queries with confidence
  - Detected intent with confidence
  - Chunk counts at each stage
  - Token size of final context
  - Guardrails applied

**Pipeline Flow:**
1. Intent Classification (with confidence check)
2. Scope Narrowing (skipped if small doc set)
3. Query Rewriting (with confidence threshold)
4. Hybrid Retrieval (vector + keyword, normalized scores)
5. MMR Diversity (skipped if < 8 chunks, preserves high relevance)
6. Reranking (with confidence guardrails)
7. Context Selection (min 6 chunks, token budget)

### 4. MMR Diversity (`packages/core/rag/agents/mmr_diversity.py`)
**Changes:**
- Preserves highly relevant chunks (top 20% by relevance) even if similar
- Boosts MMR score for chunks with relevance > 0.7
- Prevents removal of top-relevant chunks for diversity

### 5. Reranker (`packages/core/rag/agents/reranker.py`)
**Changes:**
- Returns dict with `chunks` and `confidence` score
- Calculates confidence based on score variance
- Guardrails:
  - If confidence < 0.6, keeps original vector order
  - Never drops below 6 chunks after reranking
  - Limits reranking to 20 chunks to avoid token limits

### 6. Context Selector (`packages/core/rag/agents/context_selector.py`)
**Changes:**
- Enforces minimum chunks (default 6)
- Respects token budget (default 4000 tokens)
- Prioritizes by rerank score if available
- Includes adjacent chunks for continuity (when within budget)
- Lowers relevance threshold if needed to meet minimum chunks
- Allows 20% over budget to ensure minimum chunks

### 7. Intent Classifier Safety
**Changes:**
- Logs predicted intent and confidence
- Routes to default QA pipeline if confidence < 0.5
- Continues with pipeline but uses generic intent on low confidence

### 8. Hybrid Retriever
**Already Normalized:**
- Vector scores: 0-1 (cosine similarity)
- Keyword scores: Normalized to 0-1 range
- Combined: `vector_weight * vector_score + keyword_weight * normalized_keyword`
- Weights: 0.7 vector, 0.3 keyword

### 9. Debug Endpoint (`apps/api/routes/debug.py`)
**New Endpoint:** `/debug/retrieval_trace`

**Features:**
- Returns full retrieval trace for a query
- Shows all pipeline stages
- Includes guardrails applied
- Shows chunk details with scores
- Requires `RAG_DEBUG=true` to use

**Usage:**
```bash
GET /debug/retrieval_trace?query=your+query&top_k=10
```

**Response includes:**
- Original query
- Rewritten queries with confidence
- Detected intent
- Chunk counts at each stage
- Final chunks with scores
- Guardrails applied
- Settings used

### 10. Middleware Updates (`apps/api/middleware/tenant.py`)
- Added `/debug` to `TENANT_ONLY_PATHS` for development access

## Guardrails Summary

1. **Minimum Chunks:** Always ensure at least 6 chunks in final context
2. **Small Doc Set:** Skip MMR if < 8 chunks, skip scope narrowing if < 40 chunks
3. **Query Rewrite:** Only use rewrites if confidence >= 0.7
4. **Reranker:** Keep original order if confidence < 0.6
5. **Context Selection:** Lower threshold if needed to meet minimum chunks
6. **Intent Classifier:** Route to default if confidence < 0.5

## Debug Logging

When `RAG_DEBUG=true`, detailed logs are printed at each stage:
- `[RAG_DEBUG] [START]` - Pipeline start
- `[RAG_DEBUG] [INTENT]` - Intent classification
- `[RAG_DEBUG] [SCOPE]` - Scope narrowing
- `[RAG_DEBUG] [REWRITE]` - Query rewriting
- `[RAG_DEBUG] [RETRIEVAL]` - Initial retrieval
- `[RAG_DEBUG] [HYBRID]` - Hybrid retrieval
- `[RAG_DEBUG] [MMR]` - MMR diversity
- `[RAG_DEBUG] [RERANK]` - Reranking
- `[RAG_DEBUG] [CONTEXT]` - Context selection
- `[RAG_DEBUG] [GUARDRAIL]` - Guardrails applied

## Testing

1. **Enable Debug Mode:**
   ```bash
   RAG_DEBUG=true
   ```

2. **Test Retrieval Trace:**
   ```bash
   curl "http://localhost:8000/debug/retrieval_trace?query=what+is+null&top_k=10"
   ```

3. **Monitor Logs:**
   - Check console for `[RAG_DEBUG]` messages
   - Verify guardrails are applied appropriately
   - Ensure minimum chunks are maintained

## Expected Improvements

1. **Answer Quality:**
   - More complete answers with sufficient context
   - Better relevance with preserved high-scoring chunks
   - Less over-filtering leading to missing information

2. **Retrieval Quality:**
   - Minimum 6 chunks ensures comprehensive context
   - Query rewriting preserves intent
   - Reranking improves relevance order

3. **Cost Efficiency:**
   - Guardrails prevent unnecessary filtering
   - Token budget limits prevent over-fetching
   - Smart skipping of stages for small doc sets

## Configuration

Key settings in `.env`:
```env
RAG_DEBUG=false                    # Enable debug logging
USE_RETRIEVAL_AGENTS=true          # Enable Phase 2 agents
MMR_LAMBDA=0.7                     # MMR balance (0.0=diversity, 1.0=relevance)
HYBRID_VECTOR_WEIGHT=0.7          # Vector search weight
HYBRID_KEYWORD_WEIGHT=0.3          # Keyword search weight
MAX_CONTEXT_CHUNKS=10              # Maximum chunks
MIN_CONTEXT_CHUNKS=6               # Minimum chunks (guardrail)
QUERY_REWRITE_CONFIDENCE_THRESHOLD=0.7  # Rewrite confidence threshold
CONTEXT_TOKEN_BUDGET=4000          # Token budget for context
USE_LLM_RERANKING=true             # Use LLM for reranking
```

## Next Steps

1. Monitor answer quality in production
2. Adjust thresholds based on feedback
3. Fine-tune token budget based on model limits
4. Consider adding more sophisticated adjacent chunk detection
5. Add metrics for guardrail effectiveness
