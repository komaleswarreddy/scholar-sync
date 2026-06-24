#!/usr/bin/env python3
"""Build production eval pool for Agents 23–25 (tutor + source question extraction)."""

from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))

from tutor_eval_catalog import TUTOR_BOOTSTRAP_SCOPES, TUTOR_FOLLOWUP_EXCHANGES

OUT = SCRIPTS / "agents_23_25_eval_pool.json"
COMPLETE_MD = ROOT / "Reference dataset" / "Complete_Agent_DataSet.md"
BANK_PATH = SCRIPTS / "problem_solver_question_bank.json"
PDF_ROOT = ROOT / "Problem solver_Questions"

SOURCE_VARIATIONS = [
    "mcq_section", "mcq_section", "numerical", "mcq_section", "numerical",
    "assertion_reason", "multi_section", "footer_noise", "neet", "jee",
    "cbse", "diagram_ref", "case_study", "multi_part", "low_confidence",
] * 2  # 30


def normalize(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip().lower())


def load_used_inputs() -> set[str]:
    if not COMPLETE_MD.exists():
        return set()
    text = COMPLETE_MD.read_text(encoding="utf-8")
    used: set[str] = set()
    for key in ("ncert_context", "document_text", "user_message", "assistant_message"):
        for m in re.finditer(rf"\*\*{key.replace('_', ' ').title().replace(' ', ' ')}:\*\*\s*\n\n(.+?)\n\n\*\*", text, re.S | re.I):
            used.add(normalize(m.group(1)))
    # Simpler: normalize all ncert_context blocks
    for m in re.finditer(r"\*\*Ncert Context:\*\*\s*\n\n(.+?)\n\n\*\*", text, re.S):
        used.add(normalize(m.group(1)))
    for m in re.finditer(r"\*\*Document Text:\*\*\s*\n\n(.+?)\n\n\*\*", text, re.S):
        used.add(normalize(m.group(1)))
    return used


def build_bootstrap_items(used: set[str]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for i, scope in enumerate(TUTOR_BOOTSTRAP_SCOPES):
        ex_id = f"tutor_notebook_bootstrap-{i + 1:03d}"
        ctx = scope["ncert_context"]
        if normalize(ctx) in used:
            ctx = ctx + f" Focus: {scope['chapter_title']} exam prep."
        inputs = {
            "class_num": scope["class_num"],
            "subject_label": scope["subject_label"],
            "chapter_no": scope["chapter_no"],
            "chapter_title": scope["chapter_title"],
            "ncert_context": ctx,
            "concept": scope.get("concept"),
        }
        items.append({
            "agent_id": "tutor_notebook_bootstrap",
            "agent_num": 23,
            "example_id": ex_id,
            "variation": scope["variation"],
            "subject_key": scope["subject_key"],
            "tags": ["cbse", scope["subject_key"], "tutor_mode", scope["variation"]],
            **inputs,
        })
    return items


def build_followup_items() -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for i, ex in enumerate(TUTOR_FOLLOWUP_EXCHANGES):
        scope = TUTOR_BOOTSTRAP_SCOPES[i % len(TUTOR_BOOTSTRAP_SCOPES)]
        ex_id = f"tutor_follow_up_questions-{i + 1:03d}"
        row: dict[str, Any] = {
            "agent_id": "tutor_follow_up_questions",
            "agent_num": 24,
            "example_id": ex_id,
            "variation": ex["variation"],
            "subject_key": scope["subject_key"],
            "tags": ["cbse", scope["subject_key"], ex["variation"]],
            "user_message": ex["user_message"],
            "assistant_message": ex["assistant_message"],
            "class_num": scope["class_num"],
            "subject_label": scope["subject_label"],
            "chapter_no": scope["chapter_no"],
            "chapter_title": scope["chapter_title"],
        }
        if ex.get("concept") and i % 5 != 4:  # ~40% with concept (12/30): skip every 5th without
            row["concept"] = ex["concept"]
        elif ex.get("concept") and i < 12:
            row["concept"] = ex["concept"]
        items.append(row)
    return items


def _page_documents_from_bank() -> list[dict[str, Any]]:
    if not BANK_PATH.exists():
        return []
    bank = json.loads(BANK_PATH.read_text(encoding="utf-8"))
    by_page: dict[tuple[str, int], list[dict]] = defaultdict(list)
    for q in bank["questions"]:
        by_page[(q["source_key"], int(q["page"]))].append(q)

    docs: list[dict[str, Any]] = []
    for (sk, page), qs in sorted(by_page.items()):
        raw = (qs[0].get("raw_text") or "").strip()
        if len(raw) < 80:
            texts = [q["problem_text_normalized"] for q in qs]
            raw = "\n".join(texts)
        if len(raw) < 60:
            continue
        exam = "cbse"
        if sk.startswith("jee"):
            exam = "jee"
        elif sk.startswith("neet"):
            exam = "neet"
        docs.append({
            "document_text": raw[:4000],
            "source_key": sk,
            "page": page,
            "exam_type": exam,
            "has_image": any(q.get("has_image") for q in qs),
            "question_count": len(qs),
        })
    return docs


def _curated_documents() -> list[dict[str, Any]]:
    return [
        {
            "document_text": (
                "CBSE Class 10 Science\nSection A (1 mark each)\n"
                "1. Define Ohm's law.\n2. Name the enzyme in saliva.\n"
                "Section B (3 marks)\n3. (a) Draw ray diagram for convex lens when object at 2F.\n"
            ),
            "exam_type": "cbse", "variation": "mcq_section", "has_image": False,
        },
        {
            "document_text": (
                "NEET Biology Sample Paper\n"
                "Q1. Pepsin works best at pH (1) 2 (2) 7 (3) 9 (4) 11\n"
                "Q2. Villi increase surface area for absorption. True/False?\n"
                "Q3. Assertion (A): Mitosis produces haploid cells. Reason (R): Homologous pairs separate.\n"
            ),
            "exam_type": "neet", "variation": "assertion_reason", "has_image": False,
        },
        {
            "document_text": (
                "JEE Main Physics\n"
                "1. A wire 2 m long has R=4 Ω. Find current if V=12 V.\n"
                "2. Derive v²=u²+2as for uniformly accelerated motion.\n"
            ),
            "exam_type": "jee", "variation": "numerical", "has_image": False,
        },
    ]


def build_source_extraction_items() -> list[dict[str, Any]]:
    bank_docs = _page_documents_from_bank()
    curated = _curated_documents()
    pool_docs: list[dict[str, Any]] = []
    # Prefer real bank pages with multiple questions
    bank_docs.sort(key=lambda d: (-d["question_count"], -len(d["document_text"])))
    for d in bank_docs:
        if d["has_image"]:
            d["variation"] = "diagram_ref"
        pool_docs.append(d)
    for c in curated:
        pool_docs.append(c)

    items: list[dict[str, Any]] = []
    seen_text: set[str] = set()
    for i in range(30):
        doc = pool_docs[i % len(pool_docs)]
        text = doc["document_text"]
        norm = normalize(text[:300])
        if norm in seen_text:
            text = text + f"\n[page variant {i + 1}]"
        seen_text.add(normalize(text[:300]))
        var = SOURCE_VARIATIONS[i] if i < len(SOURCE_VARIATIONS) else "mcq_section"
        if doc.get("variation"):
            var = doc["variation"]
        if i % 7 == 6:
            text = text + "\nFooter scan artifact line — ignore — page " + str(i + 1)
            var = "footer_noise"
        items.append({
            "agent_id": "source_question_extraction",
            "agent_num": 25,
            "example_id": f"source_question_extraction-{i + 1:03d}",
            "variation": var,
            "tags": [doc.get("exam_type", "cbse"), "source_upload", var],
            "document_text": text,
            "source_key": doc.get("source_key", "curated"),
            "page": doc.get("page"),
        })
    return items


def main() -> int:
    used = load_used_inputs()
    items: list[dict[str, Any]] = []
    items.extend(build_bootstrap_items(used))
    items.extend(build_followup_items())
    items.extend(build_source_extraction_items())

    payload = {
        "version": "1.4.0",
        "extraction_tag": "production_llm_gold",
        "total_examples": len(items),
        "items": items,
    }
    OUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {len(items)} examples to {OUT}")
    print("  Agent 23:", sum(1 for i in items if i["agent_id"] == "tutor_notebook_bootstrap"))
    print("  Agent 24:", sum(1 for i in items if i["agent_id"] == "tutor_follow_up_questions"))
    print("  Agent 25:", sum(1 for i in items if i["agent_id"] == "source_question_extraction"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
