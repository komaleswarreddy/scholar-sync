#!/usr/bin/env python3
"""Extract all problem-solver questions from Problem solver_Questions PDFs."""

from __future__ import annotations

import argparse
import asyncio
import io
import json
import re
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import fitz
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env")

from packages.core.processing.image_ocr import (  # noqa: E402
    describe_diagram_image_bytes,
    ocr_problem_page_bytes,
)
from packages.core.processing.problem_solver_extraction import (  # noqa: E402
    detect_corruption,
    extract_mcq_options,
    filter_diagram_description,
    finalize_problem_text,
    needs_vision_retry,
    pick_diagram_for_question,
    problem_likely_needs_diagram,
    question_references_diagram,
    reconcile_text_layers,
    should_attach_diagram,
    split_diagram_blocks,
)

PDF_ROOT = ROOT / "Problem solver_Questions"
OUT = SCRIPTS / "problem_solver_question_bank.json"
VISION_CACHE_PATH = SCRIPTS / "problem_solver_vision_extract_cache.json"

OCR_MIN_TEXT = 120
OCR: Any = None

PDF_META: dict[str, dict[str, str]] = {
    "Biology_Testing_Question_Bank_Updated.pdf": {
        "exam_type": "cbse", "subject": "biology", "class_num": "12", "source_key": "cbse_biology",
    },
    "Mathematics_Testing_Question_Bank.pdf": {
        "exam_type": "cbse", "subject": "mathematics", "class_num": "12", "source_key": "cbse_mathematics",
    },
    "Physics_testing_Question_Bank.pdf": {
        "exam_type": "cbse", "subject": "physics", "class_num": "12", "source_key": "cbse_physics",
    },
    "Mains 2026 April.pdf": {
        "exam_type": "jee", "subject": "mixed", "class_num": "12", "source_key": "jee_april_2026",
    },
    "Mains 2026 Jan.pdf": {
        "exam_type": "jee", "subject": "mixed", "class_num": "12", "source_key": "jee_jan_2026",
    },
    "Botany.pdf": {
        "exam_type": "neet", "subject": "biology", "class_num": "12", "source_key": "neet_botany",
    },
    "Chemistry.pdf": {
        "exam_type": "neet", "subject": "chemistry", "class_num": "12", "source_key": "neet_chemistry",
    },
    "Physics.pdf": {
        "exam_type": "neet", "subject": "physics", "class_num": "12", "source_key": "neet_physics",
    },
    "Zoology.pdf": {
        "exam_type": "neet", "subject": "biology", "class_num": "12", "source_key": "neet_zoology",
    },
}

Q_START = re.compile(
    r"(?:^|\n)(?:"
    r"Q\.?\s*(\d{1,3})(?:[\.\):]|\s)"
    r"|(?:Question|Problem)\s+(\d{1,3})[\.\):]"
    r"|(\d{2,3})[\.\):]\s+"
    r")",
    re.MULTILINE | re.IGNORECASE,
)
HEADER_NOISE = re.compile(
    r"(?i)(golden set|question.?only|instructions:|page \d+|section [a-z]:|"
    r"mathematics board testing|physics board|biology board|assertion-reasoning questions.*)",
    re.S,
)


@dataclass
class QuestionRecord:
    id: str
    source_pdf: str
    source_key: str
    page: int
    exam_type: str
    subject: str
    class_num: str
    format: str
    problem_text_normalized: str
    has_image: bool
    extraction_method: str
    raw_text: str = ""
    tags: list[str] = field(default_factory=list)
    diagram_description: str = ""
    corruption_flags: list[str] = field(default_factory=list)


def _get_ocr() -> Any:
    global OCR
    if OCR is None:
        from rapidocr_onnxruntime import RapidOCR
        OCR = RapidOCR()
    return OCR


def ocr_page(page: fitz.Page) -> str:
    pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
    img = Image.open(io.BytesIO(pix.tobytes("png")))
    result, _ = _get_ocr()(img)
    if not result:
        return ""
    return "\n".join(line[1] for line in result)


def page_text_basic(page: fitz.Page) -> tuple[str, str]:
    raw = page.get_text("text").strip()
    has_image = len(page.get_images()) > 0
    method = "text"
    if has_image and len(raw) < OCR_MIN_TEXT:
        ocr_text = ocr_page(page)
        if len(ocr_text) > len(raw):
            return ocr_text.strip(), "ocr"
    return raw, method


def _extract_page_images(page: fitz.Page, limit: int = 5) -> list[bytes]:
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


def _load_vision_cache() -> dict[str, Any]:
    if VISION_CACHE_PATH.exists():
        return json.loads(VISION_CACHE_PATH.read_text(encoding="utf-8"))
    return {"version": "1.0.0", "pages": {}}


def _save_vision_cache(cache: dict[str, Any]) -> None:
    VISION_CACHE_PATH.write_text(json.dumps(cache, indent=2, ensure_ascii=False), encoding="utf-8")


async def hybrid_page_extract(
    page: fitz.Page,
    cache_key: str,
    cache: dict[str, Any],
    *,
    force: bool = False,
) -> tuple[str, str, str, list[str]]:
    raw = page.get_text("text").strip()
    has_image = len(page.get_images()) > 0
    pages_cache = cache.setdefault("pages", {})

    if not needs_vision_retry(raw, has_image):
        return raw, "", "text", detect_corruption(raw)

    if cache_key in pages_cache and not force:
        entry = pages_cache[cache_key]
        return (
            entry.get("text", raw),
            entry.get("diagram_desc", ""),
            entry.get("method", "hybrid_vision"),
            entry.get("flags", []),
        )

    vision_text = ""
    png_bytes = b""
    if needs_vision_retry(raw, has_image):
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
        png_bytes = pix.tobytes("png")
        try:
            vision_text = await ocr_problem_page_bytes(png_bytes, mime_type="image/png")
        except Exception as exc:
            print(f"    vision OCR failed for {cache_key}: {exc}", flush=True)

    reconciled = reconcile_text_layers(raw, vision_text)
    flags = detect_corruption(reconciled)

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

        for img_bytes in _extract_page_images(page):
            try:
                desc = await describe_diagram_image_bytes(img_bytes)
                if desc.strip():
                    _add_desc(desc.strip())
            except Exception:
                continue
        if png_bytes:
            try:
                desc = await describe_diagram_image_bytes(png_bytes, mime_type="image/png")
                if desc.strip():
                    _add_desc(desc.strip())
            except Exception:
                pass
        diagram_desc = (
            "; ".join(f"[Diagram: {part}]" for part in parts) if parts else ""
        )

    pages_cache[cache_key] = {
        "text": reconciled,
        "diagram_desc": diagram_desc,
        "method": "hybrid_vision",
        "flags": flags,
    }
    _save_vision_cache(cache)
    return reconciled, diagram_desc, "hybrid_vision", flags


def normalize_problem(text: str) -> str:
    text = HEADER_NOISE.sub(" ", text)
    stem, options = extract_mcq_options(text.strip())
    stem = re.sub(r"\s+", " ", stem).strip()
    if options:
        options_clean = options.strip()
        if "\n" in options_clean:
            return f"{stem}\n{options_clean}".strip()
        return f"{stem} {options_clean}".strip()
    return re.sub(r"\s+", " ", text).strip()


def detect_format(text: str, exam_type: str) -> str:
    lower = text.lower()
    if "assertion" in lower and "reason" in lower:
        return "assertion_reason"
    if re.search(r"\([1-4]\)", text) and exam_type == "neet":
        return "mcq"
    if re.search(r"\([A-D]\)", text, re.I):
        return "mcq"
    if "[diagram:" in lower or "figure" in lower or "shown in" in lower or "diagram" in lower:
        return "diagram"
    if any(w in lower for w in ("derive", "derivation", "prove", "proof")):
        return "proof"
    if any(w in lower for w in ("case study", "passage", "read the following passage")):
        return "case_study"
    if re.search(r"\b(part\s*[a-z]|\(i\)|\(ii\)|\(a\)|\(b\))", lower):
        return "multi_part"
    if re.search(r"\b(find|calculate|compute|evaluate|determine|how much|magnitude)\b", lower):
        return "numerical"
    if exam_type == "jee":
        return "jee"
    if exam_type == "neet":
        return "neet"
    if exam_type == "cbse":
        return "cbse"
    return "conceptual"


def split_questions(page_text_val: str) -> list[tuple[str, str]]:
    if not page_text_val.strip():
        return []
    matches = list(Q_START.finditer(page_text_val))
    if not matches:
        chunk = normalize_problem(page_text_val)
        if len(chunk) < 40:
            return []
        m = re.match(r"(?:Q\.?\s*)?(\d{1,3})[\.\):]", chunk, re.I)
        qnum = m.group(1) if m else "0"
        return [(qnum, chunk)]
    out: list[tuple[str, str]] = []
    for idx, match in enumerate(matches):
        qnum = match.group(1) or match.group(2) or match.group(3)
        if not qnum:
            continue
        start = match.start()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(page_text_val)
        body = page_text_val[start:end].strip()
        chunk = normalize_problem(body)
        if len(chunk) < 35:
            continue
        out.append((qnum, f"Q{qnum}. {chunk}" if not chunk.lower().startswith("q") else chunk))
    return out


def infer_subject(text: str, default: str, exam_type: str) -> str:
    lower = text.lower()
    phys = ("velocity", "force", "lens", "circuit", "capacitor", "field", "m/s", "ohm", "optics", "wave")
    chem = ("mole", "reaction", "compound", "acid", "element", "oxidation", "molar", "organic", "ion")
    math = ("matrix", "integral", "derivative", "probability", "vector", "equation", "dx", "dy/dx")
    bio = ("cell", "enzyme", "dna", "plant", "animal", "mitosis", "photosynthesis", "organism")
    scores = {
        "physics": sum(1 for w in phys if w in lower),
        "chemistry": sum(1 for w in chem if w in lower),
        "mathematics": sum(1 for w in math if w in lower),
        "biology": sum(1 for w in bio if w in lower),
    }
    best = max(scores, key=scores.get)
    if scores[best] >= 2:
        return best
    if default != "mixed":
        return default
    return best if scores[best] > 0 else "physics"


async def extract_pdf(
    pdf_path: Path,
    *,
    vision_only: bool = False,
    vision_cache: dict[str, Any],
    force_vision: bool = False,
    target_ids: set[str] | None = None,
    target_pages: set[tuple[str, int]] | None = None,
) -> list[QuestionRecord]:
    meta = PDF_META.get(pdf_path.name, {})
    records: list[QuestionRecord] = []
    doc = fitz.open(pdf_path)
    source_key = meta.get("source_key", pdf_path.stem)

    for page_idx in range(len(doc)):
        page = doc[page_idx]
        has_image = len(page.get_images()) > 0
        page_num = page_idx + 1
        cache_key = f"{source_key}-p{page_num}"

        if target_pages is not None:
            if (source_key, page_num) not in target_pages:
                continue

        use_hybrid = has_image
        if use_hybrid:
            text, diagram_desc, method, flags = await hybrid_page_extract(
                page, cache_key, vision_cache, force=force_vision
            )
        else:
            text, method = page_text_basic(page)
            diagram_desc = ""
            flags = detect_corruption(text)

        for qnum, chunk in split_questions(text):
            rec_id = f"{source_key}-p{page_num}-q{qnum}"
            if target_ids is not None and rec_id not in target_ids and target_pages is None:
                continue

            problem_text = finalize_problem_text(
                chunk, diagram_desc, page_has_images=has_image
            )

            subj = infer_subject(problem_text, meta.get("subject", "physics"), meta.get("exam_type", "cbse"))
            fmt = detect_format(problem_text, meta.get("exam_type", "cbse"))
            question_has_diagram = "[diagram:" in problem_text.lower()
            if has_image and fmt not in ("diagram", "assertion_reason"):
                if question_has_diagram or problem_likely_needs_diagram(chunk):
                    fmt = "diagram" if "mcq" not in fmt else fmt

            tags = [
                meta.get("exam_type", "cbse"),
                subj,
                f"source_pdf_{source_key}",
                fmt,
            ]
            records.append(
                QuestionRecord(
                    id=rec_id,
                    source_pdf=pdf_path.name,
                    source_key=source_key,
                    page=page_num,
                    exam_type=meta.get("exam_type", "cbse"),
                    subject=subj,
                    class_num=meta.get("class_num", "12"),
                    format=fmt,
                    problem_text_normalized=problem_text,
                    has_image=question_has_diagram,
                    extraction_method=method,
                    raw_text=text[:500],
                    tags=tags,
                    diagram_description=pick_diagram_for_question(chunk, diagram_desc),
                    corruption_flags=flags,
                )
            )
    doc.close()
    return records


def dedupe_bank(records: list[QuestionRecord]) -> list[QuestionRecord]:
    seen: set[str] = set()
    out: list[QuestionRecord] = []
    for r in records:
        key = re.sub(r"\s+", " ", r.problem_text_normalized.lower())[:200]
        if key in seen:
            continue
        seen.add(key)
        out.append(r)
    return out


def _merge_vision_updates(
    existing: list[dict[str, Any]],
    updates: list[QuestionRecord],
) -> list[dict[str, Any]]:
    by_id = {r.id: asdict(r) for r in updates}
    refreshed_pages = {(r.source_key, r.page) for r in updates}
    merged: list[dict[str, Any]] = []
    for row in existing:
        page_key = (row["source_key"], row["page"])
        if page_key in refreshed_pages:
            continue
        if row["id"] in by_id:
            merged.append(by_id.pop(row["id"]))
        else:
            merged.append(row)
    for row in by_id.values():
        merged.append(row)
    return merged


async def run(args: argparse.Namespace) -> int:
    if not PDF_ROOT.exists():
        print(f"Missing PDF root: {PDF_ROOT}", file=sys.stderr)
        return 1

    vision_cache = _load_vision_cache()
    target_pages: set[tuple[str, int]] | None = None
    target_ids: set[str] | None = None
    existing_questions: list[dict[str, Any]] = []

    if args.vision_only and OUT.exists():
        bank = json.loads(OUT.read_text(encoding="utf-8"))
        existing_questions = bank["questions"]
        target_pages = {
            (q["source_key"], int(q["page"]))
            for q in existing_questions
            if q.get("has_image") or q.get("format") == "diagram"
        }
        target_ids = {
            q["id"]
            for q in existing_questions
            if q.get("has_image") or q.get("format") == "diagram"
        }
        print(f"Vision-only mode: {len(target_pages)} pages / {len(target_ids)} bank records", flush=True)

    all_records: list[QuestionRecord] = []
    for pdf in sorted(PDF_ROOT.rglob("*.pdf")):
        print(f"Extracting {pdf.name}...", flush=True)
        recs = await extract_pdf(
            pdf,
            vision_only=args.vision_only,
            vision_cache=vision_cache,
            force_vision=args.force,
            target_ids=target_ids,
            target_pages=target_pages,
        )
        print(f"  -> {len(recs)} questions", flush=True)
        all_records.extend(recs)

    if args.vision_only and existing_questions:
        payload_questions = _merge_vision_updates(existing_questions, all_records)
    else:
        payload_questions = [asdict(r) for r in dedupe_bank(all_records)]

    version = "1.4.3" if args.vision_only or any(
        q.get("extraction_method") == "hybrid_vision" for q in payload_questions
    ) else "1.0.0"

    payload = {
        "version": version,
        "extraction_tag": "vision_enriched_extraction" if version.startswith("1.4") else "",
        "total_questions": len(payload_questions),
        "source_pdfs": len(list(PDF_ROOT.rglob("*.pdf"))),
        "questions": payload_questions,
    }
    OUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    by_source: dict[str, int] = {}
    by_format: dict[str, int] = {}
    hybrid_count = 0
    for q in payload_questions:
        by_source[q["source_key"]] = by_source.get(q["source_key"], 0) + 1
        by_format[q["format"]] = by_format.get(q["format"], 0) + 1
        if q.get("extraction_method") == "hybrid_vision":
            hybrid_count += 1

    print(f"\nWrote {len(payload_questions)} questions to {OUT} (v{version})")
    print(f"Hybrid vision records: {hybrid_count}")
    print("By source:", dict(sorted(by_source.items())))
    print("By format:", dict(sorted(by_format.items())))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract problem-solver questions from PDFs")
    parser.add_argument(
        "--vision-only",
        action="store_true",
        help="Re-extract only has_image/diagram bank entries with hybrid vision",
    )
    parser.add_argument("--force", action="store_true", help="Ignore vision cache and re-run API calls")
    args = parser.parse_args()
    return asyncio.run(run(args))


if __name__ == "__main__":
    sys.exit(main())
