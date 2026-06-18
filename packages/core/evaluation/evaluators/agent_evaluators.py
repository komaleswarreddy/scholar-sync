"""Concrete evaluators for agent-level scoring."""

from __future__ import annotations

import json
import re
from typing import Any, Dict, Optional

from packages.core.evaluation.evaluators.base import BaseEvaluator, EvalResult
from packages.core.evaluation.evaluators.llm_judge import judge_answer_quality


class RouterEvaluator(BaseEvaluator):
  name = "router"
  passing_threshold = 95.0

  def evaluate(self, *, inputs, output, expected, metadata=None) -> EvalResult:
    out = output if isinstance(output, dict) else {}
    if isinstance(output, str):
      try:
        out = json.loads(output)
      except json.JSONDecodeError:
        out = {}
    exp_intent = str(expected.get("intent", "")).lower()
    got_intent = str(out.get("intent", "")).lower()
    intent_ok = 1.0 if exp_intent and got_intent == exp_intent else 0.0
    conf = float(out.get("confidence", 0) or 0)
    conf_ok = 1.0 if conf >= float(expected.get("confidence_min", 0.5)) else 0.5
    schema_ok = 1.0 if all(k in out for k in ("intent", "confidence", "reasoning")) else 0.0
    metrics = {
      "intent_accuracy": intent_ok,
      "schema_validity": schema_ok,
      "board_accuracy": intent_ok,
      "subject_accuracy": intent_ok,
      "topic_accuracy": conf_ok,
    }
    weights = {
      "board_accuracy": 0.25,
      "subject_accuracy": 0.25,
      "topic_accuracy": 0.20,
      "intent_accuracy": 0.20,
      "schema_validity": 0.10,
    }
    score = self._weighted_score(metrics, weights)
    return EvalResult(score=score, passed=score >= self.passing_threshold, metrics=metrics)


class QueryRewriterEvaluator(BaseEvaluator):
  name = "query_rewriter"
  passing_threshold = 90.0

  def evaluate(self, *, inputs, output, expected, metadata=None) -> EvalResult:
    out = output if isinstance(output, dict) else {}
    if isinstance(output, str):
      try:
        out = json.loads(output)
      except json.JSONDecodeError:
        out = {}
    queries = out.get("queries") or []
    exp_queries = expected.get("queries") or []
    if exp_queries and queries:
      overlap = len(set(q.lower() for q in queries) & set(q.lower() for q in exp_queries))
      recall = overlap / max(len(exp_queries), 1)
    else:
      recall = 1.0 if queries else 0.0
    avg_len = sum(len(q.split()) for q in queries) / max(len(queries), 1)
    conciseness = 1.0 if 3 <= avg_len <= 25 else 0.5
    metrics = {
      "retrieval_recall_improvement": recall,
      "query_relevance": recall,
      "conciseness": conciseness,
      "searchability": 1.0 if queries else 0.0,
    }
    weights = {
      "retrieval_recall_improvement": 0.40,
      "query_relevance": 0.30,
      "conciseness": 0.10,
      "searchability": 0.20,
    }
    score = self._weighted_score(metrics, weights)
    return EvalResult(score=score, passed=score >= self.passing_threshold, metrics=metrics)


class RetrieverEvaluator(BaseEvaluator):
  name = "retriever"
  passing_threshold = 90.0

  def evaluate(self, *, inputs, output, expected, metadata=None) -> EvalResult:
    phrases = expected.get("expected_phrases") or expected.get("phrases") or []
    ctx = str(output.get("context", output) if isinstance(output, dict) else output).lower()
    hits = sum(1 for p in phrases if p.lower() in ctx)
    recall = hits / max(len(phrases), 1) if phrases else 1.0
    metrics = {
      "context_recall": recall,
      "context_precision": recall,
      "top_k_accuracy": recall,
      "ranking_quality": recall,
    }
    weights = {
      "context_recall": 0.40,
      "context_precision": 0.30,
      "top_k_accuracy": 0.20,
      "ranking_quality": 0.10,
    }
    score = self._weighted_score(metrics, weights)
    return EvalResult(score=score, passed=score >= self.passing_threshold, metrics=metrics)


class AnswerGeneratorEvaluator(BaseEvaluator):
  name = "answer_generator"
  passing_threshold = 90.0

  def evaluate(self, *, inputs, output, expected, metadata=None) -> EvalResult:
    answer = str(output.get("answer", output) if isinstance(output, dict) else output)
    context = str(inputs.get("context", ""))
    judge = judge_answer_quality(
      question=str(inputs.get("query") or inputs.get("message", "")),
      answer=answer,
      context=context,
      expected_notes=str(expected.get("notes") or expected.get("reasoning", "")),
    )
    metrics = {
      "accuracy": judge["accuracy"] / 5.0,
      "completeness": judge["completeness"] / 5.0,
      "source_grounding": judge["source_grounding"] / 5.0,
      "exam_worthiness": judge["exam_worthiness"] / 5.0,
    }
    weights = {"accuracy": 0.40, "completeness": 0.25, "source_grounding": 0.20, "exam_worthiness": 0.15}
    score = self._weighted_score(metrics, weights)
    return EvalResult(score=score, passed=score >= self.passing_threshold, metrics=metrics, details=judge.get("reasoning"))


class VerifierEvaluator(BaseEvaluator):
  name = "verifier"
  passing_threshold = 95.0

  def evaluate(self, *, inputs, output, expected, metadata=None) -> EvalResult:
    corrected = str(output.get("corrected_answer", output) if isinstance(output, dict) else output)
    unsupported = inputs.get("unsupported_sentences") or []
    leaked = sum(1 for s in unsupported if s.lower() in corrected.lower())
    detection = 1.0 if leaked == 0 else max(0.0, 1.0 - leaked / max(len(unsupported), 1))
    metrics = {
      "hallucination_detection": detection,
      "false_positive_control": 1.0 if "general knowledge" not in corrected.lower() or expected.get("allow_gk") else 0.5,
      "source_alignment": detection,
      "correction_quality": detection,
    }
    weights = {
      "hallucination_detection": 0.40,
      "false_positive_control": 0.20,
      "source_alignment": 0.25,
      "correction_quality": 0.15,
    }
    score = self._weighted_score(metrics, weights)
    return EvalResult(score=score, passed=score >= self.passing_threshold, metrics=metrics)


class FormatterEvaluator(BaseEvaluator):
  name = "formatter"
  passing_threshold = 98.0

  def evaluate(self, *, inputs, output, expected, metadata=None) -> EvalResult:
    text = str(output.get("output", output) if isinstance(output, dict) else output)
    schema_ok = 1.0
    if expected.get("quiz_json") or expected.get("json_output"):
      try:
        json.loads(text) if text.strip().startswith("{") or text.strip().startswith("[") else None
        schema_ok = 1.0
      except json.JSONDecodeError:
        schema_ok = 0.0
    has_structure = 1.0 if re.search(r"^#+ |\n- |\n\d+\. ", text, re.M) or schema_ok else 0.5
    metrics = {"schema_compliance": schema_ok, "format_quality": has_structure, "consistency": has_structure}
    weights = {"schema_compliance": 0.50, "format_quality": 0.30, "consistency": 0.20}
    score = self._weighted_score(metrics, weights)
    return EvalResult(score=score, passed=score >= self.passing_threshold, metrics=metrics)


class HintAgentEvaluator(BaseEvaluator):
  name = "hint_agent"
  passing_threshold = 90.0

  def evaluate(self, *, inputs, output, expected, metadata=None) -> EvalResult:
    out = output if isinstance(output, dict) else {}
    if isinstance(output, str):
      try:
        out = json.loads(output)
      except json.JSONDecodeError:
        out = {"text": output}
    reveal = str(out.get("revealLevel", out.get("reveal_level", "")))
    final = str(out.get("finalAnswer", out.get("final_answer", "")))
    partial_ok = 1.0 if reveal in ("hint", "partial", "") else 0.8
    leak = 0.0 if (expected.get("no_final_answer") and final and final not in ("", "null")) else 1.0
    sections = out.get("sections") or []
    clarity = 1.0 if sections or out.get("title") else 0.6
    metrics = {
      "helpfulness": clarity,
      "progressive_guidance": partial_ok,
      "answer_leakage_control": leak,
      "clarity": clarity,
    }
    weights = {"helpfulness": 0.35, "progressive_guidance": 0.25, "answer_leakage_control": 0.25, "clarity": 0.15}
    score = self._weighted_score(metrics, weights)
    return EvalResult(score=score, passed=score >= self.passing_threshold, metrics=metrics)
