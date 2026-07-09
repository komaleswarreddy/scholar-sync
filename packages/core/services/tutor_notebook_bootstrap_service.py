"""Tutor notebook first-open bootstrap: summary, suggestions, studio plan."""

from __future__ import annotations

import asyncio
import json
import re
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from sqlalchemy.ext.asyncio import AsyncSession

from config.settings import settings
from packages.core.llm import LLMProvider, get_llm_client, get_model_for_task
from packages.core.prompts import load_prompt
from packages.core.rag.retriever import Retriever
from packages.core.services.chat_service import ChatService
from packages.core.services.ncert_catalog_helpers import subject_display_label
from packages.core.services.notebook_service import NotebookService
from packages.core.services.tutor_catalog_service import TutorCatalogService
from packages.core.services.tutor_ncert_context_cache import TutorNcertContextCache

BOOTSTRAP_RETRIEVAL_QUERY = (
    "Summarize main topics, key definitions, and relationships in this chapter"
)

VALID_STUDIO_TYPES = {"flashcards", "quiz", "mind_map", "slide_deck"}

STUDIO_TYPE_ORDER = ["flashcards", "quiz", "mind_map", "slide_deck"]

NARRATIVE_SUBJECT_KEYS = frozenset(
    {"civics-polity", "history", "geography", "social_science"}
)


def _auto_generate_pair_for_scope(scope: Dict[str, Any]) -> tuple[str, str]:
    """Subject-aware default pair when LLM output is missing or incomplete."""
    subject = str(scope.get("subject_key") or scope.get("subject_slug") or "").strip().lower()
    if scope.get("concept"):
        return ("flashcards", "quiz")
    if subject in NARRATIVE_SUBJECT_KEYS or "civic" in subject or "history" in subject:
        return ("slide_deck", "quiz")
    if subject in {"economics"}:
        return ("mind_map", "quiz")
    if subject in {"mathematics", "math"}:
        return ("quiz", "flashcards")
    return ("flashcards", "quiz")


def studio_recommendations_for_scope(scope: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Build ranked studio recommendations with subject-aware auto_generate flags."""
    auto_a, auto_b = _auto_generate_pair_for_scope(scope)
    auto_types = {auto_a, auto_b}
    reasons = {
        "flashcards": "Key terms and definitions",
        "quiz": "Chapter practice questions",
        "mind_map": "Topic connections",
        "slide_deck": "Narrative chapter overview",
    }
    ordered = [auto_a, auto_b]
    for stype in STUDIO_TYPE_ORDER:
        if stype not in ordered:
            ordered.append(stype)
    return [
        {
            "type": stype,
            "reason": reasons.get(stype, "Study support"),
            "auto_generate": stype in auto_types,
        }
        for stype in ordered
    ]


def _parse_json_object(raw: str) -> Optional[Dict[str, Any]]:
    text = (raw or "").strip()
    if not text:
        return None
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```$", "", text)
    try:
        data = json.loads(text)
        return data if isinstance(data, dict) else None
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            try:
                data = json.loads(text[start : end + 1])
                return data if isinstance(data, dict) else None
            except json.JSONDecodeError:
                return None
    return None


_FOLLOW_UP_CONTEXT_MAX_CHARS = 2000


def fallback_follow_ups(
    scope: Dict[str, Any],
    user_message: str,
    assistant_message: str,
) -> List[str]:
    """Chapter-aware follow-ups when the LLM path fails or returns nothing."""
    chapter_ref = f"Ch. {scope['chapter_no']} {scope['chapter_title']}"
    concept_part = scope.get("concept") or "this chapter"
    user_text = (user_message or "").strip()
    if not user_text:
        return [
            f"What are the key definitions in {chapter_ref}?",
            f"Explain the main topics in {chapter_ref} step by step.",
            f"What should I focus on for exams in {chapter_ref}?",
        ]
    assistant_lower = (assistant_message or "").lower()
    if "not found" in assistant_lower or "provided sources" in assistant_lower:
        return [
            f"Can you rephrase my question using NCERT terms from {chapter_ref}?",
            f"What related subtopics in {chapter_ref} should I study next?",
            f"Give me a simpler explanation of {concept_part} in {chapter_ref}.",
        ]
    return [
        f"Can you explain that part of {chapter_ref} with an example?",
        f"How might this appear in an exam question on {concept_part}?",
        f"What else in {chapter_ref} connects to what we just discussed?",
    ]


def _normalize_scope(scope: Dict[str, Any]) -> Dict[str, Any]:
    class_num = int(scope.get("class_num") or 12)
    subject_key = str(scope.get("subject_key") or scope.get("subject_slug") or "physics")
    chapter_no = int(scope.get("chapter_no") or 1)
    chapter_title = str(
        scope.get("chapter_title") or scope.get("chapter_name") or f"Chapter {chapter_no}"
    ).strip()
    concept = scope.get("concept")
    concept_str = str(concept).strip() if concept else None
    subsubject = scope.get("subsubject")
    subject_label = subject_display_label(subject_key, subsubject)
    filter_chapter_name = str(scope.get("filter_chapter_name") or chapter_title).strip().lower()
    return {
        "class_num": class_num,
        "subject_key": subject_key,
        "subject_slug": str(scope.get("subject_slug") or subject_key),
        "chapter_no": chapter_no,
        "chapter_title": chapter_title,
        "filter_chapter_name": filter_chapter_name,
        "concept": concept_str,
        "subject_label": subject_label,
    }


class TutorNotebookBootstrapService:
    def __init__(self, db: AsyncSession, tenant_id: str, user_id: str):
        self.db = db
        self.tenant_id = tenant_id
        self.user_id = user_id
        self.notebook_service = NotebookService(db, tenant_id, user_id)
        self.catalog_service = TutorCatalogService(db)
        self.chat_service = ChatService(db, tenant_id, user_id)
        self.context_cache = TutorNcertContextCache(tenant_id)

    async def bootstrap_notebook(self, notebook_id: str) -> Dict[str, Any]:
        notebook = await self.notebook_service.get_notebook(notebook_id)
        if not notebook:
            raise ValueError("Notebook not found")
        if notebook.mode != "tutor":
            raise ValueError("Bootstrap is only available for tutor notebooks")

        settings_dict = dict(notebook.settings or {})
        existing = settings_dict.get("tutor_bootstrap")
        if isinstance(existing, dict) and existing.get("completed_at"):
            chat_id = existing.get("overview_chat_id")
            return {
                "opening_summary": existing.get("opening_summary", ""),
                "suggestions": existing.get("suggestions") or [],
                "studio_recommendations": existing.get("studio_recommendations") or [],
                "chat_id": str(chat_id) if chat_id else None,
                "cached": True,
            }

        scope_raw = settings_dict.get("tutor_scope")
        if not isinstance(scope_raw, dict):
            raise ValueError("Notebook is missing tutor_scope settings")
        scope = _normalize_scope(scope_raw)

        t0 = time.perf_counter()
        ncert_context, topic_summary, cache_hit = await self.fetch_scope_materials(
            scope, context_cache=self.context_cache
        )
        print(
            f"[TUTOR_BOOTSTRAP] phase=ncert_retrieval ms={int((time.perf_counter() - t0) * 1000)} "
            f"cache_hit={bool(cache_hit)}"
        )

        t0 = time.perf_counter()
        payload = await self.generate_bootstrap_payload(scope, ncert_context, topic_summary)
        if not payload:
            payload = self.fallback_payload(scope, topic_summary)
        print(f"[TUTOR_BOOTSTRAP] phase=bootstrap_llm ms={int((time.perf_counter() - t0) * 1000)}")

        t0 = time.perf_counter()
        chat = await self.chat_service.create_chat(
            title="Chapter overview",
            notebook_id=notebook_id,
        )
        await self.chat_service.add_message(
            chat_id=str(chat.id),
            role="assistant",
            content=payload["opening_summary"],
        )

        completed_at = datetime.now(timezone.utc).isoformat()
        bootstrap_settings = {
            "completed_at": completed_at,
            "opening_summary": payload["opening_summary"],
            "suggestions": payload["suggestions"],
            "studio_recommendations": payload["studio_recommendations"],
            "overview_chat_id": str(chat.id),
            "studio_generation_started": False,
        }
        merged_settings = dict(settings_dict)
        merged_settings["tutor_bootstrap"] = bootstrap_settings
        await self.notebook_service.update_notebook(notebook_id, settings=merged_settings)
        print(f"[TUTOR_BOOTSTRAP] phase=persist ms={int((time.perf_counter() - t0) * 1000)}")

        return {
            **payload,
            "chat_id": str(chat.id),
            "cached": False,
        }

    async def generate_follow_ups(
        self,
        *,
        notebook_id: str,
        user_message: str,
        assistant_message: str,
    ) -> List[str]:
        notebook = await self.notebook_service.get_notebook(notebook_id)
        if not notebook or notebook.mode != "tutor":
            return []

        scope_raw = (notebook.settings or {}).get("tutor_scope")
        if not isinstance(scope_raw, dict):
            return []
        scope = _normalize_scope(scope_raw)

        trimmed_user = user_message.strip()[:_FOLLOW_UP_CONTEXT_MAX_CHARS]
        trimmed_assistant = assistant_message.strip()[:_FOLLOW_UP_CONTEXT_MAX_CHARS]

        prompt = load_prompt(
            "tutor/follow_up_questions.j2",
            class_num=scope["class_num"],
            subject_label=scope["subject_label"],
            chapter_no=scope["chapter_no"],
            chapter_title=scope["chapter_title"],
            concept=scope["concept"],
            user_message=trimmed_user,
            assistant_message=trimmed_assistant,
        )

        provider, model = get_model_for_task("tutor_follow_ups")
        llm_client = get_llm_client(provider=provider, model=model, temperature=0.4)
        gen_kwargs: Dict[str, Any] = {
            "tenant_id": self.tenant_id,
            "user_id": self.user_id,
            "feature_tag": "tutor_follow_ups",
            "max_tokens": 200,
        }
        if provider == LLMProvider.OPENAI:
            gen_kwargs["response_format"] = {"type": "json_object"}

        try:
            resp = await llm_client.generate(
                prompt=prompt,
                system_prompt="Return valid JSON only.",
                temperature=0.4,
                **gen_kwargs,
            )
            data = _parse_json_object(resp.content or "")
            out: List[str] = []
            if data:
                raw = data.get("follow_ups") or []
                for item in raw:
                    if isinstance(item, str) and item.strip():
                        out.append(item.strip()[:90])
                    if len(out) >= 3:
                        break
            if out:
                return out
            return fallback_follow_ups(scope, trimmed_user, trimmed_assistant)
        except Exception as exc:
            print(f"[TUTOR_BOOTSTRAP] follow-ups failed: {exc}")
            return fallback_follow_ups(scope, trimmed_user, trimmed_assistant)

    async def mark_studio_generation_started(self, notebook_id: str) -> None:
        notebook = await self.notebook_service.get_notebook(notebook_id)
        if not notebook:
            return
        settings_dict = dict(notebook.settings or {})
        bootstrap = dict(settings_dict.get("tutor_bootstrap") or {})
        if bootstrap.get("studio_generation_started"):
            return
        bootstrap["studio_generation_started"] = True
        settings_dict["tutor_bootstrap"] = bootstrap
        await self.notebook_service.update_notebook(notebook_id, settings=settings_dict)

    async def fetch_scope_materials(
        self,
        scope: Dict[str, Any],
        *,
        context_cache: Optional["TutorNcertContextCache"] = None,
    ) -> tuple[str, str, bool]:
        """Parallel NCERT context + catalog topic summary. Returns (ncert_context, topic_summary, cache_hit)."""
        cache_hit = False

        async def _fetch_ncert() -> str:
            nonlocal cache_hit
            if context_cache is not None:
                ctx, hit = await context_cache.get_or_fetch(
                    scope, lambda: self.fetch_ncert_context_raw(scope)
                )
                cache_hit = hit
                return ctx
            return await self.fetch_ncert_context_raw(scope)

        ncert_task = asyncio.create_task(_fetch_ncert())
        chapter_task = asyncio.create_task(
            self.catalog_service.get_chapter(
                scope["class_num"], scope["subject_key"], scope["chapter_no"]
            )
        )
        ncert_context, chapter = await asyncio.gather(ncert_task, chapter_task)
        topic_summary = (chapter.topic_summary or "").strip() if chapter else ""
        return ncert_context, topic_summary, cache_hit

    @staticmethod
    def build_context_block(ncert_context: str, topic_summary: str) -> str:
        context_block = ncert_context
        if topic_summary and topic_summary not in ncert_context:
            context_block = f"{topic_summary}\n\n{ncert_context}".strip()
        return context_block

    async def fetch_ncert_context_raw(self, scope: Dict[str, Any]) -> str:
        return await self._fetch_ncert_context(scope)

    async def generate_bootstrap_payload(
        self,
        scope: Dict[str, Any],
        ncert_context: str,
        topic_summary: str,
    ) -> Optional[Dict[str, Any]]:
        return await self._generate_bootstrap_payload(scope, ncert_context, topic_summary)

    def fallback_payload(self, scope: Dict[str, Any], topic_summary: str) -> Dict[str, Any]:
        return self._fallback_payload(scope, topic_summary)

    @staticmethod
    def _format_ncert_matches_as_context(
        matches: List[Dict[str, Any]],
        *,
        fallback: str = "",
        max_chunks: Optional[int] = None,
    ) -> str:
        parts: List[str] = []
        limit = max_chunks or getattr(settings, "DOCUMENT_SUMMARY_TOP_K", 12)
        max_chars = getattr(settings, "DOCUMENT_SUMMARY_MAX_CHUNK_CHARS", 1040)
        for i, m in enumerate(matches[:limit], 1):
            md = m.get("metadata") or {}
            text = (md.get("text") or "").strip()
            if not text:
                continue
            if len(text) > max_chars:
                text = text[:max_chars]
            title = md.get("display_source") or md.get("topic") or "NCERT"
            page = md.get("page_start") or md.get("page_number")
            page_str = f"p{page}" if page else f"chunk{i}"
            parts.append(f"[{i}] {title} ({page_str}): {text}")
        return "\n\n".join(parts) if parts else fallback

    async def _fetch_ncert_context(self, scope: Dict[str, Any]) -> str:
        if not getattr(settings, "ENABLE_NCERT_GLOBAL_IN_CHAT", False):
            return scope.get("chapter_title") or ""

        retriever = Retriever(self.tenant_id, user_id=self.user_id)
        try:
            matches = await retriever.retrieve_ncert_chapter_matches(
                query=BOOTSTRAP_RETRIEVAL_QUERY,
                ncert_class=scope["class_num"],
                ncert_subject=scope["subject_slug"],
                ncert_chapter_no=scope["chapter_no"],
                ncert_chapter_name=scope["filter_chapter_name"],
                ncert_concept=scope["concept"],
            )
        except Exception as exc:
            print(f"[TUTOR_BOOTSTRAP] retrieval failed: {exc}")
            return scope.get("chapter_title") or ""

        return self._format_ncert_matches_as_context(
            matches,
            fallback=str(scope.get("chapter_title") or ""),
        )

    async def _generate_bootstrap_payload(
        self,
        scope: Dict[str, Any],
        ncert_context: str,
        topic_summary: str,
    ) -> Optional[Dict[str, Any]]:
        context_block = ncert_context
        if topic_summary and topic_summary not in ncert_context:
            context_block = f"{topic_summary}\n\n{ncert_context}".strip()

        prompt = load_prompt(
            "tutor/notebook_bootstrap.j2",
            class_num=scope["class_num"],
            subject_label=scope["subject_label"],
            chapter_no=scope["chapter_no"],
            chapter_title=scope["chapter_title"],
            concept=scope["concept"],
            ncert_context=context_block or scope["chapter_title"],
        )

        provider, model = get_model_for_task("chat")
        llm_client = get_llm_client(provider=provider, model=model, temperature=0.35)
        gen_kwargs: Dict[str, Any] = {
            "tenant_id": self.tenant_id,
            "user_id": self.user_id,
            "feature_tag": "tutor_notebook_bootstrap",
            "max_tokens": 1400,
        }
        if provider == LLMProvider.OPENAI:
            gen_kwargs["response_format"] = {"type": "json_object"}

        try:
            resp = await llm_client.generate(
                prompt=prompt,
                system_prompt="Return valid JSON only.",
                temperature=0.35,
                **gen_kwargs,
            )
            data = _parse_json_object(resp.content or "")
            if not data:
                return None
            return self._sanitize_payload(data, scope)
        except Exception as exc:
            print(f"[TUTOR_BOOTSTRAP] LLM bootstrap failed: {exc}")
            return None

    def _sanitize_payload(self, data: Dict[str, Any], scope: Dict[str, Any]) -> Dict[str, Any]:
        opening_summary = str(data.get("opening_summary") or "").strip()
        suggestions_raw = data.get("suggestions") or []
        studio_raw = data.get("studio_recommendations") or []

        suggestions: List[Dict[str, str]] = []
        if isinstance(suggestions_raw, list):
            for item in suggestions_raw:
                if not isinstance(item, dict):
                    continue
                label = str(item.get("label") or "").strip()[:28]
                prompt = str(item.get("prompt") or "").strip()
                if label and prompt:
                    suggestions.append({"label": label, "prompt": prompt})
                if len(suggestions) >= 4:
                    break

        studio_recommendations: List[Dict[str, Any]] = []
        if isinstance(studio_raw, list):
            for item in studio_raw:
                if not isinstance(item, dict):
                    continue
                stype = str(item.get("type") or "").strip()
                if stype not in VALID_STUDIO_TYPES:
                    continue
                studio_recommendations.append(
                    {
                        "type": stype,
                        "reason": str(item.get("reason") or "").strip(),
                        "auto_generate": bool(item.get("auto_generate")),
                    }
                )
                if len(studio_recommendations) >= 4:
                    break

        if not opening_summary:
            opening_summary = self._fallback_payload(scope, "")["opening_summary"]
        if len(suggestions) < 2:
            suggestions = self._fallback_payload(scope, "")["suggestions"]
        if len(studio_recommendations) < 4:
            fallback_studio = self._fallback_payload(scope, "")["studio_recommendations"]
            seen = {s["type"] for s in studio_recommendations}
            for item in fallback_studio:
                if item["type"] not in seen:
                    studio_recommendations.append(item)
                    seen.add(item["type"])
                if len(studio_recommendations) >= 4:
                    break

        auto_indices = [i for i, s in enumerate(studio_recommendations) if s.get("auto_generate")]
        if len(auto_indices) > 2:
            keep = set(auto_indices[:2])
            for i, rec in enumerate(studio_recommendations):
                rec["auto_generate"] = i in keep
        elif len(auto_indices) < 2:
            for i, rec in enumerate(studio_recommendations):
                rec["auto_generate"] = i < 2

        return {
            "opening_summary": opening_summary,
            "suggestions": suggestions[:4],
            "studio_recommendations": studio_recommendations[:4],
        }

    def _fallback_payload(self, scope: Dict[str, Any], topic_summary: str) -> Dict[str, Any]:
        chapter_ref = f"Ch. {scope['chapter_no']} {scope['chapter_title']}"
        concept_part = scope["concept"] or "all concepts"
        summary_body = topic_summary or (
            f"This notebook covers **{chapter_ref}** in {scope['subject_label']}. "
            f"Use the tutor chat to explore {concept_part} with NCERT-grounded answers."
        )
        opening_summary = (
            f"## Summary\n\n"
            f"### Key topics\n"
            f"- **Chapter scope** — {summary_body}\n"
            f"- **Study focus** — {concept_part} in {scope['subject_label']}\n\n"
            "### Exam highlights\n"
            f"- Review **key terms** and definitions from {chapter_ref}\n"
            f"- Practice **exam-style questions** tied to this chapter\n\n"
            "### Ask me for full clarity\n\n"
            "1. Which part of this chapter feels hardest right now?\n"
            "2. Do you want definitions, solved examples, or exam-style questions first?\n"
            "3. Are you preparing for a class test or building long-term understanding?\n\n"
            "Tap a suggestion below or ask your own question to begin."
        )

        suggestions = [
            {
                "label": "Key definitions",
                "prompt": f"What are the key definitions in {chapter_ref}?",
            },
            {
                "label": "Main topics",
                "prompt": f"Explain the main topics in {chapter_ref} step by step.",
            },
            {
                "label": "Exam focus",
                "prompt": f"What should I focus on for exams in {chapter_ref}?",
            },
            {
                "label": "Quick recap",
                "prompt": f"Give me a quick recap of {concept_part} in {chapter_ref}.",
            },
        ]

        studio = studio_recommendations_for_scope(scope)

        return {
            "opening_summary": opening_summary,
            "suggestions": suggestions,
            "studio_recommendations": studio,
        }
