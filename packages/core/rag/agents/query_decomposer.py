"""
Query Decomposer Agent (optional, feature-flagged).

Breaks a complex query into:
- primary_concept: the central topic
- sub_queries: 2-4 focused retrieval queries
"""

import json
import re
from typing import Any, Dict, List, Optional

from config.settings import settings
from packages.core.llm import get_llm_client, get_model_for_task
from packages.core.llm._base import LLMProvider
from packages.core.rag.agents.conversation_context import format_routing_hints_section


def _parse_json(content: str) -> Optional[Dict[str, Any]]:
    text = (content or "").strip()
    if not text:
        return None
    try:
        obj = json.loads(text)
        return obj if isinstance(obj, dict) else None
    except Exception:
        pass
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if not m:
        return None
    try:
        obj = json.loads(m.group())
        return obj if isinstance(obj, dict) else None
    except Exception:
        return None


class QueryDecomposer:
    def __init__(self, tenant_id: str, user_id: Optional[str] = None):
        self.tenant_id = tenant_id
        self.user_id = user_id

    async def decompose(
        self,
        *,
        query: str,
        max_sub_queries: Optional[int] = None,
        feature_tag: str = "query_decomposer",
        scope: Optional[str] = None,
        requires_retrieval: Optional[bool] = None,
        requires_attachment: Optional[bool] = None,
    ) -> Dict[str, Any]:
        q = (query or "").strip()
        if not q:
            return {"primary_concept": "", "sub_queries": [], "used": False}

        max_sq = int(max_sub_queries or getattr(settings, "QUERY_DECOMPOSITION_MAX_SUB_QUERIES", 4))
        max_sq = max(0, min(max_sq, 8))

        system_prompt = (
            "Return JSON only: {"
            '"primary_concept": string, '
            '"sub_queries": string[]'
            "}."
        )
        user_prompt = (
            format_routing_hints_section(
                scope=scope,
                requires_retrieval=requires_retrieval,
                requires_attachment=requires_attachment,
            )
            + "Decompose this query into a primary concept and up to "
            f"{max_sq} short sub-queries optimized for document retrieval.\n\n"
            f"Query: {q}"
        )

        provider, model = get_model_for_task("query_decomposer")
        llm = get_llm_client(provider=provider, model=model, temperature=0.2)

        llm_kwargs: Dict[str, Any] = {
            "tenant_id": str(self.tenant_id),
            "user_id": self.user_id,
            "feature_tag": feature_tag,
        }
        if provider in (LLMProvider.OPENAI, LLMProvider.GROQ):
            llm_kwargs["response_format"] = {"type": "json_object"}

        try:
            resp = await llm.generate(
                prompt=user_prompt,
                system_prompt=system_prompt,
                temperature=0.2,
                max_tokens=240,
                **llm_kwargs,
            )
        except Exception:
            return {"primary_concept": "", "sub_queries": [], "used": False}

        obj = _parse_json(resp.content or "")
        if not obj:
            return {"primary_concept": "", "sub_queries": [], "used": False}

        pc = str(obj.get("primary_concept", "") or "").strip()
        sq_raw = obj.get("sub_queries") or []
        sub_queries: List[str] = []
        for s in sq_raw:
            ss = str(s or "").strip()
            if ss and ss.lower() != q.lower():
                sub_queries.append(ss)

        # Cap + de-dupe while preserving order.
        seen = set()
        out_sq: List[str] = []
        for s in sub_queries:
            sl = s.lower()
            if sl in seen:
                continue
            seen.add(sl)
            out_sq.append(s)
            if len(out_sq) >= max_sq:
                break

        return {
            "primary_concept": pc,
            "sub_queries": out_sq,
            "used": bool(pc or out_sq),
        }

