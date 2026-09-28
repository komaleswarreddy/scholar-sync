"""Extract individual questions from uploaded source documents."""

from __future__ import annotations

import io
import re
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import pypdf
from fastapi import HTTPException
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from packages.core.database.models.source import Source, SourceStatus
from packages.core.database.models.source_question import SourceQuestion
from packages.core.llm import get_llm_client, get_model_for_task
from packages.core.processing.question_regex_parser import regex_extract_questions
from packages.core.prompts import load_prompt
from packages.core.rag.whole_file_map_reduce import fetch_all_chunks_for_sources, _chunk_text
from packages.core.storage import get_storage_service

_PREVIEW_MAX = 120
_TEXT_BATCH_CHARS = 12_000
_PROCESSING_STALE_SECONDS = 90
_DEVANAGARI_RE = re.compile(r"[\u0900-\u097F]")
_LATIN_RE = re.compile(r"[A-Za-z]")
_DIAGRAM_CONTEXT_MAX = 1_500
_MCQ_OPTION_RE = re.compile(r"\([A-D]\)|\b[A-D]\)")
_INSTRUCTION_MARKERS = (
    "this section comprises",
    "there is no overall choice",
    "internal choice has been provided",
    "use of calculator is not allowed",
    "questions no.",
    "marks each",
)


def _parse_json_object(raw: str) -> Optional[Dict[str, Any]]:
    text = (raw or "").strip()
    if not text:
        return None
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```$", "", text)
    try:
        import json

        return json.loads(text)
    except json.JSONDecodeError:
        return None


def _preview(text: str) -> str:
    cleaned = re.sub(r"\s+", " ", (text or "").strip())
    if len(cleaned) <= _PREVIEW_MAX:
        return cleaned
    return cleaned[: _PREVIEW_MAX - 1].rstrip() + "…"


def _normalize_sections(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    sections = payload.get("sections")
    if not isinstance(sections, list):
        return []

    rows: List[Dict[str, Any]] = []
    sort_order = 0
    seen_numbers: set[int] = set()

    for section in sections:
        if not isinstance(section, dict):
            continue
        label = section.get("label")
        section_label = str(label).strip() if label else None
        questions = section.get("questions")
        if not isinstance(questions, list):
            continue
        for item in questions:
            if not isinstance(item, dict):
                continue
            try:
                number = int(item.get("number"))
            except (TypeError, ValueError):
                continue
            full_text = str(item.get("fullText") or item.get("full_text") or "").strip()
            if len(full_text) < 5:
                continue
            if number in seen_numbers:
                number = max(seen_numbers, default=0) + 1
            seen_numbers.add(number)
            preview = str(item.get("preview") or "").strip() or _preview(full_text)
            page_hint = item.get("pageHint") if item.get("pageHint") is not None else item.get("page_hint")
            try:
                page_hint = int(page_hint) if page_hint is not None else None
            except (TypeError, ValueError):
                page_hint = None
            confidence = str(item.get("confidence") or "high").lower()
            if confidence not in ("high", "low"):
                confidence = "high"
            rows.append(
                {
                    "question_number": number,
                    "section_label": section_label,
                    "preview": _preview(preview),
                    "full_text": full_text,
                    "page_hint": page_hint,
                    "sort_order": sort_order,
                    "confidence": confidence,
                }
            )
            sort_order += 1

    rows.sort(key=lambda r: (r["sort_order"], r["question_number"]))
    return rows


def _is_stale_processing(extraction_meta: Dict[str, Any]) -> bool:
    if extraction_meta.get("status") != "processing":
        return False
    started = extraction_meta.get("started_at")
    if not started:
        return True
    try:
        started_at = datetime.fromisoformat(str(started).replace("Z", "+00:00"))
        if started_at.tzinfo is None:
            started_at = started_at.replace(tzinfo=timezone.utc)
        return datetime.now(timezone.utc) - started_at > timedelta(seconds=_PROCESSING_STALE_SECONDS)
    except (TypeError, ValueError):
        return True


def _is_english_only_question(text: str) -> bool:
    candidate = (text or "").strip()
    if len(candidate) < 5:
        return False
    # Strict gate for Hindi segments: any Devanagari means drop the question.
    if _DEVANAGARI_RE.search(candidate):
        return False
    latin_count = len(_LATIN_RE.findall(candidate))
    # Keep numeric/equation-heavy questions when there is no Hindi script.
    return latin_count >= 3 or len(candidate) >= 20


def _filter_english_rows(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    kept: List[Dict[str, Any]] = []
    for row in rows:
        full_text = str(row.get("full_text") or "").strip()
        if not _is_english_only_question(full_text):
            continue
        lowered = full_text.lower()
        if any(marker in lowered for marker in _INSTRUCTION_MARKERS):
            # Guard against instruction/preamble blocks being misdetected as Q1.
            if "section a" in lowered or "section b" in lowered or not _MCQ_OPTION_RE.search(full_text):
                continue
        kept.append(row)
    for idx, row in enumerate(kept, start=1):
        row["question_number"] = idx
        row["sort_order"] = idx - 1
        row["preview"] = _preview(str(row.get("preview") or row.get("full_text") or ""))
    return kept


class SourceQuestionExtractionService:
    def __init__(self, db: AsyncSession, tenant_id: str, user_id: str):
        self.db = db
        self.tenant_id = tenant_id
        self.user_id = user_id

    async def _get_source(self, source_id: str) -> Source:
        try:
            sid = uuid.UUID(source_id)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Invalid source ID") from exc
        result = await self.db.execute(
            select(Source).where(
                Source.id == sid,
                Source.tenant_id == uuid.UUID(self.tenant_id),
                Source.user_id == self.user_id,
            )
        )
        source = result.scalar_one_or_none()
        if not source:
            raise HTTPException(status_code=404, detail="Source not found")
        return source

    def _get_extraction_meta(self, source: Source) -> Dict[str, Any]:
        meta = source.source_metadata if isinstance(source.source_metadata, dict) else {}
        extraction = meta.get("question_extraction")
        return extraction if isinstance(extraction, dict) else {}

    def _set_extraction_meta(self, source: Source, patch: Dict[str, Any]) -> None:
        meta = dict(source.source_metadata or {})
        current = self._get_extraction_meta(source)
        current.update(patch)
        meta["question_extraction"] = current
        source.source_metadata = meta
        flag_modified(source, "source_metadata")

    async def _fetch_chunks_text(self, source: Source) -> str:
        chunks = await fetch_all_chunks_for_sources(
            self.tenant_id, [str(source.id)], user_id=self.user_id
        )
        texts = [_chunk_text(c) for c in chunks]
        return "\n".join(t for t in texts if t).strip()

    async def _fetch_storage_text(self, source: Source, *, allow_ocr: bool) -> str:
        storage = get_storage_service(self.tenant_id)
        try:
            file_content = await storage.download_file(source.s3_key)
        except Exception as exc:
            print(f"[QUESTION_EXTRACT] Storage download failed for {source.id}: {exc}")
            return ""

        if not file_content:
            return ""

        key_lower = (source.s3_key or "").lower()
        title_lower = (source.title or "").lower()

        if key_lower.endswith(".pdf") or str(source.type).lower() == "pdf":
            reader = pypdf.PdfReader(io.BytesIO(file_content))
            page_texts = [(page.extract_text() or "") for page in reader.pages]
            combined = "\n".join(page_texts).strip()
            if len(combined) < 20 and allow_ocr:
                from packages.core.processing.image_ocr import ocr_scanned_pdf

                combined, _ = await ocr_scanned_pdf(
                    file_content,
                    None,
                    tenant_id=self.tenant_id,
                    user_id=self.user_id,
                )
            diagram_context = await self._extract_pdf_diagram_context(file_content)
            if diagram_context:
                combined = f"{combined}\n\n{diagram_context}".strip()
            return combined

        from packages.core.processing.image_ocr import (
            is_image_upload,
            ocr_image_bytes,
            resolve_image_mime,
        )

        if is_image_upload(title_lower, "") or is_image_upload(key_lower, ""):
            if not allow_ocr:
                return ""
            mime = resolve_image_mime(title_lower or key_lower, "")
            return await ocr_image_bytes(
                file_content,
                mime_type=mime,
                tenant_id=self.tenant_id,
                user_id=self.user_id,
            )

        if key_lower.endswith(".txt"):
            return file_content.decode("utf-8", errors="replace").strip()

        return ""

    async def _extract_pdf_diagram_context(self, file_content: bytes) -> str:
        from packages.core.processing.image_ocr import extract_pdf_diagram_context

        try:
            context = await extract_pdf_diagram_context(
                file_content,
                tenant_id=self.tenant_id,
                user_id=self.user_id,
            )
            return context[:_DIAGRAM_CONTEXT_MAX].strip()
        except Exception as exc:
            print(f"[QUESTION_EXTRACT] diagram OCR skipped: {exc}")
            return ""

    async def _fetch_source_text(self, source: Source) -> str:
        """Indexed sources: reuse ingest chunks first (avoids slow re-OCR)."""
        t0 = time.perf_counter()
        indexed = source.status == SourceStatus.INDEXED.value

        if indexed:
            combined = await self._fetch_chunks_text(source)
            if len(combined) >= 20:
                elapsed = int((time.perf_counter() - t0) * 1000)
                print(f"[QUESTION_EXTRACT] chunks text {len(combined)} chars in {elapsed}ms")
                return combined[: _TEXT_BATCH_CHARS * 2]

        combined = await self._fetch_storage_text(source, allow_ocr=not indexed)
        if len(combined) >= 20:
            elapsed = int((time.perf_counter() - t0) * 1000)
            print(f"[QUESTION_EXTRACT] storage text {len(combined)} chars in {elapsed}ms")
            return combined[: _TEXT_BATCH_CHARS * 2]

        if not indexed:
            combined = await self._fetch_chunks_text(source)
            if len(combined) >= 20:
                return combined[: _TEXT_BATCH_CHARS * 2]

        raise HTTPException(
            status_code=400,
            detail="Could not extract enough text from the source for question parsing",
        )

    async def _extract_rows(self, document_text: str) -> List[Dict[str, Any]]:
        t0 = time.perf_counter()
        rows = regex_extract_questions(document_text)
        if rows:
            rows = _filter_english_rows(rows)
            elapsed = int((time.perf_counter() - t0) * 1000)
            print(f"[QUESTION_EXTRACT] regex found {len(rows)} English questions in {elapsed}ms")
            return rows

        payload = await self._llm_extract(document_text)
        rows = _normalize_sections(payload)
        rows = _filter_english_rows(rows)
        elapsed = int((time.perf_counter() - t0) * 1000)
        print(f"[QUESTION_EXTRACT] LLM found {len(rows)} English questions in {elapsed}ms")
        return rows

    async def _llm_extract(self, document_text: str) -> Dict[str, Any]:
        provider, model = get_model_for_task("source_question_extract")
        llm = get_llm_client(provider=provider, model=model, temperature=0)
        prompt = load_prompt(
            "source_questions/extract.j2",
            document_text=document_text[:_TEXT_BATCH_CHARS],
        )
        resp = await llm.generate(
            prompt,
            response_format={"type": "json_object"},
            tenant_id=str(self.tenant_id),
            user_id=self.user_id,
            feature_tag="source_question_extract",
        )
        parsed = _parse_json_object(resp.content)
        if not parsed:
            raise HTTPException(status_code=502, detail="LLM returned invalid JSON for question extraction")
        return parsed

    async def _persist_rows(self, source: Source, rows: List[Dict[str, Any]], version: int) -> None:
        await self.db.execute(
            delete(SourceQuestion).where(
                SourceQuestion.source_id == source.id,
                SourceQuestion.tenant_id == uuid.UUID(self.tenant_id),
            )
        )
        notebook_id = source.notebook_id
        for row in rows:
            self.db.add(
                SourceQuestion(
                    tenant_id=uuid.UUID(self.tenant_id),
                    notebook_id=notebook_id,
                    source_id=source.id,
                    question_number=row["question_number"],
                    section_label=row["section_label"],
                    preview=row["preview"],
                    full_text=row["full_text"],
                    page_hint=row["page_hint"],
                    sort_order=row["sort_order"],
                    confidence=row["confidence"],
                )
            )
        self._set_extraction_meta(
            source,
            {
                "status": "ready",
                "version": version,
                "question_count": len(rows),
                "error": None,
                "started_at": None,
            },
        )
        await self.db.commit()
        await self.db.refresh(source)

    async def kickoff_extraction(self, source_id: str, *, force: bool = False) -> Dict[str, Any]:
        """Validate, dedupe in-flight work, mark processing, return immediately."""
        source = await self._get_source(source_id)
        if source.status != SourceStatus.INDEXED.value:
            raise HTTPException(status_code=409, detail="Source is not ready for question extraction")

        extraction_meta = self._get_extraction_meta(source)
        existing_questions = await self.list_questions(source_id)
        if existing_questions and not force:
            return {
                "status": "ready",
                "question_count": len(existing_questions),
                "extraction_version": extraction_meta.get("version", 1),
                "source_id": str(source.id),
                "questions": existing_questions,
                "run_background": False,
            }

        if extraction_meta.get("status") == "processing" and _is_stale_processing(extraction_meta):
            extraction_meta = {**extraction_meta, "status": "idle"}
        elif extraction_meta.get("status") == "processing" and not _is_stale_processing(extraction_meta):
            return {
                **self._public_status(source, extraction_meta),
                "questions": existing_questions,
                "run_background": False,
            }

        if extraction_meta.get("status") == "ready" and not force:
            questions = await self.list_questions(source_id)
            return {
                "status": "ready",
                "question_count": len(questions),
                "extraction_version": extraction_meta.get("version", 1),
                "source_id": str(source.id),
                "questions": questions,
                "run_background": False,
            }

        version = int(extraction_meta.get("version") or 0) + 1
        self._set_extraction_meta(
            source,
            {
                "status": "processing",
                "version": version,
                "error": None,
                "started_at": datetime.now(timezone.utc).isoformat(),
            },
        )
        await self.db.commit()

        return {
            "status": "processing",
            "question_count": 0,
            "extraction_version": version,
            "source_id": str(source.id),
            "questions": [],
            "run_background": True,
        }

    async def run_extraction_job(self, source_id: str) -> None:
        """Heavy extraction work — intended for background tasks."""
        t0 = time.perf_counter()
        source = await self._get_source(source_id)
        extraction_meta = self._get_extraction_meta(source)
        version = int(extraction_meta.get("version") or 1)

        try:
            document_text = await self._fetch_source_text(source)
            rows = await self._extract_rows(document_text)
            await self._persist_rows(source, rows, version)
            elapsed = int((time.perf_counter() - t0) * 1000)
            print(f"[QUESTION_EXTRACT] completed source {source_id} ({len(rows)} q) in {elapsed}ms")
        except HTTPException as http_exc:
            await self.db.rollback()
            source = await self._get_source(source_id)
            detail = http_exc.detail if isinstance(http_exc.detail, str) else "extraction_failed"
            self._set_extraction_meta(
                source,
                {"status": "failed", "version": version, "error": detail[:500]},
            )
            await self.db.commit()
        except Exception as exc:
            await self.db.rollback()
            print(f"[QUESTION_EXTRACT] Failed for source {source_id}: {type(exc).__name__}: {exc}")
            source = await self._get_source(source_id)
            self._set_extraction_meta(
                source,
                {"status": "failed", "version": version, "error": str(exc)[:500]},
            )
            await self.db.commit()

    async def extract_questions(self, source_id: str, *, force: bool = False) -> Dict[str, Any]:
        """Synchronous path (tests / scripts). Production API uses kickoff + background."""
        kickoff = await self.kickoff_extraction(source_id, force=force)
        if not kickoff.pop("run_background", False):
            kickoff.pop("questions", None)
            return kickoff

        await self.run_extraction_job(source_id)
        source = await self._get_source(source_id)
        extraction_meta = self._get_extraction_meta(source)
        status = extraction_meta.get("status") or "failed"
        questions = await self.list_questions(source_id) if status == "ready" else []
        if status == "failed":
            raise HTTPException(
                status_code=422,
                detail=extraction_meta.get("error") or "Question extraction failed",
            )
        return {
            "status": "ready",
            "question_count": len(questions),
            "extraction_version": extraction_meta.get("version", 0),
            "questions": questions,
        }

    def _public_status(self, source: Source, extraction_meta: Dict[str, Any]) -> Dict[str, Any]:
        status = extraction_meta.get("status") or "idle"
        return {
            "status": status,
            "question_count": extraction_meta.get("question_count", 0),
            "extraction_version": extraction_meta.get("version", 0),
            "error": extraction_meta.get("error"),
            "source_id": str(source.id),
        }

    async def list_questions(self, source_id: str) -> List[Dict[str, Any]]:
        source = await self._get_source(source_id)
        result = await self.db.execute(
            select(SourceQuestion)
            .where(
                SourceQuestion.source_id == source.id,
                SourceQuestion.tenant_id == uuid.UUID(self.tenant_id),
            )
            .order_by(SourceQuestion.sort_order.asc(), SourceQuestion.question_number.asc())
        )
        rows = result.scalars().all()
        return [self._question_summary(q) for q in rows]

    async def get_question(self, source_id: str, question_id: str) -> Dict[str, Any]:
        source = await self._get_source(source_id)
        try:
            qid = uuid.UUID(question_id)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Invalid question ID") from exc
        result = await self.db.execute(
            select(SourceQuestion).where(
                SourceQuestion.id == qid,
                SourceQuestion.source_id == source.id,
                SourceQuestion.tenant_id == uuid.UUID(self.tenant_id),
            )
        )
        question = result.scalar_one_or_none()
        if not question:
            raise HTTPException(status_code=404, detail="Question not found")
        return self._question_detail(question, source)

    def _question_summary(self, question: SourceQuestion) -> Dict[str, Any]:
        return {
            "id": str(question.id),
            "source_id": str(question.source_id),
            "question_number": question.question_number,
            "section_label": question.section_label,
            "preview": question.preview,
            "page_hint": question.page_hint,
            "sort_order": question.sort_order,
            "confidence": question.confidence,
        }

    def _question_detail(self, question: SourceQuestion, source: Source) -> Dict[str, Any]:
        detail = self._question_summary(question)
        detail["full_text"] = question.full_text
        detail["source_title"] = source.title
        return detail

    async def get_extraction_status(self, source_id: str) -> Dict[str, Any]:
        source = await self._get_source(source_id)
        extraction_meta = self._get_extraction_meta(source)

        if extraction_meta.get("status") == "processing" and _is_stale_processing(extraction_meta):
            self._set_extraction_meta(
                source,
                {
                    "status": "idle",
                    "error": "Previous extraction timed out. Retry to extract questions.",
                },
            )
            await self.db.commit()
            extraction_meta = self._get_extraction_meta(source)

        questions = await self.list_questions(source_id)
        status = extraction_meta.get("status") or "idle"

        # Questions in DB are the source of truth — repair stale processing/ready metadata.
        if questions:
            if status != "ready" or extraction_meta.get("question_count", 0) != len(questions):
                self._set_extraction_meta(
                    source,
                    {
                        "status": "ready",
                        "question_count": len(questions),
                        "error": None,
                        "started_at": None,
                    },
                )
                await self.db.commit()
                extraction_meta = self._get_extraction_meta(source)
            status = "ready"
        elif status == "ready":
            status = "idle"
            extraction_meta = {**extraction_meta, "status": "idle", "question_count": 0, "error": None}

        return {
            **self._public_status(source, {**extraction_meta, "status": status}),
            "questions": questions,
        }
