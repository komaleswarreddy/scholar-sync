"""Vision OCR for uploaded images and scanned PDFs."""

from __future__ import annotations

import asyncio
import base64
import functools
import io
import os
from typing import List, Optional, Tuple

import pypdf

from packages.core.llm import get_llm_client, get_model_for_task

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
IMAGE_MIME_BY_EXT = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".gif": "image/gif",
}

_OCR_PROMPT = (
    "Extract all readable text from this document image exactly as written. "
    "Preserve math notation, question numbers, and line breaks. "
    "Return only the extracted text with no commentary."
)
_DIAGRAM_PROMPT = (
    "You are reading a textbook diagram or circuit figure. "
    "Extract short English-only labels, variable names, and directional flow hints. "
    "Ignore Hindi/non-English text. Return plain text only."
)
_DIAGRAM_NOISE_MARKERS = (
    "no image",
    "unable to extract",
    "can't extract",
    "cannot extract",
    "please upload",
    "no diagram",
    "no text found",
)

PROBLEM_PAGE_OCR_PROMPT = (
    "You are transcribing an Indian exam problem page (JEE/NEET/CBSE) from a PDF screenshot. "
    "Extract ALL question text exactly as written. Preserve:\n"
    "- Question numbers (Q29, Q.29, etc.)\n"
    "- Block/object labels (P, Q, S, A, B, etc.) in parentheses\n"
    "- All numeric values with units (2 kg, 1.5 kg, g/2, μ, 10 m/s²)\n"
    "- MCQ option labels AND values: (1) 0.33 (2) 0.67 etc.\n"
    "- Math symbols (μ, Σ, √, fractions, subscripts)\n"
    "Return plain text only — no commentary, no markdown fences."
)

PROBLEM_DIAGRAM_DESCRIBE_PROMPT = (
    "Describe this exam figure/diagram in full detail for a physics/chemistry/biology student.\n"
    "Include EVERY visible element:\n"
    "- All named labels (points A, B, C, beads P/Q, blocks, components)\n"
    "- All numeric annotations (masses, distances, angles, dimensions, units)\n"
    "- All connections (strings, threads, wires, rays, forces, pulleys)\n"
    "- Spatial layout (top/bottom/left/right, horizontal vs vertical, arcs, curves)\n"
    "- All arrows and motion directions\n"
    "- Graph axes, scales, and curve shapes when present\n"
    "CRITICAL rules:\n"
    "- Describe ONLY what is visibly drawn — do not invent values.\n"
    "- Do NOT confuse MCQ option numbers (1.65, 2.0) with diagram masses or distances.\n"
    "- Do NOT describe question text — describe the figure only.\n"
    "If the image contains ONLY text with no figure/graph/circuit/geometry, respond exactly: NO_DIAGRAM\n"
    "Otherwise return one detailed paragraph for a [Diagram: ...] block. No preamble."
)


def is_image_upload(filename: str, content_type: str) -> bool:
    ext = os.path.splitext(filename or "")[1].lower()
    mime = (content_type or "").lower().strip()
    if ext in IMAGE_EXTENSIONS:
        return True
    return mime.startswith("image/")


def resolve_image_mime(filename: str, content_type: str) -> str:
    mime = (content_type or "").lower().strip()
    if mime.startswith("image/"):
        return mime
    ext = os.path.splitext(filename or "")[1].lower()
    return IMAGE_MIME_BY_EXT.get(ext, "image/jpeg")


def image_extension(filename: str, content_type: str) -> str:
    ext = os.path.splitext(filename or "")[1].lower()
    if ext in IMAGE_EXTENSIONS:
        return ext
    mime = resolve_image_mime(filename, content_type)
    for key, value in IMAGE_MIME_BY_EXT.items():
        if value == mime:
            return key
    return ".jpg"


async def _vision_image_call(
    image_bytes: bytes,
    *,
    mime_type: str,
    prompt: str,
    max_tokens: int = 4096,
    tenant_id: Optional[str] = None,
    user_id: Optional[str] = None,
) -> str:
    if not image_bytes:
        return ""
    provider, model = get_model_for_task("source_image_ocr")
    llm = get_llm_client(provider=provider, model=model, temperature=0)
    client = llm.client
    b64 = base64.standard_b64encode(image_bytes).decode("ascii")
    data_url = f"data:{mime_type};base64,{b64}"
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": data_url}},
            ],
        }
    ]
    call_api = functools.partial(
        client.chat.completions.create,
        model=model,
        messages=messages,
        temperature=0,
        max_tokens=max_tokens,
    )
    response = await asyncio.to_thread(call_api)
    return (response.choices[0].message.content or "").strip()


async def ocr_problem_page_bytes(
    image_bytes: bytes,
    *,
    mime_type: str = "image/png",
    tenant_id: Optional[str] = None,
    user_id: Optional[str] = None,
) -> str:
    """Full-page vision OCR for exam problems (symbols, labels, MCQ values)."""
    text = await _vision_image_call(
        image_bytes,
        mime_type=mime_type,
        prompt=PROBLEM_PAGE_OCR_PROMPT,
        max_tokens=4096,
        tenant_id=tenant_id,
        user_id=user_id,
    )
    if len(text) < 5:
        raise ValueError("Could not read problem text from page image.")
    return text


async def describe_diagram_image_bytes(
    image_bytes: bytes,
    *,
    mime_type: str = "image/png",
    tenant_id: Optional[str] = None,
    user_id: Optional[str] = None,
) -> str:
    """Structured diagram layout description for problem-solver context."""
    if not image_bytes:
        return ""
    text = await _vision_image_call(
        image_bytes,
        mime_type=mime_type,
        prompt=PROBLEM_DIAGRAM_DESCRIBE_PROMPT,
        max_tokens=1024,
        tenant_id=tenant_id,
        user_id=user_id,
    )
    cleaned = (text or "").strip()
    if cleaned.upper() == "NO_DIAGRAM" or cleaned.lower() in {"no diagram", "no figure", "text only"}:
        return ""
    return cleaned


async def ocr_image_bytes(
    image_bytes: bytes,
    *,
    mime_type: str,
    tenant_id: Optional[str] = None,
    user_id: Optional[str] = None,
) -> str:
    if not image_bytes:
        raise ValueError("Image file is empty")

    provider, model = get_model_for_task("source_image_ocr")
    llm = get_llm_client(provider=provider, model=model, temperature=0)
    client = llm.client

    b64 = base64.standard_b64encode(image_bytes).decode("ascii")
    data_url = f"data:{mime_type};base64,{b64}"
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": _OCR_PROMPT},
                {"type": "image_url", "image_url": {"url": data_url}},
            ],
        }
    ]

    call_api = functools.partial(
        client.chat.completions.create,
        model=model,
        messages=messages,
        temperature=0,
        max_tokens=4096,
    )
    response = await asyncio.to_thread(call_api)
    text = (response.choices[0].message.content or "").strip()
    if len(text) < 5:
        raise ValueError("Could not read any text from the image. Try a clearer photo or a text-based PDF.")
    return text


async def ocr_diagram_image_bytes(
    image_bytes: bytes,
    *,
    mime_type: str,
    tenant_id: Optional[str] = None,
    user_id: Optional[str] = None,
) -> str:
    if not image_bytes:
        return ""
    provider, model = get_model_for_task("source_image_ocr")
    llm = get_llm_client(provider=provider, model=model, temperature=0)
    client = llm.client
    b64 = base64.standard_b64encode(image_bytes).decode("ascii")
    data_url = f"data:{mime_type};base64,{b64}"
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": _DIAGRAM_PROMPT},
                {"type": "image_url", "image_url": {"url": data_url}},
            ],
        }
    ]
    call_api = functools.partial(
        client.chat.completions.create,
        model=model,
        messages=messages,
        temperature=0,
        max_tokens=512,
    )
    response = await asyncio.to_thread(call_api)
    return (response.choices[0].message.content or "").strip()


def _extract_pdf_embedded_images(file_content: bytes, pdf_password: Optional[str] = None) -> List[bytes]:
    reader = pypdf.PdfReader(io.BytesIO(file_content))
    if reader.is_encrypted:
        password = pdf_password or ""
        if not reader.decrypt(password):
            raise ValueError("Incorrect password for PDF. Please provide the correct password.")

    images: List[bytes] = []
    for page in reader.pages:
        try:
            for image in page.images:
                data = getattr(image, "data", None)
                if data:
                    images.append(data)
        except Exception:
            continue
    return images


async def ocr_scanned_pdf(
    file_content: bytes,
    pdf_password: Optional[str] = None,
    *,
    tenant_id: Optional[str] = None,
    user_id: Optional[str] = None,
) -> Tuple[str, List[Tuple[int, str]]]:
    """OCR a scanned/image-only PDF via embedded page images."""
    embedded = _extract_pdf_embedded_images(file_content, pdf_password)
    if not embedded:
        raise ValueError(
            "This PDF has no extractable text and could not be read as images. "
            "Upload a photo of the page (PNG/JPG) or a text-based PDF instead."
        )

    page_texts: List[str] = []
    pages: List[Tuple[int, str]] = []
    for idx, image_bytes in enumerate(embedded, start=1):
        page_text = await ocr_image_bytes(
            image_bytes,
            mime_type="image/png",
            tenant_id=tenant_id,
            user_id=user_id,
        )
        if page_text.strip():
            pages.append((idx, page_text))
            page_texts.append(page_text)

    combined = "\n\n".join(page_texts).strip()
    if len(combined) < 5:
        raise ValueError("Could not read any text from the scanned PDF.")
    return combined, pages


async def extract_pdf_diagram_context(
    file_content: bytes,
    pdf_password: Optional[str] = None,
    *,
    tenant_id: Optional[str] = None,
    user_id: Optional[str] = None,
) -> str:
    """Best-effort OCR pass for embedded diagram/circuit images in PDFs."""
    def _useful(snippet: str) -> bool:
        text = " ".join((snippet or "").split()).strip()
        if len(text) < 12:
            return False
        lowered = text.lower()
        if any(marker in lowered for marker in _DIAGRAM_NOISE_MARKERS):
            return False
        alnum = sum(ch.isalnum() for ch in text)
        return alnum >= 8

    snippets: List[str] = []
    for image_bytes in _extract_pdf_embedded_images(file_content, pdf_password)[:4]:
        try:
            text = await ocr_diagram_image_bytes(
                image_bytes,
                mime_type="image/png",
                tenant_id=tenant_id,
                user_id=user_id,
            )
        except Exception:
            continue
        clean = " ".join((text or "").split())
        if _useful(clean):
            snippets.append(clean)
    if not snippets:
        return ""
    return "Diagram context: " + " | ".join(snippets)
