from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import asyncio
import hashlib
import json
import time
from typing import Any, Dict, List, Optional, Tuple

from config.settings import settings
from packages.core.llm.openai_compat import build_openai_http_clients
from packages.core.rag.vectorstores.pinecone_store import get_pinecone_index
from packages.core.rag.vectorstores.namespace import normalize_pinecone_namespace
from packages.core.rag.contextual_retrieval import ChunkContextualizer, ChunkEnrichment
from packages.core.monitoring.pipeline_trace import get_pipeline_trace_store


@dataclass(frozen=True)
class LlamaIndexIngestionResult:
    nodes_indexed: int
    chunks_for_cache: Optional[List[Tuple[str, Dict[str, Any]]]] = None


def _sync_build_vector_index(nodes: List[Any], storage_context: Any) -> None:
    """Run in a worker thread — LlamaIndex embedding + Pinecone upsert are synchronous."""
    from llama_index.core import VectorStoreIndex

    VectorStoreIndex(nodes=nodes, storage_context=storage_context)


async def _record_llamaindex_ingest_embeddings(
    *,
    tenant_id: str,
    user_id: str,
    nodes: List[Any],
    latency_ms: float,
    embedding_model: Optional[str] = None,
    usage_accumulator: Optional[Dict[str, Any]] = None,
    feature_tag: str = "embedding",
    request_id: Optional[str] = None,
) -> None:
    """
    LlamaIndex embeds chunks via OpenAIEmbedding without our LLM client wrappers.
    Record one aggregate usage row so the Agents dashboard reflects document ingestion.
    Token counts are estimated from text length (~4 chars/token).
    """
    if not nodes or not user_id:
        return
    try:
        from packages.core.guardrails.cost_manager import get_cost_manager

        total_chars = sum(len(getattr(n, "text", "") or "") for n in nodes)
        prompt_tokens = max(1, int(total_chars / 4))
        model = embedding_model or settings.OPENAI_EMBEDDING_MODEL
        cm = get_cost_manager()
        cost = cm.calculate_cost(model, prompt_tokens, 0)
        await cm.record_usage(
            tenant_id=str(tenant_id),
            user_id=str(user_id),
            model=model,
            provider="openai",
            prompt_tokens=prompt_tokens,
            completion_tokens=0,
            feature_tag=feature_tag,
            request_id=request_id,
            latency_ms=latency_ms,
        )
        if usage_accumulator is not None:
            usage_accumulator["embedding_prompt_tokens"] = int(
                usage_accumulator.get("embedding_prompt_tokens", 0)
            ) + int(prompt_tokens)
            usage_accumulator["embedding_cost_usd"] = float(
                usage_accumulator.get("embedding_cost_usd", 0.0)
            ) + float(cost)
    except Exception:
        pass


class LlamaIndexIngestionAdapter:
    """
    Ingest text into Pinecone via LlamaIndex while preserving:
    - namespace == tenant_id
    - vector ids: {source_id}_chunk_{i}
    - metadata keys used by existing retrieval/synthesis
    """

    def __init__(
        self,
        tenant_id: str,
        user_id: Optional[str] = None,
        *,
        pinecone_namespace: Optional[str] = None,
        embedding_model: Optional[str] = None,
        embedding_dimensions: Optional[int] = None,
        contextual_llm_model: Optional[str] = None,
        ingestion_run_id: Optional[str] = None,
        static_chunk_metadata: Optional[Dict[str, Any]] = None,
        metrics_tenant_id: Optional[str] = None,
        usage_accumulator: Optional[Dict[str, Any]] = None,
        sketch_document_title: Optional[str] = None,
    ):
        self.tenant_id = tenant_id
        self.user_id = user_id
        self._namespace = pinecone_namespace or normalize_pinecone_namespace(tenant_id)
        self._embedding_model = embedding_model
        self._embedding_dimensions = embedding_dimensions
        self._contextual_llm_model = contextual_llm_model
        self._ingestion_run_id = ingestion_run_id
        self._static_chunk_metadata = dict(static_chunk_metadata or {})
        self._metrics_tenant_id = metrics_tenant_id or tenant_id
        self._usage_accumulator = usage_accumulator
        # Optional title for sketch prompt only; not written to Pinecone chunk metadata.
        self._sketch_document_title = (sketch_document_title or "").strip() or None

    def _require_llamaindex(self):
        try:
            from llama_index.core import Settings as LISettings  # noqa: F401
            from llama_index.core.schema import TextNode  # noqa: F401
            from llama_index.core.node_parser import SentenceSplitter  # noqa: F401
            from llama_index.vector_stores.pinecone import PineconeVectorStore  # noqa: F401
            from llama_index.embeddings.openai import OpenAIEmbedding  # noqa: F401
        except Exception as e:  # pragma: no cover
            raise ValueError(
                "LlamaIndex dependencies not installed. "
                "Install llama-index-core, llama-index-vector-stores-pinecone, llama-index-embeddings-openai."
            ) from e


    def _build_nodes(
        self,
        *,
        text: str,
        source_id: str,
        pages: Optional[List[Tuple[int, str]]] = None,
    ) -> List["TextNode"]:
        """
        Build TextNodes with stable ids + metadata.

        We rely on LlamaIndex SentenceSplitter for chunking. We also add
        page metadata when available by aligning chunk text to page ranges
        using a best-effort heuristic.
        """
        from llama_index.core.node_parser import SentenceSplitter
        from llama_index.core.schema import TextNode

        chunk_size = getattr(settings, "CHUNK_SIZE", 1000)
        overlap_percent = getattr(settings, "CHUNK_OVERLAP_PERCENT", 0.12)
        chunk_overlap = int(chunk_size * overlap_percent)

        splitter = SentenceSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        chunks = splitter.split_text(text)

        # Best-effort page mapping: if we have pages, keep a running cursor in the full
        # concatenated text and assign pages based on where the chunk falls.
        page_spans: Optional[List[Tuple[int, int, int]]] = None
        if pages:
            spans: List[Tuple[int, int, int]] = []
            cursor = 0
            for page_num, page_text in pages:
                start = cursor
                cursor += len(page_text)
                end = cursor
                spans.append((page_num, start, end))
            page_spans = spans

        nodes: List[TextNode] = []
        cursor = 0
        for i, chunk_text in enumerate(chunks):
            node_id = f"{source_id}_chunk_{i}"

            metadata: Dict[str, Any] = {
                "source_id": source_id,
                "tenant_id": self._namespace,
                "chunk_index": i,
                # Important: existing pipeline expects text in metadata.
                "text": chunk_text,
            }

            if page_spans:
                # Find overlap between chunk position and page spans.
                start = cursor
                end = cursor + len(chunk_text)
                cursor = end

                covered_pages = [
                    page_num
                    for (page_num, p_start, p_end) in page_spans
                    if not (end <= p_start or start >= p_end)
                ]
                if covered_pages:
                    metadata["page_start"] = min(covered_pages)
                    metadata["page_end"] = max(covered_pages)
                    # Backward compatibility with existing citations code
                    metadata["page_number"] = metadata["page_start"]

            if self._static_chunk_metadata:
                for k, v in self._static_chunk_metadata.items():
                    if v is not None:
                        metadata[k] = v

            node = TextNode(text=chunk_text, id_=node_id, metadata=metadata)
            nodes.append(node)

        return nodes

    async def _enrich_nodes_contextual(
        self,
        *,
        nodes: List[Any],
        whole_document_text: str,
    ) -> List[Any]:
        """
        Contextual Retrieval: enrich each chunk with compact contextual metadata and
        embed concatenation while keeping raw chunk text in metadata for citations.
        """
        if not getattr(settings, "ENABLE_CONTEXTUAL_RETRIEVAL_INGESTION", True):
            return nodes
        if not nodes:
            return nodes
        if not (whole_document_text or "").strip():
            return nodes

        # Build shared document context once. NCERT uses a smaller cap + metadata header so we do not send
        # ~24k chars × N chunks. Optionally replace the raw excerpt with a compact one-time \"document sketch\"
        # (LLM) stored in a disk cache to minimize repeated document tokens.
        max_chars = int(getattr(settings, "CONTEXTUAL_RETRIEVAL_MAX_DOC_CONTEXT_CHARS", 24000))
        meta = self._static_chunk_metadata or {}
        header = ""
        use_doc_sketch = bool(getattr(settings, "CONTEXTUAL_RETRIEVAL_NCERT_USE_DOC_SKETCH", False))
        if meta.get("source") == "ncert":
            ncert_cap = int(getattr(settings, "CONTEXTUAL_RETRIEVAL_NCERT_DOC_CONTEXT_CHARS", 5000))
            max_chars = min(max_chars, ncert_cap)
            ds = str(meta.get("display_source") or "NCERT").strip()
            tp = str(meta.get("topic") or "").strip()
            chn = meta.get("chapter_no")
            chname = str(meta.get("chapter_name") or "").strip()
            chap = f" Ch.{chn}" if chn is not None else ""
            if chname:
                chap += f" ({chname})"
            header = f"Scope: {ds}.{chap}\nTopic: {tp}\n\n"

        doc_context = whole_document_text
        doc_sketch_used = False
        if meta.get("source") == "ncert" and use_doc_sketch:
            try:
                from packages.core.cache.sketch_store import DiskSketchStore, RedisSketchStore
                from packages.core.rag.contextual_retrieval.document_sketcher import (
                    generate_ncert_document_sketch,
                )

                key = str(meta.get("content_hash") or "").strip()
                if not key:
                    key = hashlib.sha256(whole_document_text.encode("utf-8", errors="ignore")).hexdigest()

                backend = str(
                    getattr(settings, "CONTEXTUAL_RETRIEVAL_NCERT_DOC_SKETCH_CACHE_BACKEND", "disk") or "disk"
                ).strip().lower()

                # Redis is async; disk store is sync. Use Redis when configured, otherwise disk.
                sketch_from_cache = False
                if backend == "redis":
                    rstore = RedisSketchStore()
                    sketch = await rstore.get(key)
                else:
                    dstore = DiskSketchStore()
                    sketch = dstore.get(key)
                if isinstance(sketch, dict):
                    sketch_from_cache = True
                else:
                    sketch = None

                if sketch is None:
                    model = (
                        str(getattr(settings, "CONTEXTUAL_RETRIEVAL_NCERT_DOC_SKETCH_MODEL", "") or "").strip()
                        or str(
                            self._contextual_llm_model
                            or getattr(settings, "NCERT_GLOBAL_CONTEXT_MODEL", "gpt-4o-mini")
                        )
                    )
                    sketch = await generate_ncert_document_sketch(
                        tenant_id=str(self._metrics_tenant_id),
                        user_id=self.user_id,
                        header=header.strip(),
                        document_text=whole_document_text,
                        model=model,
                        request_id=self._ingestion_run_id,
                        usage_accumulator=self._usage_accumulator,
                    )
                    sketch_from_cache = False
                    if isinstance(sketch, dict):
                        ttl = int(
                            getattr(
                                settings,
                                "CONTEXTUAL_RETRIEVAL_NCERT_DOC_SKETCH_CACHE_TTL_SECONDS",
                                30 * 24 * 3600,
                            )
                        )
                        if backend == "redis":
                            try:
                                await rstore.set(key, sketch, ttl_seconds=ttl)
                            except Exception:
                                DiskSketchStore().set(key, sketch, ttl_seconds=ttl)
                            else:
                                DiskSketchStore().set(key, sketch, ttl_seconds=ttl)
                        else:
                            dstore.set(key, sketch, ttl_seconds=ttl)

                if isinstance(sketch, dict):
                    doc_context = header + json.dumps(sketch, ensure_ascii=False)
                    doc_sketch_used = True
                    try:
                        if sketch_from_cache:
                            print(f"[NCERT] Document sketch cache hit (key={key[:12]}...)")
                        else:
                            print(
                                f"[NCERT] Document sketch cache miss -> generated "
                                f"(key={key[:12]}..., bytes={len(json.dumps(sketch))})"
                            )
                    except Exception:
                        pass
            except Exception as ex:
                print(f"[NCERT] Document sketch disabled due to error: {ex}")

        # Normal tenant uploads: optional one-time sketch (Redis/disk), same per-chunk metadata shape as today.
        if (
            not doc_sketch_used
            and bool(getattr(settings, "CONTEXTUAL_RETRIEVAL_USE_DOC_SKETCH", False))
            and (self._static_chunk_metadata or {}).get("source") != "ncert"
        ):
            try:
                from packages.core.cache.sketch_store import DiskSketchStore, RedisSketchStore
                from packages.core.rag.contextual_retrieval.document_sketcher import (
                    generate_upload_document_sketch,
                )

                content_key = hashlib.sha256(
                    whole_document_text.encode("utf-8", errors="ignore")
                ).hexdigest()
                tid = str(self.tenant_id or "").strip() or "unknown"
                backend = str(
                    getattr(settings, "CONTEXTUAL_RETRIEVAL_DOC_SKETCH_CACHE_BACKEND", "redis")
                    or "redis"
                ).strip().lower()
                upload_prefix = str(
                    getattr(
                        settings,
                        "CONTEXTUAL_RETRIEVAL_DOC_SKETCH_REDIS_KEY_PREFIX",
                        "upload:doc_sketch:",
                    )
                )
                hdr_lines: List[str] = []
                if self._sketch_document_title:
                    hdr_lines.append(f"Title: {self._sketch_document_title}")
                normal_header = ("\n".join(hdr_lines) + "\n\n") if hdr_lines else ""

                sketch: Optional[Dict[str, Any]] = None
                disk_key = f"{tid}_{content_key}"
                if backend == "redis":
                    rstore = RedisSketchStore(key_prefix=upload_prefix, tenant_segment=tid)
                    sketch = await rstore.get(content_key)
                else:
                    dstore = DiskSketchStore(cache_dir=Path("cache/uploads/sketch"))
                    sketch = dstore.get(disk_key)

                if sketch is None:
                    model = str(
                        getattr(settings, "CONTEXTUAL_RETRIEVAL_DOC_SKETCH_MODEL", "") or ""
                    ).strip()
                    sketch = await generate_upload_document_sketch(
                        tenant_id=str(self._metrics_tenant_id),
                        user_id=self.user_id,
                        header=normal_header.strip(),
                        document_text=whole_document_text,
                        model=model,
                        request_id=self._ingestion_run_id,
                        usage_accumulator=self._usage_accumulator,
                    )
                    if isinstance(sketch, dict):
                        ttl = int(
                            getattr(
                                settings,
                                "CONTEXTUAL_RETRIEVAL_DOC_SKETCH_CACHE_TTL_SECONDS",
                                3600,
                            )
                        )
                        if backend == "redis":
                            try:
                                await rstore.set(content_key, sketch, ttl_seconds=ttl)
                            except Exception:
                                DiskSketchStore(cache_dir=Path("cache/uploads/sketch")).set(
                                    disk_key, sketch, ttl_seconds=ttl
                                )
                        else:
                            dstore.set(disk_key, sketch, ttl_seconds=ttl)
                        print(
                            f"[UPLOAD] Document sketch cache miss -> generated "
                            f"(key={content_key[:12]}..., bytes={len(json.dumps(sketch))})"
                        )
                else:
                    print(f"[UPLOAD] Document sketch cache hit (key={content_key[:12]}...)")

                if isinstance(sketch, dict):
                    doc_context = normal_header + json.dumps(sketch, ensure_ascii=False)
                    doc_sketch_used = True
            except Exception as ex:
                print(f"[UPLOAD] Document sketch disabled due to error: {ex}")

        if getattr(settings, "ENABLE_CONTEXTUAL_RETRIEVAL_DOC_SUMMARY", True):
            body_budget = max(400, max_chars - len(header))
            if len(doc_context) > body_budget:
                half = body_budget // 2
                doc_context = doc_context[:half] + "\n\n[...snip...]\n\n" + doc_context[-half:]
        else:
            body_budget = max(400, max_chars - len(header))
            if len(doc_context) > body_budget:
                doc_context = doc_context[:body_budget]
        if not doc_sketch_used:
            doc_context = header + doc_context

        # Cache enrichment per document+chunk to avoid repeated LLM calls when ingest_chunks is called with
        # already-enriched metadata (e.g. ContextCache hit).
        contextualizer = ChunkContextualizer(self._metrics_tenant_id, user_id=self.user_id)
        default_conc = int(getattr(settings, "CONTEXTUAL_RETRIEVAL_MAX_CONCURRENCY_PER_DOCUMENT", 6))
        if (self._static_chunk_metadata or {}).get("source") == "ncert":
            default_conc = min(
                default_conc,
                max(1, int(getattr(settings, "CONTEXTUAL_RETRIEVAL_NCERT_MAX_CONCURRENCY", 3))),
            )
        sem = asyncio.Semaphore(max(1, default_conc))
        ctx_tag = (
            "ncert_global_chunk_contextualization"
            if self._contextual_llm_model
            else "chunk_contextualization"
        )

        def _chunk_key(raw: str) -> str:
            return hashlib.sha256(raw.encode("utf-8", errors="ignore")).hexdigest()

        async def _enrich_one(n: Any) -> Tuple[Any, Optional[ChunkEnrichment]]:
            md = getattr(n, "metadata", None) or {}
            if isinstance(md, dict) and int(md.get("contextual_version") or 0) >= 1:
                return n, None
            raw_text = getattr(n, "metadata", {}).get("text") if isinstance(md, dict) else None
            if not raw_text:
                raw_text = getattr(n, "text", "") or ""
            raw_text = str(raw_text or "").strip()
            if not raw_text:
                return n, None

            async with sem:
                enr = await contextualizer.enrich_chunk(
                    whole_document=doc_context,
                    chunk_content=raw_text,
                    feature_tag=ctx_tag,
                    llm_model=self._contextual_llm_model,
                    request_id=self._ingestion_run_id,
                    usage_accumulator=self._usage_accumulator,
                )
                return n, enr

        t0 = time.perf_counter()
        tasks = [asyncio.create_task(_enrich_one(n)) for n in nodes]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        enriched_nodes: List[Any] = []
        ok = 0
        fail = 0
        skipped_prec = 0
        empty_summary = 0
        for item in results:
            if isinstance(item, Exception):
                fail += 1
                continue
            n, enr = item
            if enr is None:
                md0 = getattr(n, "metadata", {}) or {}
                if isinstance(md0, dict) and int(md0.get("contextual_version") or 0) >= 1:
                    skipped_prec += 1
                enriched_nodes.append(n)
                continue
            try:
                md = dict(getattr(n, "metadata", {}) or {})
                raw_text = str(md.get("text") or getattr(n, "text", "") or "").strip()
                # Keep raw for citations
                md["text"] = raw_text
                md.update(enr.to_metadata())
                md["contextual_version"] = 1
                # Prefer section-level label as topic when contextualization succeeds.
                if str(enr.section_title or "").strip():
                    md["topic"] = str(enr.section_title).strip()
                if not str(enr.chunk_summary or "").strip():
                    empty_summary += 1
                # Embed text: contextual fields + raw chunk.
                embed_text = (
                    (enr.chunk_context or "")
                    + "\n"
                    + (enr.chunk_summary or "")
                    + "\n"
                    + (enr.concept_hint or "")
                    + "\n\n"
                    + raw_text
                ).strip()
                n.text = embed_text
                n.metadata = md
                enriched_nodes.append(n)
                ok += 1
            except Exception:
                # Safe fallback: keep the original node as-is.
                enriched_nodes.append(n)
                fail += 1

        dt_ms = (time.perf_counter() - t0) * 1000
        try:
            get_pipeline_trace_store().add_span(
                "Ingestion/ContextualizeChunks",
                dt_ms,
                input_summary={"chunks_in": len(nodes)},
                output_summary={
                    "chunks_enriched": ok,
                    "chunks_failed": fail,
                    "chunks_skipped_already_contextualized": skipped_prec,
                    "chunks_empty_summary_after_enrich": empty_summary,
                },
                status="ok",
                feature_tag="chunk_contextualization",
            )
        except Exception:
            pass

        if len(nodes) > 0 and ok == 0 and skipped_prec == 0:
            print(
                f"[INGEST] Contextual retrieval: 0/{len(nodes)} chunks enriched "
                f"(fail={fail}, tag={ctx_tag}). "
                "Verify OPENAI_API_KEY and NCERT_GLOBAL_CONTEXT_MODEL / chunk_contextualization model."
            )

        return enriched_nodes

    def _build_nodes_from_chunks(
        self,
        *,
        source_id: str,
        chunks_with_metadata: List[Tuple[str, Dict[str, Any]]],
    ) -> List["TextNode"]:
        """
        Build TextNodes from pre-chunked content (e.g. cache hit) while preserving
        vector id + metadata shape.
        """
        from llama_index.core.schema import TextNode

        nodes: List[TextNode] = []
        for i, (chunk_text, chunk_metadata) in enumerate(chunks_with_metadata):
            chunk_index = int(chunk_metadata.get("chunk_index", i))
            node_id = f"{source_id}_chunk_{chunk_index}"

            metadata: Dict[str, Any] = {
                "source_id": source_id,
                "tenant_id": self._namespace,
                "text": chunk_text,
                "chunk_index": chunk_index,
            }

            # Pass-through contextual retrieval metadata from cache if present.
            for k in (
                "chunk_context",
                "chunk_summary",
                "chunk_type",
                "section_title",
                "concept_hint",
                "contextual_version",
                "topic",
            ):
                if k in chunk_metadata and chunk_metadata.get(k) is not None:
                    metadata[k] = chunk_metadata.get(k)

            if "page_start" in chunk_metadata:
                metadata["page_start"] = chunk_metadata["page_start"]
                metadata["page_number"] = chunk_metadata["page_start"]
            if "page_end" in chunk_metadata:
                metadata["page_end"] = chunk_metadata["page_end"]

            # If contextual metadata is present, embed concatenation but keep raw chunk in metadata.text.
            if int(metadata.get("contextual_version") or 0) >= 1 and (
                metadata.get("chunk_context") or metadata.get("chunk_summary") or metadata.get("concept_hint")
            ):
                embed_text = (
                    str(metadata.get("chunk_context") or "")
                    + "\n"
                    + str(metadata.get("chunk_summary") or "")
                    + "\n"
                    + str(metadata.get("concept_hint") or "")
                    + "\n\n"
                    + str(chunk_text or "")
                ).strip()
                nodes.append(TextNode(text=embed_text, id_=node_id, metadata=metadata))
            else:
                nodes.append(TextNode(text=chunk_text, id_=node_id, metadata=metadata))

        # Keep deterministic ordering by chunk_index
        nodes.sort(key=lambda n: int(getattr(n, "metadata", {}).get("chunk_index", 0)))
        return nodes

    @staticmethod
    def _nodes_to_cache_tuples(nodes: List[Any]) -> List[Tuple[str, Dict[str, Any]]]:
        """Serialize enriched nodes for ContextCache (strip tenant/source-specific ids)."""
        cache_keys = (
            "chunk_index",
            "page_start",
            "page_end",
            "page_number",
            "chunk_context",
            "chunk_summary",
            "chunk_type",
            "section_title",
            "concept_hint",
            "contextual_version",
            "topic",
        )
        out: List[Tuple[str, Dict[str, Any]]] = []
        for n in nodes:
            md = dict(getattr(n, "metadata", {}) or {})
            chunk_text = str(md.get("text") or getattr(n, "text", "") or "").strip()
            if not chunk_text:
                continue
            chunk_meta: Dict[str, Any] = {
                "chunk_index": int(md.get("chunk_index", len(out))),
            }
            for k in cache_keys:
                if k == "chunk_index":
                    continue
                if k in md and md[k] is not None:
                    chunk_meta[k] = md[k]
            out.append((chunk_text, chunk_meta))
        out.sort(key=lambda pair: int(pair[1].get("chunk_index", 0)))
        return out

    async def ingest_text(
        self,
        *,
        text: str,
        source_id: str,
        pages: Optional[List[Tuple[int, str]]] = None,
    ) -> LlamaIndexIngestionResult:
        self._require_llamaindex()

        from llama_index.core import Settings as LISettings
        from llama_index.core import StorageContext, VectorStoreIndex
        from llama_index.embeddings.openai import OpenAIEmbedding
        from llama_index.vector_stores.pinecone import PineconeVectorStore
        from llama_index.core.vector_stores.utils import node_to_metadata_dict

        if not text or not text.strip():
            raise ValueError("Cannot ingest empty text")

        pinecone_index = get_pinecone_index()

        class ScholarSyncPineconeVectorStore(PineconeVectorStore):
            """
            LlamaIndex default metadata serialization injects doc_id/document_id/ref_doc_id with 'None'.
            ScholarSync uses `metadata.source_id` as the document identifier, so we strip these keys
            to keep Pinecone metadata clean and avoid confusing UI/debug output.
            """

            def add(self, nodes: List[Any], **add_kwargs: Any) -> List[str]:  # type: ignore[override]
                ids = []
                entries = []
                sparse_inputs = []
                for node in nodes:
                    node_id = node.node_id
                    metadata = node_to_metadata_dict(
                        node,
                        remove_text=self.remove_text_from_metadata,
                        flat_metadata=self.flat_metadata,
                    )
                    # Remove LlamaIndex ref-doc compatibility keys.
                    for k in ("document_id", "doc_id", "ref_doc_id"):
                        metadata.pop(k, None)
                    if self.add_sparse_vector and getattr(self, "_sparse_embedding_model", None) is not None:
                        from llama_index.core.schema import MetadataMode

                        sparse_inputs.append(node.get_content(metadata_mode=MetadataMode.EMBED))
                    if node.ref_doc_id is not None:
                        node_id = f"{node.ref_doc_id}#{node_id}"
                    ids.append(node_id)
                    entry = {
                        "id": node_id,
                        "values": node.get_embedding(),
                        "metadata": metadata,
                    }
                    entries.append(entry)

                if sparse_inputs and getattr(self, "_sparse_embedding_model", None) is not None:
                    sparse_vectors = self._sparse_embedding_model.get_text_embedding_batch(sparse_inputs)
                    for i, sparse_vector in enumerate(sparse_vectors):
                        entries[i]["sparse_values"] = {
                            "indices": list(sparse_vector.keys()),
                            "values": list(sparse_vector.values()),
                        }
                self._pinecone_index.upsert(
                    entries,
                    namespace=self.namespace,
                    batch_size=self.batch_size,
                    **self.insert_kwargs,
                )
                return ids

        vector_store = ScholarSyncPineconeVectorStore(
            pinecone_index=pinecone_index,
            namespace=self._namespace,
        )

        _em = self._embedding_model or settings.OPENAI_EMBEDDING_MODEL
        _ed = (
            self._embedding_dimensions
            if self._embedding_dimensions is not None
            else settings.OPENAI_EMBEDDING_DIMENSIONS
        )
        sync_http_client, async_http_client = build_openai_http_clients()
        embed_kwargs: Dict[str, Any] = {
            "model": _em,
            "dimensions": _ed,
        }
        if settings.OPENAI_API_KEY:
            embed_kwargs["api_key"] = settings.OPENAI_API_KEY
        if sync_http_client is not None:
            embed_kwargs["http_client"] = sync_http_client
        if async_http_client is not None:
            embed_kwargs["async_http_client"] = async_http_client
        LISettings.embed_model = OpenAIEmbedding(**embed_kwargs)

        storage_context = StorageContext.from_defaults(vector_store=vector_store)
        nodes = self._build_nodes(text=text, source_id=source_id, pages=pages)
        # Contextual Retrieval enrichment (OpenAI) — safe fallback on failure.
        try:
            nodes = await self._enrich_nodes_contextual(nodes=nodes, whole_document_text=text)
        except Exception as ex:
            print(f"[INGEST] Contextual enrichment skipped due to error: {ex}")

        t0 = time.perf_counter()
        await asyncio.to_thread(_sync_build_vector_index, nodes, storage_context)
        elapsed_ms = (time.perf_counter() - t0) * 1000
        if self.user_id:
            await _record_llamaindex_ingest_embeddings(
                tenant_id=self._metrics_tenant_id,
                user_id=self.user_id,
                nodes=nodes,
                latency_ms=elapsed_ms,
                embedding_model=self._embedding_model,
                usage_accumulator=self._usage_accumulator,
                feature_tag="ncert_global_embedding" if self._embedding_model else "embedding",
                request_id=self._ingestion_run_id,
            )

        chunks_for_cache = self._nodes_to_cache_tuples(nodes)
        return LlamaIndexIngestionResult(
            nodes_indexed=len(nodes),
            chunks_for_cache=chunks_for_cache,
        )

    async def ingest_chunks(
        self,
        *,
        source_id: str,
        chunks_with_metadata: List[Tuple[str, Dict[str, Any]]],
    ) -> LlamaIndexIngestionResult:
        """
        Ingest already-chunked text into Pinecone using LlamaIndex embedding + write.
        Used when the pipeline hits ContextCache and we want to avoid re-splitting.
        """
        self._require_llamaindex()

        from llama_index.core import Settings as LISettings
        from llama_index.core import StorageContext, VectorStoreIndex
        from llama_index.embeddings.openai import OpenAIEmbedding
        from llama_index.vector_stores.pinecone import PineconeVectorStore
        from llama_index.core.vector_stores.utils import node_to_metadata_dict

        if not chunks_with_metadata:
            raise ValueError("Cannot ingest empty chunks")

        pinecone_index = get_pinecone_index()

        class ScholarSyncPineconeVectorStore(PineconeVectorStore):
            def add(self, nodes: List[Any], **add_kwargs: Any) -> List[str]:  # type: ignore[override]
                ids = []
                entries = []
                sparse_inputs = []
                for node in nodes:
                    node_id = node.node_id
                    metadata = node_to_metadata_dict(
                        node,
                        remove_text=self.remove_text_from_metadata,
                        flat_metadata=self.flat_metadata,
                    )
                    for k in ("document_id", "doc_id", "ref_doc_id"):
                        metadata.pop(k, None)
                    if self.add_sparse_vector and getattr(self, "_sparse_embedding_model", None) is not None:
                        from llama_index.core.schema import MetadataMode

                        sparse_inputs.append(node.get_content(metadata_mode=MetadataMode.EMBED))
                    if node.ref_doc_id is not None:
                        node_id = f"{node.ref_doc_id}#{node_id}"
                    ids.append(node_id)
                    entries.append(
                        {
                            "id": node_id,
                            "values": node.get_embedding(),
                            "metadata": metadata,
                        }
                    )
                if sparse_inputs and getattr(self, "_sparse_embedding_model", None) is not None:
                    sparse_vectors = self._sparse_embedding_model.get_text_embedding_batch(sparse_inputs)
                    for i, sparse_vector in enumerate(sparse_vectors):
                        entries[i]["sparse_values"] = {
                            "indices": list(sparse_vector.keys()),
                            "values": list(sparse_vector.values()),
                        }
                self._pinecone_index.upsert(
                    entries,
                    namespace=self.namespace,
                    batch_size=self.batch_size,
                    **self.insert_kwargs,
                )
                return ids

        vector_store = ScholarSyncPineconeVectorStore(
            pinecone_index=pinecone_index,
            namespace=self._namespace,
        )

        _em = self._embedding_model or settings.OPENAI_EMBEDDING_MODEL
        _ed = (
            self._embedding_dimensions
            if self._embedding_dimensions is not None
            else settings.OPENAI_EMBEDDING_DIMENSIONS
        )
        sync_http_client, async_http_client = build_openai_http_clients()
        embed_kwargs: Dict[str, Any] = {
            "model": _em,
            "dimensions": _ed,
        }
        if settings.OPENAI_API_KEY:
            embed_kwargs["api_key"] = settings.OPENAI_API_KEY
        if sync_http_client is not None:
            embed_kwargs["http_client"] = sync_http_client
        if async_http_client is not None:
            embed_kwargs["async_http_client"] = async_http_client
        LISettings.embed_model = OpenAIEmbedding(**embed_kwargs)
        storage_context = StorageContext.from_defaults(vector_store=vector_store)
        nodes = self._build_nodes_from_chunks(
            source_id=source_id, chunks_with_metadata=chunks_with_metadata
        )
        # If cached chunks did not include contextual metadata, enrich here.
        # Use concatenated raw chunk text as best-effort doc context.
        try:
            has_ctx = any(
                int((getattr(n, "metadata", {}) or {}).get("contextual_version") or 0) >= 1
                for n in nodes
            )
            if not has_ctx:
                doc_text = "\n\n".join([str((getattr(n, "metadata", {}) or {}).get("text") or "") for n in nodes])[:24000]
                nodes = await self._enrich_nodes_contextual(nodes=nodes, whole_document_text=doc_text)
        except Exception as ex:
            print(f"[INGEST] Contextual enrichment (cached chunks) error: {ex}")

        t0 = time.perf_counter()
        await asyncio.to_thread(_sync_build_vector_index, nodes, storage_context)
        elapsed_ms = (time.perf_counter() - t0) * 1000
        if self.user_id:
            await _record_llamaindex_ingest_embeddings(
                tenant_id=self._metrics_tenant_id,
                user_id=self.user_id,
                nodes=nodes,
                latency_ms=elapsed_ms,
                embedding_model=self._embedding_model,
                usage_accumulator=self._usage_accumulator,
                feature_tag="ncert_global_embedding" if self._embedding_model else "embedding",
                request_id=self._ingestion_run_id,
            )

        return LlamaIndexIngestionResult(nodes_indexed=len(nodes))
