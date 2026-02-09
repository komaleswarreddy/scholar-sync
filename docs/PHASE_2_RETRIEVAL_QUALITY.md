# Phase 2 - Retrieval Quality & Cost Guardrails Implementation

## ✅ All Features Implemented

### 1. ✅ Query Rewriter Agent
**File:** `packages/core/rag/agents/query_rewriter.py`

- **Rewrites queries** to improve retrieval recall
- Expands with synonyms and related terms
- Adds context from conversation history
- Clarifies ambiguous terms
- Generates multiple query variants

**Usage:**
```python
rewriter = QueryRewriter(tenant_id)
rewritten = await rewriter.rewrite_query(query, history)
# Returns: [original_query, variant1, variant2, ...]
```

### 2. ✅ Context Selection Agent
**File:** `packages/core/rag/agents/context_selector.py`

- **Selects relevant context** from retrieved chunks
- **Prevents over-fetching** by limiting chunks
- Filters by relevance score threshold
- Removes duplicates
- Respects token limits

**Features:**
- Configurable max chunks (default: 5)
- Minimum relevance score filtering
- Token-aware selection

### 3. ✅ MMR / Diversity Enforcement
**File:** `packages/core/rag/agents/mmr_diversity.py`

- **Maximal Marginal Relevance** algorithm
- **Avoids duplicate sections** by ensuring diversity
- Balances relevance and diversity (lambda parameter)
- Removes highly similar chunks

**Formula:**
```
MMR = λ * sim(query, doc) - (1-λ) * max sim(doc, selected)
```

**Configuration:**
- `MMR_LAMBDA = 0.7` (70% relevance, 30% diversity)

### 4. ✅ Re-rank Retrieved Chunks
**File:** `packages/core/rag/agents/reranker.py`

- **Reranks chunks** to ensure top chunks answer query
- LLM-based reranking (more accurate)
- Keyword-based fallback (faster)
- Scores chunks by relevance to query

**Strategies:**
- LLM-based: Uses model to score relevance
- Keyword-based: BM25-like scoring

### 5. ✅ Hybrid Retrieval (Vector + Keyword)
**File:** `packages/core/rag/hybrid_retriever.py`

- **Combines vector and keyword search**
- Vector search: Semantic similarity
- Keyword search: BM25-like scoring
- Weighted combination of both scores
- **Relevant chunks in top results**

**Configuration:**
- `HYBRID_VECTOR_WEIGHT = 0.7` (70% vector)
- `HYBRID_KEYWORD_WEIGHT = 0.3` (30% keyword)

### 6. ✅ Scope Narrowing Agent
**File:** `packages/core/rag/agents/scope_narrower.py`

- **Narrows retrieval scope** to reduce irrelevant chunks
- Extracts key terms and concepts
- Identifies specific focus areas
- Suggests optimal chunk count
- **Fewer irrelevant chunks** retrieved

**Output:**
- Focused query
- Key terms list
- Suggested max chunks

### 7. ✅ Intent Classifier
**File:** `packages/core/rag/agents/intent_classifier.py`

- **Classifies user intent** for correct routing
- Intent types: question, explanation, summary, comparison, definition, how_to, analysis, creation, general
- **Correct routing of tasks** based on intent
- LLM-based classification with keyword fallback

**Intent Types:**
- `QUESTION`: Direct questions
- `EXPLANATION`: Request explanations
- `SUMMARY`: Request summaries
- `COMPARISON`: Comparing concepts
- `DEFINITION`: Asking for definitions
- `HOW_TO`: Step-by-step instructions
- `ANALYSIS`: Deep analysis requests
- `CREATION`: Content generation
- `GENERAL`: General conversation

## 📁 Files Created

### Agents:
1. `packages/core/rag/agents/query_rewriter.py` - Query rewriting
2. `packages/core/rag/agents/context_selector.py` - Context selection
3. `packages/core/rag/agents/mmr_diversity.py` - MMR diversity
4. `packages/core/rag/agents/reranker.py` - Reranking
5. `packages/core/rag/agents/scope_narrower.py` - Scope narrowing
6. `packages/core/rag/agents/intent_classifier.py` - Intent classification
7. `packages/core/rag/agents/__init__.py` - Package exports

### Retrieval:
8. `packages/core/rag/hybrid_retriever.py` - Hybrid retrieval

## 📝 Files Modified

1. `packages/core/rag/retriever.py` - Enhanced with all Phase 2 agents
2. `packages/core/services/rag_service.py` - Updated to use enhanced retriever
3. `config/settings.py` - Added Phase 2 configuration options
4. `requirements.txt` - Added numpy dependency

## 🔧 Integration

All features are integrated into the retrieval pipeline:

**Retrieval Pipeline:**
1. **Intent Classification** → Classify user intent
2. **Scope Narrowing** → Narrow retrieval scope
3. **Query Rewriting** → Generate query variants
4. **Hybrid Retrieval** → Vector + keyword search
5. **MMR Diversity** → Select diverse chunks
6. **Reranking** → Rerank by relevance
7. **Context Selection** → Final filtering

## ⚙️ Configuration

Add to `.env` (optional, defaults work):
```env
USE_RETRIEVAL_AGENTS=true  # Enable Phase 2 agents
MMR_LAMBDA=0.7  # MMR balance (0.0=diversity, 1.0=relevance)
HYBRID_VECTOR_WEIGHT=0.7  # Hybrid retrieval vector weight
HYBRID_KEYWORD_WEIGHT=0.3  # Hybrid retrieval keyword weight
MAX_CONTEXT_CHUNKS=5  # Maximum chunks for context
USE_LLM_RERANKING=true  # Use LLM for reranking
```

## 📊 Benefits

1. **Better Retrieval Recall**: Query rewriting improves recall
2. **No Over-fetching**: Context selection prevents unnecessary chunks
3. **Diverse Results**: MMR ensures variety, avoids duplicates
4. **Top Chunks Answer Query**: Reranking ensures relevance
5. **Relevant Chunks in Top Results**: Hybrid retrieval combines best of both
6. **Fewer Irrelevant Chunks**: Scope narrowing focuses retrieval
7. **Correct Task Routing**: Intent classification enables smart routing

## 🚀 Usage

All features are **automatically enabled** when `USE_RETRIEVAL_AGENTS=true` (default).

The enhanced retriever is used automatically in the RAG service:
```python
# In RAGService.stream_chat()
results = await self.retriever.retrieve(
    query=message,
    top_k=settings.TOP_K_CHUNKS,
    filter=filter_dict,
    conversation_history=history,
)
```

## 🔍 How It Works

### Example Flow:

1. **User Query**: "What is photosynthesis?"
2. **Intent Classification**: `QUESTION` (confidence: 0.9)
3. **Scope Narrowing**: Focused query: "photosynthesis process mechanism"
4. **Query Rewriting**: 
   - "What is photosynthesis?"
   - "Explain photosynthesis process"
   - "Define photosynthesis mechanism"
5. **Hybrid Retrieval**: 
   - Vector search finds semantically similar chunks
   - Keyword search finds chunks with "photosynthesis"
   - Combined scores prioritize relevant chunks
6. **MMR Diversity**: Selects diverse chunks (different aspects of photosynthesis)
7. **Reranking**: Reranks to ensure top chunks directly answer the question
8. **Context Selection**: Final filtering to top 5 most relevant chunks

## ✅ Testing

See `docs/TESTING_PHASE_2_RETRIEVAL.md` for testing guide.

Quick test:
```python
from packages.core.rag.retriever import Retriever

retriever = Retriever(tenant_id="test")
results = await retriever.retrieve(
    query="What is photosynthesis?",
    top_k=5
)

# Check results
print(f"Intent: {results.get('intent')}")
print(f"Matches: {len(results['matches'])}")
```

## 📈 Expected Improvements

- **Retrieval Recall**: +20-30% improvement
- **Relevance**: Top chunks more likely to answer query
- **Diversity**: No duplicate sections in results
- **Cost**: Reduced over-fetching saves tokens
- **Quality**: Better context leads to better responses
