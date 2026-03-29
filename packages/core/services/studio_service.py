"""
Studio Service

Handles generative tasks with smart model routing.
Routes to optimal model based on task type.

Uses LLM abstraction layer and prompt templates.
"""

from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
import asyncio
import json
import os
import re
import time
import traceback

from config.settings import settings
from packages.core.llm import get_llm_client, get_model_for_task
from packages.core.llm._base import LLMProvider
from packages.core.prompts import load_prompt
from packages.core.rag.vectorstores.pinecone_store import PineconeVectorStore
from packages.core.monitoring.pipeline_trace import get_pipeline_trace_store


STUDIO_BROAD_RETRIEVAL_QUERIES: Tuple[str, ...] = (
    "Educational source material overview and key concepts",
    "Main themes definitions and key terms from the material",
    "Examples applications procedures and important details",
    "Structural sections summaries and conclusions",
    "Causes effects relationships how components interact and dependencies",
    "Step-by-step processes workflows methods and sequential explanations",
    "Comparisons contrasts differences similarities advantages and limitations",
)

# Single-document infographic: broader coverage for charts, timelines, data, geography (task_type infographic only)
STUDIO_INFOGRAPHIC_BROAD_RETRIEVAL_QUERIES: Tuple[str, ...] = (
    "Educational document overview executive summary and key takeaways",
    "Main themes core ideas definitions terminology and key concepts",
    "Important details examples use cases applications and procedures",
    "Document structure section headings summaries and conclusions",
    "Numerical data statistics metrics measurements quantities and units",
    "Trends percentages ratios comparisons growth and changes over time",
    "Timeline chronological sequence historical events milestones and dates",
    "Comparisons contrasts similarities differences before and after",
    "Causes effects relationships dependencies inputs and outputs",
    "Charts tables figures diagrams captions and labeled data",
    "Geographic locations maps regions countries cities and spatial context",
    "Step-by-step workflows processes sequences how-to instructions",
    "Glossary vocabulary acronyms named entities and proper nouns",
    "Lists enumerations bullet points ranked items and categories",
)


def _match_vec_id(match: Any) -> Optional[str]:
    if match is None:
        return None
    if isinstance(match, dict):
        mid = match.get("id")
        return str(mid) if mid is not None else None
    mid = getattr(match, "id", None)
    return str(mid) if mid is not None else None


def _match_score(match: Any) -> float:
    if isinstance(match, dict):
        return float(match.get("score") or 0.0)
    return float(getattr(match, "score", 0.0) or 0.0)


def _match_chunk_text(match: Any) -> str:
    meta: Any = {}
    if isinstance(match, dict):
        meta = match.get("metadata") or {}
    else:
        meta = getattr(match, "metadata", None) or {}
    if isinstance(meta, dict):
        return (meta.get("text") or "").strip()
    if hasattr(meta, "get"):
        return str(meta.get("text") or "").strip()
    return ""


def _match_source_id(match: Any) -> Optional[str]:
    meta: Any = {}
    if isinstance(match, dict):
        meta = match.get("metadata") or {}
    else:
        meta = getattr(match, "metadata", None) or {}
    if isinstance(meta, dict):
        sid = meta.get("source_id")
    elif hasattr(meta, "get"):
        sid = meta.get("source_id")
    else:
        return None
    if sid is None or sid == "":
        return None
    return str(sid)


def merge_studio_match_lists(
    per_query_matches: List[List[Any]],
    max_chunks: int,
    *,
    balance_source_ids: Optional[List[str]] = None,
) -> Tuple[str, int, int]:
    """
    Union Pinecone matches across queries by vector id (keep best score per id).
    Returns (context_text, chunks_included, unique_ids_before_truncate).

    When balance_source_ids has 2+ ids, reserves a minimum share of max_chunks per
    source (by metadata.source_id) before filling the rest by global score, so
    multi-document context is not dominated by a single high-scoring file. Used for
    mind_map, report, and flashcards when multiple sources are selected.
    """
    best: Dict[str, Tuple[float, str, Optional[str]]] = {}
    for matches in per_query_matches:
        for m in matches or []:
            vid = _match_vec_id(m)
            if not vid:
                continue
            text = _match_chunk_text(m)
            if not text:
                continue
            sc = _match_score(m)
            sid = _match_source_id(m)
            prev = best.get(vid)
            if prev is None or sc > prev[0]:
                best[vid] = (sc, text, sid)
    n_unique = len(best)
    cap = max(0, int(max_chunks))
    items = [(vid, sc, text, sid) for vid, (sc, text, sid) in best.items()]

    want = [str(s) for s in (balance_source_ids or []) if s is not None and str(s) != ""]
    if cap == 0:
        return "", 0, n_unique

    if len(want) <= 1:
        ranked = sorted(items, key=lambda x: -x[1])
        top = ranked[:cap]
        texts = [t for _, _, t, _ in top]
        return "\n\n".join(texts), len(texts), n_unique

    # Not enough slots to give each selected source a dedicated chunk; use global order.
    if cap < len(want):
        ranked = sorted(items, key=lambda x: -x[1])
        top = ranked[:cap]
        texts = [t for _, _, t, _ in top]
        return "\n\n".join(texts), len(texts), n_unique

    by_source: Dict[str, List[Tuple[str, float, str]]] = {s: [] for s in want}
    for vid, sc, text, sid in items:
        key = sid if sid else ""
        if key in by_source:
            by_source[key].append((vid, sc, text))

    min_per = max(1, cap // len(want))
    chosen_set: set[str] = set()
    ordered: List[str] = []

    for s in want:
        pool = by_source[s]
        pool.sort(key=lambda x: -x[1])
        taken = 0
        for vid, sc, text in pool:
            if len(ordered) >= cap:
                break
            if taken >= min_per:
                break
            if vid in chosen_set:
                continue
            chosen_set.add(vid)
            ordered.append(vid)
            taken += 1

    for vid, sc, text, sid in sorted(items, key=lambda x: -x[1]):
        if len(ordered) >= cap:
            break
        if vid in chosen_set:
            continue
        chosen_set.add(vid)
        ordered.append(vid)

    texts = [best[vid][1] for vid in ordered]
    return "\n\n".join(texts), len(texts), n_unique


# Studio Reports modal — must match apps/api/schemas/studio.py report_format Literal and frontend ReportSpec.
_REPORT_FORMAT_ALLOWED = frozenset({
    "integrated",
    "briefing",
    "study_guide",
    "newsletter",
    "thematic_summary",
})


def _normalize_report_format(value: Optional[str]) -> str:
    """Map API/UI report_format to a template key; default integrated."""
    if value is None or not str(value).strip():
        return "integrated"
    v = str(value).strip().lower().replace("-", "_")
    return v if v in _REPORT_FORMAT_ALLOWED else "integrated"


def _studio_span(
    name: str,
    started: float,
    *,
    input_summary: Optional[Dict[str, Any]] = None,
    output_summary: Optional[Dict[str, Any]] = None,
    status: str = "ok",
    error_message: Optional[str] = None,
    feature_tag: Optional[str] = None,
) -> None:
    dt = (time.perf_counter() - started) * 1000
    get_pipeline_trace_store().add_span(
        name,
        dt,
        input_summary=input_summary or {},
        output_summary=output_summary or {},
        status=status,
        error_message=error_message,
        feature_tag=feature_tag,
    )


class StudioService:
    """
    Service for Studio generation tasks.

    Smart Routing:
    - Structured tasks (quiz, flashcards, mind_map, slide_deck) -> GPT-4o-mini
    - Content-heavy tasks (report, infographic) -> GPT-4o (OpenAI)
    """

    def __init__(self, db: AsyncSession, tenant_id: str, user_id: str = None):
        self.db = db
        self.tenant_id = tenant_id
        self.user_id = user_id
        self.vector_store = PineconeVectorStore(tenant_id)

    async def generate(
        self,
        task_type: str,
        source_ids: list,
        custom_instructions: Optional[str] = None,
        retrieval_focus: Optional[str] = None,
        report_format: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Generate Studio content based on task type.

        retrieval_focus: optional topic string for query-conditioned vector retrieval
        (separate from custom_instructions formatting).
        report_format: optional tailored report style when task_type is "report"
            (integrated | briefing | study_guide | newsletter | thematic_summary).
        """
        if task_type == "infographic" and len(source_ids) != 1:
            raise ValueError(
                "Infographic requires exactly one selected source. "
                "Select a single document and try again."
            )

        context, retrieval_meta = await self._retrieve_studio_context(
            source_ids, retrieval_focus, task_type
        )
        retrieval_queries_note = self._format_retrieval_queries_note(
            retrieval_meta.get("queries_used") or []
        )

        if not context or not context.strip():
            print(
                f"[WARNING] Empty context for sources: {source_ids}. "
                "Generation may produce generic content."
            )

        if task_type in ["quiz", "flashcards", "mind_map", "slide_deck"]:
            return await self._generate_structured_task(
                task_type,
                context,
                custom_instructions,
                retrieval_queries_note,
                selected_source_count=len(source_ids),
            )
        if task_type == "report":
            return await self._generate_report(
                task_type,
                context,
                custom_instructions,
                retrieval_queries_note,
                selected_source_count=len(source_ids),
                report_format=report_format,
            )
        if task_type == "infographic":
            return await self._generate_infographic(
                task_type, context, custom_instructions, retrieval_queries_note
            )
        return await self._generate_report(
            task_type,
            context,
            custom_instructions,
            retrieval_queries_note,
            selected_source_count=len(source_ids),
            report_format=report_format,
        )

    def _format_retrieval_queries_note(self, queries_used: List[str]) -> str:
        if not queries_used:
            return ""
        max_chars = int(getattr(settings, "STUDIO_RETRIEVAL_NOTE_MAX_CHARS", 600))
        parts: List[str] = []
        for i, q in enumerate(queries_used[:16]):
            line = f"{i + 1}. {q.strip()}"
            parts.append(line)
        text = "\n".join(parts)
        if len(text) > max_chars:
            return text[: max_chars - 3] + "..."
        return text

    async def _retrieve_studio_context(
        self,
        source_ids: list,
        retrieval_focus: Optional[str],
        task_type: str,
    ) -> Tuple[str, Dict[str, Any]]:
        feature_tag = f"studio_{task_type}"
        meta: Dict[str, Any] = {
            "mode": "broad",
            "queries_used": [],
            "chunk_count": 0,
            "matches_before_merge": 0,
            "unique_vectors": 0,
        }
        if not source_ids:
            print("[STUDIO] No source IDs provided")
            return "", meta

        focus = (retrieval_focus or "").strip()
        # Flashcards always use broad studio queries (no topic rewrite) for consistent,
        # syllabus-style coverage across all selected sources.
        if task_type == "flashcards" and focus:
            print(
                "[STUDIO] flashcards: ignoring retrieval_focus; "
                "using STUDIO_BROAD_RETRIEVAL_QUERIES only"
            )
            focus = ""
        filter_dict = {"source_id": {"$in": source_ids}}
        top_k = int(getattr(settings, "STUDIO_RETRIEVAL_TOP_K_PER_QUERY", 10))
        query_cap = int(getattr(settings, "STUDIO_RETRIEVAL_QUERIES_CAP", 3))
        max_chunks = int(getattr(settings, "STUDIO_CONTEXT_MAX_CHUNKS", 28))
        if task_type == "infographic":
            max_chunks = int(
                getattr(settings, "STUDIO_INFOGRAPHIC_CONTEXT_MAX_CHUNKS", max_chunks)
            )

        t_retrieval = time.perf_counter()
        all_match_lists: List[List[Any]] = []
        queries_used: List[str] = []

        try:
            if focus:
                meta["mode"] = "topic_rewrite"
                t_rw = time.perf_counter()
                from packages.core.rag.agents.query_rewriter import QueryRewriter

                rewriter = QueryRewriter(self.tenant_id, self.user_id)
                rw = await rewriter.rewrite_query(
                    focus,
                    conversation_history=None,
                    max_rewrites=3,
                    feature_tag="studio_query_rewriter",
                )
                queries_used = list(rw.get("queries") or [focus])[:query_cap]
                if not queries_used:
                    queries_used = [focus]
                _studio_span(
                    "StudioRetrieval/QueryRewrite",
                    t_rw,
                    input_summary={"raw_focus_snippet": focus[:400]},
                    output_summary={
                        "queries": [q[:220] for q in queries_used[:5]],
                        "used_rewrites": rw.get("used_rewrites"),
                    },
                    feature_tag=feature_tag,
                )
            else:
                meta["mode"] = "broad"
                if task_type == "infographic":
                    ig_cap = int(
                        getattr(settings, "STUDIO_INFOGRAPHIC_RETRIEVAL_QUERIES_CAP", 14)
                    )
                    queries_used = list(STUDIO_INFOGRAPHIC_BROAD_RETRIEVAL_QUERIES)[
                        : max(1, ig_cap)
                    ]
                else:
                    queries_used = list(STUDIO_BROAD_RETRIEVAL_QUERIES)

            t_vq = time.perf_counter()
            total_raw = 0
            for q in queries_used:
                query_embedding = await self.vector_store.generate_embedding(
                    q,
                    metrics_user_id=self.user_id,
                    metrics_feature_tag="embedding",
                )
                results = await self.vector_store.query_vectors(
                    query_embedding=query_embedding,
                    top_k=top_k,
                    filter=filter_dict,
                )
                matches = results.get("matches", []) if isinstance(results, dict) else getattr(results, "matches", []) or []
                all_match_lists.append(list(matches))
                total_raw += len(matches)

            _studio_span(
                "StudioRetrieval/VectorQuery",
                t_vq,
                input_summary={
                    "queries_run": len(queries_used),
                    "top_k": top_k,
                    "source_count": len(source_ids),
                },
                output_summary={"matches_total": total_raw},
                feature_tag=feature_tag,
            )

            balance_ids: Optional[List[str]] = None
            if len(source_ids) > 1 and task_type in ("mind_map", "report", "flashcards"):
                balance_ids = [str(s) for s in source_ids if s is not None]

            context, chunk_count, n_unique = merge_studio_match_lists(
                all_match_lists, max_chunks, balance_source_ids=balance_ids
            )
            meta["queries_used"] = queries_used
            meta["chunk_count"] = chunk_count
            meta["matches_before_merge"] = total_raw
            meta["unique_vectors"] = n_unique

            _studio_span(
                "StudioRetrieval",
                t_retrieval,
                input_summary={
                    "task_type": task_type,
                    "source_count": len(source_ids),
                    "retrieval_focus_snippet": focus[:300] if focus else None,
                },
                output_summary={
                    "mode": meta["mode"],
                    "queries_used": [q[:180] for q in queries_used[:6]],
                    "chunk_count": chunk_count,
                    "unique_vectors": n_unique,
                },
                feature_tag=feature_tag,
            )

            if not context or not context.strip():
                print(f"[STUDIO] WARNING: No content retrieved from sources: {source_ids}")
                print("[STUDIO] Ingestion, Pinecone, or vector IDs may be missing.")

            print(
                f"[STUDIO] Retrieved {chunk_count} chunk(s) from {len(source_ids)} source(s) "
                f"({meta['mode']}, {len(queries_used)} queries)"
            )
            return context, meta

        except ValueError as e:
            _studio_span(
                "StudioRetrieval",
                t_retrieval,
                input_summary={"source_count": len(source_ids)},
                output_summary={},
                status="error",
                error_message=str(e)[:500],
                feature_tag=feature_tag,
            )
            print(f"[STUDIO] Configuration error retrieving context: {str(e)}")
            return "", meta
        except Exception as e:
            _studio_span(
                "StudioRetrieval",
                t_retrieval,
                input_summary={"source_count": len(source_ids)},
                output_summary={},
                status="error",
                error_message=str(e)[:500],
                feature_tag=feature_tag,
            )
            print(
                f"[STUDIO] Error retrieving context: {type(e).__name__}: {str(e)}\n"
                f"{traceback.format_exc()}"
            )
            return "", meta

    def _load_prompt_template(
        self,
        task_type: str,
        context: str,
        custom_instructions: Optional[str],
        template_map: Dict[str, str],
        default_template: str,
        retrieval_queries_note: str = "",
        *,
        selected_source_count: int = 1,
        report_format: Optional[str] = None,
    ) -> str:
        """Load prompt template with fallback."""
        template_path = template_map.get(task_type, default_template)
        try:
            kw: Dict[str, Any] = {
                "context": context or "",
                "custom_instructions": custom_instructions or "",
                "retrieval_queries_note": retrieval_queries_note or "",
            }
            if task_type in ("mind_map", "report", "flashcards"):
                kw["selected_source_count"] = max(1, int(selected_source_count))
            if task_type == "report":
                kw["report_format"] = _normalize_report_format(report_format)
            return load_prompt(template_path, **kw)
        except FileNotFoundError:
            print(f"[STUDIO] Prompt template not found: {template_path}, using fallback")
            return f"Generate a {task_type} based on: {context or 'general content'}"

    def _validate_generated_content(
        self,
        content: str,
        task_type: str,
        response: Any,
    ) -> None:
        """Validate that content was actually generated."""
        if not content or not content.strip():
            model_name = response.model if hasattr(response, "model") else "unknown"
            raise ValueError(
                f"No content was generated for {task_type}. "
                f"The model may have been blocked, encountered an error, or returned empty content. "
                f"Model used: {model_name}. "
                f"Please check your API keys and try again."
            )

    def _clean_markdown_code_blocks(self, content: str) -> str:
        """Remove markdown code blocks from content."""
        if content.strip().startswith("```"):
            lines = content.strip().split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            return "\n".join(lines)
        return content

    async def _generate_structured_task(
        self,
        task_type: str,
        context: str,
        custom_instructions: Optional[str],
        retrieval_queries_note: str = "",
        *,
        selected_source_count: int = 1,
    ) -> Dict[str, Any]:
        """Generate structured Studio tasks (JSON-ish)."""
        provider, model = get_model_for_task(task_type)
        llm_client = get_llm_client(provider=provider, model=model, temperature=0.7)

        prompt = self._load_prompt_template(
            task_type,
            context,
            custom_instructions,
            {
                "quiz": "studio/quiz_prompt.j2",
                "flashcards": "studio/flashcards_prompt.j2",
                "mind_map": "studio/mind_map_prompt.j2",
                "slide_deck": "studio/slide_deck_prompt.j2",
            },
            "studio/quiz_prompt.j2",
            retrieval_queries_note=retrieval_queries_note,
            selected_source_count=selected_source_count,
        )

        system_prompt = load_prompt("studio/system_educational_json_markdown.j2")
        studio_tag = f"studio_{task_type}"
        t_gen = time.perf_counter()
        gen_kwargs: Dict[str, Any] = {
            "tenant_id": str(self.tenant_id),
            "user_id": self.user_id,
            "feature_tag": studio_tag,
        }
        if task_type in ("slide_deck", "mind_map"):
            gen_kwargs["max_tokens"] = 4096
        try:
            response = await llm_client.generate(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=0.7,
                **gen_kwargs,
            )
        except Exception as e:
            error_msg = str(e)
            print(f"[STUDIO] [GPT] Generation failed: {type(e).__name__}: {error_msg}")
            _studio_span(
                "StudioGenerate",
                t_gen,
                input_summary={
                    "task_type": task_type,
                    "context_chars": len(context or ""),
                },
                output_summary={},
                status="error",
                error_message=error_msg[:500],
                feature_tag=studio_tag,
            )
            raise ValueError(
                f"Failed to generate {task_type}: {error_msg}. "
                f"Please check your API keys and try again."
            )

        content = response.content or ""
        print(f"[STUDIO] [GPT] Generated content length: {len(content)} characters")
        if len(content) > 0:
            print(f"[STUDIO] [GPT] Content preview: {content[:100]}...")

        _studio_span(
            "StudioGenerate",
            t_gen,
            input_summary={
                "task_type": task_type,
                "context_chars": len(context or ""),
            },
            output_summary={
                "content_chars": len(content),
                "content_preview": (content[:320] + "...")
                if len(content) > 320
                else content,
            },
            feature_tag=studio_tag,
        )

        self._validate_generated_content(content, task_type, response)
        content = self._clean_markdown_code_blocks(content)

        if not content or not content.strip():
            raise ValueError(
                f"No valid content was generated for {task_type} after processing. "
                f"The model response may have been empty or invalid."
            )

        if task_type in ["quiz", "flashcards"]:
            try:
                data = json.loads(content)
                print(f"[STUDIO] Successfully parsed {task_type} response")
                return {"task_type": task_type, "data": data}
            except json.JSONDecodeError as e:
                print(f"[STUDIO] Failed to parse JSON response: {str(e)}")
                print(f"[STUDIO] Response content: {content[:500]}...")
                json_match = re.search(r"\{.*\}", content, re.DOTALL)
                if json_match:
                    try:
                        data = json.loads(json_match.group())
                        print("[STUDIO] Successfully extracted JSON from response")
                        return {"task_type": task_type, "data": data}
                    except Exception:
                        pass
                raise ValueError(
                    f"Failed to parse {task_type} response as JSON. Response: {content[:200]}"
                )
        return {"task_type": task_type, "content": content}

    async def _generate_report(
        self,
        task_type: str,
        context: str,
        custom_instructions: Optional[str],
        retrieval_queries_note: str = "",
        *,
        selected_source_count: int = 1,
        report_format: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Generate long-form markdown content (reports and other narrative tasks)."""
        provider, model = get_model_for_task("report" if task_type == "report" else task_type)
        llm_client = get_llm_client(provider=provider, model=model, temperature=0.5)

        prompt = self._load_prompt_template(
            task_type,
            context,
            custom_instructions,
            {"report": "studio/report_prompt.j2"},
            "studio/report_prompt.j2",
            retrieval_queries_note=retrieval_queries_note,
            selected_source_count=selected_source_count,
            report_format=report_format,
        )

        system_prompt = load_prompt("studio/system_educational_markdown_fallback.j2")
        studio_tag = f"studio_{task_type}"
        t_gen = time.perf_counter()
        gen_kwargs: Dict[str, Any] = {
            "tenant_id": str(self.tenant_id),
            "user_id": self.user_id,
            "feature_tag": studio_tag,
            "max_tokens": 4096,
        }
        try:
            response = await llm_client.generate(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=0.5,
                **gen_kwargs,
            )
        except Exception as e:
            error_msg = str(e)
            print(f"[STUDIO] [REPORT] Generation failed: {type(e).__name__}: {error_msg}")
            _studio_span(
                "StudioGenerate",
                t_gen,
                input_summary={"task_type": task_type, "context_chars": len(context or "")},
                output_summary={},
                status="error",
                error_message=error_msg[:500],
                feature_tag=studio_tag,
            )
            raise ValueError(f"Failed to generate {task_type}: {error_msg}")

        content = (response.content or "").strip()
        _studio_span(
            "StudioGenerate",
            t_gen,
            input_summary={"task_type": task_type, "context_chars": len(context or "")},
            output_summary={"content_chars": len(content)},
            feature_tag=studio_tag,
        )

        self._validate_generated_content(content, task_type, response)
        content = self._clean_markdown_code_blocks(content).strip()
        if not content:
            raise ValueError(
                f"No valid content was generated for {task_type} after processing."
            )
        return {"task_type": task_type, "content": content}

    @staticmethod
    def _infographic_bullets_markdown(bullets: List[str]) -> str:
        lines = [f"- {b.strip()}" for b in bullets if b and str(b).strip()]
        if not lines:
            return "- Review the key ideas in your selected document."
        return "\n".join(lines)

    async def _infographic_learner_bullets(self, context: str) -> List[str]:
        defaults = [
            "Main themes from your selected document.",
            "Use the graphic as a quick visual anchor while you read the source.",
            "Verify names, numbers, and definitions in the original text.",
        ]
        try:
            ctx = (context or "").strip()
            if not ctx:
                return defaults
            if len(ctx) > 12000:
                ctx = ctx[:12000]
            provider, model = get_model_for_task("flashcards")
            llm_client = get_llm_client(provider=provider, model=model, temperature=0.2)
            user_prompt = load_prompt(
                "studio/infographic_summary_bullets.j2",
                context=ctx,
            )
            gen_kwargs: Dict[str, Any] = {
                "tenant_id": str(self.tenant_id),
                "user_id": self.user_id,
                "feature_tag": "studio_infographic_summary",
                "max_tokens": 400,
            }
            if provider == LLMProvider.OPENAI:
                gen_kwargs["response_format"] = {"type": "json_object"}
            resp = await llm_client.generate(
                prompt=user_prompt,
                system_prompt='Reply with JSON only: {"bullets": ["...", "...", "...", "..."]}',
                temperature=0.2,
                **gen_kwargs,
            )
            text = (resp.content or "").strip()
            parsed = json.loads(text)
            bl = parsed.get("bullets") if isinstance(parsed, dict) else None
            if not isinstance(bl, list):
                return defaults
            out = [str(x).strip() for x in bl if x and str(x).strip()][:4]
            if len(out) < 3:
                for d in defaults:
                    if len(out) >= 4:
                        break
                    if d not in out:
                        out.append(d)
            return out[:4]
        except Exception as e:
            print(f"[STUDIO] [INFOGRAPHIC] Learner bullets failed: {e}")
            return defaults

    def _parse_infographic_json(self, raw: str) -> Optional[Dict[str, Any]]:
        """Parse structured infographic JSON from LLM output, tolerating markdown fences."""
        text = self._clean_markdown_code_blocks(raw).strip()
        try:
            data = json.loads(text)
            if isinstance(data, dict) and data.get("title") and data.get("sections"):
                valid_layouts = {"comparison", "process", "timeline", "sections"}
                if data.get("layout") not in valid_layouts:
                    data["layout"] = "sections"
                valid_themes = {"blue", "green", "purple", "teal", "orange"}
                if data.get("color_theme") not in valid_themes:
                    data["color_theme"] = "blue"
                return data
        except (json.JSONDecodeError, TypeError, KeyError):
            pass
        return None

    async def _generate_infographic(
        self,
        task_type: str,
        context: str,
        custom_instructions: Optional[str],
        retrieval_queries_note: str = "",
    ) -> Dict[str, Any]:
        """Generate a structured infographic (JSON data rendered by the frontend)."""
        provider, model = get_model_for_task("infographic")
        llm_client = get_llm_client(provider=provider, model=model, temperature=0.3)

        prompt = load_prompt(
            "studio/infographic_structured_prompt.j2",
            context=context or "",
            custom_instructions=custom_instructions or "",
        )

        studio_tag = "studio_infographic"
        t_gen = time.perf_counter()

        gen_kwargs: Dict[str, Any] = {
            "tenant_id": str(self.tenant_id),
            "user_id": self.user_id,
            "feature_tag": studio_tag,
            "max_tokens": 1500,
        }
        if provider == LLMProvider.OPENAI:
            gen_kwargs["response_format"] = {"type": "json_object"}

        try:
            response = await llm_client.generate(
                prompt=prompt,
                system_prompt='You are an educational infographic designer. Reply with valid JSON only.',
                temperature=0.3,
                **gen_kwargs,
            )
        except Exception as e:
            error_msg = str(e)
            print(
                f"[STUDIO] [INFOGRAPHIC] Structured generation failed: "
                f"{type(e).__name__}: {error_msg}"
            )
            _studio_span(
                "StudioGenerate",
                t_gen,
                input_summary={"task_type": task_type, "context_chars": len(context or "")},
                output_summary={},
                status="error",
                error_message=error_msg[:500],
                feature_tag=studio_tag,
            )
            raise ValueError(f"Failed to generate infographic: {error_msg}")

        raw = (response.content or "").strip()
        _studio_span(
            "StudioGenerate",
            t_gen,
            input_summary={"task_type": task_type, "context_chars": len(context or "")},
            output_summary={"content_chars": len(raw)},
            feature_tag=studio_tag,
        )

        infographic_data = self._parse_infographic_json(raw)
        if infographic_data is None:
            raise ValueError(
                "Infographic generation produced invalid JSON. Please try again."
            )

        bullets_task = asyncio.create_task(self._infographic_learner_bullets(context))
        bullets = await bullets_task
        content_md = self._infographic_bullets_markdown(bullets)

        return {
            "task_type": task_type,
            "content": content_md,
            "summary_bullets": bullets,
            "infographic_data": infographic_data,
        }
