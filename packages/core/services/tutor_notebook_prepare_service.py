"""Unified tutor notebook prepare: create, bootstrap, parallel studio, persist."""

from __future__ import annotations

import asyncio
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from packages.core.services.notebook_service import NotebookService
from packages.core.services.studio_feature_service import StudioFeatureService
from packages.core.services.studio_service import StudioService
from packages.core.services.tutor_ncert_context_cache import TutorNcertContextCache
from packages.core.services.tutor_notebook_bootstrap_service import (
    TutorNotebookBootstrapService,
    VALID_STUDIO_TYPES,
    _normalize_scope,
)

TITLE_BY_TYPE: Dict[str, str] = {
    "mind_map": "Generated Mind Map",
    "flashcards": "Generated Flashcards",
    "quiz": "Generated Quiz",
    "slide_deck": "Generated Slide Deck",
}


def _pick_auto_generate_types(studio_recommendations: List[Dict[str, Any]]) -> List[str]:
    recs = studio_recommendations or []
    auto = [
        str(item.get("type"))
        for item in recs
        if item.get("auto_generate") and str(item.get("type")) in VALID_STUDIO_TYPES
    ]
    if len(auto) >= 2:
        return auto[:2]
    ranked = [
        str(item.get("type"))
        for item in recs
        if str(item.get("type")) in VALID_STUDIO_TYPES
    ]
    merged: List[str] = list(auto)
    for stype in ranked:
        if stype not in merged:
            merged.append(stype)
        if len(merged) >= 2:
            break
    for stype in ("flashcards", "quiz", "mind_map", "slide_deck"):
        if stype not in merged:
            merged.append(stype)
        if len(merged) >= 2:
            break
    return merged[:2]


def _format_studio_content(task_type: str, result: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if not result or not isinstance(result, dict):
        return None
    if result.get("content"):
        content = result["content"]
        if isinstance(content, str) and not content.strip():
            return None
        out: Dict[str, Any] = {
            "task_type": result.get("task_type") or task_type,
            "content": content,
        }
        for key in ("infographic_data", "summary_bullets", "image_url", "image_error"):
            if key in result:
                out[key] = result[key]
        return out
    if result.get("data"):
        data = result["data"]
        if isinstance(data, list) and len(data) == 0:
            return None
        if isinstance(data, dict) and len(data) == 0:
            return None
        if result.get("task_type"):
            return result
        return {"task_type": task_type, **result}
    return None


class TutorNotebookPrepareService:
    def __init__(self, db: AsyncSession, tenant_id: str, user_id: str):
        self.db = db
        self.tenant_id = tenant_id
        self.user_id = user_id
        self.notebook_service = NotebookService(db, tenant_id, user_id)
        self.bootstrap_service = TutorNotebookBootstrapService(db, tenant_id, user_id)
        self.studio_service = StudioService(db, tenant_id, user_id)
        self.feature_service = StudioFeatureService(db, tenant_id, user_id)
        self.context_cache = TutorNcertContextCache(tenant_id)

    async def prepare_notebook(
        self,
        *,
        title: str,
        tutor_scope: Dict[str, Any],
        class_level: Optional[str] = None,
        subject: Optional[str] = None,
        focus: Optional[str] = None,
    ) -> Dict[str, Any]:
        timing: Dict[str, int] = {}
        t_total = time.perf_counter()

        scope = _normalize_scope(tutor_scope)
        scope_settings = dict(tutor_scope)
        scope_settings.setdefault("class_num", scope["class_num"])
        scope_settings.setdefault("subject_key", scope["subject_key"])
        scope_settings.setdefault("subject_slug", scope["subject_slug"])
        scope_settings.setdefault("chapter_no", scope["chapter_no"])
        scope_settings.setdefault("chapter_title", scope["chapter_title"])
        scope_settings.setdefault("filter_chapter_name", scope["filter_chapter_name"])

        t0 = time.perf_counter()
        notebook = await self.notebook_service.create_notebook(
            title=title,
            mode="tutor",
            class_level=class_level,
            subject=subject,
            focus=focus,
            settings={"tutor_scope": scope_settings},
        )
        timing["create_notebook_ms"] = int((time.perf_counter() - t0) * 1000)
        print(f"[TUTOR_PREPARE] phase=create_notebook ms={timing['create_notebook_ms']}")

        t0 = time.perf_counter()
        ncert_context, topic_summary, cache_hit = await self.bootstrap_service.fetch_scope_materials(
            scope, context_cache=self.context_cache
        )
        timing["ncert_retrieval_ms"] = int((time.perf_counter() - t0) * 1000)
        timing["ncert_cache_hit"] = 1 if cache_hit else 0
        print(
            f"[TUTOR_PREPARE] phase=ncert_retrieval ms={timing['ncert_retrieval_ms']} "
            f"cache_hit={bool(cache_hit)}"
        )

        context_block = self.bootstrap_service.build_context_block(ncert_context, topic_summary)

        t0 = time.perf_counter()
        payload = await self.bootstrap_service.generate_bootstrap_payload(
            scope, ncert_context, topic_summary
        )
        if not payload:
            payload = self.bootstrap_service.fallback_payload(scope, topic_summary)
        timing["bootstrap_llm_ms"] = int((time.perf_counter() - t0) * 1000)
        print(f"[TUTOR_PREPARE] phase=bootstrap_llm ms={timing['bootstrap_llm_ms']}")

        auto_types = _pick_auto_generate_types(payload.get("studio_recommendations") or [])

        t0 = time.perf_counter()
        studio_results = await asyncio.gather(
            *[
                self._generate_studio_asset(task_type, context_block)
                for task_type in auto_types
            ],
            return_exceptions=True,
        )
        timing["studio_parallel_ms"] = int((time.perf_counter() - t0) * 1000)
        print(f"[TUTOR_PREPARE] phase=studio_parallel ms={timing['studio_parallel_ms']}")

        t0 = time.perf_counter()
        chat_id, assets_created, asset_records = await self._persist_all(
            str(notebook.id),
            payload,
            auto_types,
            studio_results,
        )
        timing["persist_ms"] = int((time.perf_counter() - t0) * 1000)
        print(f"[TUTOR_PREPARE] phase=persist ms={timing['persist_ms']}")

        timing["total_ms"] = int((time.perf_counter() - t_total) * 1000)
        print(f"[TUTOR_PREPARE] total_ms={timing['total_ms']} assets={assets_created}")

        return {
            "notebook_id": str(notebook.id),
            "slug": notebook.slug,
            "opening_summary": payload["opening_summary"],
            "suggestions": payload["suggestions"],
            "studio_recommendations": payload["studio_recommendations"],
            "chat_id": chat_id,
            "assets_created": assets_created,
            "assets": asset_records,
            "auto_types": auto_types,
            "timing": timing,
            "partial_failure": assets_created < len(auto_types),
        }

    async def warm_ncert_context(self, tutor_scope: Dict[str, Any]) -> Dict[str, Any]:
        scope = _normalize_scope(tutor_scope)
        return await self.context_cache.warm(
            scope,
            lambda: self.bootstrap_service.fetch_ncert_context_raw(scope),
        )

    async def _generate_studio_asset(
        self, task_type: str, context_block: str
    ) -> Tuple[str, Optional[Dict[str, Any]]]:
        if not (context_block or "").strip():
            return task_type, None
        try:
            result = await self.studio_service.generate(
                task_type,
                [],
                context_mode="selection_only",
                selection_text=context_block,
            )
            formatted = _format_studio_content(task_type, result)
            return task_type, formatted
        except Exception as exc:
            print(f"[TUTOR_PREPARE] studio {task_type} failed: {exc}")
            return task_type, None

    async def _persist_all(
        self,
        notebook_id: str,
        payload: Dict[str, Any],
        auto_types: List[str],
        studio_results: List[Any],
    ) -> Tuple[Optional[str], int, List[Dict[str, Any]]]:
        chat = await self.bootstrap_service.chat_service.create_chat(
            title="Chapter overview",
            notebook_id=notebook_id,
        )
        await self.bootstrap_service.chat_service.add_message(
            chat_id=str(chat.id),
            role="assistant",
            content=payload["opening_summary"],
        )

        notebook = await self.notebook_service.get_notebook(notebook_id)
        settings_dict = dict(notebook.settings or {}) if notebook else {}
        completed_at = datetime.now(timezone.utc).isoformat()
        settings_dict["tutor_bootstrap"] = {
            "completed_at": completed_at,
            "opening_summary": payload["opening_summary"],
            "suggestions": payload["suggestions"],
            "studio_recommendations": payload["studio_recommendations"],
            "overview_chat_id": str(chat.id),
            "studio_generation_started": True,
        }
        await self.notebook_service.update_notebook(notebook_id, settings=settings_dict)

        assets_created = 0
        asset_records: List[Dict[str, Any]] = []
        for i, task_type in enumerate(auto_types):
            raw = studio_results[i] if i < len(studio_results) else None
            if isinstance(raw, Exception):
                continue
            resolved_type, content = raw if isinstance(raw, tuple) else (task_type, None)
            if not content:
                continue
            title = TITLE_BY_TYPE.get(resolved_type, "Generated Content")
            feature = await self.feature_service.save_feature(
                notebook_id=notebook_id,
                feature_type=resolved_type,
                title=title,
                content=content,
                source_ids=[],
            )
            assets_created += 1
            asset_records.append(
                {
                    "id": str(feature.id),
                    "type": resolved_type,
                    "title": title,
                }
            )

        return str(chat.id), assets_created, asset_records
