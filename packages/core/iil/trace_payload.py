"""Pipeline trace payload for InteractionLog creation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class PipelineTracePayload:
    query_text: str = ""
    chunks_retrieved: List[Dict[str, Any]] = field(default_factory=list)
    retrieval_strategy: Optional[str] = None
    kb_hit: bool = False
    derived_hit: bool = False
    fallback_triggered: bool = False
    response_token_count: int = 0
    citations_count: int = 0
    grounding_mode: str = "strict"
    out_of_kb_indicator: bool = False
    latency_ms: int = 0
    classified_intent: Optional[str] = None
    concept_node_id: Optional[str] = None
    notebook_id: Optional[str] = None
