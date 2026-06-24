"""Hybrid PDF/image text extraction for Problem Solver uploads."""

from __future__ import annotations

import io
from typing import Optional

import fitz
import pypdf

from packages.core.processing.image_ocr import (
    describe_diagram_image_bytes,
    extract_pdf_diagram_context,
    is_image_upload,
    ocr_image_bytes,
    ocr_problem_page_bytes,
    ocr_scanned_pdf,
    resolve_image_mime,
)
from packages.core.processing.problem_solver_extraction import (
    detect_corruption,
    filter_diagram_description,
    finalize_problem_text,
    needs_vision_retry,
    reconcile_text_layers,
    should_attach_diagram,
    split_diagram_blocks,
)


def _extract_fitz_page_images(page: fitz.Page, limit: int = 5) -> list[bytes]:
    images: list[tuple[int, bytes]] = []
    for img in page.get_images(full=True):
        xref = img[0]
        try:
            base = page.parent.extract_image(xref)
            width = int(base.get("width") or 0)
            height = int(base.get("height") or 0)
            if width * height < 4000:
                continue
            images.append((width * height, base["image"]))
        except Exception:
            continue
    images.sort(key=lambda item: item[0], reverse=True)
    return [blob for _, blob in images[:limit]]


async def _hybrid_fitz_page(
    page: fitz.Page,
    *,
    tenant_id: Optional[str],
    user_id: Optional[str],
) -> tuple[str, str]:
    raw = (page.get_text("text") or "").strip()
    has_image = len(page.get_images()) > 0
    if not needs_vision_retry(raw, has_image):
        return raw, ""

    vision_text = ""
    png_bytes = b""
    if has_image or detect_corruption(raw):
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
        png_bytes = pix.tobytes("png")
        try:
            vision_text = await ocr_problem_page_bytes(
                png_bytes,
                mime_type="image/png",
                tenant_id=tenant_id,
                user_id=user_id,
            )
        except Exception:
            vision_text = ""

    reconciled = reconcile_text_layers(raw, vision_text)
    diagram_desc = ""
    if has_image:
        parts: list[str] = []
        seen: set[str] = set()

        def _add_desc(raw_desc: str) -> None:
            for block in split_diagram_blocks(raw_desc):
                key = block[:100].lower()
                if key not in seen:
                    seen.add(key)
                    parts.append(block)

        for img_bytes in _extract_fitz_page_images(page):
            try:
                desc = await describe_diagram_image_bytes(
                    img_bytes,
                    tenant_id=tenant_id,
                    user_id=user_id,
                )
                if desc.strip():
                    _add_desc(desc.strip())
            except Exception:
                continue
        if png_bytes:
            try:
                desc = await describe_diagram_image_bytes(
                    png_bytes,
                    mime_type="image/png",
                    tenant_id=tenant_id,
                    user_id=user_id,
                )
                if desc.strip():
                    _add_desc(desc.strip())
            except Exception:
                pass
        diagram_desc = (
            "; ".join(f"[Diagram: {part}]" for part in parts) if parts else ""
        )
    return reconciled, diagram_desc


async def _pdf_hybrid_text(
    file_content: bytes,
    *,
    tenant_id: Optional[str],
    user_id: Optional[str],
) -> str:
    doc = fitz.open(stream=file_content, filetype="pdf")
    page_texts: list[str] = []
    try:
        for page in doc:
            page_has_images = len(page.get_images()) > 0
            text, diagram_desc = await _hybrid_fitz_page(
                page, tenant_id=tenant_id, user_id=user_id
            )
            if text.strip():
                block = text.strip()
                if diagram_desc and should_attach_diagram(block, diagram_desc, page_has_images=page_has_images):
                    block = finalize_problem_text(
                        block, diagram_desc, page_has_images=page_has_images
                    )
                page_texts.append(block)
    finally:
        doc.close()

    combined = "\n\n".join(page_texts).strip()
    if len(combined) < 20:
        combined, _ = await ocr_scanned_pdf(
            file_content, None, tenant_id=tenant_id, user_id=user_id
        )
    if not combined.strip():
        try:
            diagram_context = await extract_pdf_diagram_context(
                file_content, tenant_id=tenant_id, user_id=user_id
            )
            if diagram_context:
                combined = diagram_context
        except Exception:
            pass
    return combined.strip()


async def extract_problem_text_from_bytes(
    file_content: bytes,
    *,
    s3_key: str = "",
    title: str = "",
    tenant_id: Optional[str] = None,
    user_id: Optional[str] = None,
    indexed_chunks: str = "",
) -> str:
    """Extract problem text from uploaded source bytes (hybrid vision when needed)."""
    key_lower = (s3_key or "").lower()
    title_lower = (title or "").lower()
    chunks = (indexed_chunks or "").strip()

    if chunks and len(chunks) >= 20 and not detect_corruption(chunks):
        return chunks

    if not file_content:
        return chunks

    if key_lower.endswith(".pdf") or file_content[:4] == b"%PDF":
        text = await _pdf_hybrid_text(
            file_content, tenant_id=tenant_id, user_id=user_id
        )
        if text:
            return text
        reader = pypdf.PdfReader(io.BytesIO(file_content))
        return "\n".join((p.extract_text() or "") for p in reader.pages).strip()

    if is_image_upload(title_lower, "") or is_image_upload(key_lower, ""):
        mime = resolve_image_mime(title_lower or key_lower, "")
        return await ocr_image_bytes(
            file_content,
            mime_type=mime,
            tenant_id=tenant_id,
            user_id=user_id,
        )

    if key_lower.endswith(".txt"):
        return file_content.decode("utf-8", errors="replace").strip()

    return chunks
