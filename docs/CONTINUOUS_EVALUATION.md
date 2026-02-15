# Continuous Evaluation Loop

## Overview

Continuous evaluation system for regression detection, quality monitoring, and cost optimization. Catches regressions early and tracks improvements.

## Features Implemented

### 1. ✅ Scheduled Evaluations

**File**: `packages/core/evaluation/scheduler.py`

Runs periodic evaluations to catch regressions early:
- **Scheduled Jobs**: Register evaluation jobs with intervals
- **Automatic Execution**: Runs evaluations on schedule
- **Error Handling**: Graceful error handling for failed evaluations
- **Manual Trigger**: Can trigger evaluations manually

**Configuration**:
```python
ENABLE_SCHEDULED_EVALS: bool = True
EVAL_INTERVAL_HOURS: int = 24  # Run every 24 hours
```

### 2. ✅ Token & Cost Comparison

**File**: `packages/core/evaluation/evaluator.py`

Compares before/after metrics to track improvements:
- **Baseline Metrics**: Stores baseline for comparison
- **Token Comparison**: Tracks token usage reduction
- **Cost Comparison**: Tracks cost reduction
- **Target Tracking**: Monitors ≥50% cost/token reduction targets

**Metrics Tracked**:
- Average tokens per query
- Average cost per query
- Total tokens
- Total cost
- Reduction percentages

**Targets**:
- ≥50% cost reduction
- ≥50% token reduction

### 3. ✅ Accuracy Benchmarking

**File**: `packages/core/evaluation/evaluator.py`

Evaluates answer quality and accuracy:
- **Accuracy Score**: Compares actual vs expected answers
- **Relevance Score**: Based on citations and answer quality
- **Completeness Score**: Based on answer length and structure
- **Regression Detection**: Detects quality regressions

**Metrics**:
- Accuracy (word overlap with expected answer)
- Relevance (citation quality and count)
- Completeness (answer length and structure)
- Overall quality score

### 4. ✅ Cold-Start Handling

**File**: `packages/core/evaluation/cold_start_handler.py`

Graceful fallback logic for first-use scenarios:
- **Cold Start Detection**: Identifies cold start scenarios
- **Fallback Messages**: Provides helpful messages
- **Skip Retrieval**: Skips retrieval when no sources available
- **Simple Responses**: Uses simple responses when appropriate

**Cold Start Reasons**:
- No sources uploaded
- No conversation history
- No cache available
- First query
- New tenant

**Fallback Messages**:
- Guides users to upload documents
- Explains what's happening
- Provides next steps

### 5. ✅ Confidence Thresholding

**File**: `packages/core/evaluation/confidence_scorer.py`

Calculates confidence scores and flags low-confidence responses:
- **Confidence Score**: 0.0-1.0 score based on multiple factors
- **Confidence Levels**: High (≥0.7), Medium (0.5-0.7), Low (<0.5)
- **Low Confidence Flagging**: Flags responses below threshold
- **Factor Analysis**: Breaks down confidence by factors

**Confidence Factors**:
- Citation quality (40% weight)
- Answer completeness (30% weight)
- Query-answer alignment (30% weight)

**Configuration**:
```python
ENABLE_CONFIDENCE_THRESHOLDING: bool = True
CONFIDENCE_LOW_THRESHOLD: float = 0.5
CONFIDENCE_HIGH_THRESHOLD: float = 0.7
```

## Settings

All evaluation settings in `config/settings.py`:

```python
# Continuous Evaluation Loop
ENABLE_EVALUATION: bool = True  # Master switch
ENABLE_SCHEDULED_EVALS: bool = True
EVAL_INTERVAL_HOURS: int = 24
ENABLE_COLD_START_HANDLING: bool = True
ENABLE_CONFIDENCE_THRESHOLDING: bool = True
CONFIDENCE_LOW_THRESHOLD: float = 0.5
CONFIDENCE_HIGH_THRESHOLD: float = 0.7
TARGET_COST_REDUCTION_PERCENT: float = 50.0
TARGET_TOKEN_REDUCTION_PERCENT: float = 50.0
```

## Integration Flow

**Request Flow**:
1. **Cold Start Check**
   - Detects cold start scenarios
   - Returns fallback message if needed
   - Skips retrieval if no sources

2. **Normal Processing**
   - RAG retrieval and generation
   - Confidence scoring
   - Evaluation recording

3. **Post-Processing**
   - Confidence scoring on output
   - Evaluation recording
   - Low confidence flagging

**Scheduled Evaluations**:
- Runs on schedule (default: every 24 hours)
- Generates evaluation reports
- Compares to baseline
- Detects regressions
- Updates baseline if improvements detected

## Evaluation Report

**Structure**:
```json
{
  "evaluation_id": "eval_2024-01-01T00:00:00",
  "timestamp": "2024-01-01T00:00:00",
  "total_queries": 100,
  "metrics": {
    "accuracy": 0.85,
    "relevance": 0.78,
    "completeness": 0.82,
    "avg_tokens": 1500,
    "avg_cost": 0.002,
    "avg_latency": 1200,
    "avg_confidence": 0.72
  },
  "token_comparison": {
    "baseline": 3000,
    "current": 1500,
    "reduction_percent": 50.0,
    "target_met": true
  },
  "cost_comparison": {
    "baseline": 0.004,
    "current": 0.002,
    "reduction_percent": 50.0,
    "target_met": true
  },
  "accuracy_score": 0.85,
  "regression_detected": false,
  "regression_details": [],
  "low_confidence_count": 5,
  "errors": []
}
```

## File Structure

```
packages/core/evaluation/
├── __init__.py              # Package exports
├── evaluator.py             # Evaluation framework
├── scheduler.py             # Scheduled evaluations
├── confidence_scorer.py     # Confidence scoring
└── cold_start_handler.py    # Cold-start handling
```

## Usage Examples

### Evaluator
```python
from packages.core.evaluation import Evaluator

evaluator = Evaluator()
result = evaluator.evaluate_query(
    query="What is AI?",
    actual_answer="AI is...",
    expected_answer="Artificial Intelligence is...",
    tokens_used=1500,
    cost=0.002,
    confidence=0.75
)
report = evaluator.generate_report()
```

### Confidence Scorer
```python
from packages.core.evaluation import ConfidenceScorer

scorer = ConfidenceScorer()
result = scorer.calculate_confidence(
    query="What is AI?",
    answer="AI is...",
    citations=[...],
    retrieval_scores=[0.8, 0.7, 0.6]
)
if result["flagged"]:
    # Handle low confidence
    pass
```

### Cold Start Handler
```python
from packages.core.evaluation import ColdStartHandler

handler = ColdStartHandler()
info = handler.check_cold_start(
    has_sources=False,
    has_history=False
)
if info["should_use_fallback"]:
    # Return fallback message
    pass
```

### Scheduler
```python
from packages.core.evaluation import EvaluationScheduler

scheduler = EvaluationScheduler()
scheduler.register_eval(
    name="daily_eval",
    interval_seconds=86400,  # 24 hours
    callback=run_evaluation
)
await scheduler.start()
```

## Benefits

1. **Early Regression Detection**: Catches quality/cost regressions early
2. **Cost Tracking**: Monitors cost reduction targets (≥50%)
3. **Quality Monitoring**: Tracks accuracy and relevance
4. **Confidence Scoring**: Flags low-confidence responses
5. **Graceful Degradation**: Handles cold-start scenarios
6. **Automated Reporting**: Generates evaluation reports automatically

## Notes

- Evaluations are stored in `evaluations/{tenant_id}/` directory
- Baseline is automatically updated when improvements are detected
- Low confidence responses are flagged for review
- Cold-start handling provides helpful guidance to users
- Scheduled evaluations run automatically in background
