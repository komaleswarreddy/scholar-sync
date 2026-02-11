"""
Evaluation Framework

Continuous evaluation loop for regression detection and quality monitoring.
"""

import json
import time
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from pathlib import Path
from dataclasses import dataclass, asdict
from enum import Enum


class EvaluationMetric(Enum):
    """Evaluation metrics."""
    ACCURACY = "accuracy"
    RELEVANCE = "relevance"
    COMPLETENESS = "completeness"
    COST = "cost"
    TOKENS = "tokens"
    LATENCY = "latency"
    CONFIDENCE = "confidence"


@dataclass
class EvaluationResult:
    """Single evaluation result."""
    query: str
    expected_answer: Optional[str]
    actual_answer: str
    metrics: Dict[str, float]
    timestamp: datetime
    model: str
    provider: str
    tokens_used: int
    cost: float
    latency_ms: float
    confidence: float
    citations: List[Dict]
    error: Optional[str] = None


@dataclass
class EvaluationReport:
    """Evaluation report with aggregated metrics."""
    evaluation_id: str
    timestamp: datetime
    total_queries: int
    metrics: Dict[str, float]
    token_comparison: Dict[str, Any]
    cost_comparison: Dict[str, Any]
    accuracy_score: float
    regression_detected: bool
    regression_details: List[str]
    low_confidence_count: int
    errors: List[str]


class Evaluator:
    """
    Evaluates RAG system performance.
    
    Tracks:
    - Accuracy and quality metrics
    - Token usage and costs
    - Latency
    - Confidence scores
    - Regressions
    """
    
    def __init__(
        self,
        evaluation_dir: Optional[str] = None,
        baseline_file: Optional[str] = None
    ):
        """
        Initialize evaluator.
        
        Args:
            evaluation_dir: Directory to store evaluation results
            baseline_file: Path to baseline metrics file
        """
        self.evaluation_dir = Path(evaluation_dir or "evaluations")
        self.evaluation_dir.mkdir(parents=True, exist_ok=True)
        
        self.baseline_file = Path(baseline_file or self.evaluation_dir / "baseline.json")
        self.baseline_metrics = self._load_baseline()
        
        # Store current evaluation results
        self.current_results: List[EvaluationResult] = []
    
    def _load_baseline(self) -> Dict[str, Any]:
        """Load baseline metrics for comparison."""
        if self.baseline_file.exists():
            try:
                with open(self.baseline_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"[WARNING] Failed to load baseline: {e}")
        return {}
    
    def _save_baseline(self, metrics: Dict[str, Any]):
        """Save current metrics as baseline."""
        try:
            with open(self.baseline_file, 'w') as f:
                json.dump(metrics, f, indent=2, default=str)
        except Exception as e:
            print(f"[WARNING] Failed to save baseline: {e}")
    
    def evaluate_query(
        self,
        query: str,
        actual_answer: str,
        expected_answer: Optional[str] = None,
        model: str = "unknown",
        provider: str = "unknown",
        tokens_used: int = 0,
        cost: float = 0.0,
        latency_ms: float = 0.0,
        confidence: float = 0.0,
        citations: List[Dict] = None,
        error: Optional[str] = None
    ) -> EvaluationResult:
        """
        Evaluate a single query.
        
        Args:
            query: User query
            actual_answer: Generated answer
            expected_answer: Expected answer (for accuracy)
            model: Model used
            provider: Provider used
            tokens_used: Tokens consumed
            cost: Cost in USD
            latency_ms: Latency in milliseconds
            confidence: Confidence score (0.0-1.0)
            citations: List of citations
            error: Optional error message
            
        Returns:
            EvaluationResult
        """
        # Calculate metrics
        metrics = {}
        
        # Accuracy (if expected answer provided)
        if expected_answer:
            accuracy = self._calculate_accuracy(actual_answer, expected_answer)
            metrics["accuracy"] = accuracy
        else:
            metrics["accuracy"] = None
        
        # Relevance (based on citations and answer quality)
        relevance = self._calculate_relevance(actual_answer, citations or [])
        metrics["relevance"] = relevance
        
        # Completeness (answer length and detail)
        completeness = self._calculate_completeness(actual_answer)
        metrics["completeness"] = completeness
        
        # Cost and tokens
        metrics["cost"] = cost
        metrics["tokens"] = tokens_used
        metrics["latency"] = latency_ms
        metrics["confidence"] = confidence
        
        result = EvaluationResult(
            query=query,
            expected_answer=expected_answer,
            actual_answer=actual_answer,
            metrics=metrics,
            timestamp=datetime.utcnow(),
            model=model,
            provider=provider,
            tokens_used=tokens_used,
            cost=cost,
            latency_ms=latency_ms,
            confidence=confidence,
            citations=citations or [],
            error=error
        )
        
        self.current_results.append(result)
        return result
    
    def _calculate_accuracy(
        self,
        actual: str,
        expected: str
    ) -> float:
        """
        Calculate accuracy score between actual and expected answer.
        
        Uses simple word overlap (can be improved with semantic similarity).
        """
        actual_words = set(actual.lower().split())
        expected_words = set(expected.lower().split())
        
        if not expected_words:
            return 0.0
        
        overlap = len(actual_words.intersection(expected_words))
        return overlap / len(expected_words)
    
    def _calculate_relevance(
        self,
        answer: str,
        citations: List[Dict]
    ) -> float:
        """
        Calculate relevance score based on citations.
        
        Higher score if answer has relevant citations.
        """
        if not citations:
            return 0.3  # Low relevance without citations
        
        # Check if citations are relevant (simple heuristic)
        citation_count = len(citations)
        avg_score = sum(c.get("score", 0) for c in citations) / max(citation_count, 1)
        
        # Relevance based on citation count and scores
        relevance = min(0.3 + (citation_count * 0.1) + (avg_score * 0.4), 1.0)
        return relevance
    
    def _calculate_completeness(
        self,
        answer: str
    ) -> float:
        """
        Calculate completeness score based on answer length and structure.
        
        Longer, structured answers score higher.
        """
        if not answer or len(answer.strip()) < 10:
            return 0.0
        
        # Base score from length
        length_score = min(len(answer) / 500, 1.0)  # 500 chars = full score
        
        # Structure bonus (has bullet points, numbered list, etc.)
        structure_bonus = 0.0
        if any(marker in answer for marker in ['•', '-', '*', '1.', '2.']):
            structure_bonus = 0.2
        
        return min(length_score + structure_bonus, 1.0)
    
    def generate_report(
        self,
        evaluation_id: Optional[str] = None,
        compare_to_baseline: bool = True
    ) -> EvaluationReport:
        """
        Generate evaluation report from current results.
        
        Args:
            evaluation_id: Optional evaluation ID
            compare_to_baseline: Compare to baseline metrics
            
        Returns:
            EvaluationReport
        """
        if not self.current_results:
            return EvaluationReport(
                evaluation_id=evaluation_id or "empty",
                timestamp=datetime.utcnow(),
                total_queries=0,
                metrics={},
                token_comparison={},
                cost_comparison={},
                accuracy_score=0.0,
                regression_detected=False,
                regression_details=[],
                low_confidence_count=0,
                errors=[]
            )
        
        # Aggregate metrics
        total_queries = len(self.current_results)
        total_tokens = sum(r.tokens_used for r in self.current_results)
        total_cost = sum(r.cost for r in self.current_results)
        avg_latency = sum(r.latency_ms for r in self.current_results) / total_queries
        avg_confidence = sum(r.confidence for r in self.current_results) / total_queries
        
        # Accuracy (only for queries with expected answers)
        accuracy_results = [r for r in self.current_results if r.metrics.get("accuracy") is not None]
        avg_accuracy = (
            sum(r.metrics["accuracy"] for r in accuracy_results) / len(accuracy_results)
            if accuracy_results else None
        )
        
        # Relevance and completeness
        avg_relevance = sum(r.metrics.get("relevance", 0) for r in self.current_results) / total_queries
        avg_completeness = sum(r.metrics.get("completeness", 0) for r in self.current_results) / total_queries
        
        metrics = {
            "accuracy": avg_accuracy or 0.0,
            "relevance": avg_relevance,
            "completeness": avg_completeness,
            "avg_tokens": total_tokens / total_queries,
            "avg_cost": total_cost / total_queries,
            "avg_latency": avg_latency,
            "avg_confidence": avg_confidence,
            "total_tokens": total_tokens,
            "total_cost": total_cost,
        }
        
        # Comparison to baseline
        token_comparison = {}
        cost_comparison = {}
        regression_detected = False
        regression_details = []
        
        if compare_to_baseline and self.baseline_metrics:
            baseline_tokens = self.baseline_metrics.get("avg_tokens", 0)
            baseline_cost = self.baseline_metrics.get("avg_cost", 0)
            baseline_accuracy = self.baseline_metrics.get("accuracy", 0)
            
            current_tokens = metrics["avg_tokens"]
            current_cost = metrics["avg_cost"]
            current_accuracy = metrics["accuracy"]
            
            # Token comparison
            token_reduction = ((baseline_tokens - current_tokens) / baseline_tokens * 100) if baseline_tokens > 0 else 0
            token_comparison = {
                "baseline": baseline_tokens,
                "current": current_tokens,
                "reduction_percent": token_reduction,
                "target_met": token_reduction >= 50  # Target: ≥50% reduction
            }
            
            # Cost comparison
            cost_reduction = ((baseline_cost - current_cost) / baseline_cost * 100) if baseline_cost > 0 else 0
            cost_comparison = {
                "baseline": baseline_cost,
                "current": current_cost,
                "reduction_percent": cost_reduction,
                "target_met": cost_reduction >= 50  # Target: ≥50% reduction
            }
            
            # Regression detection
            if current_accuracy < baseline_accuracy * 0.9:  # 10% drop
                regression_detected = True
                regression_details.append(f"Accuracy dropped: {baseline_accuracy:.2f} → {current_accuracy:.2f}")
            
            if current_tokens > baseline_tokens * 1.1:  # 10% increase
                regression_detected = True
                regression_details.append(f"Token usage increased: {baseline_tokens:.0f} → {current_tokens:.0f}")
            
            if current_cost > baseline_cost * 1.1:  # 10% increase
                regression_detected = True
                regression_details.append(f"Cost increased: ${baseline_cost:.6f} → ${current_cost:.6f}")
        
        # Low confidence count
        low_confidence_count = sum(
            1 for r in self.current_results
            if r.confidence < 0.5
        )
        
        # Errors
        errors = [r.error for r in self.current_results if r.error]
        
        report = EvaluationReport(
            evaluation_id=evaluation_id or f"eval_{datetime.utcnow().isoformat()}",
            timestamp=datetime.utcnow(),
            total_queries=total_queries,
            metrics=metrics,
            token_comparison=token_comparison,
            cost_comparison=cost_comparison,
            accuracy_score=avg_accuracy or 0.0,
            regression_detected=regression_detected,
            regression_details=regression_details,
            low_confidence_count=low_confidence_count,
            errors=errors
        )
        
        # Save report
        self._save_report(report)
        
        # Update baseline if this is a good run
        if not regression_detected and avg_accuracy and avg_accuracy > 0.7:
            self._save_baseline(metrics)
        
        return report
    
    def _save_report(self, report: EvaluationReport):
        """Save evaluation report to file."""
        report_file = self.evaluation_dir / f"{report.evaluation_id}.json"
        try:
            with open(report_file, 'w') as f:
                json.dump(asdict(report), f, indent=2, default=str)
        except Exception as e:
            print(f"[WARNING] Failed to save report: {e}")
    
    def clear_results(self):
        """Clear current evaluation results."""
        self.current_results = []
